from datetime import UTC, datetime
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tables import PriceAlert, Product


class PriceAlertError(ValueError):
    pass


def create_price_alert(
    db: Session,
    *,
    user_id: str,
    product_id: str,
    target_price: int,
    alert_type: str = "price_drop",
) -> dict[str, Any]:
    product = db.get(Product, product_id)
    if not product:
        raise PriceAlertError("没有找到对应商品，不能创建提醒。")
    if target_price <= 0:
        raise PriceAlertError("目标价格必须大于 0。")

    existing = db.scalar(
        select(PriceAlert)
        .where(PriceAlert.user_id == user_id)
        .where(PriceAlert.product_id == product_id)
        .where(PriceAlert.alert_type == alert_type)
        .where(PriceAlert.status == "active")
    )
    if existing:
        existing.target_price = target_price
        existing.current_price_snapshot = product.price
        existing.updated_at = datetime.now(UTC)
        alert = existing
    else:
        alert = PriceAlert(
            id=f"pa_{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            product_id=product.id,
            target_price=target_price,
            current_price_snapshot=product.price,
            alert_type=alert_type,
            status="active",
        )
        db.add(alert)
    if alert_type == "price_drop" and product.price <= target_price:
        alert.status = "triggered"
        alert.triggered_at = datetime.now(UTC)
    if alert_type == "stock_restock" and product.stock > 0:
        alert.status = "triggered"
        alert.triggered_at = datetime.now(UTC)
    db.commit()
    db.refresh(alert)
    return price_alert_payload(db, alert)


def list_price_alerts(
    db: Session,
    *,
    user_id: str,
    status: str | None = None,
) -> list[dict[str, Any]]:
    statement = select(PriceAlert).where(PriceAlert.user_id == user_id).order_by(PriceAlert.created_at.desc())
    if status:
        statement = statement.where(PriceAlert.status == status)
    return [price_alert_payload(db, alert) for alert in db.scalars(statement).all()]


def evaluate_price_alerts(db: Session, *, user_id: str | None = None) -> list[dict[str, Any]]:
    statement = select(PriceAlert).where(PriceAlert.status == "active")
    if user_id:
        statement = statement.where(PriceAlert.user_id == user_id)
    triggered: list[dict[str, Any]] = []
    for alert in db.scalars(statement).all():
        product = db.get(Product, alert.product_id)
        if not product:
            alert.status = "invalid"
            alert.updated_at = datetime.now(UTC)
            continue
        alert.current_price_snapshot = product.price
        alert.updated_at = datetime.now(UTC)
        if alert.alert_type == "price_drop" and product.price <= alert.target_price:
            alert.status = "triggered"
            alert.triggered_at = datetime.now(UTC)
            triggered.append(price_alert_payload(db, alert, product=product))
        elif alert.alert_type == "stock_restock" and product.stock > 0:
            alert.status = "triggered"
            alert.triggered_at = datetime.now(UTC)
            triggered.append(price_alert_payload(db, alert, product=product))
    db.commit()
    return triggered


def price_alert_payload(db: Session, alert: PriceAlert, *, product: Product | None = None) -> dict[str, Any]:
    product = product or db.get(Product, alert.product_id)
    return {
        "id": alert.id,
        "user_id": alert.user_id,
        "product_id": alert.product_id,
        "product_title": product.title if product else "",
        "target_price": alert.target_price,
        "current_price": product.price if product else alert.current_price_snapshot,
        "current_price_snapshot": alert.current_price_snapshot,
        "alert_type": alert.alert_type,
        "status": alert.status,
        "created_at": alert.created_at.isoformat(),
        "updated_at": alert.updated_at.isoformat(),
        "triggered_at": alert.triggered_at.isoformat() if alert.triggered_at else None,
    }
