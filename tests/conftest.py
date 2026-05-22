from __future__ import annotations

import os
<<<<<<< ours
<<<<<<< ours
from pathlib import Path
=======
>>>>>>> theirs
=======
>>>>>>> theirs

import asyncpg
import pytest


<<<<<<< ours
<<<<<<< ours
ROOT_DIR = Path(__file__).resolve().parents[1]
MIGRATIONS = [
    ROOT_DIR / "migrations" / "001_initial_schema.sql",
    ROOT_DIR / "migrations" / "002_outbox_hardening.sql",
    ROOT_DIR / "migrations" / "003_event_hash_chain.sql",
    ROOT_DIR / "migrations" / "004_read_models_and_outbox_consistency.sql",
    ROOT_DIR / "migrations" / "005_event_actor_claims.sql",
]


@pytest.fixture(scope="session")
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
=======
=======
>>>>>>> theirs
@pytest.fixture
async def db_pool():
    """Provide an asyncpg pool for worker integration tests."""
    dsn = os.getenv("TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres")
    pool = await asyncpg.create_pool(dsn=dsn, min_size=1, max_size=4)

    async with pool.acquire() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS outbox (
                event_id UUID PRIMARY KEY,
                tenant_id UUID NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                attempts INTEGER NOT NULL DEFAULT 0,
                available_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                payload JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )
        await conn.execute("TRUNCATE TABLE outbox")
<<<<<<< ours
>>>>>>> theirs
=======
>>>>>>> theirs

    try:
        yield pool
    finally:
<<<<<<< ours
<<<<<<< ours
        await pool.close()


@pytest.fixture
async def reset_db(db_pool: asyncpg.Pool):
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            TRUNCATE TABLE
                outbox,
                events,
                read_model_nodes,
                read_model_service_graph_edges,
                read_model_guardrail_alerts
            RESTART IDENTITY
            CASCADE
            """
        )
    yield
=======
        async with pool.acquire() as conn:
            await conn.execute("TRUNCATE TABLE outbox")
        await pool.close()
>>>>>>> theirs
=======
        async with pool.acquire() as conn:
            await conn.execute("TRUNCATE TABLE outbox")
        await pool.close()
>>>>>>> theirs
