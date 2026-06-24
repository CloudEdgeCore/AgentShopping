from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.security import CurrentUser, require_current_user, require_same_user
from app.models.db import get_db, init_db
from app.models.tables import ChatSession, Message
from app.services.behavior_service import log_behavior_event, product_ids_for_message
from app.services.feedback_service import create_feedback


router = APIRouter(prefix="/api/feedback", tags=["feedback"])


class FeedbackRequest(BaseModel):
    message_id: str
    rating: int
    reason: str = ""
    user_id: str | None = None


@router.post("")
def submit_feedback(
    payload: FeedbackRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> dict:
    init_db()
    user_id = require_same_user(current_user, payload.user_id)
    if payload.rating not in {-1, 1}:
        raise HTTPException(status_code=400, detail="rating must be 1 or -1")
    message = db.get(Message, payload.message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    session = db.get(ChatSession, message.session_id)
    if not session or session.user_id != user_id:
        raise HTTPException(status_code=403, detail="cannot submit feedback for another user's message")
    feedback = create_feedback(
        db,
        message_id=payload.message_id,
        rating=payload.rating,
        reason=payload.reason,
    )
    product_ids = product_ids_for_message(db, payload.message_id)
    log_behavior_event(
        db,
        event_type="feedback_positive" if payload.rating > 0 else "feedback_negative",
        user_id=user_id,
        message_id=payload.message_id,
        product_ids=product_ids,
        metadata={"reason": payload.reason, "rating": payload.rating},
    )
    return {
        "id": feedback.id,
        "message_id": feedback.message_id,
        "rating": feedback.rating,
        "reason": feedback.reason,
    }
