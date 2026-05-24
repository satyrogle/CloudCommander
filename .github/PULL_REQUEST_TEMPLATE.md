## Stage / Bucket Mapping

- **Target Bucket:** [e.g., Bucket 2: API Contract]
- **Implementation Plan Link / Reference:**

## Exit Criteria

*State the specific exit criteria from the implementation plan this PR fulfills.*

- [ ] Criterion 1:
- [ ] Criterion 2:

## Testing & Evidence

*Attach logs, transcript snippets, or link to CI runs proving the criteria are met.*

- [ ] **Domain/Reducers:** Pure functions tested. No external side effects.
- [ ] **Infrastructure/Worker:** Outbox processing, transactional atomicity, and idempotency verified.
- [ ] **Control Plane:** Synthetic load, EMA, PID, or circuit breaker behavior verified (if applicable).
- [ ] **Evidence attached:** [Provide stdout / pytest summary]

## Impact Assessment

- [ ] **Database Schema:** Includes new migrations? (If yes, confirm ordered execution).
- [ ] **API Contract:** OpenAPI spec updated? (`openapi/cloudcommander-v1.yaml`)
- [ ] **CQRS Read Models:** Projection drift handled?
- [ ] **Documentation:** Playbooks or architecture docs updated?

## Operational & Rollback Notes

*Detail how this change behaves under stress and how it recovers.*

- **Saga / Compensation:** (Does this introduce new partial failure paths or MAUT evaluations?)
- **Guardrails:** (Does this alter PID setpoints, M/M/1 limits, or token bucket capacities?)
- **Rollback Plan:** (Can this be safely reverted without breaking the event chain?)
