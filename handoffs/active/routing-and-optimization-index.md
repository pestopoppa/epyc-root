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
| Routing Intelligence | [`routing-intelligence.md`](routing-intelligence.md) | Phases 0-3 done, shadow active | Phase 4: risk-aware enforce |
| AutoPilot / AutoResearch | [`autopilot-continuous-optimization.md`](autopilot-continuous-optimization.md) | Impl complete, 13 wiring gaps | Wire failure context, then bootstrap autoresearch |
| Dynamic Stack | [`dynamic-stack-concurrency.md`](dynamic-stack-concurrency.md) | Strategic analysis complete | Phase B: observability instrumentation |

---

## Outstanding Tasks (Priority Order)

### P0 — Wiring Bugs (infrastructure built but not connected)

These are HIGH priority because the code exists but isn't wired up. Low effort, high value.

- [ ] **AP-1: Wire `failure_context` into PromptForge dispatch** — `autopilot.py:264` never passes `failure_context`/`per_suite_quality` to `propose_mutation()`. PromptForge mutations are blind to why previous attempts failed. See `autopilot-continuous-optimization.md` § "HIGH PRIORITY" item 1.

- [ ] **AP-2: Feed failure narratives into controller prompt** — `SafetyGate.analyze_failure()` produces structured narratives in `JournalEntry.failure_analysis`, but `summary_text()` strips them. Controller re-proposes similar failing actions. See § item 2.

- [ ] **AP-3: Populate `parent_trial` and `config_diff` journal fields** — Both fields exist on `JournalEntry` but are never written. No lineage tracking. See § item 3.

- [ ] **RI-0: Fix Q-scorer frontdoor baseline** — `q_scorer.py` uses 19.6 t/s (moe6+lookup) but lookup disabled since 2026-03-19 (segfault). Actual: 12.7 t/s. Under-penalizes frontdoor cost by ~1.5x. Location: `baseline_tps_by_role` in `orchestration/repl_memory/q_scorer.py`.

### P1 — Routing Intelligence Phase 4 (risk-aware enforcement)

Phases 0-3 built the risk scorer and put it in shadow mode. Phase 4 makes it affect routing decisions. **Prerequisite**: calibration dataset (labeled prompts with known risk levels — source from simpleqa failures + seeding diagnostics).

- [ ] **RI-1: Build calibration dataset** — Collect labeled set of prompts with known factual-risk levels. Sources: simpleqa failures, seeding diagnostic logs with `passed=False` on factual suites. Minimum 200 labeled examples. See `routing-intelligence.md` § Phase 3 design requirements.

- [ ] **RI-2: Cheap-first risk bypass** — `src/api/routes/chat.py:_try_cheap_first` (~line 208). When `risk >= high`, bypass cheap-first or apply strict pass criteria. See § Phase 4 table.

- [ ] **RI-3: Plan review gate risk integration** — `routing.py:_plan_review_gate`. High `risk_band` → force review even if generic heuristics pass. See § Phase 4 table.

- [ ] **RI-4: Escalation policy risk-awareness** — `src/escalation.py:EscalationPolicy.decide()`. High risk + uncertainty → trigger think-harder EARLIER (before penultimate retry). See § Phase 4 table.

- [ ] **RI-5: Failure graph veto modulation** — `routing.py:_route_request` (line ~48+). Hardcoded `risk > 0.5` threshold should be modulated by factual-risk band. See § Phase 4 table.

- [ ] **RI-6: Structured review objective** — `src/api/routes/chat_review.py`. Replace `answer[:100]` proxy with `{"task_type", "risk_band", "key_claims", "verification_focus"}`. See § Phase 4 design requirements.

- [ ] **RI-7: A/B test Phase 4** — Run seeding harness with `factual_risk_mode=enforce` vs `off`. Compare simpleqa F1, escalation rate, cost, p95 latency. Minimum 500 questions per arm, p < 0.05. See § Phase 4 design requirements.

### P2 — AutoPilot Structural Improvements

Medium priority. These improve autoresearch effectiveness before it starts running at scale.

- [ ] **AP-4: `lab failures` query at species proposal time** — Add `journal.recent_failures(species=X, n=10)` and inject into each species' proposal context. Prevents re-attempting known-bad ideas. See `autopilot-continuous-optimization.md` § item 4.

- [ ] **AP-5: Per-suite quality trends in controller prompt** — Add `journal.suite_quality_trend(last_n=10)`. Controller currently can't see "coder suite declining for 5 trials." See § item 5.

- [ ] **AP-6: Persist `_consecutive_failures` counter** — Safety gate's failure counter resets on restart. Serialize to `autopilot_state.json`. See § item 6 (trivial effort).

- [ ] **AP-7: Invalidate stale Optuna trials after regime changes** — When StructuralLab changes flags or PromptForge changes prompts, old Optuna trials become misleading. Add `numeric_swarm.mark_epoch(reason)`. See § item 7.

- [ ] **AP-8: Hypothesis-mechanism tracking on JournalEntry** — Add `hypothesis: str` and `expected_mechanism: str` fields. Improves Strategy Store retrieval. See § item 8.

### P3 — Routing Intelligence Phase 5 (seeding integration)

- [ ] **RI-8: Add risk fields to `RoleResult`** — `scripts/benchmark/seeding_types.py` line 167. Fields: `risk_score`, `risk_band`, `risk_features`. Was falsely marked complete 2026-03-06; verified absent 2026-03-24. See `routing-intelligence.md` § Phase 5.

- [ ] **RI-9: Threshold sweep in seeding harness** — Reuse existing `--suite` mechanism. Sweep risk thresholds and emit Pareto reports (factuality vs cost vs latency).

### P4 — Observability Infrastructure (Dynamic Stack Phase B)

These unblock data-driven stack scheduling.

- [ ] **DS-1: Instrument queue depth telemetry** — Log per-role request frequency, queue depth, active/idle instance count. Location: `src/api/routes/chat.py` request handler + `src/backends/round_robin.py`.

- [ ] **DS-2: Instrument escalation rate telemetry** — Track escalation chains per session. Location: `src/escalation.py`, `progress_logger.py`.

- [ ] **DS-3: Add `--slot-save-path` to production launches** — Enable KV state save/restore in `orchestrator_stack.py` server launch commands. See `dynamic-stack-concurrency.md` § Part 2.

- [ ] **DS-4: Log stack state alongside routing telemetry** — Which models loaded, which NUMA quarters assigned, instance counts. Enables correlation between stack config and routing outcomes.

### P5 — AutoResearch Bootstrap (Phase A)

- [ ] **AR-1: Establish debug suite baseline** — Run full debug suite (579 questions) against current production config. Record pass rate in `autopilot_baseline.yaml`. This is the "before" number.

- [ ] **AR-2: Smoke test autoresearch loop** — `python scripts/autopilot/autopilot.py start --dry-run --max-trials 5`. Verify journal writes, safety gate, Pareto archive. Fix any integration issues.

- [ ] **AR-3: First live autoresearch run** — Follow `program.md` setup phase. Start with Tier 1 experiments (prompt optimization — hot-swap, fast iteration). Target: at least one "keep" result.

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

- [ ] **AP-9: Tighter per-trial scope** — Constrain each trial to single-variable changes. See `autopilot-continuous-optimization.md` § item 9.

- [ ] **AP-10: Simplicity criterion for PromptForge** — Reject mutations that increase prompt size >20% for <0.02 quality improvement. See § item 10.

- [ ] **AP-11: Git worktree isolation for PromptForge** — Parallel prompt experiments in worktrees. See § item 11.

- [ ] **AP-12: Explicit eval trust boundary** — Document that species cannot modify eval code. See § item 12.

- [ ] **AP-13: Grep-parseable metric output** — Standardize benchmark output to `key: value` format. See § item 13.

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

---

## Dependency Graph

```
P0 (wiring bugs) ──────────────────────────── no dependencies, do first
  │
P1 (routing Phase 4) ─── needs RI-1 calibration dataset first
  │                        also benefits from RI-0 baseline fix (P0)
  │
P2 (autopilot structural) ─ independent of P1, can run in parallel
  │
P3 (routing Phase 5) ──── depends on P1 complete (need enforce mode data)
  │
P4 (observability) ─────── independent, can run in parallel with P1-P3
  │
P5 (autoresearch bootstrap) ── benefits from P0 + P2 (cleaner autopilot)
  │                              benefits from P4 (telemetry for stack exps)
  │
P6 (routing Phase 6 rollout) ── depends on P1 A/B results (RI-7)
  │
P7 (dynamic stack impl) ──── depends on P4 (telemetry) + P5 (baseline)
  │
P8 (autopilot refinements) ── lowest priority, independent
```

---

## Reporting

After completing any task group, update:
1. The task checkbox in this index (mark `[x]`)
2. The relevant handoff document (update status, add implementation notes)
3. `progress/YYYY-MM/YYYY-MM-DD.md` with session summary
4. `CHANGELOG.md` if the change is significant

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
