-- Formalize status constraints
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'chk_outbox_status'
          AND conrelid = 'outbox'::regclass
    ) THEN
        ALTER TABLE outbox
        ADD CONSTRAINT chk_outbox_status
        CHECK (status IN ('pending', 'processing', 'processed', 'failed', 'dead_letter'));
    END IF;
END $$;

-- Add columns for retry and error tracking (idempotent guards)
ALTER TABLE outbox ADD COLUMN IF NOT EXISTS last_attempt_at TIMESTAMPTZ;
ALTER TABLE outbox ADD COLUMN IF NOT EXISTS error_payload JSONB;

-- attempts already exists in 001; ensure non-null/default if pre-existing environments drifted
ALTER TABLE outbox ALTER COLUMN attempts SET DEFAULT 0;
UPDATE outbox SET attempts = 0 WHERE attempts IS NULL;
ALTER TABLE outbox ALTER COLUMN attempts SET NOT NULL;

-- Index to optimize polling query
CREATE INDEX IF NOT EXISTS idx_outbox_polling
ON outbox(status, last_attempt_at)
WHERE status IN ('pending', 'failed');
