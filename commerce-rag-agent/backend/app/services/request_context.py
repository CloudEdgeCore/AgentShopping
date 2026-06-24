import time
import uuid
from contextvars import ContextVar


_request_id: ContextVar[str] = ContextVar("request_id", default="")
_request_started_at: ContextVar[float] = ContextVar("request_started_at", default=0.0)


def start_request(request_id: str | None = None) -> str:
    resolved = (request_id or "").strip() or f"req_{uuid.uuid4().hex[:16]}"
    _request_id.set(resolved)
    _request_started_at.set(time.perf_counter())
    return resolved


def get_request_id() -> str:
    return _request_id.get("")


def get_elapsed_ms() -> int:
    started_at = _request_started_at.get(0.0)
    if started_at <= 0:
        return 0
    return max(int((time.perf_counter() - started_at) * 1000), 0)
