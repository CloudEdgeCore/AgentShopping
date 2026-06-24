from typing import Any


def build_order_guidance(result: dict[str, Any]) -> dict[str, Any]:
    memory = result.get("memory") if isinstance(result.get("memory"), dict) else {}
    cards = result.get("product_cards") if isinstance(result.get("product_cards"), list) else []
    intent = str(result.get("intent") or "")
    no_exact_match = bool(result.get("no_exact_match"))

    if memory.get("pending_checkout_id") and memory.get("pending_checkout_token"):
        return {
            "stage": "awaiting_checkout_confirmation",
            "title": "确认下单",
            "primary_action": "确认",
            "secondary_actions": ["加一件", "算了"],
            "note": "只有你确认后才会创建待支付订单。",
        }

    if memory.get("cart_item_ids") or memory.get("dialogue_state") == "cart_ready":
        return {
            "stage": "cart_ready",
            "title": "购物车已准备好",
            "primary_action": "结算购物车",
            "secondary_actions": ["查看购物车", "继续推荐同类商品"],
            "note": "结算前我会先展示商品、数量、地址和实付金额。",
        }

    if not cards:
        return {}

    if no_exact_match:
        return {
            "stage": "needs_refine_before_checkout",
            "title": "先收窄条件",
            "primary_action": "放宽预算再找",
            "secondary_actions": ["只看现货", "换个相邻品类"],
            "note": "当前结果不是严格命中条件，建议先确认是否接受再下单。",
        }

    first_card = cards[0]
    target_price = _suggest_alert_price(first_card)
    secondary = ["把第一款加入购物车"]
    if len(cards) >= 2:
        secondary.extend(["对比这几款", "这几款评价怎么样"])
    else:
        secondary.append("看看这款评价")
    if target_price:
        secondary.append(f"这款降到 {target_price} 提醒我")

    return {
        "stage": "recommendation_ready",
        "title": "可以继续下单",
        "primary_action": "就买第一款",
        "secondary_actions": secondary,
        "note": "直接购买会先生成确认单，你回复“确认”后才会创建待支付订单。",
        "product_id": first_card.get("product_id"),
        "intent": intent,
    }


def append_order_guidance(answer: str, result: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    guidance = build_order_guidance(result)
    if not guidance:
        return answer, {}
    if str(result.get("intent") or "") == "purchase_help":
        return answer, guidance
    if guidance["stage"] != "recommendation_ready":
        return answer, guidance
    if guidance["primary_action"] in answer and ("确认" in answer or "确认单" in answer or "下单" in answer):
        return answer, guidance
    guided_answer = (
        answer.rstrip()
        + "\n\n"
        + f"下一步：如果你准备下单，可以说“{guidance['primary_action']}”；"
        + guidance["note"]
    )
    return guided_answer, guidance


def _suggest_alert_price(card: dict[str, Any]) -> int | None:
    try:
        price = int(card.get("price") or 0)
    except (TypeError, ValueError):
        return None
    if price <= 0:
        return None
    return max(int(price * 0.95), 1)
