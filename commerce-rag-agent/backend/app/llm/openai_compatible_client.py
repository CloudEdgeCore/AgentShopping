import os
import json
from collections.abc import Iterator
from collections.abc import AsyncIterator

import httpx


class OpenAICompatibleClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        api_key_env: str = "LLM_API_KEY",
        base_url_env: str = "LLM_BASE_URL",
        model_env: str = "LLM_MODEL",
        timeout: float | None = None,
    ) -> None:
        # LLM_* 优先，兼容历史 DOUBAO_* / ARK_* 配置
        self.api_key = (
            api_key
            or os.getenv(api_key_env)
            or os.getenv("DOUBAO_API_KEY")
            or os.getenv("ARK_API_KEY")
            or ""
        )
        self.base_url = (
            base_url
            or os.getenv(base_url_env)
            or os.getenv("DOUBAO_BASE_URL")
            or ""
        ).rstrip("/")
        self.model = model or os.getenv(model_env) or os.getenv("DOUBAO_MODEL") or ""
        self.timeout = timeout or float(os.getenv("LLM_TIMEOUT_SECONDS", "60"))
        if not self.base_url:
            raise ValueError(f"Missing {base_url_env} for OpenAI-compatible LLM client")
        if not self.model:
            raise ValueError(f"Missing {model_env} for OpenAI-compatible LLM client")

    def chat_sync(self, messages: list[dict[str, str]], *, temperature: float = 0.2) -> str:
        payload = self._payload(messages, temperature=temperature, stream=False)
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    async def chat(self, messages: list[dict[str, str]], *, temperature: float = 0.2) -> str:
        payload = self._payload(messages, temperature=temperature, stream=False)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
    ) -> AsyncIterator[str]:
        payload = self._payload(messages, temperature=temperature, stream=True)
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        yield line.removeprefix("data: ")

    def stream_chat_sync(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
    ) -> Iterator[str]:
        payload = self._payload(messages, temperature=temperature, stream=True)
        with httpx.Client(timeout=None) as client:
            with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    for delta in _content_deltas_from_sse_line(line):
                        yield delta

    def _payload(self, messages: list[dict[str, str]], *, temperature: float, stream: bool) -> dict:
        return {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
        }

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        # 内网/自建 OpenAI 兼容服务通常免鉴权：未配置 key 时不发送 Authorization 头
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers


def _content_deltas_from_sse_line(line: str) -> Iterator[str]:
    text = str(line or "").strip()
    if not text:
        return
    if text.startswith("data:"):
        text = text.removeprefix("data:").strip()
    if not text or text == "[DONE]":
        return
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return
    for choice in payload.get("choices") or []:
        delta = choice.get("delta") or {}
        content = delta.get("content")
        if content:
            yield from _normalize_content_delta(content)
        message = choice.get("message") or {}
        message_content = message.get("content")
        if message_content:
            yield from _normalize_content_delta(message_content)


def _normalize_content_delta(content: object) -> Iterator[str]:
    if isinstance(content, str):
        yield content
        return
    if isinstance(content, list):
        for item in content:
            if isinstance(item, str):
                yield item
            elif isinstance(item, dict):
                text = item.get("text")
                if text:
                    yield str(text)
