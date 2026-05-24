from __future__ import annotations

import asyncio
import os
from typing import Any, Dict

from app.infrastructure.adapters.base import CloudAdapter


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class MockAWSAdapter(CloudAdapter):
    def __init__(
        self,
        *,
        chaos_enabled: bool | None = None,
        chaos_r: float | None = None,
        chaos_x: float | None = None,
        chaos_min_delay_sec: float | None = None,
        chaos_max_delay_sec: float | None = None,
    ):
        self.chaos_enabled = (
            _env_flag("MOCK_AWS_CHAOS_ENABLED", False)
            if chaos_enabled is None
            else chaos_enabled
        )
        self.chaos_r = float(os.getenv("MOCK_AWS_CHAOS_R", "3.7")) if chaos_r is None else chaos_r
        self.chaos_x = float(os.getenv("MOCK_AWS_CHAOS_X0", "0.42")) if chaos_x is None else chaos_x
        self.chaos_min_delay_sec = (
            float(os.getenv("MOCK_AWS_CHAOS_MIN_DELAY_SEC", "0.05"))
            if chaos_min_delay_sec is None
            else chaos_min_delay_sec
        )
        self.chaos_max_delay_sec = (
            float(os.getenv("MOCK_AWS_CHAOS_MAX_DELAY_SEC", "0.25"))
            if chaos_max_delay_sec is None
            else chaos_max_delay_sec
        )
        self._chaos_lock = asyncio.Lock()

    async def _next_chaos_value(self) -> float:
        async with self._chaos_lock:
            x = self.chaos_x
            x = max(1e-6, min(1 - 1e-6, x))
            r = max(0.0, min(4.0, self.chaos_r))
            next_x = r * x * (1 - x)
            self.chaos_x = max(1e-6, min(1 - 1e-6, next_x))
            return self.chaos_x

    async def _apply_chaos_profile(self) -> Dict[str, Any]:
        chaos = await self._next_chaos_value()
        delay = self.chaos_min_delay_sec + (
            max(0.0, self.chaos_max_delay_sec - self.chaos_min_delay_sec) * chaos
        )
        await asyncio.sleep(delay)

        if chaos >= 0.90:
            return {
                "status": "timeout",
                "nodes_success": 0,
                "nodes_failed": 4,
                "provider_message": f"Chaos timeout (x={chaos:.4f})",
            }
        if chaos >= 0.80:
            return {
                "status": "throttled",
                "nodes_success": 0,
                "nodes_failed": 4,
                "provider_message": f"Chaos throttling (x={chaos:.4f})",
            }
        if chaos >= 0.65:
            return {
                "status": "partial_failure",
                "nodes_success": 3,
                "nodes_failed": 1,
                "provider_message": f"Chaos partial capacity loss (x={chaos:.4f})",
            }
        return {
            "status": "success",
            "nodes_success": 4,
            "nodes_failed": 0,
            "provider_message": f"Chaos stable window (x={chaos:.4f})",
        }

    async def apply_allocation(self, aggregate_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        _ = aggregate_id
        reason_code = payload.get("reason_code", "")

        if reason_code == "trigger-throttle":
            await asyncio.sleep(0.1)
            return {
                "status": "throttled",
                "nodes_success": 0,
                "nodes_failed": 4,
                "provider_message": "Rate exceeded (Service: AmazonEC2; Status Code: 403; Error Code: RequestLimitExceeded)",
            }

        if reason_code == "trigger-partial":
            await asyncio.sleep(0.1)
            return {
                "status": "partial_failure",
                "nodes_success": 3,
                "nodes_failed": 1,
                "provider_message": "InsufficientInstanceCapacity on 1/4 requested nodes",
            }

        if reason_code == "trigger-timeout":
            await asyncio.sleep(0.1)
            return {
                "status": "timeout",
                "nodes_success": 0,
                "nodes_failed": 4,
                "provider_message": "Connection timed out",
            }

        if self.chaos_enabled:
            return await self._apply_chaos_profile()

        await asyncio.sleep(0.1)
        return {
            "status": "success",
            "nodes_success": 4,
            "nodes_failed": 0,
            "provider_message": "OK",
        }
