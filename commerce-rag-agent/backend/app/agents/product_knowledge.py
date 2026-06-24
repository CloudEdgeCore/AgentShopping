import json
import re

from sqlalchemy.orm import Session

from app.agents.intent_router import extract_shopping_constraints
from app.agents.shopping_guide import build_retrieved_items, merge_memory, product_to_card, products_to_cards
from app.services.business_rules import rule_list
from app.services.product_service import find_products_by_query, get_product_knowledge_docs, get_product_tags, get_products_by_ids
from app.services.review_insight_service import build_review_insight, render_review_insights, review_insight_payload
from app.services.retrieval_orchestrator import RetrievalOrchestrator


def product_knowledge_node(db: Session, *, orchestrator: RetrievalOrchestrator | None = None):
    def node(state: dict) -> dict:
        query = state["query"]
        constraints = extract_shopping_constraints(query).model_dump()
        memory = merge_memory(state.get("memory", {}), constraints, query)
        retrieval_result = None
        retrieval_trace = {}
        memory_product_ids = memory.get("last_product_ids", [])[:3]
        products = get_products_by_ids(db, memory_product_ids) if is_followup_product_question(query) else []
        if not products and orchestrator is not None:
            try:
                retrieval_result = orchestrator.search(
                    db,
                    query,
                    intent="product_knowledge",
                    memory=memory,
                    image_path=state.get("image_path"),
                    candidates=None,
                )
                products = retrieval_result.products[:3]
                retrieval_trace = {"orchestrated": True, **retrieval_result.trace}
            except Exception as error:
                retrieval_trace = {"orchestrator_error": f"{type(error).__name__}: {str(error)[:160]}"}
        if not products:
            products = find_products_by_query(db, query, limit=3)
        if not products:
            products = get_products_by_ids(db, memory_product_ids)
        if not products:
            return {
                **state,
                "answer": "我还没定位到你问的是哪一款商品，可以补充商品名、商品 ID，或者先让我推荐几款候选。",
                "product_cards": [],
                "retrieved_items": [],
                "trace": state.get("trace", []) + [{"node": "product_knowledge", "status": "need_product"}],
            }

        if is_review_question(query):
            docs_by_product = {product.id: get_product_knowledge_docs(db, product.id, limit=12) for product in products[:4]}
            insights = [
                build_review_insight(product, docs_by_product.get(product.id, []), query=query, memory=memory)
                for product in products[:4]
            ]
            answer = build_product_review_answer(
                products[:4],
                docs_by_product,
                query=query,
                memory=memory,
                insights=insights,
            )
            cards = (
                products_to_cards(products[:4], memory, retrieval_result)
                if retrieval_result is not None
                else [product_to_card(item, memory, rank) for rank, item in enumerate(products[:4], start=1)]
            )
            memory = {**memory, "last_product_ids": [product.id for product in products[:4]]}
            product_items = (
                build_retrieved_items(products[:4], retrieval_result)
                if retrieval_result is not None
                else [{"product_id": item.id, "title": item.title, "source": "products"} for item in products[:4]]
            )
            retrieved_docs = [
                {"id": doc["id"], "text": doc["text"], "source": "documents", "metadata": doc["metadata"]}
                for docs in docs_by_product.values()
                for doc in docs
                if is_review_doc(doc)
            ]
            insight_items = [
                {"id": f"review_insight:{insight.product_id}", "source": "review_insights", **review_insight_payload(insight)}
                for insight in insights
            ]
            return {
                **state,
                "memory": memory,
                "retrieved_items": product_items + insight_items + retrieved_docs,
                "product_cards": cards,
                "answer": answer,
                "trace": state.get("trace", []) + [
                    {
                        "node": "product_knowledge",
                        "products": [product.id for product in products[:4]],
                        "sources": ["products", "documents"],
                        "doc_hits": {
                            product_id: [doc["id"] for doc in docs if is_review_doc(doc)]
                            for product_id, docs in docs_by_product.items()
                        },
                        **retrieval_trace,
                    }
                ],
            }

        product = products[0]
        specs = _safe_json(product.specs_json)
        tags = get_product_tags(db, product.id)
        docs = get_product_knowledge_docs(db, product.id, limit=8)
        answer = build_product_knowledge_answer(product, specs, tags, docs, query=query)
        cards = (
            products_to_cards(products, memory, retrieval_result)
            if retrieval_result is not None
            else [product_to_card(item, memory, rank) for rank, item in enumerate(products, start=1)]
        )
        memory = {**memory, "last_product_ids": [product.id for product in products]}
        product_items = (
            build_retrieved_items(products, retrieval_result)
            if retrieval_result is not None
            else [{"product_id": item.id, "title": item.title, "source": "products"} for item in products]
        )
        if product_items:
            product_items[0]["metadata"] = {"specs": specs, "tags": [tag.value for tag in tags]}
        retrieved_docs = [
            {"id": doc["id"], "text": doc["text"], "source": "documents", "metadata": doc["metadata"]}
            for doc in docs
        ]
        return {
            **state,
            "memory": memory,
            "retrieved_items": product_items + retrieved_docs,
            "product_cards": cards,
            "answer": answer,
            "trace": state.get("trace", []) + [
                {
                    "node": "product_knowledge",
                    "product_id": product.id,
                    "sources": ["products", "product_tags", "documents"],
                    "doc_hits": [doc["id"] for doc in docs],
                    **retrieval_trace,
                }
            ],
        }

    return node


def build_product_knowledge_answer(product, specs: dict, tags: list, docs: list[dict], *, query: str) -> str:
    spec_text = "、".join(f"{key}: {value}" for key, value in specs.items()) if specs else "暂无结构化参数"
    tag_text = "、".join(tag.value for tag in tags[:6]) if tags else "暂无标签"
    doc_text = select_relevant_doc_text(query, docs)
    return (
        f"{product.title} 的核心信息如下：价格 {product.price} 元，评分 {product.rating}，库存 {product.stock}。"
        f"商品说明：{product.description} 参数：{spec_text}。相关标签：{tag_text}。"
        f"{doc_text}"
    )


def build_product_review_answer(
    products: list,
    docs_by_product: dict[str, list[dict]],
    *,
    query: str,
    memory: dict | None = None,
    insights: list | None = None,
) -> str:
    focus = _review_focus(query, memory or {})
    if insights is not None:
        return render_review_insights(insights, focus=focus)
    if focus:
        lines = [f"这几款我看到了用户评价，重点按{focus}来看："]
    else:
        lines = ["这几款我看到了用户评价，先按好评点和差评点帮你判断："]
    scored: list[tuple[float, object]] = []

    for product in products:
        review_docs = [doc for doc in docs_by_product.get(product.id, []) if is_review_doc(doc)]
        review_text = " ".join(doc.get("text", "") for doc in review_docs)
        ratings = _extract_review_ratings(review_text)
        if ratings:
            avg_rating = round(sum(ratings) / len(ratings), 1)
            scored.append((avg_rating, product))
            rating_text = f"用户评价里约 {avg_rating} 星"
        else:
            rating_text = f"商品评分 {product.rating}"
        summary = _review_summary(review_text)
        if not summary:
            summary = "我这边没有检索到足够具体的用户评价内容，只能先参考商品评分和基础信息。"
        lines.append(f"{product.title}：{rating_text}。{summary}")

    if len(scored) >= 2:
        best = max(scored, key=lambda item: (item[0], item[1].rating, -item[1].price))[1]
        if focus:
            lines.append(f"如果主要看{focus}，我会优先让你看 {best.title}；另一款可以作为备选，但下单前建议重点看差评里提到的具体风险。")
        else:
            lines.append(f"只按当前评价信息看，我会优先让你看 {best.title}；另一款可以作为备选，但下单前建议重点看差评里反复出现的问题。")
    elif products:
        lines.append(f"如果只看当前评价信息，我会先围绕 {products[0].title} 再确认差评点是否能接受。")

    return "\n".join(lines[:4])


def is_review_doc(doc: dict) -> bool:
    return "用户评价" in str(doc.get("text", ""))


def is_review_question(query: str) -> bool:
    return any(keyword in query for keyword in ["评价", "评论", "口碑", "反馈", "体验", "好不好", "怎么样"])


def _review_focus(query: str, memory: dict) -> str:
    focus_items = []
    focus_items.extend(str(item) for item in memory.get("use_cases", []) if item)
    focus_items.extend(str(item) for item in memory.get("preferences", []) if item and item not in focus_items)
    if not focus_items:
        focus_items.extend(keyword for keyword in _product_knowledge_keywords("review_focus_fallback_keywords") if keyword in query)
    if not focus_items:
        return ""
    return "、".join(list(dict.fromkeys(focus_items))[:3])


def _extract_review_ratings(text: str) -> list[int]:
    return [int(match) for match in re.findall(r"[（(]([1-5])星[）)]", text)]


def _review_summary(text: str) -> str:
    if not text:
        return ""
    compact = re.sub(r"\s+", " ", text.replace("\n", " ")).strip()
    if "用户评价：" in compact:
        compact = compact.split("用户评价：", 1)[1].strip()
    compact = re.sub(r"商品ID：\S+", "", compact).strip()
    if len(compact) <= 220:
        return compact
    return compact[:220].rstrip("，。；、 ") + "..."


def select_relevant_doc_text(query: str, docs: list[dict]) -> str:
    if not docs:
        return ""
    lowered = query.lower()
    scored = []
    for doc in docs:
        text = doc.get("text", "")
        score = sum(1 for keyword in _product_knowledge_keywords("doc_match_keywords") if keyword.lower() in lowered and keyword in text)
        score += sum(1 for char in set(lowered) if char.strip() and char in text) / 100
        scored.append((score, text))
    selected = [text for _, text in sorted(scored, key=lambda item: item[0], reverse=True)[:2] if text]
    if not selected:
        return ""
    snippets = " ".join(text.replace("\n", " ")[:220] for text in selected)
    return f" 知识库补充：{snippets}"


def _product_knowledge_keywords(key: str) -> list[str]:
    return [str(item) for item in rule_list("product_knowledge", key)]


def is_followup_product_question(query: str) -> bool:
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
            "该商品",
            "怎么用",
            "如何使用",
            "用法",
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


def _safe_json(value: str) -> dict:
    try:
        parsed = json.loads(value or "{}")
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}
