import base64
import json
import mimetypes
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from app.services.taxonomy import load_taxonomy


DEFAULT_VLM_BASE_URL = ""
DEFAULT_DASHSCOPE_COMPATIBLE_BASE_URL = ""


class VisionServiceError(RuntimeError):
    pass


@dataclass
class VisionAnalysis:
    enabled: bool
    provider: str = "disabled"
    model: str = ""
    category: str = ""
    subcategory: str = ""
    alternative_categories: list[str] = field(default_factory=list)
    alternative_subcategories: list[str] = field(default_factory=list)
    visual_terms: list[str] = field(default_factory=list)
    attributes: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    search_query: str = ""
    summary: str = ""
    object_count: int | None = None
    object_candidates: list[dict[str, Any]] = field(default_factory=list)
    quality_flags: list[str] = field(default_factory=list)
    needs_clarification: bool = False
    raw_text: str = ""
    error: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "provider": self.provider,
            "model": self.model,
            "category": self.category,
            "subcategory": self.subcategory,
            "alternative_categories": self.alternative_categories,
            "alternative_subcategories": self.alternative_subcategories,
            "visual_terms": self.visual_terms,
            "attributes": self.attributes,
            "confidence": self.confidence,
            "search_query": self.search_query,
            "summary": self.summary,
            "object_count": self.object_count,
            "object_candidates": self.object_candidates,
            "quality_flags": self.quality_flags,
            "needs_clarification": self.needs_clarification,
            "raw_text": self.raw_text,
            "error": self.error,
        }


def vision_capabilities() -> dict[str, Any]:
    provider = _provider()
    return {
        "provider": provider,
        "configured": _is_enabled_provider(provider) and bool(_api_key(provider)) and bool(_model(provider)),
        "model": _model(provider),
        "taxonomy_categories": [category["name"] for category in load_taxonomy().get("categories", [])],
    }


def analyze_product_image(image_path: str, *, query: str = "") -> VisionAnalysis:
    provider = _provider()
    model = _model(provider)
    if not _is_enabled_provider(provider):
        return VisionAnalysis(enabled=False, provider=provider, model=model, error="VLM_PROVIDER is disabled")
    api_key = _api_key(provider)
    if not api_key:
        return VisionAnalysis(enabled=False, provider=provider, model=model, error="VLM api key is missing")
    if not model:
        return VisionAnalysis(enabled=False, provider=provider, model=model, error="VLM_MODEL is missing")

    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    payload = {
        "model": model,
        "temperature": float(os.getenv("VLM_TEMPERATURE", "0.1")),
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是电商拍照找货的图片理解器。只输出 JSON，不要输出 Markdown。"
                    "你要识别图片中的商品大类、子类、颜色、材质、风格、可见文字和适合检索的关键词。"
                    "只能使用给定 taxonomy 里的 category/subcategory；不能确认就留空。"
                    "不要臆造品牌、型号、功效或图片里看不见的参数。"
                ),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": _vision_prompt(query),
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": _image_data_url(path)},
                    },
                ],
            },
        ],
    }
    if _is_alibaba_omni_provider(provider):
        payload["modalities"] = ["text"]
        payload["stream"] = _env_bool("VLM_STREAM", True)
        if payload["stream"]:
            payload["stream_options"] = {"include_usage": True}
    timeout = float(os.getenv("VLM_TIMEOUT_SECONDS", "60"))
    base_url = _base_url(provider)
    with httpx.Client(timeout=timeout) as client:
        if payload.get("stream"):
            chunks: list[str] = []
            with client.stream(
                "POST",
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    parsed = _parse_sse_json(line)
                    if not parsed:
                        continue
                    for choice in parsed.get("choices") or []:
                        delta = choice.get("delta") or {}
                        if delta.get("content"):
                            chunks.append(str(delta["content"]))
                        message = choice.get("message") or {}
                        if message.get("content"):
                            chunks.append(str(message["content"]))
            raw_text = "".join(chunks).strip()
        else:
            response = client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
            )
            response.raise_for_status()
            raw_text = str(response.json()["choices"][0]["message"]["content"]).strip()
    parsed = _parse_json_object(raw_text)
    return _analysis_from_payload(parsed, provider=provider, model=model, raw_text=raw_text)


def safe_analyze_product_image(image_path: str, *, query: str = "") -> VisionAnalysis:
    try:
        return analyze_product_image(image_path, query=query)
    except Exception as error:
        return VisionAnalysis(
            enabled=False,
            provider=_provider(),
            model=_model(_provider()),
            error=f"{type(error).__name__}: {str(error)[:240]}",
        )


def merge_vision_memory(
    memory: dict[str, Any],
    analysis: VisionAnalysis,
    *,
    prefer_image_taxonomy: bool = False,
) -> dict[str, Any]:
    merged = dict(memory or {})
    merged["visual_search_mode"] = True
    if analysis.search_query:
        merged["image_query"] = analysis.search_query
    if analysis.summary:
        merged["vision_summary"] = analysis.summary
    if analysis.visual_terms:
        existing_terms = merged.get("visual_terms", [])
        if not isinstance(existing_terms, list):
            existing_terms = [str(existing_terms)]
        merged["visual_terms"] = list(dict.fromkeys([*existing_terms, *analysis.visual_terms]))
    if analysis.attributes:
        merged["visual_attributes"] = analysis.attributes
    if analysis.confidence:
        merged["vision_confidence"] = analysis.confidence
    if analysis.category:
        merged["vision_category"] = analysis.category
    if analysis.subcategory:
        merged["vision_subcategory"] = analysis.subcategory
    if analysis.alternative_categories:
        merged["vision_alternative_categories"] = analysis.alternative_categories
    if analysis.alternative_subcategories:
        merged["vision_alternative_subcategories"] = analysis.alternative_subcategories
    if analysis.quality_flags:
        merged["vision_quality_flags"] = analysis.quality_flags
    if analysis.object_count is not None:
        merged["vision_object_count"] = analysis.object_count
    if analysis.object_candidates:
        merged["vision_object_candidates"] = analysis.object_candidates
    if analysis.needs_clarification:
        merged["vision_needs_clarification"] = True

    if analysis.enabled and analysis.confidence >= _taxonomy_confidence_threshold():
        should_override = prefer_image_taxonomy and bool(analysis.category)
        if should_override:
            merged.pop("explicit_category", None)
            merged.pop("explicit_subcategory", None)
        if should_override and analysis.category != merged.get("category"):
            for key in ["last_product_ids", "exclude_product_ids", "product_ids"]:
                merged.pop(key, None)
            merged["category"] = analysis.category
            if analysis.subcategory:
                merged["subcategory"] = analysis.subcategory
            else:
                merged.pop("subcategory", None)
        else:
            if analysis.category and not merged.get("category"):
                merged["category"] = analysis.category
            if analysis.subcategory and not merged.get("subcategory"):
                merged["subcategory"] = analysis.subcategory
    return merged


def build_visual_search_query(query: str, analysis: VisionAnalysis) -> str:
    clean_query = str(query or "").strip()
    image_query = analysis.search_query.strip()
    if clean_query and image_query and image_query not in clean_query:
        return f"{clean_query} {image_query}".strip()
    if clean_query:
        return clean_query
    if image_query:
        return image_query
    if analysis.subcategory:
        return f"找类似{analysis.subcategory}"
    if analysis.category:
        return f"找类似{analysis.category}商品"
    return "以图搜图 找相似商品"


def _provider() -> str:
    return os.getenv("VLM_PROVIDER", "disabled").strip().lower()


def _is_enabled_provider(provider: str) -> bool:
    return provider in {
        "openai",
        "openai_compatible",
        "compatible",
        "doubao",
        "ark",
        "volcengine",
        "alibaba_omni",
        "aliyun_omni",
        "dashscope_omni",
        "qwen_omni",
    }


def _api_key(provider: str) -> str:
    if _is_alibaba_omni_provider(provider):
        return _env_first("VLM_API_KEY", "DASHSCOPE_API_KEY", "ALIBABA_API_KEY")
    return _env_first("VLM_API_KEY", "DOUBAO_VISION_API_KEY", "ARK_API_KEY", "DOUBAO_API_KEY", "OPENAI_API_KEY")


def _base_url(provider: str) -> str:
    default = DEFAULT_DASHSCOPE_COMPATIBLE_BASE_URL if _is_alibaba_omni_provider(provider) else DEFAULT_VLM_BASE_URL
    value = (_env_first("VLM_BASE_URL", "DASHSCOPE_BASE_URL", "DOUBAO_BASE_URL", "OPENAI_BASE_URL") or default).rstrip("/")
    if not value:
        raise VisionServiceError("VLM_BASE_URL is required")
    return value


def _model(provider: str) -> str:
    if _is_alibaba_omni_provider(provider):
        return _env_first("VLM_MODEL")
    return _env_first("VLM_MODEL", "DOUBAO_VISION_MODEL")


def _is_alibaba_omni_provider(provider: str) -> bool:
    return provider in {"alibaba_omni", "aliyun_omni", "dashscope_omni", "qwen_omni"}


def _env_first(*names: str) -> str:
    for name in names:
        value = _resolve_env_reference(os.getenv(name, ""))
        if value:
            return value
    return ""


def _resolve_env_reference(value: str) -> str:
    text = str(value or "").strip()
    if text.startswith("${") and text.endswith("}"):
        return os.getenv(text[2:-1], "").strip()
    return text


def _taxonomy_confidence_threshold() -> float:
    try:
        return float(os.getenv("VLM_TAXONOMY_CONFIDENCE", "0.45"))
    except ValueError:
        return 0.45


def _vision_prompt(query: str) -> str:
    return json.dumps(
        {
            "user_query": query or "",
            "taxonomy": _taxonomy_prompt(),
            "output_schema": {
                "category": "taxonomy category name or empty string",
                "subcategory": "taxonomy subcategory name or empty string",
                "alternative_categories": ["可能的大类，按可能性排序，最多 3 个"],
                "alternative_subcategories": ["可能的子类，按可能性排序，最多 3 个"],
                "visual_terms": ["最多 8 个适合检索的中文关键词"],
                "attributes": {
                    "colors": ["颜色"],
                    "materials": ["材质"],
                    "style": ["风格"],
                    "shape": ["形状/款式"],
                    "visible_text": ["图片中可见文字"],
                },
                "confidence": "0 到 1",
                "search_query": "用于电商搜索的短中文查询",
                "summary": "一句话说明图片里像什么商品",
                "object_count": "图片中主要商品数量，无法判断可为空",
                "object_candidates": [
                    {
                        "label": "可供用户选择的主体名称",
                        "category": "taxonomy category name or empty string",
                        "subcategory": "taxonomy subcategory name or empty string",
                        "confidence": "0 到 1",
                        "bbox": [0, 0, 1, 1],
                        "search_query": "选中该主体后用于检索的短中文查询",
                    }
                ],
                "quality_flags": ["模糊/遮挡/背景干扰/多物体/角度异常等"],
                "needs_clarification": "如果图片无法可靠判断主要商品则为 true",
            },
            "rules": [
                "先识别图片中占主体的商品，再映射到 taxonomy；如果 taxonomy 没有合适项，category/subcategory 留空。",
                "不要为了贴合用户文字而改写图片事实；用户文字只能作为理解拍摄意图的辅助。",
                "不能确认的品牌、型号、功效、材质和参数不要输出；可见文字只写图片里真实出现的内容。",
                "visual_terms 按检索价值排序：商品名词在前，颜色、材质、风格、形状、可见文字在后。",
                "如果存在多个可能品类，把不确定性写到 alternative_categories/alternative_subcategories 和 quality_flags。",
                "search_query 要短，适合直接做电商图文召回，不要超过 24 个中文字符。",
            ],
        },
        ensure_ascii=False,
    )


def _taxonomy_prompt() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for category in load_taxonomy().get("categories", []):
        rows.append(
            {
                "category": category["name"],
                "aliases": category.get("aliases", []),
                "subcategories": [
                    {
                        "name": subcategory["name"],
                        "aliases": subcategory.get("aliases", []),
                    }
                    for subcategory in category.get("subcategories", [])
                ],
            }
        )
    return rows


def _image_data_url(path: Path) -> str:
    media_type = mimetypes.guess_type(str(path))[0] or "image/jpeg"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{media_type};base64,{data}"


def _parse_json_object(raw_text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw_text)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", raw_text, flags=re.DOTALL)
    if not match:
        return {}
    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def _parse_sse_json(line: str) -> dict[str, Any] | None:
    text = str(line or "").strip()
    if not text:
        return None
    if text.startswith("data:"):
        text = text.removeprefix("data:").strip()
    if text == "[DONE]":
        return None
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None


def _analysis_from_payload(payload: dict[str, Any], *, provider: str, model: str, raw_text: str) -> VisionAnalysis:
    taxonomy = load_taxonomy()
    category = _valid_category(str(payload.get("category") or ""), taxonomy)
    subcategory = _valid_subcategory(str(payload.get("subcategory") or ""), taxonomy, category)
    alternative_categories = [
        value
        for value in (_valid_category(item, taxonomy) for item in _string_list(payload.get("alternative_categories")))
        if value and value != category
    ][:3]
    alternative_subcategories = [
        value
        for value in (
            _valid_subcategory(item, taxonomy, category) or _valid_subcategory(item, taxonomy, "")
            for item in _string_list(payload.get("alternative_subcategories"))
        )
        if value and value != subcategory
    ][:3]
    visual_terms = _string_list(payload.get("visual_terms"))[:8]
    attributes = payload.get("attributes") if isinstance(payload.get("attributes"), dict) else {}
    confidence = _bounded_float(payload.get("confidence"), default=0.0)
    search_query = str(payload.get("search_query") or "").strip()
    summary = str(payload.get("summary") or "").strip()
    object_count = _optional_int(payload.get("object_count"))
    object_candidates = _object_candidates(payload.get("object_candidates"), taxonomy, category=category)
    quality_flags = _string_list(payload.get("quality_flags"))[:6]
    needs_clarification = _bool_value(payload.get("needs_clarification"))
    if not search_query:
        pieces = [subcategory, category, *visual_terms[:4]]
        search_query = " ".join(piece for piece in pieces if piece).strip()
    search_query = search_query[:48]
    if not object_candidates:
        object_candidates = _fallback_object_candidates(
            category=category,
            subcategory=subcategory,
            alternatives=alternative_subcategories or alternative_categories,
            visual_terms=visual_terms,
            confidence=confidence,
            search_query=search_query,
        )
    return VisionAnalysis(
        enabled=True,
        provider=provider,
        model=model,
        category=category,
        subcategory=subcategory,
        alternative_categories=list(dict.fromkeys(alternative_categories)),
        alternative_subcategories=list(dict.fromkeys(alternative_subcategories)),
        visual_terms=visual_terms,
        attributes=attributes,
        confidence=confidence,
        search_query=search_query,
        summary=summary,
        object_count=object_count,
        object_candidates=object_candidates,
        quality_flags=quality_flags,
        needs_clarification=needs_clarification,
        raw_text=raw_text,
    )


def _valid_category(value: str, taxonomy: dict[str, Any]) -> str:
    if not value:
        return ""
    for category in taxonomy.get("categories", []):
        if value == category["name"]:
            return category["name"]
    return ""


def _valid_subcategory(value: str, taxonomy: dict[str, Any], category_name: str) -> str:
    if not value:
        return ""
    for category in taxonomy.get("categories", []):
        if category_name and category["name"] != category_name:
            continue
        for subcategory in category.get("subcategories", []):
            if value == subcategory["name"]:
                return subcategory["name"]
    return ""


def _string_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [item.strip() for item in re.split(r"[,，、\s]+", value) if item.strip()]
    return []


def _bounded_float(value: object, *, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(number, 1.0))


def _optional_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _object_candidates(value: object, taxonomy: dict[str, Any], *, category: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    candidates: list[dict[str, Any]] = []
    for index, item in enumerate(value[:6], start=1):
        if not isinstance(item, dict):
            continue
        candidate_category = _valid_category(str(item.get("category") or ""), taxonomy)
        candidate_subcategory = _valid_subcategory(str(item.get("subcategory") or ""), taxonomy, candidate_category or category)
        label = str(item.get("label") or candidate_subcategory or candidate_category or f"主体 {index}").strip()
        search_query = str(item.get("search_query") or "").strip()
        visual_terms = _string_list(item.get("visual_terms"))[:4]
        if not search_query:
            search_query = " ".join(part for part in [candidate_subcategory, candidate_category, *visual_terms] if part).strip()
        bbox = _bbox(item.get("bbox"))
        candidates.append(
            {
                "id": str(item.get("id") or f"obj_{index}"),
                "label": label[:40],
                "category": candidate_category,
                "subcategory": candidate_subcategory,
                "confidence": _bounded_float(item.get("confidence"), default=0.0),
                "bbox": bbox,
                "search_query": search_query[:48] or label[:48],
            }
        )
    return candidates


def _fallback_object_candidates(
    *,
    category: str,
    subcategory: str,
    alternatives: list[str],
    visual_terms: list[str],
    confidence: float,
    search_query: str,
) -> list[dict[str, Any]]:
    label = subcategory or category or (visual_terms[0] if visual_terms else "")
    if not label:
        return []
    candidates = [
        {
            "id": "obj_main",
            "label": label,
            "category": category,
            "subcategory": subcategory,
            "confidence": confidence,
            "bbox": None,
            "search_query": search_query or " ".join([subcategory, category, *visual_terms[:3]]).strip(),
        }
    ]
    for index, alternative in enumerate(alternatives[:3], start=1):
        candidates.append(
            {
                "id": f"obj_alt_{index}",
                "label": alternative,
                "category": category if alternative != category else alternative,
                "subcategory": alternative if alternative != category else "",
                "confidence": max(round(confidence - index * 0.12, 2), 0.05),
                "bbox": None,
                "search_query": alternative,
            }
        )
    return candidates


def _bbox(value: object) -> list[float] | None:
    if not isinstance(value, list) or len(value) != 4:
        return None
    result: list[float] = []
    for item in value:
        try:
            result.append(max(0.0, min(float(item), 1.0)))
        except (TypeError, ValueError):
            return None
    return result


def _bool_value(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "是", "需要"}
    return bool(value)


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
