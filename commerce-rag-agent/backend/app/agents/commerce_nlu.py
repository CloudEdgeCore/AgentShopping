import json
import os
import re
from dataclasses import dataclass
from typing import Any

from app.llm.openai_compatible_client import OpenAICompatibleClient
from app.services.business_rules import rule_dict, rule_list


QUANTITY_UNITS = "件个台份支瓶套盒包"
CHINESE_DIGITS = {
    "零": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "俩": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}

DEFAULT_ADDRESS_ALIASES = {
    "公司地址": "公司",
    "公司收货": "公司",
    "寄公司": "公司",
    "送公司": "公司",
    "发公司": "公司",
    "到公司": "公司",
    "走公司": "公司",
    "家里地址": "家里",
    "家里收货": "家里",
    "寄家里": "家里",
    "送家里": "家里",
    "发家里": "家里",
    "到家里": "家里",
    "走家里": "家里",
    "学校地址": "学校",
    "学校收货": "学校",
    "寄学校": "学校",
    "送学校": "学校",
    "发学校": "学校",
    "到学校": "学校",
    "默认地址": "addr_default",
}

DEFAULT_LLM_ACTIONS = {
    "add_to_cart",
    "remove_from_cart",
    "update_cart_quantity",
    "adjust_cart_quantity",
    "checkout",
    "confirm_checkout",
    "cancel_checkout",
    "update_checkout_address",
    "view_cart",
    "create_price_alert",
    "help",
}


@dataclass(frozen=True)
class CommerceCommand:
    action: str
    confidence: float
    quantity: int = 1
    set_quantity: int | None = None
    quantity_delta: int = 0
    address_id: str = ""


def normalize_text(query: str) -> str:
    lowered = _to_half_width(query or "").strip().lower()
    return re.sub(r"[\s，。！？!?,.;；：“”\"'、~～]+", "", lowered)


def contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def configured_phrases(action: str, group: str, defaults: list[str] | tuple[str, ...] = ()) -> list[str]:
    configured = [str(item) for item in rule_list("nlu", "commands", action, group) if item]
    normalized = [normalize_text(item) for item in [*configured, *defaults] if item]
    return list(dict.fromkeys(item for item in normalized if item))


def contains_configured(text: str, action: str, group: str, defaults: list[str] | tuple[str, ...] = ()) -> bool:
    return contains_any(normalize_text(text), configured_phrases(action, group, defaults))


def exact_configured(text: str, action: str, group: str, defaults: list[str] | tuple[str, ...] = ()) -> bool:
    return normalize_text(text) in set(configured_phrases(action, group, defaults))


def _configured_address_aliases() -> dict[str, str]:
    aliases = {normalize_text(key): value for key, value in DEFAULT_ADDRESS_ALIASES.items()}
    for key, value in rule_dict("nlu", "address_aliases").items():
        if key and value:
            aliases[normalize_text(str(key))] = str(value)
    return aliases


def parse_quantity(query: str) -> int:
    text = normalize_text(query)
    for pattern in [
        rf"(?<!第)(\d{{1,2}})\s*[{QUANTITY_UNITS}]",
        rf"(?<!第)([一二两俩三四五六七八九十])\s*[{QUANTITY_UNITS}]",
        rf"(?:来|拿|要|买|加|添|补|减|少|改成|改为|改到|调成|调到|设为|设置为)(\d{{1,2}})",
        rf"(?:来|拿|要|买|加|添|补|减|少|改成|改为|改到|调成|调到|设为|设置为)([一二两俩三四五六七八九十])",
    ]:
        match = re.search(pattern, text)
        if match:
            return max(_number_value(match.group(1)), 1)
    return 1


def parse_quantity_delta(query: str) -> int:
    text = normalize_text(query)
    negative_patterns = configured_phrases("adjust_quantity", "negative", [
        "少",
        "减",
        "减掉",
        "去掉一",
        "不要那么多",
        "少拿",
        "少买",
    ])
    positive_patterns = configured_phrases("adjust_quantity", "positive", [
        "加一",
        "加多",
        "再来",
        "再加",
        "多来",
        "多加",
        "添",
        "补",
    ])
    if is_cart_add_request(text) and not contains_any(text, [*positive_patterns, *negative_patterns]):
        return 0
    if contains_any(text, negative_patterns):
        return -parse_quantity(query)
    if contains_any(text, positive_patterns):
        return parse_quantity(query)
    return 0


def parse_set_quantity(query: str) -> int | None:
    text = normalize_text(query)
    if not is_cart_set_quantity_request(text):
        return None
    return parse_quantity(query)


def parse_address_id(query: str) -> str:
    text = normalize_text(query)
    if not text or contains_any(text, ["地址没问题", "地址无误", "信息无误", "确认"]):
        return ""
    aliases = _configured_address_aliases()
    if text in aliases:
        return aliases[text]
    patterns = [
        r"(?:收货地址|地址)(?:改成|改为|换成|用|设为|设置为)([\w\-\u4e00-\u9fff]{1,40})",
        r"(?:改成|改为|换成|用|寄到|寄|送到|送|发到|发|到|走)([\w\-\u4e00-\u9fff]{1,40})(?:收货地址|地址|收货)?",
        r"([\w\-\u4e00-\u9fff]{1,40})(?:收货地址|地址|收货)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return normalize_address_label(match.group(1))
    return ""


def normalize_address_label(value: str) -> str:
    label = (value or "").strip()
    for suffix in ["收货地址", "地址", "收货"]:
        if label.endswith(suffix) and len(label) > len(suffix):
            label = label[: -len(suffix)]
    return label.strip()


def parse_command(query: str) -> CommerceCommand:
    text = normalize_text(query)
    if is_checkout_confirmation_reply(text):
        return CommerceCommand("confirm_checkout", 0.94)
    if is_cancel_reply(text):
        return CommerceCommand("cancel_checkout", 0.92)
    if is_address_update_request(text):
        return CommerceCommand("update_checkout_address", 0.88, address_id=parse_address_id(text))
    if is_cart_view_request(text):
        return CommerceCommand("view_cart", 0.86)
    if is_cart_remove_request(text) or is_cart_clear_request(text):
        return CommerceCommand("remove_from_cart", 0.9)
    set_quantity = parse_set_quantity(text)
    if set_quantity is not None:
        return CommerceCommand("update_cart_quantity", 0.88, set_quantity=set_quantity)
    quantity_delta = parse_quantity_delta(text)
    if quantity_delta:
        return CommerceCommand("adjust_cart_quantity", 0.82, quantity_delta=quantity_delta)
    if is_cart_add_request(text):
        return CommerceCommand("add_to_cart", 0.88, quantity=parse_quantity(text))
    if is_checkout_request(text):
        return CommerceCommand("checkout", 0.88, quantity=parse_quantity(text))
    if is_price_alert_request(text):
        return CommerceCommand("create_price_alert", 0.86)
    return _llm_fallback_command(query) or CommerceCommand("help", 0.0)


def is_purchase_intent(query: str) -> bool:
    text = normalize_text(query)
    return parse_command(text).action != "help" or contains_any(
        text,
        ["怎么购买", "如何购买", "怎么买", "购买流程", "怎么下单", "如何下单", "checkout", "buynow"],
    )


def is_checkout_confirmation_reply(query: str) -> bool:
    text = normalize_text(query)
    if contains_configured(
        text,
        "confirm_checkout",
        "contains",
        ["确认下单", "确认购买", "确认提交", "提交订单", "可以下单", "下单吧", "下吧", "就按这个来"],
    ):
        return True
    if "确认" in text and contains_any(text, ["地址没问题", "信息无误", "没问题", "无误"]):
        return True
    return exact_configured(
        text,
        "confirm_checkout",
        "exact",
        [
            "确认",
            "确认了",
            "好的",
            "好",
            "可以",
            "可以了",
            "行",
            "行的",
            "没问题",
            "没错",
            "对",
            "对的",
            "就这样",
            "就这么办",
            "嗯",
            "嗯嗯",
            "ok",
            "okay",
            "yes",
            "y",
        ],
    )


def is_cancel_reply(query: str) -> bool:
    text = normalize_text(query)
    return exact_configured(
        text,
        "cancel_checkout",
        "exact",
        ["取消", "算了", "不要了", "先不要", "不买了", "撤销", "取消下单", "不用了"],
    ) or contains_configured(
        text,
        "cancel_checkout",
        "contains",
        ["取消这单", "取消订单", "先别下单", "先别买", "等一下", "等等", "停一下", "先放一放"],
    )


def is_cart_view_request(query: str) -> bool:
    text = normalize_text(query)
    return contains_configured(
        text,
        "view_cart",
        "contains",
        ["看购物车", "查看购物车", "购物车里", "购物车有什么", "车里有什么", "看下车", "看看车"],
    ) or exact_configured(text, "view_cart", "exact", ["购物车", "我的购物车", "看车"])


def is_cart_add_request(query: str) -> bool:
    text = normalize_text(query)
    return contains_configured(
        text,
        "add_to_cart",
        "contains",
        [
            "加入购物车",
            "加购物车",
            "加到购物车",
            "加进购物车",
            "放购物车",
            "放进购物车",
            "放到购物车",
            "放车里",
            "放进车里",
            "丢车里",
            "塞车里",
            "加入车",
            "加到车里",
            "收进购物车",
            "加购",
            "先放着",
            "先留着",
            "先存着",
            "先搁着",
            "帮我留一下",
            "帮我收着",
        ],
    )


def is_cart_remove_request(query: str) -> bool:
    text = normalize_text(query)
    return contains_configured(
        text,
        "remove_from_cart",
        "contains",
        ["删除", "移除", "从购物车去掉", "购物车去掉", "删掉", "清掉", "拿掉", "踢出购物车"],
    ) or (
        contains_configured(text, "remove_from_cart", "contains", ["不要", "不想要", "去掉", "拿出去", "删了"])
        and contains_any(text, ["购物车", "商品", "这个", "这款", "第", "第一", "第二", "第三"])
    )


def is_cart_clear_request(query: str) -> bool:
    text = normalize_text(query)
    return contains_configured(
        text,
        "clear_cart",
        "contains",
        ["清空购物车", "购物车清空", "全部删除", "全部移除", "全删", "都删掉", "都移除", "车清了", "车里都不要"],
    )


def is_cart_set_quantity_request(query: str) -> bool:
    text = normalize_text(query)
    if not contains_configured(text, "set_quantity", "context", ["数量", "购物车", "第", "这个", "这款", "件", "个", "台", "款"]):
        return False
    return contains_configured(
        text,
        "set_quantity",
        "contains",
        ["数量改", "数量调整", "数量设", "改成", "改为", "改到", "改", "调整为", "调成", "调到", "设为", "设置为", "变成", "要"],
    )


def is_address_update_request(query: str) -> bool:
    text = normalize_text(query)
    if contains_configured(text, "address_update", "negative", ["地址没问题", "地址无误", "信息无误", "确认"]):
        return False
    if text in {"公司地址", "家里地址", "学校地址", "默认地址", "公司收货", "家里收货", "学校收货"}:
        return True
    return contains_configured(text, "address_update", "contains", ["地址", "收货", "寄", "送", "发", "配送"]) and parse_address_id(text) != ""


def is_checkout_request(query: str) -> bool:
    text = normalize_text(query)
    return contains_configured(
        text,
        "checkout",
        "contains",
        [
            "结算",
            "下单",
            "提交订单",
            "立即购买",
            "直接买",
            "就买",
            "买第一",
            "买第1",
            "买这款",
            "买这个",
            "帮我买",
            "帮我下单",
            "下这一款",
            "拿下",
            "要了",
            "就它",
            "就这个",
            "就这款",
            "选它",
            "选这个",
            "来一件",
            "来一个",
            "给我来",
        ],
    )


def is_purchase_selection(query: str) -> bool:
    text = normalize_text(query)
    return is_checkout_request(text) or contains_any(text, ["拿第一", "拿第1", "定第一", "定这款", "就它吧"])


def is_price_alert_request(query: str) -> bool:
    text = normalize_text(query)
    return contains_configured(
        text,
        "price_alert",
        "contains",
        [
            "降价提醒",
            "价格提醒",
            "便宜了提醒",
            "到货提醒",
            "有货提醒",
            "补货提醒",
            "提醒我",
            "降到",
            "低于",
            "目标价",
        ],
    )


def is_all_selection(query: str) -> bool:
    text = normalize_text(query)
    return contains_configured(text, "selection", "all", ["都要", "全都要", "全部要", "一起要", "都买", "全买", "一起买", "都加入购物车", "全放车里"])


def is_deictic_selection(query: str) -> bool:
    text = normalize_text(query)
    return contains_configured(text, "selection", "deictic", ["这个", "这款", "它", "就它", "第一", "第1", "第二", "第2", "第三", "第3"])


def is_implicit_selection(query: str) -> bool:
    text = normalize_text(query)
    return contains_configured(text, "selection", "implicit", ["来一件", "来一个", "给我来", "拿下", "要了", "就它吧", "下单吧", "下吧", "先放着", "先留着", "先存着"])


def is_more_or_switch_request(query: str) -> bool:
    text = normalize_text(query)
    return contains_configured(text, "selection", "more_or_switch", ["换一个", "换一款", "换个", "还有吗", "其他", "别的", "再推荐", "再找", "换一批"])


def is_cheaper_request(query: str) -> bool:
    text = normalize_text(query)
    return contains_configured(text, "selection", "cheaper", ["便宜点", "更便宜", "省钱", "低价", "价格低", "预算低", "压预算"])


def is_exclude_request(query: str) -> bool:
    text = normalize_text(query)
    return contains_configured(text, "selection", "exclude", ["不要", "不看", "排除", "去掉", "剔除", "不考虑"])


def resolve_target_indices(query: str, count: int, *, cart: bool = False) -> list[int]:
    if count <= 0:
        return []
    text = normalize_text(query)
    if is_all_selection(text) or (cart and is_cart_clear_request(text)):
        return list(range(count if cart else min(count, 3)))
    if contains_any(text, ["这两", "两个", "两件", "两款", "前两个"]) and count >= 2:
        return [0, 1]
    if contains_any(text, ["最后一个", "最后一件", "最后一款", "末尾"]):
        return [count - 1]

    ordinal_patterns = [
        (0, ["第一", "第1", "第一个", "第一件", "第一款", "首个", "首款", "主推", "首推"]),
        (1, ["第二", "第2", "第二个", "第二件", "第二款", "备选"]),
        (2, ["第三", "第3", "第三个", "第三件", "第三款"]),
    ]
    for index, keywords in ordinal_patterns:
        if index < count and contains_any(text, keywords):
            return [index]
    return []


def _llm_fallback_command(query: str) -> CommerceCommand | None:
    if not _llm_fallback_enabled():
        return None

    rules = rule_dict("nlu", "llm_fallback")
    allowed_actions = set(str(item) for item in rule_list("nlu", "llm_fallback", "allowed_actions") if item) or DEFAULT_LLM_ACTIONS
    min_confidence = _float_value(
        os.getenv("COMMERCE_NLU_LLM_MIN_CONFIDENCE") or rules.get("min_confidence"),
        0.68,
    )
    messages = [
        {
            "role": "system",
            "content": (
                "你是电商购物车命令分类器。只输出 JSON 对象，不要输出解释。"
                "action 必须是允许动作之一；无法确定时用 help。"
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "query": query,
                    "allowed_actions": sorted(allowed_actions),
                    "schema": {
                        "action": "string",
                        "confidence": "0-1 number",
                        "quantity": "optional positive integer",
                        "set_quantity": "optional positive integer",
                        "quantity_delta": "optional signed integer",
                        "address_id": "optional string",
                    },
                },
                ensure_ascii=False,
            ),
        },
    ]
    try:
        client = OpenAICompatibleClient(timeout=float(os.getenv("COMMERCE_NLU_LLM_TIMEOUT_SECONDS", "8")))
        payload = _parse_json_object(client.chat_sync(messages, temperature=0.0))
    except Exception:
        return None

    action = str(payload.get("action") or "help")
    confidence = _float_value(payload.get("confidence"), 0.0)
    if action not in allowed_actions or action == "help" or confidence < min_confidence:
        return None

    quantity = _positive_int(payload.get("quantity")) or parse_quantity(query)
    set_quantity = _positive_int(payload.get("set_quantity"))
    quantity_delta = _int_value(payload.get("quantity_delta"), 0)
    address_id = str(payload.get("address_id") or "")
    if action == "update_cart_quantity" and set_quantity is None:
        set_quantity = parse_set_quantity(query) or quantity
    if action == "adjust_cart_quantity" and quantity_delta == 0:
        quantity_delta = parse_quantity_delta(query)
    if action == "update_checkout_address" and not address_id:
        address_id = parse_address_id(query)

    return CommerceCommand(
        action=action,
        confidence=min(max(confidence, min_confidence), 0.86),
        quantity=max(quantity, 1),
        set_quantity=set_quantity,
        quantity_delta=quantity_delta,
        address_id=address_id,
    )


def _llm_fallback_enabled() -> bool:
    value = os.getenv("COMMERCE_NLU_LLM_FALLBACK_ENABLED")
    if value is None:
        value = str(rule_dict("nlu", "llm_fallback").get("enabled", "false"))
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_json_object(raw_text: str) -> dict[str, Any]:
    text = (raw_text or "").strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.S)
        if not match:
            return {}
        try:
            payload = json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}
    return payload if isinstance(payload, dict) else {}


def _positive_int(value: Any) -> int | None:
    parsed = _int_value(value, 0)
    return parsed if parsed > 0 else None


def _int_value(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _float_value(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _number_value(value: str) -> int:
    value = _to_half_width(str(value or "")).strip()
    if value.isdigit():
        return int(value)
    if value == "十":
        return 10
    if "十" in value:
        left, _, right = value.partition("十")
        tens = CHINESE_DIGITS.get(left, 1) if left else 1
        ones = CHINESE_DIGITS.get(right, 0) if right else 0
        return tens * 10 + ones
    return CHINESE_DIGITS.get(value, 1)


def _to_half_width(text: str) -> str:
    return text.translate(str.maketrans("０１２３４５６７８９", "0123456789"))
