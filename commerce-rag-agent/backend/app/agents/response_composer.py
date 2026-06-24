from collections.abc import Iterator
from copy import deepcopy
import os

from app.agents.order_guidance import append_order_guidance
from app.llm.generation import (
    ChatClient,
    GenerationComplete,
    GenerationDelta,
    GenerationResult,
    generate_response_composer_result,
    stream_response_composer_result,
)


def compose_agent_response(
    *,
    query: str,
    result: dict,
    client: ChatClient | None = None,
) -> dict:
    draft_answer = str(result.get("answer") or "").strip()
    if not draft_answer:
        return result

    composed = deepcopy(result)
    draft_with_guidance, draft_guidance = append_order_guidance(draft_answer, composed)
    composed["answer"] = draft_with_guidance
    if draft_guidance:
        composed["order_guidance"] = draft_guidance
    decision = _composer_llm_decision(query, composed)
    if _should_skip_composer(composed, decision):
        return _finalize_without_llm(composed, streaming=False, decision=decision)

    generation = generate_response_composer_result(
        query=query,
        intent=str(result.get("intent", "")),
        draft_answer=draft_with_guidance,
        memory=_as_dict(result.get("memory")),
        product_cards=_as_list(result.get("product_cards")),
        retrieved_items=_as_list(result.get("retrieved_items")),
        comparison=result.get("comparison") if isinstance(result.get("comparison"), dict) else None,
        fallback=draft_with_guidance,
        client=client,
    )
    composed["answer"] = generation.content
    final_answer, guidance = append_order_guidance(composed["answer"], composed)
    composed["answer"] = final_answer
    if guidance:
        composed["order_guidance"] = guidance
    composed["response_composer"] = {
        "llm_enabled": generation.llm_enabled,
        "llm_error": generation.llm_error,
        "provider": generation.provider,
        "model": generation.model,
        "latency_ms": generation.latency_ms,
        "cost_estimate": generation.cost_estimate or {},
        "auto_llm": decision,
    }
    trace_item = {
        "node": "response_composer",
        "llm_enabled": generation.llm_enabled,
        "provider": generation.provider,
        "model": generation.model,
        "provider_latency_ms": generation.latency_ms,
        "cost_estimate": generation.cost_estimate or {},
        "auto_llm": decision,
    }
    if generation.llm_error:
        trace_item["llm_error"] = generation.llm_error
    composed["trace"] = list(result.get("trace", [])) + [trace_item]
    return composed


def stream_compose_agent_response(
    *,
    query: str,
    result: dict,
    client: ChatClient | None = None,
) -> Iterator[dict]:
    draft_answer = str(result.get("answer") or "").strip()
    if not draft_answer:
        yield {"type": "complete", "result": result}
        return

    composed = deepcopy(result)
    draft_with_guidance, draft_guidance = append_order_guidance(draft_answer, composed)
    composed["answer"] = draft_with_guidance
    if draft_guidance:
        composed["order_guidance"] = draft_guidance

    decision = _composer_llm_decision(query, composed)
    if _should_skip_composer(composed, decision):
        composed = _finalize_without_llm(composed, streaming=True, decision=decision)
        for chunk in _stream_chunks(str(composed.get("answer") or "")):
            yield {"type": "delta", "content": chunk}
        yield {"type": "complete", "result": composed}
        return

    generation = GenerationResult(content=draft_with_guidance, llm_enabled=False)
    for event in stream_response_composer_result(
        query=query,
        intent=str(result.get("intent", "")),
        draft_answer=draft_with_guidance,
        memory=_as_dict(result.get("memory")),
        product_cards=_as_list(result.get("product_cards")),
        retrieved_items=_as_list(result.get("retrieved_items")),
        comparison=result.get("comparison") if isinstance(result.get("comparison"), dict) else None,
        fallback=draft_with_guidance,
        client=client,
    ):
        if isinstance(event, GenerationDelta):
            yield {"type": "delta", "content": event.content}
        elif isinstance(event, GenerationComplete):
            generation = event.result

    composed["answer"] = generation.content
    final_answer, guidance = append_order_guidance(composed["answer"], composed)
    if final_answer.startswith(composed["answer"]):
        suffix = final_answer[len(composed["answer"]) :]
        if suffix:
            yield {"type": "delta", "content": suffix}
    composed["answer"] = final_answer
    if guidance:
        composed["order_guidance"] = guidance
    composed["response_composer"] = {
        "llm_enabled": generation.llm_enabled,
        "llm_error": generation.llm_error,
        "provider": generation.provider,
        "model": generation.model,
        "latency_ms": generation.latency_ms,
        "cost_estimate": generation.cost_estimate or {},
        "auto_llm": decision,
    }
    trace_item = {
        "node": "response_composer",
        "llm_enabled": generation.llm_enabled,
        "provider": generation.provider,
        "model": generation.model,
        "provider_latency_ms": generation.latency_ms,
        "cost_estimate": generation.cost_estimate or {},
        "streaming": True,
        "auto_llm": decision,
    }
    if generation.llm_error:
        trace_item["llm_error"] = generation.llm_error
    composed["trace"] = list(result.get("trace", [])) + [trace_item]
    yield {"type": "complete", "result": composed}


def _as_dict(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list:
    return value if isinstance(value, list) else []


def _finalize_without_llm(composed: dict, *, streaming: bool, decision: dict) -> dict:
    composed["response_composer"] = {
        "llm_enabled": False,
        "llm_error": None,
        "provider": "",
        "model": "",
        "latency_ms": 0,
        "cost_estimate": {},
        "skipped": True,
        "skip_reason": _skip_reason(composed, decision),
        "auto_llm": decision,
    }
    trace_item = {
        "node": "response_composer",
        "llm_enabled": False,
        "provider": "",
        "model": "",
        "provider_latency_ms": 0,
        "cost_estimate": {},
        "streaming": streaming,
        "skipped": True,
        "skip_reason": _skip_reason(composed, decision),
        "auto_llm": decision,
    }
    composed["trace"] = list(composed.get("trace", [])) + [trace_item]
    return composed


def _should_skip_composer(result: dict, decision: dict) -> bool:
    if not _env_bool("RESPONSE_COMPOSER_ENABLED", True):
        return True
    if _env_bool("RESPONSE_COMPOSER_FORCE_LLM", False):
        return False
    if bool(result.get("skip_response_composer")):
        return True
    if bool(decision.get("use_llm")):
        return False
    if _env_bool("RESPONSE_COMPOSER_COMPLEX_ONLY", True):
        return True
    intent = str(result.get("intent") or "").strip().lower()
    if intent in _skip_intents():
        return True
    if _env_bool("FAST_RECOMMENDATION_TEMPLATE_ONLY", True) and intent in _recommendation_intents():
        return True
    return False


def _skip_reason(result: dict, decision: dict) -> str:
    if not _env_bool("RESPONSE_COMPOSER_ENABLED", True):
        return "RESPONSE_COMPOSER_ENABLED=false"
    if bool(result.get("skip_response_composer")):
        return "result_skip_response_composer"
    intent = str(result.get("intent") or "").strip().lower()
    if intent in _skip_intents():
        return f"fast_intent:{intent}"
    if intent in _recommendation_intents():
        return f"fast_recommendation:{intent}"
    return "fast_path"


def _composer_llm_decision(query: str, result: dict) -> dict:
    intent = str(result.get("intent") or "").strip().lower()
    if not _env_bool("RESPONSE_COMPOSER_AUTO_LLM_ENABLED", True):
        return _decision(False, "auto_llm_disabled", intent, [])
    if _env_bool("RESPONSE_COMPOSER_FORCE_LLM", False):
        return _decision(True, "force_llm", intent, ["force_llm"])
    if not _env_bool("RESPONSE_COMPOSER_ENABLED", True):
        return _decision(False, "composer_disabled", intent, [])
    if bool(result.get("skip_response_composer")):
        return _decision(False, "result_skip_response_composer", intent, [])
    if intent in _skip_intents():
        return _decision(False, f"fast_intent:{intent}", intent, [])
    if intent not in _auto_llm_intents():
        return _decision(False, f"intent_not_auto_llm:{intent or 'unknown'}", intent, [])

    features = _complex_features(query, result, intent)
    if features:
        return _decision(True, "complex_query", intent, features)
    return _decision(False, f"fast_default:{intent or 'unknown'}", intent, [])


def _decision(use_llm: bool, reason: str, intent: str, features: list[str]) -> dict:
    return {
        "enabled": _env_bool("RESPONSE_COMPOSER_AUTO_LLM_ENABLED", True),
        "complex_only": _env_bool("RESPONSE_COMPOSER_COMPLEX_ONLY", True),
        "use_llm": use_llm,
        "reason": reason,
        "intent": intent,
        "features": features,
    }


def _complex_features(query: str, result: dict, intent: str) -> list[str]:
    text = str(query or "").strip().lower()
    features: list[str] = []
    if intent == "decision_guide":
        features.append("decision_guide_intent")
    if _contains_any(text, _complex_keywords()):
        features.append("complex_keyword")
    if len(text) >= _complex_query_min_chars():
        features.append("long_query")
    if len(str(result.get("answer") or "")) >= _complex_draft_min_chars():
        features.append("long_draft")
    if isinstance(result.get("comparison"), dict) and intent in {"compare", "comparison"}:
        features.append("comparison_payload")
    if result.get("product_cards") and _contains_any(text, _decision_keywords()):
        features.append("product_decision_request")
    return list(dict.fromkeys(features))


def _skip_intents() -> set[str]:
    raw = os.getenv("RESPONSE_COMPOSER_SKIP_INTENTS", "chitchat,purchase_help,clarification,order_query").strip()
    return {item.strip().lower() for item in raw.split(",") if item.strip()}


def _recommendation_intents() -> set[str]:
    raw = os.getenv(
        "RESPONSE_COMPOSER_FAST_RECOMMENDATION_INTENTS",
        "shopping_guide,multimodal_search,comparison,compare,decision_guide,image_text_fallback",
    ).strip()
    return {item.strip().lower() for item in raw.split(",") if item.strip()}


def _auto_llm_intents() -> set[str]:
    raw = os.getenv(
        "RESPONSE_COMPOSER_AUTO_LLM_INTENTS",
        "shopping_guide,multimodal_search,comparison,compare,decision_guide,product_knowledge,faq,image_text_fallback",
    ).strip()
    return {item.strip().lower() for item in raw.split(",") if item.strip()}


def _complex_keywords() -> list[str]:
    return [
        "\u4e3a\u4ec0\u4e48",
        "\u539f\u56e0",
        "\u89e3\u91ca",
        "\u8be6\u7ec6",
        "\u5c55\u5f00",
        "\u6df1\u5165",
        "\u6df1\u5ea6",
        "\u5168\u9762",
        "\u957f\u6587",
        "\u603b\u7ed3",
        "\u62a5\u544a",
        "\u5206\u6790",
        "\u4f18\u7f3a\u70b9",
        "\u5229\u5f0a",
        "\u53d6\u820d",
        "\u6743\u8861",
        "\u98ce\u9669",
        "\u5dee\u8bc4",
        "\u6700\u7ec8\u5efa\u8bae",
        "\u8d2d\u4e70\u5efa\u8bae",
        "\u51b3\u7b56",
        "\u600e\u4e48\u9009",
        "\u5982\u4f55\u9009",
        "\u9002\u5408\u6211",
        "\u54ea\u6b3e\u66f4\u9002\u5408",
        "\u54ea\u4e2a\u66f4\u9002\u5408",
        "why",
        "explain",
        "detailed",
        "deep",
        "summary",
        "summarize",
        "analysis",
        "tradeoff",
        "trade-off",
        "pros and cons",
        "final recommendation",
        "which should i buy",
        "help me decide",
    ]


def _decision_keywords() -> list[str]:
    return [
        "\u600e\u4e48\u9009",
        "\u5982\u4f55\u9009",
        "\u54ea\u4e2a\u66f4\u9002\u5408",
        "\u54ea\u6b3e\u66f4\u9002\u5408",
        "\u6700\u7ec8\u5efa\u8bae",
        "\u8d2d\u4e70\u5efa\u8bae",
        "\u5e2e\u6211\u51b3\u7b56",
        "\u51b3\u7b56",
        "which should i buy",
        "help me decide",
        "final recommendation",
    ]


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _complex_query_min_chars() -> int:
    try:
        return max(int(os.getenv("RESPONSE_COMPOSER_COMPLEX_QUERY_MIN_CHARS", "60")), 1)
    except ValueError:
        return 60


def _complex_draft_min_chars() -> int:
    try:
        return max(int(os.getenv("RESPONSE_COMPOSER_COMPLEX_DRAFT_MIN_CHARS", "360")), 1)
    except ValueError:
        return 360


def _stream_chunks(text: str, *, chunk_size: int = 12) -> Iterator[str]:
    if not text:
        return
    for index in range(0, len(text), chunk_size):
        yield text[index : index + chunk_size]


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
