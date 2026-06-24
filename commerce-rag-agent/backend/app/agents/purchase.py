import re
from typing import Any

from sqlalchemy.orm import Session

from app.agents import commerce_nlu as nlu
from app.agents.dialogue_state import clear_transient_dialogue, parse_quantity, parse_quantity_delta
from app.agents.intent_router import extract_shopping_constraints
from app.agents.shopping_guide import product_to_card
from app.models.tables import Product
from app.services.cart_service import (
    CommerceError,
    add_cart_item,
    cancel_checkout,
    confirm_checkout,
    list_cart,
    preview_cart_checkout,
    preview_direct_checkout,
    remove_cart_item,
    revise_checkout_quantity,
    set_checkout_quantity,
    update_checkout_address,
    update_cart_item,
)
from app.services.price_alert_service import PriceAlertError, create_price_alert
from app.services.product_service import find_products_by_query, get_products_by_ids


def purchase_help_node(db: Session):
    def node(state: dict) -> dict:
        query = state["query"]
        memory = dict(state.get("memory", {}))
        constraints = extract_shopping_constraints(query).model_dump()
        action = str(memory.get("dialogue_action") or parse_purchase_action(query))

        try:
            if action == "confirm_checkout":
                return _confirm_checkout_state(db, state, memory)
            if action == "cancel_checkout":
                return _cancel_checkout_state(db, state, memory)
            if action == "adjust_checkout_quantity":
                return _adjust_checkout_quantity_state(db, state, memory)
            if action == "set_checkout_quantity":
                return _set_checkout_quantity_state(db, state, memory)
            if action == "update_checkout_address":
                return _update_checkout_address_state(db, state, memory)
            if action == "view_cart":
                return _cart_state(db, state, memory)
            if action == "remove_from_cart":
                return _remove_from_cart_state(db, state, memory, constraints)
            if action == "update_cart_quantity":
                return _update_cart_quantity_state(db, state, memory, query, constraints)
            if action == "adjust_cart_quantity":
                return _adjust_cart_quantity_state(db, state, memory, query, constraints)
            if action == "checkout":
                return _checkout_state(db, state, memory, query, constraints)
            if action == "add_to_cart":
                return _add_to_cart_state(db, state, memory, query, constraints)
            if action == "create_price_alert":
                return _create_price_alert_state(db, state, memory, query, constraints)
            return _purchase_help_state(db, state, memory, query, constraints)
        except (CommerceError, PriceAlertError) as exc:
            return {
                **state,
                "constraints": constraints,
                "memory": memory,
                "retrieved_items": [],
                "product_cards": [],
                "answer": str(exc),
                "trace": state.get("trace", []) + [{"node": "purchase_help", "action": action, "error": str(exc)}],
            }

    return node


def parse_purchase_action(query: str) -> str:
    return nlu.parse_command(query).action


def parse_target_price(query: str) -> int | None:
    match = re.search(r"(?:降到|低于|不超过|到|目标价|目标价格)\s*(\d{2,6})\s*(?:元|块)?", query)
    if match:
        return int(match.group(1))
    return None


def _current_user_id(memory: dict) -> str:
    user_id = str(memory.get("user_id") or "").strip()
    if not user_id:
        raise CommerceError("请先登录后再操作购物车、结算或价格提醒。")
    return user_id


def _add_to_cart_state(
    db: Session,
    state: dict,
    memory: dict,
    query: str,
    constraints: dict,
) -> dict:
    user_id = _current_user_id(memory)
    quantity = int(memory.get("dialogue_quantity") or parse_quantity(query))
    products = resolve_referenced_products(
        db,
        query=query,
        memory=memory,
        constraints=constraints,
        target_product_ids=memory.get("dialogue_target_product_ids") or None,
    )
    if not products:
        return _need_product_state(state, memory, constraints, "你想把哪一款加入购物车？可以说“把第一款加入购物车”。")

    added_items = []
    for product in products:
        added_items.append(add_cart_item(db, product_id=product.id, quantity=quantity, user_id=user_id, query=query))
    cart = list_cart(db, user_id=user_id)
    cards = [product_to_card(product, memory, rank) for rank, product in enumerate(products[:3], start=1)]
    answer = build_cart_added_answer(added_items, cart)
    return {
        **state,
        "constraints": constraints,
        "memory": clear_transient_dialogue({
            **memory,
            "last_product_ids": _merge_recent_product_ids(
                [product.id for product in products[:3]],
                memory.get("last_product_ids", []),
            ),
            "cart_item_ids": [item["cart_item_id"] for item in cart["items"]],
            "dialogue_state": "cart_ready",
        }),
        "retrieved_items": [{"product_id": product.id, "title": product.title} for product in products],
        "product_cards": cards,
        "cart_state": cart,
        "answer": answer,
        "trace": state.get("trace", []) + [
            {
                "node": "purchase_help",
                "action": "add_to_cart",
                "cart_item_ids": [item["cart_item_id"] for item in added_items],
            }
        ],
    }


def _cart_state(db: Session, state: dict, memory: dict) -> dict:
    user_id = _current_user_id(memory)
    cart = list_cart(db, user_id=user_id)
    return {
        **state,
        "memory": clear_transient_dialogue({
            **memory,
            "cart_item_ids": [item["cart_item_id"] for item in cart["items"]],
            "dialogue_state": "cart_ready" if cart["items"] else "idle",
        }),
        "retrieved_items": cart["items"],
        "product_cards": [],
        "cart_state": cart,
        "answer": build_cart_summary_answer(cart),
        "trace": state.get("trace", []) + [{"node": "purchase_help", "action": "view_cart"}],
    }


def _remove_from_cart_state(db: Session, state: dict, memory: dict, constraints: dict) -> dict:
    user_id = _current_user_id(memory)
    cart = list_cart(db, user_id=user_id)
    target_ids = resolve_referenced_cart_items(memory, cart)
    if not target_ids:
        return _need_cart_item_state(
            state,
            memory,
            constraints,
            "你想删除购物车里的哪一项？可以说“删除第二个商品”。",
            cart,
        )

    removed_items = [remove_cart_item(db, cart_item_id=cart_item_id, user_id=user_id) for cart_item_id in target_ids]
    updated_cart = list_cart(db, user_id=user_id)
    answer = build_cart_removed_answer(removed_items, updated_cart)
    return {
        **state,
        "constraints": constraints,
        "memory": clear_transient_dialogue({
            **memory,
            "cart_item_ids": [item["cart_item_id"] for item in updated_cart["items"]],
            "dialogue_state": "cart_ready" if updated_cart["items"] else "idle",
        }),
        "retrieved_items": updated_cart["items"],
        "product_cards": [],
        "cart_state": updated_cart,
        "answer": answer,
        "trace": state.get("trace", []) + [
            {
                "node": "purchase_help",
                "action": "remove_from_cart",
                "cart_item_ids": target_ids,
            }
        ],
    }


def _update_cart_quantity_state(
    db: Session,
    state: dict,
    memory: dict,
    query: str,
    constraints: dict,
) -> dict:
    user_id = _current_user_id(memory)
    cart = list_cart(db, user_id=user_id)
    target_ids = resolve_referenced_cart_items(memory, cart)
    if not target_ids:
        return _need_cart_item_state(
            state,
            memory,
            constraints,
            "你想修改购物车里的哪一项数量？可以说“把第二个商品数量改成 2”。",
            cart,
        )

    quantity = int(memory.get("dialogue_set_quantity") or parse_quantity(query))
    updated_items = [
        update_cart_item(db, cart_item_id=cart_item_id, quantity=quantity, user_id=user_id)
        for cart_item_id in target_ids
    ]
    updated_cart = list_cart(db, user_id=user_id)
    answer = build_cart_quantity_updated_answer(updated_items, updated_cart)
    return {
        **state,
        "constraints": constraints,
        "memory": clear_transient_dialogue({
            **memory,
            "cart_item_ids": [item["cart_item_id"] for item in updated_cart["items"]],
            "dialogue_state": "cart_ready" if updated_cart["items"] else "idle",
        }),
        "retrieved_items": updated_cart["items"],
        "product_cards": [],
        "cart_state": updated_cart,
        "answer": answer,
        "trace": state.get("trace", []) + [
            {
                "node": "purchase_help",
                "action": "update_cart_quantity",
                "cart_item_ids": target_ids,
                "quantity": quantity,
            }
        ],
    }


def _adjust_cart_quantity_state(
    db: Session,
    state: dict,
    memory: dict,
    query: str,
    constraints: dict,
) -> dict:
    user_id = _current_user_id(memory)
    cart = list_cart(db, user_id=user_id)
    target_ids = resolve_referenced_cart_items(memory, cart)
    if not target_ids:
        return _need_cart_item_state(
            state,
            memory,
            constraints,
            "你想调整购物车里的哪一项数量？可以说“第二个加一件”或“第一个少一件”。",
            cart,
        )

    quantity_delta = int(memory.get("dialogue_quantity_delta") or parse_quantity_delta(query))
    if not quantity_delta:
        return _need_cart_item_state(
            state,
            memory,
            constraints,
            "你想把数量加几件或减几件？可以说“第二个加一件”。",
            cart,
        )

    item_by_id = {str(item["cart_item_id"]): item for item in cart["items"]}
    updated_items = []
    for cart_item_id in target_ids:
        current_quantity = int(item_by_id.get(cart_item_id, {}).get("quantity") or 1)
        updated_items.append(
            update_cart_item(
                db,
                cart_item_id=cart_item_id,
                quantity=max(current_quantity + quantity_delta, 1),
                user_id=user_id,
            )
        )
    updated_cart = list_cart(db, user_id=user_id)
    answer = build_cart_quantity_updated_answer(updated_items, updated_cart)
    return {
        **state,
        "constraints": constraints,
        "memory": clear_transient_dialogue({
            **memory,
            "cart_item_ids": [item["cart_item_id"] for item in updated_cart["items"]],
            "dialogue_state": "cart_ready" if updated_cart["items"] else "idle",
        }),
        "retrieved_items": updated_cart["items"],
        "product_cards": [],
        "cart_state": updated_cart,
        "answer": answer,
        "trace": state.get("trace", []) + [
            {
                "node": "purchase_help",
                "action": "adjust_cart_quantity",
                "cart_item_ids": target_ids,
                "quantity_delta": quantity_delta,
            }
        ],
    }


def _checkout_state(
    db: Session,
    state: dict,
    memory: dict,
    query: str,
    constraints: dict,
) -> dict:
    user_id = _current_user_id(memory)
    quantity = int(memory.get("dialogue_quantity") or parse_quantity(query))
    products = resolve_referenced_products(
        db,
        query=query,
        memory=memory,
        constraints=constraints,
        target_product_ids=memory.get("dialogue_target_product_ids") or None,
    )
    if products:
        checkout = preview_direct_checkout(
            db,
            product_items=[{"product_id": product.id, "quantity": quantity} for product in products],
            user_id=user_id,
            query=query,
        )
    else:
        checkout = preview_cart_checkout(db, user_id=user_id)

    product_ids = [str(item["product_id"]) for item in checkout["items"]]
    products_for_cards = get_products_by_ids(db, product_ids[:3])
    cards = [product_to_card(product, memory, rank) for rank, product in enumerate(products_for_cards, start=1)]
    answer = build_checkout_preview_answer(checkout)
    return {
        **state,
        "constraints": constraints,
        "memory": clear_transient_dialogue({
            **memory,
            "pending_checkout_id": checkout["checkout_id"],
            "pending_checkout_token": checkout["confirm_token"],
            "last_product_ids": _merge_recent_product_ids(product_ids[:3], memory.get("last_product_ids", [])),
            "dialogue_state": "awaiting_checkout_confirmation",
        }),
        "retrieved_items": checkout["items"],
        "product_cards": cards,
        "cart_state": list_cart(db, user_id=user_id),
        "answer": answer,
        "trace": state.get("trace", []) + [
            {
                "node": "purchase_help",
                "action": "checkout_preview",
                "checkout_id": checkout["checkout_id"],
                "payable_amount": checkout["payable_amount"],
            }
        ],
    }


def _create_price_alert_state(
    db: Session,
    state: dict,
    memory: dict,
    query: str,
    constraints: dict,
) -> dict:
    user_id = _current_user_id(memory)
    products = resolve_referenced_products(
        db,
        query=query,
        memory=memory,
        constraints=constraints,
        target_product_ids=memory.get("dialogue_target_product_ids") or None,
    )
    if not products:
        return _need_product_state(state, memory, constraints, "你想给哪一款设置提醒？可以说“这款降到 1500 提醒我”。")

    target_price = int(constraints.get("budget_max") or parse_target_price(query) or 0)
    if target_price <= 0:
        target_price = max(int(products[0].price * 0.95), 1)
    alert_type = "stock_restock" if _contains_any(query, ["到货提醒", "有货提醒", "补货提醒"]) else "price_drop"
    alerts = [
        create_price_alert(
            db,
            user_id=user_id,
            product_id=product.id,
            target_price=target_price,
            alert_type=alert_type,
        )
        for product in products[:3]
    ]
    cards = [product_to_card(product, memory, rank) for rank, product in enumerate(products[:3], start=1)]
    return {
        **state,
        "constraints": constraints,
        "memory": clear_transient_dialogue({
            **memory,
            "last_product_ids": [product.id for product in products[:3]],
            "dialogue_state": "alert_created",
        }),
        "retrieved_items": alerts,
        "product_cards": cards,
        "answer": build_price_alert_answer(alerts, alert_type=alert_type),
        "trace": state.get("trace", []) + [
            {
                "node": "purchase_help",
                "action": "create_price_alert",
                "alert_ids": [alert["id"] for alert in alerts],
            }
        ],
    }


def _confirm_checkout_state(db: Session, state: dict, memory: dict) -> dict:
    user_id = _current_user_id(memory)
    checkout_id = str(memory.get("pending_checkout_id") or "")
    confirm_token = str(memory.get("pending_checkout_token") or "")
    if not checkout_id or not confirm_token:
        return {
            **state,
            "memory": memory,
            "retrieved_items": [],
            "product_cards": [],
            "answer": "我还没有可确认的结算单。你可以先说“结算购物车”或“就买第一款”，我会先生成下单确认。",
            "trace": state.get("trace", []) + [{"node": "purchase_help", "action": "confirm_checkout", "status": "missing_checkout"}],
        }
    order = confirm_checkout(
        db,
        checkout_id=checkout_id,
        confirm_token=confirm_token,
        user_id=user_id,
        idempotency_key=f"agent:{checkout_id}",
    )
    next_memory = clear_transient_dialogue(memory)
    next_memory.pop("pending_checkout_id", None)
    next_memory.pop("pending_checkout_token", None)
    next_memory["last_order_id"] = order["order_id"]
    next_memory["dialogue_state"] = "order_created"
    return {
        **state,
        "memory": next_memory,
        "retrieved_items": [{"order_id": order["order_id"], "status": order["status"]}],
        "product_cards": [],
        "cart_state": list_cart(db, user_id=user_id),
        "answer": build_order_created_answer(order),
        "trace": state.get("trace", []) + [
            {"node": "purchase_help", "action": "confirm_checkout", "order_id": order["order_id"]}
        ],
    }


def _cancel_checkout_state(db: Session, state: dict, memory: dict) -> dict:
    user_id = _current_user_id(memory)
    checkout_id = str(memory.get("pending_checkout_id") or "")
    next_memory = clear_transient_dialogue(memory)
    next_memory.pop("pending_checkout_id", None)
    next_memory.pop("pending_checkout_token", None)
    next_memory["dialogue_state"] = "idle"
    if checkout_id:
        cancel_checkout(db, checkout_id=checkout_id, user_id=user_id)
    return {
        **state,
        "memory": next_memory,
        "retrieved_items": [],
        "product_cards": [],
        "cart_state": list_cart(db, user_id=user_id),
        "answer": "好的，这次下单确认已取消，我不会创建订单。你可以继续挑别的商品，或稍后再结算。",
        "trace": state.get("trace", []) + [
            {"node": "purchase_help", "action": "cancel_checkout", "checkout_id": checkout_id}
        ],
    }


def _adjust_checkout_quantity_state(db: Session, state: dict, memory: dict) -> dict:
    user_id = _current_user_id(memory)
    checkout_id = str(memory.get("pending_checkout_id") or "")
    quantity_delta = int(memory.get("dialogue_quantity_delta") or 0)
    if not checkout_id or not quantity_delta:
        return {
            **state,
            "memory": clear_transient_dialogue(memory),
            "retrieved_items": [],
            "product_cards": [],
            "answer": "我还没有可调整的结算单。你可以先说“就买第一款”，我会先生成下单确认。",
            "trace": state.get("trace", []) + [{"node": "purchase_help", "action": "adjust_checkout_quantity", "status": "missing_checkout"}],
        }
    checkout = revise_checkout_quantity(
        db,
        checkout_id=checkout_id,
        quantity_delta=quantity_delta,
        product_ids=memory.get("dialogue_target_product_ids") or None,
        user_id=user_id,
    )
    product_ids = [str(item["product_id"]) for item in checkout["items"]]
    products_for_cards = get_products_by_ids(db, product_ids[:3])
    cards = [product_to_card(product, memory, rank) for rank, product in enumerate(products_for_cards, start=1)]
    return {
        **state,
        "memory": clear_transient_dialogue({
            **memory,
            "pending_checkout_id": checkout["checkout_id"],
            "pending_checkout_token": checkout["confirm_token"],
            "last_product_ids": product_ids[:3],
            "dialogue_state": "awaiting_checkout_confirmation",
        }),
        "retrieved_items": checkout["items"],
        "product_cards": cards,
        "cart_state": list_cart(db, user_id=user_id),
        "answer": "数量已更新。" + build_checkout_preview_answer(checkout),
        "trace": state.get("trace", []) + [
            {
                "node": "purchase_help",
                "action": "adjust_checkout_quantity",
                "checkout_id": checkout["checkout_id"],
                "quantity_delta": quantity_delta,
            }
        ],
    }


def _set_checkout_quantity_state(db: Session, state: dict, memory: dict) -> dict:
    user_id = _current_user_id(memory)
    checkout_id = str(memory.get("pending_checkout_id") or "")
    quantity = int(memory.get("dialogue_set_quantity") or 0)
    if not checkout_id or not quantity:
        return {
            **state,
            "memory": clear_transient_dialogue(memory),
            "retrieved_items": [],
            "product_cards": [],
            "answer": "我还没有可修改数量的结算单。你可以先说“就买第一款”，我会先生成下单确认。",
            "trace": state.get("trace", []) + [{"node": "purchase_help", "action": "set_checkout_quantity", "status": "missing_checkout"}],
        }
    checkout = set_checkout_quantity(
        db,
        checkout_id=checkout_id,
        quantity=quantity,
        product_ids=memory.get("dialogue_target_product_ids") or None,
        user_id=user_id,
    )
    product_ids = [str(item["product_id"]) for item in checkout["items"]]
    products_for_cards = get_products_by_ids(db, product_ids[:3])
    cards = [product_to_card(product, memory, rank) for rank, product in enumerate(products_for_cards, start=1)]
    return {
        **state,
        "memory": clear_transient_dialogue({
            **memory,
            "pending_checkout_id": checkout["checkout_id"],
            "pending_checkout_token": checkout["confirm_token"],
            "last_product_ids": product_ids[:3],
            "dialogue_state": "awaiting_checkout_confirmation",
        }),
        "retrieved_items": checkout["items"],
        "product_cards": cards,
        "cart_state": list_cart(db, user_id=user_id),
        "answer": "数量已更新。" + build_checkout_preview_answer(checkout),
        "trace": state.get("trace", []) + [
            {
                "node": "purchase_help",
                "action": "set_checkout_quantity",
                "checkout_id": checkout["checkout_id"],
                "quantity": quantity,
            }
        ],
    }


def _update_checkout_address_state(db: Session, state: dict, memory: dict) -> dict:
    user_id = _current_user_id(memory)
    checkout_id = str(memory.get("pending_checkout_id") or "")
    address_id = str(memory.get("dialogue_address_id") or "").strip()
    if not checkout_id:
        return {
            **state,
            "memory": clear_transient_dialogue(memory),
            "retrieved_items": [],
            "product_cards": [],
            "answer": "我还没有可修改地址的结算单。你可以先说“就买第一款”，我会先生成下单确认。",
            "trace": state.get("trace", []) + [{"node": "purchase_help", "action": "update_checkout_address", "status": "missing_checkout"}],
        }
    if not address_id:
        return {
            **state,
            "memory": memory,
            "retrieved_items": [],
            "product_cards": [],
            "answer": "你想把收货地址改成哪个？可以说“地址改成公司”。",
            "trace": state.get("trace", []) + [{"node": "purchase_help", "action": "update_checkout_address", "status": "missing_address"}],
        }
    checkout = update_checkout_address(db, checkout_id=checkout_id, address_id=address_id, user_id=user_id)
    product_ids = [str(item["product_id"]) for item in checkout["items"]]
    products_for_cards = get_products_by_ids(db, product_ids[:3])
    cards = [product_to_card(product, memory, rank) for rank, product in enumerate(products_for_cards, start=1)]
    return {
        **state,
        "memory": clear_transient_dialogue({
            **memory,
            "pending_checkout_id": checkout["checkout_id"],
            "pending_checkout_token": checkout["confirm_token"],
            "last_product_ids": product_ids[:3],
            "dialogue_state": "awaiting_checkout_confirmation",
        }),
        "retrieved_items": checkout["items"],
        "product_cards": cards,
        "cart_state": list_cart(db, user_id=user_id),
        "answer": "收货地址已更新。" + build_checkout_preview_answer(checkout),
        "trace": state.get("trace", []) + [
            {
                "node": "purchase_help",
                "action": "update_checkout_address",
                "checkout_id": checkout["checkout_id"],
                "address_id": checkout["address_id"],
            }
        ],
    }


def _purchase_help_state(
    db: Session,
    state: dict,
    memory: dict,
    query: str,
    constraints: dict,
) -> dict:
    products = resolve_referenced_products(db, query=query, memory=memory, constraints=constraints)
    cards = [product_to_card(product, memory, rank) for rank, product in enumerate(products[:3], start=1)]
    return {
        **state,
        "constraints": constraints,
        "memory": clear_transient_dialogue({
            **memory,
            "last_product_ids": [product.id for product in products[:3]] or memory.get("last_product_ids", []),
        }),
        "retrieved_items": [{"product_id": product.id, "title": product.title} for product in products],
        "product_cards": cards,
        "answer": build_purchase_answer(products),
        "trace": state.get("trace", []) + [{"node": "purchase_help", "action": "help"}],
    }


def _need_product_state(state: dict, memory: dict, constraints: dict, answer: str) -> dict:
    return {
        **state,
        "constraints": constraints,
        "memory": clear_transient_dialogue(memory),
        "retrieved_items": [],
        "product_cards": [],
        "answer": answer,
        "trace": state.get("trace", []) + [{"node": "purchase_help", "status": "need_product"}],
    }


def _need_cart_item_state(state: dict, memory: dict, constraints: dict, answer: str, cart: dict[str, Any]) -> dict:
    return {
        **state,
        "constraints": constraints,
        "memory": clear_transient_dialogue({
            **memory,
            "cart_item_ids": [item["cart_item_id"] for item in cart["items"]],
            "dialogue_state": "cart_ready" if cart["items"] else "idle",
        }),
        "retrieved_items": cart["items"],
        "product_cards": [],
        "cart_state": cart,
        "answer": answer if cart["items"] else "购物车现在是空的，暂时没有可操作的商品。",
        "trace": state.get("trace", []) + [{"node": "purchase_help", "status": "need_cart_item"}],
    }


def resolve_referenced_cart_items(memory: dict, cart: dict[str, Any]) -> list[str]:
    cart_items = cart.get("items") or []
    existing_ids = [str(item.get("cart_item_id") or "") for item in cart_items if item.get("cart_item_id")]
    requested = [str(item) for item in memory.get("dialogue_target_cart_item_ids", []) if item]
    if requested:
        return [item_id for item_id in requested if item_id in existing_ids]
    remembered = [str(item) for item in memory.get("cart_item_ids", []) if item]
    if len(existing_ids) == 1 and remembered:
        return existing_ids[:1]
    return []


def resolve_referenced_products(
    db: Session,
    *,
    query: str,
    memory: dict,
    constraints: dict,
    target_product_ids: list[str] | None = None,
) -> list[Product]:
    if target_product_ids:
        return get_products_by_ids(db, [str(product_id) for product_id in target_product_ids])

    product_ids = constraints.get("product_ids") or []
    if product_ids:
        return get_products_by_ids(db, product_ids)

    remembered_ids = list(memory.get("last_product_ids") or [])
    referenced = _ordinal_product_ids(query, remembered_ids)
    if referenced:
        return get_products_by_ids(db, referenced)

    if not _is_generic_purchase_text(query):
        products = find_products_by_query(db, query, limit=3)
        if products:
            return products

    if len(remembered_ids) == 1 and _contains_any(query, ["这款", "这个", "它", "买", "加入购物车", "加购"]):
        return get_products_by_ids(db, remembered_ids)
    return []


def build_cart_added_answer(items: list[dict[str, Any]], cart: dict[str, Any]) -> str:
    lines = []
    for item in items:
        spec_text = format_specs(item.get("specs") or {})
        lines.append(f"{item['title']}{spec_text} × {item['quantity']}")
    return (
        "已加入购物车："
        + "；".join(lines)
        + f"。当前购物车共 {cart['total_quantity']} 件商品，小计 {cart['subtotal_amount']} 元。"
        + "你可以继续说“结算购物车”，我会先生成下单确认。"
    )


def build_cart_summary_answer(cart: dict[str, Any]) -> str:
    if not cart["items"]:
        return "购物车现在是空的。你可以先让我要推荐商品，再说“把第一款加入购物车”。"
    lines = [
        f"{index}. {item['title']}{format_specs(item.get('specs') or {})} × {item['quantity']}，小计 {item['subtotal_amount']} 元"
        for index, item in enumerate(cart["items"], start=1)
    ]
    return (
        "购物车里有："
        + "；".join(lines)
        + f"。合计 {cart['subtotal_amount']} 元。确认要买的话，可以说“结算购物车”。"
    )


def build_cart_removed_answer(items: list[dict[str, Any]], cart: dict[str, Any]) -> str:
    names = "、".join(item["title"] for item in items)
    if not cart["items"]:
        return f"已从购物车删除：{names}。现在购物车是空的。"
    return (
        f"已从购物车删除：{names}。"
        f"当前购物车还剩 {cart['total_quantity']} 件商品，小计 {cart['subtotal_amount']} 元。"
        "如果要继续下单，可以说“结算购物车”。"
    )


def build_cart_quantity_updated_answer(items: list[dict[str, Any]], cart: dict[str, Any]) -> str:
    lines = [
        f"{item['title']}{format_specs(item.get('specs') or {})} 数量已改为 {item['quantity']}，小计 {item['subtotal_amount']} 元"
        for item in items
    ]
    return (
        "已更新购物车："
        + "；".join(lines)
        + f"。当前购物车共 {cart['total_quantity']} 件商品，合计 {cart['subtotal_amount']} 元。"
        + "确认要买的话，可以说“结算购物车”。"
    )


def build_checkout_preview_answer(checkout: dict[str, Any]) -> str:
    item_lines = [
        f"{item['title']}{format_specs(item.get('specs') or {})} × {item['quantity']}，{item['subtotal_amount']} 元"
        for item in checkout["items"]
    ]
    return (
        "我已经生成下单确认："
        + "；".join(item_lines)
        + f"。商品小计 {checkout['subtotal_amount']} 元，运费 {checkout['shipping_fee']} 元，预计实付 {checkout['payable_amount']} 元。"
        + f"默认地址：{checkout['address_id']}。如果确认无误，回复“确认下单”或“确认”，我再创建待支付订单。"
    )


def build_price_alert_answer(alerts: list[dict[str, Any]], *, alert_type: str) -> str:
    if not alerts:
        return "我还没有成功创建提醒。"
    if alert_type == "stock_restock":
        titles = "、".join(alert["product_title"] for alert in alerts[:3])
        return f"已给 {titles} 创建到货提醒。后续可以通过提醒列表检查是否触发。"
    first = alerts[0]
    if len(alerts) == 1:
        return (
            f"已给 {first['product_title']} 创建价格提醒：目标价 {first['target_price']} 元，"
            f"当前价 {first['current_price']} 元。"
        )
    return f"已给 {len(alerts)} 款商品创建价格提醒，目标价 {first['target_price']} 元。"


def build_order_created_answer(order: dict[str, Any]) -> str:
    return (
        f"订单已创建：{order['order_id']}，当前状态是{order['status']}，预计实付 {order['payable_amount']} 元。"
        f"支付入口：{order['payment_url']}。你也可以继续问“订单 {order['order_id']} 物流到哪了”。"
    )


def build_purchase_answer(products: list[Product]) -> str:
    if not products:
        return (
            "可以通过对话完成加购和生成待支付订单。你可以先说“把第一款加入购物车”，"
            "也可以说“就买第一款”，我会先给你下单确认，等你回复“确认下单”或“确认”后再创建订单。"
        )

    names = "、".join(product.title for product in products[:3])
    return (
        f"可以购买。当前可操作的商品包括：{names}。"
        "你可以说“把第一款加入购物车”，或者“就买第一款”。"
        "直接购买时我会先给出价格、规格、数量和地址确认，只有你回复“确认下单”或“确认”才会创建待支付订单。"
    )


def _merge_recent_product_ids(primary: list[Any], remembered: Any, *, limit: int = 6) -> list[str]:
    values = [*primary]
    if isinstance(remembered, list):
        values.extend(remembered)
    merged: list[str] = []
    seen: set[str] = set()
    for value in values:
        product_id = str(value or "").strip()
        if product_id and product_id not in seen:
            merged.append(product_id)
            seen.add(product_id)
        if len(merged) >= limit:
            break
    return merged


def format_specs(specs: dict[str, Any]) -> str:
    if not specs:
        return ""
    text = " / ".join(str(value) for value in specs.values() if value)
    return f"（{text}）" if text else ""


def _ordinal_product_ids(query: str, remembered_ids: list[str]) -> list[str]:
    if not remembered_ids:
        return []
    indices = nlu.resolve_target_indices(query, len(remembered_ids))
    if indices:
        return [remembered_ids[index] for index in indices[:3]]
    if nlu.is_deictic_selection(query) or nlu.is_implicit_selection(query):
        return [remembered_ids[0]]
    return []


def _is_generic_purchase_text(query: str) -> bool:
    return nlu.is_purchase_intent(query)


def _is_cart_add_text(text: str) -> bool:
    return nlu.is_cart_add_request(text)


def _is_cart_set_quantity_text(text: str) -> bool:
    return nlu.is_cart_set_quantity_request(text)


def _is_cart_adjust_quantity_text(text: str) -> bool:
    return nlu.parse_quantity_delta(text) != 0


def _contains_any(text: str, keywords: list[str]) -> bool:
    return nlu.contains_any(text, keywords)
