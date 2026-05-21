# CloudCommander Drift Detection Failure Rules

## Purpose
Define strict failure rules for external drift detection so canonical event history remains authoritative **and** grounded in observed provider reality.

## 1) Drift Worker Contract

### Role
- Independent, read-only worker that polls external providers (AWS/EKS) and compares observed state to internal projection state.
- Worker is allowed to append canonical drift events only; it cannot perform direct provider mutations.

### Cadence and SLO
- Continuous background polling.
- High-severity drift detection SLO: identify and emit event within **5 minutes** of observable divergence.

### Isolation Constraints
- No write access to command endpoints.
- No write access to projection tables.
- Event append only through canonical event-log ingestion path.

## 2) Event Taxonomy

- `ExternalDriftDetected`
  - Emitted when observed provider state differs from projection.
  - Includes severity, field-level diffs, and provider evidence reference.

- `AggregateFrozen`
  - Emitted automatically for medium/high severity drift.
  - Blocks mutation commands for targeted `aggregate_id` until resolution.

- `ExternalDriftResolved`
  - Emitted when drift is remediated and freeze condition is cleared.
  - Must include resolution mode and actor/system provenance.

## 3) Severity Tiers and Remediation Policy

### Low Severity (Informational Drift)
Examples:
- Non-critical metadata changes (e.g., tags changed externally).

Policy:
- Emit `ExternalDriftDetected`.
- Set projection warning flag.
- No freeze.
- Default posture: accept external reality and record acceptance event metadata.

### Medium Severity (Config Drift)
Examples:
- External parameter adjustments outside expected bounds but not immediately destructive.

Policy:
- Emit `ExternalDriftDetected`.
- Emit `AggregateFrozen`.
- Require manual approval path:
  - `ReapplyInternalState`, or
  - `AcceptExternalReality`.
- Unfreeze only after terminal resolution event.

### High Severity (Destructive/Security Drift)
Examples:
- Service/resource deleted externally.
- IAM/security-critical policy drift.
- Major unexpected resource reduction.

Policy:
- Emit `ExternalDriftDetected` and immediate `AggregateFrozen`.
- Trigger critical alert pipeline (Pager/On-call/SOC route).
- Require explicit manual intervention and approved unfreeze command.

## 4) AggregateFrozen Enforcement

When an aggregate is frozen:
- Any command targeting that `aggregate_id` returns HTTP `423 Locked`.
- Allowed actions are limited to drift resolution workflow commands.
- Freeze state is visible in projections and command-status APIs.

## 5) Manual Intervention Pathways

### Resolution Modes
- `ReapplyInternalState`
  - System issues reconciler intents to restore internal target state.
  - If intents fail repeatedly, escalate to `ManualInterventionRequired`.

- `AcceptExternalReality`
  - Projection is advanced to externally observed state via canonical acceptance event chain.
  - Requires actor justification and audit metadata.

### Escalation Terminal State
- `ManualInterventionRequired`
  - Entered when automated remediation/rollback retries are exhausted.
  - Aggregate remains frozen until authorized operator resolves and emits unfreeze pathway completion.

## 6) Audit and Forensics Requirements

All drift lifecycle events must include:
- `aggregate_id`, `tenant_id`, `severity`, `detected_at_utc_ms`
- provider evidence handle (`provider_request_id`/resource ARN snapshot)
- `resolution_mode`, `resolved_by`, and rationale (when resolved)

## 7) Safety Invariants

- Drift worker never mutates provider state directly.
- All freeze/unfreeze transitions are event-driven and auditable.
- No aggregate unfreezes without terminal resolution evidence.
- Replay of event stream reconstructs frozen intervals and resolution history exactly.
