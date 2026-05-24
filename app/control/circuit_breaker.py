from __future__ import annotations

import asyncio
import time
from collections import deque


class CircuitBreakerOpenError(Exception):
    pass


class CircuitBreaker:
    def __init__(
        self,
        *,
        failure_threshold: int = 5,
        failure_window_seconds: int = 60,
        half_open_after_seconds: int = 120,
        close_after_successes: int = 2,
    ):
        if failure_threshold <= 0:
            raise ValueError("failure_threshold must be greater than zero")
        if failure_window_seconds <= 0:
            raise ValueError("failure_window_seconds must be greater than zero")
        if half_open_after_seconds <= 0:
            raise ValueError("half_open_after_seconds must be greater than zero")
        if close_after_successes <= 0:
            raise ValueError("close_after_successes must be greater than zero")

        self.failure_threshold = failure_threshold
        self.failure_window_seconds = failure_window_seconds
        self.half_open_after_seconds = half_open_after_seconds
        self.close_after_successes = close_after_successes
        self._state = "closed"
        self._failures = deque()
        self._opened_at: float | None = None
        self._half_open_successes = 0
        self._lock = asyncio.Lock()

    async def before_call(self) -> None:
        now = time.time()
        async with self._lock:
            self._prune(now)
            if self._state == "open":
                assert self._opened_at is not None
                if now - self._opened_at >= self.half_open_after_seconds:
                    self._state = "half_open"
                    self._half_open_successes = 0
                    return
                raise CircuitBreakerOpenError("Reconciler circuit breaker is open")

    async def record_success(self) -> None:
        now = time.time()
        async with self._lock:
            self._prune(now)
            if self._state == "half_open":
                self._half_open_successes += 1
                if self._half_open_successes >= self.close_after_successes:
                    self._state = "closed"
                    self._failures.clear()
                    self._opened_at = None
                    self._half_open_successes = 0
                return

            if self._state == "closed":
                self._failures.clear()

    async def record_failure(self) -> None:
        now = time.time()
        async with self._lock:
            self._prune(now)
            if self._state == "half_open":
                self._open(now)
                return

            self._failures.append(now)
            if len(self._failures) >= self.failure_threshold:
                self._open(now)

    async def get_snapshot(self) -> dict:
        now = time.time()
        async with self._lock:
            self._prune(now)
            next_retry_at = None
            if self._state == "open" and self._opened_at is not None:
                next_retry_at = self._opened_at + self.half_open_after_seconds
            return {
                "state": self._state,
                "recent_failure_count": len(self._failures),
                "opened_at": self._opened_at,
                "next_retry_at": next_retry_at,
            }

    def _open(self, now: float) -> None:
        self._state = "open"
        self._opened_at = now
        self._half_open_successes = 0

    def _prune(self, now: float) -> None:
        cutoff = now - self.failure_window_seconds
        while self._failures and self._failures[0] < cutoff:
            self._failures.popleft()
