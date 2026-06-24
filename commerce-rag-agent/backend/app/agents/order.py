from sqlalchemy.orm import Session
import json

from app.services.order_service import find_order, seed_orders
from app.services.product_service import get_products_by_ids


def order_node(db: Session):
    def node(state: dict) -> dict:
        user_id = str((state.get("memory") or {}).get("user_id") or "").strip()
        if not user_id:
            return {
                **state,
                "answer": "请先登录后再查询订单。",
                "product_cards": [],
                "retrieved_items": [],
                "trace": state.get("trace", []) + [{"node": "order_query", "status": "missing_user"}],
            }
        seed_orders(db, user_id=user_id)
        order = find_order(db, state["query"], user_id=user_id)
        if not order:
            return {
                **state,
                "answer": "我没有找到你的订单。请补充订单号，例如 ord_1001。",
                "product_cards": [],
                "retrieved_items": [],
                "trace": state.get("trace", []) + [{"node": "order_query", "status": "not_found"}],
            }

        product_text = order_items_text(order)
        if not product_text:
            products = get_products_by_ids(db, [order.product_id])
            product = products[0] if products else None
            product_text = f"商品：{product.title}。" if product else ""
        answer = (
            f"订单 {order.id} 当前状态：{order.status}。{product_text}"
            f"{f'实付：{order.payable_amount} 元。' if order.payable_amount else ''}"
            f"物流：{_trim_period(order.logistics_status) or '暂无物流更新'}。"
            f"退货：{_trim_period(order.return_status) or '暂无退货记录'}。"
        )
        return {
            **state,
            "retrieved_items": [{"order_id": order.id, "product_id": order.product_id, "status": order.status}],
            "product_cards": [],
            "answer": answer,
            "trace": state.get("trace", []) + [{"node": "order_query", "order_id": order.id}],
        }

    return node


def _trim_period(value: str) -> str:
    return (value or "").rstrip("。.")


def order_items_text(order) -> str:
    try:
        items = json.loads(order.items_json or "[]")
    except json.JSONDecodeError:
        return ""
    if not items:
        return ""
    item_text = "；".join(
        f"{item.get('title', '')} × {item.get('quantity', 1)}"
        for item in items
        if item.get("title")
    )
    return f"商品：{item_text}。" if item_text else ""
