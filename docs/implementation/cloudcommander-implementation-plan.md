# CloudCommander Implementation Plan (Trimmed + Staged)

This document converts the current CloudCommander MVP markdown set into one staged implementation plan mapped directly to the existing repository layout.

## 0) Current repository map (implementation surface)

- **API surface**: `app/main.py`, `app/api/routers/*.py`, `app/api/middleware.py`, `app/api/dependencies.py`
- **Domain model + reducers**: `app/domain/schemas.py`, `app/domain/reducers.py`
- **Security/policy**: `app/security/rbac_policy.py`, `app/security/hash_chain.py`
- **Infrastructure + storage**: `app/infrastructure/repository.py`, `migrations/*.sql`
- **Adapters**: `app/infrastructure/adapters/base.py`, `app/infrastructure/adapters/mock_aws.py`
- **Control loop**: `app/control/backpressure_manager.py`, `app/control/pid_guardrail.py`, `app/control/maut_rollback.py`
- **Workers**: `app/worker/projection_worker.py`, `app/worker/reconciler.py`
- **Contracts/ops**: `openapi/cloudcommander-v1.yaml`, `.github/workflows/ci.yml`, `scripts/ci.sh`, `k8s/staging/*.yaml`
- **Tests**: `tests/test_domain`, `tests/test_api`, `tests/test_worker`

---

## Stage 1 — Stabilize the deterministic event core

**Goal:** make command -> event append -> reducer replay deterministic and auditable.

### Scope
1. Lock schema invariants in `app/domain/schemas.py` (resource identity, timestamps, versioning, event envelope constraints).
2. Keep reducers pure and total in `app/domain/reducers.py`:
   - explicit invalid transition errors
   - no side-effects
   - deterministic ordering assumptions
3. Enforce hash chain correctness:
   - generation in `app/security/hash_chain.py`
   - persistence/verification hooks in `app/infrastructure/repository.py`
4. Ensure migrations are aligned with code assumptions in:
   - `migrations/001_initial_schema.sql`
   - `migrations/002_outbox_hardening.sql`
   - `migrations/003_event_hash_chain.sql`

### Exit criteria
- Reducer and schema tests pass (`tests/test_domain/test_reducers.py`).
- Event append paths enforce optimistic concurrency and idempotency rules.
- Hash chain values are always written for appended events.

---

## Stage 2 — Harden command API contracts

**Goal:** guarantee safe write semantics and predictable failure modes at ingress.

### Scope
1. Keep command routes focused and explicit in `app/api/routers/commands.py`:
   - resource allocation
   - dependency edge
   - rollback
2. Validate required write headers (`X-Idempotency-Key`, `X-Expected-Version`) consistently.
3. Centralize dependency wiring in `app/api/dependencies.py`.
4. Apply protection-mode controls in `app/api/middleware.py` (backpressure behavior).
5. Keep read-only routes separated:
   - projections: `app/api/routers/projections.py`
   - telemetry: `app/api/routers/telemetry.py`

### Exit criteria
- API tests pass (`tests/test_api/test_commands.py`).
- Invalid/missing headers fail with consistent status and payload shape.
- OpenAPI contract remains synchronized (`openapi/cloudcommander-v1.yaml`).

---

## Stage 3 — Make outbox and workers production-safe

**Goal:** reliable asynchronous processing with clear ownership and retry semantics.

### Scope
1. Strengthen repository outbox operations in `app/infrastructure/repository.py`:
   - claim/ack/fail transitions
   - bounded batch claiming
   - lease/timeout assumptions documented in code comments
2. Keep projection worker deterministic in `app/worker/projection_worker.py`.
3. Keep reconciler idempotent in `app/worker/reconciler.py`.
4. Maintain adapter boundary at `app/infrastructure/adapters/base.py`; keep `mock_aws.py` deterministic for testability.

### Exit criteria
- Worker tests pass:
  - `tests/test_worker/test_outbox_claiming.py`
  - `tests/test_worker/test_reconciler.py`
- Replaying same event batch does not produce divergent projection state.

---

## Stage 4 — Operational guardrails + rollback decisions

**Goal:** enforce safety under stress and automate conservative rollback guidance.

### Scope
1. Backpressure state machine behavior in `app/control/backpressure_manager.py`.
2. Guardrail signal evaluation in `app/control/pid_guardrail.py`.
3. Rollback decision policy in `app/control/maut_rollback.py`.
4. Telemetry exposure and operator visibility in `app/api/routers/telemetry.py`.

### Exit criteria
- Protection mode can be toggled/observed via telemetry endpoints.
- Command routes respect backpressure state.
- Rollback recommendation path is deterministic for equivalent inputs.

---

## Stage 5 — Deployment and CI reliability

**Goal:** make local + CI + staging workflows consistent and repeatable.

### Scope
1. Keep runtime entrypoint minimal and explicit in `app/main.py`.
2. Keep dependency/test config aligned:
   - `requirements.txt`
   - `pytest.ini`
3. CI and bootstrap:
   - `.github/workflows/ci.yml`
   - `scripts/ci.sh`
4. Staging deployment assets:
   - `k8s/staging/api-deployment.yaml`
   - `k8s/staging/worker-deployment.yaml`
   - `k8s/staging/migration-job.yaml`
   - ingress/cert/secrets templates under `k8s/staging/`

### Exit criteria
- CI executes targeted tests successfully.
- Migrations are applied before API/worker startup in staging process.
- API and worker manifests reference compatible image/config assumptions.

---

## Stage 6 — Documentation consolidation policy (going forward)

**Goal:** keep this file as the single implementation-plan source of truth.

### Rules
1. New implementation tasks must be added here first (by stage).
2. Deep design rationale can remain in architecture docs, but every actionable change maps back to this file.
3. PRs should reference stage + exit criteria touched.

### Existing docs this plan supersedes for execution tracking
- `docs/architecture/*.md`
- `docs/product/cloudcommander-prd.md`
- `docs/threat-model/abuse-cases.md`
- `BUILD_FROM_DARK_PERSONA_THREAT_MODEL.md`
- `CHANGE_REVIEW_COMPREHENSIVE.md`

(Those files remain useful context, but implementation sequencing should now be driven from this one plan.)
