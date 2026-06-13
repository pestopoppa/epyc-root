# Model Stack Update Pipeline Hardening

**Status**: COMPLETED sidecar audit - reviewed and merged into `handoffs/active/model-stack-update-pipeline-audit.md` on 2026-06-13
**Created**: 2026-06-13
**Priority**: HIGH - stale model-specific constants can silently bias scoring, routing, launch, planner guidance, and replay interpretation after stack changes
**Scope**: Audit and implementation handoff only. No inference, AutoPilot, heavy indexing, code commits, index edits, or progress-log edits were performed.
**Primary owners**: Continue through `standardized-stack-update-pipeline-finalization.md` and `stack-change-governance-pipeline.md`; this file is a hardening bridge, not a replacement process.

## Audit Summary

The standardized stack-change pipeline exists and is the right foundation. It now has descriptor compilation, stack-prior compilation, procedure enum sync, source-hash validation, launch endpoint/port/tier alignment, and curated hardcoded-surface scanning. The current defect is not absence of machinery; it is that promotion remains permissive around descriptor gaps, degraded fallback constants, and ungenerated launch/model metadata.

The latest q_scorer memory-cost correction is a symptom of the remaining systemic issue: every model-specific quantity must be regenerated or validated from structured stack truth, and fallback constants must be visibly degraded mode rather than silent live defaults.

Sidecar checks performed:

```bash
cd /mnt/raid0/llm/epyc-root
gitnexus status
gitnexus impact handoffs/active/model-stack-update-pipeline-hardening.md --repo epyc-root --direction upstream

cd /mnt/raid0/llm/epyc-orchestrator
uv run python scripts/registry/stack_change_pipeline.py check --allow-known-gaps
uv run python scripts/validate/stack_change_guard.py --all-hardcoded-surfaces
```

Observed results:

- Root GitNexus was up to date at commit `acd332e`; the new markdown path was not yet indexed, so impact returned `risk=UNKNOWN`, `impactedCount=0`.
- `stack_change_pipeline.py check --allow-known-gaps` still exits 1 because `orchestration/model_descriptors.yaml` is stale. Stack priors and procedure enums report fresh.
- Guard output is improved but still permissive: `--all-hardcoded-surfaces` reports `WARN: 109 stack-prior warning(s)`.
- Strict gating is still bypassed through `--allow-known-gaps`; live stack gaps are warnings rather than launch blockers.
- The orchestrator working tree already contains uncommitted main-track edits around `src/registry/stack_priors.py`, `scripts/validate/stack_change_guard.py`, tests, and `orchestration/derived/stack_priors.yaml`. I did not touch or revert them.

## Existing Machinery

Use and harden these instead of inventing a parallel registry:

- `/mnt/raid0/llm/epyc-orchestrator/docs/reference/stack-truth-precedence.md`
- `/mnt/raid0/llm/epyc-orchestrator/orchestration/model_registry.yaml`
- `/mnt/raid0/llm/epyc-orchestrator/orchestration/model_descriptors.yaml`
- `/mnt/raid0/llm/epyc-orchestrator/src/registry/model_descriptors.py`
- `/mnt/raid0/llm/epyc-orchestrator/src/registry/stack_priors.py`
- `/mnt/raid0/llm/epyc-orchestrator/orchestration/derived/stack_priors.yaml`
- `/mnt/raid0/llm/epyc-orchestrator/scripts/registry/stack_change_pipeline.py`
- `/mnt/raid0/llm/epyc-orchestrator/scripts/registry/compile_descriptors.py`
- `/mnt/raid0/llm/epyc-orchestrator/scripts/registry/compile_stack_priors.py`
- `/mnt/raid0/llm/epyc-orchestrator/scripts/registry/sync_procedure_role_enums.py`
- `/mnt/raid0/llm/epyc-orchestrator/scripts/validate/stack_change_guard.py`
- `/mnt/raid0/llm/epyc-orchestrator/orchestration/stack_change_guard_exceptions.yaml`
- `/mnt/raid0/llm/epyc-orchestrator/scripts/server/stack_manifest.py`
- `/mnt/raid0/llm/epyc-orchestrator/scripts/server/stack_numa.py`
- `/mnt/raid0/llm/epyc-inference-research/orchestration/model_registry.yaml`

Current generated-truth rule:

1. Live serving truth: orchestrator `model_registry.yaml` `server_mode.*`, reconciled with `stack_manifest.py`/`stack_numa.py`.
2. Physical model and evidence truth: orchestrator `model_descriptors.yaml`, compiled from lean and research registries where possible.
3. Research registry: evidence and candidate history only; never direct live deployment truth.
4. Consumer truth: generated `orchestration/derived/stack_priors.yaml` plus typed helpers.
5. Fallback constants: degraded/offline mode only, with explicit provenance.

## Stale Quantity Surfaces

Highest-risk drift surfaces found in the current tree:

- q_scorer fallback tables: `orchestration/repl_memory/q_scorer.py` still seeds TPS, quality, and memory dictionaries from `FALLBACK_*`/legacy quality tables before overlaying stack priors. This is acceptable for degraded scripts, but production-like callers can still receive silent fallback-filled values when a live prior is missing.
- Descriptor completeness: generated records still carry `ctx_max: null`, vision `mmproj` gaps, worker shared-runtime conflicts, and mixed measurement evidence. These block strict launch gating.
- Descriptor freshness: the canonical pipeline reports descriptor staleness even with known gaps allowed. Stack priors and procedure enums are fresh, so descriptor drift is the current command-level blocker.
- Launch projection: endpoint, primary port, and tier are now guarded against computed launch manifest, and source artifacts are being expanded to include `stack_manifest.py`/`stack_numa.py`; broader launch fields still need comparison: model paths, binary family/dir, slots, NUMA replicas, mmproj, KV, and acceleration flags.
- Hardcoded-surface scanner coverage: current rules catch retired `architect_coding`, seeding TPS, stale CLI probes, AutoPilot program endpoint guidance, and procedure enum drift. They do not yet cover all model-specific live maps such as feature flags, policy/executor role tables, classifier tier comments, q_scorer fallback misuse, generated-doc freshness, or every launch metadata surface.
- Historical/current doc split: docs and tests legitimately preserve retired-role examples, but current operator diagrams and summaries should be generated from stack priors or explicitly labeled historical.

## Prioritized Tasks

### P0 - Normalize the current pipeline state

Goal: make the main track start from a clean, explainable baseline.

Tasks:

- Reconcile the current uncommitted orchestrator changes that add `stack_manifest` and `stack_numa` source artifacts to stack priors and guard tests.
- Run and record:

```bash
cd /mnt/raid0/llm/epyc-orchestrator
uv run python scripts/registry/stack_change_pipeline.py check --allow-known-gaps
uv run python scripts/validate/stack_change_guard.py --all-hardcoded-surfaces
uv run pytest -q tests/unit/test_stack_change_pipeline.py tests/unit/test_stack_change_guard.py tests/unit/test_stack_priors_compiler.py
```

- Decide whether descriptor staleness is expected curated-evidence drift or an actual generated artifact update that should be committed.
- Improve `stack_change_pipeline.py check` output so descriptor staleness names exact changed model IDs/fields and the required operator decision, not only "run update".

Acceptance:

- The main track can state exactly why descriptor check fails.
- Stack priors source artifacts include every source that can affect generated serving truth.
- No generated artifact update can silently remove a model descriptor without explicit approval.

### P1 - Make q_scorer live priors fail closed

Goal: prevent another stale memory/TPS/quality constant incident.

Tasks:

- Split q_scorer priors into two paths:
  - strict live loader: returns only values present in valid stack priors and errors when required live role priors are missing.
  - degraded loader: may use `FALLBACK_*`, but returns/logs provenance as `degraded_fallback`.
- Add provenance to `QScorerPriors`, or an adjacent metadata object, for TPS, quality, and memory values.
- Add guard coverage that fails if production/default q_scorer construction silently fills a live role from fallback while stack priors are present.
- Keep tests proving current truths:
  - `frontdoor` and `coder_escalation` share model/server/memory truth.
  - `architect_general` and `ingest_long_context` are HOT cost `1.0`.
  - `architect_coding` is absent from live priors.

Acceptance:

- Missing or invalid stack priors cannot be mistaken for live scoring truth.
- Fallback use is visible in logs or returned metadata.
- A stack model swap changes q_scorer costs through generated priors without hand-editing q_scorer constants.

### P2 - Complete descriptor and stack-prior semantics

Goal: make strict mode meaningful for live consumers.

Tasks:

- Add structured fields for:
  - `ctx_model_max`
  - `ctx_launch_effective`
  - KV quant/cache settings
  - vision `mmproj` path/projector identity
  - launch binary family/path requirements
  - draft/MTP/spec decode knobs
  - measurement status: `decision_grade`, `observation`, `stale`, or `missing`
- Resolve worker shared-runtime semantics for `worker_general`, `worker_math`, `toolrunner`, and `worker_explore`: encode whether they are logical roles on one runtime, aliases, or stale role records.
- Preserve gaps where facts are unknown, but classify each gap by severity.

Acceptance:

- Strict mode can distinguish `launch_blocking`, `live_consumer_blocking`, `measurement_observation`, `candidate_only`, and waived gaps.
- Context, KV, mmproj, and shared-runtime facts are no longer free-text gaps for live roles.
- Decision-grade routing/scoring consumers can require structured evidence instead of comments.

### P3 - Expand launch and runtime validation

Goal: a launch cannot proceed with stale model-specific topology.

Tasks:

- Extend guard comparison beyond endpoint/primary port/tier:
  - `PORT_MAP`
  - `ROLE_LAUNCH_META`
  - `NUMA_CONFIG`
  - primary and replica ports
  - model paths
  - binary family/dir
  - slots
  - mmproj paths
  - KV/cache settings
  - MTP/spec acceleration flags
- Wire the canonical stack-change check into launch/preflight paths with a diagnostic override, not as advisory output.
- Add stale-running-process attestation: process start time and launch args must postdate source/derived stack changes before reporting deployed success.

Acceptance:

- `orchestrator_stack.py start` or its preflight refuses stale generated stack truth by default.
- A change to launch metadata that affects stack priors is caught even when the registry file did not change.
- Current process state can be proven to match the generated contract.

### P4 - Broaden hardcoded-surface coverage without overmatching

Goal: find live drift surfaces while preserving useful historical/test records.

Tasks:

- Add targeted guard rules or semantic validators for:
  - q_scorer fallback use as live truth
  - retired topology feature flags such as `langgraph_architect_coding`
  - role permission/policy maps that should follow generated live roles
  - classifier tier/model-size comments that are treated as current policy
  - generated operator summaries and system cards
  - direct model/port/path constants in launch-adjacent scripts
- Classify tests containing retired roles as `legacy_test` or migrate them to generated fixtures.
- Generate current stack docs/summaries from stack priors and label old docs as historical snapshots.

Acceptance:

- `stack_change_guard.py --all-hardcoded-surfaces` separates production blockers, degraded fallbacks, legacy tests, and historical docs.
- Production blocker count can be driven to zero except explicitly waived, expiring exceptions.
- Current operator docs do not carry hand-written live stack tables.

### P5 - Add data-only simulated stack-change fixtures

Goal: prove model-stack changes are data changes, not scavenger hunts.

Tasks:

- Add end-to-end no-inference fixtures for:
  - shared-server model swap: `frontdoor`/`coder_escalation`
  - HOT/WARM tier change: `architect_general` or `ingest_long_context`
  - retired-role removal: `architect_coding`
  - worker shared-runtime alias changes
  - vision model/mmproj change
  - launch metadata/source-artifact change
- Assert descriptors, stack priors, procedure enums, q_scorer priors, launch checks, and generated summaries update with zero production-code edits.

Acceptance:

- At least two realistic simulated swaps pass in CI.
- A stale q_scorer memory/TPS constant or dead port table fails a fixture before merge.
- The canonical `stack_change_pipeline.py check` runs these tests or clearly prints the exact test target to run.

### P6 - Define the operator workflow and promotion gate

Goal: one reliable process for humans and autonomous agents.

Required workflow:

```bash
cd /mnt/raid0/llm/epyc-orchestrator
uv run python scripts/registry/stack_change_pipeline.py check
uv run python scripts/registry/stack_change_pipeline.py update
uv run python scripts/registry/stack_change_pipeline.py check
uv run pytest -q tests/unit/test_stack_change_pipeline.py tests/unit/test_stack_change_guard.py tests/unit/test_stack_priors_compiler.py tests/unit/test_q_scorer.py
```

Promotion rule:

- No AutoPilot restart, launch, or benchmark interpretation should proceed after a model-stack edit unless the stack-change pipeline is clean or an explicit diagnostic override is recorded.
- `--allow-known-gaps` is a development bridge only. It should not be a production promotion gate.

Acceptance:

- A model assignment, role retirement, tier change, or port change has one documented command path.
- The command is read-only in `check`, generated-artifact-only in `update`, and fail-closed on live production blockers.
- The final output is actionable: exact stale surfaces, exact generated deltas, exact remaining waived/known gaps, and exact next commands.

## Dependency Graph

- P0 blocks all other work because the current tree already contains stack-prior source-artifact WIP and descriptor staleness.
- P1 can proceed in parallel with P2, but strict q_scorer live mode depends on P2 for any role whose priors remain gaps.
- P2 blocks promotion of strict mode and simulated swaps.
- P3 depends on P0 and the launch-relevant subset of P2.
- P4 can proceed incrementally, but broad production blocker enforcement depends on P2 severity classification.
- P5 depends on P1/P2/P3 enough to test realistic generated outputs.
- P6 is the final integration pass after P0-P5 make the command trustworthy.

## Validation Commands

No-inference validation suite for the main track:

```bash
cd /mnt/raid0/llm/epyc-orchestrator

python3 -m py_compile \
  src/registry/model_descriptors.py \
  src/registry/stack_priors.py \
  orchestration/repl_memory/q_scorer.py \
  scripts/registry/stack_change_pipeline.py \
  scripts/validate/stack_change_guard.py \
  scripts/server/stack_manifest.py \
  scripts/server/stack_numa.py

uv run ruff check \
  src/registry/model_descriptors.py \
  src/registry/stack_priors.py \
  orchestration/repl_memory/q_scorer.py \
  scripts/registry/stack_change_pipeline.py \
  scripts/validate/stack_change_guard.py

uv run python scripts/registry/stack_change_pipeline.py check --allow-known-gaps
uv run python scripts/validate/stack_change_guard.py --all-hardcoded-surfaces
uv run python scripts/validate/stack_change_guard.py --strict

uv run pytest -q \
  tests/unit/test_stack_change_pipeline.py \
  tests/unit/test_stack_change_guard.py \
  tests/unit/test_stack_priors_compiler.py \
  tests/unit/test_model_descriptor_compiler.py \
  tests/unit/test_model_descriptors_schema.py \
  tests/unit/test_sync_procedure_role_enums.py \
  tests/unit/test_q_scorer.py \
  tests/unit/test_seeding_rewards.py \
  tests/unit/test_autopilot_preflight_audit.py \
  tests/unit/test_autopilot_system_card.py \
  tests/unit/test_graph_router_action_space.py
```

Useful audit searches:

```bash
cd /mnt/raid0/llm/epyc-orchestrator

rg -n "FALLBACK_|BASELINE_QUALITY|memory_cost_by_role|baseline_tps_by_role|ctx_max: null|mmproj path|Role-server conflict|PORT_MAP|ROLE_LAUNCH_META|LANGGRAPH_ARCHITECT_CODING|architect_coding" \
  src scripts orchestration tests docs
```

## Acceptance Criteria

The hardening work is complete when:

- `stack_change_pipeline.py check` passes without `--allow-known-gaps` for live launch-relevant facts.
- Descriptor staleness is either resolved or reported with exact field-level deltas and explicit operator decisions.
- `stack_priors.yaml` records every source file that can affect generated serving truth.
- q_scorer and seeding rewards consume live priors from stack priors and expose fallback provenance.
- Launch/preflight validation covers endpoint, port, tier, slots, NUMA, model path, binary, KV, mmproj, and acceleration flags.
- Simulated data-only swaps prove that model-stack changes update generated consumers without production-code edits.
- Production hardcoded-surface findings are zero except documented, expiring exceptions.
- Current operator/system-card stack summaries are generated from stack priors or runtime attestation, not hand-written live tables.

## Risks

- Overengineering risk: do not build a second registry. Extend descriptors, stack priors, and the existing guard/pipeline.
- False-positive risk: docs/tests contain valuable historical and retired-role coverage. Classify them; do not blindly delete them.
- Silent fallback risk: degraded constants are useful for offline tests, but unsafe when they masquerade as live deployment truth.
- Partial strictness risk: `--allow-known-gaps` is useful during construction, but if it becomes the normal promotion path the pipeline will keep missing exactly the class of stale constants that triggered this handoff.
