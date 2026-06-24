import json
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.tables import (
    CartItem,
    ChatSession,
    CommerceAuditLog,
    Feedback,
    Message,
    Order,
    PriceAlert,
    RecommendationLog,
    RetrievalLog,
    UserBehaviorEvent,
)


def get_ops_metrics(db: Session, *, window_hours: int | None = 24) -> dict[str, Any]:
    retrieval_logs = _filter_window(list(db.scalars(select(RetrievalLog)).all()), window_hours)
    recommendation_logs = _filter_window(list(db.scalars(select(RecommendationLog)).all()), window_hours)
    feedback_rows = _filter_window(list(db.scalars(select(Feedback)).all()), window_hours)
    audit_rows = _filter_window(list(db.scalars(select(CommerceAuditLog)).all()), window_hours)
    behavior_rows = _filter_window(list(db.scalars(select(UserBehaviorEvent)).all()), window_hours)

    session_count = _count(db, ChatSession)
    user_message_count = int(
        db.scalar(select(func.count()).select_from(Message).where(Message.role == "user")) or 0
    )
    assistant_message_count = int(
        db.scalar(select(func.count()).select_from(Message).where(Message.role == "assistant")) or 0
    )
    order_count = _count(db, Order)
    cart_item_count = _count(db, CartItem)

    no_result_count = sum(1 for log in retrieval_logs if not _safe_json_list(log.candidates_json))
    total_recommended_cards = sum(len(_safe_json_list(log.products_json)) for log in recommendation_logs)
    negative_feedback = sum(1 for item in feedback_rows if item.rating < 0)
    positive_feedback = sum(1 for item in feedback_rows if item.rating > 0)
    retrieval_latencies = [int(log.latency_ms or 0) for log in retrieval_logs if int(log.latency_ms or 0) >= 0]
    llm_error_count = sum(len(_safe_json_list(log.llm_errors_json)) for log in retrieval_logs)
    provider_latency_rows = [_safe_json_dict(log.provider_latency_json) for log in retrieval_logs]

    return {
        "window": {
            "hours": window_hours,
            "from": _window_start(window_hours).isoformat() if window_hours else "",
        },
        "traffic": {
            "sessions": session_count,
            "user_messages": user_message_count,
            "assistant_messages": assistant_message_count,
        },
        "retrieval": {
            "total_queries": len(retrieval_logs),
            "no_result_queries": no_result_count,
            "no_result_rate": _rate(no_result_count, len(retrieval_logs)),
            "intent_distribution": dict(Counter(log.intent for log in retrieval_logs)),
            "retrieval_mode_distribution": dict(Counter(log.retrieval_mode or "unknown" for log in retrieval_logs)),
            "avg_latency_ms": _avg_int(retrieval_latencies),
            "p95_latency_ms": _percentile(retrieval_latencies, 0.95),
            "llm_error_count": llm_error_count,
            "provider_latency_p95_ms": _provider_latency_p95(provider_latency_rows),
        },
        "recommendation": {
            "recommendation_events": len(recommendation_logs),
            "total_cards": total_recommended_cards,
            "avg_cards_per_event": round(total_recommended_cards / len(recommendation_logs), 2)
            if recommendation_logs
            else 0,
        },
        "commerce": {
            "cart_items": cart_item_count,
            "orders": order_count,
            "conversion_proxy": _rate(order_count, session_count),
            "action_distribution": dict(Counter(row.action for row in audit_rows)),
            "action_status_distribution": dict(Counter(row.status for row in audit_rows)),
        },
        "quality": {
            "positive_feedback": positive_feedback,
            "negative_feedback": negative_feedback,
            "negative_feedback_rate": _rate(negative_feedback, len(feedback_rows)),
        },
        "behavior": {
            "events": len(behavior_rows),
            "event_distribution": dict(Counter(row.event_type for row in behavior_rows)),
            "product_action_events": sum(1 for row in behavior_rows if row.event_type == "product_card_action"),
        },
        "alerts": {
            "active": int(
                db.scalar(select(func.count()).select_from(PriceAlert).where(PriceAlert.status == "active")) or 0
            ),
            "triggered": int(
                db.scalar(select(func.count()).select_from(PriceAlert).where(PriceAlert.status == "triggered")) or 0
            ),
        },
    }


def get_ops_dashboard(db: Session, *, window_hours: int | None = 24) -> dict[str, Any]:
    metrics = get_ops_metrics(db, window_hours=window_hours)
    retrieval_logs = _filter_window(list(db.scalars(select(RetrievalLog)).all()), window_hours)
    recommendation_logs = _filter_window(list(db.scalars(select(RecommendationLog)).all()), window_hours)
    feedback_rows = _filter_window(list(db.scalars(select(Feedback)).all()), window_hours)
    behavior_rows = _filter_window(list(db.scalars(select(UserBehaviorEvent)).all()), window_hours)
    order_rows = _filter_window(list(db.scalars(select(Order)).all()), window_hours)

    product_actions: Counter[str] = Counter()
    product_action_breakdown: dict[str, Counter[str]] = {}
    for event in behavior_rows:
        product_ids = [str(item) for item in _safe_json_list(event.product_ids_json) if item]
        for product_id in product_ids:
            product_actions[product_id] += 1
            product_action_breakdown.setdefault(product_id, Counter())[event.event_type] += 1

    no_result_queries = Counter(
        _clean_query(log.query)
        for log in retrieval_logs
        if not _safe_json_list(log.candidates_json)
    )
    feedback_reasons = Counter(_clean_reason(row.reason) for row in feedback_rows if row.rating < 0)
    image_logs = [
        log
        for log in retrieval_logs
        if "image" in str(log.retrieval_mode or "").lower()
        or "vision" in json.dumps(_safe_json_list(log.trace_json), ensure_ascii=False).lower()
    ]
    image_low_confidence = sum(1 for log in image_logs if _trace_has_flag(log, "low_confidence"))

    return {
        "window": metrics.get("window", {}),
        "kpis": {
            "sessions": metrics.get("traffic", {}).get("sessions", 0),
            "user_messages": metrics.get("traffic", {}).get("user_messages", 0),
            "no_result_rate": metrics.get("retrieval", {}).get("no_result_rate", 0),
            "conversion_proxy": metrics.get("commerce", {}).get("conversion_proxy", 0),
            "negative_feedback_rate": metrics.get("quality", {}).get("negative_feedback_rate", 0),
            "avg_latency_ms": metrics.get("retrieval", {}).get("avg_latency_ms", 0),
            "p95_latency_ms": metrics.get("retrieval", {}).get("p95_latency_ms", 0),
            "llm_error_count": metrics.get("retrieval", {}).get("llm_error_count", 0),
        },
        "funnel": [
            {"stage": "sessions", "count": metrics.get("traffic", {}).get("sessions", 0)},
            {"stage": "recommendations", "count": len(recommendation_logs)},
            {"stage": "detail_views", "count": _event_count(behavior_rows, "product_detail_view")},
            {"stage": "favorites", "count": _event_count(behavior_rows, "favorite_add")},
            {"stage": "compare_adds", "count": _event_count(behavior_rows, "compare_add")},
            {"stage": "add_to_cart", "count": _event_count(behavior_rows, "add_to_cart")},
            {"stage": "checkout_preview", "count": _event_count(behavior_rows, "checkout_preview")},
            {"stage": "checkout_confirm", "count": _event_count(behavior_rows, "checkout_confirm")},
            {"stage": "orders", "count": len(order_rows)},
        ],
        "retrieval": {
            "mode_distribution": metrics.get("retrieval", {}).get("retrieval_mode_distribution", {}),
            "intent_distribution": metrics.get("retrieval", {}).get("intent_distribution", {}),
            "top_no_result_queries": _counter_rows(no_result_queries),
        },
        "image_search": {
            "queries": len(image_logs),
            "low_confidence": image_low_confidence,
            "low_confidence_rate": _rate(image_low_confidence, len(image_logs)),
            "wrong_category_feedback": feedback_reasons.get("wrong_category", 0),
        },
        "feedback": {
            "negative_reasons": _counter_rows(feedback_reasons),
            "positive": metrics.get("quality", {}).get("positive_feedback", 0),
            "negative": metrics.get("quality", {}).get("negative_feedback", 0),
        },
        "products": {
            "top_action_products": [
                {
                    "product_id": product_id,
                    "events": count,
                    "breakdown": dict(product_action_breakdown.get(product_id, Counter())),
                }
                for product_id, count in product_actions.most_common(10)
            ],
        },
        "alerts": metrics.get("alerts", {}),
        "raw_metrics": metrics,
    }


def _count(db: Session, model: type) -> int:
    return int(db.scalar(select(func.count()).select_from(model)) or 0)


def _rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 4)


def _filter_window(rows: list[Any], window_hours: int | None) -> list[Any]:
    if not window_hours or window_hours <= 0:
        return rows
    cutoff = _window_start(window_hours)
    return [row for row in rows if _created_at(row) >= cutoff]


def _window_start(window_hours: int | None) -> datetime:
    hours = window_hours if window_hours and window_hours > 0 else 24
    return datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=hours)


def _created_at(row: Any) -> datetime:
    value = getattr(row, "created_at", None)
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    return datetime.min


def _avg_int(values: list[int]) -> int:
    if not values:
        return 0
    return int(round(sum(values) / len(values), 0))


def _percentile(values: list[int], percentile: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = min(max(int(round((len(ordered) - 1) * percentile)), 0), len(ordered) - 1)
    return ordered[index]


def _provider_latency_p95(rows: list[dict[str, Any]]) -> dict[str, int]:
    values_by_provider: dict[str, list[int]] = {}
    for row in rows:
        for provider, value in row.items():
            try:
                values_by_provider.setdefault(str(provider), []).append(int(value))
            except (TypeError, ValueError):
                continue
    return {provider: _percentile(values, 0.95) for provider, values in values_by_provider.items()}


def _safe_json_list(raw: str | None) -> list[Any]:
    try:
        value = json.loads(raw or "[]")
    except json.JSONDecodeError:
        return []
    return value if isinstance(value, list) else []


def _safe_json_dict(raw: str | None) -> dict[str, Any]:
    try:
        value = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _event_count(rows: list[UserBehaviorEvent], event_type: str) -> int:
    return sum(1 for row in rows if row.event_type == event_type)


def _counter_rows(counter: Counter[str], *, limit: int = 10) -> list[dict[str, Any]]:
    return [{"name": key, "count": count} for key, count in counter.most_common(limit) if key]


def _clean_query(query: str) -> str:
    text = " ".join(str(query or "").split())
    return text[:80] or "(empty)"


def _clean_reason(reason: str) -> str:
    text = str(reason or "").strip()
    return text or "unknown"


def _trace_has_flag(log: RetrievalLog, flag: str) -> bool:
    trace = _safe_json_list(log.trace_json)
    for item in trace:
        if isinstance(item, dict) and bool(item.get(flag)):
            return True
    return False
