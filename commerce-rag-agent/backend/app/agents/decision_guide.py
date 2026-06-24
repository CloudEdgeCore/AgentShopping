from sqlalchemy.orm import Session

from app.agents.intent_router import extract_shopping_constraints
from app.agents.shopping_guide import (
    build_generation_memory,
    build_recommendation_answer,
    merge_memory,
    products_to_cards,
    retrieve_products_for_guide,
)
from app.llm.generation import generate_decision_guide_result
from app.services.business_rules import rule_section
from app.services.product_search_service import ProductSearchService
from app.services.product_service import filter_products
from app.services.retrieval_orchestrator import RetrievalOrchestrator


def decision_guide_node(
    db: Session,
    *,
    search_service: ProductSearchService | None = None,
    orchestrator: RetrievalOrchestrator | None = None,
):
    def node(state: dict) -> dict:
        query = state["query"]
        constraints = extract_shopping_constraints(query).model_dump()
        memory = merge_memory(state.get("memory", {}), constraints, query)
        products = filter_products(
            db,
            category=memory.get("category"),
            subcategory=memory.get("subcategory"),
            budget_max=memory.get("budget_max"),
        )
        retrieval = retrieve_products_for_guide(
            db,
            products,
            memory,
            query,
            intent=state.get("intent", "decision_guide"),
            image_path=state.get("image_path"),
            search_service=search_service,
            orchestrator=orchestrator,
        )
        products = retrieval.products
        cards = products_to_cards(products, memory, retrieval.raw_result)
        fallback_answer = build_decision_fallback(cards, memory)
        generation_memory = build_generation_memory(memory, cards, no_exact_match=False)
        generation_memory["decision_mode"] = "open_ended_purchase"
        generation_memory["answer_policy"] = _decision_text("answer_policy")
        generation = generate_decision_guide_result(
            query=query,
            cards=cards,
            memory=generation_memory,
            fallback=fallback_answer,
        )
        trace_item = {
            "node": "decision_guide",
            "cards": [card["product_id"] for card in cards],
            "llm_enabled": generation.llm_enabled,
            "provider": generation.provider,
            "model": generation.model,
            "provider_latency_ms": generation.latency_ms,
            "cost_estimate": generation.cost_estimate or {},
            **retrieval.trace,
        }
        if generation.llm_error:
            trace_item["llm_error"] = generation.llm_error
        return {
            **state,
            "constraints": constraints,
            "memory": {**memory, "last_product_ids": [product.id for product in products[:3]]},
            "retrieved_items": retrieval.retrieved_items,
            "product_cards": cards,
            "answer": generation.content,
            "trace": state.get("trace", []) + [trace_item],
        }

    return node


def build_decision_fallback(cards: list[dict], memory: dict) -> str:
    subcategory = memory.get("subcategory") or memory.get("category") or "商品"
    if not cards:
        return _decision_text("empty_fallback_template").format(category=subcategory)
    first = cards[0]
    return _decision_text("default_fallback_template").format(
        category=subcategory,
        title=first["title"],
        price=first["price"],
    )


def _decision_text(key: str) -> str:
    return str(rule_section("decision_guide", key) or "")
