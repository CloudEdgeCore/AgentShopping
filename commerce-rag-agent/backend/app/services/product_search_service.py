import os
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tables import Product
from app.retrieval.text_index import TextIndex
from app.services.business_rules import rule_list
from app.services.keyword_retrieval_service import KeywordRetrievalService
from app.services.taxonomy import load_taxonomy, product_matches_category, product_matches_subcategory

SearchHits = list[dict[str, Any]]


class ProductSearchService:
    """商品搜索服务：封装向量检索逻辑，提供统一的搜索接口。"""

    def __init__(self, chroma_path: str | None = None) -> None:
        self.chroma_path = chroma_path
        self._text_index: TextIndex | None = None
        self.keyword_search = KeywordRetrievalService()

    # ------------------------------------------------------------------
    # 内部惰性初始化
    # ------------------------------------------------------------------

    def _get_index(self) -> TextIndex:
        if self._text_index is None:
            self._text_index = TextIndex(chroma_path=self.chroma_path)
        return self._text_index

    def ensure_indexed(self, db: Session) -> None:
        """确保商品数据已写入向量库（幂等）。"""
        self._get_index().ensure_products_indexed(db)

    # ------------------------------------------------------------------
    # 纯向量检索
    # ------------------------------------------------------------------

    def vector_search(
        self,
        db: Session,
        query: str,
        *,
        limit: int = 10,
        product_ids: list[str] | None = None,
        ensure_indexed: bool = False,
    ) -> SearchHits:
        """用 query 的语义向量在 ChromaDB 中检索商品。

        ensure_indexed 仅在首次使用且尚未建索引时设为 True。
        """
        if ensure_indexed:
            self.ensure_indexed(db)

        return self._get_index().search_products(
            query,
            limit=limit,
            product_ids=product_ids,
        )

    # ------------------------------------------------------------------
    # 混合检索：SQL 过滤候选 → 向量语义重排序
    # ------------------------------------------------------------------

    def hybrid_search(
        self,
        db: Session,
        query: str,
        candidates: list[Product],
        *,
        memory: dict[str, Any] | None = None,
    ) -> tuple[list[Product], dict[str, Any]]:
        """对 SQL 过滤后的候选商品做向量语义排序。

        返回：
        - 排序后的商品列表；
        - 检索追踪信息。

        如果向量库不可用，降级为按评分 / 销量排序。
        """
        query_text = _build_hybrid_query(query, memory)
        keyword_hits = self.keyword_search.search(
            db,
            query_text,
            memory=memory,
            candidates=candidates or None,
            limit=max(len(candidates), 20) if candidates else 20,
        )
        keyword_scores = _keyword_scores(keyword_hits)

        if not candidates:
            try:
                hits = self.vector_search(
                    db,
                    query_text,
                    limit=10,
                    ensure_indexed=True,
                )
            except Exception as exc:
                keyword_products = [hit["product"] for hit in keyword_hits]
                if keyword_products:
                    ranked = _rank_products(keyword_products, query, memory, {}, keyword_scores)
                    return ranked, {
                        "retrieval_mode": "pure_keyword_vector_failed",
                        "sqlite_candidates": 0,
                        "chroma_hits": [],
                        "keyword_hits": _keyword_hit_ids(keyword_hits),
                        "keyword_top_terms": _keyword_top_terms(keyword_hits),
                        "product_hits": len(ranked),
                        "confidence": _retrieval_confidence(ranked, {}, keyword_scores),
                        "low_confidence": _is_low_confidence(ranked, {}, keyword_scores),
                        "error": f"{type(exc).__name__}: {str(exc)[:160]}",
                        "scoring": "bm25_rules",
                    }
                return [], {
                    "retrieval_mode": "hybrid_keyword_vector_failed",
                    "sqlite_candidates": 0,
                    "chroma_hits": [],
                    "keyword_hits": [],
                    "error": f"{type(exc).__name__}: {str(exc)[:160]}",
                }

            chroma_product_ids = [
                hit.get("metadata", {}).get("product_id")
                for hit in hits
                if hit.get("metadata", {}).get("product_id")
            ]
            product_ids = list(chroma_product_ids)
            product_ids.extend(str(hit["product_id"]) for hit in keyword_hits if hit.get("product_id"))
            loaded_products = _load_products(db, product_ids)
            products = _apply_hard_filters(loaded_products, memory)
            semantic_scores = {
                hit.get("metadata", {}).get("product_id"): _semantic_score(hit.get("distance"))
                for hit in hits
                if hit.get("metadata", {}).get("product_id")
            }
            products = _rank_products(products, query, memory, semantic_scores, keyword_scores)
            return products, {
                "retrieval_mode": "hybrid_keyword_vector_empty_candidates",
                "sqlite_candidates": 0,
                "chroma_hits": chroma_product_ids[:5],
                "keyword_hits": _keyword_hit_ids(keyword_hits),
                "keyword_top_terms": _keyword_top_terms(keyword_hits),
                "product_hits": len(products),
                "filtered_out": len(loaded_products) - len(products),
                "confidence": _retrieval_confidence(products, semantic_scores, keyword_scores),
                "low_confidence": _is_low_confidence(products, semantic_scores, keyword_scores),
                "scoring": "bm25_semantic_rules",
            }

        candidate_by_id = {product.id: product for product in candidates}

        if not _should_use_vector_rerank(candidates, memory):
            ranked = _rank_products(candidates, query, memory, {}, keyword_scores)
            return ranked, {
                "retrieval_mode": "sqlite_filter_keyword_rerank",
                "sqlite_candidates": len(candidates),
                "chroma_hits": [],
                "keyword_hits": _keyword_hit_ids(keyword_hits),
                "keyword_top_terms": _keyword_top_terms(keyword_hits),
                "confidence": _retrieval_confidence(ranked, {}, keyword_scores),
                "low_confidence": _is_low_confidence(ranked, {}, keyword_scores),
                "scoring": "bm25_rules",
            }

        try:
            hits = self.vector_search(
                db,
                query_text,
                limit=min(max(len(candidates), 10), 30),
                product_ids=list(candidate_by_id),
                ensure_indexed=True,
            )
        except Exception as exc:
            ranked = _fallback_sort(candidates, query=query, memory=memory, keyword_scores=keyword_scores)
            return ranked, {
                "retrieval_mode": "keyword_vector_search_fallback",
                "sqlite_candidates": len(candidates),
                "chroma_hits": [],
                "keyword_hits": _keyword_hit_ids(keyword_hits),
                "keyword_top_terms": _keyword_top_terms(keyword_hits),
                "confidence": _retrieval_confidence(ranked, {}, keyword_scores),
                "low_confidence": _is_low_confidence(ranked, {}, keyword_scores),
                "error": f"{type(exc).__name__}: {str(exc)[:160]}",
            }

        semantic_scores = {
            hit.get("metadata", {}).get("product_id"): _semantic_score(hit.get("distance"))
            for hit in hits
            if hit.get("metadata", {}).get("product_id") in candidate_by_id
        }

        ranked = _rank_products(candidates, query, memory, semantic_scores, keyword_scores)

        return ranked, {
            "retrieval_mode": "hybrid_keyword_vector_rerank",
            "sqlite_candidates": len(candidates),
            "chroma_hits": [
                hit.get("metadata", {}).get("product_id")
                for hit in hits[:5]
                if hit.get("metadata", {}).get("product_id")
            ],
            "keyword_hits": _keyword_hit_ids(keyword_hits),
            "keyword_top_terms": _keyword_top_terms(keyword_hits),
            "confidence": _retrieval_confidence(ranked, semantic_scores, keyword_scores),
            "low_confidence": _is_low_confidence(ranked, semantic_scores, keyword_scores),
            "scoring": "bm25_semantic_rules",
        }


# ------------------------------------------------------------------
# 内部工具
# ------------------------------------------------------------------


def _build_hybrid_query(query: str, memory: dict[str, Any] | None = None) -> str:
    if not memory:
        return query

    sub_category = memory.get("subcategory") or memory.get("sub_category") or ""
    target_user = memory.get("target_user") or memory.get("audience") or ""

    use_cases: list[str] = []
    use_cases.extend(_as_list(memory.get("use_cases")))
    use_cases.extend(_as_list(memory.get("use_case")))

    parts = [
        query,
        memory.get("category") or "",
        sub_category,
        target_user,
        " ".join(use_cases),
        " ".join(_as_list(memory.get("preferences"))),
        " ".join(_as_list(memory.get("negative_preferences"))),
    ]

    if memory.get("budget_max"):
        parts.append(f"{memory['budget_max']} 元以内")

    return " ".join(str(part) for part in parts if part).strip() or query


def _should_use_vector_rerank(candidates: list[Product], memory: dict[str, Any] | None) -> bool:
    mode = os.getenv("PRODUCT_SEARCH_VECTOR_RERANK", "auto").strip().lower()
    if mode in {"1", "true", "yes", "on", "always"}:
        return True
    if mode in {"0", "false", "no", "off", "never"}:
        return False

    memory = memory or {}
    has_structured_filter = bool(memory.get("category") or memory.get("subcategory") or memory.get("budget_max"))
    local_limit = _to_int(os.getenv("PRODUCT_SEARCH_LOCAL_RERANK_MAX")) or 40
    return not (has_structured_filter and len(candidates) <= local_limit)


def _semantic_score(distance: float | None) -> float:
    if distance is None:
        return 0.0

    return 1.0 / (1.0 + max(float(distance), 0.0))


def _keyword_scores(keyword_hits: list[dict[str, Any]]) -> dict[str, float]:
    return {
        str(hit["product_id"]): float(hit.get("score") or 0)
        for hit in keyword_hits
        if hit.get("product_id")
    }


def _keyword_hit_ids(keyword_hits: list[dict[str, Any]]) -> list[str]:
    return [str(hit["product_id"]) for hit in keyword_hits[:5] if hit.get("product_id")]


def _keyword_top_terms(keyword_hits: list[dict[str, Any]]) -> dict[str, list[str]]:
    terms: dict[str, list[str]] = {}
    for hit in keyword_hits[:5]:
        product_id = hit.get("product_id")
        if product_id:
            terms[str(product_id)] = [str(term) for term in hit.get("matched_terms", [])[:5]]
    return terms


def _retrieval_confidence(
    products: list[Product],
    semantic_scores: dict[str, float],
    keyword_scores: dict[str, float],
) -> float:
    if not products:
        return 0.0
    top = products[0]
    semantic = min(max(semantic_scores.get(top.id, 0.0), 0.0), 1.0)
    keyword = min(max(keyword_scores.get(top.id, 0.0) / 30.0, 0.0), 1.0)
    return round(max(semantic, keyword), 4)


def _is_low_confidence(
    products: list[Product],
    semantic_scores: dict[str, float],
    keyword_scores: dict[str, float],
) -> bool:
    threshold = _env_float("PRODUCT_SEARCH_MIN_CONFIDENCE", 0.25)
    if threshold <= 0:
        return False
    return _retrieval_confidence(products, semantic_scores, keyword_scores) < threshold


def _rank_products(
    products: list[Product],
    query: str,
    memory: dict[str, Any] | None,
    semantic_scores: dict[str, float] | None = None,
    keyword_scores: dict[str, float] | None = None,
) -> list[Product]:
    semantic_scores = semantic_scores or {}
    keyword_scores = keyword_scores or {}
    return sorted(
        products,
        key=lambda product: (
            -_combined_score(product, query, memory, semantic_scores, keyword_scores),
            _num(product.price) if _prefers_low_price(memory) else 0,
            -_num(product.rating),
            -_num(product.sales),
        ),
    )


def _fallback_sort(
    candidates: list[Product],
    *,
    query: str = "",
    memory: dict[str, Any] | None = None,
    keyword_scores: dict[str, float] | None = None,
) -> list[Product]:
    return _rank_products(candidates, query, memory, {}, keyword_scores or {})


def _combined_score(
    product: Product,
    query: str,
    memory: dict[str, Any] | None,
    semantic_scores: dict[str, float],
    keyword_scores: dict[str, float],
) -> float:
    keyword_score = min(keyword_scores.get(product.id, 0.0), 40.0) * 1.5
    return semantic_scores.get(product.id, 0.0) * 20 + keyword_score + _rule_score(product, query, memory)


def _rule_score(product: Product, query: str, memory: dict[str, Any] | None) -> float:
    memory = memory or {}
    text = _product_text(product)
    score = 0.0

    category = memory.get("category")
    subcategory = memory.get("subcategory")
    if category and product_matches_category(product, str(category)):
        score += 8
    if subcategory and product_matches_subcategory(product, str(subcategory)):
        score += 10

    for keyword in _query_keywords(query):
        if keyword in text:
            score += 8

    for field, weight in [("use_cases", 6), ("preferences", 5)]:
        for value in _as_list(memory.get(field)):
            if value and str(value).lower() in text:
                score += weight

    budget = _to_int(memory.get("budget_max"))
    if budget is not None:
        if product.price <= budget:
            score += 2
        else:
            score -= min((product.price - budget) / max(budget, 1), 5)

    if product.stock <= 0:
        score -= 100

    score += _num(product.rating) * 0.2
    score += min(_num(product.sales), 20000) / 20000
    return score


def _product_text(product: Product) -> str:
    return " ".join(
        [
            product.title,
            product.category,
            product.subcategory or "",
            product.brand,
            product.description,
            product.specs_json or "",
        ]
    ).lower()


def _query_keywords(query: str) -> list[str]:
    lowered = query.lower()
    return [keyword for keyword in _domain_keywords() if keyword.lower() in lowered]


def _prefers_low_price(memory: dict[str, Any] | None) -> bool:
    preferences = set(_as_list((memory or {}).get("preferences")))
    return bool({"性价比", "便宜", "省钱"} & preferences)


def _to_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _domain_keywords() -> list[str]:
    keywords: list[str] = []
    for category in load_taxonomy().get("categories", []):
        keywords.extend([category.get("name", ""), *category.get("aliases", [])])
        for subcategory in category.get("subcategories", []):
            keywords.extend([subcategory.get("name", ""), *subcategory.get("aliases", [])])
        for value_group in category.get("attributes", {}).values():
            for value, aliases in value_group.items():
                keywords.extend([value, *aliases])
    keywords.extend(str(item) for item in rule_list("guide_quality", "guide_keywords"))
    return list(dict.fromkeys(keyword for keyword in keywords if keyword))


def _load_products(db: Session, product_ids: list[str], *, in_stock_only: bool = True) -> list[Product]:
    if not product_ids:
        return []

    unique_ids = list(dict.fromkeys(product_ids))
    statement = select(Product).where(Product.id.in_(unique_ids))
    if in_stock_only:
        statement = statement.where(Product.stock > 0)
    product_map = {
        product.id: product
        for product in db.scalars(statement).all()
    }
    return [product_map[product_id] for product_id in unique_ids if product_id in product_map]


def _apply_hard_filters(products: list[Product], memory: dict[str, Any] | None) -> list[Product]:
    if not memory:
        return products

    category = memory.get("category")
    subcategory = memory.get("subcategory")
    budget_max = memory.get("budget_max")
    filtered = products

    if category:
        filtered = [product for product in filtered if product_matches_category(product, str(category))]
    if subcategory:
        filtered = [product for product in filtered if product_matches_subcategory(product, str(subcategory))]
    if budget_max is not None:
        try:
            budget = int(budget_max)
        except (TypeError, ValueError):
            budget = None
        if budget is not None:
            filtered = [product for product in filtered if product.price <= budget]

    return filtered


def _as_list(value: Any) -> list[str]:
    if not value:
        return []

    if isinstance(value, list):
        return [str(item) for item in value if item]

    return [str(value)]


def _num(value: Any) -> float:
    if value is None:
        return 0.0

    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
