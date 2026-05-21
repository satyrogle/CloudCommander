from __future__ import annotations

import asyncio
from typing import Any, Dict

from app.infrastructure.adapters.base import CloudAdapter


class MockAWSAdapter(CloudAdapter):
    async def apply_allocation(self, aggregate_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        _ = aggregate_id
        reason_code = payload.get("reason_code", "")

        await asyncio.sleep(0.1)

        if reason_code == "trigger-throttle":
            return {
                "status": "throttled",
                "nodes_success": 0,
                "nodes_failed": 4,
                "provider_message": "Rate exceeded (Service: AmazonEC2; Status Code: 403; Error Code: RequestLimitExceeded)",
            }

        if reason_code == "trigger-partial":
            return {
                "status": "partial_failure",
                "nodes_success": 3,
                "nodes_failed": 1,
                "provider_message": "InsufficientInstanceCapacity on 1/4 requested nodes",
            }

        if reason_code == "trigger-timeout":
            return {
                "status": "timeout",
                "nodes_success": 0,
                "nodes_failed": 4,
                "provider_message": "Connection timed out",
            }

        return {
            "status": "success",
            "nodes_success": 4,
            "nodes_failed": 0,
            "provider_message": "OK",
        }
