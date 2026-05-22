from __future__ import annotations

import asyncio
import os
from pathlib import Path

import asyncpg
import pytest
import pytest_asyncio


ROOT_DIR = Path(__file__).resolve().parents[1]
MIGRATIONS = [
    ROOT_DIR / "migrations" / "001_initial_schema.sql",
    ROOT_DIR / "migrations" / "002_outbox_hardening.sql",
    ROOT_DIR / "migrations" / "003_event_hash_chain.sql",
    ROOT_DIR / "migrations" / "004_read_models_and_outbox_consistency.sql",
    ROOT_DIR / "migrations" / "005_event_actor_claims.sql",
]


RESET_SQL = """
TRUNCATE TABLE
    outbox,
    events,
    read_model_nodes,
    read_model_service_graph_edges,
    read_model_guardrail_alerts
RESTART IDENTITY
CASCADE
"""


async def _reset_tables(pool: asyncpg.Pool) -> None:
    # Retry once/twice for transient asyncpg "operation in progress" states.
    for attempt in range(3):
        try:
            async with pool.acquire() as conn:
                await conn.reset()
                await conn.execute(RESET_SQL)
            return
        except asyncpg.InterfaceError:
            if attempt == 2:
                raise
            await asyncio.sleep(0.05 * (attempt + 1))
            await pool.expire_connections()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def db_pool():
    """Provide an asyncpg pool with migrated schema for integration tests."""
    dsn = os.getenv("TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres")
    try:
        pool = await asyncpg.create_pool(dsn=dsn, min_size=1, max_size=4)
    except Exception as exc:
        pytest.skip(f"Postgres is not available for DB-backed tests: {exc}")

    async with pool.acquire() as conn:
        for migration_path in MIGRATIONS:
            await conn.execute(migration_path.read_text(encoding="utf-8"))

    try:
        yield pool
    finally:
        await pool.close()


@pytest_asyncio.fixture(loop_scope="session")
async def reset_db(db_pool: asyncpg.Pool):
    await _reset_tables(db_pool)
    yield
    # Ensure pooled connections are clean for the next test and fixture teardown.
    await db_pool.expire_connections()
