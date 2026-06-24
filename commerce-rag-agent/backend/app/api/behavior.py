from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.security import CurrentUser, require_current_user, require_same_user
from app.models.db import get_db, init_db
from app.models.tables import ChatSession, Message
from app.services.behavior_service import list_behavior_events, log_behavior_event
from app.services.user_product_service import (
    add_product_to_list,
    list_user_products,
    product_collection_state,
    remove_product_from_list,
)


router = APIRouter(prefix="/api/behavior", tags=["behavior"])


class BehaviorEventRequest(BaseModel):
    event_type: str
    user_id: str | None = None
    session_id: str = ""
    message_id: str = ""
    product_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProductListRequest(BaseModel):
    metadata: dict[str, Any] = Field(default_factory=dict)


@router.post("/events")
def create_behavior_event(
    payload: BehaviorEventRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> dict[str, Any]:
    init_db()
    user_id = require_same_user(current_user, payload.user_id)
    _require_owned_context(db, user_id=user_id, session_id=payload.session_id, message_id=payload.message_id)
    event = log_behavior_event(
        db,
        event_type=payload.event_type,
        user_id=user_id,
        session_id=payload.session_id,
        message_id=payload.message_id,
        product_ids=payload.product_ids,
        metadata=payload.metadata,
    )
    return {
        "id": event.id,
        "event_type": event.event_type,
        "product_ids": payload.product_ids,
    }


@router.get("/events")
def read_behavior_events(
    user_id: str | None = None,
    event_type: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> list[dict[str, Any]]:
    init_db()
    user_id = require_same_user(current_user, user_id)
    return list_behavior_events(db, user_id=user_id, event_type=event_type, limit=limit)


@router.get("/products")
def read_user_products(
    list_type: str,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> list[dict[str, Any]]:
    init_db()
    try:
        return list_user_products(db, user_id=current_user.user_id, list_type=list_type, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/product-state")
def read_product_state(
    product_ids: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> dict[str, Any]:
    init_db()
    ids = [item.strip() for item in product_ids.split(",") if item.strip()]
    return product_collection_state(db, user_id=current_user.user_id, product_ids=ids)


@router.put("/{list_type}/{product_id}")
def add_user_product(
    list_type: str,
    product_id: str,
    payload: ProductListRequest | None = None,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> dict[str, Any]:
    init_db()
    try:
        result = add_product_to_list(
            db,
            user_id=current_user.user_id,
            product_id=product_id,
            list_type=list_type,
            metadata=(payload.metadata if payload else {}),
        )
    except ValueError as exc:
        status = 404 if str(exc) == "Product not found" else 400
        raise HTTPException(status_code=status, detail=str(exc)) from exc
    log_behavior_event(
        db,
        event_type=f"{list_type}_add",
        user_id=current_user.user_id,
        product_ids=[product_id],
        metadata={"source": "collection"},
    )
    return result


@router.delete("/{list_type}/{product_id}")
def remove_user_product(
    list_type: str,
    product_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> dict[str, Any]:
    init_db()
    try:
        result = remove_product_from_list(
            db,
            user_id=current_user.user_id,
            product_id=product_id,
            list_type=list_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    log_behavior_event(
        db,
        event_type=f"{list_type}_remove",
        user_id=current_user.user_id,
        product_ids=[product_id],
        metadata={"source": "collection"},
    )
    return result


def _require_owned_context(db: Session, *, user_id: str, session_id: str = "", message_id: str = "") -> None:
    if session_id:
        session = db.get(ChatSession, session_id)
        if not session or session.user_id != user_id:
            raise HTTPException(status_code=403, detail="cannot attach behavior to another user's session")
    if message_id:
        message = db.get(Message, message_id)
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        session = db.get(ChatSession, message.session_id)
        if not session or session.user_id != user_id:
            raise HTTPException(status_code=403, detail="cannot attach behavior to another user's message")
        if session_id and message.session_id != session_id:
            raise HTTPException(status_code=400, detail="message does not belong to session")
