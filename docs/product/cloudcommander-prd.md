# CloudCommander Product Requirements Document (PRD)

## 1. Product Overview

### Core Value
Manage cloud reliability and cost like a Real-Time Strategy (RTS) game, with safe-by-default architectural controls.

### Target ICP
B2B SaaS companies (50-1000 employees) operating multi-service cloud environments.

### Primary Users
- VP Engineering
- CTO
- Platform Lead
- SRE Manager

## 2. MVP Feature Scope (8-10 Weeks)

### Service Map (The Viewport)
- Directed Acyclic Graph (DAG) visualization of cloud services and dependencies.
- Nodes model explicit lifecycle states:
  - `active`
  - `orphaned`
  - `tombstoned`

### Resource Control Panel (The Command Center)
- Interface for dispatching mutation commands (scale CPU, memory, replicas).
- All mutating actions require idempotency keys.
- Conflicting mutations are resolved via optimistic concurrency (`X-Expected-Version`).

### Immutable Change Journal (The Audit Log)
- Filterable append-only log of state transitions.
- Includes actor, UTC timestamp metadata, and monotonic sequence ID.
- Supports query by aggregate ID and time windows.

### Guardrails Engine
- Evaluates pure-function policies against proposed commands.
- Example default control: block commands that exceed 20% cumulative compute reduction in a rolling 7-day window.
- Emits deterministic policy outcomes (`allowed`, `blocked`, `requires_approval`).

### Snapshot & Rollback
- Automated snapshot capture and deterministic replay support.
- One-click targeted rollback via rollback command flow.
- Supports compensating saga patterns for partial external apply failures.

### Notice-Period Flagging
- Optional HR integration to flag specific actors.
- High-risk mutations by flagged actors require two-person approval workflow.
- Full auditability of approver identity and rationale.

## 3. Success Metrics

- Time-to-resolution for infrastructure rollback under 5 minutes.
- Zero direct external API mutations that bypass canonical event store pathways.
- 100% of high-risk mutation commands evaluated by guardrail policies.
- 100% of external adapter outcomes reflected as canonical result events.

## 4. Non-Goals (MVP)

- Cross-tenant benchmarking analytics.
- Automated rightsizing recommendations driven by opaque ML scoring.
- Provider-specific advanced features beyond core allocation and dependency management.

## 5. MVP Acceptance Criteria

- All write actions flow through command endpoints and append events before projection change.
- Dependency edge insertion rejects cycle creation.
- Replay from event log reproduces projection state consistently.
- Reconciler does not directly mutate projection tables.
- Rollback flow can restore known-good allocation state in staged failure simulations.
