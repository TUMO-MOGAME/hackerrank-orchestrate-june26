"""Exponential-backoff retry wrapper for transient provider errors (429, 503, timeouts).

Backoff schedule: base_delay * 2**attempt → 2s, 4s, 8s; up to `max_retries` retries; then
re-raise so the caller can emit a degraded row. Only TRANSIENT errors are retried — a
programming error or a 400 bad-request is raised immediately, not retried into the ground.
`sleeper` is injectable so tests run instantly.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")

# HTTP status codes worth retrying (rate limit / transient server / timeout).
_TRANSIENT_CODES = {408, 409, 425, 429, 500, 502, 503, 504}
# Substrings that mark a transient failure when no status code is available.
_TRANSIENT_MARKERS = (
    "429", "500", "502", "503", "504", "unavailable", "overloaded", "timeout",
    "timed out", "temporarily", "rate limit", "try again", "deadline", "connection reset",
)


def is_transient(exc: BaseException) -> bool:
    """True if `exc` looks like a retryable transient error."""
    code = getattr(exc, "code", None)
    if not isinstance(code, int):
        code = getattr(exc, "status_code", None)
    if isinstance(code, int) and code in _TRANSIENT_CODES:
        return True
    msg = str(exc).lower()
    return any(marker in msg for marker in _TRANSIENT_MARKERS)


def with_backoff(
    fn: Callable[[], T],
    *,
    max_retries: int = 3,
    base_delay: float = 2.0,
    sleeper: Callable[[float], None] = time.sleep,
    transient: Callable[[BaseException], bool] = is_transient,
) -> T:
    """Call `fn()`, retrying transient failures with exponential backoff."""
    attempt = 0
    while True:
        try:
            return fn()
        except Exception as exc:
            if attempt >= max_retries or not transient(exc):
                raise
            sleeper(base_delay * (2 ** attempt))
            attempt += 1
