# Outbox Processing Contract

## 1. Claim Semantics

Workers claim rows atomically via:
- `SELECT ... FOR UPDATE SKIP LOCKED` inside a CTE
- followed by `UPDATE ... SET status='processing' ... RETURNING ...`

`SKIP LOCKED` ensures multiple workers do not block each other and do not claim duplicate rows.

## 2. State Lifecycle

- `pending`: initial state after event append.
- `processing`: row claimed by worker.
- `processed`: terminal success state.
- `failed`: retryable failure state.
- `dead_letter`: terminal failure after max attempts; requires manual intervention.

## 3. Idempotency Guarantees

- Projection updates must be idempotent keyed by `event_id`.
- Worker crashes after claim are recovered by timeout sweeper that resets stale `processing` rows to `failed`.
- Suggested stale-processing SLA: 2 minutes.

## 4. Retry and Backoff

- Retry only rows in `failed` or `pending`.
- Backoff window: `NOW() - (2^attempts * base_interval)`.
- Suggested `MAX_ATTEMPTS`: 5.

## 5. Poison Event Handling

- Non-retryable failures (schema corruption/domain invariant violations) route directly to `dead_letter`.
- `error_payload` stores structured context for forensic triage.
