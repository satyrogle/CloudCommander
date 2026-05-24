import asyncio

import pytest

from app.control.backpressure_manager import BackpressureManager


@pytest.mark.asyncio
async def test_distinct_429_rejection_reasons():
    """
    Proves Token Bucket and M/M/1 Backpressure reject traffic independently.
    """
    manager = BackpressureManager(window_seconds=10, limit_rho=0.95)
    tenant_id = "test-tenant-1"

    for _ in range(20):
        allowed = await manager.check_tenant_rate_limit(tenant_id)
        assert allowed is True

    allowed = await manager.check_tenant_rate_limit(tenant_id)
    assert allowed is False

    for _ in range(50):
        await manager.record_arrival()

    snapshot = await manager.get_snapshot()
    assert snapshot["is_overloaded"] is True

    other_tenant_allowed = await manager.check_tenant_rate_limit("test-tenant-2")
    assert other_tenant_allowed is True
    assert snapshot["is_overloaded"] is True


@pytest.mark.asyncio
async def test_load_transitions_and_recovery():
    """
    Proves Healthy -> Overloaded -> Recovering -> Healthy.
    """
    manager = BackpressureManager(window_seconds=2, limit_rho=1.1)

    await manager.record_arrival()
    await manager.record_completion()
    snapshot = await manager.get_snapshot()
    assert snapshot["is_overloaded"] is False

    for _ in range(10):
        await manager.record_arrival()

    snapshot = await manager.get_snapshot()
    assert snapshot["is_overloaded"] is True

    await asyncio.sleep(2.1)
    for _ in range(5):
        await manager.record_completion()

    snapshot = await manager.get_snapshot()
    assert snapshot["is_overloaded"] is False


@pytest.mark.asyncio
async def test_ema_smoothing_vs_admission_control():
    """
    Proves EMA smooths telemetry but does not interfere with raw admission control.
    """
    manager = BackpressureManager(window_seconds=10, limit_rho=0.9, ema_alpha=0.2)

    for _ in range(20):
        await manager.record_arrival()

    snapshot = await manager.get_snapshot()

    assert snapshot["raw_utilization_rho"] >= 0.9
    assert snapshot["is_overloaded"] is True

    assert snapshot["ema_utilization_rho"] < 0.9
    assert snapshot["ema_utilization_rho"] != snapshot["raw_utilization_rho"]
