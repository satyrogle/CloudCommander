# CloudCommander Control-Plane Playbook

This document defines the operational behavior, telemetry interpretation, and recovery protocols for the CloudCommander control plane.

## 1. Overload Response & Ingress Controls

The API enforces a two-stage admission control process. When a request is rejected, the system returns an HTTP `429 Too Many Requests`. Operators must distinguish between the two rejection triggers to apply the correct mitigation.

### Trigger A: Token Bucket Exhaustion (Per-Tenant)

Condition: A specific tenant exceeds `60` mutating requests per minute or a sudden burst of `20` requests.

Scope: Affects only the offending tenant. Read-only telemetry endpoints remain unaffected.

Mitigation: Client-side rate limiting. No backend intervention required.

### Trigger B: M/M/1 Saturation (Global)

Condition: Global system utilization (`rho = lambda / mu`) meets or exceeds `0.95`. The outbox worker pipeline is failing to clear events fast enough to match API ingress.

Scope: Affects all tenants for mutating routes.

Mitigation: Wait for the asynchronous outbox worker to drain the backlog. If saturation persists, investigate database locks or cloud adapter latency.

## 2. Telemetry Troubleshooting Map

Operators should monitor the following endpoints to determine system health.

### `GET /api/v1/telemetry/system/backpressure`

`raw_utilization_rho`: The instantaneous system load used for admission control. High volatility is normal.

`ema_utilization_rho`: Exponential moving average. If this sustained value crosses `0.90`, the worker pool is under-provisioned relative to sustained traffic.

### `GET /api/v1/telemetry/system/reconciler`

Exposes the CloudAdapter circuit breaker state.

`closed`: Healthy.

`open`: Tripped after `5` adapter failures. All cloud mutations are temporarily suspended locally for `120` seconds.

`half_open`: Probing the cloud provider for recovery.

### `GET /api/v1/telemetry/graph/centrality`

Exposes Eigenvector Centrality scores for active and edge-referenced nodes.

Use this to assess the blast radius of a node before executing manual state overrides.

## 3. Rollback & Compensation Interpretation

The reconciler handles cloud provider discrepancies automatically using a deterministic Saga pattern and Bayesian MAUT evaluation.

### Transient Failures (`timeout`, `throttled`)

The circuit breaker registers the failure. The event remains in the outbox.

The outbox worker applies an exponential backoff sequence with a base of `15` seconds, stretching the survival window to approximately `8` minutes before dead-lettering the event.

### Partial Failures (`partial_failure`)

The adapter registers a fractured cloud state.

The Bayesian engine evaluates the evidence. If `posterior_infra_risk` is low, it selects the cost-optimized `forward_fix_retry`.

If repeated timeouts have inflated `posterior_infra_risk`, it deterministically shifts to the risk-averse `full_revert` strategy.

Saga execution: the worker immediately appends `CompensationStrategySelected` and `RollbackInitiated` to the canonical event stream, completing the loop.

## 4. PID Guardrail Alerts

The control plane runs an observe-only PID controller per aggregate to track resource allocation trajectories.

`stable`: Resource changes match expected allocation bounds.

`drifting`: Mild trajectory deviation. An alert is written to `read_model_guardrail_alerts` with a `warning` severity.

`volatile`: Severe resource spike, such as maxing out CPU cores instantly. Emits an `approval_required` severity alert. Currently does not block commands.

Bucket 4 is closed.
