from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from app.agents.chitchat import chitchat_node
from app.agents.compare import compare_node
from app.agents.decision_guide import decision_guide_node
from app.agents.dialogue_state import apply_dialogue_state
from app.agents.faq import faq_node
from app.agents.intent_router import classify_intent
from app.agents.order import order_node
from app.agents.product_knowledge import product_knowledge_node
from app.agents.purchase import purchase_help_node
from app.agents.shopping_guide import merge_memory, shopping_guide_node
from app.agents.state import AgentState
from app.agents.supervisor import build_supervisor_trace
from app.llm.generation import _build_default_client
from app.services.product_search_service import ProductSearchService
from app.services.retrieval_orchestrator import RetrievalOrchestrator


def router_node(state: AgentState) -> AgentState:
    result = classify_intent(state["query"])
    intent = result.intent
    constraints = result.constraints.model_dump()
    memory = merge_memory(state.get("memory", {}), constraints, state["query"])
    dialogue = apply_dialogue_state(state["query"], memory, intent)
    intent = dialogue.intent
    memory = dialogue.memory
    if not dialogue.handled and memory.get("last_product_ids") and _is_product_followup_query(state["query"]):
        intent = "product_knowledge"
    # 商品详情页：强制切换到产品知识模式
    if memory.get("product_id") and intent in {"chitchat", "clarification", "shopping_guide"}:
        intent = "product_knowledge"
        if not memory.get("last_product_ids"):
            memory["last_product_ids"] = [memory["product_id"]]
    if state.get("image_path") and intent in {"chitchat", "clarification", "decision_guide"}:
        intent = "shopping_guide"
    if intent == "clarification" and memory.get("category"):
        intent = "shopping_guide"
    if intent == "clarification" and len(memory.get("last_product_ids", [])) >= 2:
        intent = "compare"
    supervisor_trace = build_supervisor_trace(
        query=state["query"],
        intent=intent,
        memory=memory,
        has_image=bool(state.get("image_path")),
    )
    return {
        **state,
        "intent": intent,
        "constraints": constraints,
        "memory": memory,
        "trace": state.get("trace", [])
        + ([dialogue.trace] if dialogue.trace else [])
        + [supervisor_trace]
        + [{"node": "intent_router", "intent": intent, "confidence": result.confidence}],
    }


def route_by_intent(state: AgentState) -> str:
    intent = state.get("intent")
    if intent == "decision_guide":
        return "decision_guide"
    if intent == "shopping_guide":
        return "shopping_guide"
    if intent == "product_knowledge":
        return "product_knowledge"
    if intent == "compare":
        return "compare"
    if intent == "order_query":
        return "order"
    if intent == "purchase_help":
        return "purchase_help"
    if intent == "faq":
        return "faq"
    if intent == "clarification":
        return "clarification"
    return "chitchat"


def clarification_node(state: AgentState) -> AgentState:
    return {
        **state,
        "answer": "我需要再确认一下：你想要推荐商品、对比商品、查询订单，还是了解某个商品参数？",
        "product_cards": [],
        "retrieved_items": [],
        "trace": state.get("trace", []) + [{"node": "clarification"}],
    }


def create_agent_graph(
    db: Session,
    *,
    chroma_path: str | None = None,
    search_service: ProductSearchService | None = None,
    orchestrator: RetrievalOrchestrator | None = None,
):
    search_service = search_service or ProductSearchService(chroma_path=chroma_path)
    orchestrator = orchestrator or RetrievalOrchestrator(chroma_path=chroma_path)
    graph = StateGraph(AgentState)
    graph.add_node("intent_router", router_node)
    graph.add_node("decision_guide", decision_guide_node(db, search_service=search_service, orchestrator=orchestrator))
    graph.add_node("shopping_guide", shopping_guide_node(db, search_service=search_service, orchestrator=orchestrator))
    graph.add_node("product_knowledge", product_knowledge_node(db, orchestrator=orchestrator))
    graph.add_node("compare", compare_node(db, orchestrator=orchestrator))
    graph.add_node("order", order_node(db))
    graph.add_node("purchase_help", purchase_help_node(db))
    graph.add_node("faq", faq_node(chroma_path=chroma_path))
    graph.add_node("clarification", clarification_node)
    try:
        chitchat_client = _build_default_client()
    except Exception:
        chitchat_client = None
    graph.add_node("chitchat", chitchat_node(client=chitchat_client))
    graph.set_entry_point("intent_router")
    graph.add_conditional_edges(
        "intent_router",
        route_by_intent,
        {
            "decision_guide": "decision_guide",
            "shopping_guide": "shopping_guide",
            "product_knowledge": "product_knowledge",
            "compare": "compare",
            "order": "order",
            "purchase_help": "purchase_help",
            "faq": "faq",
            "clarification": "clarification",
            "chitchat": "chitchat",
        },
    )
    graph.add_edge("decision_guide", END)
    graph.add_edge("shopping_guide", END)
    graph.add_edge("product_knowledge", END)
    graph.add_edge("compare", END)
    graph.add_edge("order", END)
    graph.add_edge("purchase_help", END)
    graph.add_edge("faq", END)
    graph.add_edge("clarification", END)
    graph.add_edge("chitchat", END)
    return graph.compile()


def run_agent(
    db: Session,
    query: str,
    *,
    memory: dict | None = None,
    image_path: str | None = None,
    chroma_path: str | None = None,
    search_service: ProductSearchService | None = None,
    orchestrator: RetrievalOrchestrator | None = None,
) -> AgentState:
    app = create_agent_graph(db, chroma_path=chroma_path, search_service=search_service, orchestrator=orchestrator)
    state = {
        "query": query,
        "messages": [{"role": "user", "content": query}],
        "memory": memory or {},
        "trace": [],
    }
    if image_path:
        state["image_path"] = image_path
    return app.invoke(state)


def _is_product_followup_query(query: str) -> bool:
    return any(
        keyword in query
        for keyword in [
            "这款",
            "这个",
            "这两个",
            "这两款",
            "这几个",
            "它",
            "它们",
            "评价",
            "评论",
            "口碑",
            "反馈",
            "体验",
            "怎么样",
            "好不好",
            "值得买吗",
            "值得买",
        ]
    )
