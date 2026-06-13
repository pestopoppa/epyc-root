# Model Stack Update Pipeline Audit Draft

**Status**: DRAFT - sidecar audit only
**Created**: 2026-06-13
**Scope**: Documentation/audit only. No inference, no orchestrator code edits, no index edits, no progress-log edits, no process restarts.
**Primary follow-up**: Main long-horizon workflow should review, merge useful findings into the active stack-change governance handoffs, then implement in `epyc-orchestrator`.
**Related**: `standardized-stack-update-pipeline-finalization.md`, `stack-change-governance-pipeline.md`, `routing-and-optimization-index.md`

## Audit Method

Read current root handoffs and orchestrator implementation surfaces:

- `/mnt/raid0/llm/epyc-root/handoffs/active/standardized-stack-update-pipeline-finalization.md`
- `/mnt/raid0/llm/epyc-root/handoffs/active/stack-change-governance-pipeline.md`
- `/mnt/raid0/llm/epyc-root/handoffs/active/routing-and-optimization-index.md`
- `/mnt/raid0/llm/epyc-orchestrator/scripts/registry/stack_change_pipeline.py`
- `/mnt/raid0/llm/epyc-orchestrator/scripts/validate/stack_change_guard.py`
- `/mnt/raid0/llm/epyc-orchestrator/orchestration/derived/stack_priors.yaml`
- Nearby implementation/tests/docs found with `rg --files | rg 'stack_change|stack_priors|descriptor|stack-truth|model_server_coverage|q_scorer|seeding_rewards'`.

Root local-instruction checks before editing:

- `cd /mnt/raid0/llm/epyc-root && gitnexus status` reported the root index up to date at current/indexed commit `d804af0`.
- `gitnexus impact handoffs/active/model-stack-update-pipeline-audit-draft.md --direction upstream --repo epyc-root` reported `Target ... not found`, `impactedCount: 0`, `risk: UNKNOWN`, because this draft did not exist yet. Treat as low practical risk but not graph-certified.

Current validation observations from `/mnt/raid0/llm/epyc-orchestrator`:

- `uv run python scripts/registry/stack_change_pipeline.py check --allow-known-gaps` exits 1 because `orchestration/model_descriptors.yaml` is stale or missing relative to generated compiler output; `stack_priors` and procedure enums are fresh; guard phases report known-gap warnings.
- `uv run python scripts/validate/stack_change_guard.py` exits 0 with `WARN: 23 stack-prior warning(s)`.
- `uv run python scripts/validate/stack_change_guard.py --all-hardcoded-surfaces` exits 0 with `WARN: 109 stack-prior warning(s)`.
- `uv run python scripts/validate/stack_change_guard.py --strict` exits 1 with `FAIL: 22 stack-prior error(s)`, all promoted known-gap warnings.

## Current Single Sources Of Truth

1. **Live serving/deployment intent**
   - Source: `/mnt/raid0/llm/epyc-orchestrator/orchestration/model_registry.yaml` `server_mode.*`.
   - Evidence: `/mnt/raid0/llm/epyc-orchestrator/docs/reference/stack-truth-precedence.md` says live serving topology owns endpoint, port, server role, tier, shared binding, launch binary, acceleration launch knobs, and memory residency for deployed roles.
   - Caveat: the same precedence doc also includes `/mnt/raid0/llm/epyc-orchestrator/scripts/server/stack_manifest.py` `ROLE_LAUNCH_META` and computed server classification in the live topology layer, so `server_mode.*` is not yet the only live serving input.

2. **Physical model identity and evidence**
   - Source: `/mnt/raid0/llm/epyc-orchestrator/orchestration/model_descriptors.yaml`.
   - Compiler: `/mnt/raid0/llm/epyc-orchestrator/src/registry/model_descriptors.py`, wrapped by `/mnt/raid0/llm/epyc-orchestrator/scripts/registry/compile_descriptors.py`.
   - Evidence: `stack-truth-precedence.md` says descriptors own physical model identity, role bindings, suite vectors, speed evidence, acceleration compatibility, modality, context, and known gaps.
   - Current blocker: `stack_change_pipeline.py check --allow-known-gaps` reports the descriptor artifact is stale.

3. **Generated consumer contract**
   - Source: `/mnt/raid0/llm/epyc-orchestrator/orchestration/derived/stack_priors.yaml`.
   - Compiler/API: `/mnt/raid0/llm/epyc-orchestrator/src/registry/stack_priors.py`, wrapped by `/mnt/raid0/llm/epyc-orchestrator/scripts/registry/compile_stack_priors.py`.
   - Evidence: `stack_priors.yaml` declares `stack_priors_version: 1`, `contract.schema: epyc.stack_priors`, `status: compiled_with_gaps`, `coverage_scope: descriptor_role_bindings`, source hashes for registry/descriptors, and required role/serving/prior fields.
   - Current state: pipeline check reports `stack_priors: ok` and procedure enums ok, but the artifact still has role/global known gaps.

4. **Procedure role choices**
   - Sources generated/checkable from stack priors:
     - `/mnt/raid0/llm/epyc-orchestrator/orchestration/procedures/add_model_to_registry.yaml`
     - `/mnt/raid0/llm/epyc-orchestrator/orchestration/procedure.schema.json`
   - Generator/check: `/mnt/raid0/llm/epyc-orchestrator/scripts/registry/sync_procedure_role_enums.py`.
   - Evidence: `stack_change_pipeline.py` calls `sync_procedure_role_enums(...)`; `tests/unit/test_stack_change_pipeline.py` verifies check/update behavior and stale procedure enum failure.

5. **Hardcoded-surface exception metadata**
   - Source: `/mnt/raid0/llm/epyc-orchestrator/orchestration/stack_change_guard_exceptions.yaml`.
   - Guard: `/mnt/raid0/llm/epyc-orchestrator/scripts/validate/stack_change_guard.py`.
   - Evidence: current guard warnings show a waived production blocker for `/mnt/raid0/llm/epyc-orchestrator/src/roles.py:118` `ARCHITECT_CODING = "architect_coding"` with expiry `2026-07-31`.

## Hardcoded Or Stale Model-Specific Surfaces To Eliminate

These are not all necessarily wrong today; they are surfaces that can drift after stack changes and should be generated, guarded, or explicitly classified.

- **Launch port and role maps**
  - Evidence: `/mnt/raid0/llm/epyc-orchestrator/scripts/server/stack_manifest.py:27-32` still has `PORT_MAP`, including `coder_escalation: 8071`, while `stack_priors.yaml` resolves `coder_escalation` serving endpoint to `http://localhost:8070` and ports `[8070, 8080, 8180, 8280, 8380]`.
  - Evidence: `stack_manifest.py` still owns `ROLE_LAUNCH_META`, `HOT_ROLES`, `WARM_ROLES`, `SERIAL_ROLES`, and computed server lists; the guard does not currently compare all of those values against `stack_priors.yaml`.

- **Vision model/projector launch metadata**
  - Evidence: `/mnt/raid0/llm/epyc-orchestrator/scripts/server/stack_manifest.py:211-224` defines `VISION_WORKER_MODEL`, `VISION_WORKER_MMPROJ`, `VISION_ESCALATION_MODEL`, and `VISION_ESCALATION_MMPROJ`.
  - Evidence: `stack_priors.yaml` records `vision_escalation` known gap `mmproj path is not represented in a descriptor-native field yet`; `orchestration/model_descriptors.yaml` has the same gap for vision descriptors.

- **Context, KV, and launch-effective capacity**
  - Evidence: `rg -n "ctx_max: null" orchestration/derived/stack_priors.yaml orchestration/model_descriptors.yaml` finds null context on every current generated role record inspected.
  - Evidence: `stack_priors.yaml` has gaps such as `ctx_max is not structured in the lean registry`, `ctx_max and KV quantization are not structured in the lean registry`, and `ctx_max and prefill metrics must be compiled from artifacts`.
  - Risk: context-sensitive routing, compaction, admission, launch, and benchmark interpretation cannot reliably gate on null fields.

- **Worker-family shared-runtime conflicts**
  - Evidence: `stack_priors.yaml` records `worker_general`, `worker_math`, and `toolrunner` conflicts: the worker server is shared while role records declare different models or no dedicated `server_mode` entry.
  - Evidence: `/mnt/raid0/llm/epyc-orchestrator/orchestration/model_registry.yaml:416` records `shared_with: [worker_math, toolrunner]`; `stack_priors.yaml` keeps `toolrunner`/`worker_math` as `server_mode.shared_with` with unresolved role-server conflict gaps.

- **Retired role compatibility surfaces**
  - Evidence: `/mnt/raid0/llm/epyc-orchestrator/src/roles.py:118` retains `ARCHITECT_CODING = "architect_coding"` under an expiring exception.
  - Evidence: `stack_change_guard.py --all-hardcoded-surfaces` reports many legacy-test and historical-doc hits for `architect_coding`; some are legitimate negative assertions, but the guard currently uses broad warnings rather than a structured "retired-role coverage" classification per test.

- **Tool/executor permission role tables**
  - Evidence: `/mnt/raid0/llm/epyc-orchestrator/orchestration/tools/executor.py:156-162` hardcodes role-to-tool categories for `coder_escalation`, `worker_math`, `toolrunner`, and others.
  - Uncertainty: this may be policy rather than model-specific quantity. It should be audited separately, because stack changes that rename/retire roles can stale this table even if permissions are not generated from stack priors.

- **Feature-flag metadata for removed topology**
  - Evidence: `/mnt/raid0/llm/epyc-orchestrator/src/features.py:176` and `:458` still define `langgraph_architect_coding`.
  - Uncertainty: the current guard has a `retired_role_env_flag` rule only for `scripts/server/*.py`, not feature metadata. Main workflow should decide whether this is historical compatibility, dead flag cleanup, or a guard gap.

- **Operator docs/current-stack diagrams**
  - Evidence: `stack_change_guard.py --all-hardcoded-surfaces` reports historical-doc warnings in `docs/ARCHITECTURE.md`, `docs/chapters/04-production-server-stack.md`, `docs/diagrams/orchestration_topology.md`, and other docs.
  - Desired owner: generated current summaries from `stack_priors.yaml` plus runtime attestation; historical docs should be explicitly labeled.

## Pipeline And Check Gaps

- **Descriptor staleness currently blocks the canonical command.**
  - Evidence: `stack_change_pipeline.py check --allow-known-gaps` returns nonzero with descriptor staleness even though `stack_priors` and procedure enums are ok.
  - Gap: the pipeline prints `run: ... update`, but update is dangerous until descriptor-removal and curated evidence policy decisions are explicit. Existing fail-closed removal protection is good; the operator workflow still needs "what decision is required now?" output.

- **Strict mode is not promotable yet.**
  - Evidence: `stack_change_guard.py --strict` fails with 22 strict errors, all known gaps in roles and `known_global_gaps`.
  - Gap: strict mode treats every known gap equally. It does not distinguish launch-blocking gaps from acceptable benchmark/candidate gaps, historical gaps, or scoped expiring exceptions.

- **Hardcoded surface scanning is curated and narrow by design.**
  - Evidence: `HARDCODED_SURFACE_RULES` in `stack_change_guard.py` covers retired `architect_coding`, stale procedure enums, bilinear model specs, seeding baseline TPS, and legacy CLI port probes. It does not cover `PORT_MAP` vs generated serving records, vision mmproj constants, `ROLE_LAUNCH_META` agreement, `src/features.py`, or `orchestration/tools/executor.py`.
  - Gap: a stack swap could still pass current guard while leaving model-specific launch/permission/feature metadata stale.

- **Launch validation is advisory rather than generated-contract first.**
  - Evidence: `stack_manifest.py` contains cross-check helpers for registry agreement, and `stack_commands.py` has a `--compile-descriptors` path, but the finalization handoff states launch/start integration is still open.
  - Gap: pre-launch should fail closed on stale descriptors/priors or unresolved strict-eligible gaps, with diagnostic override only.

- **No full simulated data-only stack-change fixture yet.**
  - Evidence: `tests/unit/test_stack_change_pipeline.py` covers update/check, stale artifact detection, descriptor model-removal refusal, and procedure enum drift. `tests/unit/test_stack_priors_compiler.py` covers shared frontdoor/coder memory, model-role server binding, conflicts-as-gaps, stack_manifest fallback, and missing descriptor refusal.
  - Gap: tests do not yet prove that realistic role swaps, retirement, worker shared-runtime changes, or vision/mmproj changes regenerate all consumer outputs with zero production-code edits.

- **Measurement status is still too textual.**
  - Evidence: `stack_priors.yaml` `evidence.speed`/`evidence.quality` entries carry dates/protocol strings inconsistently; some `toolrunner` and `worker_math` records have `date: null` and registry-carried protocols.
  - Gap: decision-grade vs observation vs stale measurement status is not encoded in a uniform schema aligned with `/workspace/MEASUREMENT.md`.

## Proposed Reliable Update Workflow

The main workflow should keep one canonical no-inference command but make its output actionable enough for operators:

```bash
cd /mnt/raid0/llm/epyc-orchestrator
uv run python scripts/registry/stack_change_pipeline.py check
uv run python scripts/registry/stack_change_pipeline.py update
uv run python scripts/registry/stack_change_pipeline.py check --allow-known-gaps
```

Proposed phases:

1. **Classify the stack change before edits**
   - Role model swap, role retirement, shared-server consolidation, port/slot change, context/KV change, acceleration/MTP/spec change, vision/mmproj change, benchmark-only candidate addition, or documentation-only correction.

2. **Edit structured sources only**
   - Live deployment: `/mnt/raid0/llm/epyc-orchestrator/orchestration/model_registry.yaml` `server_mode.*`.
   - Physical model/evidence: descriptor compiler inputs and `/mnt/raid0/llm/epyc-orchestrator/orchestration/model_descriptors.yaml`.
   - Research evidence only: `/mnt/raid0/llm/epyc-inference-research/orchestration/model_registry.yaml`.
   - Transitional launcher metadata: `/mnt/raid0/llm/epyc-orchestrator/scripts/server/stack_manifest.py` only for fields not yet generated.

3. **Regenerate only generated artifacts**
   - Descriptors, stack priors, procedure role enums, and eventually generated operator stack summaries.
   - Never hand-edit `/mnt/raid0/llm/epyc-orchestrator/orchestration/derived/stack_priors.yaml`.

4. **Run guard tiers**
   - Loose guard for freshness and contract shape.
   - All-surface guard for docs/tests/legacy visibility.
   - Strict or strict-eligible guard once live-consumer gaps are classified.

5. **Run simulated stack-change tests**
   - Shared frontdoor/coder model consolidation.
   - Retired role removal and compatibility alias.
   - Worker shared runtime with role aliases.
   - Vision/mmproj descriptor projection.
   - Context/KV launch-effective fields.

6. **Pre-launch attestation**
   - Compare generated serving records to launch manifest, `PORT_MAP`, NUMA config, ports, binary paths, model paths, mmproj paths, and acceleration flags.
   - Compare running processes to current source mtimes before declaring a deployed fix. Do not restart here without operator approval.

7. **Document the result**
   - Main workflow should update the owning handoff/index/progress after review. This sidecar draft intentionally does not edit those files.

## Verification Commands

No-inference checks that should be part of the standardized pipeline:

```bash
cd /mnt/raid0/llm/epyc-orchestrator

python3 -m py_compile \
  src/registry/model_descriptors.py \
  src/registry/stack_priors.py \
  scripts/registry/compile_descriptors.py \
  scripts/registry/compile_stack_priors.py \
  scripts/registry/sync_procedure_role_enums.py \
  scripts/registry/stack_change_pipeline.py \
  scripts/validate/stack_change_guard.py

uv run python scripts/registry/stack_change_pipeline.py check
uv run python scripts/registry/stack_change_pipeline.py check --allow-known-gaps
uv run python scripts/registry/compile_descriptors.py --dry-run --allow-incomplete
uv run python scripts/registry/compile_stack_priors.py --allow-incomplete
python3 scripts/registry/sync_procedure_role_enums.py --check
uv run python scripts/validate/stack_change_guard.py
uv run python scripts/validate/stack_change_guard.py --all-hardcoded-surfaces
uv run python scripts/validate/stack_change_guard.py --strict

uv run --with pytest pytest -q \
  tests/unit/test_stack_change_pipeline.py \
  tests/unit/test_stack_change_guard.py \
  tests/unit/test_sync_procedure_role_enums.py \
  tests/unit/test_stack_priors_compiler.py \
  tests/unit/test_model_descriptors_schema.py \
  tests/unit/test_model_descriptor_compiler.py \
  tests/unit/test_q_scorer.py \
  tests/unit/test_seeding_rewards.py \
  tests/unit/test_model_server_coverage.py
```

Additional audit commands useful during implementation:

```bash
cd /mnt/raid0/llm/epyc-orchestrator
rg -n "PORT_MAP|ROLE_LAUNCH_META|VISION_.*MMPROJ|ctx_max: null|quality_overall: null|Role-server conflict|architect_coding|DEFAULT_BASELINE_TPS|model_specs" \
  scripts src orchestration tests docs

rg -n "ctx_max: null|mmproj path is not represented|Role-server conflict|quality_overall: null|known_global_gaps" \
  orchestration/model_descriptors.yaml orchestration/derived/stack_priors.yaml
```

## Prioritized Implementation Tasks

- [ ] **P0 - Resolve descriptor freshness and classify descriptor drift.**
  - Evidence: `stack_change_pipeline.py check --allow-known-gaps` currently fails at `descriptors: stale`.
  - Implement: make pipeline output name the exact descriptor deltas and coverage decision required before `update`, especially for curated evidence/schema drift.
  - Targets: `src/registry/model_descriptors.py`, `scripts/registry/compile_descriptors.py`, `orchestration/model_descriptors.yaml`, `tests/unit/test_model_descriptor_compiler.py`, `tests/unit/test_model_descriptors_schema.py`, `tests/unit/test_stack_change_pipeline.py`.

- [ ] **P1 - Split strict known gaps by launch-blocking severity.**
  - Evidence: `stack_change_guard.py --strict` fails with 22 known-gap errors but does not rank live launch blockers vs candidate/historical gaps.
  - Implement: add categories such as `launch_blocking`, `live_consumer_blocking`, `measurement_observation`, `candidate_only`, and `waived_until`.
  - Targets: `src/registry/stack_priors.py`, `scripts/validate/stack_change_guard.py`, `orchestration/stack_change_guard_exceptions.yaml`, `tests/unit/test_stack_change_guard.py`.

- [ ] **P2 - Generate or validate launcher serving projection from stack priors.**
  - Evidence: `stack_manifest.py` `PORT_MAP["coder_escalation"] = 8071` conflicts with generated `coder_escalation` endpoint `http://localhost:8070`.
  - Implement: compare `PORT_MAP`, `ROLE_LAUNCH_META`, `NUMA_CONFIG`, model paths, binary dirs, slot counts, and shared aliases against generated serving records; fail when production launch surfaces disagree.
  - Targets: `scripts/server/stack_manifest.py`, `scripts/server/stack_numa.py`, `scripts/server/stack_commands.py`, `scripts/server/orchestrator_stack.py`, `scripts/validate/stack_change_guard.py`, `tests/unit/test_model_server_coverage.py`, `tests/unit/test_stack_change_guard.py`.

- [ ] **P3 - Add descriptor-native context/KV/mmproj fields.**
  - Evidence: generated records carry `ctx_max: null`; vision records carry `mmproj path is not represented in a descriptor-native field yet`; worker records carry KV/context gaps.
  - Implement: add `ctx_model_max`, `ctx_launch_effective`, KV quant/cache fields, and vision projector fields with source/provenance.
  - Targets: `orchestration/model_registry.yaml`, `orchestration/model_descriptors.yaml`, `src/registry/model_descriptors.py`, `src/registry/stack_priors.py`, descriptor/stack-prior tests.

- [ ] **P4 - Resolve worker shared-runtime semantics.**
  - Evidence: `worker_general`, `worker_math`, and `toolrunner` share worker runtime surfaces but have conflicting role/model records.
  - Implement: decide whether these are aliases of one live runtime, independent logical roles on one server, or stale role descriptors; encode this explicitly in descriptors and generated priors.
  - Targets: `orchestration/model_registry.yaml`, `orchestration/model_descriptors.yaml`, `src/registry/stack_priors.py`, `tests/unit/test_stack_priors_compiler.py`.

- [ ] **P5 - Extend hardcoded-surface coverage beyond retired-role strings.**
  - Evidence: current `HARDCODED_SURFACE_RULES` misses `PORT_MAP`, mmproj constants, `src/features.py` retired topology flags, and `orchestration/tools/executor.py` role permission tables.
  - Implement: add targeted rules or generated comparison checks; avoid treating legitimate historical docs/tests as production blockers.
  - Targets: `scripts/validate/stack_change_guard.py`, `orchestration/stack_change_guard_exceptions.yaml`, guard tests.

- [ ] **P6 - Add full simulated data-only stack-change workflow fixtures.**
  - Evidence: current unit tests cover pieces, not an end-to-end realistic stack swap.
  - Implement: fixtures for shared frontdoor/coder swap, retired-role removal, worker shared-runtime change, and vision/mmproj update. Acceptance: generated descriptors/priors/enums update without production-code edits.
  - Targets: `tests/unit/test_stack_change_pipeline.py`, `tests/unit/test_stack_priors_compiler.py`, `tests/unit/test_stack_change_guard.py`, possible new `tests/unit/test_stack_change_workflow.py`.

- [ ] **P7 - Add measurement-status schema to generated priors.**
  - Evidence: some speed/quality records have `date: null` and textual protocols; `/workspace/MEASUREMENT.md` requires decision-gating numbers to cite metric, protocol-id, n/reps, date, and attestation ref.
  - Implement: encode `decision_grade`, `observation`, `stale`, or `missing` status for throughput/quality/context/memory evidence.
  - Targets: descriptor schema/compiler, stack-prior compiler, tests, and any q_scorer/seeding consumers that gate decisions.

- [ ] **P8 - Generate current operator-facing stack summaries.**
  - Evidence: all-surface guard reports historical-doc warnings in current stack docs and diagrams.
  - Implement: generate current summaries from `stack_priors.yaml` plus runtime attestation; label historical docs explicitly.
  - Targets: docs summary generator, `docs/chapters/04-production-server-stack.md`, `docs/diagrams/orchestration_topology.md`, AutoPilot system card generation.

## Open Questions / Uncertainty

- Whether `orchestration/tools/executor.py` role permission maps should be generated from stack priors or remain policy-owned static maps. They are role-specific and can drift on role rename/removal, but not all permissions are model-derived.
- Whether `src/features.py` `langgraph_architect_coding` should be deleted, converted to historical compatibility, or covered by an explicit guard exception. The current surface scan does not flag it.
- Whether `stack_manifest.py` should remain a transitional co-owner of launch truth or become a pure generated projection from `server_mode.*` plus descriptors.
- Whether `reap_25b_frontdoor` should stay in the live stack-prior artifact as `benchmark_or_candidate` or move to a separate candidate/evidence projection. It currently contributes known gaps but is not a live deployment role.
