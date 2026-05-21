# CloudCommander Integration Contract

## Purpose
Define how the frontend and external cloud adapters communicate with the deterministic event store while preserving pure reducer semantics.

## 1. High-level Interaction Model

### Write Path (Commands -> Events -> Projection)
1. Frontend submits a **command** to API (`POST /commands/...`) with:
   - `tenant_id`
   - `idempotency_key`
   - `expected_version`
   - command payload
2. API validates schema, authorization, bounds, and deterministic preconditions.
3. API appends a canonical event to the event store if concurrency checks pass.
4. Projection workers consume the event stream and update read models.
5. Frontend observes updated projection via polling or subscriptions.

### Side-Effect Path (Event Intents -> Adapter Execution -> Result Events)
1. Reducer emits side-effect intents as data.
2. Reconciler dispatches intent to adapter (AWS/EKS).
3. Adapter executes external API calls asynchronously.
4. Adapter reports result as follow-up events (`...Succeeded` / `...Failed`).
5. Projection converges via new events; no direct state mutation by adapters.

## 2. Frontend Contract

### Command API principles
- Mutations are command-based, not direct model writes.
- All mutating endpoints require `idempotency_key`.
- All mutating endpoints require `expected_version` for optimistic concurrency.
- Conflict returns HTTP `409` with latest aggregate version.

### Read API principles
- Read models are eventually consistent projections.
- All reads are tenant-scoped.
- UI must tolerate projection lag and display command status (`pending`, `applied`, `failed`).

### Recommended endpoint families
- `POST /commands/resource-allocation`
- `POST /commands/dependency-edge`
- `POST /commands/rollback`
- `GET /projections/service-graph`
- `GET /projections/resource-nodes`
- `GET /events/{aggregate_id}`

## 3. Adapter Contract (AWS/EKS and future providers)

### Adapter input
- Immutable intent object:
  - `intent_id`
  - `tenant_id`
  - `aggregate_id`
  - `provider`
  - `operation`
  - `parameters`
  - `correlation_id`

### Adapter output
- Never mutates projections directly.
- Emits only domain result events:
  - `ResourceAllocationApplied`
  - `ResourceAllocationRejected`
  - `RollbackApplied`
  - `RollbackRejected`
- Includes deterministic metadata (`intent_id`, `correlation_id`, `provider_request_id`).

### Adapter reliability rules
- Retries must preserve idempotency across provider APIs.
- Timeouts are mapped to explicit pending/failed domain events.
- Partial external success must produce compensating intents/events.

## 4. Concurrency and Ordering Guarantees

- Event store ordering authority is `sequence_id`.
- `timestamp_utc_ms` is informational metadata, not ordering source.
- Per-aggregate optimistic locking via `expected_version`.
- Cross-aggregate workflows use saga orchestration with compensating events.

## 5. Security and Isolation

- Tenant isolation enforced at command ingest and read projection layers.
- RBAC defaults to deny-all; explicit grants required per command family.
- High-risk operations (large downsizing, rollback) support two-person approval workflow.
- Full audit trail from command receipt to adapter completion event.

## 6. Failure Semantics

- Commands targeting `AggregateFrozen` resources must return HTTP `423 Locked` with resolution guidance.


- Duplicate command submission returns prior outcome via idempotency key.
- Projection worker crash recovery via replay from last committed offset.
- Adapter crash recovery via intent rehydration and retry policies.
- No operation is considered complete until terminal result event is appended.

## 7. Suggested Next Deliverables

- `openapi/cloudcommander-v1.yaml` with concrete command/read schemas.
- `docs/architecture/reconciler-state-machine.md` for intent lifecycle.
- `docs/architecture/projection-lag-slo.md` defining UX consistency targets.
- `docs/architecture/drift-detection-failure-rules.md` for freeze/remediation lifecycle.


## 8. Projection Lag UX Contract (Decision)

Decision: **Lock-first with scoped optimistic feedback**.

- After `202 Accepted`, UI marks only the targeted node as `Syncing` and disables duplicate mutation actions for that node.
- UI renders a lightweight optimistic preview (pending badge + intended target values), but does not mark mutation as applied until projection/result events confirm.
- If projection update has not arrived within SLO window, UI prompts retry/rebase flow with latest aggregate version.
- This prevents double-submit churn while preserving user clarity under CQRS lag.

## 9. Event Granularity Rules (UI to Command Boundary)

- UI interactions (slider drag/typing) are local state only.
- Command emission occurs only on explicit commit action (e.g., `Submit Intent`).
- Clients should debounce rapid edits and send one command envelope per committed intent.
