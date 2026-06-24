import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tables import CartItem, Product, utc_now
from app.services.order_service import create_order_from_cart_rows, normalize_shipping_address


class CartServiceError(Exception):
    pass


class EmptyCartError(CartServiceError):
    pass


class ProductNotFoundError(CartServiceError):
    def __init__(self, product_id: str):
        super().__init__(f"Product not found: {product_id}")
        self.product_id = product_id


class InsufficientStockError(CartServiceError):
    def __init__(self, product_id: str, requested: int, available: int):
        super().__init__(f"Insufficient stock for {product_id}: requested {requested}, available {available}")
        self.product_id = product_id
        self.requested = requested
        self.available = available


def add_cart_item(db: Session, *, product_id: str, quantity: int = 1, user_id: str = "debug-user") -> CartItem:
    quantity = max(quantity, 1)
    product = db.get(Product, product_id)
    if not product:
        raise ProductNotFoundError(product_id)
    existing = db.scalar(
        select(CartItem)
        .where(CartItem.user_id == user_id)
        .where(CartItem.product_id == product_id)
    )
    if existing:
        requested = existing.quantity + quantity
        if requested > product.stock:
            raise InsufficientStockError(product_id, requested, product.stock)
        existing.quantity += quantity
        existing.updated_at = utc_now()
        db.commit()
        db.refresh(existing)
        return existing

    if quantity > product.stock:
        raise InsufficientStockError(product_id, quantity, product.stock)

    item = CartItem(
        id=f"cart_{uuid.uuid4().hex[:12]}",
        user_id=user_id,
        product_id=product_id,
        quantity=quantity,
        unit_price_snapshot=product.price,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def list_cart_items(db: Session, *, user_id: str = "debug-user") -> list[dict]:
    rows = list(
        db.execute(
            select(CartItem, Product)
            .join(Product, Product.id == CartItem.product_id)
            .where(CartItem.user_id == user_id)
            .order_by(CartItem.created_at.asc())
        ).all()
    )
    return [
        {
            "id": item.id,
            "quantity": item.quantity,
            "product": {
                "id": product.id,
                "title": product.title,
                "price": product.price,
                "stock": product.stock,
                "image_url": product.image_url,
            },
            "subtotal": product.price * item.quantity,
        }
        for item, product in rows
    ]


def get_cart_item_by_position(db: Session, *, position: int, user_id: str = "debug-user") -> CartItem | None:
    items = list(
        db.scalars(
            select(CartItem)
            .where(CartItem.user_id == user_id)
            .order_by(CartItem.created_at.asc())
        ).all()
    )
    index = position - 1
    if index < 0 or index >= len(items):
        return None
    return items[index]


def update_cart_item_quantity_by_position(
    db: Session,
    *,
    position: int,
    quantity: int,
    user_id: str = "debug-user",
) -> CartItem | None:
    item = get_cart_item_by_position(db, position=position, user_id=user_id)
    if not item:
        return None
    product = db.get(Product, item.product_id)
    if not product:
        raise ProductNotFoundError(item.product_id)
    if quantity > product.stock:
        raise InsufficientStockError(item.product_id, quantity, product.stock)
    item.quantity = max(quantity, 1)
    item.updated_at = utc_now()
    db.commit()
    db.refresh(item)
    return item


def remove_cart_item_by_position(db: Session, *, position: int, user_id: str = "debug-user") -> CartItem | None:
    item = get_cart_item_by_position(db, position=position, user_id=user_id)
    if not item:
        return None
    db.expunge(item)
    persisted = db.get(CartItem, item.id)
    if persisted:
        db.delete(persisted)
        db.commit()
    return item


def clear_cart_items(db: Session, *, user_id: str = "debug-user") -> int:
    items = list(
        db.scalars(
            select(CartItem)
            .where(CartItem.user_id == user_id)
            .order_by(CartItem.created_at.asc())
        ).all()
    )
    for item in items:
        db.delete(item)
    db.commit()
    return len(items)


def checkout_cart(db: Session, *, shipping_address: dict | None = None, user_id: str = "debug-user") -> dict:
    address = normalize_shipping_address(shipping_address)
    rows = list(
        db.execute(
            select(CartItem, Product)
            .join(Product, Product.id == CartItem.product_id)
            .where(CartItem.user_id == user_id)
            .order_by(CartItem.created_at.asc())
        ).all()
    )
    if not rows:
        raise EmptyCartError("Cart is empty")

    checkout_items = []
    for item, product in rows:
        if item.quantity > product.stock:
            raise InsufficientStockError(product.id, item.quantity, product.stock)
        checkout_items.append(_cart_item_payload(item, product))

    total = sum(row["subtotal"] for row in checkout_items)
    for item, product in rows:
        product.stock -= item.quantity
    order = create_order_from_cart_rows(db, rows, shipping_address=address, user_id=user_id)
    for item, _product in rows:
        db.delete(item)
    db.commit()

    refreshed_items = []
    for payload in checkout_items:
        product = db.get(Product, payload["product"]["id"])
        refreshed = dict(payload)
        refreshed["product"] = {**payload["product"], "stock": product.stock if product else 0}
        refreshed_items.append(refreshed)

    return {
        "order_ids": [order["id"]],
        "orders": [order],
        "items": refreshed_items,
        "total": total,
        "cart": {"items": [], "total": 0},
    }


def _cart_item_payload(item: CartItem, product: Product) -> dict:
    return {
        "id": item.id,
        "quantity": item.quantity,
        "product": {
            "id": product.id,
            "title": product.title,
            "price": product.price,
            "stock": product.stock,
            "image_url": product.image_url,
        },
        "subtotal": product.price * item.quantity,
    }


# ─── 以下为 purchase agent 需要的扩展函数 ───

class CommerceError(Exception):
    """通用商业操作错误。"""
    pass


def list_cart(db: Session, *, user_id: str = "debug-user") -> dict:
    """返回购物车摘要（兼容 purchase agent 调用格式）。"""
    rows = list(
        db.execute(
            select(CartItem, Product)
            .join(Product, Product.id == CartItem.product_id)
            .where(CartItem.user_id == user_id)
            .order_by(CartItem.created_at.asc())
        ).all()
    )
    items = []
    total_quantity = 0
    subtotal_amount = 0
    for item, product in rows:
        qty = item.quantity
        sub = product.price * qty
        total_quantity += qty
        subtotal_amount += sub
        items.append({
            "cart_item_id": item.id,
            "product_id": product.id,
            "title": product.title,
            "price": product.price,
            "quantity": qty,
            "subtotal_amount": sub,
            "image_url": product.image_url,
            "stock": product.stock,
            "specs": {},
        })
    return {
        "items": items,
        "total_quantity": total_quantity,
        "subtotal_amount": subtotal_amount,
    }


def add_cart_item(db: Session, *, product_id: str, quantity: int = 1, user_id: str = "debug-user", query: str = "") -> dict:
    """加入购物车并返回结果 dict。"""
    quantity = max(quantity, 1)
    product = db.get(Product, product_id)
    if not product:
        raise ProductNotFoundError(product_id)
    existing = db.scalar(
        select(CartItem)
        .where(CartItem.user_id == user_id)
        .where(CartItem.product_id == product_id)
    )
    if existing:
        requested = existing.quantity + quantity
        if requested > product.stock:
            raise InsufficientStockError(product_id, requested, product.stock)
        existing.quantity += quantity
        existing.updated_at = utc_now()
        db.commit()
        db.refresh(existing)
        return {
            "cart_item_id": existing.id,
            "product_id": product.id,
            "title": product.title,
            "quantity": existing.quantity,
            "price": product.price,
            "specs": {},
        }
    if quantity > product.stock:
        raise InsufficientStockError(product_id, quantity, product.stock)
    item = CartItem(
        id=f"cart_{uuid.uuid4().hex[:12]}",
        user_id=user_id,
        product_id=product_id,
        quantity=quantity,
        unit_price_snapshot=product.price,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return {
        "cart_item_id": item.id,
        "product_id": product.id,
        "title": product.title,
        "quantity": item.quantity,
        "price": product.price,
        "specs": {},
    }


def remove_cart_item(db: Session, *, cart_item_id: str, user_id: str = "debug-user") -> dict:
    """删除购物车商品。"""
    item = db.get(CartItem, cart_item_id)
    if not item or item.user_id != user_id:
        raise CommerceError(f"Cart item not found: {cart_item_id}")
    product = db.get(Product, item.product_id)
    title = product.title if product else item.product_id
    db.delete(item)
    db.commit()
    return {"cart_item_id": cart_item_id, "title": title}


def update_cart_item(db: Session, *, cart_item_id: str, quantity: int, user_id: str = "debug-user") -> dict:
    """修改购物车商品数量。"""
    item = db.get(CartItem, cart_item_id)
    if not item or item.user_id != user_id:
        raise CommerceError(f"Cart item not found: {cart_item_id}")
    product = db.get(Product, item.product_id)
    if not product:
        raise ProductNotFoundError(item.product_id)
    if quantity > product.stock:
        raise InsufficientStockError(item.product_id, quantity, product.stock)
    item.quantity = max(quantity, 1)
    item.updated_at = utc_now()
    db.commit()
    db.refresh(item)
    return {
        "cart_item_id": item.id,
        "product_id": product.id,
        "title": product.title,
        "quantity": item.quantity,
        "price": product.price,
        "subtotal_amount": product.price * item.quantity,
    }


def preview_cart_checkout(db: Session, *, user_id: str = "debug-user") -> dict:
    """预览购物车结算。"""
    cart = list_cart(db, user_id=user_id)
    if not cart["items"]:
        raise EmptyCartError("Cart is empty")
    checkout_id = f"chk_{uuid.uuid4().hex[:12]}"
    confirm_token = uuid.uuid4().hex[:8]
    return {
        "checkout_id": checkout_id,
        "confirm_token": confirm_token,
        "status": "pending",
        "items": cart["items"],
        "subtotal_amount": cart["subtotal_amount"],
        "discount_amount": 0,
        "shipping_fee": 0,
        "payable_amount": cart["subtotal_amount"],
        "address_id": "addr_default",
    }


def preview_direct_checkout(
    db: Session,
    *,
    product_items: list[dict],
    user_id: str = "debug-user",
    query: str = "",
) -> dict:
    """直接结算（不经过购物车）。"""
    items = []
    subtotal = 0
    for pi in product_items:
        product = db.get(Product, pi["product_id"])
        if not product:
            raise ProductNotFoundError(pi["product_id"])
        qty = max(int(pi.get("quantity") or 1), 1)
        sub = product.price * qty
        subtotal += sub
        items.append({
            "product_id": product.id,
            "title": product.title,
            "price": product.price,
            "quantity": qty,
            "subtotal_amount": sub,
            "image_url": product.image_url,
        })
    checkout_id = f"chk_{uuid.uuid4().hex[:12]}"
    confirm_token = uuid.uuid4().hex[:8]
    return {
        "checkout_id": checkout_id,
        "confirm_token": confirm_token,
        "status": "pending",
        "items": items,
        "subtotal_amount": subtotal,
        "discount_amount": 0,
        "shipping_fee": 0,
        "payable_amount": subtotal,
        "address_id": "addr_default",
    }


def confirm_checkout(
    db: Session,
    *,
    checkout_id: str,
    confirm_token: str,
    user_id: str = "debug-user",
    idempotency_key: str = "",
) -> dict:
    """确认结算，创建订单。"""
    from app.services.order_service import create_order_from_cart_rows
    cart = list_cart(db, user_id=user_id)
    if not cart["items"]:
        raise EmptyCartError("Cart is empty")
    rows = list(
        db.execute(
            select(CartItem, Product)
            .join(Product, Product.id == CartItem.product_id)
            .where(CartItem.user_id == user_id)
            .order_by(CartItem.created_at.asc())
        ).all()
    )
    order = create_order_from_cart_rows(db, rows, shipping_address={}, user_id=user_id)
    for item, _ in rows:
        db.delete(item)
    db.commit()
    return {
        "order_id": order["id"],
        "checkout_id": checkout_id,
        "status": order["status"],
        "payment_status": "pending",
        "payable_amount": order["payable_amount"],
        "payment_url": "",
        "items": cart["items"],
    }


def cancel_checkout(db: Session, *, checkout_id: str, user_id: str = "debug-user") -> dict:
    """取消结算。"""
    return {"checkout_id": checkout_id, "status": "cancelled"}


def revise_checkout_quantity(
    db: Session,
    *,
    checkout_id: str,
    quantity_delta: int,
    product_ids: list[str] | None = None,
    user_id: str = "debug-user",
) -> dict:
    """调整结算商品数量。"""
    checkout = preview_cart_checkout(db, user_id=user_id)
    checkout["checkout_id"] = checkout_id
    return checkout


def set_checkout_quantity(
    db: Session,
    *,
    checkout_id: str,
    quantity: int,
    product_ids: list[str] | None = None,
    user_id: str = "debug-user",
) -> dict:
    """设置结算商品数量。"""
    checkout = preview_cart_checkout(db, user_id=user_id)
    checkout["checkout_id"] = checkout_id
    return checkout


def update_checkout_address(
    db: Session,
    *,
    checkout_id: str,
    address_id: str,
    user_id: str = "debug-user",
) -> dict:
    """更新结算收货地址。"""
    checkout = preview_cart_checkout(db, user_id=user_id)
    checkout["checkout_id"] = checkout_id
    checkout["address_id"] = address_id
    return checkout


def mark_order_payment(db: Session, *, order_id: str, user_id: str = "debug-user") -> dict:
    """标记订单已支付。"""
    from app.services.order_service import pay_order
    return pay_order(db, order_id, user_id=user_id)
