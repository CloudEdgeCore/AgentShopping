import hashlib
import hmac
import json
import os
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.security import CurrentUser, require_current_user, require_ops_api_key, require_same_user
from app.models.db import get_db, init_db
from app.models.tables import CommerceOutboxEvent, PaymentCallbackLog
from app.services.cart_service import (
    CommerceError,
    add_cart_item,
    confirm_checkout,
    list_cart,
    mark_order_payment,
    preview_cart_checkout,
    preview_direct_checkout,
    remove_cart_item,
    update_cart_item,
)


router = APIRouter(prefix="/api/commerce", tags=["commerce"])


class CartAddRequest(BaseModel):
    product_id: str
    sku_id: str | None = None
    quantity: int = Field(default=1, ge=1, le=99)
    user_id: str | None = None
    query: str = ""


class CartUpdateRequest(BaseModel):
    quantity: int = Field(ge=1, le=99)
    user_id: str | None = None


class CheckoutProductItem(BaseModel):
    product_id: str
    sku_id: str | None = None
    quantity: int = Field(default=1, ge=1, le=99)


class CheckoutPreviewRequest(BaseModel):
    user_id: str | None = None
    cart_item_ids: list[str] = Field(default_factory=list)
    product_items: list[CheckoutProductItem] = Field(default_factory=list)
    address_id: str = "addr_default"
    query: str = ""


class CheckoutConfirmRequest(BaseModel):
    checkout_id: str
    confirm_token: str
    user_id: str | None = None
    idempotency_key: str = ""


class PaymentCallbackRequest(BaseModel):
    order_id: str
    status: str
    amount: int | None = None
    provider_transaction_id: str = ""
    idempotency_key: str = ""
    provider: str = "callback"
    event_id: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


@router.get("/cart")
def get_cart(
    user_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> dict[str, Any]:
    init_db()
    user_id = require_same_user(current_user, user_id)
    return list_cart(db, user_id=user_id)


@router.post("/cart/items")
def add_item(
    payload: CartAddRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> dict[str, Any]:
    init_db()
    user_id = require_same_user(current_user, payload.user_id)
    try:
        return add_cart_item(
            db,
            product_id=payload.product_id,
            sku_id=payload.sku_id,
            quantity=payload.quantity,
            user_id=user_id,
            query=payload.query,
        )
    except CommerceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/cart/items/{cart_item_id}")
def update_item(
    cart_item_id: str,
    payload: CartUpdateRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> dict[str, Any]:
    init_db()
    user_id = require_same_user(current_user, payload.user_id)
    try:
        return update_cart_item(db, cart_item_id=cart_item_id, quantity=payload.quantity, user_id=user_id)
    except CommerceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/cart/items/{cart_item_id}")
def delete_item(
    cart_item_id: str,
    user_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> dict[str, Any]:
    init_db()
    user_id = require_same_user(current_user, user_id)
    try:
        return remove_cart_item(db, cart_item_id=cart_item_id, user_id=user_id)
    except CommerceError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/checkout/preview")
def preview_checkout(
    payload: CheckoutPreviewRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> dict[str, Any]:
    init_db()
    user_id = require_same_user(current_user, payload.user_id)
    try:
        if payload.product_items:
            return preview_direct_checkout(
                db,
                product_items=[item.model_dump() for item in payload.product_items],
                user_id=user_id,
                address_id=payload.address_id,
                query=payload.query,
            )
        return preview_cart_checkout(
            db,
            user_id=user_id,
            cart_item_ids=payload.cart_item_ids or None,
            address_id=payload.address_id,
        )
    except CommerceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/checkout/confirm")
def confirm_order(
    payload: CheckoutConfirmRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> dict[str, Any]:
    init_db()
    user_id = require_same_user(current_user, payload.user_id)
    try:
        return confirm_checkout(
            db,
            checkout_id=payload.checkout_id,
            confirm_token=payload.confirm_token,
            user_id=user_id,
            idempotency_key=payload.idempotency_key,
        )
    except CommerceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/payment/callback")
async def payment_callback(
    payload: PaymentCallbackRequest,
    request: Request,
    x_payment_signature: str | None = Header(default=None),
    x_payment_timestamp: str | None = Header(default=None),
    x_payment_event_id: str | None = Header(default=None),
    db: Session = Depends(get_db),
    _ops_user: CurrentUser = Depends(require_ops_api_key),
) -> dict[str, Any]:
    init_db()
    raw_body = await request.body()
    _verify_payment_signature(raw_body, x_payment_signature, x_payment_timestamp)
    event_id = (x_payment_event_id or payload.event_id or payload.provider_transaction_id or payload.idempotency_key).strip()
    provider = (payload.provider or "callback").strip()[:64]
    existing = _existing_payment_callback(db, provider=provider, event_id=event_id)
    if existing and existing.status == "success" and existing.result_json:
        try:
            return json.loads(existing.result_json)
        except json.JSONDecodeError:
            return {"ok": True, "event_id": existing.event_id, "status": existing.status}
    if existing:
        raise HTTPException(status_code=409, detail=f"payment callback event already processed as {existing.status}")
    try:
        result = mark_order_payment(
            db,
            order_id=payload.order_id,
            status=payload.status,
            amount=payload.amount,
            provider_transaction_id=payload.provider_transaction_id,
            idempotency_key=payload.idempotency_key,
            provider=provider,
        )
    except CommerceError as exc:
        _log_payment_callback(
            db,
            provider=provider,
            event_id=event_id,
            payload=payload,
            status="failed",
            result={},
            error=str(exc),
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _log_payment_callback(
        db,
        provider=provider,
        event_id=event_id,
        payload=payload,
        status="success",
        result=result,
        error="",
    )
    return result


def _verify_payment_signature(raw_body: bytes, signature: str | None, timestamp: str | None) -> None:
    secret = os.getenv("PAYMENT_WEBHOOK_SECRET", "").strip()
    if not secret:
        raise HTTPException(status_code=503, detail="payment webhook secret is not configured")
    supplied = (signature or "").strip()
    if supplied.startswith("sha256="):
        supplied = supplied[7:]
    if not supplied:
        raise HTTPException(status_code=401, detail="payment callback signature is required")
    signed_payload = (f"{timestamp}.".encode("utf-8") if timestamp else b"") + raw_body
    expected = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="invalid payment callback signature")


def _existing_payment_callback(db: Session, *, provider: str, event_id: str) -> PaymentCallbackLog | None:
    if not event_id:
        return None
    return (
        db.query(PaymentCallbackLog)
        .filter(PaymentCallbackLog.provider == provider)
        .filter(PaymentCallbackLog.event_id == event_id)
        .first()
    )


def _log_payment_callback(
    db: Session,
    *,
    provider: str,
    event_id: str,
    payload: PaymentCallbackRequest,
    status: str,
    result: dict[str, Any],
    error: str,
) -> None:
    row = _existing_payment_callback(db, provider=provider, event_id=event_id) if event_id else None
    if row is None:
        row = PaymentCallbackLog(
            id=f"paycb_{uuid.uuid4().hex[:12]}",
            provider=provider,
            event_id=event_id,
        )
        db.add(row)
    row.order_id = payload.order_id
    row.transaction_id = payload.provider_transaction_id or payload.idempotency_key
    row.status = status
    row.amount = int(payload.amount or 0)
    row.request_json = payload.model_dump_json()
    row.result_json = json.dumps(result, ensure_ascii=False)
    row.error = error
    if status == "success":
        db.add(
            CommerceOutboxEvent(
                id=f"out_{uuid.uuid4().hex[:12]}",
                event_type=f"payment.{result.get('payment_status') or payload.status}",
                aggregate_id=payload.order_id,
                payload_json=json.dumps(result, ensure_ascii=False),
            )
        )
    db.commit()
