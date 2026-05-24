from __future__ import annotations

import pytest

from app.worker.projection_worker import create_pool_from_env, main


@pytest.mark.asyncio
async def test_create_pool_requires_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="DATABASE_URL must be set"):
        await create_pool_from_env()


@pytest.mark.asyncio
async def test_create_pool_uses_asyncpg(monkeypatch):
    sentinel_pool = object()

    async def _create_pool(*args, **kwargs):
        _ = args
        assert kwargs["dsn"] == "postgresql://postgres:postgres@localhost:5432/postgres"
        return sentinel_pool

    monkeypatch.setenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres")
    monkeypatch.setattr("app.worker.projection_worker.asyncpg.create_pool", _create_pool)
    pool = await create_pool_from_env()
    assert pool is sentinel_pool


@pytest.mark.asyncio
async def test_main_closes_pool_after_worker_stops(monkeypatch):
    class FakePool:
        def __init__(self):
            self.closed = False

        async def close(self):
            self.closed = True

    class FakeWorker:
        def __init__(self, pool):
            self.pool = pool

        async def run(self, stop_event=None):
            assert stop_event is not None
            stop_event.set()

    fake_pool = FakePool()

    async def _create_pool_from_env():
        return fake_pool

    monkeypatch.setattr(
        "app.worker.projection_worker.create_pool_from_env",
        _create_pool_from_env,
    )
    monkeypatch.setattr("app.worker.projection_worker.OutboxWorker", FakeWorker)
    monkeypatch.setattr("app.worker.projection_worker._install_shutdown_handlers", lambda _event: None)

    await main()

    assert fake_pool.closed is True
