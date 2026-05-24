# Weekly Burndown Process

## Objective

Maintain the implementation plan as the strict single source of truth for all engineering progress.

## Protocol (Execute Weekly)

1. **Audit Merged PRs:** Review all PRs merged during the current week. Ensure each contains a mapped stage and completed exit criteria.
2. **State Reconciliation:** Update `docs/implementation/cloudcommander-implementation-plan.md`. Move verified items to `[x] Complete`.
3. **Traceability:** Append the PR link or commit hash next to the completed exit criterion in the plan.
4. **Scope Management:** If architectural discoveries forced a deviation (e.g., adding circuit breakers to Bucket 3), explicitly log the scope addition in the plan.
5. **Commit:** Push the update with the standard commit format: `chore(governance): weekly burndown update`.

Bucket 6 is closed. The implementation plan is fully executed.
