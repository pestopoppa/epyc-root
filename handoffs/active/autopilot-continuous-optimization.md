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

## Research Intake Update — 2026-03-14

### New Related Research
- **[intake-108] "EvoScientist: Multi-Agent Evolving AI Scientists"** (arxiv:2603.08127)
  - Relevance: Directly addresses multi-agent scientific discovery with persistent memory — core pattern for AutoPilot's recursive optimization
  - Key technique: Three specialized agents (Researcher, Engineer, Evolution Manager) with persistent ideation + experimentation memory modules enabling continuous improvement across iterations
  - Reported results: Outperforms 7 SOTA systems in novelty, feasibility, relevance, and clarity; substantially improved code execution success rates
  - Delta from current approach: AutoPilot uses 4 optimizer species with a Pareto archive; EvoScientist separates idea generation from execution with an Evolution Manager for knowledge distillation — this separation pattern could inform AutoPilot's species design

- **[intake-106] "Agentic Critical Training (ACT)"** (arxiv:2603.08706)
  - Relevance: RL-based self-reflection training for agents — relevant to AutoPilot's optimizer species learning to judge action quality
  - Key technique: GRPO-based training where models learn to identify superior actions among alternatives
  - Reported results: +5.07 points over imitation learning, transfers across model sizes (4B→8B trajectories)
  - Delta from current approach: AutoPilot evaluates via benchmark tower; ACT shows agents can learn quality-awareness through RL

- **[intake-105] "PostTrainBench"** (arxiv:2603.08640)
  - Relevance: Benchmarks autonomous post-training by agents — informs what AutoPilot-style systems can realistically achieve
  - Key technique: Evaluates frontier agents autonomously post-training LLMs under 10h/1xH100 constraint
  - Reported results: Best agent (Opus 4.6) at 23.2% vs 51.1% official, but can surpass baselines on targeted tasks; performance plateaus after ~5 hours
  - Delta from current approach: Sets empirical expectations for autonomous optimization capabilities

- **[intake-240] "GEPA: Reflective Prompt Evolution Can Outperform Reinforcement Learning"** (arxiv:2507.19457)
  - Relevance: **Direct replacement candidate for PromptForge species**. Genetic-Pareto prompt optimizer with natural language reflection. Outperforms GRPO by 6% avg (up to 20%) with 35x fewer rollouts. Outperforms MIPROv2 by >10%.
  - Key technique: Pareto-aware selection + Actionable Side Information (ASI, text-optimization analogue of gradient). Population-based evolution handles multi-objective (quality × speed × cost × reliability) natively — maps directly onto our 4D Pareto archive.
  - Available as: `dspy.GEPA` (drop-in DSPy optimizer) and DeepEval framework. GitHub: `github.com/gepa-ai/gepa`.
  - Delta from current approach: PromptForge uses heuristic mutation operators (targeted_fix, compress, crossover). GEPA's principled evolutionary search with proven convergence properties could replace the mutation loop entirely. The 35x rollout reduction vs RL makes it practical for prompt-level optimization where RL (GRPO) is too expensive.
  - ICLR 2026 Oral.

### Deep-Dive Findings (2026-03-15)

**Source**: `research/deep-dives/agent-architectures-paperclip-agentrxiv.md`

#### Cost Governance Gap

Paperclip (arxiv:2502.01157) implements cost-aware LLM selection with explicit per-request cost tracking. Our orchestrator currently has **zero cost tracking** — no field on `RoutingResult`, no per-request token cost accumulation, no cost dimension in routing decisions.

**Implemented**: Added `estimated_cost: float` to `RoutingResult`. Computed in `_route_request()` as `_TIER_COST_WEIGHTS[tier] × est_tokens / 1M` (tier A=10, B=3, C=1, D=0.2). Logged in `routing_meta` as telemetry. Default 0.0 (backward compatible). 3 tests added.

**Next step**: Wire into Pareto archive's cost dimension (currently approximated). Becomes critical if/when we add external API fallback (cloud models have explicit per-token pricing).

#### Retrieval-Augmented Autopilot Iteration

AgentRxiv's pattern of retrieving similar past problems/solutions to guide current iteration maps onto AutoPilot's continuous optimization loop. Currently, AutoPilot's species operate independently — each trial starts fresh without consulting past trial outcomes beyond the Pareto archive.

**Proposed enhancement**: When PromptForge proposes a prompt mutation, first retrieve similar past mutations from the experiment journal (JSONL) to inform the mutation direction. When NumericSwarm suggests parameters, retrieve past trials in the same parameter neighborhood. This is essentially RAG for the optimizer loop.

**Implementation**: The experiment journal (`autopilot_journal.jsonl`) already stores full trial details. Add a retrieval step (embed trial description, cosine similarity search) before each species proposes an action. Could reuse the existing MemRL retriever infrastructure.

**Priority**: Low — only valuable after AutoPilot has accumulated enough trial history to make retrieval useful (50+ trials).

#### EvoScientist Knowledge Distillation Gap (intake-108)

**Source**: `research/deep-dives/evoscientist-multi-agent-evolution.md`

EvoScientist's Evolution Manager (EMA) separates knowledge distillation from ideation/execution. Three channels: IDE (direction distillation from successes), IVE (failure analysis with LLM-summarized root causes), ESE (strategy distillation from engineer trajectories). Ablation shows +45.83 gap from full evolution vs none; ESE alone gives +10.17pp code execution success.

**Key finding**: Our AutoPilot species are **memoryless** — the experiment journal is comprehensive but passive. Species code never retrieves past trial outcomes:
- `Seeder.run_batch()`: no past trial reads
- `NumericSwarm.suggest_trial()`: Optuna internal state only
- `PromptForge.propose_mutation()`: current failure context only, no past mutation outcomes
- `StructuralLab`: no past experiment consultation

Journal's `summary_text()` only consumed by Controller (last 20 entries as flat text) — poor substitute for targeted semantic retrieval.

**Proposed improvements** (ordered by effort):

1. **Failure analysis on rejection** — **DONE** (2026-03-15): `SafetyGate.analyze_failure()` builds structured narrative (VIOLATIONS/DEGRADED SUITES/ROUTING IMBALANCE/WARNINGS). `failure_analysis: str` field on `JournalEntry`. Wired into autopilot main loop. 6 tests.

2. **Strategy memory store** — **DONE** (2026-03-15): `StrategyStore` in `orchestration/repl_memory/strategy_store.py` — FAISS+SQLite, reuses `FAISSEmbeddingStore` and `TaskEmbedder`. Registered in `__init__.py`. 8 tests. Prerequisite for items 3-4.

3. **Evolution Manager species** (medium effort, highest long-term value): 5th species that runs every 5 trials, distills knowledge from recent outcomes into strategy memory via LLM summarization. Use explore worker (Qwen2.5-7B, port 8082) for cost-efficient processing.

4. **Species retrieval integration** (low effort once store exists): Wire `strategy_memory.retrieve()` into each species' proposal method. Biggest impact for PromptForge — add "Past mutation insights" to `_build_mutation_prompt()`.

**What NOT to adopt from EvoScientist**: Elo-based ranking (our Pareto archive is superior), fixed pipeline (our species architecture is more flexible), external embedding models (reuse existing FAISS infrastructure).

#### AutoResearch Ecosystem — Deep Dive (intake-148, intake-149)

**Source**: PraxLab (github.com/Hamza-Mos/praxlab), AutoResearch (github.com/karpathy/autoresearch)

The autoresearch pattern (Karpathy, March 2026) demonstrates that **tightly constrained agents** — one file, one metric, fixed 5-minute budget — outperform open-ended experimentation. 700 autonomous experiments produced ~20 additive improvements, 11% efficiency gain on Time-to-GPT-2. No programmatic orchestrator — the LLM IS the loop, guided by `program.md`.

PraxLab extends this with structured experiment memory (SQLite: hypotheses→experiments→results with mechanism confirmation/refutation), modular training approaches (pretrain/rl/sl/prime/gepa), git worktree isolation per experiment, and `lab` CLI (5 commands, zero deps) for cross-session knowledge persistence via `git rev-parse --git-common-dir`.

**Key architectural differences from AutoPilot:**
- Autoresearch has NO orchestrator code — trust is in the LLM's judgment + `results.tsv` ratchet
- PraxLab's `lab failures` dumps failed approaches at session start — agents never retry known-bad ideas
- Both use git as the rollback mechanism (commit before, `git reset HEAD~1` on failure)
- Autoresearch's simplicity criterion: "0.001 improvement + 20 lines of hacky code = not worth it"
- PraxLab's `--mechanism-confirmed`/`--mechanism-refuted` flags close the hypothesis loop

**Deep-dive audit identified 13 recommended actions** against our AutoPilot codebase, organized by priority:

##### HIGH PRIORITY — Wiring bugs (infrastructure built but not connected)

**1. Wire `failure_context` into PromptForge dispatch** (LOW effort)
`propose_mutation()` accepts `failure_context` and `per_suite_quality` parameters, but `dispatch_action()` at `autopilot.py:264` never passes them. PromptForge mutations are currently blind to why previous attempts failed. Fix: extract last failure narrative from journal and pass to `propose_mutation()`.

**2. Feed failure narratives into controller prompt** (LOW effort)
`SafetyGate.analyze_failure()` produces structured narratives stored in `JournalEntry.failure_analysis`, but `summary_text()` strips them to one-line summaries. The controller re-proposes similar failing actions because it never sees *why* things failed. Fix: add `recent_failures_text(n=5)` method returning failure narratives for the last N failed trials, inject into controller prompt.

**3. Populate `parent_trial` and `config_diff` journal fields** (LOW effort)
Both fields exist on `JournalEntry` but are never written. Without lineage tracking, neither the controller nor any analysis tool can reconstruct "trial 47 was a refinement of trial 42." Autoresearch gets this for free via git lineage; PraxLab gets it via hypothesis→experiment FK. Fix: set `parent_trial` to previous trial ID for same species, compute `config_diff` from action dict delta.

##### MEDIUM PRIORITY — Structural improvements from autoresearch patterns

**4. `lab failures`-style query at species proposal time** (MEDIUM effort)
PraxLab's `lab failures` dumps all failed approaches for the current task at session start. Our species have no equivalent. Add `journal.recent_failures(species=X, n=10)` and inject into each species' proposal context. Highest impact for PromptForge and StructuralLab.

**5. Per-suite quality trends in controller prompt** (MEDIUM effort)
The controller sees only aggregate quality — cannot say "coder suite declining for 5 trials." Add `journal.suite_quality_trend(last_n=10)` fed into controller prompt template.

**6. Persist `_consecutive_failures` counter** (TRIVIAL effort)
Safety gate's failure counter lives in memory, resets on process restart. After crash/restart, gate loses "2 of 3 failures before rollback" state. Fix: serialize to `autopilot_state.json`.

**7. Invalidate stale Optuna trials after regime changes** (MEDIUM effort)
When StructuralLab changes feature flags or PromptForge changes prompts, the optimization landscape shifts. Old Optuna trials become misleading. Add `numeric_swarm.mark_epoch(reason)` after structural/prompt changes that creates a new Optuna study or marks a regime boundary.

**8. Hypothesis-mechanism tracking on JournalEntry** (LOW effort)
PraxLab's SQLite stores not just outcomes but *why* something was tried and the *mechanism* expected to cause improvement. Our `JournalEntry` has `summary_text` but no structured hypothesis field. Adding `hypothesis: str` and `expected_mechanism: str` would improve Strategy Store retrieval quality.

##### LOWER PRIORITY — Design philosophy imports

**9. Tighter per-trial scope** (design change)
Our species propose actions across multiple dimensions simultaneously. Autoresearch constrains to one-file, one-variable changes for clean attribution. Consider constraining each trial to a single variable change — may improve convergence and make `config_diff` meaningful.

**10. Simplicity criterion for PromptForge** (LOW effort)
Autoresearch rejects improvements that add disproportionate complexity. Add prompt length delta to mutation evaluation — reject mutations that increase prompt size by >20% for <0.02 quality improvement.

**11. Git worktree isolation for PromptForge** (MEDIUM effort)
PraxLab isolates each experiment in a worktree. PromptForge currently mutates prompts in-place with git snapshots for rollback. Worktree isolation would make parallel prompt experiments safe and rollback trivial.

**12. Explicit eval trust boundary** (LOW effort, documentation)
Autoresearch's `prepare.py` is explicitly immutable — the agent cannot game the metric. Our EvalTower's scoring code is theoretically accessible to species. Make the eval trust boundary explicit in species constraints.

**13. Grep-parseable metric output from eval scripts** (LOW effort)
Autoresearch outputs `val_bpb: 0.993` for automated extraction. Standardize benchmark scripts to `key: value` stdout format to enable automated log analysis and `results.tsv`-style scoreboards.

#### GPD Governance Patterns — Deep Dive (intake-150)

**Source**: Get Physics Done (github.com/psi-oss/get-physics-done)

Deep-dive into GPD's four-phase workflow revealed six patterns directly applicable to EPYC governance (epyc-root + root-archetype), beyond the physics domain. GPD is a 23-agent, 61-command system with 6 MCP servers, 19 tiered verification checks, and a `ResearchContract` as central governance object.

**Gap analysis against our governance architecture** (from `agents/shared/`, `scripts/validate/`, `scripts/hooks/`):

| Gap | Current State | GPD Pattern |
|-----|--------------|-------------|
| No plan/task decomposition | Handoff → execution, no intermediate | Phase → Plan → Wave → Task with dependency DAG |
| Validators run manually | 5 validators exist, none triggered automatically | Verification registry with tiered auto-dispatch |
| No formal planning phase for new work | Handoff creation is free-form | ResearchContract: scope, claims, acceptance tests, forbidden proxies |
| No cross-role handoff protocol | Lead-developer delegation matrix, no artifact contract | Agent-to-agent artifact verification on disk |
| No session continuity state machine | Reconstruct from MEMORY.md + handoffs | Dual-write state (MD+JSON) with crash recovery + execution guards |
| Verification is advisory | Output contract in AGENT_INSTRUCTIONS.md, not enforced | Never-skippable gates (first-result, skeptical re-questioning, pre-fanout) |

**Recommended actions for epyc-root governance** (ordered by impact):

**14. Handoff contract template** (LOW effort)
GPD's `ResearchContract` binds scope to verification. Add a structured template to handoff creation requiring: scope (in/out), acceptance criteria, forbidden shortcuts, and verification method. Currently handoffs are free-form markdown with no required fields beyond status/created.

**15. Wire validators into pre-commit or post-session hook** (MEDIUM effort)
Our 5 validators (`validate_agents_structure.py`, `validate_agents_references.py`, `validate_claude_md_matrix.py`, `validate_doc_drift.py`, `check_numeric_literals.py`) exist but never run automatically. GPD's verification registry auto-dispatches checks by tier. Wire our validators into a post-session or pre-commit hook so drift is caught before it accumulates.

**16. Skeptical re-questioning gate for AutoPilot** (MEDIUM effort)
GPD's most novel governance pattern: execution halts when results are "proxy-only" (metric improved but via shortcut) or "anchor-thin" (no comparison to established result). Maps directly to AutoPilot's safety gate — add a `proxy_check()` that flags trials where quality improved but per-suite breakdown shows improvement concentrated in easy suites only. Currently the gate checks aggregate quality floor but not whether improvement is substantive.

**17. Forbidden proxy tracking** (LOW effort)
GPD explicitly tracks "forbidden proxies" — tempting shortcuts that don't actually demonstrate capability. For AutoPilot, this means maintaining a list of known-ineffective optimization directions (e.g., "lowering REPL token cap to improve speed at cost of quality") that species should never re-propose. Complements the `lab failures` pattern (#4 above) but is proactive rather than reactive.

**18. Context budget management for nightshift/autopilot** (MEDIUM effort)
GPD tracks context pressure (GREEN→RED) and auto-pauses at thresholds. Our nightshift and autopilot sessions can run for hours without context awareness. Add pressure-based pause points: at 60% context, checkpoint state; at 80%, force pause and create `.continue-here.md` equivalent.

**19. Convention locking for feature flag immutability** (LOW effort)
GPD's convention lock prevents changing notation once established. Apply same pattern to AutoPilot: once a trial establishes a baseline config, lock those parameters from species modification until explicitly unlocked. Prevents StructuralLab from accidentally reverting NumericSwarm's optimized parameters.

#### Cheat-Sheet Distillation Insight (intake-142)

**Source**: arxiv:2509.20820 "Distilling Many-Shot ICL into a Cheat Sheet" (EMNLP 2025)

When implementing `distill_skillbank` (StructuralLab action), adopt cheat-sheet's **difficulty-focused prompting**: "identify which examples you find most difficult, create a cheat sheet for only those." This outperformed broader textbook-style distillation in ablation (90.0% vs 88.9% avg on BBH). The principle: distill hard cases only, don't waste tokens on what the model already handles.

Also: cheat sheets transfer across models (GPT-4.1 → Gemini 2.0 Flash). Test whether skills distilled from architect-tier models improve worker-tier behavior — if so, distillation becomes a cross-tier knowledge transfer mechanism.

#### Hard-Negative Training Data for Routing Classifier (intake-176)

**Source**: ReasonIR (arxiv:2504.20595) — synthetic data generation for reasoning-aware retrieval

**Applies to**: `CHECKPOINT → TRAIN MLP + GAT` step in StructuralLab lifecycle. Currently `extract_training_data.py` generates training pairs from Q-values (positive = high-Q action for a given task context, implicit negative = random other actions). This lacks **explicit hard negatives** — examples that are semantically similar to the query but led to different optimal routing.

**Proposed change**: After extracting Q-value training pairs, generate contrastive hard negatives by finding same-domain tasks that succeeded with *different* roles. Example: "implement quicksort" (Q-value high for REPL/worker_coder) vs "explain quicksort complexity" (Q-value high for direct/worker_general). These are close in BGE-large embedding space but require different routing — exactly the decision boundary the MLP needs to learn.

ReasonIR's methodology: for each document, create a "plausibly related but ultimately unhelpful" negative. Adapted to routing: for each (task, best_role) pair, find the nearest-neighbor task in embedding space where a *different* role had the highest Q-value. This is a data pipeline change in `structural_lab.py` / `extract_training_data.py`, not an architecture change. Estimate: ~2 days to implement + validate via A/B gate.

---

## Evolution: Seeding → Claude-Debugger → AutoPilot → AutoResearch (2026-03-25)

### Evolution Chain

```
Seeding (passive eval, human fixes)
  → Claude-Debugger (active anomaly detection + Claude fixes during seeding)
    → AutoPilot (4-species continuous optimization)
      → AutoResearch (autonomous hypothesis-driven optimization)
```

### Claude-Debugger Subsumption

The Claude-Debugger (`src/pipeline_monitor/claude_debugger.py`) provides anomaly detection + hot-fix capabilities during seeding runs. Rather than maintaining it as a separate subprocess, its capabilities are **subsumed into the autoresearch framework**:

- **Anomaly detection** → runs as part of the experiment evaluation loop (post-trial analysis)
- **Hot-fix generation** → replaced by PromptForge's `targeted_fix` mutation with failure context
- **Session monitoring** → replaced by SafetyGate's consecutive failure detection + auto-rollback

The debugger code remains as reference but is not invoked separately. AutoResearch handles the same failure detection and correction loop as part of its experiment cycle.

### Stack-Config as Optimization Axis

The optimization surface now includes the full stack configuration:

| Axis | Species | Application Method |
|------|---------|-------------------|
| Model selection per role | StructuralLab | Restart (edit model_registry.yaml + orchestrator_stack.py) |
| Instance counts | StructuralLab | Restart |
| NUMA topology | StructuralLab | Restart |
| Tier assignment (HOT/WARM/COLD) | StructuralLab | Restart (mlock flags) |
| Acceleration flags | NumericSwarm | Restart (draft_max, moe_experts, lookup) |
| Cascade depth | StructuralLab | Restart (add/remove routing tiers) |
| General model prompting | PromptForge | Hot-swap (prompt .md files) |
| TOON compression | NumericSwarm | Hot-swap (encoding params) |

Stack experiments are expensive (require restart, ~2-5 min per trial). The autoresearch loop batches them: prompt/numeric experiments run hot-swap between stack experiments.

### program.md — Autoresearch Strategy Document

Located at `scripts/autopilot/program.md`. This is the single strategy document that guides autonomous experimentation, following the Karpathy autoresearch pattern:

- **Setup phase**: Initialize run, verify stack health, read state + recent failures
- **Immutable boundary**: Evaluation methodology, scoring, safety gates, core orchestrator code
- **Mutable scope**: Prompts, configs, registry, stack topology, feature flags, specialist pipelines
- **Goal metric**: Debug suite pass rate (deterministic, no LLM judge) for fast iteration
- **Experiment loop**: Hypothesize → commit → evaluate → keep/revert → repeat forever
- **Git-based ratchet**: Every improvement is a commit; degradations are reverted; best config always recoverable
- **Known dead ends**: Documents approaches that have been empirically exhausted (hybrid acceleration, lookup segfault, etc.)

Key design principles from autoresearch ecosystem research:
- **One variable per experiment** (clean attribution)
- **Simplicity criterion** (reject disproportionate complexity for marginal gain)
- **NEVER STOP** (continue experiments indefinitely until human interrupts)
- **Failure memory** (never retry known-bad approaches — `lab failures` pattern from PraxLab)

### Model-Agnostic Design

The framework tests any model available in the registry. New models (REAP variants, Nanbeige, MiroThinker, future downloads) become candidates with minimal manual effort — add to registry, autoresearch discovers and evaluates.

### Connection to Dynamic Stack Assembly

See [`dynamic-stack-concurrency.md`](dynamic-stack-concurrency.md) for the full NUMA scheduling architecture. Key integration points:

- **Infrastructure ready**: `RoundRobinBackend` supports runtime backend list changes
- **Stack experiments**: StructuralLab can modify `orchestrator_stack.py` within program.md constraints
- **Tier optimization**: HOT vs WARM vs COLD assignment is an autoresearch experiment, not a hardcoded decision
- **Constraint**: Primary user is single (Daniele). Per-request latency usually matters more than aggregate throughput

See also [`routing-and-optimization-index.md`](routing-and-optimization-index.md) for the umbrella view of all three optimization subsystems and their cross-cutting concerns.
