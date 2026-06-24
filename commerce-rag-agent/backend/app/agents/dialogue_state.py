from dataclasses import dataclass
from typing import Any

from app.agents import commerce_nlu as nlu


TRANSIENT_DIALOGUE_FIELDS = [
    "dialogue_action",
    "dialogue_target_product_ids",
    "dialogue_target_cart_item_ids",
    "dialogue_quantity",
    "dialogue_set_quantity",
    "dialogue_quantity_delta",
    "dialogue_target_price",
    "dialogue_address_id",
    "dialogue_message",
]

PERSISTENT_DIALOGUE_FIELDS = [
    "dialogue_state",
]


@dataclass
class DialogueTransition:
    intent: str
    memory: dict[str, Any]
    trace: dict[str, Any] | None = None
    action: str = ""
    handled: bool = False


def apply_dialogue_state(query: str, memory: dict[str, Any], intent: str) -> DialogueTransition:
    next_memory = clear_transient_dialogue(memory)
    normalized = normalize_reply(query)
    last_product_ids = [str(item) for item in next_memory.get("last_product_ids", []) if item]
    cart_item_ids = [str(item) for item in next_memory.get("cart_item_ids", []) if item]

    if has_pending_checkout(next_memory):
        next_memory["dialogue_state"] = "awaiting_checkout_confirmation"
        transition = _pending_checkout_transition(query, normalized, next_memory)
        if transition:
            return transition
    elif next_memory.get("dialogue_state") == "awaiting_checkout_confirmation":
        next_memory.pop("dialogue_state", None)

    transition = _cart_management_transition(query, normalized, next_memory, cart_item_ids)
    if transition:
        return transition

    transition = _recommendation_transition(query, normalized, next_memory, intent, last_product_ids)
    if transition:
        return transition

    return DialogueTransition(intent=intent, memory=next_memory)


def clear_transient_dialogue(memory: dict[str, Any]) -> dict[str, Any]:
    next_memory = dict(memory or {})
    for field in TRANSIENT_DIALOGUE_FIELDS:
        next_memory.pop(field, None)
    return next_memory


def is_checkout_confirmation_reply(query: str) -> bool:
    return nlu.is_checkout_confirmation_reply(query)


def has_pending_checkout(memory: dict[str, Any]) -> bool:
    return bool(memory.get("pending_checkout_id") and memory.get("pending_checkout_token"))


def normalize_reply(query: str) -> str:
    return nlu.normalize_text(query)


def parse_quantity(query: str) -> int:
    return nlu.parse_quantity(query)


def parse_quantity_delta(query: str) -> int:
    return nlu.parse_quantity_delta(query)


def parse_set_quantity(query: str) -> int | None:
    return nlu.parse_set_quantity(query)


def parse_address_id(query: str) -> str:
    return nlu.parse_address_id(query)


def _pending_checkout_transition(
    query: str,
    normalized: str,
    memory: dict[str, Any],
) -> DialogueTransition | None:
    if _is_cancel_reply(normalized):
        next_memory = _with_action(memory, "cancel_checkout")
        return _transition("purchase_help", next_memory, action="cancel_checkout", state="awaiting_checkout_confirmation")

    address_id = parse_address_id(query)
    looks_like_quantity_change = parse_set_quantity(query) is not None or bool(parse_quantity_delta(query))
    if (_is_address_update_request(normalized) or address_id) and not looks_like_quantity_change:
        next_memory = _with_action(memory, "update_checkout_address", address_id=address_id)
        return _transition("purchase_help", next_memory, action="update_checkout_address", state="awaiting_checkout_confirmation")

    if is_checkout_confirmation_reply(query):
        next_memory = _with_action(memory, "confirm_checkout")
        return _transition("purchase_help", next_memory, action="confirm_checkout", state="awaiting_checkout_confirmation")

    set_quantity = parse_set_quantity(query)
    if set_quantity is not None:
        target_ids = resolve_product_targets(query, memory.get("last_product_ids", []))
        next_memory = _with_action(
            memory,
            "set_checkout_quantity",
            target_product_ids=target_ids,
            set_quantity=set_quantity,
        )
        return _transition(
            "purchase_help",
            next_memory,
            action="set_checkout_quantity",
            state="awaiting_checkout_confirmation",
        )

    quantity_delta = parse_quantity_delta(query)
    if quantity_delta:
        target_ids = resolve_product_targets(query, memory.get("last_product_ids", []))
        next_memory = _with_action(
            memory,
            "adjust_checkout_quantity",
            target_product_ids=target_ids,
            quantity_delta=quantity_delta,
        )
        return _transition(
            "purchase_help",
            next_memory,
            action="adjust_checkout_quantity",
            state="awaiting_checkout_confirmation",
        )

    return None


def _cart_management_transition(
    query: str,
    normalized: str,
    memory: dict[str, Any],
    cart_item_ids: list[str],
) -> DialogueTransition | None:
    if not cart_item_ids:
        return None

    if _is_cart_clear_request(normalized):
        next_memory = _with_action(memory, "remove_from_cart", target_cart_item_ids=cart_item_ids)
        return _transition("purchase_help", next_memory, action="remove_from_cart", state="cart_ready")

    if _is_cart_remove_request(normalized):
        target_ids = resolve_cart_item_targets(query, cart_item_ids)
        next_memory = _with_action(memory, "remove_from_cart", target_cart_item_ids=target_ids)
        return _transition("purchase_help", next_memory, action="remove_from_cart", state="cart_ready")

    quantity = parse_set_quantity(query)
    if quantity is not None:
        target_ids = resolve_cart_item_targets(query, cart_item_ids)
        next_memory = _with_action(
            memory,
            "update_cart_quantity",
            target_cart_item_ids=target_ids,
            set_quantity=quantity,
        )
        return _transition("purchase_help", next_memory, action="update_cart_quantity", state="cart_ready")

    quantity_delta = parse_quantity_delta(query)
    if quantity_delta:
        target_ids = resolve_cart_item_targets(query, cart_item_ids)
        next_memory = _with_action(
            memory,
            "adjust_cart_quantity",
            target_cart_item_ids=target_ids,
            quantity_delta=quantity_delta,
        )
        return _transition("purchase_help", next_memory, action="adjust_cart_quantity", state="cart_ready")

    return None


def _recommendation_transition(
    query: str,
    normalized: str,
    memory: dict[str, Any],
    intent: str,
    last_product_ids: list[str],
) -> DialogueTransition | None:
    if not last_product_ids:
        return None

    target_ids = resolve_product_targets(query, last_product_ids)
    if _is_exclude_request(normalized):
        excluded = target_ids or last_product_ids[:1]
        next_memory = dict(memory)
        next_memory["exclude_product_ids"] = _unique([*next_memory.get("exclude_product_ids", []), *excluded])
        next_memory["dialogue_state"] = "refining_recommendation"
        return _transition("shopping_guide", next_memory, action="exclude_products", state="refining_recommendation")

    if _is_more_or_switch_request(normalized):
        excluded = target_ids or last_product_ids[:1]
        next_memory = dict(memory)
        next_memory["exclude_product_ids"] = _unique([*next_memory.get("exclude_product_ids", []), *excluded])
        next_memory["dialogue_state"] = "refining_recommendation"
        return _transition("shopping_guide", next_memory, action="switch_options", state="refining_recommendation")

    if _is_cheaper_request(normalized):
        next_memory = dict(memory)
        preferences = [str(item) for item in next_memory.get("preferences", []) if item]
        if "性价比" not in preferences:
            preferences.append("性价比")
        next_memory["preferences"] = preferences
        next_memory["dialogue_state"] = "refining_recommendation"
        return _transition("shopping_guide", next_memory, action="cheaper_options", state="refining_recommendation")

    if _is_all_selection(normalized):
        action = "add_to_cart" if _is_cart_add_request(normalized) else "checkout"
        next_memory = _with_action(memory, action, target_product_ids=last_product_ids[:3], quantity=parse_quantity(query))
        return _transition("purchase_help", next_memory, action=action, state="acting_on_recommendation")

    if _is_cart_add_request(normalized):
        next_memory = _with_action(memory, "add_to_cart", target_product_ids=target_ids or last_product_ids[:1], quantity=parse_quantity(query))
        return _transition("purchase_help", next_memory, action="add_to_cart", state="acting_on_recommendation")

    if _is_purchase_selection(normalized) and (target_ids or _has_deictic_selection(normalized) or nlu.is_implicit_selection(normalized)):
        next_memory = _with_action(memory, "checkout", target_product_ids=target_ids or last_product_ids[:1], quantity=parse_quantity(query))
        return _transition("purchase_help", next_memory, action="checkout", state="acting_on_recommendation")

    if _is_price_alert_request(normalized):
        next_memory = _with_action(memory, "create_price_alert", target_product_ids=target_ids or last_product_ids[:1])
        return _transition("purchase_help", next_memory, action="create_price_alert", state="acting_on_recommendation")

    quantity_delta = parse_quantity_delta(query)
    if quantity_delta > 0 and _has_deictic_selection(normalized):
        next_memory = _with_action(memory, "add_to_cart", target_product_ids=target_ids or last_product_ids[:1], quantity=quantity_delta)
        return _transition("purchase_help", next_memory, action="add_to_cart", state="acting_on_recommendation")

    return None


def resolve_product_targets(query: str, product_ids: list[str]) -> list[str]:
    remembered_ids = [str(item) for item in product_ids if item]
    if not remembered_ids:
        return []
    normalized = normalize_reply(query)
    if _is_all_selection(normalized):
        return remembered_ids[:3]

    indices = nlu.resolve_target_indices(query, len(remembered_ids))
    if indices:
        return [remembered_ids[index] for index in indices[:3]]
    if _has_deictic_selection(normalized) or nlu.is_implicit_selection(normalized):
        return remembered_ids[:1]
    return []


def resolve_cart_item_targets(query: str, cart_item_ids: list[str]) -> list[str]:
    remembered_ids = [str(item) for item in cart_item_ids if item]
    if not remembered_ids:
        return []
    normalized = normalize_reply(query)
    indices = nlu.resolve_target_indices(query, len(remembered_ids), cart=True)
    if indices:
        return [remembered_ids[index] for index in indices]
    if len(remembered_ids) == 1:
        return [remembered_ids[0]]
    return []


def _with_action(
    memory: dict[str, Any],
    action: str,
    *,
    target_product_ids: list[str] | None = None,
    target_cart_item_ids: list[str] | None = None,
    quantity: int | None = None,
    set_quantity: int | None = None,
    quantity_delta: int | None = None,
    address_id: str | None = None,
) -> dict[str, Any]:
    next_memory = dict(memory)
    next_memory["dialogue_action"] = action
    next_memory["dialogue_state"] = "acting_on_recommendation"
    if target_product_ids:
        next_memory["dialogue_target_product_ids"] = _unique(target_product_ids)
    if target_cart_item_ids:
        next_memory["dialogue_target_cart_item_ids"] = _unique(target_cart_item_ids)
    if quantity is not None:
        next_memory["dialogue_quantity"] = max(int(quantity), 1)
    if set_quantity is not None:
        next_memory["dialogue_set_quantity"] = max(int(set_quantity), 1)
    if quantity_delta is not None:
        next_memory["dialogue_quantity_delta"] = int(quantity_delta)
    if address_id:
        next_memory["dialogue_address_id"] = address_id
    return next_memory


def _transition(intent: str, memory: dict[str, Any], *, action: str, state: str) -> DialogueTransition:
    return DialogueTransition(
        intent=intent,
        memory=memory,
        action=action,
        handled=True,
        trace={"node": "dialogue_state", "state": state, "action": action},
    )


def _is_cancel_reply(normalized: str) -> bool:
    return nlu.is_cancel_reply(normalized)


def _is_exclude_request(normalized: str) -> bool:
    return nlu.is_exclude_request(normalized)


def _is_more_or_switch_request(normalized: str) -> bool:
    return nlu.is_more_or_switch_request(normalized)


def _is_cheaper_request(normalized: str) -> bool:
    return nlu.is_cheaper_request(normalized)


def _is_all_selection(normalized: str) -> bool:
    return nlu.is_all_selection(normalized)


def _is_cart_add_request(normalized: str) -> bool:
    return nlu.is_cart_add_request(normalized)


def _is_cart_remove_request(normalized: str) -> bool:
    return nlu.is_cart_remove_request(normalized)


def _is_cart_clear_request(normalized: str) -> bool:
    return nlu.is_cart_clear_request(normalized)


def _is_address_update_request(normalized: str) -> bool:
    return nlu.is_address_update_request(normalized)


def _normalize_address_label(value: str) -> str:
    return nlu.normalize_address_label(value)


def _is_purchase_selection(normalized: str) -> bool:
    return nlu.is_purchase_selection(normalized)


def _is_price_alert_request(normalized: str) -> bool:
    return nlu.is_price_alert_request(normalized)


def _has_deictic_selection(normalized: str) -> bool:
    return nlu.is_deictic_selection(normalized)


def _contains_any(text: str, keywords: list[str]) -> bool:
    return nlu.contains_any(text, keywords)


def _unique(values: list[Any]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if value))
