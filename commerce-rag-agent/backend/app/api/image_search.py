from typing import Any
import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.security import CurrentUser, require_current_user
from app.agents.intent_router import extract_shopping_constraints
from app.agents.shopping_guide import build_retrieved_items, merge_memory, products_to_cards
from app.models.db import get_db, init_db
from app.services.image_service import resolve_upload_path
from app.services.rate_limit_service import limiter
from app.services.retrieval_orchestrator import RetrievalOrchestrator
from app.services.vision_service import merge_vision_memory, safe_analyze_product_image


router = APIRouter(prefix="/api/image-search", tags=["image-search"])


class ImageSearchByUploadRequest(BaseModel):
    upload_id: str
    query: str = ""
    memory: dict[str, Any] = Field(default_factory=dict)
    limit: int = Field(default=8, ge=1, le=24)


class ImageSearchByTextRequest(BaseModel):
    query: str
    memory: dict[str, Any] = Field(default_factory=dict)
    limit: int = Field(default=8, ge=1, le=24)


@router.post("/upload")
def search_by_uploaded_image(
    payload: ImageSearchByUploadRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> dict[str, Any]:
    init_db()
    _enforce_image_search_limit(current_user)
    image_path = resolve_upload_path(payload.upload_id)
    if image_path is None:
        raise HTTPException(status_code=404, detail="Upload image not found")

    memory = image_search_memory(payload.query, payload.memory, user_id=current_user.user_id)
    query_constraints = extract_shopping_constraints(payload.query)
    vision_analysis = safe_analyze_product_image(image_path, query=payload.query)
    memory = merge_vision_memory(memory, vision_analysis, prefer_image_taxonomy=not bool(query_constraints.category))
    result = RetrievalOrchestrator().search(
        db,
        payload.query or "以图搜图",
        intent="multimodal_search",
        memory=memory,
        image_path=image_path,
        limit=payload.limit,
    )
    return image_search_response(result, memory, limit=payload.limit, vision_analysis=vision_analysis.as_dict())


@router.post("/text")
def search_images_by_text(
    payload: ImageSearchByTextRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> dict[str, Any]:
    init_db()
    _enforce_image_search_limit(current_user)
    memory = image_search_memory(payload.query, payload.memory, user_id=current_user.user_id)
    result = RetrievalOrchestrator().search(
        db,
        payload.query,
        intent="multimodal_search",
        memory=memory,
        limit=payload.limit,
    )
    return image_search_response(result, memory, limit=payload.limit)


def image_search_memory(query: str, memory: dict[str, Any], *, user_id: str = "") -> dict[str, Any]:
    extracted = extract_shopping_constraints(query).model_dump()
    merged = merge_memory(memory or {}, extracted, query)
    if user_id:
        merged["user_id"] = user_id
    return merged


def image_search_response(
    result,
    memory: dict[str, Any],
    *,
    limit: int,
    vision_analysis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    products = result.products[:limit]
    visual = vision_analysis or {}
    return {
        "products": result.image_products[:limit],
        "product_cards": products_to_cards(products, memory, result),
        "retrieved_items": build_retrieved_items(products, result),
        "raw_hits": result.image_candidates_raw[:limit],
        "trace": result.trace,
        "memory": memory,
        "vision_analysis": visual,
        "object_candidates": visual.get("object_candidates", []) if isinstance(visual, dict) else [],
        "needs_clarification": bool(visual.get("needs_clarification")) if isinstance(visual, dict) else False,
    }


def _enforce_image_search_limit(current_user: CurrentUser) -> None:
    decision = limiter.check(
        f"image-search:{current_user.user_id}",
        limit=_image_search_rate_limit_per_minute(),
        window_seconds=60,
    )
    if not decision.allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "message": "image search rate limit exceeded",
                "retry_after_seconds": decision.retry_after_seconds,
            },
            headers={"Retry-After": str(decision.retry_after_seconds)},
        )


def _image_search_rate_limit_per_minute() -> int:
    try:
        return max(int(os.getenv("IMAGE_SEARCH_RATE_LIMIT_PER_MINUTE", "30")), 1)
    except ValueError:
        return 30
