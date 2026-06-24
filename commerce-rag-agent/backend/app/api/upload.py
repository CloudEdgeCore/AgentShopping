import os

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.security import CurrentUser, require_current_user
from app.services.image_service import save_upload_image
from app.services.rate_limit_service import limiter


router = APIRouter(prefix="/api/upload", tags=["upload"])


@router.post("/image")
def upload_image(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(require_current_user),
) -> dict[str, str]:
    decision = limiter.check(
        f"upload:{current_user.user_id}",
        limit=_upload_rate_limit_per_minute(),
        window_seconds=60,
    )
    if not decision.allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "message": "upload rate limit exceeded",
                "retry_after_seconds": decision.retry_after_seconds,
            },
            headers={"Retry-After": str(decision.retry_after_seconds)},
        )
    try:
        return save_upload_image(file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _upload_rate_limit_per_minute() -> int:
    try:
        return max(int(os.getenv("UPLOAD_RATE_LIMIT_PER_MINUTE", "20")), 1)
    except ValueError:
        return 20
