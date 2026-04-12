# Routing & Optimization — Coordination Index

**Created**: 2026-03-25
**Purpose**: Actionable entry point for agents working on routing, optimization, and stack infrastructure. Read this first — it tells you what needs doing, in what order, and where to find the details.

---

## How to Use This Index

1. **Read the outstanding tasks below** — they are ordered by priority and dependency
2. **Check the dependency graph** — some tasks unblock others
3. **Read the relevant handoff** for implementation details before starting work
4. **After completing a task**, update both the handoff AND this index (mark task done, update status)
5. **Check cross-cutting concerns** before modifying any subsystem — changes cascade

---

## Subsystem Status

| Subsystem | Handoff | Status | Next Action |
|-----------|---------|--------|-------------|
| Routing Intelligence | [`routing-intelligence.md`](routing-intelligence.md) | Phase 4 code complete (RI-2–6) | RI-1 calibration dataset + RI-7 A/B test (need compute) |
| AutoPilot / AutoResearch | [`autopilot-continuous-optimization.md`](autopilot-continuous-optimization.md) | AR-3 trial ~78 (Package D). **P10 GEPA + P11 controller upgrades queued** (2026-04-12 research intake). | P10/P11 tasks ready; AP-14–17 still pending |
| Dynamic Stack | [`dynamic-stack-concurrency.md`](dynamic-stack-concurrency.md) | Phases B-D complete (pre-warm + KV migration) | Phase E: autoresearch exploration |
| KV Cache Quantization | [`kv-cache-quantization.md`](kv-cache-quantization.md) | Hadamard deployed, TQ/PQ abandoned | Monitor upstream TurboQuant |
| Context Folding | [`context-folding-progressive.md`](context-folding-progressive.md) | Phase 0/1/1+/2c/3a/3b code complete. **Phase 2d queued** (provenance CF-P1–P4, non-inference) | Phase 2a/2b eval (→ Package C), Phase 2d provenance (→ non-inference), Phase 3c (→ Package D), Phase 2c ByteRover (design ready) |
| Conversation Management | [`orchestrator-conversation-management.md`](orchestrator-conversation-management.md) | COMPLETE (B1-B7 + integration) | All 7 modules done, 99 tests |
| LangGraph Migration | [`langgraph-migration.md`](langgraph-migration.md) | Phase 3 infra complete (7 per-node flags + dispatch + 48 tests) | Phase 3: Flip flags per node + production validation |
| CC Local Integration | [`claude-code-local-constellation-routing.md`](claude-code-local-constellation-routing.md) | Phase 0 complete (MCP chat tools, 15 tests) | Phase 1: hardening, telemetry |
| Retrain Routing Models | [`retrain-routing-models.md`](retrain-routing-models.md) | BLOCKED | Accumulate ~500+ routing memories via seeding |
| Meta-Harness Optimization | [`meta-harness-optimization.md`](meta-harness-optimization.md) | Tier 1+2 done, **Tier 2b queued** (GEPA search + Agent Lightning telemetry) | MH-4 GEPA eval, MH-5 trace collection |
| ~~Stack Audit~~ | ~~[`orchestrator-stack-audit.md`](../completed/orchestrator-stack-audit.md)~~ | ARCHIVED 2026-03-29 | Purpose fulfilled by NUMA + REAP deployments |

---

## Outstanding Tasks (Priority Order)

### P0 — Wiring Bugs (infrastructure built but not connected)

These are HIGH priority because the code exists but isn't wired up. Low effort, high value.

- [x] **AP-1: Wire `failure_context` into PromptForge dispatch** — ✅ 2026-03-29. `dispatch_action()` now extracts last 5 PromptForge failures from journal and passes `failure_context` + `per_suite_quality` to `propose_mutation()`. Also added `journal` parameter to `dispatch_action()`.

- [x] **AP-2: Feed failure narratives into controller prompt** — ✅ 2026-03-29. `summary_text()` now appends compact failure analysis (truncated to 200 chars) for failed trials. Controller can see why trials failed.

- [x] **AP-3: Populate `parent_trial` and `config_diff` journal fields** — ✅ 2026-03-29. `parent_trial` set to most recent trial from same species. `config_diff` computed as key-level delta between current and parent config_snapshot.

- [x] **RI-0: Fix Q-scorer frontdoor baseline** — ✅ 2026-03-29. Updated `baseline_tps_by_role`: frontdoor 19.6→12.7 (moe6, no lookup), architect_coding 7.0→8.0 (REAP-246B). Also updated `memory_cost_by_role` for architect_coding: 5.0→3.5 (139GB vs 271GB).

### P1 — Routing Intelligence Phase 4 (risk-aware enforcement)

Phases 0-3 built the risk scorer and put it in shadow mode. Phase 4 makes it affect routing decisions. **Prerequisite**: calibration dataset (labeled prompts with known risk levels — source from simpleqa failures + seeding diagnostics).

- [x] **RI-1: Build calibration dataset** — ✅ 2026-03-29. `build_factual_risk_calibration.py` extracts 2,000 labeled examples (1,314 high, 616 low, 70 medium) from seeding_diagnostics.jsonl (781 with eval ground truth) + question_pool.jsonl (1,219 tier-based). Output: `orchestration/factual_risk_calibration.jsonl`.

- [x] **RI-2: Cheap-first risk bypass** — ✅ 2026-03-29. `_try_cheap_first()` now returns `None` (skip) when `routing.factual_risk_band == "high"`. High-risk factual prompts go directly to normal pipeline.

- [x] **RI-3: Plan review gate risk integration** — ✅ 2026-03-29. `_plan_review_gate()` forces review when `factual_risk_band == "high"` AND `factual_risk_mode == "enforce"`, regardless of complexity heuristics.

- [x] **RI-4: Escalation policy risk-awareness** — ✅ 2026-03-29. `EscalationPolicy.decide()` triggers think-harder on FIRST failure (not penultimate retry) when `risk_band == "high"` and `risk_score > 0.5`. Early deep thinking is cheaper than multiple shallow retries.

- [x] **RI-5: Failure graph veto modulation** — ✅ 2026-03-29. Factual risk scoring moved BEFORE failure graph veto. Threshold modulated: high→0.3, medium→0.5, low→0.7 (was hardcoded 0.5). High-risk prompts trigger more conservative specialist vetoing.

- [x] **RI-6: Structured review objective** — ✅ 2026-03-29. Both progress log and MemRL episode storage now include `task_type`, `risk_band`, `verification_focus`. Feedback truncation raised from 100→200 chars.

- [x] **RI-7: A/B test Phase 4** — ✅ 2026-03-31. Ran 70 questions per arm (10/suite × 7 suites). Results: all differences NS (p > 0.4). Direct: off 61.4% vs enforce 62.9% (p=0.86). REPL: off 48.6% vs enforce 42.9% (p=0.50). Architect: off 55.7% vs enforce 52.2% (p=0.68). **Verdict**: enforce mode neither helps nor hurts at this sample size. Underpowered (70 vs target 500/arm) — re-run with larger sample recommended before rollout. Bug fixes: added `ORCHESTRATOR_FACTUAL_RISK_MODE` env var override, fixed `features().factual_risk_mode` AttributeError in routing.py.

### P2 — AutoPilot Structural Improvements

Medium priority. These improve autoresearch effectiveness before it starts running at scale.

- [x] **AP-4: `lab failures` query at species proposal time** — ✅ 2026-03-29. Added `journal.recent_failures(species, n)` method. Already wired into AP-1's PromptForge dispatch (extracts last 5 failures for the species).

- [x] **AP-5: Per-suite quality trends in controller prompt** — ✅ 2026-03-29. Added `journal.suite_quality_trend(last_n)` method returning per-suite quality over time. Added `### Suite Quality Trends` section to controller prompt template with decline/improve direction indicators.

- [x] **AP-6: Persist `_consecutive_failures` counter** — ✅ 2026-03-29. `SafetyGate.__init__()` accepts `consecutive_failures` param. Loaded from / saved to `autopilot_state.json` each trial.

- [x] **AP-7: Invalidate stale Optuna trials after regime changes** — ✅ 2026-03-29. Added `NumericSwarm.mark_epoch(reason)` + `_study_name()` with epoch suffix. Called in `dispatch_action()` after accepted prompt mutations and structural experiments. Old studies preserved for history, new studies start clean.

- [x] **AP-8: Hypothesis-mechanism tracking on JournalEntry** — ✅ 2026-03-29. Added `hypothesis: str` and `expected_mechanism: str` fields to `JournalEntry` dataclass. JSONL load/save updated. Fields available for Strategy Store retrieval.

### P3 — Routing Intelligence Phase 5 (seeding integration)

- [x] **RI-8: Add risk fields to `RoleResult`** — ✅ Verified 2026-03-29. Fields exist at `seeding_types.py:230-234` with `factual_risk_` prefix: `factual_risk_score`, `factual_risk_adjusted`, `factual_risk_band`, `factual_risk_features`. Original probe used wrong naming convention; actual implementation is correct.

- [ ] **RI-9: Threshold sweep in seeding harness** — Reuse existing `--suite` mechanism. Sweep risk thresholds and emit Pareto reports (factuality vs cost vs latency). (→ Package B, see [`bulk-inference-campaign.md`](bulk-inference-campaign.md))

### P4 — Observability Infrastructure (Dynamic Stack Phase B)

These unblock data-driven stack scheduling.

- [x] **DS-1: Instrument queue depth telemetry** — ✅ 2026-03-29. `RoundRobinBackend` now tracks per-instance active/total counts, idle instances, seconds since last request. `get_stats()` exposes all. Queue depth injected into `routing_meta` in `_route_request()`.

- [x] **DS-2: Instrument escalation rate telemetry** — ✅ 2026-03-29. `AppState.record_escalation(from, to)` tracks total escalations and per-path counts (e.g., "frontdoor→coder"). Wired into streaming chat.py (2 call sites) and graph helpers. `get_stats()` returns escalation_rate and escalations_by_path.

- [x] **DS-3: Add `--slot-save-path` to production launches** — ✅ 2026-03-29. `build_server_command()` appends `--slot-save-path <cache_dir>/kv_slots/<role>` for all roles. Per-role subdirectories created automatically.

- [x] **DS-4: Log stack state alongside routing telemetry** — ✅ 2026-03-29. `routing_meta["stack_state"]` populated from `state.registry.roles` with model name, tier, and instance count. Logged via `log_task_started()` in progress JSONL.

### P5 — AutoResearch Bootstrap (Phase A)

- [x] **AR-1: Establish debug suite baseline** — ✅ 2026-03-30. 3-way eval on 105 questions (15/suite × 7 suites). Direct 57.3%, REPL 43.1%, Architect 52.4%. Tools hurt 2.7× more than help (24 vs 9). Median pipeline latency 181s. Baseline written to `orchestration/autopilot_baseline.yaml`. Per-suite breakdown pending (output JSON lost to pipe error; re-run needed for granular data).

- [x] **AR-2: Smoke test autoresearch loop** — ✅ 2026-03-29. Dry-run 5 trials passed: journal writes (JSONL + TSV), parent_trial linkage, consecutive_failures persistence, Pareto archive, safety gate all functional. matplotlib missing (non-fatal).

- [x] **AR-3: First live autoresearch run** — Run 1 (2026-04-01): 9 wiring bugs fixed, program.md rewritten. Run 2 (2026-04-02–04): 44 trials, 6 Pareto frontier, 1 useful change (`get_direct_answer_prefix()` in resolver.py, q=3.0). **Corruption incident**: trial ~25 destroyed `escalation.py` (454→3 lines), API down 11h. Safety hardened with 5 fixes (deep validation, shrinkage guards, revert commits). **Run 3 (Package D)**: Relaunched 2026-04-11 with expanded 39-sentinel pool. Trial ~78 as of 2026-04-11. (→ Package D, see [`bulk-inference-campaign.md`](bulk-inference-campaign.md))

### P6 — Routing Intelligence Phase 6 (controlled rollout)

Depends on Phase 4 A/B results.

- [ ] **RI-10: Shadow → enforce canary** — 🔄 ACTIVE since 2026-04-06. Canary mode live: 25% enforce on frontdoor, 75% shadow. Verified 23/77 split on 100-sample test. Window extended to 2026-04-15 (was 2026-04-09) — n=16 high-risk samples insufficient for decision, need ≥50. Monitor via `delegation_slo_report.py` + `chain_anomaly_detector.py`. Decision: compare enforce vs shadow latency/accuracy/escalation rate, then RI-11 if no regression.

- [ ] **RI-11: Enforce expand** — Frontdoor 100% + worker_general, 7 days.

- [ ] **RI-12: Enforce global** — All roles. Set up monitoring dashboards.

### P7 — Dynamic Stack Implementation (Phases C-F)

Depends on observability (P4) and autoresearch baseline (P5).

- [ ] **DS-5: Autoresearch-driven model exploration** — Test frontdoor candidates, instance counts, tier assignments via autoresearch loop. See `dynamic-stack-concurrency.md` § Part 6. (→ Package D, see [`bulk-inference-campaign.md`](bulk-inference-campaign.md))

- [ ] **DS-6: Deterministic quarter scheduler** — Event-driven NUMA quarter allocation. Design doc appended to `dynamic-stack-concurrency.md` (2026-04-08). **Design audit 2026-04-09**: 6 gaps identified. **Gap resolutions 2026-04-09**: All 6 gaps resolved with concrete specs (dynamic URL API, liveness heartbeat, quarter-fixed ports, 3-phase drain protocol, idle tracking, degradation via existing retry paths). See `dynamic-stack-concurrency.md` § DS-6 Gap Resolutions. Implementation deferred to Phase F.

- [ ] **DS-7: Stack templates in orchestrator config** — Encode autoresearch findings as selectable stack profiles. **Design audit 2026-04-09**: 4 gaps identified. **Gap resolutions 2026-04-09**: All 4 gaps resolved (formal YAML template schema, `--stack-profile` CLI selection, migration paths with/without DS-6, resource validation with fail-fast). See `dynamic-stack-concurrency.md` § DS-7 Gap Resolutions. Implementation deferred to Phase F.

### P8 — AutoPilot Design Philosophy Imports

Lower priority refinements.

- [x] **AP-9: Tighter per-trial scope** — ✅ 2026-04-05. `_validate_single_variable()` in `autopilot.py` rejects multi-file prompt mutations, multi-flag structural experiments, and multi-param explicit numeric trials before dispatch.

- [x] **AP-10: Simplicity criterion for PromptForge** — ✅ 2026-03-29. After safety gate passes, checks prompt size increase >20% with quality delta <0.02 — reverts if criterion violated.

- [x] **AP-11: Git worktree isolation for PromptForge** — ✅ 2026-04-05. `worktree_manager.py` creates temp worktrees per trial. `ExperimentContext` handles apply/accept/reject with auto-reject safety default. PromptForge gains `apply_mutation_in_context()` + `apply_code_mutation_in_context()`. 5 tests.

- [x] **AP-12: Explicit eval trust boundary** — ✅ 2026-03-29. Added trust boundary table to `program.md` showing OUTSIDE (species-modifiable) vs INSIDE (immutable eval) files.

- [x] **AP-13: Grep-parseable metric output** — ✅ 2026-04-05. `EvalResult.to_grep_lines()` emits `METRIC key: value` lines. Logged after each eval in the autopilot main loop. Extract via `grep METRIC autopilot.log`.

- [x] **AP-14: Structured deficiency classification** — ✅ 2026-04-07. `DeficiencyCategory` enum (9 values) in `experiment_journal.py`. `SafetyVerdict.categories` list tags each violation. `deficiency_category` field on `JournalEntry`. Dispatch-level shrinkage/consecutive_failures via `state["_dispatch_deficiency"]` side channel.

- [x] **AP-15: Species field verification audit** — ✅ 2026-04-07. Audit found 3/5 species (Seeder, NumericSwarm, StructuralLab) produce empty `hypothesis`. Added fallback logic in main loop: species-specific hypothesis generation + `action.get("type")` as final `expected_mechanism` fallback.

- [x] **AP-16: Instruction token budget tracking** — ✅ 2026-04-07. `instruction_token_count` and `instruction_token_ratio` on `EvalResult` + `JournalEntry`. `_count_instruction_tokens()` in `eval_tower.py` scans `orchestration/prompts/*.md`. `to_grep_lines()` emits `METRIC instruction_tokens` + `METRIC instruction_ratio`. Warning at >20%. State tracks `_last_instruction_ratio` for AP-17.

- [x] **AP-17: Structural pruning in StructuralLab** — ✅ 2026-04-07. `structural_prune` action type in `dispatch_action()`. `prune_block()` method on StructuralLab removes heading-delimited sections. Acceptance: safety gate passes AND instruction_token_ratio decreases. Revert on rejection. Added to controller prompt template.

### P8b — Web Search Over-Reliance Fix (from Package B Omega audit)

Package B Phase 4 found 7/10 suites where REPL mode hurts accuracy vs direct. Root cause: the model web-searches for answers instead of reasoning. `rules.md` actively encouraged this with "Use Python computation, web_search, or llm_call to VERIFY your answer."

- [x] **WS-1: Fix tool selection guidance** — ✅ 2026-04-09. **Root cause**: `DEFAULT_ROOT_LM_RULES` in `src/prompt_builders/constants.py` (not `rules.md`) was the actual prompt. It said "when in doubt, search first" and "Use web_research for: any factual question." Replaced with priority-ordered guidance: compute → direct answer → reason → search only for genuine gaps. Also updated `rules.md` (secondary, used when `config.rules_file` is set). Arm B running with fix — preliminary check showed 100% web search before fix; monitoring for improvement.
- [ ] **WS-2: Re-run Omega measurement post-fix** — Compare direct vs REPL accuracy with updated prompts. Target: REPL ≥ direct on ≥5/10 suites (currently 2/10).
- [x] **WS-3: Cascading tool policy for web denial** — ✅ 2026-04-09. Implemented belt-and-suspenders enforcement: `NO_WEB_TASK_TYPES` constant in `tool_policy.py` (math, coder, thinking, instruction_precision). `tool_context` param added to `REPLEnvironment`. Context threaded through `_invoke_tool`/`_list_tools` → `ToolRegistry.invoke()`/`list_tools()` with `context` param. All 4 REPL creation sites (`repl_executor.py`, `stream_adapter.py`, `stages.py`) derive `no_web` from `routing.task_ir["task_type"]`. Feature flag `cascading_tool_policy` enabled by default (validated in prod). 5 new tests in `test_tool_policy.py` (32 total, all passing). **BUG FOUND 2026-04-09**: `routing.py:56` hardcoded `task_type: "chat"` so `NO_WEB_TASK_TYPES` never matched. Fixed: role→task_type derivation added after routing (worker_math→math, coder_*→coder, thinking_reasoning→thinking).

### P10 — GEPA PromptForge Integration (2026-04-12 research intake)

Source: intake-327/345/240. GEPA reflective trace analysis (ASI) + evolutionary Pareto search. 35x fewer rollouts than GRPO. Compatible with local inference. See [`autopilot-continuous-optimization.md`](autopilot-continuous-optimization.md) P10.

- [ ] **AP-18: DSPy + GEPA setup** — Install DSPy, wrap 3 routing prompts as DSPy Signatures. Non-inference. (→ also non-inference-backlog Task 10)
- [ ] **AP-19: GEPA optimize_anything on frontdoor** — ~150 evals, ~2hr inference. (→ also bulk-inference Package H)
- [ ] **AP-20: GEPA Full Program Adapter eval** — Test as PromptForge search replacement. Cross-ref: meta-harness MH-4. (→ also bulk-inference Package H)
- [ ] **AP-21: PromptForge GEPA refactor** — If AP-19/20 succeed, integrate GEPA as PromptForge backend. (→ also bulk-inference Package H)

### P11 — Autopilot Controller Upgrades (2026-04-12 research intake)

Source: intake-328/329 (MiniMax 3-component harness), intake-349 (dspy.RLM), intake-320 (RLVR). See [`autopilot-continuous-optimization.md`](autopilot-continuous-optimization.md) P11.

- [ ] **AP-22: Short-term memory per trial** — Non-inference. (→ also non-inference-backlog Task 9)
- [ ] **AP-23: Self-criticism step** — Non-inference. (→ also non-inference-backlog Task 9)
- [ ] **AP-24: Keep/revert protocol** — Non-inference. (→ also non-inference-backlog Task 9)
- [ ] **AP-25: dspy.RLM infrastructure setup** — Install dspy.RLM, configure with llama-server /v1/. Non-inference setup. (→ also non-inference-backlog Task 11)
- [ ] **AP-26: dspy.RLM integration testing** — Test benchmark analysis via REPL exploration. Needs inference. (→ also bulk-inference Package H)
- [ ] **AP-27: RLVR eval tower formalization** — Formalize T0/T1/T2 as verification functions. Needs inference for validation. Depends on P7 Ouro eval. (→ also bulk-inference Package H)

### P10b — Context Folding Phase 2d (2026-04-12 research intake)

Source: intake-316 (LTM Unsolved gap analysis: FORGETTING axis), intake-326 (MemPalace patterns). See [`context-folding-progressive.md`](context-folding-progressive.md) Phase 2d. All non-inference.

- [ ] **CF-P1: Validity timestamps** — Add `validity_timestamp` + `source_turn_ids` to ConsolidatedSegment. (→ also non-inference-backlog Task 12)
- [ ] **CF-P2: Supersession detection** — Detect when new info contradicts compacted segments. (→ also non-inference-backlog Task 13)
- [ ] **CF-P3: Metadata filtering** — Evaluate MemPalace wing/room pattern for session index. (→ also non-inference-backlog Task 14)
- [ ] **CF-P4: Hybrid raw+derived** — Test keeping raw segments for recent turns alongside compressed older ones. (→ also non-inference-backlog Task 15)

### P10c — Meta-Harness Tier 2b (2026-04-12 research intake)

Source: intake-338/345. See [`meta-harness-optimization.md`](meta-harness-optimization.md) Tier 2b.

- [ ] **MH-4: GEPA as search algorithm** — Evaluate whether GEPA's Pareto-frontier outperforms PromptForge's top-1 selection. Cross-ref: AP-20 owns implementation. Needs inference. (→ also bulk-inference Package H)
- [ ] **MH-5: Agent Lightning trace collection** — Adopt OTLP span pattern for autopilot telemetry. Non-inference infrastructure. (→ also non-inference-backlog Task 16)

### P9 — Legacy Cleanup & Operational Debt

Extracted from archived `rlm-orchestrator-roadmap.md` (Section 4, Follow-On Tasks). Independent — can be done any time.

- [x] **LC-1: Delegation SLO report** — ✅ 2026-04-04. `scripts/server/delegation_slo_report.py` parses progress JSONL logs, computes p50/p95/p99 latency, success/failure/timeout rates, delegation lineage distribution, escalation paths, per-role latency breakdown. Supports `--date`, `--from/--to`, `--json`.

- [x] **LC-2: Chain anomaly detection** — ✅ 2026-04-05. `scripts/server/chain_anomaly_detector.py` parses progress JSONL for: escalation path concentration, role concentration, failure rate, multi-hop anomaly, stale tasks, wave stalls, failure patterns. Supports `--date`, `--from/--to`, `--json`.

- [x] **LC-3: Remove `worker_code` legacy naming** — ✅ 2026-03-29. Removed from model_registry.yaml (both full and lean), orchestrator_stack.py port map, inference.py comment, 2 doc chapters. Historical benchmark JSON preserved.

- [x] **LC-4: Shared-result cache for delegation** — ✅ 2026-04-05. `delegation_cache.py` — in-memory SHA-256 keyed cache (brief+target), 1h TTL, 200 max entries. Integrated into architect delegation loop: cache check before specialist execution, store after compression. Cache hits in `delegation_diagnostics`. 10 tests.

- [x] **LC-5: Fix health probe for `full:` prefix URLs** — ✅ 2026-04-04. `_probe_core_backends()` in `health.py` now strips `full:` prefix and takes first URL from comma-separated lists before probing.

---

## Cross-Cutting Concerns

Check these before modifying any subsystem — changes in one affect the others.

### 1. Q-Scorer Baselines ↔ Stack Config
`routing-intelligence.md` § baselines defines per-role t/s used by `q_scorer.py`. If the stack changes (different models, instance counts), `baseline_tps_by_role` MUST update. ~~**Current issue**: frontdoor baseline stale (RI-0).~~ ✅ Fixed 2026-03-29 (frontdoor 19.6→12.7, architect_coding 7.0→8.0).

### 2. Routing Quality → Stack Capacity
High escalation rate from routing means more specialist instances needed. Low escalation rate means more frontdoor instances may be optimal. Routing classifier quality directly affects what the scheduler provisions.

### 3. Autoresearch Scope Includes Stack
The `program.md` governs what autoresearch can modify. Stack-config (models, instances, NUMA, tiers) is an optimization axis alongside routing params and prompts. StructuralLab species handles stack experiments.

### 4. Factual Risk → Resource Allocation
When risk-aware routing goes to enforce (RI-2 through RI-6), high-risk prompts trigger escalation to larger models. The stack scheduler must anticipate architect demand from the risk score distribution.

### 5. Conversation Logs Feed All Three
Observed patterns inform routing (Q-value training), autopilot (experiment evaluation), and stack (demand patterns, tier utilization). This mirrors episodic memory's Q-value accumulation loop.

### 6. KV Cache Config ↔ Stack Capacity
`kv-cache-quantization.md` — Hadamard + q4_0 K / f16 V is the production KV config. DS-3 (`--slot-save-path`) interacts with KV quantization config — if KV type changes, save/restore format may need updating. Dynamic stack assembly (DS-6) must account for per-model KV quantization when computing memory budgets.

### 7. Context Folding ↔ AutoResearch Baseline
`context-folding-progressive.md` Phase 0-1 (compaction trigger + two-level condensation) changes session quality behavior. The autoresearch baseline (AR-1) should be captured AFTER Phase 0-1 is deployed, or the "before" number will reflect a compaction policy that is about to change. Phase 3 process rewards feed MemRL Q-value enrichment (routing-intelligence Phase 5). **Updated 2026-04-05**: Phase 2 now includes free-zone threshold sweep and helpfulness scoring (intake-261/262); Phase 3 now includes role-aware compaction profiles that parameterize aggressiveness per orchestrator role. Phase 3b role profiles will directly affect autopilot token costs — `worker_explore` gets more aggressive compaction than `worker_coder`. **Updated 2026-04-05 (session 4)**: Phase 1+ (SegmentCache), 2c (helpfulness scoring), 3a (process rewards), 3b (CompactionProfile + CompactionQualityMonitor) all code-complete with 32 unit tests. Feature flags: `segment_cache_dedup`, `helpfulness_scoring`, `process_reward_telemetry`, `role_aware_compaction` (all off by default).
**Updated 2026-04-06**: Phase 2c ByteRover enhancement (intake-267) adds compound retention scoring (access_count, importance_score, maturity_tier with hysteresis) to `segment_helpfulness()`. Design documented in handoff. Implementation after Package C — uses Package C Δ_k ground truth for weight calibration.

### 9. Instruction Budget ↔ PromptForge Mutations
intake-272 (ETH Zurich) shows context files increase inference cost by 20%+ without improving success rates. Every PromptForge mutation that adds instructions must be evaluated against instruction overhead (AP-16). AP-17 provides the corrective mechanism — structural pruning to reduce instruction load. Agent files should target ≤400 words of toolchain-only instructions (intake-271). This constrains both `prompt_mutation` and `code_mutation` species: quality gains that come with >15% instruction overhead increase should be scrutinized.

### 10. GEPA ↔ Multiple Subsystems
`autopilot-continuous-optimization.md` P10 (GEPA PromptForge Integration) and `meta-harness-optimization.md` Tier 2b/MH-4 (GEPA as search algorithm) evaluate the same technique from two perspectives. Autopilot owns implementation (AP-18–21: DSPy signature wrapping, optimize_anything, Full Program Adapter). Meta-harness evaluates whether GEPA's Pareto-frontier selection outperforms our current top-1 selection as a search algorithm. Results from either inform the other. Source: 2026-04-12 research intake (intake-327/345/240).

### 8. Conversation Mgmt B2 ↔ Context Folding Phase 1
`orchestrator-conversation-management.md` B2 (protected-zone compression from Hermes/OpenGauss) and `context-folding-progressive.md` Phase 1 (two-level condensation) both modify session compaction behavior. They must be sequenced — context-folding Phase 1 should land first as the structural upgrade, then B2's protected-zone logic can layer on top. Alternatively, B2's tool-pair sanitization (`_sanitize_tool_pairs()`) could be extracted as a standalone prerequisite for both. **Updated 2026-04-05**: Context-folding Phase 3b (role-aware compaction profiles) must align with B2's role taxonomy — the `CompactionProfile` roles must match the conversation management role definitions. **Updated 2026-04-05 (session 4)**: `CompactionProfile` roles now defined (`architect`, `worker_coder`, `worker_explore`, `worker_fast`) with `get_compaction_profile()` in `session_log.py`. B2 can now reference these profiles directly. `segment_helpfulness()` + `prioritized_compaction()` available as building blocks for B2's protected-zone logic.

---

## Dependency Graph

```
✅ P0 (wiring bugs) ──────────── DONE (AP-1–3, RI-0)
✅ P1 (routing Phase 4 code) ─── DONE (RI-2–6). RI-1 + RI-7 need compute.
✅ P2 (autopilot structural) ─── DONE (AP-4–8, 10, 12)
✅ P4 (observability) ─────────── DONE (DS-1–4)
✅ CF Phase 0+1 ───────────────── DONE (trigger + two-level condensation)
✅ P8 (autopilot refinements) ─── DONE (AP-9, 11, 13)
✅ P9 (legacy cleanup) ────────── DONE (LC-1–5)
  │
  ├── ✅ PACKAGE A ──────────────── DONE (2026-04-06, 635 decisions, thresholds recalibrated)
  │     │                            CF Phase 1 validation + difficulty signal + RI-9 profiling + TrimR
  │     │                            Output: data/package_a/<timestamp>/
  │     │
  │     ├── ✅ PACKAGE B ────────── DONE (2026-04-10). TrimR +6pp, tool A/B +4pp, WS-3 validated, Omega measured.
  │     │     │                       RI-9 + TrimR + difficulty + Omega + tool A/B
  │     │     │
  │     │     └── PACKAGE D (active) ── AR-3 trial ~78 + RI-10 Canary (to 2026-04-15) + CF-3c + DS-5
  │     │                               AR-3 relaunched with 39 sentinels. LG Phase 3 INGEST flag not yet flipped.
  │     │
  │     ├── PACKAGE C ────────────── CF Eval Batch (~½d, individual models, independent)
  │     │                             CF Phase 2a/2b/2c
  │     │
  │     └── PACKAGE E ────────────── Vision + Hermes validation (~1h, independent)
  │
  ├── DS-C (pre-warm deploy) ──── HIGH PRIORITY. No dependencies.
  │     Add 1×96t + 4×48t instances for frontdoor/coder/worker.
  │
  ├── DS-D (concurrency router) ── Depends on DS-C.
  │
  ├── P5 (autoresearch) ──────── AR-3 relaunch = Package D.
  │
  ├── P3 (routing Phase 5) ──── depends on P1 A/B results
  │
  └── DS-E/F (templates, prediction) ── after DS-D + P5 data
```

---

## Reporting

After completing any task group, update:
1. The task checkbox in this index (mark `[x]`)
2. The relevant handoff document (update status, add implementation notes)
3. `progress/YYYY-MM/YYYY-MM-DD.md` with session summary
4. `CHANGELOG.md` if the change is significant

---

## Upstream Dependencies

This index consumes data and findings from:

| Source | Handoff | What It Provides |
|--------|---------|-----------------|
| Inference acceleration | [`inference-acceleration-index.md`](inference-acceleration-index.md) | Benchmark results, model speed/quality data, NUMA deployment findings. Stack config changes originate from acceleration work. |
| KV cache quantization | [`kv-cache-quantization.md`](kv-cache-quantization.md) | Production KV config (`--kv-hadamard -ctk q4_0 -ctv f16`), memory budget inputs for stack planning. |

Changes in upstream handoffs may invalidate assumptions in this index (e.g., model speed numbers, memory footprints). After any upstream deployment, verify RI-0 baseline and stack table in `dynamic-stack-concurrency.md`.

## Related Infrastructure

These handoffs are tracked in other indices but have cross-cutting impact here:

| Handoff | Index | Relevant Aspects |
|---------|-------|-----------------|
| [`context-folding-progressive.md`](context-folding-progressive.md) | this index | Phase 3a process rewards feed routing intelligence; Phase 3b role-aware profiles affect per-role token costs; Phases 0-2 compaction mechanics |
| [`tool-output-compression.md`](tool-output-compression.md) | research-evaluation | RTK/native hooks reduce context pressure, interacts with autopilot token costs |
| [`reasoning-compression.md`](reasoning-compression.md) | research-evaluation | TrimR/difficulty_signal shares scorer infra with factual-risk routing |
| [`bulk-inference-campaign.md`](bulk-inference-campaign.md) | this index | Packages B-E consolidate 14 inference tasks; B feeds RI-9/TrimR, D feeds AR-3/RI-10/DS-5 |
| ~~[`rlm-orchestrator-roadmap.md`](../completed/rlm-orchestrator-roadmap.md)~~ | archived | Follow-on tasks extracted to P9. |

---

## Key File Locations

| What | Where |
|------|-------|
| Factual risk scorer | `epyc-orchestrator/src/classifiers/factual_risk.py` |
| Q-scorer baselines | `epyc-orchestrator/orchestration/repl_memory/q_scorer.py` |
| Autopilot scripts | `epyc-orchestrator/scripts/autopilot/` |
| Autoresearch strategy | `epyc-orchestrator/scripts/autopilot/program.md` |
| Safety gate | `epyc-orchestrator/scripts/autopilot/safety_gate.py` |
| Classifier config | `epyc-orchestrator/orchestration/classifier_config.yaml` |
| Stack launcher | `epyc-orchestrator/scripts/server/orchestrator_stack.py` |
| Round-robin backend | `epyc-orchestrator/src/backends/round_robin.py` |
| Seeding types | `epyc-orchestrator/scripts/benchmark/seeding_types.py` |
| Model registry (full) | `epyc-inference-research/orchestration/model_registry.yaml` |
| Debug suite pool | `epyc-inference-research/benchmarks/prompts/question_pool.jsonl` |
| Model registry (lean) | `epyc-orchestrator/orchestration/model_registry.yaml` |
| KV cache config | `epyc-llama` production branch (`--kv-hadamard` flag in `orchestrator_stack.py`) |

## Research Intake Update — 2026-04-07

### New Related Research (intake-275 deep-dive)
- **[intake-275] "PufferLib 4.0"** — Not directly applicable, but deep-dive uncovered lightweight RL routing alternatives:
  - **BaRP** (arXiv:2510.07429): Lightweight policy network + bandit feedback, preference-conditioned. 16.8% better than GraphRouter at 50% less cost. Most directly applicable to our stack.
  - **PROTEUS** (arXiv:2604.00136): Lagrangian RL with explicit cost constraints. Minimizes cost subject to accuracy floor — matches our cost-aware routing philosophy.
  - **LLM Bandit** (arXiv:2502.02743): Online bandit that transfers across unseen models.
  - **Key insight**: A tiny MLP routing policy (~5-10k params, 2x64 hidden) trained via PPO on our seeding diagnostics data could replace heuristic routing rules. Sub-microsecond inference. Deploy as 50 lines of C linked into orchestrator.
  - **vs xRouter (7B)**: xRouter reads full prompt text; tiny MLP operates on pre-extracted classifier features. We already have the feature pipeline (factual_risk, difficulty_signal, keyword classification). The RL policy sits on top.
  - **Action**: Queue BaRP, PROTEUS, LLM Bandit for next intake batch. Evaluate offline RL feasibility on Package A data.
