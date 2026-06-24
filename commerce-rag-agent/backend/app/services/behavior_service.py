import json
import uuid
from collections import Counter, defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tables import RecommendationLog, UserBehaviorEvent
from app.services.request_context import get_request_id


POSITIVE_EVENT_WEIGHTS = {
    "recommendation_impression": 0.08,
    "product_card_action": 0.8,
    "product_detail_view": 1.0,
    "favorite_add": 1.8,
    "compare_add": 1.4,
    "recent_add": 0.4,
    "review_followup": 1.2,
    "feedback_positive": 2.0,
    "add_to_cart": 3.5,
    "cart_quantity_update": 1.5,
    "checkout_preview": 4.5,
    "checkout_address_update": 0.5,
    "checkout_confirm": 8.0,
}

NEGATIVE_EVENT_WEIGHTS = {
    "feedback_negative": -6.0,
    "favorite_remove": -0.8,
    "compare_remove": -0.5,
    "remove_from_cart": -2.5,
    "checkout_cancel": -3.0,
}


def log_behavior_event(
    db: Session,
    *,
    event_type: str,
    user_id: str,
    session_id: str = "",
    message_id: str = "",
    product_ids: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> UserBehaviorEvent:
    event = UserBehaviorEvent(
        id=f"beh_{uuid.uuid4().hex[:12]}",
        trace_id=get_request_id(),
        user_id=user_id,
        session_id=session_id,
        message_id=message_id,
        event_type=event_type,
        product_ids_json=json.dumps(product_ids or [], ensure_ascii=False),
        metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def log_recommendation_impression(
    db: Session,
    *,
    user_id: str,
    session_id: str,
    message_id: str,
    query: str,
    intent: str,
    product_cards: list[dict[str, Any]],
) -> UserBehaviorEvent | None:
    product_ids = [str(card.get("product_id") or "") for card in product_cards if card.get("product_id")]
    if not product_ids:
        return None
    return log_behavior_event(
        db,
        event_type="recommendation_impression",
        user_id=user_id,
        session_id=session_id,
        message_id=message_id,
        product_ids=product_ids,
        metadata={
            "query": query,
            "intent": intent,
            "ranked_products": [
                {
                    "product_id": card.get("product_id"),
                    "rank": index,
                    "score": card.get("score"),
                    "match_score": card.get("match_score"),
                    "commercial_score": card.get("commercial_score"),
                }
                for index, card in enumerate(product_cards, start=1)
            ],
        },
    )


def product_ids_for_message(db: Session, message_id: str) -> list[str]:
    if not message_id:
        return []
    row = db.scalar(select(RecommendationLog).where(RecommendationLog.message_id == message_id))
    if row is None:
        return []
    product_ids: list[str] = []
    for item in _safe_json_list(row.products_json):
        if isinstance(item, dict) and item.get("product_id"):
            product_ids.append(str(item["product_id"]))
    return list(dict.fromkeys(product_ids))


def list_behavior_events(
    db: Session,
    *,
    user_id: str | None = None,
    event_type: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    statement = select(UserBehaviorEvent).order_by(UserBehaviorEvent.created_at.desc())
    if user_id:
        statement = statement.where(UserBehaviorEvent.user_id == user_id)
    if event_type:
        statement = statement.where(UserBehaviorEvent.event_type == event_type)
    rows = list(db.scalars(statement.limit(max(min(limit, 500), 1))).all())
    return [behavior_event_payload(row) for row in rows]


def behavior_event_payload(event: UserBehaviorEvent) -> dict[str, Any]:
    return {
        "id": event.id,
        "trace_id": event.trace_id,
        "user_id": event.user_id,
        "session_id": event.session_id,
        "message_id": event.message_id,
        "event_type": event.event_type,
        "product_ids": _safe_json_list(event.product_ids_json),
        "metadata": _safe_json_dict(event.metadata_json),
        "created_at": event.created_at.isoformat(),
    }


def product_behavior_summary(
    db: Session,
    product_ids: list[str],
    *,
    limit: int = 5000,
) -> dict[str, dict[str, Any]]:
    requested = {str(product_id) for product_id in product_ids if product_id}
    if not requested:
        return {}

    rows = list(
        db.scalars(
            select(UserBehaviorEvent)
            .order_by(UserBehaviorEvent.created_at.desc())
            .limit(max(min(limit, 20000), 1))
        ).all()
    )
    event_counts: dict[str, Counter[str]] = defaultdict(Counter)
    score_by_product: dict[str, float] = defaultdict(float)

    for row in rows:
        ids = [product_id for product_id in _safe_json_list(row.product_ids_json) if product_id in requested]
        if not ids:
            continue
        weight = POSITIVE_EVENT_WEIGHTS.get(row.event_type, NEGATIVE_EVENT_WEIGHTS.get(row.event_type, 0.0))
        for product_id in ids:
            event_counts[product_id][row.event_type] += 1
            score_by_product[product_id] += weight

    return {
        product_id: {
            "events": dict(event_counts.get(product_id, Counter())),
            "score": round(max(min(score_by_product.get(product_id, 0.0), 18.0), -18.0), 4),
        }
        for product_id in requested
    }


def _safe_json_dict(raw: str | None) -> dict[str, Any]:
    try:
        parsed = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _safe_json_list(raw: str | None) -> list[Any]:
    try:
        parsed = json.loads(raw or "[]")
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []
