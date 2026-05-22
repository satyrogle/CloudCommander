from __future__ import annotations

import asyncio
import os

import asyncpg

from app.worker.projection_worker import OutboxWorker


async def _run() -> None:
    dsn = os.getenv("DATABASE_URL") or os.getenv("TEST_DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL or TEST_DATABASE_URL must be set")

    pool = await asyncpg.create_pool(dsn=dsn, min_size=1, max_size=8)
    try:
        worker = OutboxWorker(pool)
        await worker.run()
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(_run())
