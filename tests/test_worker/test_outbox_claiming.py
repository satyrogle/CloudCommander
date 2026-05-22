import asyncio
from uuid import uuid4

import asyncpg
import pytest


@pytest.mark.asyncio
async def test_skip_locked_prevents_duplicate_claims(db_pool: asyncpg.Pool):
    tenant_id = uuid4()
    event_ids = [uuid4() for _ in range(5)]

    async with db_pool.acquire() as conn:
        for eid in event_ids:
            await conn.execute(
                "INSERT INTO outbox (event_id, tenant_id, status) VALUES ($1, $2, 'pending')",
                eid,
                tenant_id,
            )

    async def worker_claim(batch_size: int):
        claim_query = """
            WITH claimed AS (
                SELECT event_id
                FROM outbox
                WHERE status = 'pending'
                ORDER BY created_at ASC
                LIMIT $1
                FOR UPDATE SKIP LOCKED
            )
            UPDATE outbox
            SET status = 'processing'
            FROM claimed
            WHERE outbox.event_id = claimed.event_id
            RETURNING outbox.event_id;
        """

        async with db_pool.acquire() as conn:
            async with conn.transaction():
                records = await conn.fetch(claim_query, batch_size)
                await asyncio.sleep(0.5)
                return [r["event_id"] for r in records]

    worker_1_claims, worker_2_claims = await asyncio.gather(
        worker_claim(3), worker_claim(3)
    )

    assert len(worker_1_claims) == 3
    assert len(worker_2_claims) == 2
    assert set(worker_1_claims).isdisjoint(set(worker_2_claims))
