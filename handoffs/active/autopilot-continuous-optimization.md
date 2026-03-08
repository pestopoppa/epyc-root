# AutoPilot: Continuous Recursive Optimization

**Status**: Implementation complete (Phase 1-3), ready for integration testing
**Created**: 2026-03-08
**Location**: `epyc-orchestrator/scripts/autopilot/`

## Architecture

A continuous agent loop that autonomously optimizes orchestration intelligence through 4 optimizer "species", a tiered evaluation tower, 4D Pareto archive, and safety gates.

```
Controller (Claude CLI meta-reasoning)
  ├── Species 0: Seeder (3-way eval → Q-value training)
  ├── Species 1: NumericSwarm (Optuna NSGA-II → hot-swap config)
  ├── Species 2: PromptForge (LLM prompt mutation → .md hot-swap)
  └── Species 3: StructuralLab (flags + routing model lifecycle)
  │
  EvalTower: T0 (10q/30s) → T1 (100q/5m) → T2 (500+/30m)
  ParetoArchive: 4D (quality × speed × -cost × reliability)
  SafetyGate: quality floor + per-suite guard + routing diversity
```

## File Structure

```
epyc-orchestrator/scripts/autopilot/
  autopilot.py              # Main controller + CLI (start|status|pause|resume|report|plot|checkpoint|restore)
  experiment_journal.py     # Dual TSV + JSONL logging with rotation
  pareto_archive.py         # 4D non-dominated sorting + hypervolume indicator
  safety_gate.py            # Quality floor, regression guards, rollback triggers
  eval_tower.py             # Tiered evaluation wrapping seeding infrastructure
  config_applicator.py      # Hot-swap vs restart parameter routing
  meta_optimizer.py         # Species budget rebalancing + stagnation detection
  progress_plots.py         # 6 matplotlib visualizations (auto-updated)
  sentinel_questions.yaml   # 10 curated T0 validation questions
  species/
    __init__.py
    seeder.py               # 3-way eval + reward injection + convergence monitoring
    numeric_swarm.py        # Optuna multi-objective + cluster-based robust selection
    prompt_forge.py         # Claude CLI prompt mutation (targeted_fix, compress, crossover...)
    structural_lab.py       # Checkpointing, training, distillation, memory reset

epyc-orchestrator/orchestration/
  autopilot_state.json      # Persistent state (Pareto archive, trial counter, budgets)
  autopilot_journal.tsv     # Human-readable experiment log
  autopilot_journal.jsonl   # Machine-readable experiment log
  autopilot_baseline.yaml   # Frozen baseline metrics
  autopilot_checkpoints/    # Timestamped routing intelligence snapshots
  autopilot_plots/          # Auto-generated progress visualizations
```

## Key Data Structures

```python
# Action types the controller can emit
{"type": "seed_batch", "n_questions": 50, "suites": ["coder", "thinking"]}
{"type": "numeric_trial", "surface": "memrl_retrieval", "params": {}}
{"type": "prompt_mutation", "file": "frontdoor.md", "mutation": "targeted_fix"}
{"type": "structural_experiment", "flags": {"skillbank": true}}
{"type": "train_routing_models", "min_memories": 500}
{"type": "distill_skillbank", "teacher": "claude", "categories": ["routing"]}
{"type": "reset_memories", "keep_seen": true, "keep_skills": true}
{"type": "deep_eval", "tier": 2}
{"type": "rollback", "to_checkpoint": "production_best"}

# EvalResult (from eval_tower → safety_gate → pareto_archive)
EvalResult(tier, quality, speed, cost, reliability, per_suite_quality, routing_distribution)

# ParetoEntry (4D: quality↑, speed↑, -cost↑, reliability↑)
ParetoEntry(trial_id, objectives, config_snapshot, species, git_tag, parent_trial, ...)

# JournalEntry (TSV columns + JSONL full detail)
JournalEntry(trial_id, timestamp, species, action_type, tier, quality, speed, cost, ...)
```

## Routing Intelligence Lifecycle

```
SEED (3-way eval) → Q-values accumulate
    │ [500+ memories?]
    ▼
CHECKPOINT → TRAIN MLP + GAT
    │ [A/B passes?]
    ▼                    ↘ RESTORE checkpoint
CHECKPOINT + ENABLE routing_classifier + graph_router
    │ [Q-values stable?]
    ▼
DISTILL SkillBank
    │ [A/B passes?]
    ▼                    ↘ RESTORE checkpoint
CHECKPOINT (production_best) + ENABLE skillbank
    │ [plateau?]
    ▼
CHECKPOINT + RESET (selective) + RESEED → back to top
```

## Safety Mechanisms

| Gate | Threshold | Action |
|------|-----------|--------|
| Quality floor | avg < 2.0/3.0 | Reject |
| Regression | Δq < -0.05 vs baseline | Reject |
| Per-suite | Δq < -0.1 any suite | Reject |
| Routing diversity | >80% architect | Reject |
| Throughput floor | <80% baseline speed | Reject |
| Consecutive failures | 3 × T0 fail | Auto-rollback |

## Integration Points

| Component | Path | Integration |
|-----------|------|-------------|
| Seeding 3-way | `scripts/benchmark/seed_specialist_routing.py` | Seeder wraps `evaluate_question_3way` + `_inject_3way_rewards_http` |
| Question pool | Research: `scripts/benchmark/question_pool.py` | EvalTower draws T1/T2 validation questions |
| Optuna | Research: `scripts/benchmark/optuna_orchestrator.py` | NumericSwarm reuses TPE/cluster patterns |
| Claude Debugger | `src/pipeline_monitor/claude_debugger.py` | PromptForge reuses Popen+session+git pattern |
| Episodic memory | `orchestration/repl_memory/episodic_store.py` | Seeder monitors count/convergence |
| Memory reset | `scripts/session/reset_episodic_memory.sh` | StructuralLab calls with selective flags |
| SkillBank | `orchestration/repl_memory/skill_bank.py` | StructuralLab triggers distillation |
| Config hot-swap | `src/api/routes/config.py` (POST /config) | ConfigApplicator routes flag changes |
| Feature flags | `src/features.py` (43 flags + validate()) | StructuralLab proposes flag combos |

## Train/Validate Split

- **Training** (Seeder): 579 debug suite questions + 53K pool → Q-value training
- **Validation** (EvalTower): HF benchmark questions (MMLU, GSM8K, etc.) → system quality
- Prevents overfitting: debug suites train routing intelligence, benchmarks validate generalization

## Usage

```bash
# Start optimization loop
python scripts/autopilot/autopilot.py start

# Start without Claude CLI controller (autonomous mode)
python scripts/autopilot/autopilot.py start --no-controller

# Dry run (no API calls, synthetic results)
python scripts/autopilot/autopilot.py start --dry-run --max-trials 10

# Check status
python scripts/autopilot/autopilot.py status

# Pause/resume
python scripts/autopilot/autopilot.py pause
python scripts/autopilot/autopilot.py resume

# Generate report
python scripts/autopilot/autopilot.py report

# Generate plots
python scripts/autopilot/autopilot.py plot

# Checkpoint current state
python scripts/autopilot/autopilot.py checkpoint --production-best

# Restore from checkpoint
python scripts/autopilot/autopilot.py restore
```

## Verification Plan

1. **Smoke test**: `python autopilot.py start --dry-run --max-trials 5`
2. **Seeder integration**: Run 20-question batch, verify reward injection
3. **NumericSwarm**: Create Optuna study, suggest trials, verify cluster selection
4. **PromptForge**: Propose mutation, apply, verify git snapshot
5. **Full loop**: 10 trials across all species, verify journal + Pareto + safety gate
6. **Overnight**: 8-hour unattended run, check hypervolume trend

## Staleness Notes

- `optuna_orchestrator.py`: TPE/cluster patterns reusable; parameter ranges stale (predate current config/models.py)
- `seed_specialist_routing.py`: Canonical source at `epyc-orchestrator/scripts/benchmark/` (1,449 lines)
- `orchestrator_self_management.md` Phase 9: Deferred Optuna loop; architecture evolved significantly
- `pre-split-optimization-ab-test-plan.md`: Decision function reusable; specific paths broken post-split

## Numeric Parameter Surfaces

| Surface | Key Params | Application |
|---------|-----------|-------------|
| memrl_retrieval | q_weight, min_similarity, min_q_value, confidence_threshold, semantic_k, prior_strength | Hot-swap via env + restart |
| think_harder | min_expected_roi, token_budget_min/max, cot_roi_threshold | Hot-swap via env + restart |
| chat_pipeline | try_cheap_first_quality_threshold | Hot-swap via env + restart |
| monitor | entropy_threshold, repetition_threshold, entropy_spike_threshold | Hot-swap via env + restart |
| escalation | max_retries, max_escalations | Hot-swap via env + restart |

## Dependencies

- Python 3.11+
- `optuna` (pip install optuna) — NumericSwarm Bayesian optimization
- `matplotlib` (already installed) — Progress plots
- `httpx` (already installed) — API calls
- `scikit-learn` (optional) — Cluster-based robust selection
- `claude` CLI (on PATH) — Controller meta-reasoning (optional, --no-controller for autonomous mode)
