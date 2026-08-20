"""基于模型的检索重排服务（OpenAI 兼容 rerank API，如 bge-reranker-v2-m3）。

配置：
- RERANK_BASE_URL：服务地址，如 http://host:8080/v1（自动兼容带/不带 /v1）
- RERANK_MODEL：模型名，默认 bge-reranker-v2-m3
- RERANK_API_KEY：可选，内网服务免鉴权时留空
- RERANK_TIMEOUT_SECONDS：超时，默认 30
"""

import os
from dataclasses import dataclass
from typing import Any

import httpx

from dotenv import load_dotenv


@dataclass(frozen=True)
class RerankHit:
    index: int
    score: float


class RerankClient:
    def __init__(self) -> None:
        load_dotenv()
        self.base_url = os.getenv("RERANK_BASE_URL", "").strip().rstrip("/")
        self.model = os.getenv("RERANK_MODEL", "bge-reranker-v2-m3").strip() or "bge-reranker-v2-m3"
        self.api_key = os.getenv("RERANK_API_KEY", "").strip()
        self.timeout = float(os.getenv("RERANK_TIMEOUT_SECONDS", "30"))

    @property
    def available(self) -> bool:
        return bool(self.base_url)

    def rerank(
        self,
        query: str,
        documents: list[str],
        *,
        top_n: int | None = None,
    ) -> list[RerankHit]:
        if not self.available:
            raise RuntimeError("RERANK_BASE_URL is not configured")
        if not documents:
            return []

        payload: dict[str, Any] = {
            "model": self.model,
            "query": query,
            "documents": documents,
        }
        if top_n is not None:
            payload["top_n"] = top_n

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                self._endpoint("rerank"),
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        items = data.get("results")
        if not isinstance(items, list):
            # 兼容部分实现把结果直接放在 data 字段
            items = data.get("data") or []
        hits: list[RerankHit] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            index = item.get("index")
            score = item.get("relevance_score", item.get("score"))
            if index is None or score is None:
                continue
            hits.append(RerankHit(index=int(index), score=float(score)))
        hits.sort(key=lambda hit: -hit.score)
        return hits

    def _endpoint(self, path: str) -> str:
        if self.base_url.endswith("/v1"):
            return f"{self.base_url}/{path}"
        return f"{self.base_url}/v1/{path}"


_client: RerankClient | None = None


def get_rerank_client() -> RerankClient | None:
    """懒加载单例；未配置 RERANK_BASE_URL 时返回 None（重排降级跳过）。"""
    global _client
    if _client is None:
        client = RerankClient()
        if not client.available:
            return None
        _client = client
    return _client
