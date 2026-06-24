import json
import uuid

from sqlalchemy.orm import Session

from app.models.tables import RecommendationLog, RetrievalLog
from app.services.request_context import get_elapsed_ms, get_request_id


def log_retrieval(
    db: Session,
    *,
    session_id: str,
    query: str,
    intent: str,
    filters: dict,
    candidates: list,
    trace: list | dict | None = None,
    status: str = "success",
    latency_ms: int | None = None,
    error: str = "",
) -> None:
    trace_items = _trace_items(trace)
    db.add(
        RetrievalLog(
            id=f"ret_{uuid.uuid4().hex[:12]}",
            trace_id=get_request_id(),
            session_id=session_id,
            query=query,
            intent=intent,
            filters_json=json.dumps(filters, ensure_ascii=False),
            candidates_json=json.dumps(candidates, ensure_ascii=False),
            trace_json=json.dumps(trace_items, ensure_ascii=False, default=str),
            retrieval_mode=_first_trace_value(trace_items, "retrieval_mode"),
            llm_errors_json=json.dumps(_llm_errors(trace_items), ensure_ascii=False),
            provider_latency_json=json.dumps(_provider_latencies(trace_items), ensure_ascii=False),
            cost_estimate_json=json.dumps(_cost_estimates(trace_items), ensure_ascii=False),
            status=status,
            latency_ms=latency_ms if latency_ms is not None else get_elapsed_ms(),
            error=error,
        )
    )
    db.commit()


def log_recommendation(db: Session, *, session_id: str, message_id: str, products: list) -> None:
    db.add(
        RecommendationLog(
            id=f"rec_{uuid.uuid4().hex[:12]}",
            trace_id=get_request_id(),
            session_id=session_id,
            message_id=message_id,
            products_json=json.dumps(products, ensure_ascii=False),
        )
    )
    db.commit()


def _trace_items(trace: list | dict | None) -> list[dict]:
    if isinstance(trace, dict):
        return [trace]
    if isinstance(trace, list):
        return [item for item in trace if isinstance(item, dict)]
    return []


def _first_trace_value(trace: list[dict], key: str) -> str:
    for item in trace:
        value = item.get(key)
        if value:
            return str(value)[:64]
    return ""


def _llm_errors(trace: list[dict]) -> list[dict[str, str]]:
    errors = []
    for item in trace:
        error = item.get("llm_error")
        if error:
            errors.append({"node": str(item.get("node") or ""), "error": str(error)[:500]})
    return errors


def _provider_latencies(trace: list[dict]) -> dict[str, int]:
    latencies: dict[str, int] = {}
    for item in trace:
        latency = item.get("provider_latency_ms") or item.get("llm_latency_ms")
        if latency is None:
            continue
        key = str(item.get("provider") or item.get("node") or "provider")
        try:
            latencies[key] = int(latency)
        except (TypeError, ValueError):
            continue
    return latencies


def _cost_estimates(trace: list[dict]) -> dict[str, object]:
    estimates = []
    for item in trace:
        estimate = item.get("cost_estimate")
        if isinstance(estimate, dict):
            estimates.append({"node": str(item.get("node") or ""), **estimate})
    total = sum(float(item.get("estimated_cost") or 0.0) for item in estimates)
    return {"total_estimated_cost": round(total, 8), "items": estimates}
