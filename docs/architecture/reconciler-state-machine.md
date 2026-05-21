# CloudCommander Reconciler State Machine

## Purpose
Define how reducer-emitted intents are executed against eventually consistent providers (e.g., AWS/EKS) without violating deterministic core guarantees.

## 1) Intent Lifecycle States

- `Pending`: Intent emitted by reducer and queued for execution.
- `Dispatched`: Reconciler claimed intent and initiated provider request.
- `Resolved_Success`: Provider confirmed requested change.
- `Resolved_Failure`: Provider rejected, timed out, or exceeded retry threshold.
- `Compensating`: Partial success detected; compensating actions in progress.

State transitions (simplified):
- `Pending -> Dispatched`
- `Dispatched -> Resolved_Success`
- `Dispatched -> Resolved_Failure`
- `Dispatched -> Compensating`
- `Compensating -> Resolved_Success` (compensation complete)
- `Compensating -> Resolved_Failure` (compensation failed)

## 2) Adapter Execution Rules

- Reconciler is read-only against projection tables; it consumes intent queue and emits result events only.
- `intent_id` is mapped to provider idempotency token (e.g., AWS `ClientToken`).
- Re-dispatches for the same intent must reuse the same provider idempotency token.
- Reconciler may store ephemeral transport metadata, but canonical truth remains event log.

## 3) Result Event Generation

- Provider HTTP `2xx` maps to `ResourceAllocationApplied` or `RollbackApplied`.
- Provider HTTP `4xx/5xx` maps to `ResourceAllocationRejected` or `RollbackRejected` with categorized reason.
- Every terminal attempt emits a canonical result event appended to main event log.
- Projection updates only from appended result events.

## 4) Failure and Retry Mechanics

- Network/transient failures use exponential backoff with jitter.
- Retry policy example:
  - initial delay: 250ms
  - multiplier: 2.0
  - max delay: 30s
  - max attempts: 8
- On max-attempt exhaustion, intent transitions to `Resolved_Failure` and a rejection event is emitted.
- Timeout is explicit failure reason; never silent drop.

## 5) Saga Orchestration and Compensation

For multi-target mutations:
1. Emit child intents for each target in a deterministic order.
2. Track per-target completion in saga state.
3. If any child fails after prior successes, enter `Compensating`.
4. Emit compensating intents for previously applied targets in reverse application order.
5. Finalize with terminal saga event indicating fully compensated or compensation failure.

Example (batch downsizing):
- Nodes A, B, C succeed; D fails.
- Compensate C, then B, then A to prior known-good allocations.
- Emit canonical compensation result events for each node plus saga terminal event.

## 6) Determinism Guardrails

- Reconciler never mutates core state directly.
- All externally observed outcomes are reified as domain events.
- Ordering authority is event `sequence_id`; wall-clock timestamps are metadata only.
- Replay of event log reproduces projection regardless of adapter latency or network variance.


## 7) Anti-Patterns and Required Safeguards

### Split-Brain Reconciler (Zombie Intents)
- Before re-dispatching a `Pending` intent older than the dispatch timeout, reconciler must perform provider reconciliation lookup using stable provider idempotency token (for AWS: `ClientToken`).
- If provider confirms prior success, reconciler emits canonical success event instead of re-executing mutation.
- If provider confirms failure/non-execution, reconciler may safely retry under the same idempotency token.

### Domain Leakage Prevention
- Core events and reducer state remain provider-agnostic (`compute_units`, `memory_blocks`, `replica_target`).
- Provider-specific nouns (e.g., ECS/Fargate/EC2) are confined to adapter mapping layer.
- Backward compatibility rule: event schema evolution may extend abstract fields but must not introduce provider-coupled types in core stream.

### Rate Limiting and Batch Drip Control
- Multi-target intents are converted into bounded-concurrency execution plans.
- Adapter workers enforce per-provider rate limits and token-bucket/concurrency caps.
- HTTP 429/5xx responses trigger exponential backoff with jitter and retry budgeting.

### Snapshot and Schema Evolution
- Replay pipeline includes upcaster chain to normalize historical events to current reducer contract.
- Snapshot metadata stores schema version; incompatible snapshots must be rebuilt via replay + upcasting.
