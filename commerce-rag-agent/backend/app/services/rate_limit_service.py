import os
import time
from collections import defaultdict, deque
from dataclasses import dataclass


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    limit: int
    remaining: int
    retry_after_seconds: int = 0


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, *, limit: int, window_seconds: int) -> RateLimitDecision:
        now = time.monotonic()
        events = self._events[key]
        cutoff = now - window_seconds
        while events and events[0] <= cutoff:
            events.popleft()

        if len(events) >= limit:
            retry_after = max(int(window_seconds - (now - events[0])) + 1, 1)
            return RateLimitDecision(
                allowed=False,
                limit=limit,
                remaining=0,
                retry_after_seconds=retry_after,
            )

        events.append(now)
        return RateLimitDecision(
            allowed=True,
            limit=limit,
            remaining=max(limit - len(events), 0),
        )


limiter = InMemoryRateLimiter()


def rate_limit_enabled() -> bool:
    return _env_bool("RATE_LIMIT_ENABLED", True)


def rate_limit_per_minute() -> int:
    return max(_env_int("RATE_LIMIT_PER_MINUTE", 120), 1)


def exempt_path(path: str) -> bool:
    defaults = ["/health", "/docs", "/openapi.json", "/static"]
    configured = [
        item.strip()
        for item in os.getenv("RATE_LIMIT_EXEMPT_PATHS", "").split(",")
        if item.strip()
    ]
    return any(path == item or path.startswith(f"{item}/") for item in [*defaults, *configured])


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
