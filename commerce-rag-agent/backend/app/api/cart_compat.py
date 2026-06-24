"""
购物车兼容路由 — 提供与 Java 平台相同格式的 /api/cart 接口。
前端调用 /api/cart/items 等接口时走这里，而不是 Java 后端。
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.security import CurrentUser, require_current_user
from app.models.db import get_db, init_db
from app.services.cart_service import (
    CommerceError,
    add_cart_item,
    list_cart,
    remove_cart_item,
    update_cart_item,
)

router = APIRouter(prefix="/api/cart", tags=["cart-compat"])


def _current_user_id(request: Request) -> str:
    """从 JWT 中提取 user_id，未登录返回空字符串。"""
    auth = request.headers.get("Authorization", "")
    if not auth:
        return ""
    try:
        from app.api.security import _user_from_jwt
        user = _user_from_jwt(auth.removeprefix("Bearer ").strip())
        return user.user_id if user else ""
    except Exception:
        return ""


@router.get("/items")
def get_items(request: Request, db: Session = Depends(get_db)) -> dict:
    init_db()
    user_id = _current_user_id(request)
    if not user_id:
        return JSONResponse(status_code=401, content={"code": "40100", "success": False, "message": "未登录"})
    cart = list_cart(db, user_id=user_id)
    return {
        "code": "00000",
        "success": True,
        "data": {
            "items": [
                {
                    "id": item["cart_item_id"],
                    "skuId": item.get("sku_id", ""),
                    "spuId": item["product_id"],
                    "spuName": item["title"],
                    "skuName": "",
                    "salePrice": item["price"],
                    "quantity": item["quantity"],
                    "checked": True,
                    "thumbUrl": item.get("image_url", ""),
                }
                for item in cart.get("items", [])
            ],
            "totalItemCount": cart.get("total_quantity", 0),
            "checkedAmount": cart.get("subtotal_amount", 0),
        },
    }


@router.post("/items")
async def add_item(request: Request, db: Session = Depends(get_db)) -> dict:
    init_db()
    user_id = _current_user_id(request)
    if not user_id:
        return JSONResponse(status_code=401, content={"code": "40100", "success": False, "message": "未登录"})
    body = await request.json()
    sku_id = str(body.get("skuId") or "")
    quantity = int(body.get("quantity") or 1)
    # 从 skuId 推导 productId（Agent 的 sku 格式是 s_{product_id}_{index}）
    product_id = sku_id.rsplit("_", 1)[0] if "_" in sku_id else sku_id
    if product_id.startswith("s_"):
        product_id = product_id[2:]
    try:
        add_cart_item(db, product_id=product_id, quantity=quantity, user_id=user_id)
        return {"code": "00000", "success": True, "message": "已加入购物车"}
    except CommerceError as exc:
        return JSONResponse(status_code=400, content={"code": "40000", "success": False, "message": str(exc)})


@router.put("/items/{cart_item_id}/quantity")
async def update_quantity(cart_item_id: str, request: Request, db: Session = Depends(get_db)) -> dict:
    init_db()
    user_id = _current_user_id(request)
    if not user_id:
        return JSONResponse(status_code=401, content={"code": "40100", "success": False, "message": "未登录"})
    body = await request.json()
    quantity = int(body.get("quantity") or 1)
    try:
        update_cart_item(db, cart_item_id=cart_item_id, quantity=quantity, user_id=user_id)
        return {"code": "00000", "success": True}
    except CommerceError as exc:
        return JSONResponse(status_code=400, content={"code": "40000", "success": False, "message": str(exc)})


@router.put("/items/{cart_item_id}/checked")
def update_checked(cart_item_id: str, request: Request, db: Session = Depends(get_db)) -> dict:
    # Agent 没有勾选状态，直接返回成功
    return {"code": "00000", "success": True}


@router.delete("/items/{cart_item_id}")
def delete_item(cart_item_id: str, request: Request, db: Session = Depends(get_db)) -> dict:
    init_db()
    user_id = _current_user_id(request)
    if not user_id:
        return JSONResponse(status_code=401, content={"code": "40100", "success": False, "message": "未登录"})
    try:
        remove_cart_item(db, cart_item_id=cart_item_id, user_id=user_id)
        return {"code": "00000", "success": True}
    except CommerceError as exc:
        return JSONResponse(status_code=400, content={"code": "40000", "success": False, "message": str(exc)})


@router.delete("/items/clear")
def clear_cart(request: Request, db: Session = Depends(get_db)) -> dict:
    init_db()
    user_id = _current_user_id(request)
    if not user_id:
        return JSONResponse(status_code=401, content={"code": "40100", "success": False, "message": "未登录"})
    from app.services.cart_service import clear_cart_items
    clear_cart_items(db, user_id=user_id)
    return {"code": "00000", "success": True}
