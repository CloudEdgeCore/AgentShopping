from dataclasses import dataclass, field
import os
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tables import Product
from app.retrieval.reranker import rerank_image_candidates
from app.services.image_search_service import ImageSearchService
from app.services.product_search_service import ProductSearchService
from app.services.taxonomy import product_matches_category, product_matches_subcategory


@dataclass
class RetrievalResult:
    """统一检索结果，供 agent node 消费。"""

    products: list[Product] = field(default_factory=list)
    """SQLAlchemy Product 对象列表（文本检索路径才有）。"""

    image_products: list[dict[str, Any]] = field(default_factory=list)
    """图片搜索聚合后的商品 dict（图片检索路径才有）。"""

    image_candidates_raw: list[dict[str, Any]] = field(default_factory=list)
    """图片搜索原始 hits / reranker 结果。"""

    trace: dict[str, Any] = field(default_factory=dict)
    """检索追踪信息。"""


# ── 视觉风格关键词（用于判断“找类似”类 query） ──────────────────────────

_VISUAL_STYLE_TRIGGERS = [
    "类似这",
    "找类似",
    "同款",
    "相似",
    "这种风格",
    "这种款式",
    "一样",
    "同风格",
    "同类型",
    "外观",
    "similar",
    "same style",
    "looks like",
]


def _is_visual_style_query(query: str) -> bool:
    lowered = (query or "").lower()
    return any(keyword in lowered for keyword in _VISUAL_STYLE_TRIGGERS)


class RetrievalOrchestrator:
    """统一 Agent 检索入口。

    根据意图 / 上下文决定用什么检索路径：

    - 用户上传图片（image_path 非空）→ 以图搜图 + reranker
    - 用户说“找类似这种风格”      → 文搜图 + reranker
    - 其他购物 query              → 商品文本向量检索
    """

    def __init__(self, chroma_path: str | None = None) -> None:
        self.product_search = ProductSearchService(chroma_path=chroma_path)
        self.image_search = ImageSearchService(chroma_path=chroma_path)

    # ── 统一入口 ──────────────────────────────────────────────────────

    def search(
        self,
        db: Session,
        query: str,
        *,
        intent: str = "",
        memory: dict[str, Any] | None = None,
        image_path: str | None = None,
        candidates: list[Product] | None = None,
        limit: int = 8,
    ) -> RetrievalResult:
        """根据上下文自动路由到合适的检索服务。"""

        # 1) 以图搜图
        if image_path:
            return self._route_image_search(
                db,
                query,
                image_path,
                memory=memory,
                limit=limit,
            )

        # 2) 文搜图：视觉风格匹配
        if _is_visual_style_query(query) or intent == "multimodal_search":
            return self._route_text_image_search(
                db,
                query,
                memory=memory,
                limit=limit,
            )

        # 3) 商品文本检索
        return self._route_product_search(
            db,
            query,
            memory=memory,
            candidates=candidates,
        )

    # ── 各路由实现 ────────────────────────────────────────────────────

    def _route_image_search(
        self,
        db: Session,
        query: str,
        image_path: str,
        *,
        memory: dict[str, Any] | None = None,
        limit: int = 8,
    ) -> RetrievalResult:
        """以图搜图 + 视觉文本召回融合 → reranker → 结果。"""

        self.image_search.ensure_indexed(db)
        result_limit = _normalize_limit(limit)
        image_candidates = self.image_search.search_by_image(
            image_path,
            limit=max(result_limit * 3, 24),
        )
        mem = memory or {}
        fusion_query = _build_image_fusion_query(query, mem)
        text_candidates: list[dict[str, Any]] = []
        if fusion_query:
            text_candidates = self.image_search.search_by_text(
                fusion_query,
                limit=max(result_limit * 3, 24),
            )
        fused_candidates = _merge_image_candidate_pool(
            image_candidates,
            text_candidates,
            image_source="image_vector",
            text_source="vision_text",
        )

        if not fused_candidates:
            return RetrievalResult(
                trace={
                    "retrieval_mode": "image_search_fused",
                    "image_hits": 0,
                    "text_image_hits": 0,
                    "product_hits": 0,
                }
            )

        category = _as_non_empty_string(mem.get("category"))
        subcategory = _as_non_empty_string(mem.get("subcategory"))
        alternative_categories = _as_string_list(mem.get("vision_alternative_categories"))
        alternative_subcategories = _as_string_list(mem.get("vision_alternative_subcategories"))
        budget = _as_int(mem.get("budget_max"))
        visual_terms = _as_string_list(mem.get("visual_terms"))
        taxonomy_mode = _taxonomy_mode(query, mem)
        taxonomy_weight = _taxonomy_weight_from_memory(mem, taxonomy_mode)

        ranked = rerank_image_candidates(
            fused_candidates,
            text_query=fusion_query or query,
            budget_max=budget,
            category=category,
            subcategory=subcategory,
            alternative_categories=alternative_categories,
            alternative_subcategories=alternative_subcategories,
            visual_terms=visual_terms,
            taxonomy_mode=taxonomy_mode,
            taxonomy_weight=taxonomy_weight,
        )

        # 降级策略：如果预算过滤后没有结果，放宽预算再排一次。
        relaxed_budget = False
        if not ranked and budget is not None:
            ranked = rerank_image_candidates(
                fused_candidates,
                text_query=fusion_query or query,
                budget_max=None,
                category=category,
                subcategory=subcategory,
                alternative_categories=alternative_categories,
                alternative_subcategories=alternative_subcategories,
                visual_terms=visual_terms,
                taxonomy_mode=taxonomy_mode,
                taxonomy_weight=taxonomy_weight,
            )
            relaxed_budget = bool(ranked)
        relaxed_taxonomy = False
        if not ranked and taxonomy_mode == "hard":
            taxonomy_mode = "soft"
            relaxed_taxonomy = True
            ranked = rerank_image_candidates(
                fused_candidates,
                text_query=fusion_query or query,
                budget_max=None if relaxed_budget else budget,
                category=category,
                subcategory=subcategory,
                alternative_categories=alternative_categories,
                alternative_subcategories=alternative_subcategories,
                visual_terms=visual_terms,
                taxonomy_mode=taxonomy_mode,
                taxonomy_weight=taxonomy_weight,
            )

        product_ids = [
            product_id
            for product_id in (_hit_product_id(item) for item in ranked)
            if product_id
        ]

        products = _apply_hard_filters(
            self._load_products(db, product_ids, in_stock_only=True),
            mem,
            enforce_budget=not relaxed_budget,
            enforce_taxonomy=taxonomy_mode == "hard",
        )
        product_by_id = {product.id: product for product in products}

        image_products: list[dict[str, Any]] = []

        for item in ranked[:result_limit]:
            product_id = _hit_product_id(item)
            product = product_by_id.get(product_id) if product_id else None

            if not product:
                continue

            image_products.append(_image_product_payload(product, item))

        return RetrievalResult(
            products=products,
            image_products=image_products,
            image_candidates_raw=ranked[:result_limit],
            trace={
                "retrieval_mode": "image_search_fused",
                "image_hits": len(image_candidates),
                "text_image_hits": len(text_candidates),
                "fused_hits": len(fused_candidates),
                "ranked_hits": len(ranked),
                "product_hits": len(image_products),
                "relaxed_budget": relaxed_budget,
                "relaxed_taxonomy": relaxed_taxonomy,
                "filtered_out": len(set(product_ids)) - len(products),
                "fusion_sources": _fusion_source_counts(fused_candidates),
                "filter_constraints": {
                    "category": category,
                    "subcategory": subcategory,
                    "alternative_categories": alternative_categories or [],
                    "alternative_subcategories": alternative_subcategories or [],
                    "budget_max": budget,
                    "visual_terms": visual_terms,
                    "taxonomy_mode": taxonomy_mode,
                    "taxonomy_weight": taxonomy_weight,
                    "in_stock_only": True,
                },
                "fusion_query": fusion_query,
                "confidence": _ranked_confidence(ranked),
                "low_confidence": _image_low_confidence(ranked, mem),
                "vision_confidence": _as_float(mem.get("vision_confidence"), 0.0),
                "vision_summary": mem.get("vision_summary", ""),
                "vision_object_count": mem.get("vision_object_count"),
                "vision_object_candidates": mem.get("vision_object_candidates", []),
                "vision_quality_flags": mem.get("vision_quality_flags", []),
            },
        )

    def _route_text_image_search(
        self,
        db: Session,
        query: str,
        *,
        memory: dict[str, Any] | None = None,
        limit: int = 8,
    ) -> RetrievalResult:
        """文搜图 → reranker → 结果。"""

        self.image_search.ensure_indexed(db)
        result_limit = _normalize_limit(limit)
        image_candidates = self.image_search.search_by_text(
            query,
            limit=max(result_limit * 3, 24),
        )

        if not image_candidates:
            return RetrievalResult(
                trace={
                    "retrieval_mode": "text_image_search",
                    "image_hits": 0,
                    "product_hits": 0,
                }
            )

        mem = memory or {}
        category = _as_non_empty_string(mem.get("category"))
        subcategory = _as_non_empty_string(mem.get("subcategory"))
        alternative_categories = _as_string_list(mem.get("vision_alternative_categories"))
        alternative_subcategories = _as_string_list(mem.get("vision_alternative_subcategories"))
        budget = _as_int(mem.get("budget_max"))
        visual_terms = _as_string_list(mem.get("visual_terms"))
        taxonomy_mode = _taxonomy_mode(query, mem)
        taxonomy_weight = _taxonomy_weight_from_memory(mem, taxonomy_mode)

        ranked = rerank_image_candidates(
            image_candidates,
            text_query=query,
            budget_max=budget,
            category=category,
            subcategory=subcategory,
            alternative_categories=alternative_categories,
            alternative_subcategories=alternative_subcategories,
            visual_terms=visual_terms,
            taxonomy_mode=taxonomy_mode,
            taxonomy_weight=taxonomy_weight,
        )
        relaxed_budget = False
        if not ranked and budget is not None:
            ranked = rerank_image_candidates(
                image_candidates,
                text_query=query,
                budget_max=None,
                category=category,
                subcategory=subcategory,
                alternative_categories=alternative_categories,
                alternative_subcategories=alternative_subcategories,
                visual_terms=visual_terms,
                taxonomy_mode=taxonomy_mode,
                taxonomy_weight=taxonomy_weight,
            )
            relaxed_budget = bool(ranked)
        relaxed_taxonomy = False
        if not ranked and taxonomy_mode == "hard":
            taxonomy_mode = "soft"
            relaxed_taxonomy = True
            ranked = rerank_image_candidates(
                image_candidates,
                text_query=query,
                budget_max=None if relaxed_budget else budget,
                category=category,
                subcategory=subcategory,
                alternative_categories=alternative_categories,
                alternative_subcategories=alternative_subcategories,
                visual_terms=visual_terms,
                taxonomy_mode=taxonomy_mode,
                taxonomy_weight=taxonomy_weight,
            )

        product_ids = [
            product_id
            for product_id in (_hit_product_id(item) for item in ranked)
            if product_id
        ]

        products = _apply_hard_filters(
            self._load_products(db, product_ids, in_stock_only=True),
            mem,
            enforce_budget=not relaxed_budget,
            enforce_taxonomy=taxonomy_mode == "hard",
        )
        product_by_id = {product.id: product for product in products}

        image_products: list[dict[str, Any]] = []

        for item in ranked[:result_limit]:
            product_id = _hit_product_id(item)
            product = product_by_id.get(product_id) if product_id else None

            if not product:
                continue

            image_products.append(_image_product_payload(product, item))

        return RetrievalResult(
            products=products,
            image_products=image_products,
            image_candidates_raw=ranked[:result_limit],
            trace={
                "retrieval_mode": "text_image_search_reranked",
                "image_hits": len(image_candidates),
                "ranked_hits": len(ranked),
                "product_hits": len(image_products),
                "relaxed_budget": relaxed_budget,
                "relaxed_taxonomy": relaxed_taxonomy,
                "filtered_out": len(set(product_ids)) - len(products),
                "filter_constraints": {
                    "category": category,
                    "subcategory": subcategory,
                    "alternative_categories": alternative_categories or [],
                    "alternative_subcategories": alternative_subcategories or [],
                    "budget_max": budget,
                    "visual_terms": visual_terms,
                    "taxonomy_mode": taxonomy_mode,
                    "taxonomy_weight": taxonomy_weight,
                    "in_stock_only": True,
                },
                "confidence": _ranked_confidence(ranked),
                "low_confidence": _image_low_confidence(ranked, mem),
                "vision_summary": mem.get("vision_summary", ""),
            },
        )

    def _route_product_search(
        self,
        db: Session,
        query: str,
        *,
        memory: dict[str, Any] | None = None,
        candidates: list[Product] | None = None,
    ) -> RetrievalResult:
        """商品文本检索：有 candidates 时 hybrid_search，否则纯 vector_search。"""

        if candidates is not None:
            ranked, trace = self.product_search.hybrid_search(
                db,
                query,
                candidates,
                memory=memory,
            )
            return RetrievalResult(products=ranked, trace=trace)

        ranked, trace = self.product_search.hybrid_search(
            db,
            query,
            [],
            memory=memory,
        )
        return RetrievalResult(products=ranked, trace=trace)

    # ── 工具 ──────────────────────────────────────────────────────────

    @staticmethod
    def _load_products(db: Session, product_ids: list[str], *, in_stock_only: bool = False) -> list[Product]:
        if not product_ids:
            return []

        unique_ids = list(dict.fromkeys(product_ids))
        statement = select(Product).where(Product.id.in_(unique_ids))
        if in_stock_only:
            statement = statement.where(Product.stock > 0)

        product_map: dict[str, Product] = {
            product.id: product
            for product in db.scalars(statement).all()
        }

        return [
            product_map[product_id]
            for product_id in unique_ids
            if product_id in product_map
        ]


def _hit_product_id(item: dict[str, Any]) -> str | None:
    """兼容 reranker 返回顶层 product_id 或 metadata.product_id。"""
    return item.get("product_id") or item.get("metadata", {}).get("product_id")


def _apply_hard_filters(
    products: list[Product],
    memory: dict[str, Any] | None,
    *,
    enforce_budget: bool = True,
    enforce_taxonomy: bool = True,
    in_stock_only: bool = True,
) -> list[Product]:
    if not memory:
        return [product for product in products if not in_stock_only or product.stock > 0]

    category = memory.get("category")
    subcategory = memory.get("subcategory")
    budget_max = memory.get("budget_max")
    filtered = [product for product in products if not in_stock_only or product.stock > 0]

    if enforce_taxonomy and category:
        filtered = [product for product in filtered if product_matches_category(product, str(category))]
    if enforce_taxonomy and subcategory:
        filtered = [product for product in filtered if product_matches_subcategory(product, str(subcategory))]
    if enforce_budget and budget_max is not None:
        try:
            budget = int(budget_max)
        except (TypeError, ValueError):
            budget = None
        if budget is not None:
            filtered = [product for product in filtered if product.price <= budget]

    return filtered


def _image_product_payload(product: Product, item: dict[str, Any]) -> dict[str, Any]:
    metadata = item.get("metadata") or {}
    return {
        "product_id": product.id,
        "title": product.title,
        "category": product.category,
        "subcategory": product.subcategory or "",
        "price": product.price,
        "rating": product.rating,
        "sales": product.sales,
        "stock": product.stock,
        "image_url": product.image_url,
        "image_similarity": item.get("image_similarity", 0),
        "text_image_similarity": item.get("text_image_similarity", 0),
        "final_score": item.get("final_score", 0),
        "matched_image_id": metadata.get("image_id", ""),
        "matched_filters": item.get("matched_filters", {}),
        "retrieval_sources": item.get("retrieval_sources", []),
        "score_breakdown": item.get("score_breakdown", {}),
    }


def _normalize_limit(limit: int) -> int:
    try:
        value = int(limit)
    except (TypeError, ValueError):
        value = 8
    return min(max(value, 1), 24)


def _as_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_non_empty_string(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None


def _as_string_list(value: object) -> list[str] | None:
    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
    elif isinstance(value, str) and value.strip():
        items = [value.strip()]
    else:
        items = []
    return items or None


def _as_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _ranked_confidence(ranked: list[dict[str, Any]]) -> float:
    if not ranked:
        return 0.0
    return round(_as_float(ranked[0].get("final_score"), 0.0), 4)


def _image_low_confidence(ranked: list[dict[str, Any]], memory: dict[str, Any]) -> bool:
    if bool(memory.get("vision_needs_clarification")):
        return True
    threshold = _env_float("IMAGE_SEARCH_MIN_CONFIDENCE", 0.28)
    if threshold <= 0:
        return False
    return _ranked_confidence(ranked) < threshold


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def _build_image_fusion_query(query: str, memory: dict[str, Any]) -> str:
    attributes = memory.get("visual_attributes") if isinstance(memory.get("visual_attributes"), dict) else {}
    attribute_values: list[str] = []
    for value in attributes.values():
        if isinstance(value, list):
            attribute_values.extend(str(item).strip() for item in value if str(item).strip())
        elif str(value or "").strip():
            attribute_values.append(str(value).strip())
    parts = [
        query,
        memory.get("image_query") or "",
        memory.get("vision_summary") or "",
        memory.get("vision_category") or "",
        memory.get("vision_subcategory") or "",
        " ".join(_as_string_list(memory.get("visual_terms")) or []),
        " ".join(attribute_values[:8]),
    ]
    return " ".join(part for part in parts if str(part or "").strip()).strip()


def _merge_image_candidate_pool(
    image_candidates: list[dict[str, Any]],
    text_candidates: list[dict[str, Any]],
    *,
    image_source: str,
    text_source: str,
) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    order = 0

    for rank, candidate in enumerate(image_candidates, start=1):
        order = _merge_one_candidate(
            merged,
            candidate,
            source=image_source,
            similarity_key="image_similarity",
            source_score_key="image",
            rank=rank,
            order=order,
        )

    for rank, candidate in enumerate(text_candidates, start=1):
        order = _merge_one_candidate(
            merged,
            candidate,
            source=text_source,
            similarity_key="text_image_similarity",
            source_score_key="vision_text",
            rank=rank,
            order=order,
        )

    return sorted(
        merged.values(),
        key=lambda item: (
            -max(
                _as_float(item.get("image_similarity"), 0.0),
                _as_float(item.get("text_image_similarity"), 0.0),
            ),
            item.get("_fusion_order", 0),
        ),
    )


def _merge_one_candidate(
    merged: dict[str, dict[str, Any]],
    candidate: dict[str, Any],
    *,
    source: str,
    similarity_key: str,
    source_score_key: str,
    rank: int,
    order: int,
) -> int:
    metadata = candidate.get("metadata") or {}
    product_id = metadata.get("product_id")
    candidate_id = str(product_id or candidate.get("id") or "")
    if not candidate_id:
        return order

    similarity = _as_float(candidate.get("image_similarity"), 0.0)
    existing = merged.get(candidate_id)
    if existing is None:
        existing = {
            **candidate,
            "metadata": metadata,
            "image_similarity": 0.0,
            "text_image_similarity": 0.0,
            "source_scores": {},
            "source_ranks": {},
            "retrieval_sources": [],
            "_fusion_order": order,
        }
        merged[candidate_id] = existing
        order += 1

    if similarity > _as_float(existing.get(similarity_key), 0.0):
        existing[similarity_key] = similarity
        existing["id"] = candidate.get("id", existing.get("id"))
        existing["text"] = candidate.get("text", existing.get("text", ""))
        existing["metadata"] = {**existing.get("metadata", {}), **metadata}
        if candidate.get("distance") is not None:
            existing["distance"] = candidate.get("distance")

    source_scores = existing.setdefault("source_scores", {})
    source_scores[source_score_key] = max(_as_float(source_scores.get(source_score_key), 0.0), similarity)
    source_ranks = existing.setdefault("source_ranks", {})
    source_ranks[source_score_key] = min(int(source_ranks.get(source_score_key, rank)), rank)
    sources = existing.setdefault("retrieval_sources", [])
    if source not in sources:
        sources.append(source)
    return order


def _fusion_source_counts(candidates: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for candidate in candidates:
        for source in candidate.get("retrieval_sources") or []:
            counts[str(source)] = counts.get(str(source), 0) + 1
    return counts


def _taxonomy_mode(query: str, memory: dict[str, Any]) -> str:
    explicit_category = _as_non_empty_string(memory.get("explicit_category"))
    explicit_subcategory = _as_non_empty_string(memory.get("explicit_subcategory"))
    if explicit_category or explicit_subcategory or _query_requests_hard_taxonomy(query):
        return "hard"
    return "soft"


def _taxonomy_weight_from_memory(memory: dict[str, Any], taxonomy_mode: str) -> float:
    confidence = _as_float(memory.get("vision_confidence"), 0.0)
    if taxonomy_mode == "hard":
        return 0.24
    if confidence >= 0.85:
        return 0.24
    if confidence >= 0.65:
        return 0.20
    if confidence >= 0.45:
        return 0.16
    return 0.10


def _query_requests_hard_taxonomy(query: str) -> bool:
    lowered = (query or "").lower()
    hard_words = ["只看", "仅看", "必须是", "不要其他", "同品类", "同类", "限定", "只要"]
    return any(word in lowered for word in hard_words)
