# Model Stack Single-Source Update Pipeline

**Status**: READY FOR IMPLEMENTATION - stack-change surface inventory exposure is live as of `epyc-orchestrator` `34a0407`, the canonical preflight advertises the inventory command as of `b82ae3d`, and compact surface-warning summary mode is available as of `2cb3d6c`; the broader W2 consumer ownership manifest and remaining migrations are still open.
**Created**: 2026-06-13
**Priority**: HIGH - prevents stale model-specific quantities from silently corrupting routing, scoring, launch, planner prompts, replay analysis, and operator docs after a stack change
**Scope**: Documentation handoff only. No application code, inference, AutoPilot, server restarts, or index edits were performed in this sidecar pass.
**Related**: [standardized-stack-update-pipeline-finalization.md](standardized-stack-update-pipeline-finalization.md), [model-stack-update-pipeline-audit.md](model-stack-update-pipeline-audit.md), [model-stack-change-standardization-audit.md](model-stack-change-standardization-audit.md), [stack-change-governance-pipeline.md](stack-change-governance-pipeline.md), [model-capability-descriptors.md](model-capability-descriptors.md)

## Objective

Make orchestration-stack changes reliable by turning model-specific updates into a single-source pipeline:

1. edit structured truth;
2. compile generated contracts;
3. validate all consumers and docs;
4. refuse launch, AutoPilot resume, or benchmark interpretation when live model facts are stale.

The immediate trigger was stale q_scorer/model-stack quantities: `frontdoor` and `coder_escalation` share the same live model/server, `architect_general` and `ingest_long_context` are HOT, and `architect_coding` is retired as a distinct live role. Those facts must not depend on somebody remembering to update local constants.

This handoff is a concise pickup contract. The long historical audit lives in `model-stack-update-pipeline-audit.md`; implementation should extend the existing descriptor -> stack-prior -> guard -> consumer-migration path instead of inventing a parallel registry.

## Current Evidence

- `epyc-orchestrator/docs/reference/stack-truth-precedence.md` already defines the precedence rule: live serving topology first, model descriptors second, role metadata third, historical/benchmark records last.
- `epyc-orchestrator/orchestration/derived/stack_priors.yaml` is the generated consumer contract. Current contract version is `4`, with required role, serving, launch, runtime, and prior fields.
- `epyc-orchestrator/scripts/registry/stack_change_pipeline.py` already composes descriptor check/update, stack-prior check/update, procedure enum sync/check, loose guard, all-surface guard, strict guard, and simulated fixture references.
- `epyc-orchestrator/scripts/validate/stack_change_guard.py` now exposes a machine-readable hardcoded-surface rule inventory in `34a0407`: `hardcoded_surface_rule_inventory()` plus `--list-hardcoded-surface-rules --surface-inventory-format yaml|json`. The inventory reports `version`, `rule_count`, `categories`, and per-rule `rule_id`, category, pattern, path/exclude globs, comment-line handling, and remediation. The same commit fixed direct-by-path CLI import hygiene so `python scripts/validate/stack_change_guard.py ...` works outside pipeline imports.
- `epyc-orchestrator/scripts/registry/stack_change_pipeline.py check` now prints `surface_inventory: run uv run python scripts/validate/stack_change_guard.py --list-hardcoded-surface-rules` in the passing acceptance block as of `b82ae3d`, so the canonical stack-change preflight points operators at the machine-readable scanner-rule catalog. No enforcement semantics changed.
- `epyc-orchestrator/scripts/validate/stack_change_guard.py` now exposes `hardcoded_surface_warning_counts()` and `--surface-summary-only` as of `2cb3d6c`, letting operators compact hardcoded-surface scan warnings into category counts such as waived production blockers, legacy tests, and historical docs while preserving the default detailed warning output. This is reporting hygiene only; canonical pipeline output and guard policy are unchanged.
- `epyc-orchestrator/orchestration/repl_memory/q_scorer.py` now loads live TPS, quality, and memory priors from stack priors first and labels local constants as degraded fallback.
- Generated/system-card and launch-wrapper work has started: AutoPilot live-stack rows and production launch summaries are derived from stack priors or stack manifest instead of hand-written inventory.
- Root GitNexus was refreshed before this edit. New handoff path impact is `UNKNOWN` with `impactedCount=0` because the file did not exist yet; nearby `model-stack-change-standardization-audit.md` is a MEDIUM coordination surface, so this pass avoids modifying it or shared indices.

## Single-Source Contract

Every model-stack change must classify and update these quantities through structured sources:

| Quantity | Canonical source | Generated surface / consumer |
|---|---|---|
| Live role -> endpoint, port, slots, tier, shared-server binding | `epyc-orchestrator/orchestration/model_registry.yaml` `server_mode.*`, reconciled with `scripts/server/stack_manifest.py` | `orchestration/derived/stack_priors.yaml` `roles.*.serving` |
| Physical model identity, modality, context, quant, evidence | `orchestration/model_descriptors.yaml` and descriptor compiler inputs | `stack_priors.yaml` `model`, `evidence`, `priors`, `acceleration` |
| Benchmark/candidate history | `epyc-inference-research/orchestration/model_registry.yaml` and benchmark artifacts | imported into descriptors only with provenance/status; never live truth by itself |
| q_scorer, seeding, replay, reward cost/TPS/quality | `stack_priors.yaml` `roles.*.priors` | typed loaders or explicit degraded fallback provenance |
| Procedure role enums and executor permissions | live roles from `stack_priors.yaml` | `sync_procedure_role_enums.py` generated/check mode |
| Launch runtime, binary, context, KV/cache, spec/MTP, mmproj | stack manifest/runtime witnesses projected into stack priors | stack-change guard and launch/status consumers |
| Runtime policy tables: admission, locks, tap streaming, high-cost roles | stack-prior tier/slots/model class plus explicit policy hints | generated policy projection or clearly named degraded fallback |
| Operator docs, planner prompts, dashboards, system cards | generated stack summary plus runtime attestation | no manual current-stack tables unless labelled historical |

Rules:

- Production consumers should use typed helpers around `src/registry/stack_priors.py` where possible.
- Direct YAML parsing is acceptable for scripts that cannot import runtime code, but it must preserve degraded-mode warnings and source provenance.
- Fallback constants must be named `FALLBACK_*` or `DEGRADED_*`, must exclude retired live roles unless testing historical compatibility, and must not silently satisfy live decisions while fresh stack priors exist.
- Historical docs and replay data may retain retired roles only with era/legacy classification; they are not live role truth.

## Required Operator Workflow

The target operator workflow should be one canonical no-inference command family:

```bash
cd /mnt/raid0/llm/epyc-orchestrator
uv run python scripts/registry/stack_change_pipeline.py check
uv run python scripts/registry/stack_change_pipeline.py update
uv run python scripts/registry/stack_change_pipeline.py check --strict
```

`check` must be read-only and fail when generated artifacts are stale, procedure enums drift, stack-prior contracts are invalid, source hashes changed, live known gaps block decision-grade consumers, or production hardcoded surfaces are unwaived.

`update` must write only generated artifacts from structured truth: descriptors, stack priors, procedure role enums, and generated stack summaries once those exist. It must never invent missing measurements, classify hardcoded surfaces by default, or edit historical records.

Before launch, AutoPilot resume, or benchmark interpretation, require:

- descriptor check/update clean;
- stack-prior check/update clean;
- procedure enum check clean;
- stack-change guard loose/all-surface/strict result summarized;
- simulated data-only stack-change fixtures passing;
- current process/port/runtime attestation compared against generated priors;
- doc/planner/operator summaries generated or explicitly marked historical.

## Implementation Work Packages

### W1 - Finish The Canonical Pipeline Command

Goal: one operator command replaces scattered manual steps.

Tasks:

- Extend `scripts/registry/stack_change_pipeline.py` output with an acceptance summary: descriptor freshness, stack-prior freshness, source hashes, loose/all-surface/strict guard counts, stale surface categories, simulated fixture target, and exact remediation commands.
- Keep the `b82ae3d` `surface_inventory:` acceptance hint in the passing `check` output so operators can discover the scanner-rule catalog before launch or AutoPilot resume review.
- Add a "promotion gate" mode for launch/AutoPilot decisions that refuses on production hardcoded surfaces, missing decision-grade priors, stale generated summaries, or unattested live processes.
- Ensure update mode writes generated summaries only after structured artifacts are fresh.

Likely targets:

- `scripts/registry/stack_change_pipeline.py`
- `scripts/validate/stack_change_guard.py`
- `src/registry/stack_priors.py`
- `tests/unit/test_stack_change_pipeline.py`
- `tests/unit/test_stack_change_pipeline_simulated_fixtures.py`

### W2 - Add A Complete Model-Specific Surface Inventory

Goal: every live model-specific quantity has an owner and validator.

Current increment: `34a0407` exposes the existing hardcoded-surface scanner rules as a machine-readable inventory through `hardcoded_surface_rule_inventory()` and the `stack_change_guard.py --list-hardcoded-surface-rules` CLI. This gives operators and docs sidecars an auditable rule catalog, but it is not yet the full W2 manifest of every model-specific consumer surface and owner.

Tasks:

- Add a machine-readable manifest of model-specific consumer surfaces: q_scorer, seeding, routing priors, admission, lock/tap policy, config URLs, health probes, launch maps, dashboards, system card, planner prompts, procedure enums, and docs summaries.
- Use the `34a0407` guard-rule inventory as the scanner-rule input to that manifest; keep the distinction clear between "scanner rules known" and "all model-specific consumer surfaces owned".
- Classify each surface as generated, typed consumer, explicit degraded fallback, legacy test, historical doc, or open production blocker.
- Teach the guard to report unclassified model-specific surfaces as actionable drift.

Likely targets:

- `orchestration/stack_change_guard_exceptions.yaml`
- `scripts/validate/stack_change_guard.py`
- `tests/unit/test_stack_change_guard.py`
- root handoff/wiki docs after implementation lands

### W3 - Centralize Typed Consumer APIs

Goal: production code stops hand-parsing stack facts.

Tasks:

- Add or extend stack-prior helpers for live roles, retired roles, serving records, scorer priors, policy hints, launch requirements, modality/projector requirements, and generated summary rows.
- Migrate remaining local policy tables where model identity, tier, port, cost, or residency is the underlying reason.
- Keep non-live compatibility aliases as explicit compatibility API, not live role discovery.

Likely targets:

- `src/registry/stack_priors.py`
- `src/config/models.py`
- `src/runtime/inference_lock.py`
- `src/runtime/inference_tap.py`
- `src/api/admission.py`
- dashboard/status/health routes
- q_scorer and seeding/replay consumers

### W4 - Generate Current Docs And Planner Context

Goal: operator-facing text cannot become hidden source truth.

Tasks:

- Generate current stack summaries from stack priors and runtime attestation for system cards, status pages, and runbooks.
- Add guard coverage for static current-stack tables in prompts/docs/scripts.
- Label historical docs explicitly when they preserve old role/model names.
- Use documentation sidecars during implementation so docs are updated in parallel with code changes, but do not let sidecars edit shared indices unless the main workflow approves.

Likely targets:

- `scripts/autopilot/gen_system_card.py`
- `scripts/server/launch_production.sh`
- dashboard/status routes
- root `handoffs/active/*` and `wiki/*` summaries
- docs build/rewrite validation where applicable

### W5 - Prove Data-Only Stack Changes

Goal: model swaps and role retirements are data updates, not source edits.

Tasks:

- Extend simulated fixtures for:
  - shared-server model swaps like `frontdoor` / `coder_escalation`;
  - role retirement like `architect_coding`;
  - HOT/WARM tier changes;
  - context/KV/spec/MTP changes;
  - VL model/mmproj swaps;
  - research-only candidate additions.
- Acceptance: generated descriptors/priors/enums/summaries change, production code does not.
- Fail if live consumers read stale fallback tables while valid stack priors exist.

Likely targets:

- `tests/unit/test_stack_change_pipeline_simulated_fixtures.py`
- stack-prior compiler fixtures
- guard fixtures for stale surface recurrence

## Validation Checklist

Run this no-inference validation set after implementation changes:

```bash
cd /mnt/raid0/llm/epyc-orchestrator
uv run python scripts/registry/stack_change_pipeline.py check
uv run python scripts/registry/stack_change_pipeline.py check --allow-known-gaps
uv run python scripts/registry/stack_change_pipeline.py update
uv run python scripts/validate/stack_change_guard.py
uv run python scripts/validate/stack_change_guard.py --list-hardcoded-surface-rules --surface-inventory-format yaml
uv run python scripts/validate/stack_change_guard.py --list-hardcoded-surface-rules --surface-inventory-format json
uv run python scripts/validate/stack_change_guard.py --all-hardcoded-surfaces
uv run python scripts/validate/stack_change_guard.py --all-hardcoded-surfaces --surface-summary-only
uv run python scripts/validate/stack_change_guard.py --strict
python3 scripts/registry/sync_procedure_role_enums.py --check
uv run --with pytest pytest -q \
  tests/unit/test_stack_change_pipeline.py \
  tests/unit/test_stack_change_pipeline_simulated_fixtures.py \
  tests/unit/test_stack_change_guard.py \
  tests/unit/test_stack_priors_compiler.py \
  tests/unit/test_model_descriptor_compiler.py \
  tests/unit/test_model_descriptors_schema.py \
  tests/unit/test_q_scorer.py
```

If code touches API/runtime consumers, add the focused consumer tests for admission, config, health/status, dashboard, vision, seeding, GraphRouter, and system-card generation.

## Non-Goals

- Do not choose the next model stack or run inference in this handoff.
- Do not replace the research registry; it remains evidence/candidate history.
- Do not make historical docs or old replay labels disappear; classify them.
- Do not hand-edit generated YAML to pass validation.
- Do not let fallback constants become "good enough" live truth.
- Do not register broad index updates from a sidecar unless the main workflow requests it.

## Done Criteria

- A documented operator can perform a role model swap by editing structured sources, running the canonical pipeline, and reviewing generated diffs.
- q_scorer, seeding/reward, admission, routing priors, runtime policy classifications, launch/status probes, and planner/operator summaries read stack-prior truth or report explicit degraded fallback provenance.
- `stack_change_pipeline.py check` is the canonical no-inference preflight for launch, AutoPilot resume, and model-stack benchmark interpretation.
- Simulated data-only fixtures prove shared-server swaps, role retirement, tier changes, launch/runtime changes, and VL projector changes without production source edits.
- All current-stack docs/prompts are generated or labelled historical.
