import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.models.tables import Product


TAXONOMY_PATH = Path(__file__).resolve().parents[1] / "data" / "taxonomy.json"
STRICT_FILTER_KEYWORDS = [
    "有哪些",
    "哪些",
    "有什么",
    "有哪几款",
    "列出",
    "清单",
    "不能超",
    "别超",
    "不超",
    "不要超",
    "绝对不能超",
    "卡死",
    "必须以内",
]


@dataclass
class TaxonomyConstraints:
    category: str | None
    subcategory: str | None
    use_cases: list[str]
    preferences: list[str]
    strict_filter: bool


@lru_cache
def load_taxonomy() -> dict[str, Any]:
    with TAXONOMY_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def extract_taxonomy_constraints(text: str, *, budget: int | None = None) -> TaxonomyConstraints:
    category, subcategory = match_subcategory(text)
    category = category or match_category(text)
    use_cases = extract_taxonomy_values(text, value_type="use_cases")
    preferences = extract_taxonomy_values(text, value_type="preferences")
    if budget is not None and "性价比" not in preferences:
        preferences.append("性价比")
    return TaxonomyConstraints(
        category=category,
        subcategory=subcategory,
        use_cases=use_cases,
        preferences=preferences,
        strict_filter=is_strict_filter_query(text, budget=budget),
    )


def match_category(text: str) -> str | None:
    lowered = text.lower()
    best: tuple[int, str] | None = None
    for category in load_taxonomy().get("categories", []):
        for alias in [category["name"], *category.get("aliases", [])]:
            normalized = alias.lower()
            if normalized in lowered:
                candidate = (len(normalized), category["name"])
                if best is None or candidate[0] > best[0]:
                    best = candidate
    return best[1] if best else None


def match_subcategory(text: str) -> tuple[str | None, str | None]:
    lowered = text.lower()
    best: tuple[int, str, str] | None = None
    for category in load_taxonomy().get("categories", []):
        for subcategory in category.get("subcategories", []):
            for alias in [subcategory["name"], *subcategory.get("aliases", [])]:
                normalized = alias.lower()
                if normalized in lowered:
                    candidate = (len(normalized), category["name"], subcategory["name"])
                    if best is None or candidate[0] > best[0]:
                        best = candidate
    if best is None:
        return None, None
    return best[1], best[2]


def extract_taxonomy_values(text: str, *, value_type: str) -> list[str]:
    lowered = text.lower()
    values: list[str] = []
    for category in load_taxonomy().get("categories", []):
        attributes = category.get("attributes", {}).get(value_type, {})
        for value, aliases in attributes.items():
            if any(alias.lower() in lowered for alias in aliases):
                values.append(value)
    return list(dict.fromkeys(values))


def is_strict_filter_query(text: str, *, budget: int | None = None) -> bool:
    if budget is None:
        return False
    lowered = text.lower()
    return any(keyword in lowered for keyword in STRICT_FILTER_KEYWORDS)


def product_matches_subcategory(product: Product, subcategory: str) -> bool:
    if getattr(product, "subcategory", "") == subcategory:
        return True
    if product.category == subcategory:
        return True
    inferred = infer_product_subcategory(product)
    if inferred:
        return inferred == subcategory
    aliases = get_subcategory_aliases(subcategory)
    haystack = _product_identity_text(product)
    return any(alias.lower() in haystack for alias in aliases)


def product_matches_category(product: Product, category_name: str) -> bool:
    category = _find_category(category_name)
    if category is None:
        haystack = _product_search_text(product)
        return category_name.lower() in haystack

    if product.category == category["name"]:
        return True

    if getattr(product, "subcategory", ""):
        return any(
            getattr(product, "subcategory", "").lower() == alias.lower()
            for subcategory in category.get("subcategories", [])
            for alias in [subcategory["name"], *subcategory.get("aliases", [])]
        )

    product_category = (product.category or "").lower()
    for subcategory in category.get("subcategories", []):
        aliases = [subcategory["name"], *subcategory.get("aliases", [])]
        if any(product_category == alias.lower() for alias in aliases):
            return True

    haystack = _product_search_text(product)
    category_aliases = [category["name"], *category.get("aliases", [])]
    return any(alias.lower() in haystack for alias in category_aliases)


def infer_product_subcategory(product: Product) -> str | None:
    existing = getattr(product, "subcategory", "")
    if existing:
        normalized = normalize_product_taxonomy(product.category, existing)[1]
        return normalized or existing

    haystack = _product_search_text(product)
    best: tuple[int, str] | None = None
    for category in load_taxonomy().get("categories", []):
        if _is_other_top_level_category(product.category, category["name"]):
            continue
        for subcategory in category.get("subcategories", []):
            for alias in [subcategory["name"], *subcategory.get("aliases", [])]:
                normalized = alias.lower()
                if normalized in haystack:
                    candidate = (len(normalized), subcategory["name"])
                    if best is None or candidate[0] > best[0]:
                        best = candidate
    return best[1] if best else None


def get_subcategory_aliases(subcategory_name: str) -> list[str]:
    for category in load_taxonomy().get("categories", []):
        for subcategory in category.get("subcategories", []):
            if subcategory["name"] == subcategory_name:
                return [subcategory["name"], *subcategory.get("aliases", [])]
    return [subcategory_name]


def normalize_product_taxonomy(
    category: str,
    subcategory: str = "",
    *,
    title: str = "",
    brand: str = "",
) -> tuple[str, str]:
    subcategory_match = _match_subcategory_alias(subcategory, exact=True)
    category_as_subcategory = _match_subcategory_alias(category, exact=True)
    text_match = _match_subcategory_alias(" ".join([title, brand, category, subcategory]), exact=False)
    top_category = _match_category_alias(category)

    matched = subcategory_match or category_as_subcategory or text_match
    if matched:
        return matched[0], matched[1]
    if top_category:
        return top_category, subcategory.strip()
    return category.strip(), subcategory.strip()


def _product_identity_text(product: Product) -> str:
    return " ".join([product.title, product.brand, getattr(product, "subcategory", "") or ""]).lower()


def _product_search_text(product: Product) -> str:
    return " ".join(
        [product.title, product.brand, product.category or "", getattr(product, "subcategory", "") or ""]
    ).lower()


def _find_category(category_name: str) -> dict[str, Any] | None:
    for category in load_taxonomy().get("categories", []):
        if category["name"] == category_name:
            return category
    return None


def _match_category_alias(value: str) -> str | None:
    normalized_value = value.strip().lower()
    if not normalized_value:
        return None
    for category in load_taxonomy().get("categories", []):
        aliases = [category["name"], *category.get("aliases", [])]
        if any(normalized_value == alias.lower() for alias in aliases):
            return category["name"]
    return None


def _match_subcategory_alias(value: str, *, exact: bool) -> tuple[str, str] | None:
    normalized_value = value.strip().lower()
    if not normalized_value:
        return None

    best: tuple[int, str, str] | None = None
    for category in load_taxonomy().get("categories", []):
        for subcategory in category.get("subcategories", []):
            for alias in [subcategory["name"], *subcategory.get("aliases", [])]:
                normalized_alias = alias.lower()
                matched = normalized_value == normalized_alias if exact else normalized_alias in normalized_value
                if matched and (best is None or len(normalized_alias) > best[0]):
                    best = (len(normalized_alias), category["name"], subcategory["name"])
    return (best[1], best[2]) if best else None


def _is_other_top_level_category(product_category: str | None, current_category: str) -> bool:
    if not product_category:
        return False
    top_level_categories = {category["name"] for category in load_taxonomy().get("categories", [])}
    return product_category in top_level_categories and product_category != current_category
