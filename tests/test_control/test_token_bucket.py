import pytest

from app.control.token_bucket import TokenBucketRateLimiter


@pytest.mark.asyncio
async def test_token_bucket_allows_burst_then_rejects(monkeypatch):
    monkeypatch.setattr("app.control.token_bucket.time.time", lambda: 1000.0)
    limiter = TokenBucketRateLimiter(rate_per_minute=60, burst_capacity=2)

    assert await limiter.allow("tenant-a") is True
    assert await limiter.allow("tenant-a") is True
    assert await limiter.allow("tenant-a") is False


@pytest.mark.asyncio
async def test_token_bucket_refills_over_time(monkeypatch):
    ticks = iter([1000.0, 1000.0, 1001.0])
    monkeypatch.setattr("app.control.token_bucket.time.time", lambda: next(ticks))
    limiter = TokenBucketRateLimiter(rate_per_minute=60, burst_capacity=1)

    assert await limiter.allow("tenant-a") is True
    assert await limiter.allow("tenant-a") is False
    assert await limiter.allow("tenant-a") is True


@pytest.mark.asyncio
async def test_token_bucket_isolates_tenants(monkeypatch):
    monkeypatch.setattr("app.control.token_bucket.time.time", lambda: 1000.0)
    limiter = TokenBucketRateLimiter(rate_per_minute=60, burst_capacity=1)

    assert await limiter.allow("tenant-a") is True
    assert await limiter.allow("tenant-a") is False
    assert await limiter.allow("tenant-b") is True
