"""Fixed-window rate limiting for the extraction API (Phase 4).

Fixed-window counter (rag_kb's pattern): one Redis key per (identity, window)
incremented per request, rejected past the limit. Simpler than a sliding
window and sufficient for API throttling; the fixed-window boundary burst
(up to 2x at a window edge) is accepted here, sliding-window precision
deferred until actually needed.

Identity is the JWT sub when authenticated, else the client IP. Backend is a
Counter protocol so production injects Redis and tests inject an in-memory
fake -- fully offline-testable, no Redis required for the logic. Disabled
when REDIS_URL is unset (dev convenience, as with auth).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol


class WindowCounter(Protocol):
    def incr_in_window(self, key: str, window_seconds: int) -> int:
        """Increment the counter for key, (re)set its TTL, return the new count."""
        ...


class InMemoryCounter:
    """Test/dev backend: fixed-window counts in a dict with wall-clock expiry."""

    def __init__(self) -> None:
        self._counts: dict[str, tuple[int, float]] = {}

    def incr_in_window(self, key: str, window_seconds: int) -> int:
        now = time.time()
        count, expiry = self._counts.get(key, (0, 0.0))
        if now >= expiry:
            count, expiry = 0, now + window_seconds
        count += 1
        self._counts[key] = (count, expiry)
        return count


class RedisCounter:
    """Production backend: INCR + EXPIRE on a per-window key."""

    def __init__(self, client: object) -> None:
        self._client = client

    def incr_in_window(self, key: str, window_seconds: int) -> int:
        # INCR returns the post-increment value; set EXPIRE only on first hit
        # (value == 1) so the window does not slide forward on every request.
        count = self._client.incr(key)  # type: ignore[attr-defined]
        if count == 1:
            self._client.expire(key, window_seconds)  # type: ignore[attr-defined]
        return int(count)


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    count: int
    limit: int
    retry_after: int


class RateLimiter:
    def __init__(self, counter: WindowCounter, limit_per_minute: int) -> None:
        self._counter = counter
        self._limit = limit_per_minute
        self._window = 60

    def check(self, identity: str, now: float | None = None) -> RateLimitDecision:
        now = time.time() if now is None else now
        window_epoch = int(now) // self._window
        key = f"ratelimit:{identity}:{window_epoch}"
        count = self._counter.incr_in_window(key, self._window)
        allowed = count <= self._limit
        retry_after = 0 if allowed else self._window - (int(now) % self._window)
        return RateLimitDecision(
            allowed=allowed, count=count, limit=self._limit, retry_after=retry_after
        )
