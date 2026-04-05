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
| AutoPilot / AutoResearch | [`autopilot-continuous-optimization.md`](autopilot-continuous-optimization.md) | AR-3 run 2: 46 trials. Safety hardened + hybrid eval (T1 real gate). | Relaunch AR-3 |
| Dynamic Stack | [`dynamic-stack-concurrency.md`](dynamic-stack-concurrency.md) | Phases B-D complete (pre-warm + KV migration) | Phase E: autoresearch exploration |
| KV Cache Quantization | [`kv-cache-quantization.md`](kv-cache-quantization.md) | Hadamard deployed, TQ/PQ abandoned | Monitor upstream TurboQuant |
| Context Folding | [`context-folding-progressive.md`](context-folding-progressive.md) | Phase 0+1 complete | Phase 1+ (segment dedup), Phase 2 (quality + helpfulness scoring + free-zone sweep), Phase 3 (process rewards + role-aware compaction) |
| Conversation Management | [`orchestrator-conversation-management.md`](orchestrator-conversation-management.md) | Active, 7 work items | B1 user modeling, B2 context compression |
| LangGraph Migration | [`langgraph-migration.md`](langgraph-migration.md) | pre-migration-complete (analysis done) | Execute migration: pydantic_graph → LangGraph |
| CC Local Integration | [`claude-code-local-constellation-routing.md`](claude-code-local-constellation-routing.md) | READY TO IMPLEMENT | Adapter hardening, MCP contract, endpoint compat |
| Retrain Routing Models | [`retrain-routing-models.md`](retrain-routing-models.md) | BLOCKED | Accumulate ~500+ routing memories via seeding |
| Meta-Harness Optimization | [`meta-harness-optimization.md`](meta-harness-optimization.md) | Tier 1+2 done, ready for AR-3 validation | Live validation via next AR-3 run |
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

- [ ] **RI-9: Threshold sweep in seeding harness** — Reuse existing `--suite` mechanism. Sweep risk thresholds and emit Pareto reports (factuality vs cost vs latency).

### P4 — Observability Infrastructure (Dynamic Stack Phase B)

These unblock data-driven stack scheduling.

- [x] **DS-1: Instrument queue depth telemetry** — ✅ 2026-03-29. `RoundRobinBackend` now tracks per-instance active/total counts, idle instances, seconds since last request. `get_stats()` exposes all. Queue depth injected into `routing_meta` in `_route_request()`.

- [x] **DS-2: Instrument escalation rate telemetry** — ✅ 2026-03-29. `AppState.record_escalation(from, to)` tracks total escalations and per-path counts (e.g., "frontdoor→coder"). Wired into streaming chat.py (2 call sites) and graph helpers. `get_stats()` returns escalation_rate and escalations_by_path.

- [x] **DS-3: Add `--slot-save-path` to production launches** — ✅ 2026-03-29. `build_server_command()` appends `--slot-save-path <cache_dir>/kv_slots/<role>` for all roles. Per-role subdirectories created automatically.

- [x] **DS-4: Log stack state alongside routing telemetry** — ✅ 2026-03-29. `routing_meta["stack_state"]` populated from `state.registry.roles` with model name, tier, and instance count. Logged via `log_task_started()` in progress JSONL.

### P5 — AutoResearch Bootstrap (Phase A)

- [x] **AR-1: Establish debug suite baseline** — ✅ 2026-03-30. 3-way eval on 105 questions (15/suite × 7 suites). Direct 57.3%, REPL 43.1%, Architect 52.4%. Tools hurt 2.7× more than help (24 vs 9). Median pipeline latency 181s. Baseline written to `orchestration/autopilot_baseline.yaml`. Per-suite breakdown pending (output JSON lost to pipe error; re-run needed for granular data).

- [x] **AR-2: Smoke test autoresearch loop** — ✅ 2026-03-29. Dry-run 5 trials passed: journal writes (JSONL + TSV), parent_trial linkage, consecutive_failures persistence, Pareto archive, safety gate all functional. matplotlib missing (non-fatal).

- [ ] **AR-3: First live autoresearch run** — Run 1 (2026-04-01): 9 wiring bugs fixed, program.md rewritten. Run 2 (2026-04-02–04): 44 trials, 6 Pareto frontier, 1 useful change (`get_direct_answer_prefix()` in resolver.py, q=3.0). **Corruption incident**: trial ~25 destroyed `escalation.py` (454→3 lines), API down 11h. Safety hardened with 5 fixes (deep validation, shrinkage guards, revert commits). T0 sentinels saturated at q=3.0 — need larger eval pool before relaunch.

### P6 — Routing Intelligence Phase 6 (controlled rollout)

Depends on Phase 4 A/B results.

- [ ] **RI-10: Shadow → enforce canary** — Enable enforce on frontdoor role only, 25% of requests, 3 days. Monitor latency, cost, escalation rate. See `routing-intelligence.md` § Phase 6.

- [ ] **RI-11: Enforce expand** — Frontdoor 100% + worker_general, 7 days.

- [ ] **RI-12: Enforce global** — All roles. Set up monitoring dashboards.

### P7 — Dynamic Stack Implementation (Phases C-F)

Depends on observability (P4) and autoresearch baseline (P5).

- [ ] **DS-5: Autoresearch-driven model exploration** — Test frontdoor candidates, instance counts, tier assignments via autoresearch loop. See `dynamic-stack-concurrency.md` § Part 6.

- [ ] **DS-6: Deterministic quarter scheduler** — Event-driven NUMA quarter allocation. See § Part 4.

- [ ] **DS-7: Stack templates in orchestrator config** — Encode autoresearch findings as selectable stack profiles. See § Strategic Sequence Phase E.

### P8 — AutoPilot Design Philosophy Imports

Lower priority refinements.

- [x] **AP-9: Tighter per-trial scope** — ✅ 2026-04-05. `_validate_single_variable()` in `autopilot.py` rejects multi-file prompt mutations, multi-flag structural experiments, and multi-param explicit numeric trials before dispatch.

- [x] **AP-10: Simplicity criterion for PromptForge** — ✅ 2026-03-29. After safety gate passes, checks prompt size increase >20% with quality delta <0.02 — reverts if criterion violated.

- [x] **AP-11: Git worktree isolation for PromptForge** — ✅ 2026-04-05. `worktree_manager.py` creates temp worktrees per trial. `ExperimentContext` handles apply/accept/reject with auto-reject safety default. PromptForge gains `apply_mutation_in_context()` + `apply_code_mutation_in_context()`. 5 tests.

- [x] **AP-12: Explicit eval trust boundary** — ✅ 2026-03-29. Added trust boundary table to `program.md` showing OUTSIDE (species-modifiable) vs INSIDE (immutable eval) files.

- [x] **AP-13: Grep-parseable metric output** — ✅ 2026-04-05. `EvalResult.to_grep_lines()` emits `METRIC key: value` lines. Logged after each eval in the autopilot main loop. Extract via `grep METRIC autopilot.log`.

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
`routing-intelligence.md` § baselines defines per-role t/s used by `q_scorer.py`. If the stack changes (different models, instance counts), `baseline_tps_by_role` MUST update. **Current issue**: frontdoor baseline stale (RI-0).

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
`context-folding-progressive.md` Phase 0-1 (compaction trigger + two-level condensation) changes session quality behavior. The autoresearch baseline (AR-1) should be captured AFTER Phase 0-1 is deployed, or the "before" number will reflect a compaction policy that is about to change. Phase 3 process rewards feed MemRL Q-value enrichment (routing-intelligence Phase 5). **Updated 2026-04-05**: Phase 2 now includes free-zone threshold sweep and helpfulness scoring (intake-261/262); Phase 3 now includes role-aware compaction profiles that parameterize aggressiveness per orchestrator role. Phase 3b role profiles will directly affect autopilot token costs — `worker_explore` gets more aggressive compaction than `worker_coder`.

### 8. Conversation Mgmt B2 ↔ Context Folding Phase 1
`orchestrator-conversation-management.md` B2 (protected-zone compression from Hermes/OpenGauss) and `context-folding-progressive.md` Phase 1 (two-level condensation) both modify session compaction behavior. They must be sequenced — context-folding Phase 1 should land first as the structural upgrade, then B2's protected-zone logic can layer on top. Alternatively, B2's tool-pair sanitization (`_sanitize_tool_pairs()`) could be extracted as a standalone prerequisite for both. **Updated 2026-04-05**: Context-folding Phase 3b (role-aware compaction profiles) must align with B2's role taxonomy — the `CompactionProfile` roles must match the conversation management role definitions.

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
  ├── 🔄 PACKAGE A (running) ──── Instrumented seeding eval
  │     CF Phase 1 validation + difficulty signal + RI-9 sweep + TrimR
  │     Output: data/package_a/<timestamp>/
  │
  ├── PACKAGE B (next) ────────── AR-3 relaunch + RTK eval
  │     Depends on Package A results for config decisions
  │
  ├── PACKAGE C (after B) ─────── RI-10 canary (3-day passive)
  │     25% enforce on frontdoor, monitor latency/cost/escalation
  │
  ├── DS-C (pre-warm deploy) ──── HIGH PRIORITY. No dependencies.
  │     Add 1×96t + 4×48t instances for frontdoor/coder/worker.
  │
  ├── DS-D (concurrency router) ── Depends on DS-C.
  │
  ├── P5 (autoresearch) ──────── AR-3 relaunch = Package B.
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
