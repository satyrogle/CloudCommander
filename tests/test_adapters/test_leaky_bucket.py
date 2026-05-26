import asyncio
import time

import pytest

from app.infrastructure.adapters.base import EgressBucketSaturated, LeakyBucketAdapter


@pytest.mark.asyncio
async def test_leaky_bucket_enforces_dispatch_pacing():
    dispatch_rate_hz = 20.0
    request_count = 10
    bucket = LeakyBucketAdapter(dispatch_rate_hz=dispatch_rate_hz, burst_capacity=20)
    await bucket.start()
    execution_timestamps: list[float] = []

    async def fake_call(index: int) -> int:
        execution_timestamps.append(time.monotonic())
        return index

    started_at = time.monotonic()
    try:
        results = await asyncio.gather(
            *[bucket.execute(fake_call, i) for i in range(request_count)]
        )
    finally:
        await bucket.stop()
    finished_at = time.monotonic()

    assert results == list(range(request_count))
    assert len(execution_timestamps) == request_count
    assert (finished_at - started_at) >= (request_count / dispatch_rate_hz) - 0.01


@pytest.mark.asyncio
async def test_leaky_bucket_sheds_when_burst_capacity_is_exceeded():
    bucket = LeakyBucketAdapter(dispatch_rate_hz=1.0, burst_capacity=5)
    await bucket.start()

    async def fake_call(_: int) -> int:
        return 1

    tasks = [asyncio.create_task(bucket.execute(fake_call, i)) for i in range(6)]
    try:
        results = await asyncio.gather(*tasks, return_exceptions=True)
    finally:
        await bucket.stop()

    saturated_errors = [r for r in results if isinstance(r, EgressBucketSaturated)]
    assert len(saturated_errors) == 1
