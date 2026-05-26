from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict

from app.control.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError
from app.control.maut_rollback import RollbackDecisionEngine
from app.infrastructure.adapters.base import CloudAdapter

logger = logging.getLogger(__name__)

DEFAULT_MAUT_WEIGHTS = {
    "restore_time_normalized": 0.5,
    "operational_risk_normalized": 0.3,
    "infrastructure_cost_normalized": 0.2,
}

reconciler_circuit_breaker = CircuitBreaker()


class CyclicDependencyError(Exception):
    """Raised when the reconciliation plan contains cyclic dependencies."""


@dataclass(frozen=True)
class TaskNode:
    name: str
    func: Callable[..., Awaitable[Any]]
    args: tuple[Any, ...]
    kwargs: dict[str, Any]


class DAGExecutor:
    def __init__(self) -> None:
        self.nodes: dict[str, TaskNode] = {}
        self.adjacency_list: dict[str, list[str]] = {}
        self.in_degree: dict[str, int] = {}

    def add_node(
        self, name: str, func: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any
    ) -> None:
        self.nodes[name] = TaskNode(name=name, func=func, args=args, kwargs=kwargs)
        self.adjacency_list.setdefault(name, [])
        self.in_degree.setdefault(name, 0)

    def add_dependency(self, parent: str, child: str) -> None:
        if parent not in self.nodes or child not in self.nodes:
            raise ValueError("Both parent and child nodes must exist before wiring dependencies.")
        self.adjacency_list[parent].append(child)
        self.in_degree[child] = self.in_degree.get(child, 0) + 1

    def compute_topological_levels(self) -> list[list[TaskNode]]:
        in_deg = self.in_degree.copy()
        queue = [name for name, deg in in_deg.items() if deg == 0]
        levels: list[list[TaskNode]] = []
        visited_count = 0

        while queue:
            current_level: list[TaskNode] = []
            next_queue: list[str] = []

            for node_name in queue:
                current_level.append(self.nodes[node_name])
                visited_count += 1
                for neighbor in self.adjacency_list.get(node_name, []):
                    in_deg[neighbor] -= 1
                    if in_deg[neighbor] == 0:
                        next_queue.append(neighbor)

            levels.append(current_level)
            queue = next_queue

        if visited_count != len(self.nodes):
            raise CyclicDependencyError("Cyclic loop detected inside reconciliation task plan.")
        return levels

    async def execute(self) -> dict[str, Any]:
        levels = self.compute_topological_levels()
        results: dict[str, Any] = {}

        for level in levels:
            tasks = [node.func(*node.args, **node.kwargs) for node in level]
            level_results = await asyncio.gather(*tasks, return_exceptions=False)
            for node, result in zip(level, level_results):
                results[node.name] = result

        return results


class ReconcilerLoop:
    def __init__(
        self,
        adapter: CloudAdapter,
        decision_engine: RollbackDecisionEngine | None = None,
        circuit_breaker: CircuitBreaker | None = None,
    ):
        self.adapter = adapter
        self.decision_engine = decision_engine or RollbackDecisionEngine(weights=DEFAULT_MAUT_WEIGHTS)
        self.circuit_breaker = circuit_breaker or reconciler_circuit_breaker

    async def execute_plan(
        self, aggregate_id: str, plan_steps: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Executes a plan of adapter actions. If dependencies are present, uses
        DAG layering with per-level parallelism; otherwise falls back to sequential order.
        """
        executor = DAGExecutor()
        has_dependencies = False

        for step in plan_steps:
            step_name = step["name"]
            action = step["action"]
            payload = step.get("payload", {})
            target_aggregate_id = step.get("target_aggregate_id", aggregate_id)

            executor.add_node(
                step_name,
                self._execute_plan_action,
                action,
                target_aggregate_id,
                payload,
            )

        for step in plan_steps:
            dependencies = step.get("depends_on", []) or []
            if dependencies:
                has_dependencies = True
            for parent in dependencies:
                executor.add_dependency(parent, step["name"])

        if has_dependencies:
            return await executor.execute()

        legacy_results: dict[str, Any] = {}
        for step in plan_steps:
            node = executor.nodes[step["name"]]
            legacy_results[node.name] = await node.func(*node.args, **node.kwargs)
        return legacy_results

    async def _execute_plan_action(
        self, action: str, aggregate_id: str, payload: dict[str, Any]
    ) -> Dict[str, Any]:
        if action == "apply_allocation":
            return await self._call_adapter(self.adapter.apply_allocation, aggregate_id, payload)
        if action == "rollback_allocation":
            return await self._call_adapter(self.adapter.rollback_allocation, aggregate_id, payload)
        raise ValueError(f"Unsupported reconciliation action: {action}")

    async def execute_intent(self, event_id: str, aggregate_id: str, payload: Dict[str, Any]) -> str:
        logger.info("Reconciler dispatching intent for %s", aggregate_id)

        plan_steps = payload.get("plan_steps")
        if isinstance(plan_steps, list) and plan_steps:
            await self.execute_plan(aggregate_id, plan_steps)
            await self.circuit_breaker.record_success()
            logger.info("Intent %s DAG plan completed.", event_id)
            return "completed"

        result = await self._call_adapter(self.adapter.apply_allocation, aggregate_id, payload)
        self.decision_engine.observe_evidence(result["status"])

        if result["status"] == "success":
            logger.info("Intent %s succeeded.", event_id)
            await self.circuit_breaker.record_success()
            return "completed"

        if result["status"] == "partial_failure":
            await self.circuit_breaker.record_failure()
            return await self._handle_partial_failure(event_id, aggregate_id, result)

        if result["status"] in ["throttled", "timeout"]:
            await self.circuit_breaker.record_failure()
            logger.warning(
                "Intent %s hit transient failure: %s. Will retry via outbox.",
                event_id,
                result["status"],
            )
            raise Exception(f"Transient adapter failure: {result['status']}")

        await self.circuit_breaker.record_failure()
        return "failed"

    async def execute_rollback(self, event_id: str, aggregate_id: str, payload: Dict[str, Any]) -> str:
        logger.info("Reconciler dispatching rollback for %s", aggregate_id)

        result = await self._call_adapter(self.adapter.rollback_allocation, aggregate_id, payload)
        self.decision_engine.observe_evidence(result["status"])

        if result["status"] == "success":
            logger.info("Rollback %s succeeded.", event_id)
            await self.circuit_breaker.record_success()
            return "rollback_completed"

        if result["status"] in ["throttled", "timeout"]:
            await self.circuit_breaker.record_failure()
            logger.warning(
                "Rollback %s hit transient failure: %s. Will retry via outbox.",
                event_id,
                result["status"],
            )
            raise Exception(f"Transient adapter failure: {result['status']}")

        await self.circuit_breaker.record_failure()
        return "failed"

    async def _call_adapter(self, func, aggregate_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        await self.circuit_breaker.before_call()
        try:
            return await func(aggregate_id, payload)
        except CircuitBreakerOpenError:
            raise
        except Exception:
            await self.circuit_breaker.record_failure()
            raise

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

        best_strategy = self.decision_engine.evaluate_rollback_paths(available_paths)
        logger.info(
            "MAUT selected compensation strategy: %s with weights=%s posterior_infra_risk=%.3f",
            best_strategy,
            self.decision_engine.get_effective_weights(),
            self.decision_engine.posterior_infra_risk,
        )

        return f"compensating_via_{best_strategy}"
