from __future__ import annotations

import asyncio
import time
from collections import deque

from app.control.token_bucket import TokenBucketRateLimiter


class BackpressureManager:
    def __init__(
        self,
        window_seconds: int = 60,
        limit_rho: float = 0.95,
        ema_alpha: float = 0.3,
        token_rate_per_minute: float = 60.0,
        token_burst_capacity: float = 20.0,
    ):
        self.window_seconds = window_seconds
        self.limit_rho = limit_rho
        if ema_alpha <= 0 or ema_alpha > 1:
            raise ValueError("ema_alpha must be within (0, 1]")
        self.ema_alpha = ema_alpha
        self._ema_arrival_rate_hz = 0.0
        self._ema_service_rate_hz = 0.0
        self._ema_utilization_rho = 0.0
        self.tenant_rate_limiter = TokenBucketRateLimiter(
            rate_per_minute=token_rate_per_minute,
            burst_capacity=token_burst_capacity,
        )
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

            ema_lambda = self._update_ema("_ema_arrival_rate_hz", lambda_rate)
            ema_mu = self._update_ema("_ema_service_rate_hz", mu_rate)
            ema_rho = self._update_ema("_ema_utilization_rho", rho)

        return {
            "arrival_rate_hz": lambda_rate,
            "service_rate_hz": mu_rate,
            "utilization_rho": rho,
            "raw_arrival_rate_hz": lambda_rate,
            "raw_service_rate_hz": mu_rate,
            "raw_utilization_rho": rho,
            "ema_arrival_rate_hz": ema_lambda,
            "ema_service_rate_hz": ema_mu,
            "ema_utilization_rho": ema_rho,
            "is_overloaded": rho >= self.limit_rho,
            "limit_rho": self.limit_rho,
        }

    async def is_overloaded(self) -> bool:
        snapshot = await self.get_snapshot()
        return snapshot["is_overloaded"]

    async def check_tenant_rate_limit(self, tenant_id: str) -> bool:
        return await self.tenant_rate_limiter.allow(tenant_id)

    def _prune(self, current_time: float) -> None:
        cutoff = current_time - self.window_seconds
        while self.arrivals and self.arrivals[0] < cutoff:
            self.arrivals.popleft()
        while self.completions and self.completions[0] < cutoff:
            self.completions.popleft()

    def _update_ema(self, attr_name: str, value: float) -> float:
        current = getattr(self, attr_name)
        updated = (self.ema_alpha * value) + ((1.0 - self.ema_alpha) * current)
        setattr(self, attr_name, updated)
        return updated
