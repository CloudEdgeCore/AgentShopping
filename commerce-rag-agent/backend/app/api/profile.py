from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.security import CurrentUser, require_current_user, require_same_user
from app.models.db import get_db, init_db
from app.services.user_profile_service import delete_user_profile, get_user_profile, upsert_preference


router = APIRouter(prefix="/api/profile", tags=["profile"])


class PreferenceUpsertRequest(BaseModel):
    user_id: str | None = None
    scope: str = "global"
    key: str = "shopping_context"
    value: dict[str, Any]
    source: str = "user"


@router.get("")
def read_profile(
    user_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> dict[str, Any]:
    init_db()
    user_id = require_same_user(current_user, user_id)
    return get_user_profile(db, user_id=user_id)


@router.put("/preferences")
def save_preference(
    payload: PreferenceUpsertRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> dict[str, Any]:
    init_db()
    user_id = require_same_user(current_user, payload.user_id)
    upsert_preference(
        db,
        user_id=user_id,
        scope=payload.scope,
        key=payload.key,
        value=payload.value,
        source=payload.source,
    )
    return get_user_profile(db, user_id=user_id)


@router.delete("")
def clear_profile(
    user_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> dict[str, Any]:
    init_db()
    user_id = require_same_user(current_user, user_id)
    deleted = delete_user_profile(db, user_id=user_id)
    return {"ok": True, "user_id": user_id, "deleted": deleted}
