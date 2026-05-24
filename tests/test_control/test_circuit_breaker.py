import pytest

from app.control.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError


@pytest.mark.asyncio
async def test_circuit_breaker_trips_after_threshold(monkeypatch):
    monkeypatch.setattr("app.control.circuit_breaker.time.time", lambda: 1000.0)
    breaker = CircuitBreaker(failure_threshold=2, failure_window_seconds=60)

    await breaker.record_failure()
    await breaker.record_failure()

    snapshot = await breaker.get_snapshot()
    assert snapshot["state"] == "open"
    with pytest.raises(CircuitBreakerOpenError):
        await breaker.before_call()


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_then_closes(monkeypatch):
    ticks = iter([1000.0, 1121.0, 1121.0, 1121.0, 1121.0, 1121.0])
    monkeypatch.setattr("app.control.circuit_breaker.time.time", lambda: next(ticks))
    breaker = CircuitBreaker(
        failure_threshold=1,
        failure_window_seconds=60,
        half_open_after_seconds=120,
        close_after_successes=2,
    )

    await breaker.record_failure()
    await breaker.before_call()
    assert (await breaker.get_snapshot())["state"] == "half_open"

    await breaker.record_success()
    await breaker.record_success()

    assert (await breaker.get_snapshot())["state"] == "closed"


@pytest.mark.asyncio
async def test_circuit_breaker_reopens_on_half_open_failure(monkeypatch):
    ticks = iter([1000.0, 1121.0, 1121.0, 1121.0])
    monkeypatch.setattr("app.control.circuit_breaker.time.time", lambda: next(ticks))
    breaker = CircuitBreaker(
        failure_threshold=1,
        failure_window_seconds=60,
        half_open_after_seconds=120,
    )

    await breaker.record_failure()
    await breaker.before_call()
    await breaker.record_failure()

    assert (await breaker.get_snapshot())["state"] == "open"
