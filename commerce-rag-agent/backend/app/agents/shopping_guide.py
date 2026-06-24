from dataclasses import dataclass
import os
from typing import Any

from sqlalchemy.orm import Session

from app.agents.guide_quality import (
    build_clarification_answer,
    build_guide_answer,
    build_product_card,
    diagnose_guide_demand,
    guide_answer_policy,
    rank_products_for_guide,
    score_product_for_guide,
)
from app.agents.intent_router import extract_shopping_constraints
from app.llm.generation import generate_shopping_result
from app.models.tables import Product
from app.retrieval.text_index import TextIndex
from app.services.commercial_ranking_service import CommercialScore, rank_products_with_commercial_factors
from app.services.business_rules import rule_dict, rule_list
from app.services.product_search_service import ProductSearchService
from app.services.product_service import filter_products
from app.services.retrieval_orchestrator import RetrievalOrchestrator, RetrievalResult
from app.services.taxonomy import load_taxonomy


MEMORY_FIELDS = [
    "budget_max",
    "category",
    "subcategory",
    "audience",
    "use_cases",
    "preferences",
    "product_ids",
    "strict_filter",
    "last_product_ids",
    "exclude_product_ids",
    "cart_item_ids",
    "pending_checkout_id",
    "pending_checkout_token",
    "last_order_id",
    "dialogue_state",
    "dialogue_action",
    "dialogue_target_product_ids",
    "dialogue_quantity",
    "dialogue_quantity_delta",
    "dialogue_message",
    "user_profile",
    "user_id",
    "visual_search_mode",
    "visual_terms",
    "visual_attributes",
    "vision_summary",
    "vision_confidence",
    "vision_category",
    "vision_subcategory",
    "vision_alternative_categories",
    "vision_alternative_subcategories",
    "vision_quality_flags",
    "vision_object_count",
    "vision_needs_clarification",
    "image_query",
    "explicit_category",
    "explicit_subcategory",
]


@dataclass
class GuideRetrieval:
    products: list[Product]
    trace: dict[str, Any]
    retrieved_items: list[dict[str, Any]]
    raw_result: RetrievalResult | None = None


def shopping_guide_node(
    db: Session,
    *,
    search_service: ProductSearchService | None = None,
    orchestrator: RetrievalOrchestrator | None = None,
):
    def node(state: dict) -> dict:
        query = state["query"]
        constraints = extract_shopping_constraints(query).model_dump()
        memory = merge_memory(state.get("memory", {}), constraints, query)
        diagnosis = diagnose_guide_demand(query, memory, has_image=bool(state.get("image_path")))
        if not diagnosis.ready:
            trace_item = {
                **diagnosis.trace,
                "node": "shopping_guide",
                "guide_quality_action": diagnosis.action,
                "missing_fields": diagnosis.missing_fields,
            }
            return {
                **state,
                "constraints": constraints,
                "memory": memory,
                "retrieved_items": [],
                "product_cards": [],
                "guide_diagnosis": diagnosis.trace,
                "answer": build_clarification_answer(diagnosis),
                "trace": state.get("trace", []) + [trace_item],
            }
        products = filter_products(
            db,
            category=memory.get("category"),
            subcategory=memory.get("subcategory"),
            budget_max=memory.get("budget_max"),
        )
        alternative_products = exclude_previous_products(products, memory)
        if memory.get("exclude_product_ids") and not alternative_products:
            cards: list[dict] = []
            answer = build_no_more_options_answer(memory)
            trace_item = {
                "node": "shopping_guide",
                "cards": [],
                "llm_enabled": False,
                "retrieval_mode": "sqlite_filter_no_new_alternatives",
                "sqlite_candidates": len(products),
                "excluded_product_ids": memory.get("exclude_product_ids", []),
            }
            return {
                **state,
                "constraints": constraints,
                "memory": {**memory, "exclude_product_ids": []},
                "retrieved_items": [],
                "product_cards": cards,
                "no_exact_match": False,
                "answer": answer,
                "trace": state.get("trace", []) + [trace_item],
            }
        products = alternative_products
        if not products and memory.get("strict_filter"):
            cards: list[dict] = []
            answer = build_recommendation_answer(cards, memory, strict_no_match=True)
            trace_item = {
                "node": "shopping_guide",
                "cards": [],
                "llm_enabled": False,
                "retrieval_mode": "sqlite_strict_filter_empty",
                "sqlite_candidates": 0,
                "chroma_hits": [],
                "fallback_reason": "strict_filter_no_match",
            }
            return {
                **state,
                "constraints": constraints,
                "memory": {**memory, "last_product_ids": []},
                "retrieved_items": [],
                "product_cards": cards,
                "no_exact_match": True,
                "answer": answer,
                "trace": state.get("trace", []) + [trace_item],
            }
        no_exact_match = False
        if not products and memory.get("subcategory") and memory.get("budget_max"):
            no_exact_match = True
            products = filter_products(
                db,
                category=memory.get("category"),
                subcategory=memory.get("subcategory"),
                budget_max=None,
            )
        retrieval = retrieve_products_for_guide(
            db,
            products,
            memory,
            query,
            intent=state.get("intent", "shopping_guide"),
            image_path=state.get("image_path"),
            search_service=search_service,
            orchestrator=orchestrator,
        )
        products = retrieval.products
        products, commercial_scores = rank_products_with_commercial_factors(db, products, memory, query)
        cards = products_to_cards(
            products,
            memory,
            retrieval.raw_result,
            query=query,
            commercial_scores=commercial_scores,
        )
        if should_use_low_confidence_response(retrieval, memory, cards):
            answer = build_low_confidence_answer(query, memory, cards, retrieval)
            trace_item = {
                "node": "shopping_guide",
                "cards": [card["product_id"] for card in cards],
                "llm_enabled": False,
                **retrieval.trace,
                "guide_quality": diagnosis.trace,
                "fallback_reason": "low_confidence_retrieval",
            }
            return {
                **state,
                "constraints": constraints,
                "memory": build_turn_memory(memory, products, retrieval.raw_result),
                "retrieved_items": retrieval.retrieved_items,
                "product_cards": cards,
                "no_exact_match": True,
                "answer": answer,
                "trace": state.get("trace", []) + [trace_item],
            }
        visual_search_mode = is_visual_retrieval(retrieval.raw_result)
        fallback_answer = build_recommendation_answer(
            cards,
            memory,
            no_exact_match=no_exact_match,
            visual_search_mode=visual_search_mode,
        )
        if _shopping_guide_llm_enabled():
            generation_memory = build_generation_memory(
                memory,
                cards,
                no_exact_match=no_exact_match,
                query=query,
                retrieval=retrieval.raw_result,
            )
            generation = generate_shopping_result(
                query=query,
                cards=cards,
                memory=generation_memory,
                fallback=fallback_answer,
            )
            answer = generation.content
        else:
            generation = None
            answer = fallback_answer
        trace_item = {
            "node": "shopping_guide",
            "cards": [card["product_id"] for card in cards],
            "llm_enabled": bool(generation and generation.llm_enabled),
            "provider": generation.provider if generation else "",
            "model": generation.model if generation else "",
            "provider_latency_ms": generation.latency_ms if generation else 0,
            "cost_estimate": generation.cost_estimate if generation else {},
            **retrieval.trace,
            "guide_quality": diagnosis.trace,
        }
        if generation is None:
            trace_item["speed_mode"] = "template_draft"
            trace_item["skip_reason"] = "SHOPPING_GUIDE_LLM_ENABLED=false"
        if no_exact_match:
            trace_item["fallback_reason"] = "no_exact_subcategory_budget_match"
        if generation and generation.llm_error:
            trace_item["llm_error"] = generation.llm_error
        return {
            **state,
            "constraints": constraints,
            "memory": build_turn_memory(memory, products, retrieval.raw_result),
            "retrieved_items": retrieval.retrieved_items,
            "product_cards": cards,
            "no_exact_match": no_exact_match,
            "answer": answer,
            "trace": state.get("trace", []) + [trace_item],
        }

    return node


def merge_memory(previous: dict, constraints: dict, query: str) -> dict:
    category_switched = _category_switched(previous, constraints)
    memory = (
        _memory_for_new_category()
        if category_switched
        else {field: previous.get(field) for field in MEMORY_FIELDS if field in previous}
    )
    for field in MEMORY_FIELDS:
        value = constraints.get(field)
        if value:
            if isinstance(value, list):
                merged = list(dict.fromkeys(memory.get(field, []) + value))
                memory[field] = merged
            else:
                memory[field] = value
    if constraints.get("category"):
        memory["explicit_category"] = constraints["category"]
    if constraints.get("subcategory"):
        memory["explicit_subcategory"] = constraints["subcategory"]
    memory["strict_filter"] = bool(constraints.get("strict_filter"))
    if constraints.get("category") and not constraints.get("subcategory") and (
        category_switched or _asks_for_broad_category(query)
    ):
        memory.pop("subcategory", None)
    if category_switched:
        memory.pop("last_product_ids", None)
        memory.pop("exclude_product_ids", None)
    lowered = query.lower()
    _merge_preference_aliases(memory, lowered)
    if memory.get("exclude_product_ids"):
        memory["exclude_product_ids"] = memory.get("exclude_product_ids", [])
    elif _asks_for_more_options(query):
        memory["exclude_product_ids"] = previous.get("last_product_ids", [])
    else:
        memory.pop("exclude_product_ids", None)
    return memory


def _category_switched(previous: dict, constraints: dict) -> bool:
    new_category = constraints.get("category")
    if not new_category:
        return False
    old_category = previous.get("category")
    old_subcategory = previous.get("subcategory")
    new_subcategory = constraints.get("subcategory")
    return new_category != old_category or bool(old_subcategory and old_subcategory != new_subcategory)


def _memory_for_new_category() -> dict:
    return {}


def exclude_previous_products(products: list[Product], memory: dict) -> list[Product]:
    excluded = set(memory.get("exclude_product_ids") or [])
    if not excluded:
        return products
    return [product for product in products if product.id not in excluded]


def sort_products_for_memory(products: list[Product], memory: dict, query: str = "") -> list[Product]:
    return rank_products_for_guide(products, memory, query)


def retrieve_products_for_guide(
    db: Session,
    candidates: list[Product],
    memory: dict,
    query: str,
    *,
    intent: str = "shopping_guide",
    image_path: str | None = None,
    search_service: ProductSearchService | None = None,
    orchestrator: RetrievalOrchestrator | None = None,
) -> GuideRetrieval:
    orchestrator_error: str | None = None

    if orchestrator is not None:
        try:
            result = orchestrator.search(
                db,
                query,
                intent=intent,
                memory=memory,
                image_path=image_path,
                candidates=candidates,
            )
            products = exclude_previous_products(result.products, memory)
            trace = {
                "orchestrated": True,
                "sqlite_candidates": len(candidates),
                **result.trace,
            }
            return GuideRetrieval(
                products=products,
                trace=trace,
                retrieved_items=build_retrieved_items(products, result),
                raw_result=result,
            )
        except Exception as error:
            orchestrator_error = f"{type(error).__name__}: {str(error)[:160]}"

    products, trace = hybrid_retrieve_and_rerank(
        db,
        candidates,
        memory,
        query,
        search_service=search_service,
    )
    if orchestrator_error:
        trace = {**trace, "orchestrator_error": orchestrator_error}
    return GuideRetrieval(
        products=products,
        trace=trace,
        retrieved_items=build_retrieved_items(products),
        raw_result=None,
    )


def products_to_cards(
    products: list[Product],
    memory: dict,
    retrieval: RetrievalResult | None = None,
    query: str = "",
    commercial_scores: dict[str, CommercialScore] | None = None,
) -> list[dict]:
    retrieval_meta = _retrieval_metadata_by_product_id(retrieval)
    retrieval_mode = (retrieval.trace.get("retrieval_mode") if retrieval else "") or ""
    commercial_scores = commercial_scores or {}
    cards = []
    for rank, product in enumerate(products[:3], start=1):
        card = product_to_card(product, memory, rank, query=query)
        _apply_commercial_signal(card, commercial_scores.get(product.id))
        metadata = retrieval_meta.get(product.id, {})
        if retrieval_mode:
            reason = "图片相似" if "image" in retrieval_mode else "语义匹配"
            existing_reasons = card.get("reasons", [])
            if "image" in retrieval_mode:
                card["reasons"] = list(dict.fromkeys([reason, *existing_reasons]))[:4]
            else:
                card["reasons"] = list(dict.fromkeys([*existing_reasons, reason]))[:4]
        if metadata:
            score = metadata.get("final_score") or metadata.get("image_similarity")
            if score is not None:
                try:
                    card["score"] = round(float(score), 2)
                except (TypeError, ValueError):
                    pass
            card["retrieval"] = {
                key: value
                for key, value in metadata.items()
                if key
                in {
                    "retrieval_mode",
                    "image_similarity",
                    "text_image_similarity",
                    "final_score",
                    "matched_image_id",
                    "matched_filters",
                    "retrieval_sources",
                    "score_breakdown",
                }
            }
        elif retrieval_mode:
            card["retrieval"] = {"retrieval_mode": retrieval_mode}
        cards.append(card)
    return cards


def _apply_commercial_signal(card: dict, signal: CommercialScore | None) -> None:
    if signal is None:
        return
    card["commercial_score"] = signal.total
    card["commercial_breakdown"] = signal.breakdown
    card["commercial_badges"] = signal.badges
    card["behavior_signals"] = signal.behavior
    if signal.badges:
        card["selling_points"] = list(dict.fromkeys([*card.get("selling_points", []), *signal.badges]))[:4]
    if signal.risk_points:
        card["tradeoffs"] = list(dict.fromkeys([*card.get("tradeoffs", []), *signal.risk_points]))[:4]


def build_retrieved_items(
    products: list[Product],
    retrieval: RetrievalResult | None = None,
) -> list[dict[str, Any]]:
    retrieval_meta = _retrieval_metadata_by_product_id(retrieval)
    retrieval_mode = (retrieval.trace.get("retrieval_mode") if retrieval else "") or ""
    items: list[dict[str, Any]] = []
    for product in products[:5]:
        item: dict[str, Any] = {
            "product_id": product.id,
            "title": product.title,
            "category": product.category,
            "subcategory": product.subcategory or "",
            "brand": product.brand,
            "price": product.price,
            "rating": product.rating,
            "sales": product.sales,
        }
        if retrieval_mode:
            item["retrieval_mode"] = retrieval_mode
        item.update(retrieval_meta.get(product.id, {}))
        items.append(item)
    return items


def _retrieval_metadata_by_product_id(retrieval: RetrievalResult | None) -> dict[str, dict[str, Any]]:
    if retrieval is None:
        return {}

    mode = retrieval.trace.get("retrieval_mode", "")
    metadata_by_id: dict[str, dict[str, Any]] = {}

    for item in retrieval.image_products:
        product_id = item.get("product_id")
        if not product_id:
            continue
        metadata_by_id[str(product_id)] = {
            "retrieval_mode": mode,
            "image_similarity": item.get("image_similarity"),
            "text_image_similarity": item.get("text_image_similarity"),
            "final_score": item.get("final_score"),
            "matched_image_id": item.get("matched_image_id"),
            "matched_filters": item.get("matched_filters", {}),
            "retrieval_sources": item.get("retrieval_sources", []),
            "score_breakdown": item.get("score_breakdown", {}),
        }

    for item in retrieval.image_candidates_raw:
        product_id = item.get("product_id") or item.get("metadata", {}).get("product_id")
        if not product_id:
            continue
        metadata = metadata_by_id.setdefault(str(product_id), {"retrieval_mode": mode})
        metadata.setdefault("image_similarity", item.get("image_similarity"))
        metadata.setdefault("text_image_similarity", item.get("text_image_similarity"))
        metadata.setdefault("final_score", item.get("final_score"))
        metadata.setdefault("matched_filters", item.get("matched_filters", {}))
        metadata.setdefault("retrieval_sources", item.get("retrieval_sources", []))
        metadata.setdefault("score_breakdown", item.get("score_breakdown", {}))
        if item.get("metadata", {}).get("image_id"):
            metadata["matched_image_id"] = item["metadata"]["image_id"]

    return metadata_by_id


def hybrid_retrieve_and_rerank(
    db: Session,
    candidates: list[Product],
    memory: dict,
    query: str,
    *,
    search_service: ProductSearchService | None = None,
) -> tuple[list[Product], dict]:
    if not candidates:
        return [], {"retrieval_mode": "sqlite_filter_empty", "sqlite_candidates": 0, "chroma_hits": []}

    candidate_by_id = {product.id: product for product in candidates}
    query_text = build_retrieval_query(query, memory)

    # 使用 ProductSearchService 进行向量检索
    if search_service is not None:
        try:
            hits = search_service.vector_search(
                db,
                query_text,
                limit=min(max(len(candidates), 10), 30),
                product_ids=list(candidate_by_id),
                ensure_indexed=True,
            )
        except Exception as error:
            return sort_products_for_memory(candidates, memory, query), {
                "retrieval_mode": "sqlite_filter_local_rerank",
                "sqlite_candidates": len(candidates),
                "chroma_hits": [],
                "chroma_error": f"{type(error).__name__}: {str(error)[:160]}",
            }
    else:
        # 兼容：无服务时直接创建 TextIndex
        try:
            index = TextIndex()
            index.ensure_products_indexed(db)
            hits = index.search_products(
                query_text,
                limit=min(max(len(candidates), 10), 30),
                product_ids=list(candidate_by_id),
            )
        except Exception as error:
            return sort_products_for_memory(candidates, memory, query), {
                "retrieval_mode": "sqlite_filter_local_rerank",
                "sqlite_candidates": len(candidates),
                "chroma_hits": [],
                "chroma_error": f"{type(error).__name__}: {str(error)[:160]}",
            }

    semantic_scores = {
        hit["metadata"]["product_id"]: _semantic_score(hit.get("distance"))
        for hit in hits
        if hit.get("metadata", {}).get("product_id") in candidate_by_id
    }
    ranked = sorted(
        candidates,
        key=lambda product: (
            -_hybrid_score(product, memory, query, semantic_scores),
            product.price if "性价比" in set(memory.get("preferences", [])) else 0,
            -product.rating,
            -product.sales,
        ),
    )
    return ranked, {
        "retrieval_mode": "sqlite_filter_chroma_rerank",
        "sqlite_candidates": len(candidates),
        "chroma_hits": [hit["metadata"]["product_id"] for hit in hits[:5] if hit.get("metadata")],
    }


def build_retrieval_query(query: str, memory: dict) -> str:
    parts = [
        query,
        memory.get("category") or "",
        memory.get("subcategory") or "",
        memory.get("audience") or "",
        " ".join(memory.get("use_cases", [])),
        " ".join(memory.get("preferences", [])),
    ]
    if memory.get("budget_max"):
        parts.append(f"{memory['budget_max']} 元以内")
    return " ".join(part for part in parts if part).strip()


def build_generation_memory(
    memory: dict,
    cards: list[dict],
    *,
    no_exact_match: bool,
    query: str = "",
    retrieval: RetrievalResult | None = None,
) -> dict:
    generation_memory = dict(memory)
    generation_memory["no_exact_match"] = no_exact_match
    if is_visual_retrieval(retrieval):
        generation_memory["visual_search_mode"] = True
        generation_memory["answer_policy"] = _merge_answer_policy(
            generation_memory.get("answer_policy"),
            _visual_search_answer_policy(),
        )
    if no_exact_match:
        budget = memory.get("budget_max")
        candidate_prices = [card["price"] for card in cards]
        lowest_price = min(candidate_prices) if candidate_prices else None
        gap = lowest_price - budget if budget and lowest_price else None
        generation_memory["answer_policy"] = _merge_answer_policy(
            generation_memory.get("answer_policy"),
            (
                "没有严格符合预算和子品类的商品；不能把超预算备选说成预算内推荐。"
                "请先明确说明没有精确匹配，再解释为什么展示这些同子品类备选，"
                "给出预算差距、是否值得加预算、以及如果预算不变可以怎么调整需求。"
                "不要推荐候选卡片之外的具体商品。"
            ),
        )
        generation_memory["budget_gap_min"] = gap
        generation_memory["lowest_candidate_price"] = lowest_price
    assumption_policy = _build_unstated_assumption_policy(memory, query)
    if assumption_policy:
        generation_memory["answer_policy"] = _merge_answer_policy(
            generation_memory.get("answer_policy"),
            assumption_policy,
        )
    if _is_broad_intro_query(query, memory):
        generation_memory["broad_intro_mode"] = True
    profile_policy = _build_user_profile_policy(memory)
    if profile_policy:
        generation_memory["answer_policy"] = _merge_answer_policy(
            generation_memory.get("answer_policy"),
            profile_policy,
        )
    category_policy = guide_answer_policy(memory)
    if category_policy:
        generation_memory["answer_policy"] = _merge_answer_policy(
            generation_memory.get("answer_policy"),
            category_policy,
        )
    generation_memory["answer_policy"] = _merge_answer_policy(
        generation_memory.get("answer_policy"),
        _professional_guide_answer_policy(),
    )
    return generation_memory


def _semantic_score(distance: float | None) -> float:
    if distance is None:
        return 0.0
    return 1.0 / (1.0 + max(float(distance), 0.0))


def _hybrid_score(product: Product, memory: dict, query: str, semantic_scores: dict[str, float]) -> float:
    return score_product_for_guide(
        product,
        memory,
        query,
        semantic_score=semantic_scores.get(product.id, 0.0),
    ).total


def product_to_card(product: Product, memory: dict, rank: int, query: str = "") -> dict:
    return build_product_card(product, memory, rank, query=query)


def build_recommendation_answer(
    cards: list[dict],
    memory: dict,
    *,
    no_exact_match: bool = False,
    strict_no_match: bool = False,
    visual_search_mode: bool = False,
) -> str:
    return build_guide_answer(
        cards,
        memory,
        no_exact_match=no_exact_match,
        strict_no_match=strict_no_match,
        visual_search_mode=visual_search_mode,
    )


def _shopping_guide_llm_enabled() -> bool:
    return _env_bool("SHOPPING_GUIDE_LLM_ENABLED", False)


def build_no_more_options_answer(memory: dict) -> str:
    category = memory.get("subcategory") or memory.get("category") or "这个品类"
    budget = f"{memory['budget_max']} 元以内" if memory.get("budget_max") else "当前条件下"
    focus_items = [*memory.get("use_cases", []), *memory.get("preferences", [])]
    focus = "、".join(focus_items[:2]) if focus_items else "你的核心需求"
    return (
        f"我又帮你往下找了一圈，{budget}适合你的{category}选择确实不多。"
        f"刚才给你看的那几款已经算比较稳了，再硬找的话，要么会超预算比较多，要么就不太贴合{focus}。"
        "如果你想继续扩，我建议先放宽一个条件，比如预算、品牌、规格或使用场景。"
    )


def _asks_for_broad_category(query: str) -> bool:
    lowered = query.lower()
    return any(keyword in lowered for keyword in ["都有什么", "有哪些", "电子产品", "数码产品", "全部"])


def _is_broad_intro_query(query: str, memory: dict) -> bool:
    if not (memory.get("category") or memory.get("subcategory")):
        return False
    if memory.get("budget_max") or memory.get("audience") or memory.get("use_cases") or memory.get("preferences"):
        return False
    lowered = query.lower()
    return any(
        keyword in lowered
        for keyword in [
            "介绍一下",
            "介绍下",
            "介绍",
            "了解一下",
            "了解下",
            "讲讲",
            "说说",
            "看看",
        ]
    )


def should_use_low_confidence_response(
    retrieval: GuideRetrieval,
    memory: dict[str, Any],
    cards: list[dict],
) -> bool:
    action = os.getenv("PRODUCT_SEARCH_LOW_CONFIDENCE_ACTION", "clarify").strip().lower()
    if action in {"", "off", "false", "0", "trace"}:
        return False
    if not cards:
        return False
    trace = retrieval.trace or {}
    if bool(trace.get("low_confidence")):
        return True
    if memory.get("vision_needs_clarification"):
        return True
    if is_visual_retrieval(retrieval.raw_result):
        confidence = _float_or_zero(memory.get("vision_confidence"))
        threshold = _float_env("VISION_LOW_CONFIDENCE_THRESHOLD", 0.45)
        return 0 < confidence < threshold
    return False


def build_low_confidence_answer(
    query: str,
    memory: dict[str, Any],
    cards: list[dict],
    retrieval: GuideRetrieval,
) -> str:
    category = memory.get("subcategory") or memory.get("category") or "这个需求"
    confidence = retrieval.trace.get("confidence")
    reason = "我对这次匹配的把握不够高"
    if memory.get("vision_needs_clarification"):
        reason = "这张图的主体或品类不够稳定"
    elif confidence is not None:
        reason = f"这次召回置信度只有 {confidence}"
    names = [str(card.get("title") or card.get("name") or card.get("product_id")) for card in cards[:2]]
    options = "、".join(name for name in names if name)
    suffix = f"我可以先给你看接近的候选：{options}。" if options else ""
    return (
        f"{reason}，不建议直接把它当成精准推荐。"
        f"你可以补充预算、品牌、用途，或换一张主体更清楚的图片，我再按{category}重新筛。"
        f"{suffix}"
    )


def build_turn_memory(memory: dict, products: list[Product], retrieval: RetrievalResult | None = None) -> dict:
    turn_memory = {**memory, "last_product_ids": [product.id for product in products[:3]]}
    if is_visual_retrieval(retrieval):
        turn_memory["visual_search_mode"] = True
        turn_memory["answer_policy"] = _merge_answer_policy(
            turn_memory.get("answer_policy"),
            _visual_search_answer_policy(),
        )
    return turn_memory


def is_visual_retrieval(retrieval: RetrievalResult | None) -> bool:
    if retrieval is None:
        return False
    mode = str(retrieval.trace.get("retrieval_mode", ""))
    return "image_search" in mode


def _visual_search_answer_policy() -> str:
    return (
        "本轮有上传图片或图搜结果，回答要自然说明商品是按图片外观相似度筛出来的；"
        "再结合商品卡片里的品类、价格、库存和用户文字条件做取舍。"
        "如果 memory 里有 vision_summary 或 visual_attributes，可以用“图片看起来像/更接近”来表达，"
        "但不要把图片理解结果说成绝对事实；不要说成只按文字检索，也不要编造图片中无法确认的材质、品牌或具体参数。"
        "如果 vision_quality_flags 或 vision_needs_clarification 表示图片质量不稳定，要简短说明结果是按当前可见主体推断，"
        "并引导用户换更清晰、主体更完整的图片。"
    )


def _build_unstated_assumption_policy(memory: dict, query: str) -> str:
    policy_parts: list[str] = []
    if _is_broad_intro_query(query, memory):
        policy_parts.append(
            "用户只是想了解这个品类，不要把回答开头写成已经确认了某个具体购买场景；"
            "可以先简单介绍怎么选，再结合商品卡片给当前可看选项。"
        )
    if not memory.get("budget_max"):
        policy_parts.append("用户没有明确预算，不要说用户有某个预算，也不要带入历史预算。")
    if not memory.get("audience"):
        policy_parts.append("用户没有说明人群身份，不要替用户假设任何具体身份或购买对象。")
    if not memory.get("use_cases"):
        policy_parts.append(
            "用户没有说明用途，不要说用户已经确认某个具体使用场景；"
            "商品描述里的适用场景只能写成商品本身的适合场景，或用“如果你要……”表达。"
        )
    if not memory.get("preferences"):
        policy_parts.append("用户没有说明偏好，不要替用户假设某个具体偏好。")
    return "".join(policy_parts)


def _build_user_profile_policy(memory: dict) -> str:
    profile = memory.get("user_profile")
    if not isinstance(profile, dict):
        return ""
    if not (profile.get("global") or profile.get("scoped")):
        return ""
    return (
        "可以参考 user_profile 里的长期偏好提升个性化，但本轮用户明确说出的预算、品类、用途和限制优先级最高；"
        "如果长期偏好和本轮需求冲突，必须以本轮需求为准，并且不要擅自复用其他品类的预算或场景。"
    )


def _professional_guide_answer_policy() -> str:
    return (
        "导购回复必须像专业导购：明确主推哪款、为什么最贴合用户需求、备选适合什么情况、"
        "是否有风险点或取舍，并自然给出下一步购买动作；不要只罗列参数。"
    )


def _merge_answer_policy(existing: object, addition: str) -> str:
    existing_text = str(existing or "").strip()
    if not existing_text:
        return addition
    if addition in existing_text:
        return existing_text
    return existing_text + addition


def _asks_for_more_options(query: str) -> bool:
    lowered = query.lower()
    return any(keyword in lowered for keyword in ["还有", "其他", "别的", "换一批", "换个", "再推荐", "再找"])


def _append_preference(memory: dict, value: str) -> None:
    preferences = memory.get("preferences", [])
    if value not in preferences:
        memory["preferences"] = preferences + [value]


def _merge_preference_aliases(memory: dict, lowered_query: str) -> None:
    aliases = rule_dict("guide_quality", "value_aliases")
    for value, raw_aliases in aliases.items():
        if not isinstance(raw_aliases, list):
            continue
        if any(str(alias).lower() in lowered_query for alias in raw_aliases if str(alias)):
            _append_preference(memory, str(value))


def _score_product(product: Product, memory: dict, query: str) -> float:
    text = " ".join(
        [
            product.title,
            product.category,
            product.subcategory or "",
            product.brand,
            product.description,
            product.specs_json or "",
        ]
    ).lower()
    score = 0.0

    if memory.get("category") and product.category == memory["category"]:
        score += 8

    for keyword in _query_keywords(query):
        if keyword in text:
            score += 12 if len(keyword) >= 2 else 2

    for use_case in memory.get("use_cases", []):
        normalized = use_case.lower()
        if normalized in text:
            score += 8

    for preference in memory.get("preferences", []):
        normalized = preference.lower()
        if normalized in text:
            score += 6

    if memory.get("budget_max") and product.price <= memory["budget_max"]:
        score += 2

    score += product.rating * 0.2
    score += min(product.sales, 20000) / 20000
    return score


def _query_keywords(query: str) -> list[str]:
    lowered = query.lower()
    return [keyword for keyword in _domain_keywords() if keyword.lower() in lowered]


def _float_or_zero(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _domain_keywords() -> list[str]:
    keywords: list[str] = []
    for category in load_taxonomy().get("categories", []):
        keywords.extend([category.get("name", ""), *category.get("aliases", [])])
        for subcategory in category.get("subcategories", []):
            keywords.extend([subcategory.get("name", ""), *subcategory.get("aliases", [])])
        for value_group in category.get("attributes", {}).values():
            for value, aliases in value_group.items():
                keywords.extend([value, *aliases])
    keywords.extend(str(item) for item in rule_list("guide_quality", "guide_keywords"))
    return list(dict.fromkeys(keyword for keyword in keywords if keyword))
