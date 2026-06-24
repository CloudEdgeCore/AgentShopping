import json
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tables import CommerceAuditLog
from app.services.request_context import get_request_id


def log_commerce_action(
    db: Session,
    *,
    user_id: str,
    action: str,
    status: str,
    session_id: str = "",
    product_ids: list[str] | None = None,
    amount: int = 0,
    request: dict[str, Any] | None = None,
    result: dict[str, Any] | None = None,
    error: str = "",
) -> CommerceAuditLog:
    log = CommerceAuditLog(
        id=f"aud_{uuid.uuid4().hex[:12]}",
        trace_id=get_request_id(),
        user_id=user_id,
        session_id=session_id,
        action=action,
        status=status,
        product_ids_json=json.dumps(product_ids or [], ensure_ascii=False),
        amount=int(amount or 0),
        request_json=json.dumps(request or {}, ensure_ascii=False),
        result_json=json.dumps(result or {}, ensure_ascii=False),
        error=error,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def list_commerce_audits(
    db: Session,
    *,
    user_id: str | None = None,
    action: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    statement = select(CommerceAuditLog).order_by(CommerceAuditLog.created_at.desc())
    if user_id:
        statement = statement.where(CommerceAuditLog.user_id == user_id)
    if action:
        statement = statement.where(CommerceAuditLog.action == action)
    rows = list(db.scalars(statement.limit(max(min(limit, 200), 1))).all())
    return [commerce_audit_payload(row) for row in rows]


def commerce_audit_payload(log: CommerceAuditLog) -> dict[str, Any]:
    return {
        "id": log.id,
        "trace_id": log.trace_id,
        "user_id": log.user_id,
        "session_id": log.session_id,
        "action": log.action,
        "status": log.status,
        "product_ids": _safe_json_list(log.product_ids_json),
        "amount": log.amount,
        "request": _safe_json_dict(log.request_json),
        "result": _safe_json_dict(log.result_json),
        "error": log.error,
        "created_at": log.created_at.isoformat(),
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
