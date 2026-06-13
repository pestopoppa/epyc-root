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
- Current contract status after `54b7c77`: `compiled`.
- Guard result after `03ed49f`: default `uv run python scripts/validate/stack_change_guard.py` and strict guard are clean; `--all-hardcoded-surfaces` still reports legacy-test and historical-doc mentions only.
- Generated descriptors and stack priors now have `status: compiled`; stack-prior role records have empty `known_gaps`.
- Procedure role enum check: `python3 scripts/registry/sync_procedure_role_enums.py --check` exits 0.
- Command skeleton landing: `epyc-orchestrator` `e01d64d` adds `scripts/registry/stack_change_pipeline.py` plus `tests/unit/test_stack_change_pipeline.py`; follow-up `fe4b2aa` fixes temp preview procedure/schema paths and default stack-prior role scoping.
- Descriptor compiler quality-key normalization landed in `epyc-orchestrator` `3e7efce`: registry `quality_pct`/`quality_score` now become descriptor `overall`, `*_suite` keys become stable suite names such as `coder`/`agentic`/`math`, `vl_score` becomes `vision_language`, and `long_context_quality` becomes `long_context`. Role-specific `long_context` no longer overwrites an existing shared-model `overall` score.
- Descriptor compiler model-ID stabilization landed in `epyc-orchestrator` `ca9af53`: generated IDs now preserve quant underscores and strip suffixes such as `-Instruct`/`-it`, matching every current generated/live descriptor identity except the existing REAP benchmark-only descriptor.
- Descriptor update fail-closed guard landed in `epyc-orchestrator` `022a0d1`: `check` now reports that generated output would remove `reap-qwen3-coder-25b-a3b-q4_k_m`, and `update` refuses to write descriptors, stack priors, or procedure enum updates unless `--allow-descriptor-model-removal` is passed after an explicit coverage decision.
- REAP descriptor coverage landed in `epyc-orchestrator` `fbef837`: `roles.reap_25b_frontdoor` now mirrors `server_mode.reap_25b`, so compiler preview has no current-only or generated-only model IDs. `365e370` refreshed stack-prior source metadata afterward.
- Domain modality derivation landed in `epyc-orchestrator` `846c2d4`: generated descriptors now retain model-derived `code`, `math`, and `long_context` modalities instead of collapsing those models to text-only.
- GraphRouter training fleet discovery landed in `epyc-orchestrator` `8cf0310`: `scripts/graph_router/train_graph_router.py` now loads live LLMRole nodes from generated stack priors, skips benchmark/candidate roles, and keeps only a current non-retired degraded fallback.
- GraphRouter extraction/verifier action-space discovery landed in `epyc-orchestrator` `1f16759`: `scripts/graph_router/action_space.py` centralizes live action labels from stack priors, remaps legacy replay labels into current live roles, and makes verifier one-hot widths infer from classifier artifacts instead of fixed `8`.
- Launch alias port-map drift fix landed in `epyc-orchestrator` `d4acf24`: `PORT_MAP` now maps shared live aliases (`coder_escalation`, `worker_summarize`, `toolrunner`) to their computed shared server ports, and `validate_against_registry()` warns if future `PORT_MAP` values diverge from `ROLE_LAUNCH_META + NUMA_CONFIG`.
- Vision ReAct serving-port migration landed in `epyc-orchestrator` `06ff53c`: `src/api/routes/chat_pipeline/vision_stage.py` now reads `worker_vision` and `vision_escalation` ports from generated stack-prior serving records for multimodal ReAct calls, preserving only explicit degraded-mode fallback ports.
- Shared `server_mode` alias-port validation landed in `epyc-orchestrator` `40d46ea`: `validate_against_registry()` now warns if a registry row such as `server_mode.worker` carries a stale port for launch roles named through `model_role` or `shared_with`.
- AutoPilot preflight health-target migration landed in `epyc-orchestrator` `a5aaafb`: `scripts/autopilot/preflight_audit.py` now derives model-server health probes from generated stack-prior serving records and keeps only a current degraded fallback target list.
- AutoPilot human program guidance cleanup landed in `epyc-orchestrator` `60733c7`: `scripts/autopilot/program.md` now derives compaction target endpoints from generated stack priors instead of carrying a static target-port table, and no longer mentions dead coder/retired-architect ports or fixed-RAM tier-demotion guidance.
- AutoPilot program recurrence guard landed in `epyc-orchestrator` `cf73ac1`: `stack_change_guard.py --all-hardcoded-surfaces` now treats stale static endpoint/tier guidance in `scripts/autopilot/program.md` as a production-blocker surface.
- Launch-manifest semantic guard landed in `epyc-orchestrator` `312b28e`: `stack_change_guard.py` now compares live stack-prior serving endpoint ports, primary port membership, and tier against the current computed `HOT_SERVERS`/`WARM_SERVERS` launch manifest.
- Exact launch-port projection landed in `epyc-orchestrator` `dc14196`: `src/registry/stack_priors.py` now projects computed launch role port sets into serving records, preserving server slots, and `stack_change_guard.py` rejects missing launch ports or extra non-launch ports.
- Launch witness contract v2 landed in `epyc-orchestrator` `7917535`: generated stack priors now require `serving.launch.entries` and the guard compares launch mode, alias status, primary role, and optional NUMA/worker/vision instance metadata against the computed manifest.
- Launch-context/path witness contract v3 landed in `epyc-orchestrator` `a001017`: generated stack priors now require `serving.effective_context_tokens` and `serving.launch.requirements`, and the guard compares Gemma worker model/draft paths plus VL model/mmproj paths against computed stack-manifest launch truth.
- Launch-runtime witness contract v4 landed in `epyc-orchestrator` `33c81ff`: generated stack priors now require `serving.launch.runtime`, include launcher/path/runtime source hashes, and guard effective binary, runtime requirements, cache/KV, slot/save, and launch flag/spec state against computed stack-manifest launch truth.
- Supporting sidecar audits are retained under `handoffs/completed/`; active follow-up now lives in `model-stack-update-pipeline-audit.md`. Shared-runtime alias semantics are resolved as of `epyc-orchestrator` `a7b72a9`, and shared-runtime alias provenance is resolved as of `54b7c77`: `worker_general`, `worker_math`, and `toolrunner` alias mismatch notes are structured provenance, not blocking gaps. Runtime witness coverage is resolved as of `33c81ff`; simulated data-only stack-change fixtures are resolved as of `fb0fd6d`; architect quality projection is resolved as of `837829f` with `quality_overall: 0.8567`; GGUF-derived model context projection is resolved as of `b8477b0`; REAP quality projection is resolved as of `2ea28dd` with `quality_overall: 0.6011`; descriptor-native thinking-control evidence is resolved as of `865b2b1`; the retired-architect enum waiver path is closed as of `03ed49f`; production launcher help/summary inventory is manifest-derived as of `53f452c` and recurrence-guarded as of `b8a1abc`; stale KV/tool-permission runtime surfaces are normalized as of `e7fab9d`; AutoPilot system-card live-stack rows are rendered from stack priors as of `603ad6b`; status cleanup scans generated live stack-prior serving ports as of `6062a57`. The remaining blockers are other hardcoded-surface cleanup, scanner coverage for launch/feature/tool permission surfaces, and consumer migrations. q_scorer live/degraded provenance is available as of `d6912e7`; unsafe conflicted descriptor updates are blocked as of `4ca702d`.
- Live result after `603ad6b`: `stack_change_pipeline.py check --allow-known-gaps` reports descriptors, stack priors, procedure enums, guard, and strict checks OK; `--all-hardcoded-surfaces` reports only legacy-test and historical-doc classes after split-string test literals, with scanner warning count down to 90.
- Delegation report role preamble normalization landed in `epyc-orchestrator`
  `6ec2686`: compact specialist report prompts canonicalize legacy worker
  aliases before preamble selection, direct prompt preambles advertise only live
  `coder_escalation` / `worker_general`, and tests prove `worker_coder`,
  `worker_explore`, and `worker_fast` resolve without advertising retired
  labels.
- Architect investigation prompt live-role alignment landed in
  `epyc-orchestrator` `09948db`: the active template, fallback constant, and
  architect system example now use `coder_escalation` for implementation or
  file-split delegation and `worker_general` for investigation/search, with the
  valid role list excluding retired worker labels.
- Output formalizer live-worker routing landed in `epyc-orchestrator`
  `4bf8061`: `_formalize_output` now delegates final formatting to
  `worker_general` instead of legacy `worker_explore`, and the helper docstring
  no longer embeds stale model speed or port assumptions.

## Prior Pipeline Work Found

The standardized-pipeline foundation already exists in `epyc-orchestrator`:

| Artifact | Role in pipeline | Current status |
|---|---|---|
| `docs/reference/stack-truth-precedence.md` | Declares source precedence: live serving topology first, descriptors second, role metadata third, historical evidence last. | Present; use as governance contract. |
| `orchestration/model_registry.yaml` | Lean live deployment truth for `server_mode.*`, ports, slots, tiers, shared bindings, role metadata, and runtime defaults. | Source of live serving truth, but still contains older role/prose fields that can drift. |
| `orchestration/model_descriptors.yaml` | Physical model/evidence layer keyed by model identity, not role. | Present and `status: compiled` after `54b7c77`; carries GGUF-derived context, REAP/architect quality, structured thinking-control evidence, and alias provenance under `role_bindings.alias_overrides`. |
| `src/registry/model_descriptors.py` and `scripts/registry/compile_descriptors.py` | Descriptor compiler and CLI wrapper. | Present; needs stricter completeness policy and richer structured fields. |
| `src/registry/stack_priors.py` and `scripts/registry/compile_stack_priors.py` | Generates the single consumer contract from lean registry, descriptors, and stack manifest. | Present; current generated records expose alias provenance under `evidence.alias_overrides` and have empty `known_gaps`. |
| `orchestration/derived/stack_priors.yaml` | Generated consumer surface for role -> model, serving, priors, acceleration, evidence, known gaps. | Current no-inference contract; `status: compiled` after `54b7c77`. |
| `scripts/validate/stack_change_guard.py` | Validates freshness, contract shape, live-role invariants, procedure enum drift, hardcoded surfaces, and exceptions. | Passes through `603ad6b`; stack-change pipeline check reports guard/strict OK and all-surface warnings classified legacy-test/historical-doc only. |
| `orchestration/stack_change_guard_exceptions.yaml` | Expiring metadata for hardcoded-surface exceptions. | Present; `03ed49f` removed the retired `src/roles.py` enum waiver from the default/strict guard path. |
| `scripts/registry/sync_procedure_role_enums.py` | Generates/checks procedure role choices from stack priors. | Green on 2026-06-13. |
| `scripts/server/orchestrator_stack.py start --compile-descriptors` | Launcher-side descriptor compile hook. | Exists, but does not replace a full canonical post-stack-change pipeline. |

Recently completed main-track work also matters:

- Retired active `architect_coding` graph node removed from active PydanticGraph/LangGraph topology.
- `Role.ARCHITECT_CODING` normalized in `03ed49f` as an enum alias of live `Role.ARCHITECT_GENERAL`; old serialized/direct string input `"architect_coding"` still normalizes through `_missing_` / `_LEGACY_ROLE_ALIASES`.
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
| Context limits | Scattered `ctx_max`, `context_length`, `max_context`, launch `-c`/`n_ctx`, research registry | Descriptor `ctx_model_max` plus serving `ctx_launch_effective` projected to stack priors | GGUF-derived `ctx_max` projection landed in `b8477b0`; keep guards for future swaps and any roles without structured header evidence. |
| Thinking controls | Chat-template kwargs, model-family behavior, role registry notes | Descriptor `acceleration.thinking_control` plus legacy boolean `enable_thinking` only when truly boolean | `865b2b1` preserves native/no-toggle/template-ignored evidence without forcing `enable_thinking` true/false. |
| KV/cache settings | `server_mode.kv_quant`, descriptor acceleration `kv`, launcher args, model comments, `scripts/autopilot/kv_compress.py` | Descriptor/serving structured fields | `e7fab9d` normalized adaptive compression fallbacks for shared frontdoor roles and retired architect removal; continue compiling `kv.k`, `kv.v`, cache sizing, slot/KV implications and guard consumers reading comments. |
| Server launch args and binary family | `scripts/server/stack_manifest.py`, `stack_numa.py`, `stack_commands.py`, `orchestrator_stack.py`, `server_mode.runtime_requirements` | Generated launch requirements from stack priors or a validated launch projection | Add compile/check for binary path, ik-llama requirements, MTP/spec knobs, mmproj paths, and stale running process attestation. |
| Vision/mmproj metadata | `stack_manifest.py` `VISION_*`, registry role records, `src/vision/models.py`; `chat_pipeline/vision_stage.py` now reads serving ports from stack priors | Descriptor-native model + mmproj fields projected into serving records | Current descriptors note mmproj is not native; add fields before strict mode. |
| Role aliases and retired compatibility | `src/roles.py`, tests, historical docs, graph aliases, legacy tool permission strings | Live roles from stack priors; compatibility aliases normalize to live roles; legacy mentions stay classified | Shared-runtime alias overrides are provenance after `54b7c77`; `03ed49f` removed the temporary `Role.ARCHITECT_CODING` production-waiver path by making it an enum alias of `architect_general`; `e7fab9d` makes legacy `ToolRegistry` permission strings canonicalize through live `Role` semantics; `6ec2686`, `09948db`, and `4bf8061` keep report/investigation/formalizer prompt surfaces on live role wording while preserving legacy worker alias compatibility where needed. |
| Graph nodes and routing topology | `src/graph/**`, `src/api/routes/chat_pipeline/**`, `src/api/routes/chat_routing.py` | Live role set and generated role classifications | Retired active node is removed; keep guard coverage for recurrence. |
| Admission/runtime policy tables | `src/api/admission.py`, `src/runtime/inference_lock.py`, `src/runtime/inference_tap.py`, dashboard routes, legacy executor permissions | Stack-prior serving/tier/slot records plus explicit policy hints | Migrate remaining local high-cost/lock/tap classifications or label as generated policy projection; `e7fab9d` removes the separate `architect_coding` executor permission row by canonicalizing compatibility strings. |
| API/config model maps | `src/config/models.py`, `src/api/routes/openai_compat.py`, CLI/status probes | Stack-prior live roles and serving records | Recent cleanup removed retired active maps; finish replacing parallel static maps where practical. |
| Procedure role enums | `orchestration/procedure.schema.json`, `orchestration/procedures/add_model_to_registry.yaml` | Generated from stack priors | Already guarded; keep in stack-change workflow. |
| Operator docs, system cards, dashboards | `docs/**`, dashboard snapshot/routes, AutoPilot system-card code | Generated summaries from stack priors plus running-state attestation | `603ad6b` renders the AutoPilot system-card live-stack table from stack priors first; manual docs can remain historical only if labeled, and remaining current summaries should be generated. |
| Production launch wrapper summaries | `scripts/server/launch_production.sh` help/mode text | `scripts/server/stack_manifest.py` launch groups plus `--status` runtime attestation | `53f452c` derives `--full`/`--with-burst` summaries from `HOT_SERVERS`/`WARM_SERVERS`, labels `--minimal` as a legacy HOT-tier alias, and removes stale RAM/model/retired-role inventory from the wrapper; `b8a1abc` guards against recurrence in `scripts/server/*.sh`. |
| Research registry and benchmark artifacts | `/mnt/raid0/llm/epyc-inference-research/orchestration/model_registry.yaml`, `benchmarks/results/**` | Evidence/candidate history only | Never let research rows become live deployment truth without descriptor projection and measurement status. |

Highest-risk live stale-value hazards today:

1. RESOLVED/EXTENDED 2026-06-13 in `d4acf24`/`dc14196`/`7917535`/`a001017`/`33c81ff`: `scripts/server/stack_manifest.py` no longer maps `coder_escalation` to dead port `8071`, stack priors now project exact computed launch port sets rather than broad shared-server NUMA unions, contract v2 carries launch-entry witness data, contract v3 guards effective launch context plus worker/VL model paths, and contract v4 guards effective runtime/binary/cache/KV/flag state.
2. Descriptor-native `ctx_max` is no longer the current live blocker for the main GGUF roles after `b8477b0`; future model swaps still need the same projection path and guard coverage before launch.
3. Vision launch requirements now carry guarded `mmproj` paths in stack priors (`a001017`), but descriptor-native projector metadata remains incomplete. The active VL ReAct port consumer was migrated to stack-prior serving records in `06ff53c`.
4. Worker-family shared-runtime conflicts are resolved in `a7b72a9` and structured as provenance in `54b7c77`: `worker_general`, `worker_math`, and `toolrunner` alias overrides preserve ignored stale role-local model metadata under descriptor `role_bindings.alias_overrides` and stack-prior `evidence.alias_overrides`.
5. Strict launch gating no longer depends on the temporary `ARCHITECT_CODING` enum waiver after `03ed49f`, and `e7fab9d` normalized the remaining low-risk stale role runtime surfaces in KV compression and legacy tool permissions; remaining work is consumer migration and residual classified hardcoded-surface cleanup, not descriptor `known_gaps`.

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
   - Strict guard / launch promotion: only after the temporary retired-role enum
     compatibility waiver and remaining consumer surfaces are handled.
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
  - DONE in `b8477b0`: add structured `ctx_model_max` / GGUF-derived `ctx_max` evidence for Qwen3-Next 80B, Qwen3.5-122B, Qwen2.5-VL 7B, Qwen3-VL 30B, and REAP-Qwen3-Coder 25B; effective launch context was already guarded by contract v3.
  - Add descriptor-native vision `mmproj`/projector fields.
  - Add KV/cache settings and launch-effective context where missing.
  - DONE in `a7b72a9`: classify worker/toolrunner role-server conflicts as resolved shared-runtime alias projections with non-live role metadata preserved as known-gap notes.
  - DONE in `837829f`: structure `roles.architect_general.performance.quality_score: "2.57/3"` and regenerate descriptors/stack priors so `architect_general`/`qwen35_122b_q4km` project `quality_overall: 0.8567`; their remaining known gap is structured ctx only.
  - DONE in `2ea28dd`: project REAP-25B Claude-as-Judge raw-score quality evidence into descriptors/stack priors as `quality_overall: 0.6011`.
  - DONE in `865b2b1`: add structured `acceleration.thinking_control` evidence for ingest, REAP, and VL roles while leaving legacy `enable_thinking` unset for native/no-toggle/template-ignored behavior; enable-thinking compatibility gaps are cleared.
  - DONE in `54b7c77`: treat shared-runtime alias mismatch notes as provenance, writing descriptor `role_bindings.alias_overrides` and stack-prior `evidence.alias_overrides`; generated descriptors/priors now have `status: compiled` and stack-prior records have empty `known_gaps`.
  - Target files: `src/registry/model_descriptors.py`, `scripts/registry/compile_descriptors.py`, `orchestration/model_descriptors.yaml`, `src/registry/stack_priors.py`, `scripts/registry/compile_stack_priors.py`, `tests/unit/test_model_descriptor_compiler.py`, `tests/unit/test_model_descriptors_schema.py`, `tests/unit/test_stack_priors_compiler.py`.

- [ ] **P1 - Add the canonical stack-change command/procedure.**
  - **2026-06-13 partial**: `e01d64d` added the initial command skeleton and unit tests; `fe4b2aa` fixed preview-path and role-scope handling; `3e7efce` normalized descriptor compiler quality suite keys without touching the HIGH-impact merge helper; `ca9af53` stabilized compiler model IDs against the current descriptor policy; `022a0d1` added fail-closed descriptor model-removal protection; `fbef837` closed REAP descriptor coverage; `365e370` refreshed stack-prior metadata; `846c2d4` restored generated code/math/long-context modalities.
  - Build one no-inference operator entrypoint with `check` and `update` modes.
  - `check` mode must be safe for CI and local preflight: read-only, deterministic, and nonzero on stale generated artifacts, enum drift, unwaived production blockers, or strict-eligible gaps.
  - `update` mode must regenerate descriptors, stack priors, procedure enums, and any generated stack summaries from structured sources only.
  - The command output should include current loose/all-surface/strict guard counts, stale hardcoded-surface categories, source hashes, and next remediation commands.
  - Target files: new `scripts/registry/stack_change_pipeline.py` or equivalent Make/CLI target, `scripts/registry/compile_descriptors.py`, `scripts/registry/compile_stack_priors.py`, `scripts/registry/sync_procedure_role_enums.py`, `scripts/validate/stack_change_guard.py`, `scripts/server/orchestrator_stack.py`, `tests/unit/test_stack_change_guard.py`, new workflow tests if needed.

- [ ] **P2 - Make launch/serving projection consume the generated contract.**
  - **2026-06-13 partial**: `d4acf24` reconciled stale raw `PORT_MAP` entries for shared aliases and added a registry validation warning if `PORT_MAP` drifts from computed launch roles again.
  - **2026-06-13 partial**: `06ff53c` migrated `chat_pipeline/vision_stage.py` ReAct VL port selection from a raw `_VL_PORT_MAP` to generated stack-prior serving records, with explicit degraded fallback and tests.
  - **2026-06-13 partial**: `40d46ea` extended `validate_against_registry()` so shared `server_mode` rows with `model_role`/`shared_with` aliases warn when their port diverges from computed launch roles.
  - **2026-06-13 partial**: `a5aaafb` migrated AutoPilot preflight model-server health targets from a raw port table to generated stack-prior serving records, grouped by shared health URL.
  - **2026-06-13 partial**: `60733c7` replaced the AutoPilot program's static compaction target-port table with a stack-priors endpoint query and removed stale tier/RAM guidance.
  - **2026-06-13 partial**: `cf73ac1` added hardcoded-surface scanner coverage so stale static endpoint/tier guidance in the AutoPilot program fails future guard checks.
  - **2026-06-13 partial**: `312b28e` added a semantic guard comparing generated live serving endpoint/primary-port/tier records against computed launch-manifest roles.
  - **2026-06-13 partial**: `dc14196` made stack priors project exact per-role launch port sets from computed `HOT_SERVERS`/`WARM_SERVERS`, while preserving slots, and added missing/extra port-set validation.
  - **2026-06-13 partial**: `7917535` bumped stack-prior contract v2 and added guarded `serving.launch.entries` witness data for launch mode, alias status, primary role, and optional NUMA/worker/vision instance metadata.
  - **2026-06-13 partial**: `a001017` bumped stack-prior contract v3 and added guarded `serving.effective_context_tokens` plus `serving.launch.requirements` for Gemma worker model/draft paths and VL model/mmproj paths.
  - **2026-06-13 partial**: `33c81ff` bumped stack-prior contract v4 and added guarded `serving.launch.runtime` effective runtime witness records with launcher/path/runtime source hashes.
  - **2026-06-13 partial**: `e7fab9d` normalized `scripts/autopilot/kv_compress.py` production port names and adaptive layer fallbacks so shared frontdoor roles share layer evidence and retired architect entries are inactive.
  - Continue with remaining hardcoded-surface cleanup and consumer migrations; the temporary retired-role enum waiver path is closed by `03ed49f`.
  - Ensure health/status/probe code reads stack-prior serving records or validated launch metadata.
  - Target files: `scripts/server/stack_manifest.py`, `scripts/server/stack_numa.py`, `scripts/server/stack_commands.py`, `scripts/server/orchestrator_stack.py`, `src/cli_orch.py`, `src/api/routes/dashboard_topology.py`, `tests/unit/test_model_server_coverage.py`, `tests/unit/test_stack_change_guard.py`, `tests/unit/test_build_server_command_helpers.py`.

- [x] **P3 - Add simulated data-only stack-change CI fixtures.**
  - DONE in `fb0fd6d`: `tests/unit/test_stack_change_pipeline_simulated_fixtures.py` covers frontdoor/coder shared-runtime swaps, worker-family aliases, retired-role enum cleanup, stale runtime requirements, and context/KV/acceleration drift.
  - `stack_change_pipeline.py check` now prints the simulated fixture pytest target as a reference step.
  - Acceptance: fixture registry/descriptor inputs regenerate consumer outputs with no production-code edits; stale drift is rejected before promotion.

- [ ] **P4 - Add provenance plumbing for live vs degraded consumer values.**
  - **2026-06-13 partial**: `8cf0310` migrated GraphRouter training fleet discovery from a stale hardcoded model table to generated stack priors. Live smoke returned 10 HOT live roles with current shared ports and no retired `architect_coding`; `--all-hardcoded-surfaces` stayed at `WARN: 109`.
  - **2026-06-13 partial**: `1f16759` migrated GraphRouter extraction/verifier action spaces to a shared helper backed by stack priors. Legacy `architect_coding`/`worker_explore` replay labels now remap to current live actions, verifier extraction infers action width from the classifier artifact, and focused GraphRouter/stack-change tests passed (`40 passed`).
  - **2026-06-13 partial**: `6af8b3d` added public `throughput_prior_provenance(cost_config=None)` for comparative seeding reward throughput priors. It reports config override, legacy override, stack-prior, degraded fallback, or missing source plus role coverage/path/reason metadata while leaving `compute_comparative_rewards` math and return shape unchanged.
  - **2026-06-13 partial**: `6ec2686` normalized compact specialist delegation report preambles through `_normalize_delegate_role`; direct preambles now advertise live `coder_escalation`/`worker_general` while `worker_coder`, `worker_explore`, and `worker_fast` remain compatibility aliases that render live-role prompt text.
  - **2026-06-13 partial**: `09948db` aligned architect investigation prompt templates, fallback text, and architect examples with live roles only: `coder_escalation` for implementation/file-split delegation and `worker_general` for investigation/search. Prompt-builder tests assert retired worker labels are absent.
  - **2026-06-13 partial**: `4bf8061` routed `_formalize_output` through live `worker_general` instead of legacy `worker_explore`, removed stale model speed/port assumptions from the docstring, and added coverage asserting the `llm_call` role.
  - q_scorer should be able to expose whether values came from `stack_priors`, override, registry fallback, or degraded local fallback.
  - Seeding/replay reward paths should write cost-prior provenance when they use live priors vs replay overrides.
  - Continue with remaining low-risk offline/replay consumers, classifying true historical labels separately from live training priors.
  - Target files: `orchestration/repl_memory/q_scorer.py`, `scripts/benchmark/seeding_rewards.py`, `scripts/benchmark/seeding_eval.py`, `scripts/graph_router/extract_training_data.py`, `scripts/graph_router/extract_verifier_training_data_debiased.py`, `tests/unit/test_q_scorer.py`, `tests/unit/test_seeding_rewards.py`, graph-router tests.

- [ ] **P5 - Generate current operator-facing stack summaries.**
  - **2026-06-13 partial**: `53f452c` moved `scripts/server/launch_production.sh` mode summaries from duplicated hand-written inventory to `scripts/server/stack_manifest.py` launch groups; `--full` prints HOT groups, `--with-burst` prints HOT+WARM groups, and `--minimal` is labelled as a legacy HOT-tier alias.
  - **2026-06-13 partial**: `b8a1abc` added `stale_launch_wrapper_static_inventory` scanner coverage so removed architect/port/model/RAM wording in `scripts/server/*.sh` is a production blocker.
  - **2026-06-13 partial**: `603ad6b` moved the AutoPilot system-card active role table from raw registry/server-mode rows to generated stack-prior live rows, with stale registry rows retained only as degraded fallback.
  - Replace manual current-stack tables in docs/system cards/dashboards with generated output from stack priors plus running-state attestation.
  - Keep historical docs only if labeled historical.
  - Target files: `docs/chapters/04-production-server-stack.md`, `docs/diagrams/orchestration_topology.md`, AutoPilot system-card generation, dashboard snapshot routes, launch/status wrappers, and a new summary generator if needed.

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

P3 simulated swaps (complete in fb0fd6d)
  -> strict guard promotion
  -> launch gate enforcement
```

P1 can begin immediately by composing existing scripts and preserving current gaps as failures/warnings. P2 can also begin before P0 is completely done for obvious stale maps such as `coder_escalation: 8071`; P3 is complete as of `fb0fd6d`, so strict launch enforcement now waits on P0 strict-gap closure and the P6 launch gates.

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
- `architect_coding` cannot appear in live priors, active graph topology, launch flags, status probes, q_scorer defaults, or routing defaults. Compatibility aliases normalize to the live architect role and are covered by legacy-routing tests.
- Shared-server roles do not double-count memory or drift to dead ports; `frontdoor` and `coder_escalation` agree on model id, endpoint, mmap ownership, and scorer costs.
- Live context, KV/cache, mmproj, launch binary, and acceleration requirements are structured, generated, and guarded.
- Pre-launch and post-launch checks detect stale generated artifacts and stale running processes before AutoPilot or production traffic can rely on them.

## Main Workflow Pickup

1. **DONE 2026-06-13 (`e01d64d`, `fe4b2aa`) - Create the canonical stack-change command skeleton.** `scripts/registry/stack_change_pipeline.py` now composes the existing descriptor compiler, stack-prior compiler, enum sync, and guard into read-only `check` and generated-artifact `update` modes.
2. **DONE 2026-06-13 (`3e7efce`, `ca9af53`, `022a0d1`, `fbef837`, `365e370`, `846c2d4`, `4ca702d`, `a7b72a9`) - Resolve descriptor/compiler drift reported by the new command through shared-runtime alias semantics.** Safe compiler fixes now normalize generated quality keys and model IDs, fail closed on descriptor model-ID removal, preserve REAP coverage through structured registry metadata, retain domain modalities, block generated descriptor updates when role/server conflicts are present, and represent `worker_math`/`toolrunner` as live aliases on the Gemma worker runtime descriptor. `check --allow-known-gaps` now passes with expected known-gap warnings; remaining descriptor work is strict-contract field coverage, not the shared-runtime conflict blocker.
3. **PARTIAL 2026-06-13 (`8cf0310`, `1f16759`) - Migrate offline stack consumers away from hardcoded model rosters/action spaces.** GraphRouter training now reads live stack priors, and GraphRouter extraction/verifier data now derives its action space from stack priors/classifier artifacts while preserving explicit legacy replay remaps. Continue with any remaining low-risk offline consumers before touching HIGH-impact descriptor assembly.
4. **DONE 2026-06-13 (`837829f`, `b8477b0`, `2ea28dd`, `865b2b1`, `54b7c77`) - Close the current descriptor evidence/gap tranche.** Architect quality, GGUF-derived model context, REAP quality, thinking-control evidence, and shared-runtime alias provenance now compile cleanly; generated descriptors/priors are `status: compiled` and stack-prior `known_gaps` are empty.
5. **DONE 2026-06-13 (`03ed49f`) - Close the temporary retired-architect production-waiver path.** `Role.ARCHITECT_CODING` is an enum alias of live `Role.ARCHITECT_GENERAL`, legacy `"architect_coding"` strings still normalize to `architect_general`, and the active prompt fallback / graph node map / prewarm special-cases no longer treat coding architect as a distinct live role. Default and strict guards are clean; `--all-hardcoded-surfaces` remains useful for legacy-test and historical-doc cleanup.
6. **PARTIAL 2026-06-13 (`d4acf24`, `06ff53c`, `40d46ea`, `a5aaafb`, `60733c7`, `cf73ac1`, `312b28e`, `dc14196`, `7917535`, `a001017`, `33c81ff`, `fb0fd6d`, `53f452c`, `b8a1abc`, `e7fab9d`, `603ad6b`, `6062a57`) - Fix the serving/launch/runtime/controller drift path.** The concrete shared-alias `PORT_MAP` mismatch is fixed and covered by tests/registry warnings; the active vision ReAct path and AutoPilot preflight health probes now read ports from generated stack-prior serving records; shared `server_mode` alias rows now warn on stale ports for covered launch roles; the AutoPilot program prompt now derives compaction endpoints from stack priors and has guard coverage against static endpoint/tier recurrence; generated live serving endpoint/primary-port/tier drift, exact launch port sets, launch-entry witness data, effective launch context, worker/VL model-path requirements, and effective runtime/binary/cache/KV/flag state are checked against the computed launch manifest; the production launch wrapper and AutoPilot system card now derive current stack summaries from generated/validated sources, with launch-wrapper static-inventory recurrence guarded; status cleanup scans include manifest HOT/WARM, NUMA replica, Docker, `PORT_MAP`, and generated live stack-prior serving ports while excluding candidate/malformed stack-prior ports; KV adaptive compression now treats shared frontdoor roles and retired architect compatibility using current live role semantics; simulated data-only fixtures now exercise stack-change drift without production-code edits. Continue with remaining consumer migrations and classified hardcoded-surface cleanup.

## Reporting Instructions

After each implementation pass:

- Update this handoff and `stack-change-governance-pipeline.md` with commit hash, commands, guard counts, and remaining strict blockers.
- Add a concise progress entry under `progress/YYYY-MM/YYYY-MM-DD.md`.
- If index registration is not done in the same pass, include the suggested row in the final report for the main workflow.
