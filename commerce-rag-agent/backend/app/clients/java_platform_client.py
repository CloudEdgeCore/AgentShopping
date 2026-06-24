"""
Java shopping-platform API 客户端。

用于将购物车、订单等交易操作代理到 Java 后端服务。
Python RAG Agent 只负责 AI 能力，交易数据以 Java 为准。
"""

import os
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

JAVA_PLATFORM_URL = os.getenv("JAVA_PLATFORM_URL", "http://localhost:8080")
_REQUEST_TIMEOUT = 10.0


class JavaPlatformClient:
    """Java 平台 REST API 客户端。"""

    def __init__(self, base_url: str | None = None, timeout: float = _REQUEST_TIMEOUT):
        self.base_url = (base_url or JAVA_PLATFORM_URL).rstrip("/")
        self.timeout = timeout

    def _headers(self, jwt_token: str | None = None) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if jwt_token:
            headers["Authorization"] = f"Bearer {jwt_token}"
        return headers

    # ─── 购物车 ───

    async def get_cart_items(self, jwt_token: str) -> dict[str, Any]:
        """获取购物车列表。"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                f"{self.base_url}/cart/items",
                headers=self._headers(jwt_token),
            )
            resp.raise_for_status()
            return resp.json()

    async def add_cart_item(self, jwt_token: str, sku_id: int, quantity: int = 1) -> dict[str, Any]:
        """加入购物车。"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/cart/items",
                headers=self._headers(jwt_token),
                json={"skuId": sku_id, "quantity": quantity},
            )
            resp.raise_for_status()
            return resp.json()

    async def update_cart_item_quantity(self, jwt_token: str, item_id: int, quantity: int) -> dict[str, Any]:
        """修改购物车商品数量。"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.put(
                f"{self.base_url}/cart/items/{item_id}/quantity",
                headers=self._headers(jwt_token),
                json={"quantity": quantity},
            )
            resp.raise_for_status()
            return resp.json()

    async def delete_cart_item(self, jwt_token: str, item_id: int) -> dict[str, Any]:
        """删除购物车商品。"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.delete(
                f"{self.base_url}/cart/items/{item_id}",
                headers=self._headers(jwt_token),
            )
            resp.raise_for_status()
            return resp.json()

    async def clear_cart(self, jwt_token: str) -> dict[str, Any]:
        """清空购物车。"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.delete(
                f"{self.base_url}/cart/items/clear",
                headers=self._headers(jwt_token),
            )
            resp.raise_for_status()
            return resp.json()

    # ─── 订单 ───

    async def preview_order(self, jwt_token: str, cart_item_ids: list[int]) -> dict[str, Any]:
        """订单预览（确认页）。"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/orders/preview",
                headers=self._headers(jwt_token),
                json={"cartItemIds": cart_item_ids},
            )
            resp.raise_for_status()
            return resp.json()

    async def submit_order(
        self,
        jwt_token: str,
        address_id: int,
        cart_item_ids: list[int],
        coupon_user_id: int | None = None,
    ) -> dict[str, Any]:
        """提交订单。"""
        payload: dict[str, Any] = {
            "addressId": address_id,
            "cartItemIds": cart_item_ids,
        }
        if coupon_user_id is not None:
            payload["couponUserIds"] = [coupon_user_id]
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/orders/submit",
                headers=self._headers(jwt_token),
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()

    async def get_order(self, jwt_token: str, order_no: str) -> dict[str, Any]:
        """查询订单详情。"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                f"{self.base_url}/orders/{order_no}",
                headers=self._headers(jwt_token),
            )
            resp.raise_for_status()
            return resp.json()

    async def get_orders(self, jwt_token: str, page: int = 1, size: int = 10) -> dict[str, Any]:
        """查询订单列表。"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                f"{self.base_url}/orders/page",
                headers=self._headers(jwt_token),
                params={"page": page, "size": size},
            )
            resp.raise_for_status()
            return resp.json()

    async def cancel_order(self, jwt_token: str, order_no: str) -> dict[str, Any]:
        """取消订单。"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/orders/{order_no}/cancel",
                headers=self._headers(jwt_token),
            )
            resp.raise_for_status()
            return resp.json()

    # ─── 支付 ───

    async def create_mock_payment(self, jwt_token: str, order_no: str) -> dict[str, Any]:
        """创建模拟支付。"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/payments/mock/create",
                headers=self._headers(jwt_token),
                json={"orderNo": order_no},
            )
            resp.raise_for_status()
            return resp.json()

    async def confirm_payment(self, jwt_token: str, payment_no: str) -> dict[str, Any]:
        """确认支付成功。"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/payments/{payment_no}/success",
                headers=self._headers(jwt_token),
            )
            resp.raise_for_status()
            return resp.json()

    # ─── 商品（只读） ───

    async def search_products(
        self,
        keyword: str | None = None,
        category_id: int | None = None,
        page: int = 1,
        size: int = 20,
    ) -> dict[str, Any]:
        """搜索商品（公开接口，不需要认证）。"""
        params: dict[str, Any] = {"page": page, "size": size}
        if keyword:
            params["keyword"] = keyword
        if category_id:
            params["categoryId"] = category_id
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                f"{self.base_url}/search/product/page",
                params=params,
            )
            resp.raise_for_status()
            return resp.json()

    async def get_product_detail(self, product_id: int) -> dict[str, Any]:
        """获取商品详情（公开接口）。"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(f"{self.base_url}/product/{product_id}")
            resp.raise_for_status()
            return resp.json()

    async def get_categories(self) -> dict[str, Any]:
        """获取分类树（公开接口）。"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(f"{self.base_url}/product/categories")
            resp.raise_for_status()
            return resp.json()

    # ─── 用户 ───

    async def get_user_profile(self, jwt_token: str) -> dict[str, Any]:
        """获取用户信息。"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                f"{self.base_url}/user/profile",
                headers=self._headers(jwt_token),
            )
            resp.raise_for_status()
            return resp.json()

    async def get_user_addresses(self, jwt_token: str) -> dict[str, Any]:
        """获取收货地址列表。"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                f"{self.base_url}/user/address/list",
                headers=self._headers(jwt_token),
            )
            resp.raise_for_status()
            return resp.json()


# 全局单例
java_client = JavaPlatformClient()
