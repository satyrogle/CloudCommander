# CloudCommander Implementation Plan (Trimmed + Staged)

This document is the strict single source of truth for CloudCommander engineering progress. The current implementation pass is fully executed and reconciled here for PR traceability.

## 0) Current Repository Map (Implementation Surface)

- **API surface:** `app/main.py`, `app/api/routers/*.py`, `app/api/middleware.py`, `app/api/dependencies.py`
- **Domain model + reducers:** `app/domain/schemas.py`, `app/domain/reducers.py`
- **Security/policy:** `app/security/rbac_policy.py`, `app/security/hash_chain.py`
- **Infrastructure + storage:** `app/infrastructure/repository.py`, `migrations/*.sql`
- **Adapters:** `app/infrastructure/adapters/base.py`, `app/infrastructure/adapters/mock_aws.py`
- **Control loop:** `app/control/backpressure_manager.py`, `app/control/pid_guardrail.py`, `app/control/maut_rollback.py`, `app/control/token_bucket.py`, `app/control/circuit_breaker.py`, `app/control/graph_centrality.py`
- **Workers:** `app/worker/projection_worker.py`, `app/worker/reconciler.py`
- **Contracts/ops:** `openapi/cloudcommander-v1.yaml`, `.github/workflows/ci.yml`, `.github/PULL_REQUEST_TEMPLATE.md`, `scripts/ci.sh`, `k8s/staging/*.yaml`
- **Tests:** `tests/test_domain`, `tests/test_api`, `tests/test_worker`, `tests/test_control`

---

## Stage 1 - Stabilize the Deterministic Event Core

**Goal:** make command -> event append -> reducer replay deterministic and auditable.

### Scope

1. Lock schema invariants in `app/domain/schemas.py`.
2. Keep reducers pure and total in `app/domain/reducers.py`.
3. Enforce hash chain correctness in `app/security/hash_chain.py` and `app/infrastructure/repository.py`.
4. Align migrations with runtime assumptions.

### Exit Criteria

- [x] Complete - Reducer and schema tests pass.
- [x] Complete - Event append paths enforce optimistic concurrency and idempotency rules.
- [x] Complete - Hash chain values are written and verified for appended events.

---

## Stage 2 - Harden Command API Contracts

**Goal:** guarantee safe write semantics and predictable failure modes at ingress.

### Scope

1. Keep command routes focused and explicit.
2. Validate required write headers consistently.
3. Centralize dependency wiring.
4. Apply protection-mode controls through middleware.
5. Keep read-only projections and telemetry separated.

### Scope Additions Logged

- Added per-tenant token bucket admission control for mutating routes.
- Added EMA-smoothed backpressure telemetry without changing raw admission decisions.
- Added graph blast-radius centrality as read-only telemetry.

### Exit Criteria

- [x] Complete - API tests pass.
- [x] Complete - Invalid/missing headers fail with consistent status and payload shape.
- [x] Complete - OpenAPI contract remains synchronized.
- [x] Complete - Synthetic load validation proves token bucket, M/M/1 overload, recovery, and EMA behavior.

---

## Stage 3 - Make Outbox and Workers Production-Safe

**Goal:** reliable asynchronous processing with clear ownership and retry semantics.

### Scope

1. Strengthen repository outbox operations.
2. Keep projection worker deterministic.
3. Keep reconciler idempotent.
4. Maintain deterministic adapter boundary for testability.

### Scope Additions Logged

- Added reconciler circuit breaker around cloud adapter calls.
- Formalized compensation as a Saga-style flow.
- Added idempotency guard for compensation followup replay.

### Exit Criteria

- [x] Complete - Worker tests pass.
- [x] Complete - Replaying same event batch does not produce divergent projection state.
- [x] Complete - Projection update and outbox status mutation remain transactionally coupled.
- [x] Complete - Circuit breaker behavior is tested for open, half-open, and closed transitions.
- [x] Complete - Compensation followups are deterministic and replay-safe.

---

## Stage 4 - Operational Guardrails + Rollback Decisions

**Goal:** enforce safety under stress and automate conservative rollback guidance.

### Scope

1. Backpressure state machine behavior.
2. Guardrail signal evaluation.
3. Rollback decision policy.
4. Telemetry exposure and operator visibility.

### Scope Additions Logged

- Added control-plane playbook for overload response, telemetry interpretation, rollback behavior, and PID guardrails.

### Exit Criteria

- [x] Complete - Protection mode can be observed via telemetry endpoints.
- [x] Complete - Command routes respect token bucket and backpressure state.
- [x] Complete - PID state is isolated per aggregate and fuzzy thresholds are validated.
- [x] Complete - Rollback recommendation path is deterministic for equivalent inputs.
- [x] Complete - Bayesian MAUT reset returns the engine to exact initial conditions.

---

## Stage 5 - Deployment and CI Reliability

**Goal:** make local + CI + staging workflows consistent and repeatable.

### Scope

1. Keep runtime entrypoints minimal and explicit.
2. Keep dependency/test config aligned.
3. Maintain CI and bootstrap scripts.
4. Preserve staging deployment ordering, including migrations before API/worker rollout.

### Exit Criteria

- [x] Complete - Local full regression suite passes: `80 passed, 7 skipped`.
- [x] Complete - Migration ordering is documented in staging process.
- [x] Complete - API and worker lifecycle/resource cleanup behavior is implemented and tested.

---

## Stage 6 - Governance Lock-In

**Goal:** keep this file as the single implementation-plan source of truth.

### Scope Additions Logged

- Added `.github/PULL_REQUEST_TEMPLATE.md` requiring stage/bucket mapping and exit criteria.
- Added `docs/governance/weekly-burndown.md` defining the weekly reconciliation process.

### Rules

1. New implementation tasks must be added here first by stage.
2. Deep design rationale can remain in architecture docs, but every actionable change maps back to this file.
3. PRs must reference stage and exit criteria touched.
4. Weekly burndown updates must reconcile merged PRs back into this file.

### Exit Criteria

- [x] Complete - PR template enforces stage mapping, exit criteria, testing evidence, impact, and rollback notes.
- [x] Complete - Weekly burndown process is documented.
- [x] Complete - This implementation plan is reconciled as the authoritative engineering record.

---

## Validation Record

- Focused Bucket 4 validation: `12 passed in 2.20s`.
- Full regression: `80 passed, 7 skipped in 7.48s`.

## Existing Docs This Plan Supersedes for Execution Tracking

- `docs/architecture/*.md`
- `docs/product/cloudcommander-prd.md`
- `docs/threat-model/abuse-cases.md`
- `BUILD_FROM_DARK_PERSONA_THREAT_MODEL.md`
- `CHANGE_REVIEW_COMPREHENSIVE.md`

Those files remain useful context, but implementation sequencing is driven from this plan.
