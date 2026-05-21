# Adaptive Control and Security Hardening

## Purpose
Define quantitative control loops and fail-closed security behavior for the deterministic CloudCommander core.

---

## 1) Backpressure Control (M/M/1-Inspired)

### Model
- Arrival rate: `λ` = accepted mutation commands per second.
- Service rate: `μ` = successfully processed outbox events per second.
- Utilization: `ρ = λ / μ`.

### Thresholds
- `ρ < 0.80` → **Normal**.
- `0.80 <= ρ < 0.90` → **Warning** (emit telemetry + operator warning).
- `0.90 <= ρ < 0.95` → **Degraded** (tighten command rate limits).
- `ρ >= 0.95` → **Protection Mode** (return HTTP `429` for non-essential mutation commands).

### Fail-Closed Behavior
- If control metrics are unavailable or stale, default to **Degraded** policy.
- If queue depth exceeds hard cap, reject new mutation commands with `429` and retry hints.
- Read-only endpoints remain available.

### Rolling Window Guidance
- Compute λ/μ over 60s short window and 5m long window.
- Enter protection mode if either window breaches threshold persistently (e.g., 3 consecutive samples).

---

## 2) PID Guardrail Controller (Dynamic Risk Throttling)

### Control Variable
Let `x(t)` be normalized risk from cumulative downsizing and stability signals.
Target risk setpoint: `r`.
Error: `e(t) = r - x(t)`.

### PID Equation
`u(t) = Kp*e(t) + Ki*∫e(τ)dτ + Kd*(de/dt)`

Where:
- `Kp`: immediate response to abrupt drops.
- `Ki`: accumulation of repeated small reductions.
- `Kd`: anticipates fast downward trends.

### Suggested Initial Gains
- `Kp = 0.8`
- `Ki = 0.2`
- `Kd = 0.1`

(Initial values must be tuned in staging with replayed workloads.)

### Policy Mapping
- `u(t) <= T1` → allow.
- `T1 < u(t) <= T2` → allow with warning + additional audit annotation.
- `T2 < u(t) <= T3` → require approval.
- `u(t) > T3` → freeze aggregate (`AggregateFrozen`) and block mutations (`423`).

### Fail-Closed Behavior
- If controller state cannot be computed (missing input stream), route to `requires_approval`.
- If sustained calculation failure > configured SLA, freeze targeted aggregate.

---

## 3) MAUT Rollback Decision Engine

### Utility Function
For rollback option `x`:

`U(x) = Σ (wi * ui(xi))`, with `Σ wi = 1`.

Example attributes:
- `x1`: time-to-restore (minimize)
- `x2`: infrastructure cost impact (minimize)
- `x3`: operational risk (minimize)

Example weights:
- `w1 = 0.50`
- `w2 = 0.15`
- `w3 = 0.35`

Decision: choose action `argmax_x U(x)` among viable options (rollback path, forward-fix, partial compensation).

### Safety Constraints
- Options violating hard guardrails (security/SLO limits) are excluded regardless of utility.
- If no option satisfies hard constraints, enter `ManualInterventionRequired` terminal state.

### Fail-Closed Behavior
- If MAUT inputs are incomplete/untrusted, default to safest low-risk compensation path.
- If no low-risk path exists, freeze and require manual intervention.

---

## 4) Tamper-Evident Event Hash Chaining

### Event Hash Definition
For stream event `n`:

`Hash_n = SHA256(Hash_{n-1} || CanonicalPayload_n || Timestamp_n || SequenceID_n)`

Genesis event (`sequence_id = 1`) uses a fixed stream seed for `Hash_0`.

### Verification Rules
- Projection/replay worker verifies hash linkage before applying event.
- Any mismatch emits integrity alert and halts stream application for affected aggregate.

### Fail-Closed Behavior
- On hash mismatch, mark stream as compromised and block downstream projection mutation.
- Require security review + explicit recovery workflow before unfreezing stream.

---

## 5) Reducer-Level RBAC Enforcement

### Deterministic Authorization Contract
Reducer receives deterministic context:
- `actor_id`
- permission claims snapshot
- target aggregate/node scope

Transition is rejected in-domain if claims do not authorize requested transition.

### Fail-Closed Behavior
- Missing/invalid claims snapshot => reject transition.
- Unknown permission scope => reject transition.
- API-layer authorization success does not bypass reducer authorization checks.

---

## 6) mTLS for Adapter Boundary

### Boundary Definition
- Reconciler-to-adapter traffic is mTLS-only.
- Certificates are workload identity bound and rotated automatically.

### Fail-Closed Behavior
- Certificate validation failure => deny connection, no adapter action.
- Expired certs => deny and alert; no downgrade to plaintext/TLS-without-client-auth.
- Adapter endpoints inaccessible => keep event in retry/failure lifecycle; never perform insecure fallback.

---

## 7) Operational Threshold Defaults (Initial)

- Backpressure protection: `ρ >= 0.95`
- Outbox dead-letter threshold: `MAX_ATTEMPTS = 5`
- Stale-processing sweeper: 2 minutes
- PID freeze threshold: `u(t) > T3` (tune in staging)
- Hash mismatch tolerance: zero (single mismatch halts affected stream)

These defaults are intentionally conservative and should be tuned only with replay-based validation.
