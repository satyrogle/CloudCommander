from __future__ import annotations

import asyncio
import logging
from typing import Optional
from uuid import UUID

import asyncpg

from app.api.middleware import backpressure_manager
from app.control.pid_guardrail import PIDGuardrailController
from app.domain.schemas import ResourceAllocationRequested

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 5
POLL_INTERVAL_SEC = 1.0

pid_controller = PIDGuardrailController(kp=0.5, ki=0.1, kd=0.2, setpoint=0.8)


class OutboxWorker:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def run(self) -> None:
        logger.info("Starting outbox worker loop")
        while True:
            try:
                processed_any = await self.process_next_batch()
                if not processed_any:
                    await asyncio.sleep(POLL_INTERVAL_SEC)
            except Exception as exc:  # safeguard loop
                logger.exception("Worker loop error: %s", exc)
                await asyncio.sleep(POLL_INTERVAL_SEC)

    async def process_next_batch(self, batch_size: int = 10) -> bool:
        claim_query = """
            WITH claimed AS (
                SELECT event_id, tenant_id
                FROM outbox
                WHERE status IN ('pending', 'failed')
                  AND (
                    last_attempt_at IS NULL
                    OR last_attempt_at < NOW() - (POWER(2, attempts) * INTERVAL '1 second')
                  )
                ORDER BY created_at ASC
                LIMIT $1
                FOR UPDATE SKIP LOCKED
            )
            UPDATE outbox
            SET status = 'processing',
                attempts = attempts + 1,
                last_attempt_at = NOW()
            FROM claimed
            WHERE outbox.event_id = claimed.event_id
            RETURNING outbox.event_id, outbox.tenant_id, outbox.attempts;
        """

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                rows = await conn.fetch(claim_query, batch_size)

            if not rows:
                return False

            for row in rows:
                await self._process_record(conn, row)

        return True

    async def _process_record(self, conn: asyncpg.Connection, row: asyncpg.Record) -> None:
        event_id: UUID = row["event_id"]
        attempts: int = row["attempts"]

        try:
            # TODO: fetch event, project idempotently, dispatch reconciler as needed
            # Observe-only PID hook: only runs when payload is ResourceAllocationRequested
            event = None
            if event is not None and isinstance(event.payload, ResourceAllocationRequested):
                max_limit_cores = 16.0
                current_utilization = event.payload.target_cpu_cores / max_limit_cores
                pid_controller.observe_resource_change(
                    current_utilization=current_utilization,
                    aggregate_id=str(event.aggregate_id),
                )
            await self._mark_processed(conn, event_id)
            await backpressure_manager.record_completion()
        except Exception as exc:
            logger.error("Failed processing event %s: %s", event_id, exc)
            await self._handle_failure(conn, event_id, attempts, str(exc))

    async def _mark_processed(self, conn: asyncpg.Connection, event_id: UUID) -> None:
        await conn.execute(
            "UPDATE outbox SET status = 'processed', processed_at = NOW() WHERE event_id = $1",
            event_id,
        )

    async def _handle_failure(
        self, conn: asyncpg.Connection, event_id: UUID, attempts: int, error_msg: str
    ) -> None:
        status = "dead_letter" if attempts >= MAX_ATTEMPTS else "failed"
        if status == "dead_letter":
            logger.critical("Event %s moved to dead_letter", event_id)

        await conn.execute(
            """
            UPDATE outbox
            SET status = $1,
                error_payload = jsonb_build_object('error', $2)
            WHERE event_id = $3
            """,
            status,
            error_msg,
            event_id,
        )
