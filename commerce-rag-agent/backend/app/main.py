import os
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse
from dotenv import load_dotenv

from app.api.catalog import router as catalog_router
from app.api.cart_compat import router as cart_compat_router
from app.api.alerts import router as alerts_router
from app.api.behavior import router as behavior_router
from app.api.chat import router as chat_router
from app.api.commerce import router as commerce_router
from app.api.docs import router as docs_router
from app.api.feedback import router as feedback_router
from app.api.image_search import router as image_search_router
from app.api.ops import router as ops_router
from app.api.profile import router as profile_router
from app.api.products import router as products_router
from app.api.sessions import router as sessions_router
from app.api.upload import router as upload_router
from app.api.voice import router as voice_router
from app.api.security import create_auth_router
from app.models.db import get_db
from app.services.image_service import DATA_DIR, ensure_image_dirs
from app.services.rate_limit_service import exempt_path, limiter, rate_limit_enabled, rate_limit_per_minute
from app.services.request_context import get_elapsed_ms, get_request_id, start_request
from app.services.runtime_config_service import runtime_health


def create_app() -> FastAPI:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    api = FastAPI(title="Commerce RAG Agent", version="0.1.0")
    ensure_image_dirs()
    api.mount("/static", StaticFiles(directory=DATA_DIR), name="static")
    api.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @api.middleware("http")
    async def request_guard_middleware(request: Request, call_next):
        request_id = start_request(request.headers.get("X-Request-ID"))
        if rate_limit_enabled() and not exempt_path(request.url.path):
            client_host = request.client.host if request.client else "unknown"
            key = f"{client_host}:{request.url.path}"
            decision = limiter.check(key, limit=rate_limit_per_minute(), window_seconds=60)
            if not decision.allowed:
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "rate limit exceeded",
                        "trace_id": request_id,
                        "retry_after_seconds": decision.retry_after_seconds,
                    },
                    headers={
                        "X-Request-ID": request_id,
                        "Retry-After": str(decision.retry_after_seconds),
                        "X-RateLimit-Limit": str(decision.limit),
                        "X-RateLimit-Remaining": str(decision.remaining),
                    },
                )
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = str(get_elapsed_ms())
        return response

    @api.get("/health")
    def health(db: Session = Depends(get_db)) -> dict[str, object]:
        return {"trace_id": get_request_id(), **runtime_health(db, deep=False)}

    @api.get("/health/deep")
    def health_deep(db: Session = Depends(get_db)) -> dict[str, object]:
        return {"trace_id": get_request_id(), **runtime_health(db, deep=True)}

    api.include_router(chat_router)
    api.include_router(create_auth_router())
    api.include_router(cart_compat_router)
    api.include_router(alerts_router)
    api.include_router(behavior_router)
    api.include_router(catalog_router)
    api.include_router(commerce_router)
    api.include_router(docs_router)
    api.include_router(feedback_router)
    api.include_router(image_search_router)
    api.include_router(ops_router)
    api.include_router(profile_router)
    api.include_router(products_router)
    api.include_router(sessions_router)
    api.include_router(upload_router)
    api.include_router(voice_router)
    return api


def _cors_origins() -> list[str]:
    raw = os.getenv("CORS_ALLOW_ORIGINS", "")
    return [item.strip() for item in raw.split(",") if item.strip()]


app = create_app()
