# Model Stack Single-Source Update Pipeline

**Status**: PARTIAL IMPLEMENTATION LANDED - stack-prior single-source contract,
runtime attestation, generated stack summaries, scanner-rule ownership,
production launch gate, AutoPilot preflight gate, and direct benchmark runtime
enforcement are live. Remaining work is other high-risk P2 consumer migrations
and swap-CI coverage.
**Created**: 2026-06-13
**Priority**: HIGH - stale model-specific quantities can silently corrupt
routing, scoring, launch, planner prompts, replay analysis, and operator docs
after a stack change.
**History**:
[model-stack-single-source-update-pipeline-history-2026-06-15.md](../archived/model-stack-single-source-update-pipeline-history-2026-06-15.md)
preserves the completed chronology compacted out of this active handoff.
**Related**:
[standardized-stack-update-pipeline-finalization.md](standardized-stack-update-pipeline-finalization.md),
[model-stack-update-pipeline-audit.md](model-stack-update-pipeline-audit.md),
[model-stack-change-standardization-audit.md](model-stack-change-standardization-audit.md),
[stack-change-governance-pipeline.md](stack-change-governance-pipeline.md),
[model-capability-descriptors.md](model-capability-descriptors.md)

## Objective

Make orchestration-stack changes reliable by ensuring model-specific facts are
updated once, then projected everywhere:

1. edit structured truth;
2. compile generated contracts;
3. validate all consumers and docs;
4. refuse launch, AutoPilot resume, or benchmark interpretation when generated
   truth and live/runtime facts disagree.

The concrete trigger remains the stale-quantity class of bug: shared models,
retired roles, HOT/WARM status, memory footprints, context windows, launch
ports, q_scorer costs, and prompt/operator labels must not be duplicated in
unowned local constants.

## Current Baseline

- Source contract is generated through model descriptors and
  `orchestration/derived/stack_priors.yaml`.
- Runtime attestation is part of the stack-change pipeline and currently
  reports `runtime_attestation: ok`.
- q_scorer prior provenance is part of the pipeline and currently reports
  `q_scorer_priors: ok`.
- Production `orchestrator_stack.py start`, AutoPilot preflight, and direct
  benchmark preflight all run the canonical stack-change gate before mutating
  runtime state.
- Direct benchmark runtime enforcement is closed by Orchestrator `09d9028`.
- Active operator docs were refreshed by `8221971`, historical retired-role doc
  notes were explicitly marked by `d94954a`, and legacy seed fixtures were moved
  to exact inline allowances by `7ad5965`; current warning baseline is
  `2 unique / 2 total`, both owned expiring `waived_production_blocker` guards.
- Guard inventory reports `consumer_surface_count=13` and `rule_count=27`.

## Required Contract

Any future stack update should be accepted only when these hold:

- generated descriptors, stack priors, procedure enums, and operator summaries
  are fresh;
- model-specific consumer surfaces are either generated from stack priors or
  explicitly owned degraded fallbacks;
- q_scorer/reward/routing/admission/launch/status/prompt consumers do not hide
  stale local model facts;
- live runtime flags, model paths, mmproj paths, context/KV/spec flags, and
  known-stack listeners agree with generated launch truth;
- scanner rules and consumer surfaces have manifest ownership metadata.

## Outstanding Work

- [ ] Pick the next high-risk P2 consumer from
  `orchestration/stack_change_surface_manifest.yaml`; run focused GitNexus
  impact before touching production code.
- [ ] Preserve env override precedence and explicit degraded fallbacks whenever
  migrating config or runtime consumers.
- [ ] Extend W4 swap-CI coverage so representative stack swaps prove generated
  artifacts and selected consumers move together.
- [ ] Keep completed implementation logs out of active indices; record future
  closures in `progress/` and move closed handoff material to
  `handoffs/completed/` or `handoffs/archived/`.

## Validation

Default no-inference acceptance:

```bash
uv run python scripts/registry/stack_change_pipeline.py check
```

Promotion/launch-boundary acceptance:

```bash
uv run python scripts/registry/stack_change_pipeline.py check --run-promotion-gate
```

Surface inventory checks:

```bash
uv run python scripts/validate/stack_change_guard.py --surface-summary-only --all-hardcoded-surfaces
uv run python scripts/validate/stack_change_guard.py --inventory-json /tmp/stack-change-inventory.json
```
