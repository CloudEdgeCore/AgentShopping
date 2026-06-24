import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tables import Product, ProductAttribute, ProductSku, ProductTag
from app.services.product_service import get_product_knowledge_docs


def build_product_intelligence(db: Session, product_id: str) -> dict[str, Any]:
    product = db.get(Product, product_id)
    if not product:
        return {}
    skus = list(db.scalars(select(ProductSku).where(ProductSku.product_id == product.id)).all())
    attributes = list(db.scalars(select(ProductAttribute).where(ProductAttribute.product_id == product.id)).all())
    tags = list(db.scalars(select(ProductTag).where(ProductTag.product_id == product.id)).all())
    docs = get_product_knowledge_docs(db, product.id, limit=16)
    sku_prices = [sku.price for sku in skus] or [product.price]
    sku_stock = sum(max(sku.stock, 0) for sku in skus) if skus else max(product.stock, 0)
    return {
        "product": {
            "id": product.id,
            "title": product.title,
            "category": product.category,
            "subcategory": product.subcategory or "",
            "brand": product.brand,
            "description": product.description,
            "image_url": product.image_url,
        },
        "commerce": {
            "price": product.price,
            "min_sku_price": min(sku_prices),
            "max_sku_price": max(sku_prices),
            "rating": product.rating,
            "sales": product.sales,
            "stock": product.stock,
            "effective_stock": sku_stock,
            "stock_status": "in_stock" if sku_stock > 0 else "out_of_stock",
        },
        "specs": _safe_json_dict(product.specs_json),
        "skus": [
            {
                "id": sku.id,
                "sku_name": sku.sku_name,
                "price": sku.price,
                "stock": sku.stock,
                "specs": _safe_json_dict(sku.specs_json),
                "image_url": sku.image_url,
            }
            for sku in skus
        ],
        "attributes": [{"name": attr.name, "value": attr.value} for attr in attributes],
        "tags": [{"type": tag.tag_type, "value": tag.value} for tag in tags],
        "knowledge": {
            "doc_count": len(docs),
            "review_doc_count": sum(1 for doc in docs if "用户评价" in str(doc.get("text") or "")),
            "faq_doc_count": sum(1 for doc in docs if "FAQ" in str(doc.get("text") or "")),
            "sample_docs": docs[:3],
        },
    }


def _safe_json_dict(raw: str | None) -> dict[str, Any]:
    try:
        value = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}
