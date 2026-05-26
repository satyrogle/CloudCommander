from __future__ import annotations

import asyncio
import time

import pytest

from app.control.circuit_breaker import CircuitBreaker
from app.infrastructure.adapters.base import EgressBucketSaturated
from app.infrastructure.adapters.mock_aws import MockAWSAdapter
from app.worker.reconciler import ReconcilerLoop


@pytest.mark.asyncio
async def test_reconciler_burst_is_smoothed_by_leaky_bucket():
    rate_hz = 10.0
    request_count = 20
    adapter = MockAWSAdapter(
        chaos_enabled=False,
        egress_rate_hz=rate_hz,
        egress_burst_capacity=100,
    )
    reconciler = ReconcilerLoop(adapter, circuit_breaker=CircuitBreaker(failure_threshold=1000))
    await adapter.start()

    started_at = time.monotonic()
    try:
        results = await asyncio.gather(
            *[
                reconciler.execute_intent(
                    f"evt-{i}",
                    f"agg-{i}",
                    {"reason_code": "standard-scale", "target_cpu_cores": 4},
                )
                for i in range(request_count)
            ]
        )
    finally:
        await adapter.stop()
    elapsed = time.monotonic() - started_at

    assert all(result == "completed" for result in results)
    assert elapsed >= (request_count / rate_hz) - 0.05


@pytest.mark.asyncio
async def test_reconciler_surfaces_egress_saturation_fast_fail():
    adapter = MockAWSAdapter(
        chaos_enabled=False,
        egress_rate_hz=1.0,
        egress_burst_capacity=2,
    )
    reconciler = ReconcilerLoop(adapter, circuit_breaker=CircuitBreaker(failure_threshold=1000))
    await adapter.start()

    try:
        results = await asyncio.gather(
            *[
                reconciler.execute_intent(
                    f"evt-{i}",
                    f"agg-{i}",
                    {"reason_code": "standard-scale", "target_cpu_cores": 4},
                )
                for i in range(4)
            ],
            return_exceptions=True,
        )
    finally:
        await adapter.stop()

    assert any(isinstance(result, EgressBucketSaturated) for result in results)
