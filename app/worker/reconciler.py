from __future__ import annotations

import logging
from typing import Any, Dict

from app.control.maut_rollback import RollbackDecisionEngine
from app.infrastructure.adapters.base import CloudAdapter

logger = logging.getLogger(__name__)

maut_engine = RollbackDecisionEngine(
    weights={
        "restore_time_normalized": 0.5,
        "operational_risk_normalized": 0.3,
        "infrastructure_cost_normalized": 0.2,
    }
)


class ReconcilerLoop:
    def __init__(self, adapter: CloudAdapter):
        self.adapter = adapter

    async def execute_intent(self, event_id: str, aggregate_id: str, payload: Dict[str, Any]) -> str:
        logger.info("Reconciler dispatching intent for %s", aggregate_id)

        result = await self.adapter.apply_allocation(aggregate_id, payload)

        if result["status"] == "success":
            logger.info("Intent %s succeeded.", event_id)
            return "completed"

        if result["status"] == "partial_failure":
            return await self._handle_partial_failure(event_id, aggregate_id, result)

        if result["status"] in ["throttled", "timeout"]:
            logger.warning(
                "Intent %s hit transient failure: %s. Will retry via outbox.",
                event_id,
                result["status"],
            )
            raise Exception(f"Transient adapter failure: {result['status']}")

        return "failed"

    async def _handle_partial_failure(
        self, event_id: str, aggregate_id: str, context: Dict[str, Any]
    ) -> str:
        logger.warning(
            "Partial failure for %s: %s. Triggering MAUT.",
            aggregate_id,
            context["provider_message"],
        )

        available_paths = [
            {
                "strategy_id": "full_revert",
                "attributes": {
                    "restore_time_normalized": 0.8,
                    "operational_risk_normalized": 0.9,
                    "infrastructure_cost_normalized": 0.4,
                },
            },
            {
                "strategy_id": "forward_fix_retry",
                "attributes": {
                    "restore_time_normalized": 0.3,
                    "operational_risk_normalized": 0.4,
                    "infrastructure_cost_normalized": 0.9,
                },
            },
        ]

        best_strategy = maut_engine.evaluate_rollback_paths(available_paths)
        logger.info("MAUT selected compensation strategy: %s", best_strategy)

        return f"compensating_via_{best_strategy}"
