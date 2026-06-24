import re
from typing import Any, Literal

from app.services.taxonomy import load_taxonomy


TaxonomyMode = Literal["soft", "hard"]


def rerank_image_candidates(
    candidates: list[dict],
    *,
    text_query: str = "",
    budget_max: int | None = None,
    category: str | None = None,
    subcategory: str | None = None,
    alternative_categories: list[str] | None = None,
    alternative_subcategories: list[str] | None = None,
    visual_terms: list[str] | None = None,
    taxonomy_mode: TaxonomyMode = "soft",
    taxonomy_weight: float | None = None,
) -> list[dict]:
    eligible = [
        item
        for item in candidates
        if _candidate_passes_filters(
            item,
            budget_max=budget_max,
            category=category,
            subcategory=subcategory,
            taxonomy_mode=taxonomy_mode,
        )
    ]
    ranked = []
    max_sales = max((_as_float(item.get("metadata", {}).get("sales"), 0.0) for item in eligible), default=1.0) or 1.0
    resolved_taxonomy_weight = _taxonomy_weight(
        category=category,
        subcategory=subcategory,
        taxonomy_mode=taxonomy_mode,
        override=taxonomy_weight,
    )

    for item in eligible:
        metadata = item.get("metadata", {})
        price = _as_float(metadata.get("price"), 0.0)
        stock = _as_float(metadata.get("stock"), 0.0)
        image_similarity = _bounded_score(item.get("image_similarity"))
        text_image_similarity = _bounded_score(_text_image_similarity(item))
        lexical_text_score = _text_similarity(text_query, item)
        taxonomy_score = _taxonomy_score(
            metadata,
            text_query,
            category=category,
            subcategory=subcategory,
            alternative_categories=alternative_categories,
            alternative_subcategories=alternative_subcategories,
        )
        visual_score = _visual_terms_score(item, visual_terms or [])
        budget_score = _budget_score(price, budget_max)
        rating_score = min(_as_float(metadata.get("rating"), 0.0) / 5.0, 1.0)
        sales_score = min(_as_float(metadata.get("sales"), 0.0) / max_sales, 1.0)
        stock_score = min(stock / 100.0, 1.0)
        consensus_score = _source_consensus_score(item)

        final_score = (
            image_similarity * 0.32
            + text_image_similarity * 0.18
            + lexical_text_score * 0.08
            + taxonomy_score * resolved_taxonomy_weight
            + visual_score * 0.09
            + budget_score * 0.06
            + rating_score * 0.04
            + sales_score * 0.04
            + stock_score * 0.04
            + consensus_score * 0.05
        )
        if taxonomy_mode == "soft":
            final_score -= _taxonomy_mismatch_penalty(
                metadata,
                category=category,
                subcategory=subcategory,
            ) * resolved_taxonomy_weight * 0.35
        final_score = max(0.0, final_score)

        ranked.append(
            {
                **item,
                "product_id": metadata["product_id"],
                "text_image_similarity": round(text_image_similarity, 6),
                "final_score": round(final_score, 4),
                "score_breakdown": {
                    "image_similarity": round(image_similarity, 4),
                    "text_image_similarity": round(text_image_similarity, 4),
                    "lexical_text": round(lexical_text_score, 4),
                    "taxonomy": round(taxonomy_score, 4),
                    "visual_terms": round(visual_score, 4),
                    "budget": round(budget_score, 4),
                    "rating": round(rating_score, 4),
                    "sales": round(sales_score, 4),
                    "stock": round(stock_score, 4),
                    "source_consensus": round(consensus_score, 4),
                },
                "matched_filters": {
                    "taxonomy_mode": taxonomy_mode,
                    "category": bool(category and _metadata_matches_category(metadata, category)),
                    "subcategory": bool(subcategory and _metadata_matches_subcategory(metadata, subcategory)),
                    "budget": budget_max is not None and price <= budget_max,
                    "in_stock": stock > 0,
                    "visual_terms": round(visual_score, 4),
                },
            }
        )
    return sorted(ranked, key=lambda item: item["final_score"], reverse=True)


def _candidate_passes_filters(
    item: dict,
    *,
    budget_max: int | None,
    category: str | None,
    subcategory: str | None,
    taxonomy_mode: TaxonomyMode,
) -> bool:
    metadata = item.get("metadata") or {}
    price = _as_float(metadata.get("price"), 0.0)
    stock = _as_float(metadata.get("stock"), 0.0)
    if stock <= 0:
        return False
    if taxonomy_mode == "hard":
        if category and not _metadata_matches_category(metadata, category):
            return False
        if subcategory and not _metadata_matches_subcategory(metadata, subcategory):
            return False
    if budget_max is not None and price > budget_max:
        return False
    return bool(metadata.get("product_id"))


def _text_image_similarity(item: dict) -> float:
    source_scores = item.get("source_scores") if isinstance(item.get("source_scores"), dict) else {}
    return max(
        _as_float(item.get("text_image_similarity"), 0.0),
        _as_float(source_scores.get("vision_text"), 0.0),
        _as_float(source_scores.get("text_image"), 0.0),
    )


def _source_consensus_score(item: dict) -> float:
    sources = item.get("retrieval_sources") or []
    if not isinstance(sources, list):
        return 0.0
    if "image_vector" in sources and ("vision_text" in sources or "text_image" in sources):
        return 1.0
    if len(sources) >= 2:
        return 0.7
    return 0.25 if sources else 0.0


def _text_similarity(text_query: str, item: dict) -> float:
    if not text_query:
        return 0.0
    haystack = _candidate_text(item)
    keywords = _query_keywords(text_query)
    keyword_hits = sum(_term_match_score(keyword, haystack) for keyword in keywords)
    keyword_score = keyword_hits / max(len(keywords), 1)
    char_hits = sum(1 for char in set(text_query) if char.strip() and char in haystack)
    char_score = char_hits / max(len(set(text_query)), 1)
    return min(keyword_score * 0.75 + char_score * 0.25, 1.0)


def _candidate_text(item: dict) -> str:
    metadata = item.get("metadata", {})
    return " ".join(
        str(value)
        for value in [
            item.get("text", ""),
            metadata.get("category", ""),
            metadata.get("subcategory", ""),
            metadata.get("brand", ""),
            metadata.get("title", ""),
            metadata.get("description", ""),
            metadata.get("specs_json", ""),
            metadata.get("tags", ""),
            metadata.get("attributes", ""),
            metadata.get("image_url", ""),
            metadata.get("local_path", ""),
        ]
        if value is not None
    ).lower()


def _taxonomy_score(
    metadata: dict,
    text_query: str,
    *,
    category: str | None,
    subcategory: str | None,
    alternative_categories: list[str] | None,
    alternative_subcategories: list[str] | None,
) -> float:
    score = 0.0
    if category:
        score += 0.38 if _metadata_matches_category(metadata, category) else 0.0
    if subcategory:
        score += 0.52 if _metadata_matches_subcategory(metadata, subcategory) else 0.0
    for alt_category in alternative_categories or []:
        if _metadata_matches_category(metadata, alt_category):
            score += 0.18
            break
    for alt_subcategory in alternative_subcategories or []:
        if _metadata_matches_subcategory(metadata, alt_subcategory):
            score += 0.24
            break
    if category or subcategory or alternative_categories or alternative_subcategories:
        return min(score, 1.0)
    return min(_text_similarity(text_query, {"text": "", "metadata": metadata}), 1.0)


def _taxonomy_mismatch_penalty(
    metadata: dict,
    *,
    category: str | None,
    subcategory: str | None,
) -> float:
    if subcategory and not _metadata_matches_subcategory(metadata, subcategory):
        return 1.0
    if category and not _metadata_matches_category(metadata, category):
        return 0.7
    return 0.0


def _visual_terms_score(item: dict, visual_terms: list[str]) -> float:
    if not visual_terms:
        return 0.0
    haystack = _candidate_text(item)
    scores = [_term_match_score(term, haystack) for term in visual_terms if str(term).strip()]
    if not scores:
        return 0.0
    return min((max(scores) * 0.55) + (sum(scores) / len(scores)) * 0.45, 1.0)


def _term_match_score(term: str, haystack: str) -> float:
    normalized = str(term or "").strip().lower()
    if not normalized:
        return 0.0
    if normalized in haystack:
        return 1.0

    parts = [part for part in re.split(r"[\s,，、/;；|]+", normalized) if part]
    if parts and any(part in haystack for part in parts if len(part) >= 2):
        return 0.8

    meaningful_chars = {char for char in normalized if "\u4e00" <= char <= "\u9fff"}
    if len(meaningful_chars) >= 2:
        overlap = sum(1 for char in meaningful_chars if char in haystack) / len(meaningful_chars)
        if overlap >= 0.67:
            return 0.55
        if overlap >= 0.45:
            return 0.32
    return 0.0


def _metadata_matches_category(metadata: dict, category: str) -> bool:
    expected = str(category or "").strip()
    actual = str(metadata.get("category") or "").strip()
    if not expected:
        return True
    return actual == expected


def _metadata_matches_subcategory(metadata: dict, subcategory: str) -> bool:
    expected = str(subcategory or "").strip()
    actual = str(metadata.get("subcategory") or "").strip()
    if not expected:
        return True
    return actual == expected


def _budget_score(price: float, budget_max: int | None) -> float:
    if budget_max is None or budget_max <= 0:
        return 0.5
    if price <= 0:
        return 0.0
    if price > budget_max:
        return 0.0
    return max(0.0, 1.0 - (price / budget_max) * 0.5)


def _taxonomy_weight(
    *,
    category: str | None,
    subcategory: str | None,
    taxonomy_mode: TaxonomyMode,
    override: float | None,
) -> float:
    if override is not None:
        return max(0.0, min(float(override), 0.32))
    if taxonomy_mode == "hard":
        return 0.22
    if subcategory:
        return 0.18
    if category:
        return 0.14
    return 0.08


def _query_keywords(text_query: str) -> list[str]:
    lowered = text_query.lower()
    keywords: list[str] = []
    for category in load_taxonomy().get("categories", []):
        for alias in [category["name"], *category.get("aliases", [])]:
            if alias.lower() in lowered:
                keywords.append(alias)
        for subcategory in category.get("subcategories", []):
            for alias in [subcategory["name"], *subcategory.get("aliases", [])]:
                if alias.lower() in lowered:
                    keywords.append(alias)
        for group in category.get("attributes", {}).values():
            for value, aliases in group.items():
                if value.lower() in lowered or any(alias.lower() in lowered for alias in aliases):
                    keywords.append(value)
                    keywords.extend(aliases[:2])

    ascii_terms = re.findall(r"[a-zA-Z0-9][a-zA-Z0-9+\-.]{1,}", text_query)
    keywords.extend(ascii_terms)
    return list(dict.fromkeys(str(keyword).strip() for keyword in keywords if str(keyword).strip()))


def _as_float(value: object, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _bounded_score(value: object) -> float:
    return max(0.0, min(_as_float(value, 0.0), 1.0))
