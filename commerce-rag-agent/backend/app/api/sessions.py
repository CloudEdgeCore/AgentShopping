from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.security import CurrentUser, require_current_user
from app.models.db import get_db, init_db
from app.models.tables import ChatSession
from app.services.session_service import (
    SessionAccessError,
    delete_session,
    ensure_session,
    list_session_messages,
    list_sessions,
)


router = APIRouter(prefix="/api/sessions", tags=["sessions"])


class CreateSessionRequest(BaseModel):
    title: str = "导购会话"


@router.get("")
def get_sessions(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> list[dict]:
    init_db()
    return [
        {
            "id": session.id,
            "title": session.title,
            "updatedAt": session.updated_at.isoformat(),
        }
        for session in list_sessions(db, user_id=current_user.user_id)
    ]


@router.post("")
def create_session(
    payload: CreateSessionRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> dict:
    init_db()
    session = ensure_session(db, user_id=current_user.user_id)
    session.title = payload.title
    db.commit()
    db.refresh(session)
    return {
        "id": session.id,
        "title": session.title,
        "updatedAt": session.updated_at.isoformat(),
    }


@router.get("/{session_id}/messages")
def get_session_messages(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> list[dict]:
    init_db()
    if not db.get(ChatSession, session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        return list_session_messages(db, session_id=session_id, user_id=current_user.user_id)
    except SessionAccessError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.delete("/{session_id}")
def remove_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> dict:
    init_db()
    try:
        if not delete_session(db, session_id=session_id, user_id=current_user.user_id):
            raise HTTPException(status_code=404, detail="Session not found")
    except SessionAccessError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return {"ok": True, "session_id": session_id}
