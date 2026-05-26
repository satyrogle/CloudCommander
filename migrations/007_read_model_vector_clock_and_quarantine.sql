ALTER TABLE read_model_nodes
ADD COLUMN IF NOT EXISTS vclock JSONB NOT NULL DEFAULT '{}'::jsonb;

CREATE TABLE IF NOT EXISTS read_model_causality_quarantine (
    quarantine_id BIGSERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL,
    aggregate_id UUID NOT NULL,
    event_id UUID NOT NULL,
    sender_id TEXT NOT NULL,
    relation TEXT NOT NULL,
    incoming_vclock JSONB NOT NULL,
    current_vclock JSONB NOT NULL,
    reason TEXT NOT NULL,
    quarantined_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_causality_quarantine_latest
ON read_model_causality_quarantine(tenant_id, aggregate_id, quarantined_at DESC);
