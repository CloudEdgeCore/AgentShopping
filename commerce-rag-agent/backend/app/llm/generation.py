import os
import time
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Protocol

import httpx
from dotenv import load_dotenv

from app.llm.openai_compatible_client import OpenAICompatibleClient
from app.llm.prompt_registry import (
    build_chitchat_messages,
    build_decision_guide_messages,
    build_faq_messages,
    build_response_composer_messages,
    build_shopping_messages,
)


load_dotenv()


class ChatClient(Protocol):
    def chat_sync(self, messages: list[dict[str, str]], *, temperature: float = 0.2) -> str:
        ...


@dataclass(frozen=True)
class GenerationResult:
    content: str
    llm_enabled: bool
    llm_error: str | None = None
    provider: str = ""
    model: str = ""
    latency_ms: int = 0
    cost_estimate: dict[str, float | int | str] | None = None


@dataclass(frozen=True)
class GenerationDelta:
    content: str


@dataclass(frozen=True)
class GenerationComplete:
    result: GenerationResult


def generate_shopping_answer(
    *,
    query: str,
    cards: list[dict],
    memory: dict,
    fallback: str,
    client: ChatClient | None = None,
) -> str:
    return generate_shopping_result(
        query=query,
        cards=cards,
        memory=memory,
        fallback=fallback,
        client=client,
    ).content


def generate_shopping_result(
    *,
    query: str,
    cards: list[dict],
    memory: dict,
    fallback: str,
    client: ChatClient | None = None,
) -> GenerationResult:
    return _generate_result(
        messages=build_shopping_messages(query=query, cards=cards, memory=memory),
        fallback=fallback,
        client=client,
    )


def generate_decision_guide_result(
    *,
    query: str,
    cards: list[dict],
    memory: dict,
    fallback: str,
    client: ChatClient | None = None,
) -> GenerationResult:
    return _generate_result(
        messages=build_decision_guide_messages(query=query, cards=cards, memory=memory),
        fallback=fallback,
        client=client,
    )


def generate_chitchat_result(
    *,
    query: str,
    fallback: str,
    client: ChatClient | None = None,
) -> GenerationResult:
    return _generate_result(
        messages=build_chitchat_messages(query=query),
        fallback=fallback,
        client=client,
    )


def generate_faq_answer(
    *,
    query: str,
    hits: list[dict],
    fallback: str,
    client: ChatClient | None = None,
) -> str:
    return generate_faq_result(query=query, hits=hits, fallback=fallback, client=client).content


def generate_response_composer_result(
    *,
    query: str,
    intent: str,
    draft_answer: str,
    memory: dict,
    product_cards: list[dict],
    retrieved_items: list,
    fallback: str,
    comparison: dict | None = None,
    client: ChatClient | None = None,
) -> GenerationResult:
    return _generate_result(
        messages=build_response_composer_messages(
            query=query,
            intent=intent,
            draft_answer=draft_answer,
            memory=memory,
            product_cards=product_cards,
            retrieved_items=retrieved_items,
            comparison=comparison,
        ),
        fallback=fallback,
        client=client,
    )


def stream_response_composer_result(
    *,
    query: str,
    intent: str,
    draft_answer: str,
    memory: dict,
    product_cards: list[dict],
    retrieved_items: list,
    fallback: str,
    comparison: dict | None = None,
    client: ChatClient | None = None,
) -> Iterator[GenerationDelta | GenerationComplete]:
    yield from _stream_result(
        messages=build_response_composer_messages(
            query=query,
            intent=intent,
            draft_answer=draft_answer,
            memory=memory,
            product_cards=product_cards,
            retrieved_items=retrieved_items,
            comparison=comparison,
        ),
        fallback=fallback,
        client=client,
    )


def generate_faq_result(
    *,
    query: str,
    hits: list[dict],
    fallback: str,
    client: ChatClient | None = None,
) -> GenerationResult:
    return _generate_result(
        messages=build_faq_messages(query=query, hits=hits),
        fallback=fallback,
        client=client,
    )


def _generate(*, messages: list[dict[str, str]], fallback: str, client: ChatClient | None) -> str:
    return _generate_result(messages=messages, fallback=fallback, client=client).content


def _generate_result(
    *,
    messages: list[dict[str, str]],
    fallback: str,
    client: ChatClient | None,
) -> GenerationResult:
    if client is None and not _has_provider_key():
        return GenerationResult(content=fallback, llm_enabled=False, llm_error="missing_api_key")
    started_at = time.perf_counter()
    resolved_client = client
    try:
        resolved_client = client or _build_default_client()
        answer = resolved_client.chat_sync(messages, temperature=0.2).strip()
        latency_ms = max(int((time.perf_counter() - started_at) * 1000), 0)
        if not answer:
            return GenerationResult(
                content=fallback,
                llm_enabled=False,
                llm_error="empty_response",
                provider=_client_provider(resolved_client),
                model=_client_model(resolved_client),
                latency_ms=latency_ms,
                cost_estimate=_estimate_cost(messages, fallback),
            )
        return GenerationResult(
            content=answer,
            llm_enabled=True,
            provider=_client_provider(resolved_client),
            model=_client_model(resolved_client),
            latency_ms=latency_ms,
            cost_estimate=_estimate_cost(messages, answer),
        )
    except Exception as error:
        latency_ms = max(int((time.perf_counter() - started_at) * 1000), 0)
        return GenerationResult(
            content=fallback,
            llm_enabled=False,
            llm_error=_format_llm_error(error),
            provider=_client_provider(resolved_client),
            model=_client_model(resolved_client),
            latency_ms=latency_ms,
            cost_estimate=_estimate_cost(messages, fallback),
        )


def _stream_result(
    *,
    messages: list[dict[str, str]],
    fallback: str,
    client: ChatClient | None,
) -> Iterator[GenerationDelta | GenerationComplete]:
    if client is None and not _has_provider_key():
        if fallback:
            yield GenerationDelta(fallback)
        yield GenerationComplete(GenerationResult(content=fallback, llm_enabled=False, llm_error="missing_api_key"))
        return

    started_at = time.perf_counter()
    resolved_client = client
    chunks: list[str] = []
    try:
        resolved_client = client or _build_default_client()
        stream_chat = getattr(resolved_client, "stream_chat_sync", None)
        if stream_chat is None:
            generation = _generate_result(messages=messages, fallback=fallback, client=resolved_client)
            if generation.content:
                yield GenerationDelta(generation.content)
            yield GenerationComplete(generation)
            return

        for chunk in stream_chat(messages, temperature=0.2):
            text = str(chunk or "")
            if not text:
                continue
            chunks.append(text)
            yield GenerationDelta(text)

        latency_ms = max(int((time.perf_counter() - started_at) * 1000), 0)
        answer = "".join(chunks).strip()
        if not answer:
            if fallback:
                yield GenerationDelta(fallback)
            yield GenerationComplete(
                GenerationResult(
                    content=fallback,
                    llm_enabled=False,
                    llm_error="empty_response",
                    provider=_client_provider(resolved_client),
                    model=_client_model(resolved_client),
                    latency_ms=latency_ms,
                    cost_estimate=_estimate_cost(messages, fallback),
                )
            )
            return
        yield GenerationComplete(
            GenerationResult(
                content=answer,
                llm_enabled=True,
                provider=_client_provider(resolved_client),
                model=_client_model(resolved_client),
                latency_ms=latency_ms,
                cost_estimate=_estimate_cost(messages, answer),
            )
        )
    except Exception as error:
        latency_ms = max(int((time.perf_counter() - started_at) * 1000), 0)
        partial = "".join(chunks).strip()
        content = partial or fallback
        if not partial and fallback:
            yield GenerationDelta(fallback)
        yield GenerationComplete(
            GenerationResult(
                content=content,
                llm_enabled=False,
                llm_error=_format_llm_error(error),
                provider=_client_provider(resolved_client),
                model=_client_model(resolved_client),
                latency_ms=latency_ms,
                cost_estimate=_estimate_cost(messages, content),
            )
        )


def _build_default_client() -> ChatClient:
    return OpenAICompatibleClient()


def _has_provider_key() -> bool:
    if not _env_bool("LLM_ENABLED", True):
        return False
    return bool(
        os.getenv("LLM_BASE_URL")
        or os.getenv("DOUBAO_BASE_URL")
        or os.getenv("LLM_API_KEY")
        or os.getenv("DOUBAO_API_KEY")
        or os.getenv("ARK_API_KEY")
    )


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _format_llm_error(error: Exception) -> str:
    if isinstance(error, httpx.HTTPStatusError):
        body = error.response.text.replace("\n", " ")[:500]
        return f"http_{error.response.status_code}: {body}"
    return f"{type(error).__name__}: {str(error)[:500]}"


def _client_provider(client: ChatClient | None) -> str:
    if client is None:
        return os.getenv("LLM_PROVIDER", "openai_compatible")
    return str(getattr(client, "provider", "") or os.getenv("LLM_PROVIDER", "openai_compatible"))


def _client_model(client: ChatClient | None) -> str:
    if client is None:
        return os.getenv("LLM_MODEL") or os.getenv("DOUBAO_MODEL") or ""
    return str(getattr(client, "model", "") or os.getenv("LLM_MODEL") or os.getenv("DOUBAO_MODEL") or "")


def _estimate_cost(messages: list[dict[str, str]], output: str) -> dict[str, float | int | str]:
    input_chars = sum(len(str(message.get("content", ""))) for message in messages)
    output_chars = len(output or "")
    input_tokens = max(input_chars // 2, 1)
    output_tokens = max(output_chars // 2, 1)
    input_rate = _env_float("LLM_ESTIMATED_INPUT_COST_PER_1K", 0.0)
    output_rate = _env_float("LLM_ESTIMATED_OUTPUT_COST_PER_1K", 0.0)
    estimated = input_tokens / 1000 * input_rate + output_tokens / 1000 * output_rate
    return {
        "currency": os.getenv("LLM_COST_CURRENCY", "CNY"),
        "input_tokens_estimate": input_tokens,
        "output_tokens_estimate": output_tokens,
        "estimated_cost": round(estimated, 8),
    }


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default
