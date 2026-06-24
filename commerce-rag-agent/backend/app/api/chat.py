import json
import os
import time
from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette.responses import StreamingResponse

from app.agents.graph import run_agent
from app.agents.intent_router import extract_shopping_constraints
from app.agents.response_composer import stream_compose_agent_response
from app.agents.shopping_guide import products_to_cards
from app.api.security import CurrentUser, require_current_user, require_same_user
from app.models.db import get_db, init_db
from app.services.behavior_service import log_recommendation_impression
from app.services.image_service import resolve_upload_path
from app.services.log_service import log_recommendation, log_retrieval
from app.services.retrieval_orchestrator import RetrievalOrchestrator
from app.services.session_service import SessionAccessError, add_message, ensure_session, get_latest_memory
from app.services.user_profile_service import memory_with_profile_defaults, update_profile_from_memory
from app.services.vision_service import merge_vision_memory, safe_analyze_product_image


router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatStreamRequest(BaseModel):
    message: str
    session_id: str | None = None
    user_id: str | None = None
    memory: dict | None = None
    upload_id: str | None = None


@router.post("/stream")
def chat_stream(
    payload: ChatStreamRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_current_user),
) -> StreamingResponse:
    init_db()
    user_id = require_same_user(current_user, payload.user_id)
    try:
        session = ensure_session(db, session_id=payload.session_id, user_id=user_id)
    except SessionAccessError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    add_message(db, session_id=session.id, role="user", content=payload.message)
    raw_memory = payload.memory if payload.memory is not None else get_latest_memory(db, session_id=session.id)
    session_memory = memory_with_profile_defaults(
        db,
        user_id=user_id,
        query=payload.message,
        memory=raw_memory,
    )
    session_memory["user_id"] = user_id
    image_path = resolve_upload_path(payload.upload_id) if payload.upload_id else None

    def event_stream() -> Iterator[str]:
        phase_timings: dict[str, int] = {}
        delta_count = 0
        yield sse("status", status_payload("received", session.id))
        try:
            if payload.upload_id and image_path is None:
                yield sse("status", status_payload("validating_image", session.id))
                result = {
                    "intent": "multimodal_search",
                    "answer": "我没有找到这张上传图片，请重新上传后再试。",
                    "memory": session_memory,
                    "retrieved_items": [],
                    "product_cards": [],
                    "trace": [{"node": "retrieval_orchestrator", "error": "upload_not_found"}],
                }
            else:
                agent_query = payload.message
                agent_memory = dict(session_memory)
                vision_analysis = None
                orchestrator = RetrievalOrchestrator()
                if image_path and _image_fast_preview_enabled():
                    yield sse("status", status_payload("image_fast_preview", session.id))
                    preview_started = time.perf_counter()
                    try:
                        preview_result = orchestrator.search(
                            db,
                            agent_query or "以图搜图",
                            intent="multimodal_search",
                            memory=agent_memory,
                            image_path=image_path,
                            limit=_image_fast_preview_limit(),
                        )
                        preview_cards = products_to_cards(
                            preview_result.products[: _image_fast_preview_limit()],
                            agent_memory,
                            preview_result,
                        )
                        phase_timings["image_fast_preview_ms"] = _elapsed_ms(preview_started)
                        if preview_cards:
                            yield sse("product_cards", preview_cards)
                    except Exception as error:
                        phase_timings["image_fast_preview_ms"] = _elapsed_ms(preview_started)
                        yield sse(
                            "trace",
                            [
                                {
                                    "node": "image_fast_preview",
                                    "error": f"{type(error).__name__}: {str(error)[:240]}",
                                }
                            ],
                        )
                if image_path:
                    yield sse("status", status_payload("vision_understanding", session.id))
                    vision_started = time.perf_counter()
                    query_constraints = extract_shopping_constraints(payload.message)
                    vision_analysis = safe_analyze_product_image(image_path, query=payload.message)
                    phase_timings["vision_ms"] = _elapsed_ms(vision_started)
                    agent_memory = merge_vision_memory(
                        agent_memory,
                        vision_analysis,
                        prefer_image_taxonomy=not bool(query_constraints.category),
                    )
                yield sse(
                    "status",
                    status_payload("image_retrieving" if image_path else "retrieving", session.id),
                )
                agent_started = time.perf_counter()
                result = run_agent(
                    db,
                    agent_query,
                    memory=agent_memory,
                    image_path=image_path,
                    orchestrator=orchestrator,
                )
                phase_timings["agent_ms"] = _elapsed_ms(agent_started)
                if vision_analysis is not None:
                    result = {
                        **result,
                        "vision_analysis": vision_analysis.as_dict(),
                        "trace": result.get("trace", [])
                        + [
                            {
                                "node": "vision_analysis",
                                "enabled": vision_analysis.enabled,
                                "category": vision_analysis.category,
                                "subcategory": vision_analysis.subcategory,
                                "alternative_categories": vision_analysis.alternative_categories,
                                "alternative_subcategories": vision_analysis.alternative_subcategories,
                                "visual_terms": vision_analysis.visual_terms,
                                "confidence": vision_analysis.confidence,
                                "object_count": vision_analysis.object_count,
                                "object_candidates": vision_analysis.object_candidates,
                                "quality_flags": vision_analysis.quality_flags,
                                "needs_clarification": vision_analysis.needs_clarification,
                                "error": vision_analysis.error,
                            }
                        ],
                    }
                if image_path is None and implies_missing_image(payload.message):
                    result = {
                        **result,
                        "intent": "image_text_fallback",
                        "answer": (
                            "我还没有收到图片，所以暂时不能按图片外观做相似检索。"
                            "但我可以先根据你文字里提到的预算、品类和使用场景，为你推荐以下几种选择。\n\n"
                            f"{result.get('answer', '')}"
                        ),
                        "trace": result.get("trace", []) + [
                            {"node": "image_text_fallback", "reason": "image_reference_without_upload"}
                        ],
                    }

            yield sse("status", status_payload("agent_done", session.id))
            yield sse("status", status_payload("composing", session.id))
            compose_started = time.perf_counter()
            first_delta_sent = False
            assistant_message = add_message(
                db,
                session_id=session.id,
                role="assistant",
                content="",
                metadata_json="{}",
            )
            yield sse(
                "message_start",
                {
                    "message_id": assistant_message.id,
                    "session_id": session.id,
                },
            )
            initial_cards = result.get("product_cards") if isinstance(result.get("product_cards"), list) else []
            if initial_cards:
                phase_timings["product_cards_first_ms"] = _elapsed_ms(agent_started)
                yield sse("product_cards", initial_cards)
            for compose_event in stream_compose_agent_response(query=payload.message, result=result):
                if compose_event.get("type") == "delta":
                    if not first_delta_sent:
                        phase_timings["compose_first_delta_ms"] = _elapsed_ms(compose_started)
                        first_delta_sent = True
                    delta_count += 1
                    yield sse(
                        "message_delta",
                        {
                            "message_id": assistant_message.id,
                            "session_id": session.id,
                            "delta": compose_event.get("content", ""),
                        },
                    )
                elif compose_event.get("type") == "complete":
                    result = compose_event.get("result", result)
            phase_timings["compose_total_ms"] = _elapsed_ms(compose_started)
            result["trace"] = result.get("trace", []) + [
                {
                    "node": "chat_stream",
                    "phase_timings_ms": phase_timings,
                    "delta_count": delta_count,
                    "streaming": True,
                }
            ]

            assistant_message.content = result.get("answer", "")
            assistant_message.metadata_json = json.dumps({"memory": result.get("memory", {})}, ensure_ascii=False)
            db.commit()
            db.refresh(assistant_message)
            update_profile_from_memory(
                db,
                user_id=user_id,
                memory=result.get("memory", {}),
                source="agent",
            )
            log_retrieval(
                db,
                session_id=session.id,
                query=payload.message,
                intent=result.get("intent", ""),
                filters=result.get("memory", {}),
                candidates=result.get("retrieved_items", []),
                trace=result.get("trace", []),
            )
            log_recommendation(
                db,
                session_id=session.id,
                message_id=assistant_message.id,
                products=result.get("product_cards", []),
            )
            log_recommendation_impression(
                db,
                user_id=user_id,
                session_id=session.id,
                message_id=assistant_message.id,
                query=payload.message,
                intent=result.get("intent", ""),
                product_cards=result.get("product_cards", []),
            )

            answer = str(result.get("answer", ""))
            yield sse(
                "message",
                {
                    "content": answer,
                    "message_id": assistant_message.id,
                    "session_id": session.id,
                    "memory": result.get("memory", {}),
                    "feedback_enabled": should_enable_feedback(result),
                    "feedback_reasons": feedback_reason_options(),
                    "order_guidance": result.get("order_guidance") or {},
                    "suggested_actions": build_suggested_actions(result),
                    "cart_state": result.get("cart_state") or {},
                },
            )
            if result.get("cart_state"):
                yield sse("cart_state", result.get("cart_state", {}))
            yield sse("trace", result.get("trace", []))
            if result.get("vision_analysis"):
                yield sse("vision_analysis", result.get("vision_analysis", {}))
            yield sse("product_cards", result.get("product_cards", []))
            if result.get("comparison"):
                yield sse("comparison", result.get("comparison", {}))
            yield sse("done", {"ok": True})
        except Exception as error:
            db.rollback()
            try:
                log_retrieval(
                    db,
                    session_id=session.id,
                    query=payload.message,
                    intent="error",
                    filters=session_memory,
                    candidates=[],
                    trace=[{"node": "chat_stream", "error": f"{type(error).__name__}: {str(error)[:500]}"}],
                    status="error",
                    error=f"{type(error).__name__}: {str(error)[:500]}",
                )
            except Exception:
                db.rollback()
            yield sse("error", {"message": f"{type(error).__name__}: {str(error)[:500]}"})
            yield sse("done", {"ok": False})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def sse(event: str, data: object) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def status_payload(stage: str, session_id: str) -> dict[str, str]:
    labels = {
        "received": "已接收请求",
        "validating_image": "正在校验上传图片",
        "image_fast_preview": "正在先按图片相似度快速出结果",
        "vision_understanding": "正在识别图片里的商品属性",
        "retrieving": "正在理解需求并检索商品",
        "image_retrieving": "正在按图片相似度筛选商品",
        "agent_done": "已完成检索和策略判断",
        "composing": "正在整理导购回复",
    }
    return {"stage": stage, "label": labels.get(stage, stage), "session_id": session_id}


def feedback_reason_options() -> list[dict[str, str]]:
    return [
        {"id": "wrong_category", "label": "品类不对"},
        {"id": "over_budget", "label": "价格不合适"},
        {"id": "bad_stock", "label": "库存不合适"},
        {"id": "weak_reason", "label": "理由不充分"},
        {"id": "missing_reviews", "label": "评价信息不足"},
        {"id": "wrong_context", "label": "上下文串了"},
    ]


def build_suggested_actions(result: dict) -> list[str]:
    cards = result.get("product_cards") or []
    memory = result.get("memory") or {}
    intent = str(result.get("intent") or "")
    no_exact_match = bool(result.get("no_exact_match"))
    trace_text = json.dumps(result.get("trace", []), ensure_ascii=False)
    visual_mode = "image_search" in trace_text or bool(memory.get("visual_search_mode"))
    order_guidance = result.get("order_guidance") if isinstance(result.get("order_guidance"), dict) else {}
    cart_state = result.get("cart_state") if isinstance(result.get("cart_state"), dict) else {}
    cart_items = cart_state.get("items") if isinstance(cart_state.get("items"), list) else []

    actions: list[str] = []
    primary_action = str(order_guidance.get("primary_action") or "").strip()
    secondary_actions = order_guidance.get("secondary_actions") or []
    guided_actions = {primary_action} if primary_action else set()
    if isinstance(secondary_actions, list):
        guided_actions.update(str(action) for action in secondary_actions if action)

    if len(cards) >= 2:
        actions.extend(["对比这几款", "这几款评价怎么样", "哪款更适合我？"])
    elif len(cards) == 1:
        actions.extend(["看看这款评价", "还有其他选择吗？"])

    if visual_mode:
        actions.extend(["只看同品类现货", "按价格从低到高", "换一张图再搜"])

    if cart_items:
        actions.extend(["查看购物车", "把数量改成 2"])
        if len(cart_items) >= 2:
            actions.append("删除第二个商品")
        else:
            actions.append("删除第一个商品")
        actions.append("结算购物车")
    elif no_exact_match or not cards:
        actions.extend(["放宽预算再找", "换个相邻品类", "只看现货"])

    if intent in {"product_knowledge", "comparison"}:
        actions.extend(["总结差评风险", "给我最终购买建议"])

    if memory.get("budget_max") and cards:
        actions.append("只看预算内")
    if cards:
        actions.append("降价了提醒我")

    return [action for action in list(dict.fromkeys(actions)) if action not in guided_actions][:5]


def implies_missing_image(message: str) -> bool:
    lowered = message.lower()
    explicit_image_reference_keywords = [
        "这张图",
        "这张图片",
        "图片里",
        "图里",
        "照片里",
        "这张照片",
        "上传的图",
        "上传的图片",
        "如图",
    ]
    image_similarity_keywords = [
        "类似这",
        "像这张",
        "找图里",
        "找这张",
        "找这个图片",
        "找类似这",
        "找相似这",
        "similar to this",
        "same style",
    ]
    return any(keyword in lowered for keyword in explicit_image_reference_keywords) or any(
        keyword in lowered for keyword in image_similarity_keywords
    )


def should_enable_feedback(result: dict) -> bool:
    intent = str(result.get("intent", "")).strip().lower()
    if intent in {"chitchat"}:
        return False
    if result.get("product_cards"):
        return True
    return intent in {
        "faq",
        "product_knowledge",
        "product_query",
        "shopping_guide",
        "decision_guide",
        "comparison",
        "multimodal_search",
        "image_text_fallback",
    }


def _elapsed_ms(started_at: float) -> int:
    return max(int((time.perf_counter() - started_at) * 1000), 0)


def _image_fast_preview_enabled() -> bool:
    return _env_bool("IMAGE_SEARCH_FAST_PREVIEW_ENABLED", True)


def _image_fast_preview_limit() -> int:
    try:
        return max(min(int(os.getenv("IMAGE_SEARCH_FAST_PREVIEW_LIMIT", "6")), 12), 1)
    except ValueError:
        return 6


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
