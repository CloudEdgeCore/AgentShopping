from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.security import CurrentUser, require_current_user, require_ops_api_key, require_same_user
from app.models.db import get_db, init_db
from app.services.price_alert_service import (
    PriceAlertError,
    create_price_alert,
    evaluate_price_alerts,
    list_price_alerts,
)


router = APIRouter(prefix="/api/alerts", tags=["alerts"])


class PriceAlertRequest(BaseModel):
    user_id: str | None = None
    product_id: str
    target_price: int = Field(gt=0)
    alert_type: str = "price_drop"


@router.post("/price")
def create_alert(
    payload: PriceAlertRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> dict[str, Any]:
    init_db()
    user_id = require_same_user(current_user, payload.user_id)
    try:
        return create_price_alert(
            db,
            user_id=user_id,
            product_id=payload.product_id,
            target_price=payload.target_price,
            alert_type=payload.alert_type,
        )
    except PriceAlertError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/price")
def get_alerts(
    user_id: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> list[dict[str, Any]]:
    init_db()
    user_id = require_same_user(current_user, user_id)
    return list_price_alerts(db, user_id=user_id, status=status)


@router.post("/price/evaluate")
def evaluate_alerts(
    user_id: str | None = None,
    db: Session = Depends(get_db),
    _ops_user: CurrentUser = Depends(require_ops_api_key),
) -> dict[str, Any]:
    init_db()
    triggered = evaluate_price_alerts(db, user_id=user_id)
    return {"triggered_count": len(triggered), "triggered": triggered}
