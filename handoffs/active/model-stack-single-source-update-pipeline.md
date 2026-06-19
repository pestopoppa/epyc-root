# Model Stack Single-Source Update Pipeline

**Status**: PARTIAL IMPLEMENTATION LANDED - stack-prior single-source contract,
runtime attestation, generated stack summaries, scanner-rule ownership,
production launch gate, AutoPilot preflight gate, direct benchmark runtime
enforcement, and representative frontdoor/worker/vision swap-CI coverage are
live. Remaining work is other high-risk P2 consumer migrations plus future
swap-CI expansion as new consumers are migrated.
**Created**: 2026-06-13
**Priority**: HIGH - stale model-specific quantities can silently corrupt
routing, scoring, launch, planner prompts, replay analysis, and operator docs
after a stack change.
**History**:
[model-stack-single-source-update-pipeline-history-2026-06-15.md](../archived/model-stack-single-source-update-pipeline-history-2026-06-15.md)
and
[model-stack-single-source-update-pipeline-history-through-2026-06-19.md](../archived/model-stack-single-source-update-pipeline-history-through-2026-06-19.md)
preserve completed chronology compacted out of this active handoff.
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

- Generated model descriptors and `orchestration/derived/stack_priors.yaml`
  are the source contract for live model, role, serving, launch, quality, and
  memory facts.
- Canonical stack-change checks are live for descriptor/stack-prior freshness,
  stack-manifest registry drift, q_scorer provenance, runtime attestation,
  production launch, AutoPilot preflight, and direct benchmark preflight.
- Current hardcoded-surface inventory is owned by
  `orchestration/stack_change_surface_manifest.yaml` with
  `consumer_surface_count=13` and `rule_count=27`; the previous active-code
  warning baseline is clean.
- Shared stack-prior helpers now cover the main config/admission, health,
  status, preflight, routing/action, prompt/delegation, benchmark/eval, and
  runtime-policy consumers. Completed details through 2026-06-19 are compacted
  in
  [model-stack-single-source-update-pipeline-history-through-2026-06-19.md](../archived/model-stack-single-source-update-pipeline-history-through-2026-06-19.md).
- `src.runtime.inference_tap` safe-mode stream policy now resolves its
  generated-prior or manifest-derived non-stream role set dynamically instead
  of freezing `SAFE_NON_STREAM_ROLES` at import time; the legacy module
  attribute remains available for compatibility.
- `src.runtime.inference_lock` exclusive/shared role policy now resolves its
  generated-prior or manifest-derived lock role sets dynamically instead of
  freezing `HEAVY_ROLES` / `LIGHT_ROLES` at import time; legacy module
  attributes remain available for compatibility.
- `src.api.routes.chat_routing` heuristic prior roles now keep generated stack
  priors as primary and derive degraded fallback candidates from the computed
  stack manifest instead of a four-role static tuple; embedding services are
  excluded and aliases are canonicalized.
- `orchestration.repl_memory.bilinear_scorer` cold-start model features now
  keep generated stack priors as primary and derive degraded fallback specs
  from compiled model descriptors instead of a hand-maintained role/model
  feature table.
- `scripts.graph_router.train_graph_router` model-fleet training nodes now
  keep generated stack priors as primary and derive degraded fallback fleet
  records from compiled model descriptors instead of a static model-fleet table.
- X-MAS has an evidence-backed true function-axis 5x5 winner table and a
  default-off guarded enforce path, but the 2026-06-18 held-out A/B returned
  `decision: hold`; regression diagnostics show hard replacement of the learned
  incumbent route, so a constrained/incumbent-aware policy is required before
  any new enforce attempt.

## Completed Scope

| Through | Historical ledger |
|---------|-------------------|
| 2026-06-15 | [model-stack-single-source-update-pipeline-history-2026-06-15.md](../archived/model-stack-single-source-update-pipeline-history-2026-06-15.md) |
| 2026-06-19 | [model-stack-single-source-update-pipeline-history-through-2026-06-19.md](../archived/model-stack-single-source-update-pipeline-history-through-2026-06-19.md) |

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
  impact before touching production code, and keep HIGH/CRITICAL shared-helper
  edits on the main thread.
- [ ] Preserve env override precedence and explicit degraded fallbacks whenever
  migrating config, runtime, benchmark, or prompt consumers.
- [ ] Continue migrating remaining high-risk P2 consumers only where a concrete
  duplicated model/role/serving fact or duplicated stack-prior traversal still
  exists; avoid broad renderer rewrites unless there is a narrow helper seam.
- [ ] Broaden W4 swap-CI opportunistically as migrated consumers create new
  witness surfaces; do not add abstract fixture coverage without a migrated
  consumer to prove.
- [ ] Build an incumbent-aware/constrained X-MAS policy before any new
  `mode: enforce` attempt. The table is evidence-backed, but the 2026-06-18
  held-out run returned `decision: hold` and diagnostics identify hard route
  replacement as the first-order failure, so production routing remains
  default-off.
- [ ] Keep `scripts/autopilot/short_term_memory.md` under review as live run
  state; do not prune it during active AutoPilot execution.
- [ ] Keep completed implementation logs out of active indices; record future
  closures in `progress/` and compact/archive at wrap-up.

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
