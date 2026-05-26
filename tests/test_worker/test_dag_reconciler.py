from __future__ import annotations

import asyncio

import pytest

from app.control.circuit_breaker import CircuitBreaker
from app.infrastructure.adapters.mock_aws import MockAWSAdapter
from app.worker.reconciler import CyclicDependencyError, DAGExecutor, ReconcilerLoop


async def mock_task(duration: float, val: str, execution_log: list[str]) -> str:
    await asyncio.sleep(duration)
    execution_log.append(val)
    return f"processed_{val}"


@pytest.mark.asyncio
async def test_linear_chain_execution():
    executor = DAGExecutor()
    log: list[str] = []

    executor.add_node("step_1", mock_task, 0.01, "A", log)
    executor.add_node("step_2", mock_task, 0.01, "B", log)
    executor.add_dependency("step_1", "step_2")

    results = await executor.execute()

    assert log == ["A", "B"]
    assert results["step_2"] == "processed_B"


@pytest.mark.asyncio
async def test_fan_out_parallelism():
    executor = DAGExecutor()
    log: list[str] = []

    executor.add_node("root", mock_task, 0.01, "root", log)
    executor.add_node("left", mock_task, 0.05, "left", log)
    executor.add_node("right", mock_task, 0.01, "right", log)

    executor.add_dependency("root", "left")
    executor.add_dependency("root", "right")

    await executor.execute()

    assert log == ["root", "right", "left"]


@pytest.mark.asyncio
async def test_cycle_rejection():
    executor = DAGExecutor()
    log: list[str] = []

    executor.add_node("step_1", mock_task, 0.01, "A", log)
    executor.add_node("step_2", mock_task, 0.01, "B", log)

    executor.add_dependency("step_1", "step_2")
    executor.add_dependency("step_2", "step_1")

    with pytest.raises(CyclicDependencyError):
        executor.compute_topological_levels()


@pytest.mark.asyncio
async def test_reconciler_execute_plan_supports_legacy_no_dependency_path():
    adapter = MockAWSAdapter()
    reconciler = ReconcilerLoop(adapter, circuit_breaker=CircuitBreaker(failure_threshold=100))

    results = await reconciler.execute_plan(
        aggregate_id="agg-legacy",
        plan_steps=[
            {
                "name": "step_apply",
                "action": "apply_allocation",
                "payload": {"reason_code": "standard-scale"},
            }
        ],
    )

    assert "step_apply" in results
    assert results["step_apply"]["status"] == "success"
