# Standardized Stack Update Pipeline Finalization

**Status**: READY FOR MAIN IMPLEMENTATION
**Created**: 2026-06-13
**Priority**: HIGH - prevents stale model-specific constants from corrupting scoring, routing, launch, planner context, and benchmark interpretation after model assignment changes
**Scope**: Implementation-ready audit and handoff only. No inference, benchmarks, AutoPilot restart, server restart, or child-repo code changes were performed in this sidecar pass.
**Related**: [stack-change-governance-pipeline.md](stack-change-governance-pipeline.md), [model-stack-update-pipeline-audit.md](model-stack-update-pipeline-audit.md), [model-stack-change-standardization-audit.md](model-stack-change-standardization-audit.md), [model-capability-descriptors.md](model-capability-descriptors.md), [routing-truth-restoration.md](routing-truth-restoration.md), [fable5-findings-01-measurement-and-integrity.md](fable5-findings-01-measurement-and-integrity.md)

## Purpose

This handoff consolidates the current stack-change-governance work into a final implementation plan for a standardized, reliable update pipeline whenever orchestration model assignments, serving topology, or model details change.

The recurring failure mode is clear: live stack changes have left stale role/model quantities in q_scorer costs, seeding reward priors, routing defaults, launch maps, graph nodes, docs, and tests. The project now has the right foundation, but strict launch gating is still blocked by descriptor gaps and a few remaining hardcoded surfaces.

Treat this file as a pickup bridge for the main workflow. Do not start a competing registry or a second guard system; finish and wire the existing stack-prior contract.

Main-agent observation to fold into implementation: the pipeline is real but fragmented. The repo has descriptor compile, stack-prior compile, procedure-enum sync, guard validation, and a launcher-side `start --compile-descriptors` hook, but there is not yet one canonical operator command that says "after a stack change, run this". The highest-value deliverable is therefore a single stack-change procedure with check mode, update mode, stale-surface reporting, and promotion/launch acceptance gates.

## Current State Snapshot

Read-only audit and lightweight validation on 2026-06-13 found:

- Existing implementation track: `handoffs/active/stack-change-governance-pipeline.md`.
- Existing detailed audit: `handoffs/active/model-stack-update-pipeline-audit.md`.
- Existing concise implementation bridge: `handoffs/active/model-stack-change-standardization-audit.md`.
- Generated contract: `/mnt/raid0/llm/epyc-orchestrator/orchestration/derived/stack_priors.yaml`.
- Current contract status: `compiled_with_gaps`.
- Loose guard result: `uv run python scripts/validate/stack_change_guard.py` exits 0 with `WARN: 23 stack-prior warning(s)`.
- All-surface guard result: `uv run python scripts/validate/stack_change_guard.py --all-hardcoded-surfaces` exits 0 with `WARN: 109 stack-prior warning(s)`.
- Strict guard result: `uv run python scripts/validate/stack_change_guard.py --strict` exits 1 with 22 strict errors, all from known role/global gaps; the retained `Role.ARCHITECT_CODING` compatibility enum is waived by expiring exception metadata.
- Procedure role enum check: `python3 scripts/registry/sync_procedure_role_enums.py --check` exits 0.
- Command skeleton landing: `epyc-orchestrator` `e01d64d` adds `scripts/registry/stack_change_pipeline.py` plus `tests/unit/test_stack_change_pipeline.py`; follow-up `fe4b2aa` fixes temp preview procedure/schema paths and default stack-prior role scoping.
- Live read-only result after `fe4b2aa`: `uv run python scripts/registry/stack_change_pipeline.py check --allow-known-gaps` exits 1 because `orchestration/model_descriptors.yaml` is semantically stale relative to compiler output. Stack priors and procedure enums are fresh; strict known gaps are reported as warnings under the compatibility flag.

## Prior Pipeline Work Found

The standardized-pipeline foundation already exists in `epyc-orchestrator`:

| Artifact | Role in pipeline | Current status |
|---|---|---|
| `docs/reference/stack-truth-precedence.md` | Declares source precedence: live serving topology first, descriptors second, role metadata third, historical evidence last. | Present; use as governance contract. |
| `orchestration/model_registry.yaml` | Lean live deployment truth for `server_mode.*`, ports, slots, tiers, shared bindings, role metadata, and runtime defaults. | Source of live serving truth, but still contains older role/prose fields that can drift. |
| `orchestration/model_descriptors.yaml` | Physical model/evidence layer keyed by model identity, not role. | Present but compiled with gaps for context, KV, some quality/TPS, role-server conflicts, and vision mmproj metadata. |
| `src/registry/model_descriptors.py` and `scripts/registry/compile_descriptors.py` | Descriptor compiler and CLI wrapper. | Present; needs stricter completeness policy and richer structured fields. |
| `src/registry/stack_priors.py` and `scripts/registry/compile_stack_priors.py` | Generates the single consumer contract from lean registry, descriptors, and stack manifest. | Present; current contract version 1; still `compiled_with_gaps`. |
| `orchestration/derived/stack_priors.yaml` | Generated consumer surface for role -> model, serving, priors, acceleration, evidence, known gaps. | Current no-inference contract; should become the source all consumers read. |
| `scripts/validate/stack_change_guard.py` | Validates freshness, contract shape, live-role invariants, procedure enum drift, hardcoded surfaces, and exceptions. | Loose mode useful; strict mode blocked by known gaps. |
| `orchestration/stack_change_guard_exceptions.yaml` | Expiring metadata for hardcoded-surface exceptions. | Present; currently only waives `src/roles.py:118` for compatibility until 2026-07-31. |
| `scripts/registry/sync_procedure_role_enums.py` | Generates/checks procedure role choices from stack priors. | Green on 2026-06-13. |
| `scripts/server/orchestrator_stack.py start --compile-descriptors` | Launcher-side descriptor compile hook. | Exists, but does not replace a full canonical post-stack-change pipeline. |

Recently completed main-track work also matters:

- Retired active `architect_coding` graph node removed from active PydanticGraph/LangGraph topology.
- `Role.ARCHITECT_CODING` retained only as an expiring compatibility enum alias.
- `stack_priors.yaml` metadata refreshed.
- Descriptor quality priors added for `architect_general`, `ingest_long_context`, `worker_vision`, `vision_escalation`, and `toolrunner`.
- q_scorer live defaults now load generated stack priors first, keeping fallback tables only for degraded/offline mode.
- Seeding reward TPS/cost priors and several benchmark/config/routing surfaces have migrated to stack-prior discovery.

## Hardcoded And Derived Surface Inventory

These are the current surfaces that must stay synchronized whenever model roles, assignments, serving details, or model capabilities change.

| Surface | Current location | Desired owner | Required guard/generation |
|---|---|---|---|
| Live role -> server, endpoint, ports, slots, tier, shared mmap | `orchestration/model_registry.yaml` `server_mode.*`; transitional witness in `scripts/server/stack_manifest.py` | `server_mode.*`, then generated `stack_priors.yaml` | Guard direct consumers of stale raw maps such as `PORT_MAP`; launch/status should read generated serving records or validated launch metadata. |
| Role -> model identity | `model_descriptors.yaml`, lean/research registries | Descriptors keyed by physical model id | Compile from structured registry evidence; fail on role-keyed/manual consumer model tables. |
| q_scorer TPS, quality, memory costs | `orchestration/repl_memory/q_scorer.py` | `stack_priors.yaml` `priors.*` | Already migrated for live defaults; add provenance for `stack_priors` vs override vs degraded fallback. |
| Seeding reward TPS/cost priors | `scripts/benchmark/seeding_rewards.py` and related seeding files | `stack_priors.yaml` | Mostly migrated; guard future live local tables. |
| Throughput/TPS and latency evidence | `server_mode.throughput`, descriptor speed blocks, benchmark artifacts, historical comments | Measurement-attested descriptor fields projected into stack priors | Add decision-grade/observation/stale status per `MEASUREMENT.md`; strict consumers must not use unproven values silently. |
| Quality priors | Descriptor `quality.suite_vector`, generated stack priors | Descriptor evidence from lean/research registries and artifacts | Continue filling structured evidence; preserve gaps rather than inventing priors. |
| Context limits | Scattered `ctx_max`, `context_length`, `max_context`, launch `-c`/`n_ctx`, research registry | Descriptor `ctx_model_max` plus serving `ctx_launch_effective` projected to stack priors | Add fields and guard null live values where routing/compaction/budget consumers need them. |
| KV/cache settings | `server_mode.kv_quant`, descriptor acceleration `kv`, launcher args, model comments | Descriptor/serving structured fields | Compile `kv.k`, `kv.v`, cache sizing, slot/KV implications; guard consumers reading comments. |
| Server launch args and binary family | `scripts/server/stack_manifest.py`, `stack_numa.py`, `stack_commands.py`, `orchestrator_stack.py`, `server_mode.runtime_requirements` | Generated launch requirements from stack priors or a validated launch projection | Add compile/check for binary path, ik-llama requirements, MTP/spec knobs, mmproj paths, and stale running process attestation. |
| Vision/mmproj metadata | `stack_manifest.py` `VISION_*`, registry role records, `src/vision/models.py`, `chat_pipeline/vision_stage.py` | Descriptor-native model + mmproj fields projected into serving records | Current descriptors note mmproj is not native; add fields before strict mode. |
| Role aliases and retired compatibility | `src/roles.py`, tests, historical docs, graph aliases | Live roles from stack priors; compatibility exceptions only when documented | Keep `Role.ARCHITECT_CODING` exception expiring 2026-07-31; audit/remove before expiry. |
| Graph nodes and routing topology | `src/graph/**`, `src/api/routes/chat_pipeline/**`, `src/api/routes/chat_routing.py` | Live role set and generated role classifications | Retired active node is removed; keep guard coverage for recurrence. |
| Admission/runtime policy tables | `src/api/admission.py`, `src/runtime/inference_lock.py`, `src/runtime/inference_tap.py`, dashboard routes | Stack-prior serving/tier/slot records plus explicit policy hints | Migrate remaining local high-cost/lock/tap classifications or label as generated policy projection. |
| API/config model maps | `src/config/models.py`, `src/api/routes/openai_compat.py`, CLI/status probes | Stack-prior live roles and serving records | Recent cleanup removed retired active maps; finish replacing parallel static maps where practical. |
| Procedure role enums | `orchestration/procedure.schema.json`, `orchestration/procedures/add_model_to_registry.yaml` | Generated from stack priors | Already guarded; keep in stack-change workflow. |
| Operator docs, system cards, dashboards | `docs/**`, dashboard snapshot/routes, AutoPilot system-card code | Generated summaries from stack priors plus running-state attestation | Manual docs can remain historical only if labeled; current stack summaries should be generated. |
| Research registry and benchmark artifacts | `/mnt/raid0/llm/epyc-inference-research/orchestration/model_registry.yaml`, `benchmarks/results/**` | Evidence/candidate history only | Never let research rows become live deployment truth without descriptor projection and measurement status. |

Highest-risk live stale-value hazards today:

1. `scripts/server/stack_manifest.py` still has raw `PORT_MAP["coder_escalation"] = 8071` while stack priors resolve `coder_escalation` to the shared frontdoor endpoint `http://localhost:8070`.
2. `ctx_max` is null for many live roles in descriptors and stack priors, while context-sensitive routing/compaction/launch decisions need both model max context and effective launch context.
3. Vision descriptors currently lack descriptor-native `mmproj` fields even though server launch and VL request handling depend on model/projector pairs.
4. Worker-family role-server conflicts remain explicit gaps: `worker_general`, `worker_math`, and `toolrunner` share runtime but role records can describe different models.
5. Strict launch gating cannot be enabled until known gaps are resolved or classified with scoped, expiring exceptions.

## Source-Of-Truth Contract

Use this contract for future stack/model changes:

1. **Live serving truth** lives in `epyc-orchestrator/orchestration/model_registry.yaml` `server_mode.*`.
   - Includes role -> endpoint, port, slot count, tier, shared server bindings, and runtime deployment intent.
   - `server_mode` outranks older `roles.*`, `process_layout.*`, comments, docs, and research records.

2. **Physical model truth and evidence** live in `orchestration/model_descriptors.yaml`.
   - Descriptors are keyed by model identity, not role.
   - They carry modality, architecture, quant, memory, context, acceleration, quality/speed evidence, KV/cache, and known gaps.

3. **Research registry** is comprehensive evidence and candidate history only.
   - `/mnt/raid0/llm/epyc-inference-research/orchestration/model_registry.yaml` can feed descriptors, but it is not live deployment truth.
   - Decision-gating numbers must obey `MEASUREMENT.md`: metric, protocol id, n/reps, date, and attestation ref.

4. **Generated consumer contract** is `orchestration/derived/stack_priors.yaml`.
   - Consumers should use typed helpers from `src/registry/stack_priors.py` or small role-specific wrappers.
   - Direct YAML parsing is acceptable only for scripts/tests that cannot import production modules; those paths still need degraded-mode warnings.

5. **Fallback constants are degraded mode only.**
   - Names should say `FALLBACK_*` or `DEGRADED_*`.
   - They must not silently satisfy live stack decisions when stack priors are present.
   - They must exclude retired live roles unless testing historical compatibility.

## Future Stack-Change Process

For any model assignment/detail change, run this no-inference process before any launch or AutoPilot resume. Implementation should expose it as a canonical command/procedure rather than asking operators to remember five scattered scripts.

Proposed command shape:

```bash
cd /mnt/raid0/llm/epyc-orchestrator
uv run python scripts/registry/stack_change_pipeline.py check
uv run python scripts/registry/stack_change_pipeline.py update
```

`check` mode should be read-only and fail nonzero when generated artifacts are stale, procedure enums drift, strict-eligible gaps remain, or hardcoded production blockers are unwaived. It should print exact remediation commands and current guard counts.

`update` mode should write only generated artifacts from structured sources: descriptors, stack priors, procedure role enums, and generated operator summaries once those exist. It should never invent missing model facts, edit historical records, or silently classify hardcoded surfaces. Any remaining gaps must be reported with owner/category/expiry instructions.

Minimal pipeline phases:

- compile/check descriptors
- compile/check stack priors
- sync/check procedure role enums
- run stack-change guard in loose, all-surface, and strict/strict-eligible modes
- run no-inference simulated stack-change tests
- report stale hardcoded surfaces grouped as production blocker, waived exception, legacy test, and historical doc
- emit a concise acceptance summary for launch/autopilot decisions

1. Classify the change.
   - Role model swap, role retirement, shared-server consolidation, tier/hotness change, port/slot change, context change, acceleration/MTP/spec change, KV/cache change, vision/mmproj change, or benchmark-only candidate addition.

2. Edit only structured inputs.
   - `epyc-orchestrator/orchestration/model_registry.yaml` `server_mode.*` for live deployment.
   - `epyc-orchestrator/orchestration/model_descriptors.yaml` or its compiler inputs for model/evidence facts.
   - `epyc-inference-research/orchestration/model_registry.yaml` only for research/candidate evidence.
   - `scripts/server/stack_manifest.py` only where launcher metadata still lacks generated ownership.

3. Compile and check generated surfaces.
   - Compile descriptors.
   - Compile stack priors.
   - Sync procedure role enums.
   - Generate/update operator stack summaries from priors when they exist.

4. Run validation gates.
   - Loose guard: source hash, contract shape, live invariants.
   - All-surface guard: production blockers plus legacy tests and historical docs.
   - Strict guard: only after current known gaps are resolved/classified.
   - Focused tests for stack priors, descriptors, q_scorer, guard, admission, launch manifest, config/API maps, and any touched consumer.

5. Run stale-value detection.
   - Search for retired roles and old model IDs in `src/`, `scripts/`, `orchestration/`, `tests/`, `docs/`.
   - Compare direct launch maps against generated serving records.
   - Compare running PIDs/ports/flags/binaries against generated priors before declaring the stack deployed.
   - If a process predates the code/config change, treat it as stale and restart only in an operator-approved deployment window.

6. Record evidence and rollback semantics.
   - Every generated artifact records source hashes and commits.
   - Any derived value records source, precedence, measurement status, and known gaps.
   - Rollback means reverting structured source edits and regenerating descriptors/priors/enums, not hand-editing derived YAML.
   - Replay/historical datasets keep era labels so retired roles can remain in old records without becoming live priors.

7. Update docs and handoffs.
   - Update this handoff or `stack-change-governance-pipeline.md`.
   - Add a progress entry with commands and guard counts.
   - If an index row is not updated immediately, report the suggested row in the final response for the main workflow.

## Prioritized Implementation Tasks

- [ ] **P0 - Close strict-mode descriptor gaps required by live consumers.**
  - Add structured `ctx_model_max` and `ctx_launch_effective` fields.
  - Add descriptor-native vision `mmproj`/projector fields.
  - Add KV/cache settings and launch-effective context where missing.
  - Classify worker/toolrunner role-server conflicts as resolved shared-runtime projections or explicit gaps with owner/expiry.
  - Target files: `src/registry/model_descriptors.py`, `scripts/registry/compile_descriptors.py`, `orchestration/model_descriptors.yaml`, `src/registry/stack_priors.py`, `scripts/registry/compile_stack_priors.py`, `tests/unit/test_model_descriptor_compiler.py`, `tests/unit/test_model_descriptors_schema.py`, `tests/unit/test_stack_priors_compiler.py`.

- [ ] **P1 - Add the canonical stack-change command/procedure.**
  - **2026-06-13 partial**: `e01d64d` added the initial command skeleton and unit tests; `fe4b2aa` fixed preview-path and role-scope handling.
  - Build one no-inference operator entrypoint with `check` and `update` modes.
  - `check` mode must be safe for CI and local preflight: read-only, deterministic, and nonzero on stale generated artifacts, enum drift, unwaived production blockers, or strict-eligible gaps.
  - `update` mode must regenerate descriptors, stack priors, procedure enums, and any generated stack summaries from structured sources only.
  - The command output should include current loose/all-surface/strict guard counts, stale hardcoded-surface categories, source hashes, and next remediation commands.
  - Target files: new `scripts/registry/stack_change_pipeline.py` or equivalent Make/CLI target, `scripts/registry/compile_descriptors.py`, `scripts/registry/compile_stack_priors.py`, `scripts/registry/sync_procedure_role_enums.py`, `scripts/validate/stack_change_guard.py`, `scripts/server/orchestrator_stack.py`, `tests/unit/test_stack_change_guard.py`, new workflow tests if needed.

- [ ] **P2 - Make launch/serving projection consume the generated contract.**
  - Reconcile or retire stale raw `PORT_MAP` entries such as `coder_escalation: 8071`.
  - Add a guard that compares `PORT_MAP`, `ROLE_LAUNCH_META`, `NUMA_CONFIG`, and `server_mode` against generated serving records.
  - Ensure health/status/probe code reads stack-prior serving records or validated launch metadata.
  - Target files: `scripts/server/stack_manifest.py`, `scripts/server/stack_numa.py`, `scripts/server/stack_commands.py`, `scripts/server/orchestrator_stack.py`, `src/cli_orch.py`, `src/api/routes/dashboard_topology.py`, `tests/unit/test_model_server_coverage.py`, `tests/unit/test_stack_change_guard.py`, `tests/unit/test_build_server_command_helpers.py`.

- [ ] **P3 - Add simulated data-only stack-change CI fixtures.**
  - Fixture A: shared-mmap role swap where `frontdoor` and `coder_escalation` keep one model identity and one memory owner.
  - Fixture B: role retirement where `architect_coding` remains historical/compatibility-only and cannot appear in live priors.
  - Fixture C: worker-family shared runtime with launch-specific requirements such as gemma4 MTP / ik binary.
  - Acceptance: changing fixture registry/descriptor inputs regenerates consumer outputs with no production-code edits.
  - Target tests: `tests/unit/test_stack_priors_compiler.py`, `tests/unit/test_stack_change_guard.py`, `tests/unit/test_q_scorer.py`, new `tests/unit/test_stack_change_workflow.py` if needed.

- [ ] **P4 - Add provenance plumbing for live vs degraded consumer values.**
  - q_scorer should be able to expose whether values came from `stack_priors`, override, registry fallback, or degraded local fallback.
  - Seeding/replay reward paths should write cost-prior provenance when they use live priors vs replay overrides.
  - Target files: `orchestration/repl_memory/q_scorer.py`, `scripts/benchmark/seeding_rewards.py`, `scripts/benchmark/seeding_eval.py`, `tests/unit/test_q_scorer.py`, `tests/unit/test_seeding_rewards.py`.

- [ ] **P5 - Generate current operator-facing stack summaries.**
  - Replace manual current-stack tables in docs/system cards/dashboards with generated output from stack priors plus running-state attestation.
  - Keep historical docs only if labeled historical.
  - Target files: `docs/chapters/04-production-server-stack.md`, `docs/diagrams/orchestration_topology.md`, AutoPilot system-card generation, dashboard snapshot routes, and a new summary generator if needed.

- [ ] **P6 - Wire pre-launch and post-launch gates.**
  - Pre-launch: refuse production start when source hashes are stale or strict-eligible gaps remain unclassified, unless an explicit diagnostic override is present.
  - Post-launch: compare PIDs/ports/flags/binaries/model paths against generated priors and report stale running processes.
  - Do not restart AutoPilot as part of this handoff; AutoPilot is paused due to contaminated trials from `#786` onward.
  - Target files: `scripts/server/orchestrator_stack.py`, `scripts/server/stack_health.py`, `scripts/server/stack_runtime.py`, `scripts/session/health_check.sh`, related unit tests.

## Dependency Graph

```text
P0 descriptor/contract gaps
  -> P1 canonical check/update command
  -> P2 launch/serving projection
  -> P3 simulated data-only swaps
  -> P6 pre/post-launch gates

P0 descriptor/contract gaps
  -> P4 provenance plumbing
  -> P5 generated operator summaries

P3 simulated swaps
  -> strict guard promotion
  -> launch gate enforcement
```

P1 can begin immediately by composing existing scripts and preserving current gaps as failures/warnings. P2 can also begin before P0 is completely done for obvious stale maps such as `coder_escalation: 8071`, but strict launch enforcement should wait until P0 and P3 are green.

## Cross-Cutting Concerns

- **Measurement policy**: throughput, quality, context, and memory values used for decisions must carry source/protocol/date/status. Unknowns remain gaps; do not invent missing priors to make strict mode pass.
- **Historical replay**: retired roles and old model IDs can remain in replay datasets and historical docs only with era/legacy classification. They cannot leak into live priors.
- **Shared mmap accounting**: `frontdoor` and `coder_escalation` share the same physical Qwen3.6 server. Memory/cost accounting must not double-count them.
- **Vision stack**: VL roles require both text model and mmproj/projector metadata. Descriptors and launch/health validation must account for pairs, not only model GGUF paths.
- **Launcher truth**: stack manifest remains a transitional source. The end state should be a generated or validated launch projection so raw port/path maps cannot drift from stack priors.
- **AutoPilot**: do not restart AutoPilot while implementing this. Any post-launch attestation must be separated from the contaminated trial cleanup/resume workflow.

## Validation Commands

Use this baseline after each implementation pass:

```bash
cd /mnt/raid0/llm/epyc-orchestrator
python3 -m py_compile \
  src/registry/model_descriptors.py \
  src/registry/stack_priors.py \
  scripts/registry/compile_descriptors.py \
  scripts/registry/compile_stack_priors.py \
  scripts/registry/sync_procedure_role_enums.py \
  scripts/validate/stack_change_guard.py \
  orchestration/repl_memory/q_scorer.py \
  scripts/server/stack_manifest.py
uv run python scripts/registry/stack_change_pipeline.py check  # once implemented
uv run python scripts/registry/compile_descriptors.py --dry-run --allow-incomplete
uv run python scripts/registry/compile_stack_priors.py --allow-incomplete
python3 scripts/registry/sync_procedure_role_enums.py --check
uv run python scripts/validate/stack_change_guard.py
uv run python scripts/validate/stack_change_guard.py --all-hardcoded-surfaces
uv run python scripts/validate/stack_change_guard.py --strict
uv run --with pytest pytest -q \
  tests/unit/test_model_descriptor_compiler.py \
  tests/unit/test_model_descriptors_schema.py \
  tests/unit/test_stack_priors_compiler.py \
  tests/unit/test_stack_change_guard.py \
  tests/unit/test_q_scorer.py
git diff --check
```

Add launch/config/dashboard tests when touching those consumers.

## Acceptance Criteria

- A live model assignment or serving-topology change can be made by editing structured source files, running one canonical `check`/`update` stack-change command, and reviewing its acceptance summary; q_scorer, seeding rewards, routing/config, launch/status, and operator summaries update without hand-edited constants.
- The canonical command has read-only `check` mode and generated-artifact `update` mode. It runs descriptor compile/check, stack-prior compile/check, procedure enum sync/check, guard scans, stale hardcoded-surface reporting, and simulated no-inference stack-change tests.
- `uv run python scripts/validate/stack_change_guard.py --strict` passes or fails only on intentionally documented, expiring exceptions.
- `architect_coding` cannot appear in live priors, active graph topology, launch flags, status probes, q_scorer defaults, or routing defaults. Compatibility aliases remain only while explicitly waived and tested.
- Shared-server roles do not double-count memory or drift to dead ports; `frontdoor` and `coder_escalation` agree on model id, endpoint, mmap ownership, and scorer costs.
- Live context, KV/cache, mmproj, launch binary, and acceleration requirements are structured, generated, and guarded.
- Pre-launch and post-launch checks detect stale generated artifacts and stale running processes before AutoPilot or production traffic can rely on them.

## Main Workflow Pickup

1. **DONE 2026-06-13 (`e01d64d`, `fe4b2aa`) - Create the canonical stack-change command skeleton.** `scripts/registry/stack_change_pipeline.py` now composes the existing descriptor compiler, stack-prior compiler, enum sync, and guard into read-only `check` and generated-artifact `update` modes.
2. **Resolve the descriptor/compiler drift reported by the new command.** A temp preview showed that regenerating descriptors as-is would discard curated evidence and candidate-role coverage, so do not run `update` in place until the compiler can preserve or structurally derive that evidence. Target: make `check --allow-known-gaps` pass except for intentional strict warnings.
3. **Start P0 context/vision/KV descriptor gaps.** Extend descriptor and stack-prior schemas with `ctx_model_max`, `ctx_launch_effective`, descriptor-native `mmproj`, KV/cache, and launch-effective fields. Regenerate with `--allow-incomplete` first, then shrink strict warnings.
4. **Fix the serving/launch drift path.** Reconcile `PORT_MAP["coder_escalation"] = 8071` versus generated `coder_escalation.endpoint=http://localhost:8070`, then add a guard/test that would catch recurrence.

## Reporting Instructions

After each implementation pass:

- Update this handoff and `stack-change-governance-pipeline.md` with commit hash, commands, guard counts, and remaining strict blockers.
- Add a concise progress entry under `progress/YYYY-MM/YYYY-MM-DD.md`.
- If index registration is not done in the same pass, include the suggested row in the final report for the main workflow.
