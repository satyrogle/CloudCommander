from __future__ import annotations

from typing import List
from uuid import UUID

import asyncpg
from asyncpg.exceptions import UniqueViolationError
from pydantic import ValidationError

from app.domain.schemas import EventEnvelope
from app.security.hash_chain import generate_event_hash, verify_chain


class ConcurrencyConflictError(Exception):
    pass


class IdempotencyKeyInUseError(Exception):
    pass


class DataCorruptionError(Exception):
    pass


class EventRepository:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def _get_latest_hash(
        self, conn: asyncpg.Connection, tenant_id: UUID, aggregate_id: UUID
    ) -> str:
        query = """
            SELECT event_hash
            FROM events
            WHERE tenant_id = $1 AND aggregate_id = $2
            ORDER BY sequence_id DESC
            LIMIT 1
        """
        result = await conn.fetchval(query, tenant_id, aggregate_id)
        return result or "genesis_hash"

    async def append_event_and_enqueue(self, envelope: EventEnvelope) -> None:
        append_query = """
            INSERT INTO events (
                event_id, tenant_id, aggregate_id, sequence_id,
                timestamp_utc_ms, idempotency_key, actor_id,
                expected_version, event_type, payload,
                previous_hash, event_hash
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10::jsonb, $11, $12)
        """

        outbox_query = """
            INSERT INTO outbox (event_id, tenant_id, status)
            VALUES ($1, $2, 'pending')
        """

        payload_dict = envelope.payload.model_dump(mode="json")

        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    previous_hash = await self._get_latest_hash(
                        conn, envelope.tenant_id, envelope.aggregate_id
                    )
                    event_hash = generate_event_hash(
                        previous_hash=previous_hash,
                        payload=payload_dict,
                        timestamp_ms=envelope.timestamp_utc_ms,
                        sequence_id=envelope.sequence_id,
                    )

                    await conn.execute(
                        append_query,
                        envelope.event_id,
                        envelope.tenant_id,
                        envelope.aggregate_id,
                        envelope.sequence_id,
                        envelope.timestamp_utc_ms,
                        envelope.idempotency_key,
                        envelope.actor_id,
                        envelope.expected_version,
                        envelope.payload.event_type,
                        payload_dict,
                        previous_hash,
                        event_hash,
                    )

                    await conn.execute(outbox_query, envelope.event_id, envelope.tenant_id)

        except UniqueViolationError as e:
            constraint_name = e.constraint_name
            if constraint_name == "uq_aggregate_sequence":
                raise ConcurrencyConflictError(
                    f"Sequence {envelope.sequence_id} already exists for aggregate {envelope.aggregate_id}."
                )
            if constraint_name == "uq_tenant_idempotency":
                raise IdempotencyKeyInUseError(
                    f"Idempotency key {envelope.idempotency_key} is already in use for this tenant."
                )
            raise

    async def get_events(
        self, tenant_id: UUID, aggregate_id: UUID, after_sequence_id: int = 0
    ) -> List[EventEnvelope]:
        query = """
            SELECT event_id, tenant_id, aggregate_id, sequence_id,
                   timestamp_utc_ms, idempotency_key, actor_id,
                   expected_version, payload, previous_hash, event_hash
            FROM events
            WHERE tenant_id = $1 AND aggregate_id = $2 AND sequence_id > $3
            ORDER BY sequence_id ASC
        """
        async with self.pool.acquire() as conn:
            records = await conn.fetch(query, tenant_id, aggregate_id, after_sequence_id)

        for record in records:
            payload_dict = record["payload"]
            verify_chain(
                previous_hash=record["previous_hash"],
                current_hash=record["event_hash"],
                payload=payload_dict,
                timestamp_ms=record["timestamp_utc_ms"],
                sequence_id=record["sequence_id"],
            )

        return [self._map_record_to_envelope(record) for record in records]

    def _map_record_to_envelope(self, record: asyncpg.Record) -> EventEnvelope:
        try:
            raw_dict = dict(record)
            raw_dict.pop("previous_hash", None)
            raw_dict.pop("event_hash", None)
            return EventEnvelope.model_validate(raw_dict)
        except ValidationError as e:
            raise DataCorruptionError(
                f"Failed to rehydrate event {record['event_id']}: {str(e)}"
            )
