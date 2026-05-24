import pytest

from app.control.backpressure_manager import BackpressureManager


@pytest.mark.asyncio
async def test_backpressure_snapshot_includes_raw_and_ema(monkeypatch):
    monkeypatch.setattr("app.control.backpressure_manager.time.time", lambda: 1000.0)
    manager = BackpressureManager(window_seconds=10, limit_rho=0.95, ema_alpha=0.5)

    await manager.record_arrival()
    await manager.record_completion()

    snapshot = await manager.get_snapshot()

    assert snapshot["raw_arrival_rate_hz"] == 0.1
    assert snapshot["raw_service_rate_hz"] == 0.1
    assert snapshot["raw_utilization_rho"] == 1.0
    assert snapshot["ema_arrival_rate_hz"] == 0.05
    assert snapshot["ema_service_rate_hz"] == 0.05
    assert snapshot["ema_utilization_rho"] == 0.5


@pytest.mark.asyncio
async def test_ema_does_not_drive_overload_decision(monkeypatch):
    ticks = iter([1000.0, 1000.0, 1011.0])
    monkeypatch.setattr("app.control.backpressure_manager.time.time", lambda: next(ticks))
    manager = BackpressureManager(window_seconds=10, limit_rho=0.95, ema_alpha=0.5)

    await manager.record_arrival()
    first = await manager.get_snapshot()
    second = await manager.get_snapshot()

    assert first["is_overloaded"] is True
    assert second["raw_utilization_rho"] == 0.0
    assert second["ema_utilization_rho"] > 0.0
    assert second["is_overloaded"] is False
