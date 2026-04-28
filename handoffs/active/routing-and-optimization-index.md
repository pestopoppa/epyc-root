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

## Standing Comparative Context

Before proposing or revising routing/coordination architecture, read [`research/deep-dives/trinity-evolved-llm-coordinator-methodology.md`](../../research/deep-dives/trinity-evolved-llm-coordinator-methodology.md) (intake-474, ICLR 2026, Sakana AI). Trinity is the most direct prior art for the lightweight-learned-coordinator-over-heterogeneous-pool thesis we are pursuing. The deep-dive cross-checks Trinity's choices against ours on architecture, training signal, optimizer, action space, and pool composition — and lists the portable lessons (tri-role action space, sep-CMA-ES cold-start, block-ε-separability diagnostic, SVD-FT) and the non-portable ones (penultimate-token finding, frontier-closed-pool gain numbers). Reference it explicitly when arguing for a routing-architecture change so we know which Trinity lever the change does or does not echo.

**Routing/coordination design-space reference points (added 2026-04-28)**: four published systems anchor the current research landscape for learned routing and coordination heads:

- **BaRP** (intake-495, arxiv:2510.07429) — bandit-feedback training + 2-D preference-vector conditioning. **EPYC adopts patterns** at DAR-3 (motivation), DAR-4b (preference vector + cost τ), and via the routing-policy lens.
- **LLM Bandit** (intake-496, arxiv:2502.02743) — IRT score predictor + model identity vectors + IRT-stratified cold-start onboarding. **EPYC adopts patterns** at LRC P4.1.3 (P19.9, IRT feature audit), LRC P5 (P19.10, IRT-stratified cold-start), and DAR-5.
- **Trinity** (intake-474, arxiv:2512.04695) — sep-CMA-ES on a 0.6B SLM + 10K head with tri-role `(LLM, role)` action space. **EPYC tracks selectively** — tri-role architectural change (P19.1) is a real candidate; sep-CMA-ES is the realistic CPU-feasible escalation path if DAR-3/4 underdeliver.
- **Conductor** (intake-493, arxiv:2512.04388) — 7B GRPO-trained coordinator emitting `(worker_id, NL_subtask, access_list)`. **EPYC treats as competitive intelligence ONLY** (NOT a target architecture; OC-0.6 captures the comparison row, with explicit "what to learn from / what NOT to copy" framing). GPU-class architecture, out of CPU stack.

When making a routing-architecture proposal, name which of these four (and which Trinity lever from the deep-dive) the proposal echoes — and which it deliberately does not. Closure-inflation discipline applies: do not generalize "Conductor's 7B is out of scope" into "no learned coordinator could ever work" — the four systems are distinct points, not a single architecture.

---

## Subsystem Status

| Subsystem | Handoff | Status | Next Action |
|-----------|---------|--------|-------------|
| Routing Intelligence | [`routing-intelligence.md`](routing-intelligence.md) | Phase 4 code complete (RI-2–6) | RI-1 calibration dataset + RI-7 A/B test (need compute) |
| AutoPilot / AutoResearch | [`autopilot-continuous-optimization.md`](autopilot-continuous-optimization.md) | **Phase 5 seeder refactor DONE** (2026-04-17). 3-way→per-role eval. Blacklist cleaned (6→1). Model signatures in controller. AR-3 needs restart. | Restart AR-3, accumulate per-role Q-values, then route_per_role() in retriever |
| Dynamic Stack | [`dynamic-stack-concurrency.md`](dynamic-stack-concurrency.md) | Phases B-D complete (pre-warm + KV migration) | Phase E: autoresearch exploration |
| KV Cache Quantization | [`kv-cache-quantization.md`](kv-cache-quantization.md) | Hadamard deployed, TQ/PQ abandoned | Monitor upstream TurboQuant |
| Context Folding | [`context-folding-progressive.md`](context-folding-progressive.md) | Phase 0/1/1+/2c/3a/3b code complete. **Phase 2d DONE** (CF-P1–P4, 2026-04-12). | Phase 2a/2b eval (→ Package C), Phase 3c (→ Package D), Phase 2c ByteRover (design ready) |
| Conversation Management | [`orchestrator-conversation-management.md`](orchestrator-conversation-management.md) | COMPLETE (B1-B7 + integration) | All 7 modules done, 99 tests |
| LangGraph Migration | [`langgraph-migration.md`](langgraph-migration.md) | Phase 3 infra complete (7 per-node flags + dispatch + 48 tests) | Phase 3: Flip flags per node + production validation |
| ~~CC Local Integration~~ | ~~[`claude-code-local-constellation-routing.md`](../archived/claude-code-local-constellation-routing.md)~~ | ARCHIVED — superseded by Hermes outer shell | — |
| ~~Retrain Routing Models~~ | ~~(blocked handoff removed; archival pending)~~ | SUPERSEDED by Learned Routing Controller Phase 1 (2026-04-15, 157K samples, 92% val acc, flag enabled). Duplicate `active/` copy removed 2026-04-17; blocked copy no longer present. | — |
| Meta-Harness Optimization | [`meta-harness-optimization.md`](meta-harness-optimization.md) | Tier 1+2 done, MH-4 DONE (folded into AR-3), MH-5 DONE. Operator guide written. | Tier 3 outer loop rebuild (deferred) |
| Web Search Backend | [`searxng-search-backend.md`](searxng-search-backend.md) | SX-1–4 done, SX-5/6 folded into AR-3 Package D | SX-5 load test + SX-6 swap gated on AR-3 warmup |
| Decision-Aware Routing | [`decision-aware-routing.md`](decision-aware-routing.md) | NEW — 4-phase experiment (regret → contrastive → SPO+ → bilinear) | DAR-1 offline regret analysis (no code changes) |
| Learned Routing Controller | [`learned-routing-controller.md`](learned-routing-controller.md) | Phase 1 P1.1-P1.4+P1.6 DONE — 92% val acc, per-class thresholds calibrated | P1.5 enable flag, Phase 1.5 logit probe |
| Environment Synthesis (5th species) | [`agent-world-env-synthesis.md`](agent-world-env-synthesis.md) | NEW 2026-04-22 — stub/in-planning; Phase 1 training-free, Phase 2 GPU-gated (intake-444, DD6) | AW-1: scaffold `env_synth/` module |
| Deep Research Mode | [`minddr-deep-research-mode.md`](minddr-deep-research-mode.md) | NEW 2026-04-22 — stub/in-planning; Phase 1 prompt-level, Phase 2 GPU-gated (intake-438, DD7) | MD-1: `deep_research_mode` feature flag |
| Tri-Role Coordinator | [`tri-role-coordinator-architecture.md`](tri-role-coordinator-architecture.md) | NEW 2026-04-26 — stub; Trinity-derived (intake-474, ICLR 2026); architectural change orthogonal to optimizer choice; +5–8 points in Trinity ablation | TR-1.1: audit existing role-bearing fields and produce {T, W, V} mapping table |
| Outer-Coordinator Learned Head | [`outer-coordinator-learned-head.md`](outer-coordinator-learned-head.md) | NEW 2026-04-26 — SCOPING ONLY (Trinity-derived, intake-474); speculative long-term replacement of part of the Claude-driven autopilot loop | OC-0: scoping document — gated until tri-role + DAR + LRC Phase 4 land |
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

- [ ] **RI-10: Shadow → enforce canary** — 🔄 ACTIVE since 2026-04-06. Canary mode live: 25% enforce on frontdoor, 75% shadow. Verified 23/77 split on 100-sample test. Window extended to 2026-04-27 (was 2026-04-09) — n=16 high-risk samples insufficient for decision, need ≥50. Monitor via `delegation_slo_report.py` + `chain_anomaly_detector.py`. Decision: compare enforce vs shadow latency/accuracy/escalation rate, then RI-11 if no regression.

- [ ] **RI-11: Enforce expand** — Frontdoor 100% + worker_general, 7 days.

- [ ] **RI-12: Enforce global** — All roles. Set up monitoring dashboards.

### P7 — Dynamic Stack Implementation (Phases C-F+)

Depends on observability (P4) and autoresearch baseline (P5). **Phase F now includes KVCOMM cross-instance KV sharing** (intake-352, NeurIPS'25) for homogeneous worker pools — see `dynamic-stack-concurrency.md` § Phase F.

> **Ownership note (2026-04-17)**: This handoff has dual relevance. Phases B-E (stack exploration, QuarterScheduler, templates, autoresearch) are routing-and-optimization concerns owned here. **Phase F (KVCOMM F1-F4) is inference-acceleration-adjacent** — it compounds with AM compaction L4b and affects cross-NUMA cache coherence. Phase F status is cross-listed in `inference-acceleration-index.md` landscape table for discoverability. Single source of truth remains this file + the underlying handoff.

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

- [x] **AP-18: DSPy + GEPA setup** — ✅ 2026-04-12. `dspy>=2.5.0` in pyproject.toml. `src/dspy_signatures/` with 3 signatures + config. 8 tests.
- [x] **AP-19: GEPA frontdoor optimization** — ✅ Folded into AR-3 Package D (2026-04-12). `gepa_optimizer.py` adapter + `gepa` mutation type in PromptForge (30% of trials). 10 integration tests.
- [x] **AP-20: GEPA Full Program Adapter eval** — ✅ Folded into AR-3 Package D (2026-04-12). Resolved by comparing GEPA vs LLM mutation acceptance rates in AR-3 journal.
- [ ] **AP-21: PromptForge GEPA refactor** — Conditional on AR-3 data. If GEPA dominates Pareto frontier → increase ratio to 100%.

### P11 — Autopilot Controller Upgrades (2026-04-12 research intake)

Source: intake-328/329 (MiniMax 3-component harness), intake-349 (dspy.RLM), intake-320 (RLVR). See [`autopilot-continuous-optimization.md`](autopilot-continuous-optimization.md) P11.

- [x] **AP-22: Short-term memory per trial** — ✅ 2026-04-12. `short_term_memory.py` (4-section markdown, token-budgeted, CLI reset).
- [x] **AP-23: Self-criticism step** — ✅ 2026-04-12. `self_criticism.py` (rule-based, no inference cost).
- [x] **AP-24: Keep/revert protocol** — ✅ 2026-04-12. 3 new JournalEntry fields, wired into controller loop.
- [x] **AP-25: dspy.RLM infrastructure setup** — ✅ 2026-04-12. `configure_rlm()` in config.py, `test_connection()` health check.
- [ ] **AP-26: dspy.RLM integration testing** — Test benchmark analysis via REPL exploration. Needs inference. (→ also bulk-inference Package H)
- [ ] **AP-27: RLVR eval tower formalization** — Formalize T0/T1/T2 as verification functions. Needs inference for validation. Depends on P7 Ouro eval. (→ also bulk-inference Package H)

### P10b — Context Folding Phase 2d (2026-04-12 research intake)

Source: intake-316 (LTM Unsolved gap analysis: FORGETTING axis), intake-326 (MemPalace patterns). See [`context-folding-progressive.md`](context-folding-progressive.md) Phase 2d. All non-inference.

- [x] **CF-P1: Validity timestamps** — ✅ 2026-04-12. Fields + serialization + all 3 creation sites populated.
- [x] **CF-P2: Supersession detection** — ✅ 2026-04-12. `check_supersession()` with 8 regex patterns.
- [x] **CF-P3: Metadata filtering** — ✅ 2026-04-12. `topic_tags` + `_extract_topic_tags()` (7 categories).
- [x] **CF-P4: Hybrid raw+derived** — ✅ 2026-04-12. `is_raw` field, serialization ready. Raw window logic pending production wiring.

### P10c — Meta-Harness Tier 2b (2026-04-12 research intake)

Source: intake-338/345. See [`meta-harness-optimization.md`](meta-harness-optimization.md) Tier 2b.

- [x] **MH-4: GEPA as search algorithm** — ✅ Folded into AR-3 Package D (2026-04-12). GEPA integrated as PromptForge mutation type. Journal collects Pareto frontier contributions by mutation source.
- [x] **MH-5: Agent Lightning trace collection** — ✅ 2026-04-12. `telemetry.py` with TelemetryCollector, TransitionRecord, OTLP spans, JSONL export.

### P12 — SearXNG Search Backend (2026-04-14 research intake)

Source: intake-359/360/361. Replaces DDG HTML scraping + Brave fallback in `search.py` (lines 31-142) with self-hosted SearXNG JSON API. Independent workstream — no data gate, no inference dependency. Composes with ColBERT reranker S5 (richer snippets with `engines[]`/`score` metadata). See [`searxng-search-backend.md`](searxng-search-backend.md).

- [x] **SX-1: Docker container deployment** — ✅ 2026-04-14. SearXNG in `DOCKER_SERVICES` (port 8090). Config: `config/searxng/settings.yml`.
- [x] **SX-2: `_search_searxng()` implementation** — ✅ 2026-04-14. JSON API backend in `search.py` with DDG fallback.
- [x] **SX-3: Engine tuning** — ✅ 2026-04-14. Google inactive, DDG/Brave/Wikipedia/Qwant weighted, per-engine timeout 3.0s.
- [x] **SX-4: `unresponsive_engines[]` telemetry** — ✅ 2026-04-14. Logged on every call with failures.
- [ ] **SX-5: Load test** — Folded into AR-3 Package D Phase 6b. Web_research sentinel suite (50q) validates under real query patterns.
- [ ] **SX-6: Swap default** — Feature flag `ORCHESTRATOR_SEARXNG_DEFAULT=1` ready. Gated on AR-3 warmup trial. See bulk-inference-campaign.md Phase 6b.

### P13 — Decision-Aware Q-Scorer Routing (2026-04-14 deep-dive research)

Source: intake-366 deep-dive. Diagnosed pathology: difficulty signal has zero predictive spread (P0 validation). Current Q-scorer uses predict-then-optimize (TD-learn Q-values, argmax). Decision-aware learning aligns training with routing DECISIONS. Our N=3-5 routing is trivially tractable — SPO+ is convex with closed-form gradients, no RL infrastructure needed. See [`decision-aware-routing.md`](decision-aware-routing.md).

- [x] **DAR-1: Offline regret analysis** ✅ 2026-04-15 — Replay logged decisions, compute regret = Q(best) - Q(chosen). Result: 96% uniform Q-values (near-zero predictive spread confirmed). No code changes needed.
- [x] **DAR-2: Contrastive Q-score update** ✅ 2026-04-15 — ~50 lines in `q_scorer.py`. Pairwise ranking loss + `_compute_contrastive_adjustment()`. Modified `_compute_reward()` + `update_q_value()`. Unit test deferred.
- [ ] **DAR-3: SPO+ with exploration** — ~100 lines. Convex surrogate loss + 10% epsilon-greedy exploration in `retriever.py` L225-368 for counterfactual data. Blocks on DAR-2 Q-signal validation. **2026-04-28 motivation note added (intake-495)**: BaRP frames this as the train/test mismatch fix — DAR-3 adopts the bandit-feedback rationale with a convex surrogate loss instead of REINFORCE.
- [ ] **DAR-4: Model-feature-conditioned Q** — ~200 lines. Bilinear scorer replacing per-action Q-tables. Zero cold-start for new models. New `bilinear_scorer.py` module.
- [ ] **DAR-4b: Inference-time preference vector + cost scaling τ** (NEW 2026-04-28, from intake-495 BaRP) — ~50–100 lines, 1–2 sessions. 2-D preference vector `ω = (ω_perf, ω_cost)` modulating the trained DAR-4 bilinear scorer at inference WITHOUT retraining. Cost scaling τ as runtime knob. Per-tenant or per-task ω override. Independent of DAR-4 if DAR-4 slips — applies to existing per-action Q-table too. See `decision-aware-routing.md` DAR-4b.
- [ ] **DAR-5: IRT-augmented prompt features + learned model identity vectors** (NEW 2026-04-28, from intake-496 LLM Bandit) — ~150 lines, 3–5 sessions, conditional on DAR-4. Replaces hard-coded model-feature specs with end-to-end learned model identity vectors; augments prompt embedding with IRT (latent_difficulty, latent_discrimination). Decision gate: ≥ 2-pt val acc improvement to promote. See `decision-aware-routing.md` DAR-5.
- **Future routing signal (2026-04-15 deep-dive)**: intake-378 identifies branching density (Propose step ratio) as a runtime quality signal. High branching = unproductive exploration. 21pp generalization gap on Llama3.1-8B from reasoning pattern quality alone. Could feed DAR-4 bilinear scorer as a prompt/output feature: branch-heavy outputs warrant stronger models. Implementation: `quality_detector.py` branching density (see `routing-intelligence.md`). Cross-ref: `research/deep-dives/sft-generalization-reasoning-patterns.md`.

### P14 — AutoPilot Iteration Strategy Upgrade (2026-04-20 deep-dive synthesis)

Source: intake-413 (HCC), intake-414 (Token Savior), intake-415 (Context Mode). Synthesis deep dive: `research/deep-dives/autopilot-iteration-strategy-synthesis.md`. See [`autopilot-continuous-optimization.md`](autopilot-continuous-optimization.md) for full context.

4-phase improvement plan for AutoPilot knowledge accumulation, retrieval quality, and context budget management. Phase 1 is directly implementable from the synthesis document.

- [ ] **AP-28: Strategy Memory Upgrade** — ~200 LoC changes to `strategy_store.py`. Add FTS5 parallel index + RRF fusion, content-hash staleness detection (hash model_registry + prompts), Bayesian validity tracking. Zero-downtime schema migration.
- [ ] **AP-29: Knowledge Distillation Pipeline** — ~300 LoC new `knowledge_distiller.py`. L1→L2→L3 tier promotion every 25 trials. Embedding-based clustering + MDL consolidation. Convention promotion when 3+ species agree.
- [ ] **AP-30: Controller Context Budget** — ~150 LoC changes to `autopilot.py` + `eval_tower.py`. Fixed token budgets per controller prompt section. Progressive disclosure for strategy injection. 5KB threshold gating on eval output.
- [ ] **AP-31: Mutation Knowledge Graph** — ~200 LoC enhancement to `prompt_forge.py`. Track mutation_type × failure_pattern × outcome triples. Enable informed crossover from Pareto-best prompt sections.

### P16 — Strategy Store + PromptForge Safety (2026-04-22 research intake deep-dive)

Source: intake-425 (Memory Transfer Learning, arXiv:2604.14004). Deep dive confirms 4 adoptable patterns for autopilot strategy_store and PromptForge mutation safety. See [autopilot-continuous-optimization.md](autopilot-continuous-optimization.md) Research Intake Update 2026-04-21.

- [ ] **AP-32: Insight format for strategy_store entries** — Adopt the `(title, description, generalized_content)` format with no task-specific implementation details for new strategy_store entries. Audit existing entries for over-specificity. Task-agnostic insights outperform task-specific by +1.1%. ~50 LoC in `strategy_store.py`. Validates HCC L3 upgrade path (AP-29).
- [ ] **AP-33: Negative transfer safety gates for PromptForge** — Implement 3 mutation safety checks based on negative transfer taxonomy: (1) domain-mismatched anchoring detector (reject mutations that import patterns from mismatched benchmark suites), (2) false validation confidence flag (warn when mutation success is based on <5 trials), (3) misapplied best-practice filter (reject mutations that generalize suite-specific patterns). ~100 LoC in `prompt_forge.py` safety section.
- [ ] **AP-34: Validate N=3 embedding retrieval** — Confirm that our FAISS top-3 cosine retrieval matches or exceeds any LLM-based reranking we might consider. Paper shows: embedding similarity (0.630 avg) > LLM reranking (0.598) > adaptive rewriting (0.608). Run ablation: top-1 vs top-3 vs top-5 on next AR-3 run. Zero code changes — configuration experiment via autopilot.

### P17 — Environment Synthesis Species (2026-04-22 deep-dive integration, DD6)

Pointer — full plan tracked in [`agent-world-env-synthesis.md`](agent-world-env-synthesis.md). Phase 1 is training-free and CPU-feasible today; Phase 2 is GPU-gated (post-DGX-Spark). Makes env-synth the 5th autopilot species (alongside Seeder/NumericSwarm/PromptForge/StructuralLab), providing a concrete Tier 3 outer-loop rebuild recipe for meta-harness.

- [ ] **P17 rollup**: see `agent-world-env-synthesis.md` AW-1..AW-9 — entry points: AW-1 (`env_synth/` module scaffold), AW-6 (48h arena bootstrap).

### P18 — Deep Research Mode (2026-04-22 deep-dive integration, DD7)

Pointer — full plan tracked in [`minddr-deep-research-mode.md`](minddr-deep-research-mode.md). Phase 1 prompt-level three-agent pipeline (Planning/DeepSearch/Report) is zero-infra and falsifiable under existing eval tower. Phase 2 adds the paper's four-stage RL recipe (SFT → Search-RL → Report-RL → preference alignment) post-DGX-Spark. Phase 3 conditionally refactors the orchestrator's Tier-B architect split.

- [ ] **P18 rollup**: see `minddr-deep-research-mode.md` MD-1..MD-14 — entry points: MD-1 (`deep_research_mode` feature flag), MD-6 (pydantic_graph flow), MD-7 (multi-dimensional rubric — hands off to `eval-tower-verification.md` EV-9).

### P19 — Trinity-Derived Coordinator/Routing Tasks (2026-04-26 deep-dive integration)

Source: deep-dive [`research/deep-dives/trinity-evolved-llm-coordinator-methodology.md`](../../research/deep-dives/trinity-evolved-llm-coordinator-methodology.md) on intake-474 (TRINITY: An Evolved LLM Coordinator, ICLR 2026, Sakana AI). Trinity is the most direct prior art for our lightweight-learned-coordinator-over-heterogeneous-pool thesis. The deep-dive cross-checks Trinity's design choices against ours and produces nine portable lessons. **Standing reference**: link the deep-dive when arguing for any routing-architecture change so we know which Trinity lever the change does or does not echo.

These tasks live across multiple handoffs. This section is the index roll-up — for implementation detail, follow the linked handoff phases.

**Architectural change (orthogonal to optimizer)**:

- [ ] **P19.1**: TR-1 through TR-5 in [`tri-role-coordinator-architecture.md`](tri-role-coordinator-architecture.md). Add per-call role axis (Thinker/Worker/Verifier) to routing decisions. Trinity ablation: removing tri-role costs −5 to −8 points across all four benchmarks; second-largest ablation effect after the feature-position swap. TR-1 (taxonomy + open questions) is a hard gate before TR-2+. **Independent of any optimizer work** — can ship under SFT, contrastive Q-update, or sep-CMA-ES alike.

**Methodology audits on Learned Routing Controller**:

- [ ] **P19.2**: P4.1 in [`learned-routing-controller.md`](learned-routing-controller.md). Feature-extraction position audit (BGE CLS vs mean-pool vs last-layer). Cheapest of the four LRC Phase 4 tasks; informs whether our 1031-dim input vector is well-chosen.
- [ ] **P19.3**: P4.2 in [`learned-routing-controller.md`](learned-routing-controller.md). Block-ε-separability diagnostic on our routing landscape (full-rank vs block-diagonal-10 vs diagonal head). Tells us whether Trinity's optimizer-choice argument applies to our problem geometry. **Gates P19.5** (sep-CMA-ES spike).
- [ ] **P19.4**: P4.3 in [`learned-routing-controller.md`](learned-routing-controller.md). SVD-scale fine-tuning trial on BGE backbone (~9K extra params, claimed +3-4 points in Trinity's ablation). Cheaper than LoRA, applicable independent of all other Phase 4 work.
- [ ] **P19.5**: P4.4 in [`learned-routing-controller.md`](learned-routing-controller.md). sep-CMA-ES cold-start spike for routing surfaces lacking episodic labels. Population λ≈45, m=16, ≈10h overnight at 32-way concurrency for feasibility test. **Prerequisites**: P19.3 (block-ε diagnostic favourable) + Math-Verify adoption (cross-cutting concern #13) so eval-tower can serve as fitness oracle.

**Methodology audit on Decision-Aware Routing**:

- [ ] **P19.6**: DAR-1.5 in [`decision-aware-routing.md`](decision-aware-routing.md). REINFORCE-pathology audit — analytical, no code. Trinity's REINFORCE collapse (0.253 vs 0.615 LCB) raises the question of whether DAR-3/DAR-4 gradients share the same off-block-noise weakness on a block-ε-separable loss. 1 session of work. Cross-references P19.3 — together they answer "does Trinity's optimizer argument transfer to us?" with both empirical (P19.3) and analytical (P19.6) evidence.

**Documentation update**:

- [ ] **P19.7**: Update [`epyc-inference-research/docs/chapters/08-cost-aware-rewards.md`](/mnt/raid0/llm/epyc-inference-research/docs/chapters/08-cost-aware-rewards.md) to add a fourth methodological class — *ES-trained routers* — alongside RL-trained (xRouter / Router-R1), preference-trained (RouteLLM), and matrix-factorization. Trinity is the canonical citation. Cite intake-474 and the 21.9% mean error-reduction headline (caveat: heterogeneous-pool-specific). Doc edit; no code.

**Speculative scoping**:

- [ ] **P19.8**: OC-0 in [`outer-coordinator-learned-head.md`](outer-coordinator-learned-head.md). Scoping document for whether a learned-head replacement of part of the Claude-driven autopilot loop is worth pursuing. Speculative; gated until tri-role + DAR + LRC Phase 4 land. **Six sub-tasks** (OC-0.1–0.6 — OC-0.6 added 2026-04-28: design-space-reference table populating Conductor (intake-493) + Trinity (intake-474) rows as **competitive intelligence**, NOT target architectures, per user feedback) to produce a written scope before any implementation phases are even drafted.

**Bandit-feedback / IRT cold-start routing (intake-495/496 derived, NEW 2026-04-28)**:

- [ ] **P19.9**: LRC P4.1.3 in [`learned-routing-controller.md`](learned-routing-controller.md). Bundle an IRT-feature variant into the P4.1 feature-position audit. Train a quick IRT score predictor over BGE pooled output that emits `(latent_difficulty, latent_discrimination)` per prompt; include as a 4th variant alongside BGE-CLS / BGE-mean / BGE-last. Decision gate: ≥1 pt val-acc improvement → escalate to a separate phase plan (cross-link to DAR-5). Bundled with P4.1 — +1 session, no separate ablation infrastructure. Source: intake-496 (LLM Bandit).
- [ ] **P19.10**: LRC Phase 5 in [`learned-routing-controller.md`](learned-routing-controller.md). IRT-stratified cold-start onboarding. P5.1 (IRT discrimination scorer, ~80–100 LoC, ~2 sessions) + P5.2 (cold-start A/B re-onboarding existing specialist with 50 IRT-stratified prompts vs on-disk full sweep, ~70 LoC harness, 1 session) + P5.3 (conditional production rollout if P5.2 passes). Decision gate: ≤ 5% relative error on each baseline feature AND ≥ 5× faster than full sweep wall-clock. **This is the most actionable single experiment from intakes 495/496** — if it passes, every future model swap compresses from a multi-hour sweep to a ~30-minute calibration. Source: intake-496 (LLM Bandit).
- Pointer: DAR-4b and DAR-5 (intake-495/496 patterns adopted at the Q-scorer layer) are tracked at P13 above, not duplicated here.

**Dependency chain summary**:

```
P19.7 (chapter doc)         ──independent──
P19.4 (SVD-FT trial)        ──independent──
P19.2 (feature-position)    ──independent──
P19.6 (DAR-1.5 audit)       ──independent──, but P19.3 result strengthens its conclusions
P19.3 (block-ε diagnostic)  ──gates P19.5──
P19.5 (sep-CMA-ES spike)    ──needs P19.3 favourable + Math-Verify adoption──
P19.1 (tri-role TR-1..5)    ──independent of all P19.2-6, can run in parallel; TR-1 is its own hard gate──
P19.8 (outer-coord scoping) ──gated until tri-role + DAR + LRC Phase 4 all land──
```

**Recommended execution order** (by cheapness × informativeness):
1. P19.6 (DAR-1.5 audit — 1 session, analytical)
2. P19.2 (feature-position audit — 1 session, single training run)
3. P19.7 (chapter update — 1 session, doc only)
4. P19.4 (SVD-FT trial — moderate, 2-3 sessions)
5. P19.3 (block-ε diagnostic — moderate, 3-5 sessions)
6. P19.1 (tri-role TR-1 scoping in parallel — start anytime)
7. Conditional on above: P19.5 (sep-CMA-ES spike if P19.3 favourable + Math-Verify shipped)
8. Long-term: P19.1 TR-2..5 (after TR-1 review)
9. Speculative: P19.8 (only after the above land and reveal pain points)

### P15 — Parallel Seeding via NUMA Quarter Isolation (merged 2026-04-21 from `parallel-seeding-eval.md`)

Independent workstream — 2× AR-3 throughput by running 2 concurrent eval streams on dedicated port sets. No contention, no changes to existing seeding scripts, no inference dependency on implementation side. **Cross-ref**: `non-inference-backlog.md` NIB2-12 (implementation) and NIB2-29 (port-doc update).

**Problem**: AR-3 evaluates questions sequentially through the 3-way pipeline. With 192 CPU threads and 30 model servers, seeding utilization is ~13%. Each trial takes 20-40 minutes. Quarter instances (8180-8381) receive zero traffic from seeding.

**Design**: Run 2 concurrent eval streams (not 4 — architect_general and architect_coding each have only 2 instances).

| Stream | frontdoor | coder | worker | architect_gen | architect_code |
|--------|:---------:|:-----:|:------:|:-------------:|:--------------:|
| A | 8080 | 8081 | 8082 | 8083 | 8084 |
| B | 8180 | 8181 | 8182 | 8183 | 8184 |

**New files** (existing scripts untouched):

| File | Purpose |
|------|---------|
| `scripts/benchmark/parallel_seeding.py` | NEW — parallel orchestrator. Imports from existing seeding_eval/orchestrator. Splits questions across 2 streams. ThreadPoolExecutor(2). Thread-safe checkpoint. |
| `scripts/benchmark/seeding_port_sets.py` | NEW — port set definitions (STREAM_A, STREAM_B). |

**Key details**:
- Pass `server_urls` dict in ChatRequest to pin each stream to its port set (field already exists)
- Scope slot erasure to stream's own ports only
- Thread lock around checkpoint JSONL writes
- Ingest (1 instance, 8085) could contend — rare in seeding, acceptable

**Expected impact**: 2× throughput (10-20 min trials instead of 20-40). Same quality/speed measurements (no cross-stream contention). Fallback: use original `seed_specialist_routing.py` if anything breaks.

**Deferred**: 4-stream parallelism — requires adding 3rd/4th architect instances on remaining NUMA quarters.

- [ ] **PS-1: Implement `parallel_seeding.py` + `seeding_port_sets.py`** — ~200 LoC total. Tracked as NIB2-12 in non-inference-backlog.
- [ ] **PS-2: Update `orchestrator_stack.py` port docs** — reflect 8080-8084 / 8180-8184 stream split once PS-1 lands. Tracked as NIB2-29.

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

**Operationalized 2026-04-25**: [`unified-trace-memory-service.md`](unified-trace-memory-service.md) (stub) collapses `agent_audit.log` + `progress/` + `autopilot_journal.{tsv,jsonl}` + `autopilot_state.json` into a single SQLite query layer for cross-source provenance queries during autopilot debugging and post-nightshift analysis. **Not** a replacement for autopilot's evolutionary memory (`repl_memory/strategy_store.py`, episodic store, skill bank) or Hermes's conversation memory — those remain domain-specific. Cross-link: include `trial_id` in both the unified store and `strategy_store` so an insight can link back to its source events.

### 6. KV Cache Config ↔ Stack Capacity
`kv-cache-quantization.md` — Hadamard + q4_0 K / f16 V is the production KV config. DS-3 (`--slot-save-path`) interacts with KV quantization config — if KV type changes, save/restore format may need updating. Dynamic stack assembly (DS-6) must account for per-model KV quantization when computing memory budgets.

### 7. Context Folding ↔ AutoResearch Baseline
`context-folding-progressive.md` Phase 0-1 (compaction trigger + two-level condensation) changes session quality behavior. The autoresearch baseline (AR-1) should be captured AFTER Phase 0-1 is deployed, or the "before" number will reflect a compaction policy that is about to change. Phase 3 process rewards feed MemRL Q-value enrichment (routing-intelligence Phase 5). **Updated 2026-04-05**: Phase 2 now includes free-zone threshold sweep and helpfulness scoring (intake-261/262); Phase 3 now includes role-aware compaction profiles that parameterize aggressiveness per orchestrator role. Phase 3b role profiles will directly affect autopilot token costs — `worker_explore` gets more aggressive compaction than `worker_coder`. **Updated 2026-04-05 (session 4)**: Phase 1+ (SegmentCache), 2c (helpfulness scoring), 3a (process rewards), 3b (CompactionProfile + CompactionQualityMonitor) all code-complete with 32 unit tests. Feature flags: `segment_cache_dedup`, `helpfulness_scoring`, `process_reward_telemetry`, `role_aware_compaction` (all off by default).
**Updated 2026-04-06**: Phase 2c ByteRover enhancement (intake-267) adds compound retention scoring (access_count, importance_score, maturity_tier with hysteresis) to `segment_helpfulness()`. Design documented in handoff. Implementation after Package C — uses Package C Δ_k ground truth for weight calibration.

### 9. Instruction Budget ↔ PromptForge Mutations
intake-272 (ETH Zurich) shows context files increase inference cost by 20%+ without improving success rates. Every PromptForge mutation that adds instructions must be evaluated against instruction overhead (AP-16). AP-17 provides the corrective mechanism — structural pruning to reduce instruction load. Agent files should target ≤400 words of toolchain-only instructions (intake-271). This constrains both `prompt_mutation` and `code_mutation` species: quality gains that come with >15% instruction overhead increase should be scrutinized.

### 10. GEPA ↔ Multiple Subsystems
`autopilot-continuous-optimization.md` P10 (GEPA PromptForge Integration) and `meta-harness-optimization.md` Tier 2b/MH-4 (GEPA as search algorithm) evaluate the same technique from two perspectives. Autopilot owns implementation (AP-18–21: DSPy signature wrapping, optimize_anything, Full Program Adapter). Meta-harness evaluates whether GEPA's Pareto-frontier selection outperforms our current top-1 selection as a search algorithm. Results from either inform the other. Source: 2026-04-12 research intake (intake-327/345/240).

### 11. SearXNG Backend ↔ Web Search Pipeline (P8b)
`searxng-search-backend.md` replaces the DDG/Brave scraping layer that P8b's WS-1/WS-2/WS-3 fixes operate on. SearXNG is orthogonal to prompt-level over-reliance fixes but changes the search result quality and metadata available to the pipeline. When SearXNG is deployed: (a) WS-2 Omega re-measurement should use SearXNG results, not DDG HTML, (b) `unresponsive_engines[]` telemetry feeds the same monitoring pipeline as DS-1 queue depth. Source: 2026-04-14 research intake (intake-359/360/361).

### 12. Decision-Aware Routing ↔ Difficulty Signal ↔ AP-27
`decision-aware-routing.md` P13 addresses the zero-predictive-spread pathology diagnosed in Package B Phase 4 (research-eval P0). If contrastive Q-scoring (DAR-2) resolves the flat-band problem, `difficulty_signal.py` may become useful as a routing feature again. DAR-4 (model-feature-conditioned Q) interacts with AP-27 (RLVR eval tower) because the verification framework must evaluate the new routing reward signal. Source: 2026-04-14 deep-dive research (intake-366).

### 13. Math-Verify Ground Truth ↔ Decision-Aware Routing
intake-377 (2026-04-15 deep-dive) shows exact-match scoring underestimates math model capability by ~66% (Math-Verify accuracy 0.1328 vs lm-eval-harness 0.0802). DAR-3/DAR-4 reward signals in `decision-aware-routing.md` derive from eval tower scoring. If Q-scorer trains on exact-match rewards that systematically undercount correct math answers, Q-values will be biased toward models producing parseable outputs, not correct ones. Math-Verify must be adopted in the scoring pipeline before DAR-3 SPO+ training begins. See `eval-tower-verification.md` Research Intake Update 2026-04-15 for integration caveats (NOT symmetric, NOT thread-safe). Deep dive: `research/deep-dives/math-verify-integration-analysis.md`.

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
  │     │     └── PACKAGE D (active) ── AR-3 trial ~78 + RI-10 Canary (to 2026-04-27) + CF-3c + DS-5
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
| [`searxng-search-backend.md`](searxng-search-backend.md) | standalone | Web search backend replacement; affects P8b search pipeline and ColBERT reranker input |
| [`decision-aware-routing.md`](decision-aware-routing.md) | this index (P13) | Decision-aware Q-scorer: contrastive + SPO+ + bilinear model-feature scoring |
| [`unified-trace-memory-service.md`](unified-trace-memory-service.md) | standalone (stub 2026-04-25) | Cross-source provenance store over `agent_audit.log` + `progress/` + `autopilot_journal.*` + `autopilot_state.json`. Operationalizes Cross-Cutting Concern §5 above. Read-only query layer; no migration of existing writers. Useful during autopilot debugging and post-nightshift "why did we decide X" investigations. |

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

## Research Intake Update — 2026-04-22

### New Related Research (intake-425/426 deep-dive)
- **[intake-425] "Memory Transfer Learning: How Memories are Transferred Across Domains in Coding Agents"** (arxiv:2604.14004)
  - 4 adoptable patterns for strategy_store and PromptForge: (1) Insight abstraction format `(title, description, generalized_content)` with no task-specific details, (2) N=3 embedding retrieval validation (embedding > LLM reranking > adaptive rewriting), (3) negative transfer safety gates (3-category taxonomy), (4) task-agnostic > task-specific insights (+1.1%). See P16 (AP-32/33/34) above.
- **[intake-426] "Dive into Claude Code: The Design Space of Today's and Future AI Agent Systems"** (arxiv:2604.14228)
  - Graduated trust model for routing confidence thresholds: new models start conservative (~20% auto-approve at <50 sessions), relax as benchmarks accumulate (40% at 750+ sessions). Pattern applicable to RI-10 canary and learned routing controller work. No new task code — design pattern absorbed into existing P6/P13.
  - Input-only classification (anti-gaming pattern): Claude Code's permission classifier sees user request + tool call but NOT model reasoning — prevents model from influencing its own safety gate. Validates current `factual_risk.py` design which classifies on input features only. No code change needed.
