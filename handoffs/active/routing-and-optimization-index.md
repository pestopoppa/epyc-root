# Routing & Optimization — Umbrella Index

**Created**: 2026-03-25
**Purpose**: Links and coordinates the three interconnected optimization subsystems

---

## Subsystem Handoffs

### 1. [`routing-intelligence.md`](routing-intelligence.md)
Semantic classifiers, factual risk scoring, role selection.

**Status**: Phases 0-3 complete, shadow mode active since 2026-03-15. Phases 4-6 (enforcement) deferred.

**Scope**: Input classification (prompt intent, summarization/vision/factual-risk), output parsing (verdict detection, stub detection), quality signals (repetition, garble, factual risk). Unified `src/classifiers/` module replacing 9 scattered heuristics.

**Key artifacts**: `src/classifiers/factual_risk.py` (280 lines, 43 tests), `ClassificationRetriever` (315 lines), `src/classifiers/output_parsers/` (config-driven YAML).

### 2. [`autopilot-continuous-optimization.md`](autopilot-continuous-optimization.md)
Autonomous optimization framework — 4 species, tiered evaluation, Pareto archive, safety gates. Evolved from seeding -> Claude-Debugger -> AutoPilot -> AutoResearch.

**Status**: Implementation complete (Phase 1-3). 13 wiring actions identified. Claude-Debugger subsumed. Stack-config added as optimization axis.

**Key artifacts**: `epyc-orchestrator/scripts/autopilot/` (12 files), `program.md` (autoresearch strategy document).

### 3. [`dynamic-stack-concurrency.md`](dynamic-stack-concurrency.md)
NUMA quarter scheduling, tiered deployment (HOT/WARM/COLD), KV state migration, single-to-multi instance transition.

**Status**: Strategic analysis complete. Implementation deferred to Phase D (after autoresearch bootstrap + observability).

**Key artifacts**: None yet — strategy document only. Implementation targets `orchestrator_stack.py`, `round_robin.py`, llama-server `--slot-save-path`.

---

## Cross-Cutting Concerns

### 1. Q-Scorer Baselines Depend on Stack Config

`routing-intelligence.md` § baselines defines per-role t/s used by the Q-scorer cost dimension. If the stack changes (different models, different instance counts), `baseline_tps_by_role` in `q_scorer.py` must update.

**Current discrepancy**: Q-scorer uses 19.6 t/s for frontdoor (moe6+lookup) but lookup disabled since 2026-03-19 (segfault). Actual: 12.7 t/s. Under-penalizes frontdoor cost by ~1.5x.

### 2. Routing Quality Informs Stack Decisions

High escalation rate from routing-intelligence means more specialist capacity needed (stack concern). Low escalation rate means more frontdoor instances may be optimal. The routing classifier's quality directly affects what the scheduler needs to provision.

### 3. Autoresearch Evaluates Stack Configs

The autoresearch framework (autopilot) must test stack configurations — not just routing parameters. Stack-config is an optimization axis alongside numeric params, prompts, and feature flags. The `program.md` governs what can be modified.

### 4. Factual Risk Affects Resource Allocation

`factual_risk.py` scores prompt risk. High-risk prompts need bigger models = more NUMA resources. When risk-aware routing goes to enforce mode (Phase 4), the scheduler must anticipate architect demand from risk distribution.

### 5. Conversation Logs Feed Back Into All Three

Observed patterns inform:
- **Routing**: Escalation chains, quality outcomes -> Q-value training data
- **Autopilot**: Experiment evaluation, regime detection
- **Stack**: Demand patterns, tier utilization -> template refinement

This mirrors how episodic memory already works — Q-values accumulate from routing outcomes, routing classifier trains on accumulated Q-values. Autoresearch extends this loop to stack-level decisions.

---

## Strategic Sequence

```
Phase A: Autoresearch Bootstrap
  - Draft program.md (strategy, constraints, research directions)
  - Subsume Claude-Debugger into autoresearch framework
  - Wire stack-config as experiment variable
  - Deliverable: Autonomous experimentation with debug suite scoring

Phase B: Observability Infrastructure
  - Instrument queue depth, per-role frequency, escalation rate, NUMA utilization
  - Add --slot-save-path to production server launches
  - Log stack state alongside routing telemetry
  - Deliverable: Telemetry foundation for data-driven scheduling

Phase C: Autoresearch-Driven Exploration
  - Test model candidates, tier assignments, instance counts
  - Test cascading configs, general model prompting efficiency
  - Evaluate via debug suite (fast) -> promote via full suite (T2)
  - Deliverable: Empirically-grounded stack configuration

Phase D: Deterministic Quarter Scheduler
  - Event-driven NUMA quarter allocation
  - KV state save/restore for same-model transitions
  - Overflow queuing with priority scheduling
  - Deliverable: Self-contained scheduler in orchestrator

Phase E: Template Codification
  - Encode findings as stack templates in orchestrator config
  - Template selection at session boundary
  - Dynamic backend add/remove in RoundRobinBackend
  - Deliverable: Production-ready dynamic stack

Phase F: Conversation-Log-Driven Refinement
  - Analyze real usage patterns
  - Build predictive workload model
  - Feed predictions into scheduler
  - Deliverable: Usage-pattern-aware optimization
```

---

## Dependency Graph

```
routing-intelligence (Phases 0-3 done)
  |
  +-- factual risk scores --> stack scheduler (Phase D)
  +-- escalation rates --> autoresearch stack experiments (Phase C)
  +-- Q-scorer baselines --> stack config updates

autopilot / autoresearch
  |
  +-- program.md --> experiment methodology
  +-- debug suite scoring --> stack config evaluation
  +-- findings --> orchestrator config commits

dynamic-stack-concurrency
  |
  +-- telemetry (Phase B) --> scheduler decisions
  +-- KV migration capability --> single-to-multi transition
  +-- quarter allocation --> round_robin.py backend list
```

## See Also

- `model_registry.yaml` — full model catalog with benchmarks
- `orchestrator_stack.py` — current static stack configuration
- `src/backends/round_robin.py` — runtime instance routing
- `scripts/autopilot/` — autoresearch implementation
