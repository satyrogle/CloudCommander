from __future__ import annotations

import asyncio
import time
from collections import deque


class BackpressureManager:
    def __init__(self, window_seconds: int = 60, limit_rho: float = 0.95):
        self.window_seconds = window_seconds
        self.limit_rho = limit_rho
        self.arrivals = deque()
        self.completions = deque()
        self._lock = asyncio.Lock()

    async def record_arrival(self) -> None:
        now = time.time()
        async with self._lock:
            self.arrivals.append(now)
            self._prune(now)

    async def record_completion(self) -> None:
        now = time.time()
        async with self._lock:
            self.completions.append(now)
            self._prune(now)

    async def get_snapshot(self) -> dict:
        now = time.time()
        async with self._lock:
            self._prune(now)
            lambda_rate = len(self.arrivals) / self.window_seconds
            mu_rate = len(self.completions) / self.window_seconds

        if mu_rate == 0:
            rho = 1.0 if lambda_rate > 0 else 0.0
        else:
            rho = lambda_rate / mu_rate

        return {
            "arrival_rate_hz": lambda_rate,
            "service_rate_hz": mu_rate,
            "utilization_rho": rho,
            "is_overloaded": rho >= self.limit_rho,
            "limit_rho": self.limit_rho,
        }

    async def is_overloaded(self) -> bool:
        snapshot = await self.get_snapshot()
        return snapshot["is_overloaded"]

    def _prune(self, current_time: float) -> None:
        cutoff = current_time - self.window_seconds
        while self.arrivals and self.arrivals[0] < cutoff:
            self.arrivals.popleft()
        while self.completions and self.completions[0] < cutoff:
            self.completions.popleft()
