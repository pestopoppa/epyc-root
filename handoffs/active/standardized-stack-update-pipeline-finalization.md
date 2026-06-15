# Standardized Stack Update Pipeline Finalization

**Status**: PARTIAL IMPLEMENTATION LANDED - canonical stack-change command and
promotion gates are live; current default check is green. Remaining work is
high-risk consumer migrations and W4 swap-CI.
**Created**: 2026-06-13
**Priority**: HIGH - stale model-specific constants can corrupt scoring,
routing, launch, planner context, and benchmark interpretation after stack
changes.
**History**:
[standardized-stack-update-pipeline-finalization-history-2026-06-15.md](../archived/standardized-stack-update-pipeline-finalization-history-2026-06-15.md)
preserves the completed chronology compacted out of this active handoff.
**Related**:
[model-stack-single-source-update-pipeline.md](model-stack-single-source-update-pipeline.md),
[stack-change-governance-pipeline.md](stack-change-governance-pipeline.md),
[model-stack-update-pipeline-audit.md](model-stack-update-pipeline-audit.md),
[model-stack-change-standardization-audit.md](model-stack-change-standardization-audit.md),
[model-capability-descriptors.md](model-capability-descriptors.md),
[routing-truth-restoration.md](routing-truth-restoration.md),
[fable5-findings-01-measurement-and-integrity.md](fable5-findings-01-measurement-and-integrity.md)

## Purpose

Finish the standardized pipeline that makes orchestration model/serving changes
safe:

1. structured stack truth changes first;
2. generated descriptors, stack priors, and operator summaries refreshed from
   that truth;
3. all known model-specific consumers validated;
4. production launch, AutoPilot resume, and benchmark preflight blocked when
   live model facts drift from generated truth.

Do not create a second registry or guard system. Extend the current
descriptor -> stack-prior -> guard -> consumer-migration path.

## Current Baseline

- Canonical command:
  `uv run python scripts/registry/stack_change_pipeline.py check --run-promotion-gate`
  in `epyc-orchestrator`.
- Default check after Orchestrator `7ad5965` is green:
  `runtime_attestation: ok`, `q_scorer_priors: ok`, and descriptors/stack
  priors fresh.
- Generated descriptors and stack priors are `status: compiled`; stack-prior
  role `known_gaps` are empty.
- Current all-surface warning baseline: `2 unique / 2 total`; both remaining
  surfaces are owned, expiring `waived_production_blocker` compatibility guards.
- Guard inventory currently reports `consumer_surface_count=13` and
  `rule_count=27`.
- Active operator topology docs were refreshed in `8221971`, `d94954a` marked
  remaining retired-role doc mentions as historical notes, and `7ad5965` moved
  legacy seed fixtures to exact inline allowances.
- W4 promotion-gate execution/failure coverage landed in Orchestrator
  `d9fd1eb`; system-card swap visibility landed in `4aed83d`;
  health/dashboard stack-prior witnesses landed in `8beaf79`; representative
  routing/API role-surface witnesses landed in `edd20f7`; swap-CI can still be
  broadened as new high-risk consumers are migrated.

## Outstanding Work

- [ ] Keep the two `waived_production_blocker` surfaces intentional, owned, and
  expiring; remove them if compatibility no longer needs them.
- [ ] Continue high-risk consumer migrations only after focused GitNexus impact
  checks. Use the stack-change surface manifest to pick the next consumer.
- [ ] Finish W4 swap-CI so representative stack changes prove generated
  descriptors, stack priors, q_scorer priors, operator summary, promotion-gate
  execution, and selected consumer witnesses move together.
- [ ] Keep direct benchmark, production launch, and AutoPilot preflight wired to
  the canonical gate; no new bypasses.

## Operating Rules

- Before editing root or orchestrator files, run `gitnexus status`; re-index
  through the repo wrapper if stale.
- Before code or high-impact doc changes, run `gitnexus impact ... --direction
  upstream` and keep the patch scoped to the blast radius.
- Active indices should stay dispatch-oriented. Completed chronology belongs in
  `progress/`, completed/archived handoffs, and commit history.
- No inference is required for this handoff unless a future consumer migration
  explicitly needs live runtime validation.

## Validation

For no-inference stack-change work in `epyc-orchestrator`:

```bash
uv run python scripts/validate/stack_change_guard.py --surface-summary-only --all-hardcoded-surfaces
uv run pytest -q tests/unit/test_stack_change_guard.py
uv run python scripts/registry/stack_change_pipeline.py check
```

For promotion-gate or launch-boundary changes:

```bash
uv run python scripts/registry/stack_change_pipeline.py check --run-promotion-gate
```
