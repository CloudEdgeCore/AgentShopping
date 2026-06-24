from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.guide_quality import score_product_for_guide
from app.models.tables import Product, ProductAttribute, ProductSku, ProductTag
from app.services.behavior_service import product_behavior_summary


@dataclass(frozen=True)
class CommercialScore:
    product_id: str
    total: float
    breakdown: dict[str, float]
    badges: list[str]
    risk_points: list[str]
    behavior: dict[str, Any]


def rank_products_with_commercial_factors(
    db: Session,
    products: list[Product],
    memory: dict[str, Any],
    query: str,
) -> tuple[list[Product], dict[str, CommercialScore]]:
    if not products:
        return [], {}

    product_ids = [product.id for product in products]
    signals = build_commercial_scores(db, products)
    ranked = sorted(
        products,
        key=lambda product: (
            -(score_product_for_guide(product, memory, query).total + signals[product.id].total),
            -signals[product.id].total,
            product.price if _prefers_value(memory) else 0,
            -float(product.rating or 0),
            -int(product.sales or 0),
        ),
    )
    return ranked, {product_id: signals[product_id] for product_id in product_ids if product_id in signals}


def build_commercial_scores(db: Session, products: list[Product]) -> dict[str, CommercialScore]:
    product_ids = [product.id for product in products]
    tags_by_product = _load_tags(db, product_ids)
    attrs_by_product = _load_attributes(db, product_ids)
    sku_stock_by_product = _load_sku_stock(db, product_ids)
    behavior_by_product = product_behavior_summary(db, product_ids)

    return {
        product.id: score_product_commercially(
            product,
            tags=tags_by_product.get(product.id, []),
            attributes=attrs_by_product.get(product.id, {}),
            sku_stock=sku_stock_by_product.get(product.id),
            behavior=behavior_by_product.get(product.id, {"events": {}, "score": 0.0}),
        )
        for product in products
    }


def score_product_commercially(
    product: Product,
    *,
    tags: list[ProductTag] | None = None,
    attributes: dict[str, str] | None = None,
    sku_stock: int | None = None,
    behavior: dict[str, Any] | None = None,
) -> CommercialScore:
    tags = tags or []
    attributes = attributes or {}
    behavior = behavior or {"events": {}, "score": 0.0}
    breakdown: dict[str, float] = {}
    badges: list[str] = []
    risks: list[str] = []

    stock = int(sku_stock if sku_stock is not None else product.stock or 0)
    if stock <= 0:
        _add(breakdown, "无库存", -80)
        risks.append("当前无货")
    elif stock <= 2:
        _add(breakdown, "库存偏低", -4)
        risks.append("库存偏低")
    elif stock >= 20:
        _add(breakdown, "库存充足", 8)
        badges.append("库存充足")
    else:
        _add(breakdown, "库存健康", 4)

    if product.rating >= 4.7:
        _add(breakdown, "高评分", 5)
        badges.append("评分高")
    elif product.rating >= 4.3:
        _add(breakdown, "评分稳定", 3)
    elif product.rating and product.rating < 3.8:
        _add(breakdown, "评分风险", -8)
        risks.append("评分偏低")

    if product.sales >= 5000:
        _add(breakdown, "爆品销量", 5)
        badges.append("热销")
    elif product.sales >= 1500:
        _add(breakdown, "销量稳定", 3)

    tag_values = {tag.value for tag in tags}
    tag_types = {tag.tag_type for tag in tags}
    if tag_types & {"promotion", "coupon", "campaign"} or _has_any(tag_values, ["优惠", "券", "满减", "活动", "赠品"]):
        _add(breakdown, "活动优先", 5)
        badges.append("有活动")
    if tag_types & {"new", "featured"} or _has_any(tag_values, ["新品", "主推", "精选"]):
        _add(breakdown, "运营主推", 3)
        badges.append("运营主推")
    if tag_types & {"risk", "after_sale_risk"} or _has_any(tag_values, ["退货高", "差评", "慎选"]):
        _add(breakdown, "运营风险", -8)
        risks.append("运营风险")

    margin = _attr_float(attributes, ["margin_rate", "gross_margin", "毛利率", "毛利"])
    if margin is not None:
        if margin >= 0.35:
            _add(breakdown, "毛利健康", 4)
        elif margin <= 0.08:
            _add(breakdown, "毛利偏低", -2)

    delivery_hours = _attr_float(attributes, ["delivery_hours", "发货时效", "预计发货小时"])
    shipping_text = _attr_text(attributes, ["shipping_speed", "发货", "物流", "配送"])
    if delivery_hours is not None and delivery_hours <= 48 or shipping_text and _has_any({shipping_text}, ["现货", "次日", "48小时", "24小时"]):
        _add(breakdown, "发货快", 3)
        badges.append("发货快")

    return_rate = _attr_float(attributes, ["return_rate", "退货率"])
    bad_review_rate = _attr_float(attributes, ["bad_review_rate", "差评率"])
    if return_rate is not None and return_rate >= 0.15:
        _add(breakdown, "退货率风险", -10)
        risks.append("退货率偏高")
    elif return_rate is not None and return_rate <= 0.04:
        _add(breakdown, "退货率低", 2)
    if bad_review_rate is not None and bad_review_rate >= 0.08:
        _add(breakdown, "差评率风险", -8)
        risks.append("差评率偏高")

    behavior_score = float(behavior.get("score") or 0.0)
    if behavior_score:
        _add(breakdown, "行为转化", behavior_score)
        if behavior_score >= 5:
            badges.append("转化好")
        if behavior_score <= -5:
            risks.append("近期负反馈偏多")

    total = round(sum(breakdown.values()), 4)
    return CommercialScore(
        product_id=product.id,
        total=total,
        breakdown={key: round(value, 4) for key, value in breakdown.items()},
        badges=list(dict.fromkeys(badges))[:4],
        risk_points=list(dict.fromkeys(risks))[:4],
        behavior=behavior,
    )


def _load_tags(db: Session, product_ids: list[str]) -> dict[str, list[ProductTag]]:
    rows = list(db.scalars(select(ProductTag).where(ProductTag.product_id.in_(product_ids))).all()) if product_ids else []
    result: dict[str, list[ProductTag]] = {}
    for row in rows:
        result.setdefault(row.product_id, []).append(row)
    return result


def _load_attributes(db: Session, product_ids: list[str]) -> dict[str, dict[str, str]]:
    rows = list(db.scalars(select(ProductAttribute).where(ProductAttribute.product_id.in_(product_ids))).all()) if product_ids else []
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        result.setdefault(row.product_id, {})[row.name] = row.value
    return result


def _load_sku_stock(db: Session, product_ids: list[str]) -> dict[str, int]:
    rows = list(db.scalars(select(ProductSku).where(ProductSku.product_id.in_(product_ids))).all()) if product_ids else []
    result: dict[str, int] = {}
    for row in rows:
        result[row.product_id] = result.get(row.product_id, 0) + max(int(row.stock or 0), 0)
    return result


def _attr_float(attributes: dict[str, str], names: list[str]) -> float | None:
    for name in names:
        if name not in attributes:
            continue
        text = str(attributes[name]).strip().replace("%", "")
        try:
            value = float(text)
        except ValueError:
            continue
        return value / 100 if value > 1 else value
    return None


def _attr_text(attributes: dict[str, str], names: list[str]) -> str:
    for name in names:
        if name in attributes:
            return str(attributes[name])
    return ""


def _has_any(values: set[str], keywords: list[str]) -> bool:
    text = " ".join(values).lower()
    return any(keyword.lower() in text for keyword in keywords)


def _prefers_value(memory: dict[str, Any]) -> bool:
    preferences = {str(item) for item in memory.get("preferences", [])}
    return bool(preferences & {"性价比", "便宜", "省钱"})


def _add(breakdown: dict[str, float], key: str, value: float) -> None:
    breakdown[key] = breakdown.get(key, 0.0) + float(value)
