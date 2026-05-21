CREATE TABLE IF NOT EXISTS events (
    event_id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    aggregate_id UUID NOT NULL,
    sequence_id INTEGER NOT NULL,
    timestamp_utc_ms BIGINT NOT NULL,
    idempotency_key VARCHAR(100) NOT NULL,
    actor_id VARCHAR(255) NOT NULL,
    expected_version INTEGER NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE events
ADD CONSTRAINT uq_aggregate_sequence
UNIQUE (tenant_id, aggregate_id, sequence_id);

ALTER TABLE events
ADD CONSTRAINT uq_tenant_idempotency
UNIQUE (tenant_id, idempotency_key);

CREATE INDEX idx_events_aggregate ON events(tenant_id, aggregate_id, sequence_id);

CREATE TABLE IF NOT EXISTS outbox (
    outbox_id BIGSERIAL PRIMARY KEY,
    event_id UUID NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    locked_at TIMESTAMPTZ,
    processed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_outbox_pending ON outbox(status, created_at);
