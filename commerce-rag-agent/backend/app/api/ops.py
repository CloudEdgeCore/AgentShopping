from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.security import require_ops_api_key
from app.models.db import get_db, init_db
from app.evaluation.guide_quality_platform import run_guide_quality_evaluation
from app.services.behavior_service import list_behavior_events
from app.services.commerce_audit_service import list_commerce_audits
from app.services.ops_metrics_service import get_ops_dashboard, get_ops_metrics


router = APIRouter(prefix="/api/ops", tags=["ops"], dependencies=[Depends(require_ops_api_key)])


@router.get("/metrics")
def read_metrics(window_hours: int = 24, db: Session = Depends(get_db)) -> dict[str, Any]:
    init_db()
    return get_ops_metrics(db, window_hours=max(min(window_hours, 24 * 90), 1))


@router.get("/dashboard")
def read_dashboard(window_hours: int = 24, db: Session = Depends(get_db)) -> dict[str, Any]:
    init_db()
    return get_ops_dashboard(db, window_hours=max(min(window_hours, 24 * 90), 1))


@router.get("/commerce-audits")
def read_commerce_audits(
    user_id: str | None = None,
    action: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    init_db()
    return list_commerce_audits(db, user_id=user_id, action=action, limit=limit)


@router.get("/behavior-events")
def read_behavior_events(
    user_id: str | None = None,
    event_type: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    init_db()
    return list_behavior_events(db, user_id=user_id, event_type=event_type, limit=limit)


@router.post("/evaluations/guide-quality")
def run_guide_quality_eval_endpoint(db: Session = Depends(get_db)) -> dict[str, Any]:
    init_db()
    result = run_guide_quality_evaluation(db)
    return {
        "metrics": result["metrics"],
        "failures": result["failures"],
    }
