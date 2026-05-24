from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass


@dataclass
class _Bucket:
    tokens: float
    updated_at: float


class TokenBucketRateLimiter:
    def __init__(
        self,
        *,
        rate_per_minute: float = 60.0,
        burst_capacity: float = 20.0,
    ):
        if rate_per_minute <= 0:
            raise ValueError("rate_per_minute must be greater than zero")
        if burst_capacity <= 0:
            raise ValueError("burst_capacity must be greater than zero")

        self.rate_per_second = rate_per_minute / 60.0
        self.burst_capacity = burst_capacity
        self._buckets: dict[str, _Bucket] = {}
        self._lock = asyncio.Lock()

    async def allow(self, key: str, *, cost: float = 1.0) -> bool:
        if cost <= 0:
            raise ValueError("cost must be greater than zero")

        now = time.time()
        async with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = _Bucket(tokens=self.burst_capacity, updated_at=now)
                self._buckets[key] = bucket

            elapsed = max(0.0, now - bucket.updated_at)
            bucket.tokens = min(
                self.burst_capacity,
                bucket.tokens + (elapsed * self.rate_per_second),
            )
            bucket.updated_at = now

            if bucket.tokens < cost:
                return False

            bucket.tokens -= cost
            return True

    async def get_snapshot(self, key: str) -> dict:
        now = time.time()
        async with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                return {
                    "tokens_available": self.burst_capacity,
                    "burst_capacity": self.burst_capacity,
                    "rate_per_minute": self.rate_per_second * 60.0,
                }

            elapsed = max(0.0, now - bucket.updated_at)
            tokens = min(
                self.burst_capacity,
                bucket.tokens + (elapsed * self.rate_per_second),
            )
            return {
                "tokens_available": tokens,
                "burst_capacity": self.burst_capacity,
                "rate_per_minute": self.rate_per_second * 60.0,
            }
