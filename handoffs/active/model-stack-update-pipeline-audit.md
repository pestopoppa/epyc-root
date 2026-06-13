# Model Stack Update Pipeline Audit

**Status**: IN PROGRESS 2026-06-13 - W1/W2 stack-prior consumer migration active; GraphRouter offline action-space cleanup complete through `epyc-orchestrator` `1f16759`; serving-port/operator-guidance migrations/guards complete through `a6d1200`; descriptor-delta reporting complete through `d5cb80a`; conflicted descriptor update guard complete through `4ca702d`; exact launch-port projection/guard complete through `dc14196`; launch-witness contract v2 complete through `7917535`; shared-runtime descriptor alias semantics complete through `a7b72a9`; launch-context/path witness contract v3 complete through `a001017`; launch-runtime witness contract v4 complete through `33c81ff`; simulated data-only stack-change fixtures complete through `fb0fd6d`; architect quality projection complete through `837829f`; retired architect enum waiver path closed through `03ed49f`; production launcher summary derived from manifest through `53f452c`; sidecar hardening audit merged from `handoffs/completed/model-stack-update-pipeline-hardening-sidecar.md`
**Priority**: HIGH - stale model constants can silently misroute, mis-score, launch the wrong stack, or corrupt AutoPilot/replay data after a model change
**Scope**: Audit and implementation handoff. No inference, AutoPilot, orchestrator code, research code, or index files were changed by this pass.
**Related**: [stack-change-governance-pipeline.md](stack-change-governance-pipeline.md), [model-capability-descriptors.md](model-capability-descriptors.md), [routing-truth-restoration.md](routing-truth-restoration.md), [running-state-attestation.md](../completed/running-state-attestation.md), [MEASUREMENT.md](../../MEASUREMENT.md)

## Objective

Turn the existing stack-prior work into a robust, repeatable, fail-closed pipeline for changing orchestration-stack models and all model-specific quantities:

- role -> model binding
- role -> serving endpoint, ports, slots, shared-server binding, and hot/warm state
- q_scorer and seeding reward cost/TPS/quality priors
- routing priors, role budgets, role enums, admission limits, lock/tap classifications, and launch requirements
- generated operator docs/runbooks and runtime attestation

The audit conclusion is clear: the project already has the right foundation, but the process is not yet standardized enough to make model swaps data-only. The next step is not another manual q_scorer-style patch; it is to harden `stack_priors.yaml` as the generated contract and migrate every live consumer to that contract or to an explicit degraded-mode fallback.

## Existing Pipeline Artifacts

These are the real standardized-pipeline artifacts found in the current root/orchestrator trees:

- `/mnt/raid0/llm/epyc-orchestrator/docs/reference/stack-truth-precedence.md`
  - Defines precedence: live serving topology first, descriptors second, role metadata third, historical records last.
  - Explicitly states that `server_mode.*.tier` overrides stale `roles.*.memory.residency`, shared mmap roles must not double-count memory, and retired roles such as `architect_coding` must not appear in active live priors.
- `/mnt/raid0/llm/epyc-orchestrator/src/registry/stack_priors.py`
  - Compiles role records from lean registry, model descriptors, and stack manifest.
  - Current output includes contract v3 plus serving endpoint/ports/slots/tier, effective launch context, launch-entry witness records, launch requirements for worker/VL model paths, priors for throughput/quality/memory, acceleration metadata, model identity, source evidence, and known gaps (`69057f3`, `7917535`, `a001017`).
- `/mnt/raid0/llm/epyc-orchestrator/scripts/registry/compile_stack_priors.py`
  - Writes `/mnt/raid0/llm/epyc-orchestrator/orchestration/derived/stack_priors.yaml`.
- `/mnt/raid0/llm/epyc-orchestrator/scripts/validate/stack_change_guard.py`
  - Validates generated artifact contract shape, freshness, live-role gaps, retired-role leakage, generated procedure enums, and curated hardcoded surfaces.
  - `--all-hardcoded-surfaces` currently reports production blockers, legacy tests, and historical docs separately; `--surface-exceptions` reads documented, expiring exceptions (`e162c7c`).
- `/mnt/raid0/llm/epyc-orchestrator/scripts/registry/sync_procedure_role_enums.py`
  - Syncs `add_model_to_registry.yaml` role choices and `procedure.schema.json` executor roles from stack priors.
- `/mnt/raid0/llm/epyc-orchestrator/orchestration/model_descriptors.yaml`
  - Physical model identity/evidence layer. Descriptors are keyed by model, not role.
- `/mnt/raid0/llm/epyc-root/handoffs/active/stack-change-governance-pipeline.md`
  - The implementation track. W1/W2 are landed; W3 and W4 are partially landed; W5/W6 remain open.

GitNexus note before this handoff edit: root was refreshed via `scripts/gitnexus-analyze.sh` to `24,180 nodes | 26,206 edges | 43 flows`. `gitnexus impact --repo epyc-root handoffs/active/model-stack-update-pipeline-audit.md --direction upstream` returned target not found, `UNKNOWN` risk, `impactedCount=0`, which is expected for this doc path.

## Sidecar Hardening Review

The 2026-06-13 sidecar audit in `handoffs/completed/model-stack-update-pipeline-hardening-sidecar.md` found no reason to invent a parallel registry or process. It confirmed that the current descriptor -> stack-prior -> guard -> consumer-migration path is the right foundation, with three immediate hardening priorities:

1. **Descriptor check output is now actionable for shared-runtime aliases.** PARTIAL RESOLUTION in `epyc-orchestrator` `d5cb80a`: check mode reports changed model IDs, changed field paths, generated removals/additions, and top-level drift before stale-artifact errors. SAFETY EXTENSION in `4ca702d`: `check` and `update` fail closed when generated descriptors contain role/server conflict gaps. RESOLUTION in `a7b72a9`: `worker_math` and `toolrunner` now compile as virtual aliases of the live Gemma worker runtime instead of standalone live Qwen descriptors; `stack_change_pipeline.py check --allow-known-gaps` now passes with expected known-gap warnings.
2. **q_scorer fallback provenance is now visible.** RESOLVED in `epyc-orchestrator` `d6912e7`: `QScorerPriors` and default `ScoringConfig` now expose per-role source maps for TPS, quality, and memory priors plus an optional degraded reason. Degraded fallback tables remain available for offline/replay, but live/default scoring can now distinguish generated stack-prior values from fallback-filled values.
3. **Generated semantics remain incomplete but launch witness is stronger.** EXTENDED in `epyc-orchestrator` `dc14196`: stack priors now project exact per-role launch port sets from computed `HOT_SERVERS`/`WARM_SERVERS`, and the guard rejects both missing launch ports and extra non-launch ports. EXTENDED in `7917535`: contract v2 requires `serving.launch.entries` and the guard compares launch mode, alias status, primary role, and NUMA/worker/vision instance metadata against the computed manifest. EXTENDED in `a7b72a9`: shared-runtime aliases are represented as alias bindings on the primary runtime descriptor with non-live role metadata recorded as known gaps. EXTENDED in `a001017`: contract v3 requires `serving.effective_context_tokens` and `serving.launch.requirements`, projecting Gemma worker model/draft paths and VL model/mmproj paths into guarded generated priors. EXTENDED in `33c81ff`: contract v4 requires `serving.launch.runtime`, adds launcher/path/runtime source hashes, and guards effective binary family/path, runtime requirements, cache/KV settings, slot-save policy, and launch flags/spec state against computed launch truth. EXTENDED in `fb0fd6d`: simulated data-only workflow fixtures prove shared-runtime swaps, retired-role cleanup, runtime-requirement drift, and context/KV/acceleration drift are caught without production-code edits. EXTENDED in `837829f`: architect quality evidence is structured and projected into descriptors/stack priors. EXTENDED in `03ed49f`: the temporary retired-architect production waiver is gone because the enum member now aliases live `architect_general` and legacy strings normalize to the live role. Remaining work is consumer migration plus residual classified hardcoded-surface cleanup.

## Current Drift Examples

The following examples are evidence-backed reasons this work should stay high ROI and should not be handled as one-off cleanup.

1. `scripts/benchmark/seeding_rewards.py` previously owned a stale TPS table.
   - RESOLVED in `epyc-orchestrator` `7ecf847`: `compute_comparative_rewards()` now reads live role throughput from `orchestration/derived/stack_priors.yaml`; missing priors fail closed to the existing no-TPS `0.3` branch unless a caller explicitly provides override/degraded data.
   - EXTENDED in `epyc-orchestrator` `5773777`: active 3-way benchmark evaluation now enumerates live non-VL architect roles from stack priors, the legacy seeder derives slow roles from `ARCHITECT_ROLES`, and the corpus quality gate loads live model/port/name data from stack priors instead of the stale pre-consolidation model table.
   - Validation dropped the live guard from 73 to 62 warnings in `7ecf847`, then from 62 to 56 warnings in `5773777`; `--all-hardcoded-surfaces` now reports 161 warnings after the benchmark cleanup.

2. API routing and delegation still contain retired live-role constants.
   - First cleanup landed in `epyc-orchestrator` `b1402a2`: `src/api/routes/chat_delegation_decision.py` no longer keeps `architect_coding` budget defaults, and the live guard warning count dropped from 85 to 83.
   - Second cleanup landed in `epyc-orchestrator` `481516c`: `src/api/routes/chat_pipeline/delegation_stage.py` and `src/api/routes/chat_pipeline/proactive_stage.py` no longer treat retired `architect_coding` as an architect entrypoint, and the live guard warning count dropped from 83 to 81.
   - Third cleanup landed in `epyc-orchestrator` `519f710`: `_role_to_task_type()` no longer contains the redundant retired-role check, and the live guard warning count dropped from 81 to 80.
   - Fourth cleanup landed in `epyc-orchestrator` `d9c053c`: `/v1/models` now derives live model IDs from `stack_priors.yaml` plus compatibility aliases, and the live guard warning count dropped from 80 to 79.
   - Fifth cleanup landed in `epyc-orchestrator` `1b9db81`: `dashboard_snapshot.py` no longer carries a retired in-flight age override, and the live guard warning count dropped from 79 to 78.
   - Sixth cleanup landed in `epyc-orchestrator` `6bc1f51`: runtime inference lock/tap heavy-role classifications no longer include retired `architect_coding`, and the live guard warning count dropped from 78 to 76.
   - Seventh cleanup landed in `epyc-orchestrator` `e6e10d8`: approval-gate high-cost role classification no longer includes retired `architect_coding`, and the live guard warning count dropped from 76 to 75.
   - Eighth cleanup landed in `epyc-orchestrator` `eb4dac5`: `_heuristic_role_priors()` now filters its default candidate roles through live `stack_priors.yaml` roles and uses a non-retired degraded fallback; live guard warning count dropped from 75 to 74.
   - Ninth cleanup landed in `epyc-orchestrator` `b5bf5eb`: `analyze_routing_policy.py` now derives specialist-utilization roles from live `stack_priors.yaml` roles with a non-retired fallback; live guard warning count dropped from 74 to 73.
   - Tenth cleanup landed in `epyc-orchestrator` `7ecf847`: `seeding_rewards.py` derives reward throughput and architect grouping from stack priors; live guard warning count dropped from 73 to 62.
   - Eleventh cleanup landed in `epyc-orchestrator` `5773777`: `seeding_eval.py`, `seeding_scoring.py`, `seeding_legacy.py`, and `corpus_quality_gate.py` no longer contain live benchmark retired-role/model assumptions; live guard warning count dropped from 62 to 56.
   - Twelfth cleanup landed in `epyc-orchestrator` `f24eab7`: active config URL/timeout maps no longer publish retired `architect_coding` endpoints or role timeouts; live guard warning count dropped from 56 to 46 and `--all-hardcoded-surfaces` dropped from 161 to 146.
   - Thirteenth cleanup landed in `epyc-orchestrator` `2967526`: the production launcher no longer force-enables `ORCHESTRATOR_LANGGRAPH_ARCHITECT_CODING`; this removed a live startup hazard that the current lowercase hardcoded-surface scan did not count.
   - Fourteenth cleanup landed in `epyc-orchestrator` `c2b4437`: retired `architect_coding` no longer has an active parsing-mode entry and the llm-cache target comment no longer lists it; live guard warning count dropped from 46 to 44 and `--all-hardcoded-surfaces` dropped from 146 to 143.
   - Fifteenth cleanup landed in `epyc-orchestrator` `03ed49f`: `Role.ARCHITECT_CODING` is now an enum alias of live `Role.ARCHITECT_GENERAL`; legacy `"architect_coding"` strings still normalize to `architect_general`; and active prompt fallback / graph node map / prewarm special-cases no longer treat coding architect as a distinct live role.
   - Remaining risk: legacy tests and historical docs can still preserve old names unless classified or rewritten; they are no longer production blocker waivers.

3. Config models no longer preserve dead URLs/timeouts as active live maps.
   - RESOLVED in `epyc-orchestrator` `f24eab7`: `src/config/models.py` and `src/config/__init__.py` no longer expose `architect_coding` through `ServerURLsConfig.as_dict()`, `TimeoutsConfig.role_timeouts_dict()`, or env-backed active settings.
   - `TimeoutsConfig.for_role("architect_coding")` now falls through to the default request timeout instead of advertising a retired-role-specific value.
   - Remaining risk: compatibility aliases or legacy tests can still mention dead ports, but they should stay explicit degraded/legacy surfaces rather than active stack truth.

4. Raw launch maps can disagree with generated serving truth.
   - RESOLVED for shared aliases in `epyc-orchestrator` `d4acf24`: `/mnt/raid0/llm/epyc-orchestrator/scripts/server/stack_manifest.py` now maps `coder_escalation` and `worker_summarize` to `8070`, and `toolrunner` to `8072`, matching computed launch roles.
   - Current stack priors now keep exact per-role launch ports instead of broad shared-server NUMA port unions: for example `coder_escalation` and `worker_summarize` project only `8070`, `worker_math` and `toolrunner` project `8072/8082`, and `ingest_long_context` projects `8085/8185/8285/8385/8485`.
   - EXTENDED in `epyc-orchestrator` `40d46ea`: `validate_against_registry()` now also checks `server_mode` rows that cover launch roles through `model_role` or `shared_with`, so a stale shared worker port warns before launch.
   - EXTENDED in `epyc-orchestrator` `312b28e`: `stack_change_guard.py` now validates live stack-prior `serving.endpoint`, primary `serving.ports`, and `serving.tier` against the current computed launch manifest, catching launch-manifest changes that registry/descriptor source hashes cannot see.
   - EXTENDED in `epyc-orchestrator` `a6d1200`: generated stack priors now hash `scripts/server/stack_manifest.py` and `scripts/server/stack_numa.py`, and `stack_change_guard.py` requires those source artifacts. A launch topology/tier edit now forces stack-prior regeneration even if registry/descriptors did not change.
   - EXTENDED in `epyc-orchestrator` `dc14196`: the stack-prior compiler now treats computed launch-port sets as authoritative per role, while preserving server `slots`; `stack_change_guard.py` rejects missing launch ports and extra non-launch ports.
   - EXTENDED in `epyc-orchestrator` `7917535`: `serving.launch.entries` records each computed launch entry's port, primary role, mode, alias status, and optional NUMA instance, worker type, or vision type; `stack_change_guard.py` now compares that witness against computed `HOT_SERVERS`/`WARM_SERVERS`.
   - EXTENDED in `epyc-orchestrator` `a001017`: `serving.effective_context_tokens` and `serving.launch.requirements` now project worker model/draft paths and VL model/mmproj paths, with guard comparisons against stack-manifest launch truth.
   - EXTENDED in `epyc-orchestrator` `33c81ff`: contract v4 now adds an effective launch runtime witness under `serving.launch.runtime`, including launcher/path/runtime source hashes and guard comparison.
   - Remaining risk: descriptor-native model context/measurement gaps and hardcoded-surface cleanup still need closure; guards now catch future `PORT_MAP`, shared `server_mode` alias-port drift, generated serving endpoint/tier drift, exact serving port-set drift, launch-entry witness drift, effective-context drift, worker/VL model-path drift, effective runtime/binary/KV/flag drift, and simulated data-only workflow drift.

5. The generated contract now has explicit shape validation but remains semantically incomplete.
   - `epyc-orchestrator` `69057f3` embeds a versioned `epyc.stack_priors` contract and makes `stack_change_guard.py` reject artifacts missing required role/serving/prior fields.
   - `epyc-orchestrator` `7917535` bumps the contract to v2 and requires a structured `serving.launch` section so launch-mode witness data is no longer an optional side effect.
   - GUARDED in `epyc-orchestrator` `4ca702d`: the canonical `stack_change_pipeline.py` refuses descriptor updates when generated descriptors contain role/server conflicts, preventing a stale manual descriptor artifact from being replaced by output that misattributes alias roles to the shared runtime model.
   - RESOLVED in `epyc-orchestrator` `a7b72a9`: shared-runtime aliases with stale role-level model metadata now merge into the primary runtime descriptor instead of emitting standalone live Qwen descriptors.
   - EXTENDED in `epyc-orchestrator` `a001017`: contract v3 requires effective context plus launch requirements; candidate/non-live records still carry complete empty launch structure so consumers can validate before live-role filtering.
   - `/mnt/raid0/llm/epyc-orchestrator/orchestration/derived/stack_priors.yaml:1` is still compiled with gaps.
   - RESOLVED for architect quality in `epyc-orchestrator` `837829f`: `roles.architect_general.performance.quality_score: "2.57/3"` now compiles into regenerated `model_descriptors.yaml` and `derived/stack_priors.yaml`, projecting `quality_overall: 0.8567` for both `architect_general` and `qwen35_122b_q4km`.
   - `architect_general` / `qwen35_122b_q4km` known gaps narrowed from quality+ctx to structured ctx only.
   - `frontdoor` and `coder_escalation` record shared serving truth and memory cost correctly at lines 78-205, but still have `ctx_max` and quarter-TPS gaps.
   - `worker_general` has ik-llama launch metadata, MTP metadata, and alias bindings for `worker_math` and `toolrunner`; descriptors record ignored non-live Qwen alias metadata as known gaps rather than role/server conflicts.
   - Risk: consumers need to preserve gaps and fail closed where decision-grade priors are required.

6. The validator is finding the right problems, and the former retired-role waiver is no longer a strict-mode blocker.
   - After `03ed49f`, default `stack_change_guard.py` and `stack_change_guard.py --strict` are clean.
   - `uv run python scripts/validate/stack_change_guard.py --all-hardcoded-surfaces` still reports legacy-test and historical-doc mentions, but no production blocker waiver for `ARCHITECT_CODING`.
   - This is good machinery; it now needs continued consumer migration and generated-summary replacement so current operator guidance cannot drift.

7. q_scorer live priors now consume the generated stack-prior contract.
   - RESOLVED in `epyc-orchestrator` `e3d967a`: `orchestration/repl_memory/q_scorer.py` loads live TPS, quality, and memory priors from `orchestration/derived/stack_priors.yaml` before falling back to degraded local tables.
   - `frontdoor` and `coder_escalation` now share generated TPS/memory truth; `worker_explore` inherits worker-server TPS/memory from the live `worker_general` stack-prior record; `architect_coding` remains absent from live scorer priors.
   - Remaining risk: fallback tables are still intentionally present for degraded/offline mode and should eventually expose explicit provenance if downstream consumers need to distinguish live vs fallback scoring.

8. GraphRouter offline consumers no longer own stale live action/model rosters.
   - RESOLVED for GAT training in `epyc-orchestrator` `8cf0310`: `train_graph_router.py` loads live `LLMRole` nodes from `stack_priors.yaml` and skips benchmark/candidate roles.
   - RESOLVED for classifier/verifier extraction in `epyc-orchestrator` `1f16759`: `scripts/graph_router/action_space.py` derives live action labels from stack priors, remaps legacy replay labels into current live roles, and verifier extraction infers `n_actions` from classifier artifacts instead of a fixed `8`.
   - Remaining risk: other historical replay/offline scripts may still need explicit era labels, but the main GraphRouter extraction path no longer leaks retired live roles into new artifacts.

9. Vision ReAct serving-port routing now consumes generated serving truth.
   - RESOLVED in `epyc-orchestrator` `06ff53c`: `src/api/routes/chat_pipeline/vision_stage.py` now reads `worker_vision` and `vision_escalation` ports from `orchestration/derived/stack_priors.yaml` for multimodal ReAct calls.
   - Fallback ports remain explicitly degraded-mode only; the helper reloads the generated artifact on each call rather than caching stale ports in a long-lived API process.
   - Remaining risk: descriptors still lack native mmproj/projector fields, so launch/model-projector validation remains open.

10. AutoPilot preflight no longer owns a stale model-server health table.
   - RESOLVED in `epyc-orchestrator` `a5aaafb`: `scripts/autopilot/preflight_audit.py` now derives live model-server health targets from generated stack-prior serving endpoints and groups shared roles by health URL.
   - Fallback targets are current degraded mode only: no retired `architect_coding`, no dead `8071`, and both VL servers included.
   - Remaining risk: broader AutoPilot/system-card/operator summaries should keep moving to generated stack-prior summaries instead of manual tables.

11. AutoPilot human program guidance no longer carries dead endpoint examples.
   - RESOLVED in `epyc-orchestrator` `60733c7`: `scripts/autopilot/program.md` now tells autonomous operator sessions to derive compaction endpoints from `orchestration/derived/stack_priors.yaml` instead of copying a static target-port table.
   - Removed the stale coder `8071`, retired coding-architect `8084`, and obsolete fixed-RAM tier-demotion wording from the program prompt.
   - GUARDED in `epyc-orchestrator` `cf73ac1`: `stack_change_guard.py --all-hardcoded-surfaces` now scans `scripts/autopilot/program.md` for stale static target-port, retired-role, and fixed-RAM tier guidance, with unit fixtures proving both the stale and stack-prior-derived cases.
   - Remaining risk: generated system-card/runtime summaries are healthier, but active operator docs and historical chapters still need generated current-stack summaries or explicit historical labels.

12. Production launcher summaries no longer duplicate stale stack inventory.
   - RESOLVED in `epyc-orchestrator` `53f452c`: `scripts/server/launch_production.sh` keeps launch behavior unchanged while deriving its displayed component inventory from `scripts/server/stack_manifest.py`.
   - `--full` prints HOT launch groups from `HOT_SERVERS`; `--with-burst` prints HOT plus WARM launch groups; `--minimal` is now labelled as a legacy HOT-tier alias rather than claiming architects are excluded.
   - Help text points operators at `stack_manifest.py` and `--status` for current inventory/residency instead of carrying hardcoded RAM/model breakdowns.
   - Validation: `bash -n scripts/server/launch_production.sh`; launcher `--help`; embedded summary Python compile; stale literal search for removed role/model/RAM strings; focused `test_cli_orch.py` + `test_stack_change_guard.py` -> 25 passed; strict guard OK; all-surface guard shows no production launcher warning.

## Model-Specific Quantity Audit Matrix

| Quantity | Current state | Canonical source | Required projection / guard |
|---|---|---|---|
| q_scorer TPS, quality, memory priors | DONE in `e3d967a`: live defaults read `stack_priors.yaml`; fallback tables remain for degraded/offline mode. | `stack_priors.yaml` role `priors` with descriptor evidence and measurement status. | Follow up with explicit provenance plumbing for live vs degraded fallback scoring. |
| Seeding reward TPS/cost assumptions | DONE in `7ecf847`: `seeding_rewards.py` reads live `priors.throughput_tps`, keeps explicit override/degraded fallback for replay/tests, and no longer exports the stale baseline table. | Same stack-prior `priors.throughput_tps` plus per-role memory/admission costs. | Keep guard coverage so any future live seeding cost table or retired-role default fails. |
| Seeding scoring/architect assumptions | DONE in `5773777`: active `seeding_eval.py` enumerates live non-VL architect roles from stack priors; `seeding_scoring.py` no longer documents the retired architect split; `seeding_legacy.py` derives slow roles from current `ARCHITECT_ROLES`. | Live roles from stack priors; historical benchmark-only comparisons from research registry with non-live status. | Remaining historical/deprecated fixtures should stay explicit legacy/test-only; live benchmark defaults should keep reading stack priors. |
| Memory/admission costs | `src/api/admission.py` derives limits from stack-prior ports/slots with fallback; q_scorer memory now reads stack-prior memory cost first. | `server_mode.*.tier`, `slots`, shared mmap binding compiled into stack priors. | Add tests that frontdoor/coder_escalation share memory and admission truth; fail on role-level WARM overrides for live HOT roles. |
| Hot/warm deployment status | `server_mode` is current truth; older research docs and role metadata still mention WARM `architect_coding`/`ingest_long_context`. | Orchestrator lean registry `server_mode.*`; research registry is comprehensive evidence/candidate history only. | Compiler must preserve conflict notes and prevent non-live research rows from satisfying live deployment. |
| Context size / ctx limits | Effective launch context is now guarded in stack priors (`a001017`): frontdoor 32768, worker aliases 16384, worker_vision 8192, vision_escalation 16384, architect_general 16384, and ingest_long_context 32768. Model-native `ctx_max` remains incomplete in descriptors. | Physical descriptor `model.ctx_max` from research/lean registry, plus launch `-c` effective context from stack manifest. | Extend descriptor contract with `ctx_model_max`; strict mode blocks live consumers that need model-native context limits while null. |
| TPS, latency, reward baselines | TPS partly structured; latency/admission history lives in comments/docs; reward baselines are split across q_scorer, seeding, eval tower, and AutoPilot artifacts. | Measurement-attested descriptor evidence and stack-prior priors; historical benchmark artifacts remain provenance only. | Add provenance status fields: decision-grade, observation, gap, stale. Decision gates must require protocol/date/ref per `MEASUREMENT.md`. |
| Routing priors / role priors | `_heuristic_role_priors()` now filters through live stack priors; learned-routing handoffs/docs still contain `architect_coding` training labels. | Live role set from stack priors; learned/replay datasets must carry era labels. | Add simulated retired-role fixture proving `architect_coding` is ignored in live priors but preserved in historical replay with era metadata. |
| OpenAI-compatible model listing | `/v1/models` now derives live model IDs from stack priors plus compatibility aliases. | Stack-prior live roles. | Keep compatibility aliases separate from live role IDs; guard any static live model list. |
| Dashboard/runtime classification | Dashboard age overrides and inference lock/tap had recent cleanup; lock heavy roles and tap stream roles are still local policy tables. | Stack-prior tier/slots/model class plus explicit runtime policy hints. | Compile role policy hints or a generated runtime classification projection; local tables must be fallback/override only. |
| Launch ports and shared servers | DONE for shared aliases in `d4acf24`; active VL ReAct ports now read stack-prior serving records in `06ff53c`; shared `server_mode` alias-port drift is guarded in `40d46ea`; AutoPilot preflight health probes read stack-prior serving endpoints in `a5aaafb`; AutoPilot human program guidance now derives compaction endpoints from stack priors in `60733c7`; production launcher summaries derive HOT/WARM groups from `stack_manifest.py` in `53f452c`; stack-prior endpoint/primary-port/tier drift from the computed launch manifest is guarded in `312b28e`; stack priors now hash `stack_manifest.py`/`stack_numa.py` in `a6d1200`; exact per-role launch port sets are projected and guarded in `dc14196`; contract v2 launch-entry witness is projected and guarded in `7917535`; contract v3 effective-context and worker/VL model-path requirements are projected and guarded in `a001017`. Broader launch projection still needs binary/KV/acceleration comparison. | `server_mode` plus generated stack priors should outrank raw port maps. | Guard direct `PORT_MAP` consumers; launch/health probes and operator guidance should consume generated serving records or verified launch metadata. |
| Registry/derived YAML drift | `stack_priors.yaml` has a contract and freshness hash but is `compiled_with_gaps`; context and some quality fields remain null. | Lean registry + descriptors generated from research evidence. | One workflow command must compile descriptors/priors, sync procedure enums, run strict guard, and fail on stale generated hashes. |

## Proposed Source-Of-Truth Design

Adopt this rule for every stack/model change:

1. **Edit structured truth only.**
   - Physical model identity and measured evidence: `orchestration/model_descriptors.yaml`.
   - Live serving topology, ports, slots, tiers, shared bindings, and deployment intent: `orchestration/model_registry.yaml` `server_mode.*`.
   - Comprehensive benchmark/candidate history: `/mnt/raid0/llm/epyc-inference-research/orchestration/model_registry.yaml`; values imported from here must remain non-live until projected through orchestrator descriptors/stack priors with measurement status.
   - Temporary launch witness until fully generated: `scripts/server/stack_manifest.py` `ROLE_LAUNCH_META`.

2. **Compile exactly one consumer contract.**
   - `orchestration/derived/stack_priors.yaml` is the generated contract for model-specific consumers.
   - It must include role, model id, endpoint/ports/slots, tier/memory cost, TPS/quality/latency/reward priors with measurement provenance, model max context, effective launch context, launch binary, draft/MTP/spec settings, KV settings, modality, shared mmap group, source hashes, and known gaps.

3. **Consume through a typed API, not ad hoc YAML parsing.**
   - Add or extend a small loader, for example `src/registry/stack_priors.py` runtime helpers, so production code can ask for:
     - live roles
     - retired roles
     - role serving record
     - role scorer priors
     - role budget/policy hints
     - launch requirements
     - high-cost/lock/tap classifications
   - Tests and scripts may read YAML directly only when imports would create a cycle; they must still preserve degraded-mode warnings.

4. **Make fallback tables explicit degraded mode.**
   - Fallback constants should be named `DEGRADED_*` or `FALLBACK_*`, must exclude retired live roles unless testing legacy behavior, and must emit or return provenance that says "not live stack truth".
   - Production validators should fail if a live consumer silently accepts fallback values while stack priors are present.

5. **Require data-only simulated swaps.**
   - A model swap is not complete until fixture-based tests prove that changing registry/descriptors regenerates consumer outputs without code edits.
   - Include a retired-role fixture where `architect_coding` is removed from live stack truth and a shared-server fixture where `frontdoor`/`coder_escalation` keep one model identity, one memory owner, and distinct role IDs.

## Work Packages

### W1 - Harden the stack-prior contract and guard

Goal: make `stack_priors.yaml` complete enough to be the only model-specific consumer contract.

Tasks:

- DONE foundation in `69057f3`: add an explicit versioned contract plus structural validation for stack priors.
- Extend compiled records with missing consumer fields:
  - context window / effective max context
  - decision-grade TPS and quality status
  - launch binary path/family and runtime incompatibilities
  - draft/MTP/spec decode knobs
  - KV/cache settings
  - shared mmap group id and memory-accounting owner
  - role policy hints needed by API budgets/routing if those remain role-specific
- DONE for launch topology in `a6d1200`: stack priors now include source hashes for `scripts/server/stack_manifest.py` and `scripts/server/stack_numa.py`, and the guard requires those artifacts.
- DONE for exact launch-port projection in `dc14196`: stack priors now use computed launch role ports as the serving port set for live roles, preserve server slot metadata, and reject missing/extra port drift against the launch manifest.
- DONE for launch-entry witness in `7917535`: stack-prior contract v2 requires `serving.launch.entries`, and the guard compares generated launch mode/alias/primary-role/NUMA witness data against the computed launch manifest.
- DONE for launch-context/path witness in `a001017`: stack-prior contract v3 requires
  `serving.effective_context_tokens` and `serving.launch.requirements`; worker
  model/draft paths and VL model/mmproj paths are now generated and guarded.
- DONE for launch-runtime witness in `33c81ff`: stack-prior contract v4
  requires `serving.launch.runtime`; generated priors now witness effective
  launcher binary family/path, runtime requirements, cache/KV settings, slot
  save policy, and launch flags/spec state, and the guard compares them against
  computed launch truth.
- Add source metadata for research-registry/benchmark evidence where descriptors depend on research artifacts, not just the lean orchestrator registry and launch topology.
- DONE foundation in `e162c7c`: add an external exception allowlist for `stack_change_guard.py` with owner, category, rationale, expiry/review date, and whether the exception is live, degraded fallback, legacy test, or historical doc.
- PARTIAL in `e162c7c`: strict mode now keeps valid waived hardcoded-surface findings visible as warnings instead of promoting them to errors; unresolved descriptor/global-gap policy still needs final strict-mode tightening.

Acceptance:

- `uv run python scripts/registry/compile_stack_priors.py --allow-incomplete` preserves known gaps.
- strict mode can distinguish "blocked live consumer" from "documented fallback" without hiding either.
- changing stack manifest/NUMA launch metadata makes generated stack priors stale until regenerated.
- Adding a retired live role to a production consumer fails the guard.

### W2 - Migrate highest-risk live consumers

Goal: eliminate model-specific hardcoding from live scoring/routing/config behavior.

Priority order:

1. `scripts/benchmark/seeding_rewards.py`
   - DONE in `7ecf847`: replaced the stale TPS table with stack-prior-derived live throughput.
   - DONE in `7ecf847`: kept explicit override/degraded fallback paths for replay/offline tests without silent live fallback.
   - Treat this as a separate blast-radius pass because `compute_comparative_rewards` was previously marked CRITICAL.
   - Follow-up: wire provenance metadata if downstream injection needs to record live-prior vs override/degraded cost source.
2. `src/api/routes/chat_delegation_decision.py`
   - DONE first cleanup in `b1402a2`: removed `architect_coding` from live budget defaults.
   - Remaining follow-up: derive architect/delegation budget maps from stack-prior role policy or live architect roles instead of a local static table.
3. `src/api/routes/chat_pipeline/delegation_stage.py` and `src/api/routes/chat_pipeline/proactive_stage.py`
   - DONE cleanup in `481516c`: retired `architect_coding` no longer triggers delegated/proactive architect branch behavior.
4. `src/api/routes/chat_routing.py`
   - PARTIAL cleanup in `519f710`: removed the redundant retired-role check from `_role_to_task_type()` and added live-role mapping coverage.
   - DONE HIGH-impact follow-up in `eb4dac5`: `_heuristic_role_priors()` now reads live stack-prior role status before seeding candidate priors, with a non-retired degraded fallback.
5. `src/api/routes/openai_compat.py` and `src/api/routes/dashboard_snapshot.py`
   - DONE cleanup in `d9c053c`: OpenAI-compatible `/v1/models` now reads deployed roles from stack priors and keeps only non-retired degraded fallback roles plus aliases.
   - DONE cleanup in `1b9db81`: dashboard in-flight task age overrides no longer include retired `architect_coding`.
6. `src/config/__init__.py` and `src/config/models.py`
   - DONE in `f24eab7`: removed retired `architect_coding` from active server URL maps, role timeout maps, env-backed settings, and API import expectations.
   - Follow-up: prefer stack-prior endpoints/timeouts where possible for generated config projections, rather than maintaining parallel role maps indefinitely.
7. `src/runtime/inference_lock.py`, `src/runtime/inference_tap.py`, and `src/graph/**`
   - PARTIAL cleanup in `6bc1f51`: removed retired `architect_coding` from inference lock/tap heavy-role classifications.
   - PARTIAL cleanup in `e6e10d8`: removed retired `architect_coding` from approval-gate high-cost classification.
   - PARTIAL cleanup in `2967526`: `scripts/server/orchestrator_stack.py` now enables only live LangGraph Phase 3 node env vars and no longer sets the retired `ORCHESTRATOR_LANGGRAPH_ARCHITECT_CODING` launch flag.
   - PARTIAL cleanup in `c2b4437`: `src/parsing_config.py` no longer assigns an active parsing strategy to retired `architect_coding`, and `src/inference/llm_cache.py` no longer recommends it as a cache target.
   - DONE in `03ed49f`: `Role.ARCHITECT_CODING` now aliases live `Role.ARCHITECT_GENERAL`; legacy string routing is preserved through `_missing_` / `_LEGACY_ROLE_ALIASES`; active prompt fallback, graph node map, and prewarm special-cases no longer treat coding architect as a separate live role.
   - Remaining follow-up: derive high-cost/streaming/exclusive-role classifications from stack priors or explicit role policy.
   - Remaining LangGraph retired-role mentions should be legacy-test or historical-doc cleanup only.
8. `scripts/benchmark/seeding_eval.py`, `scripts/benchmark/seeding_scoring.py`, `scripts/benchmark/analyze_routing_policy.py`, and `scripts/benchmark/corpus_quality_gate.py`
   - DONE in `5773777`: live seeding/eval behavior now derives non-VL architect candidates from stack priors, legacy slow-role logic derives from `ARCHITECT_ROLES`, and the corpus quality gate loads current model configs from stack priors.
   - Architect comparisons enumerate live architect-like roles from stack priors and treat removed roles as legacy benchmark fixtures only.
   - DONE for `analyze_routing_policy.py` in `b5bf5eb`: specialist-utilization summary reads live stack-prior roles and the fallback excludes retired `architect_coding`.

DONE in `d6912e7`: q_scorer now exposes live/degraded provenance metadata. Follow-up, if strict promotion needs a harder failure mode, is to make selected production callers reject `PRIOR_SOURCE_DEGRADED_FALLBACK` for required live roles instead of only inspecting metadata.

Acceptance:

- `stack_change_guard.py --all-hardcoded-surfaces` production-blocker count drops materially after each pass.
- q_scorer, seeding reward costs, routing priors, admission limits, procedure role enums, and API examples all agree on the same live roles.
- `architect_coding` remains only in historical docs, retired compatibility tests, or explicit legacy fixtures.

### W3 - Build the repeatable stack-change workflow

Goal: one command sequence for safe model changes, usable by the main agent or a human operator.

Tasks:

- Add a no-inference stack-change workflow script or documented command target that runs:
  - descriptor compile/check
  - stack-prior compile/check
  - procedure enum sync check
  - stack-change guard strict mode
  - consumer snapshot tests
  - simulated model-swap tests
  - source/derived artifact freshness checks
- DONE in `d5cb80a`: descriptor freshness checks now show exact changed model IDs/field paths, generated add/remove model IDs, and top-level drift before the stale-artifact error.
- DONE in `4ca702d`: descriptor update/check paths now fail closed on generated role/server conflict gaps instead of suggesting or performing an unsafe artifact update.
- DONE in `a7b72a9`: `src/registry/model_descriptors.py` now treats `server_mode.shared_with` aliases with different role-level models as virtual aliases served by the primary runtime descriptor. The generated artifacts intentionally remove standalone live Qwen math/toolrunner descriptors while preserving alias coverage and known-gap notes. GitNexus marked `compile_model_descriptors` and `_descriptor_for_role` HIGH through the launch-adjacent stack command path, so the fix landed with focused descriptor, stack-prior, pipeline, schema, q_scorer, routing, vision, preflight, and CLI tests.
- DONE in `fb0fd6d`: add fixture-based simulated swaps:
  - shared-mmap role swap, e.g. frontdoor/coder_escalation same-GGUF group
  - worker-family swap with launch requirements, e.g. gemma4 worker MTP/ik binary
  - retired-role removal, e.g. `architect_coding`
- DONE in `837829f`: project architect quality from structured registry evidence
  into descriptors and stack priors; `architect_general` and
  `qwen35_122b_q4km` now carry `quality_overall: 0.8567` and no longer have a
  quality known gap.
- DONE in `03ed49f`: close the temporary retired-role enum production-waiver path by normalizing `Role.ARCHITECT_CODING` to live `architect_general`, preserving legacy string compatibility, and removing distinct-live-role prompt/graph/prewarm surfaces.
- Add pre-launch and post-launch gates:
  - pre-launch: strict stack-change guard must pass or require an explicit diagnostic override
  - launch: launcher consumes generated launch requirements where available
  - post-launch: running-state attestation compares live PIDs/ports/flags/binary paths against stack priors
- Generate or refresh operator-facing stack summaries from stack priors so manual docs do not become source truth.
- DONE in `53f452c` for one production wrapper: `launch_production.sh` derives its mode summary from `stack_manifest.py` instead of carrying stale model/RAM/retired-role text.

Acceptance:

- A model assignment can be changed in structured inputs, generated artifacts update, and no live consumer requires hand-editing.
- Launch refuses stale generated priors unless an explicit diagnostic override is present.
- Runtime attestation detects stale running processes after config/code changes.
- Repeating the 2026-06 `architect_coding` retirement or q_scorer-cost drift pattern is impossible without a failing guard: retired roles are absent from live priors, shared mmap roles do not double-count cost, and live cost/TPS/context consumers either read the generated contract or declare degraded fallback.

## Validation Strategy

No inference is required for W1-W3 until a later benchmark gate explicitly requests it.

```bash
cd /mnt/raid0/llm/epyc-orchestrator

python3 -m py_compile \
  src/registry/stack_priors.py \
  scripts/registry/compile_stack_priors.py \
  scripts/registry/sync_procedure_role_enums.py \
  scripts/validate/stack_change_guard.py \
  scripts/registry/compile_descriptors.py \
  src/registry/model_descriptors.py \
  orchestration/repl_memory/q_scorer.py \
  scripts/benchmark/seeding_rewards.py

uv run python scripts/registry/compile_descriptors.py --dry-run --allow-incomplete
uv run python scripts/registry/compile_stack_priors.py --allow-incomplete
python3 scripts/registry/sync_procedure_role_enums.py --check
uv run python scripts/validate/stack_change_guard.py
uv run python scripts/validate/stack_change_guard.py --all-hardcoded-surfaces
uv run python scripts/validate/stack_change_guard.py --strict

uv run --with pytest pytest -q \
  tests/unit/test_stack_priors_compiler.py \
  tests/unit/test_stack_change_guard.py \
  tests/unit/test_sync_procedure_role_enums.py \
  tests/unit/test_model_descriptors_schema.py \
  tests/unit/test_model_descriptor_compiler.py \
  tests/unit/test_q_scorer.py \
  tests/unit/test_admission.py

git diff --check
```

Use focused extra tests for each W2 consumer pass. Do not run AutoPilot or llama inference while implementing this handoff unless a later explicit benchmark/attestation step requires it.

## Non-Goals

- Do not restart AutoPilot or run inference as part of this audit handoff.
- Do not design a second registry. The point is to make descriptors, lean registry `server_mode`, stack manifest launch metadata, and generated stack priors cohere.
- Do not rewrite all historical docs. Historical references should be labeled or generated separately; production launch should not depend on them.
- Do not suppress guard findings without owner/rationale/expiry metadata.
- Do not reopen learned-routing expansion work. Routing-truth restoration remains frozen until the measured gates in the routing handoffs justify expansion.
- Do not edit master or sub-index files during implementation except in a deliberate doc-sync pass.

## Reporting Instructions

- Update this handoff when an audited failure mode is closed, reclassified, or assigned an explicit exception.
- Update `stack-change-governance-pipeline.md` only for waypoint progress and validation results.
- Keep `master-handoff-index.md`, `routing-and-optimization-index.md`, and `model-capability-descriptors.md` out of incidental edits; those have broader blast radius and should be synchronized deliberately.
- Progress notes should include exact commands, guard warning counts before/after, and whether AutoPilot/inference was paused.
