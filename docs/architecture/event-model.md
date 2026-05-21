# CloudCommander Event Model (Deterministic Core)

## 1. System State (The Projection)

### ServiceGraph
- `ServiceGraph` is a Directed Acyclic Graph (DAG) of service dependencies.
- Cycle detection is enforced on dependency edge insertion.
- Any write that would introduce a cycle is rejected before commit.

### ResourceNode
- `ResourceNode` lifecycle is explicit and non-destructive:
  - `active`
  - `orphaned`
  - `tombstoned`
- Hard delete is disallowed in the canonical state machine.
- Orphaning is modeled as a state transition event, not implicit data loss.

## 2. Event Schemas (Append-Only Canonical Log)

All state mutations are represented as immutable events.

Required event envelope fields:
- `event_id` (globally unique)
- `tenant_id`
- `sequence_id` (monotonic, per-tenant ordering)
- `timestamp_utc_ms` (UTC epoch milliseconds)
- `idempotency_key`
- `actor_id`
- `expected_version` (for optimistic concurrency)
- `payload`

Core event types (initial set):
- `ResourceAllocationRequested`
- `DependencyEdgeProposed`
- `RollbackInitiated`

Design constraints:
- Event log is append-only and canonical.
- Rebuild of projection state must be possible from events + snapshots.
- Event consumers must treat duplicate deliveries as safe via idempotency key semantics.

## 3. Reducers (Pure Functions)

State transitions follow:

`next_state = reducer(prev_state, command, deterministic_context)`

Deterministic requirements:
- Reducers are pure functions.
- No external I/O inside reducers.
- No wall-clock reads inside reducers.
- No randomness without deterministic seeding captured in event payload.

Numeric safety requirements:
- Clamp all boundary-sensitive values (utility scores, limits, thresholds).
- Reject non-finite values (`NaN`, `Infinity`, `-Infinity`) at command validation.
- Use saturating/checked arithmetic where overflow risk exists.

Side-effect boundary:
- Reducers emit side-effect intents (if any) as data.
- Side effects execute only after successful state commit.

## 4. Concurrency & Reconciler Boundaries

### Optimistic Concurrency
- Mutations require `expected_version` checks.
- If current version differs, command is rejected with conflict and must retry/rebase.
- Winner is defined by first successful commit at the event store boundary.

### Reconciler / External APIs
- External cloud APIs (e.g., AWS/EKS) are isolated behind adapters.
- Adapter layer is treated as eventually consistent and non-deterministic.
- Anti-corruption layer maps external state and async callbacks into deterministic domain events.
- Core projection never reads directly from external APIs during reducer execution.

### Deterministic Core Contract
- Core domain state is fully testable headlessly via event replay.
- Asynchronous completion updates are represented as follow-up events, never implicit in-memory mutation.
