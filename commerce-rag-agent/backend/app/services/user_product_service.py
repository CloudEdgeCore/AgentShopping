import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tables import Product, UserProductCollection


VALID_LIST_TYPES = {"favorite", "compare", "recent"}


def add_product_to_list(
    db: Session,
    *,
    user_id: str,
    product_id: str,
    list_type: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    list_type = _validate_list_type(list_type)
    product = _require_product(db, product_id)
    row = _get_collection_row(db, user_id=user_id, product_id=product_id, list_type=list_type)
    now = _now()
    if row is None:
        row = UserProductCollection(
            id=f"upc_{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            product_id=product_id,
            list_type=list_type,
            view_count=1 if list_type == "recent" else 0,
            metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
            created_at=now,
            updated_at=now,
        )
        db.add(row)
    else:
        if list_type == "recent":
            row.view_count = int(row.view_count or 0) + 1
        if metadata:
            row.metadata_json = json.dumps(metadata, ensure_ascii=False)
        row.updated_at = now
    db.commit()
    db.refresh(row)
    return _collection_payload(row, product)


def remove_product_from_list(db: Session, *, user_id: str, product_id: str, list_type: str) -> dict[str, Any]:
    list_type = _validate_list_type(list_type)
    row = _get_collection_row(db, user_id=user_id, product_id=product_id, list_type=list_type)
    if row is not None:
        db.delete(row)
        db.commit()
    return {"product_id": product_id, "list_type": list_type, "active": False}


def list_user_products(
    db: Session,
    *,
    user_id: str,
    list_type: str,
    limit: int = 20,
) -> list[dict[str, Any]]:
    list_type = _validate_list_type(list_type)
    rows = list(
        db.scalars(
            select(UserProductCollection)
            .where(UserProductCollection.user_id == user_id)
            .where(UserProductCollection.list_type == list_type)
            .order_by(UserProductCollection.updated_at.desc())
            .limit(max(min(limit, 100), 1))
        ).all()
    )
    products = _load_products(db, [row.product_id for row in rows])
    return [_collection_payload(row, products[row.product_id]) for row in rows if row.product_id in products]


def product_collection_state(db: Session, *, user_id: str, product_ids: list[str]) -> dict[str, Any]:
    ids = [item for item in list(dict.fromkeys(str(product_id) for product_id in product_ids)) if item]
    if not ids:
        return {"products": {}}
    rows = list(
        db.scalars(
            select(UserProductCollection)
            .where(UserProductCollection.user_id == user_id)
            .where(UserProductCollection.product_id.in_(ids))
        ).all()
    )
    state: dict[str, dict[str, Any]] = {
        product_id: {"favorite": False, "compare": False, "recent": False, "view_count": 0}
        for product_id in ids
    }
    for row in rows:
        item = state.setdefault(
            row.product_id,
            {"favorite": False, "compare": False, "recent": False, "view_count": 0},
        )
        item[row.list_type] = True
        if row.list_type == "recent":
            item["view_count"] = row.view_count
            item["last_viewed_at"] = row.updated_at.isoformat()
    return {"products": state}


def collection_counts(db: Session, *, user_id: str) -> dict[str, int]:
    return {
        list_type: len(list_user_products(db, user_id=user_id, list_type=list_type, limit=100))
        for list_type in sorted(VALID_LIST_TYPES)
    }


def _collection_payload(row: UserProductCollection, product: Product) -> dict[str, Any]:
    return {
        "id": row.id,
        "user_id": row.user_id,
        "list_type": row.list_type,
        "view_count": row.view_count,
        "metadata": _safe_json_dict(row.metadata_json),
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
        "product": _product_payload(product),
    }


def _product_payload(product: Product) -> dict[str, Any]:
    return {
        "product_id": product.id,
        "title": product.title,
        "category": product.category,
        "subcategory": product.subcategory or "",
        "brand": product.brand,
        "price": product.price,
        "rating": product.rating,
        "sales": product.sales,
        "stock": product.stock,
        "image_url": product.image_url,
    }


def _validate_list_type(list_type: str) -> str:
    value = str(list_type or "").strip().lower()
    if value not in VALID_LIST_TYPES:
        raise ValueError(f"Unsupported list_type: {list_type}")
    return value


def _get_collection_row(
    db: Session,
    *,
    user_id: str,
    product_id: str,
    list_type: str,
) -> UserProductCollection | None:
    return db.scalar(
        select(UserProductCollection)
        .where(UserProductCollection.user_id == user_id)
        .where(UserProductCollection.product_id == product_id)
        .where(UserProductCollection.list_type == list_type)
    )


def _require_product(db: Session, product_id: str) -> Product:
    product = db.get(Product, product_id)
    if not product:
        raise ValueError("Product not found")
    return product


def _load_products(db: Session, product_ids: list[str]) -> dict[str, Product]:
    ids = [item for item in list(dict.fromkeys(product_ids)) if item]
    if not ids:
        return {}
    return {product.id: product for product in db.scalars(select(Product).where(Product.id.in_(ids))).all()}


def _safe_json_dict(raw: str | None) -> dict[str, Any]:
    try:
        parsed = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)
