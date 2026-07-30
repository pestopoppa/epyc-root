# Shared Workflows

## New Feature

1. Add or extend a feature flag.
2. Implement guarded behavior.
3. Add tests for enabled and disabled states.
4. Document architecture impact in `docs/`.

## API Change

1. Update route, models, and service boundaries.
2. Verify request/response validation at boundaries.
3. Run focused API tests.
4. Document behavior changes.

## Escalation Logic Change

1. Modify canonical escalation modules only.
2. Add tests for expected decisions.
3. Validate no regressions in existing routes.

## System Change

1. Capture current system state.
2. Log rollback command.
3. Apply change via audited commands.
4. Validate expected impact and stability.

## Benchmark Update

Measurement policy is canonical in `agents/shared/MEASUREMENT_POLICY.md` (region claim, codified
recipes, reps, claim grammar, era labeling) — follow it, don't restate it. Workflow-specific
step: update `repos/epyc-inference-research/docs/reference/benchmarks/RESULTS.md` when a run
changes the master table.

## Handoff Closure And Roadmap Refresh

1. Reconcile handoff checklist against real code/tests before marking complete.
2. Extract durable findings into docs and agent playbooks; keep handoff as execution log, not the only source of truth.
3. Update the master index (`handoffs/active/master-handoff-index.md`): **delete** the completed row — terminal rows do not stay in the queue. Update `handoffs/blocked/BLOCKED.md` if a blocker changed.
4. Record evidence in `CHANGELOG.md` and progress log (`progress/YYYY-MM/`) with exact commands/tests used; performance/quality numbers use the claim grammar (`agents/shared/MEASUREMENT_POLICY.md`).
5. Move handoff from `handoffs/active/` to `handoffs/completed/` only after docs + trackers + evidence are in place.

## Orchestrator Lifecycle

Operational guidance for orchestrator lifecycle/stabilization work:
`docs/guides/agent-workflows/orchestrator-lifecycle.md`.
