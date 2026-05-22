# CloudCommander Threat Model Abuse Cases

## 1) Insider Sabotage Cascade

### Attacker
Disgruntled platform engineer with elevated access (including notice-period employees).

### Attack Vector
The actor gradually reduces resource allocations across several non-critical services over multiple days, avoiding single-change thresholds to cause delayed degradation.

### Mitigations
- **Guardrails Engine:** Tracks cumulative downsizing; alerts and blocks when reductions exceed policy threshold in rolling windows.
- **Notice-Period Controls:** Applies two-person approval requirements to high-risk resource reduction commands by flagged users.
- **Snapshot Rollback:** Restores infrastructure state to a pre-incident sequence/snapshot with auditable rollback intent.

## 2) State Desync Exploit

### Attacker
Rogue internal user or compromised token attempting race-condition exploitation.

### Attack Vector
Sends conflicting scale commands directly to command APIs in rapid succession, attempting to exploit provider latency and create divergence between intended and observed state.

### Mitigations
- **Optimistic Concurrency:** `X-Expected-Version` is required and conflicts return `409`, forcing explicit client rebase.
- **Canonical Ordering:** Event store sequence IDs provide deterministic mutation order.
- **Reconciler Isolation:** Adapter latency is isolated from pure domain reducers; external results are fed back only as result events.

## 3) Shadow Infrastructure Deployment

### Attacker
User with enough permissions to attempt unauthorized compute expansion for non-business workloads.

### Attack Vector
Attempts to create compute resources or dependency entries outside approved service graph controls to hide unauthorized workloads.

### Mitigations
- **RBAC Default Deny-All:** Explicit command permissions required per tenant and role.
- **Graph Validation:** Dependency and lifecycle constraints reject invalid or unmapped graph manipulations.
- **Audit Trail:** All attempted writes (including rejects) are logged with actor and reason for forensic review.
