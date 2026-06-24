from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.agents.category_sop import build_category_sop_context
from app.models.tables import Product


# ─── 需求诊断 ───

@dataclass
class GuideDiagnosis:
    ready: bool
    action: str
    missing_fields: list[str]
    trace: dict[str, Any]


def diagnose_guide_demand(query: str, memory: dict, *, has_image: bool = False) -> GuideDiagnosis:
    """判断用户需求是否足够给出推荐，还是需要追问。"""
    missing: list[str] = []
    if not memory.get("category") and not has_image:
        missing.append("category")
    trace = {"query": query, "has_image": has_image, "has_category": bool(memory.get("category"))}
    if missing:
        return GuideDiagnosis(ready=False, action="clarify", missing_fields=missing, trace=trace)
    return GuideDiagnosis(ready=True, action="proceed", missing_fields=[], trace=trace)


# ─── 追问话术 ───

def build_clarification_answer(diagnosis: GuideDiagnosis) -> str:
    """根据缺失字段生成追问回复。"""
    if "category" in diagnosis.missing_fields:
        return "你想找哪类商品呢？比如手机、耳机、护肤品，告诉我品类我好帮你筛。"
    return "能再补充一下你的具体需求吗？比如预算、品牌偏好或使用场景。"


# ─── 推荐话术 ───

def build_guide_answer(
    cards: list[dict],
    memory: dict,
    *,
    no_exact_match: bool = False,
    strict_no_match: bool = False,
    visual_search_mode: bool = False,
) -> str:
    """基于商品卡片生成推荐话术（模板版，LLM 版由 generation.py 覆盖）。"""
    if not cards:
        return "暂时没有找到合适的商品，你可以换个关键词或放宽条件试试。"
    lines = []
    category = memory.get("subcategory") or memory.get("category") or ""
    if strict_no_match:
        lines.append(f"在 {category} 下没有完全匹配你条件的商品，以下几款可以参考：")
    elif no_exact_match:
        lines.append(f"没有严格符合预算的 {category}，以下是同品类备选：")
    for card in cards[:3]:
        title = card.get("title", "")
        price = card.get("price", 0)
        reasons = card.get("reasons", [])
        reason_text = "，".join(reasons[:2]) if reasons else ""
        line = f"• {title}（¥{price}）"
        if reason_text:
            line += f"——{reason_text}"
        lines.append(line)
    return "\n".join(lines)


# ─── 商品卡片构建 ───

def build_product_card(product: Product, memory: dict, rank: int, *, query: str = "") -> dict:
    """将 Product ORM 对象转为前端可用的商品卡片 dict。"""
    specs = {}
    if product.specs_json:
        import json
        try:
            specs = json.loads(product.specs_json)
        except (json.JSONDecodeError, TypeError):
            specs = {}
    return {
        "product_id": product.id,
        "title": product.title,
        "category": product.category,
        "subcategory": product.subcategory or "",
        "brand": product.brand,
        "price": product.price,
        "image_url": product.image_url or "",
        "rating": product.rating,
        "sales": product.sales,
        "stock": product.stock,
        "rank": rank,
        "reasons": _build_reasons(product, memory),
        "selling_points": _extract_selling_points(product),
        "tradeoffs": [],
    }


def _build_reasons(product: Product, memory: dict) -> list[str]:
    reasons: list[str] = []
    if memory.get("category") and product.category == memory["category"]:
        reasons.append("品类匹配")
    if memory.get("subcategory") and product.subcategory == memory.get("subcategory"):
        reasons.append("子品类匹配")
    if memory.get("budget_max") and product.price <= memory["budget_max"]:
        reasons.append("预算内")
    if product.rating >= 4.0:
        reasons.append("高评分")
    return reasons[:4]


def _extract_selling_points(product: Product) -> list[str]:
    points: list[str] = []
    if product.rating >= 4.5:
        points.append("口碑极佳")
    elif product.rating >= 4.0:
        points.append("好评较多")
    if product.sales >= 5000:
        points.append("热销款")
    return points[:3]


# ─── 排序和评分 ───

@dataclass
class ProductScore:
    total: float
    category_score: float
    keyword_score: float
    preference_score: float
    budget_score: float
    quality_score: float


def score_product_for_guide(
    product: Product,
    memory: dict,
    query: str,
    *,
    semantic_score: float = 0.0,
) -> ProductScore:
    """为商品打综合分，用于排序。"""
    text = " ".join([
        product.title,
        product.category,
        product.subcategory or "",
        product.brand,
        product.description or "",
    ]).lower()

    category_score = 0.0
    if memory.get("category") and product.category == memory["category"]:
        category_score = 8.0
    if memory.get("subcategory") and product.subcategory == memory.get("subcategory"):
        category_score += 4.0

    keyword_score = 0.0
    for keyword in _query_keywords_from_text(query):
        if keyword in text:
            keyword_score += 12.0 if len(keyword) >= 2 else 2.0

    preference_score = 0.0
    for use_case in memory.get("use_cases", []):
        if use_case.lower() in text:
            preference_score += 8.0
    for preference in memory.get("preferences", []):
        if preference.lower() in text:
            preference_score += 6.0

    budget_score = 0.0
    if memory.get("budget_max") and product.price <= memory["budget_max"]:
        budget_score = 2.0

    quality_score = product.rating * 0.2 + min(product.sales, 20000) / 20000

    total = category_score + keyword_score + preference_score + budget_score + quality_score + semantic_score * 10
    return ProductScore(
        total=round(total, 2),
        category_score=category_score,
        keyword_score=keyword_score,
        preference_score=preference_score,
        budget_score=budget_score,
        quality_score=quality_score,
    )


def rank_products_for_guide(products: list[Product], memory: dict, query: str = "") -> list[Product]:
    """按综合分排序商品列表。"""
    return sorted(
        products,
        key=lambda p: score_product_for_guide(p, memory, query).total,
        reverse=True,
    )


def guide_answer_policy(memory: dict) -> str:
    """根据类目 SOP 生成回答策略提示。"""
    category = memory.get("category") or ""
    subcategory = memory.get("subcategory") or ""
    if not category:
        return ""
    return f"当前用户关注 {category}/{subcategory}，回答时优先突出该品类的核心选购要点。"


def _query_keywords_from_text(query: str) -> list[str]:
    """从查询中提取关键词（简化版）。"""
    # 去掉常见停用词，保留有意义的词
    stop_words = {"的", "了", "吗", "吧", "呢", "啊", "是", "在", "有", "和", "与", "或", "帮", "我", "你", "想", "要", "找", "推荐", "一款", "一个"}
    words = []
    for char_group in query.replace("，", " ").replace("。", " ").replace("、", " ").split():
        if len(char_group) >= 2 and char_group not in stop_words:
            words.append(char_group.lower())
    return words


def _quality_flags(cards: list[dict], retrieval_trace: dict, category_sop: dict) -> list[str]:
    flags: list[str] = []
    if retrieval_trace.get("low_confidence"):
        flags.append("low_confidence_retrieval")
    if not cards:
        flags.append("no_candidate_cards")
    if category_sop["missing_slots"]:
        flags.append("missing_key_slots")
    if cards and not _has_non_basic_evidence(cards):
        flags.append("thin_product_evidence")
    return flags


def _needs_clarification(category_sop: dict, quality_flags: list[str]) -> bool:
    if "no_candidate_cards" in quality_flags and category_sop["missing_slots"]:
        return True
    return "low_confidence_retrieval" in quality_flags and len(category_sop["missing_slots"]) >= 2


def _evidence_score(cards: list[dict], retrieval_trace: dict) -> float:
    if not cards:
        return 0.0
    score = 0.35
    if _has_non_basic_evidence(cards):
        score += 0.3
    if any(card.get("review_insight") for card in cards):
        score += 0.15
    if not retrieval_trace.get("low_confidence"):
        score += 0.2
    return round(min(score, 1.0), 2)


def _has_non_basic_evidence(cards: list[dict]) -> bool:
    for card in cards:
        for item in card.get("evidence", []):
            source = str(item.get("source", ""))
            if source and source != "价格/销量/评分":
                return True
    return False
