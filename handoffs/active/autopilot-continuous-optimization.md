# AutoPilot: Continuous Recursive Optimization

**Status**: **Phase 5 seeder refactor DONE** (2026-04-17). 3-way eval replaced with dynamic per-role eval. AR-3 killed — needs restart with new seeder. Blacklist cleaned (6→1 entry). Model quality signatures wired into controller prompt.
**Created**: 2026-03-08
**Updated**: 2026-04-17
**Location**: `epyc-orchestrator/scripts/autopilot/`

## Architecture

A continuous agent loop that autonomously optimizes orchestration intelligence through 4 optimizer "species", a tiered evaluation tower, 4D Pareto archive, and safety gates.

```
Controller (Claude CLI meta-reasoning)
  ├── Species 0: Seeder (per-role eval → Q-value training)
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
  eval_tower.py             # Tiered evaluation wrapping seeding infrastructure (on_question callback for TUI)
  config_applicator.py      # Hot-swap vs restart parameter routing
  meta_optimizer.py         # Species budget rebalancing + stagnation detection
  progress_plots.py         # 6 matplotlib visualizations (auto-updated)
  sentinel_questions.yaml   # 10 curated T0 validation questions
  program.md                # Human-editable autoresearch strategy document
  failure_blacklist.yaml    # Known-bad configs species must not re-propose
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
  repl_memory/strategy_store.py  # FAISS+SQLite strategy memory (species retrieval)
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
JournalEntry(trial_id, timestamp, species, action_type, tier, quality, speed, cost,
             config_diff, parent_trial, failure_analysis, hypothesis, expected_mechanism, ...)
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
| **Code mutation deep validation** | Syntax + shrinkage + public names + import test | Reject (added 2026-04-04) |
| **Catastrophic shrinkage** | >50% size reduction (code or prompt) | Reject (added 2026-04-04) |
| **Revert commit** | All reverts are git-committed | Prevents corruption as HEAD (added 2026-04-04) |

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
| Strategy store | `orchestration/repl_memory/strategy_store.py` | Species retrieve past insights before proposals |

## Train/Validate Split

- **Training** (Seeder): 579 debug suite questions + 53K pool → Q-value training via per-role eval
- **Validation** (EvalTower): HF benchmark questions (MMLU, GSM8K, etc.) → system quality (end-to-end, `force_role=""`)
- Prevents overfitting: debug suites train routing intelligence, benchmarks validate generalization

## Phase 5: Per-Role Seeder (2026-04-17)

The original 3-way eval (SELF:direct, SELF:repl, ARCHITECT) was a pre-autopilot simplification that prevented Q-values from learning per-model preferences (96% uniform after 7,211 decisions). Replaced with dynamic per-role eval.

**Key changes:**
- `discover_active_roles()` reads `server_mode` from model_registry.yaml → 6 active roles
- `evaluate_question_per_role()` tests each role with `force_mode=""` (natural mode) + `allow_delegation=True`
- Rewards keyed by role name (e.g., "frontdoor", "architect_general") not abstract classes ("SELF:direct")
- Periodic role refresh every 10 batches for stack change resilience

**Adaptation surface** (when stack changes): only `seeding_types.py` needs updates — `ROLE_PORT`, `SEEDING_EXCLUDED_ROLES`, `_REGISTRY_KEY_TO_ROLE`. See `wiki/autonomous-research.md` for full table.

**Deferred**: `route_per_role()` in retriever.py (follow-up once per-role Q-values accumulate).

## Evolution: Seeding → AutoResearch

```
Seeding (passive eval, human fixes)
  → Claude-Debugger (active anomaly detection + Claude fixes during seeding)
    → AutoPilot (4-species continuous optimization)
      → AutoResearch (autonomous hypothesis-driven optimization)
```

The Claude-Debugger's capabilities are **subsumed into the autoresearch framework**: anomaly detection runs as post-trial analysis, hot-fix generation is replaced by PromptForge's `targeted_fix` mutation, session monitoring is replaced by SafetyGate's consecutive failure detection + auto-rollback.

### Stack-Config as Optimization Axis

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

### program.md — Autoresearch Strategy Document

Located at `scripts/autopilot/program.md`. Human-editable strategy guiding autonomous experimentation:
- **Immutable boundary**: Evaluation methodology, scoring, safety gates, core orchestrator code
- **Mutable scope**: Prompts, configs, registry, stack topology, feature flags, specialist pipelines
- **Goal metric**: Debug suite pass rate (deterministic, no LLM judge) for fast iteration
- **Git-based ratchet**: Every improvement is a commit; degradations are reverted
- **Known dead ends**: Documents approaches that have been empirically exhausted

Key principles: one variable per experiment (clean attribution), simplicity criterion (reject disproportionate complexity), NEVER STOP, failure memory (never retry known-bad approaches).

### Related Handoffs

- [`dynamic-stack-concurrency.md`](dynamic-stack-concurrency.md) — Full NUMA scheduling architecture, Phases B-D complete
- [`routing-and-optimization-index.md`](routing-and-optimization-index.md) — Umbrella view of all optimization subsystems
- [`meta-harness-optimization.md`](meta-harness-optimization.md) — Execution trace feedback for PromptForge (3-tier plan)

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

# Generate report / plots
python scripts/autopilot/autopilot.py report
python scripts/autopilot/autopilot.py plot

# Checkpoint / restore
python scripts/autopilot/autopilot.py checkpoint --production-best
python scripts/autopilot/autopilot.py restore
```

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

## Implementation Status

All core infrastructure verified in code as of 2026-04-01:

- [x] AP-1: Wire `failure_context` into PromptForge dispatch (2026-03-29)
- [x] AP-2: Feed failure narratives into controller prompt via `summary_text()` (2026-03-29)
- [x] AP-3: Populate `parent_trial` and `config_diff` journal fields (2026-03-29)
- [x] AP-4: `lab failures`-style query — `journal.recent_failures()` (2026-03-29)
- [x] AP-5: Per-suite quality trends in controller prompt (2026-03-29)
- [x] AP-6: Persist `consecutive_failures` counter across sessions (2026-03-29)
- [x] AP-7: Invalidate stale Optuna trials after regime changes — `mark_epoch()` (2026-03-29)
- [x] AP-8: Hypothesis + expected_mechanism tracking on JournalEntry (2026-03-29)
- [x] AP-10: Simplicity criterion — reject >20% prompt growth for <0.02 quality (2026-03-29)
- [x] AP-12: TUI 4-panel live monitor (`--tui` flag) (2026-03-22)
- [x] AR-2: Smoke test passed — 5 dry-run trials verified (2026-03-29)
- [x] SafetyGate `analyze_failure()` — structured violation narrative (2026-03-15)
- [x] StrategyStore (FAISS+SQLite) built in `repl_memory/strategy_store.py` (2026-03-15)
- [x] Cost tracking — `estimated_cost` field on `RoutingResult` (2026-03-15)
- [x] B1: Wire `strategy_store.retrieve()` into PromptForge species (2026-04-01)
- [x] B2: Failure blacklist — `failure_blacklist.yaml` with auto-append (2026-04-01)
- [x] B3: Execution trace feedback — `inference_tap.log` → PromptForge (2026-04-01)
- [x] B4: `insights_text()` on ExperimentJournal (2026-04-01)
- [x] B5: Cross-species fertilization via insights injection (2026-04-01)
- [x] #4: Evolution Manager species — 5th species for knowledge distillation (2026-04-01)
- [x] #5: Skeptical re-questioning gate — `_proxy_check()` in SafetyGate (2026-04-01)
- [x] #6: Forbidden proxy seeding — known dead ends in `failure_blacklist.yaml` (2026-04-01)
- [x] #7: Context budget management — auto-checkpoint every 25 trials (2026-04-01)
- [x] #8: Per-species token budget — `SPECIES_TOKEN_BUDGETS` in meta_optimizer (2026-04-01)
- [x] Tier 2: Code mutations in PromptForge — `code_mutation` action type + allowlist (2026-04-01)
- [x] Deep code mutation validation — shrinkage + public names + import test (2026-04-04)
- [x] Catastrophic shrinkage guard — >50% reduction blocked for code and prompts (2026-04-04)
- [x] Revert commits — reverts auto-committed to prevent corruption as HEAD (2026-04-04)
- [x] TUI on_question for EvalTower — prompt panel shows actual questions during deep eval (2026-04-04)
- [x] Hybrid eval gate — T0 fast-reject + T1 real gate replaces saturated T0-only eval (2026-04-04)
- [x] Tier-aware safety gate — quality floor and regression scaled by eval tier (2026-04-04)
- [x] Baseline recalibration — recalibrated to T1/T2 scale (q=1.16) from inflated T0 scale (2026-04-04)

## Remaining Work — Prioritized

### HIGH priority (next compute session)

1. **AR-3 continuation**: Relaunch — `python scripts/autopilot/autopilot.py start --tui`
   - Run 2 (2026-04-02–04): 46 trials, 7 frontier. One useful change: `get_direct_answer_prefix()` in resolver.py (q 2.4→3.0)
   - **Corruption incident**: Trial ~25 replaced escalation.py (454→3 lines). API down 11+ hours. Safety hardened (5 gaps fixed).
   - ~~T0 saturated at q=3.0~~ **FIXED**: Hybrid eval (T0 fast-reject + T1 real gate) now gives honest signal per trial.
   - Baseline recalibrated to T1 scale (q=1.16). Safety gate tier-aware.
   - State at trial_counter=46


2. **AP-14: Structured deficiency classification** — Add `deficiency_category` enum to `JournalEntry` in `experiment_journal.py`. Values: QUALITY_FLOOR, REGRESSION, PER_SUITE, ROUTING_DIVERSITY, THROUGHPUT, CONSECUTIVE_FAILURES, CODE_VALIDATION, SHRINKAGE, REVERT. Auto-populated from SafetyGate violation type. Enables journal filtering by failure mode and downstream pattern detection in PromptForge.
   - Source: intake-265 deep-dive (AutoResearchClaw structured error taxonomy)

3. **AP-15: Species field verification audit** — Verify all 5 species populate `hypothesis` + `expected_mechanism` during AR-3. AP-8 added fields; confirm Seeder, NumericSwarm, PromptForge, StructuralLab, EvolutionManager actually fill them.
   - Acceptance: 100% of trials have non-empty hypothesis + expected_mechanism in JSONL
   - Source: intake-265 deep-dive

4. **AP-16: Instruction token budget tracking** — Add `instruction_token_count` (int) and `instruction_token_ratio` (float) to `EvalResult` in `eval_tower.py`.
   - Implementation: In `run_eval()`, before scoring, count tokens in all loaded `.md` templates (resolver, escalation, tool policy prompts) using `LlamaTokenizer` (already available). Ratio = instruction_tokens / total_input_tokens.
   - Emit via `to_grep_lines()`: `METRIC instruction_tokens: N` and `METRIC instruction_ratio: 0.XX`.
   - Add to `JournalEntry` for longitudinal tracking.
   - Alert: log warning if ratio > 0.20 (intake-272 threshold).
   - Acceptance: metric appears in JSONL for 10+ consecutive trials.
   - Source: intake-272 (AGENTS.md eval 20%+ cost), intake-271 (14-22% overhead)

5. **AP-17: Structural pruning in StructuralLab** — New `structural_prune` action type.
   - Implementation: `structural_lab.py` proposes block-level deletions from `.md` prompt files (full sections, not line-edits). Uses same allowlist as code_mutation.
   - Safety: deleted block saved in journal for rollback. Quality must be >= baseline AND instruction_token_ratio must decrease.
   - Depends on AP-16 (need the metric to evaluate prune impact).
   - Source: intake-272 (context files hurt), intake-271 (failure-driven only)

### P10 — GEPA PromptForge Integration (intake-327/345/240)

Source: hermes-agent-self-evolution (DSPy+GEPA), GEPA Full Program Adapter (93% MATH), GEPA paper (ICLR 2026 Oral). GEPA uses reflective trace analysis (ASI = Actionable Side Information) for 35x fewer rollouts than GRPO. Compatible with local inference (Ollama/vLLM format). 3-example minimum. MIT licensed.

- [x] AP-18: Install DSPy, wrap 3 routing prompts as DSPy Signatures — ✅ 2026-04-12. `dspy>=2.5.0` added to pyproject.toml. `src/dspy_signatures/` package: FrontdoorClassifier, EscalationDecider, ModeSelector signatures + config.py (configure_local_lm, configure_rlm). 8 smoke tests.
- [x] AP-19: GEPA frontdoor optimization — ✅ **Integrated into AR-3** (2026-04-12). `gepa_optimizer.py` adapter + `gepa` mutation type in PromptForge. 30% of PromptForge trials use GEPA evolutionary optimization via `OrchestratorGEPAAdapter` (evaluates through orchestrator API with sentinel questions). AR-3 journal collects comparison data automatically. 10 tests pass.
- [x] AP-20: GEPA Full Program Adapter eval — ✅ **Folded into AR-3** (2026-04-12). Resolved by comparing GEPA vs LLM mutation acceptance rates + Pareto frontier contributions in AR-3 journal after ~50 trials. No separate inference run needed.
- [ ] AP-21: PromptForge GEPA refactor decision — **Conditional on AR-3 data**. If GEPA trials dominate Pareto frontier after 50+ trials → increase GEPA ratio from 30% to 100%. If no improvement → keep mixed or revert to LLM-only.

### P11 — Autopilot Controller Upgrades (intake-328/329/349/320)

Source: MiniMax M2.7 3-component self-evolution harness (100+ autonomous rounds), dspy.RLM (WASM sandbox + sub_lm pattern), Unsloth RLVR (environment-first RL).

- [x] AP-22: Add `short_term_memory.md` per trial — ✅ 2026-04-12. `ShortTermMemory` class in `short_term_memory.py` (load/update/clear/to_text). Persists as markdown with 4 sections (hypotheses, directions, failures, context). Token-budgeted (~120 lines). Injected into CONTROLLER_PROMPT_TEMPLATE. CLI: `autopilot.py reset-memory`.
- [x] AP-23: Add explicit self-criticism step before next proposal — ✅ 2026-04-12. `self_criticism.py` with rule-based `generate_self_criticism()`. `SelfCriticism` dataclass (what_went_wrong, why, what_should_change, optimization_directions, keep/revert). Inserted between Evaluate and Record in controller loop. No inference cost.
- [x] AP-24: Formalize keep/revert protocol with structured forward-looking reasoning — ✅ 2026-04-12. `keep_revert_decision` and `optimization_directions` fields on JournalEntry. Centralized in `generate_self_criticism()`. Directions feed into short-term memory accumulator.
- [x] AP-25: Set up dspy.RLM with llama-server `/v1/` endpoint — ✅ 2026-04-12. `configure_rlm(main_lm_url, sub_lm_url)` in `src/dspy_signatures/config.py`. Coder as main LM, frontdoor as sub_lm. `test_connection()` health check. Integration testing deferred to AP-26 (needs inference).
- [ ] AP-26: Test dspy.RLM for autopilot tasks — long-horizon benchmark analysis where metadata-first context exploration avoids context window limits
- [ ] AP-27: Formalize eval tower tiers (T0/T1/T2) as RLVR verification functions with deterministic reward signals per tier (state matching, not LLM-as-judge). **Implementation plan**: See [eval-tower-verification.md](eval-tower-verification.md) EV-1–EV-7. Depends on EV-4 (calibration baseline) and P7 Ouro results.

### DEFERRED (explicit reasons)

2. ~~**GEPA integration** (intake-240)~~: **PROMOTED to P10** (2026-04-12). Deep-dive confirmed GEPA works with local inference, 35x cheaper than GRPO, 3-example minimum. No longer needs to wait for AR-3 PromptForge limitations — GEPA is strictly better.
3. **Hard-negative training data** (intake-176): Contrastive negatives for routing classifier. Only relevant when 500+ memories exist for retraining.
4. ~~**Git worktree isolation for PromptForge**~~: ✅ 2026-04-05. Implemented `worktree_manager.py` with `WorktreeManager` + `ExperimentContext`. Auto-reject safety default prevents corruption incidents like AR-3 trial ~25.
5. **Convention locking** (intake-150): Lock baseline parameters from species modification. Premature without more trials.

### Design considerations (no implementation needed)

6. ~~**Tighter per-trial scope**~~: ✅ 2026-04-05. Implemented as code enforcement via `_validate_single_variable()` in `autopilot.py`. Rejects multi-file, multi-flag, and multi-param actions before dispatch.
7. **Explicit eval trust boundary**: Document that EvalTower scoring code is immutable — species must never modify it. Add to `program.md` constraints.

## Research References

| Intake | Paper | Key Insight | Applied? |
|--------|-------|-------------|----------|
| 108 | EvoScientist (arxiv:2603.08127) | Evolution Manager separates knowledge distillation from execution | Informed Evolution Manager species design (#4) |
| 106 | Agentic Critical Training (arxiv:2603.08706) | GRPO-based self-reflection for quality-aware agents | Background — AutoPilot evaluates via benchmark tower instead |
| 105 | PostTrainBench (arxiv:2603.08640) | Autonomous post-training plateaus after ~5h | Calibrates expectations for AR-3 run length |
| 142 | Cheat-Sheet Distillation (arxiv:2509.20820) | Difficulty-focused distillation outperforms broad textbook style | Applies to `distill_skillbank` in StructuralLab |
| 148/149 | AutoResearch + PraxLab | Tight constraints + failure memory + git ratchet | Core design of `program.md` and failure blacklist |
| 150 | GPD (get-physics-done) | Skeptical re-questioning, forbidden proxies, convention locks | Informed items #5-7 in remaining work |
| 176 | ReasonIR (arxiv:2504.20595) | Hard-negative training data for routing classifier | Deferred (#10) until 500+ memories |
| 240 | GEPA (arxiv:2507.19457) | Pareto-aware prompt evolution, 35x fewer rollouts vs RL | Deferred (#9) — potential PromptForge replacement |
| 244 | Meta-Harness (arxiv:2603.28052) | Execution trace feedback +15pts over score-only | **Applied** (B3) — traces fed to PromptForge |
| 248 | SiliconSwarm@Ensue | Cross-agent knowledge transfer breaks plateaus | **Applied** (B1, B4, B5) — strategy store + insights + cross-species |
| 265 | Omni-SimpleMem (arxiv:2604.01007) | Bug fixes > tuning on broken baselines; 6-type discovery taxonomy; 4 suitability properties (we pass all 4) | AP-14 deficiency classification, AP-15 field audit |
| 271 | Skill Issue: Harness Engineering (HumanLayer) | Harness config drives ~28 TerminalBench-2 rank delta; 14-22% instruction overhead; CLI > MCP heuristic | AP-16, AP-17 |
| 272 | Evaluating AGENTS.md (ETH Zurich, 2602.11988) | Context files REDUCE success rates, +20% cost; help only when docs absent; thin-map not tested | AP-16, AP-17 |
| 273 | Context Rot (Chroma) | Shuffled > structured for RETRIEVAL only; semantic similarity compounds degradation | Background — informs CF experiments |
| 274 | The Complexity Trap (2508.21433) | Observation masking matches LLM summarization at 50% cost; hybrid 7-11% further | Validates two-layer compression architecture |
| 312 | Mismanaged Geniuses Hypothesis (Zhang/Khattab) | Decomposition space design is the key variable; 4B RLM→100% MRCRv2 via composition | Theoretical foundation for P10/P11 |
| 320 | Unsloth RL Environments | RLVR (verifiable rewards) maps 1:1 to eval tower; environment-first RL design | AP-27 |
| 327 | Hermes Agent Self-Evolution (NousResearch) | GEPA reflective trace analysis + 6-stage optimization loop; $2-10/run via API | P10 (AP-18–21) |
| 328/329 | MiniMax M2.7 Self-Evolution | 3-component harness (memory+feedback+optimization), 100+ autonomous rounds, 30% improvement | P11 (AP-22–24) |
| 345 | GEPA Full Program Adapter | 93% MATH (vs 67% base); evolves signatures+modules+control flow; 35x fewer rollouts | P10 (AP-20) |
| 349 | dspy.RLM Module | Metadata-first REPL exploration; sub_lm pattern; works with OpenAI-compatible /v1/ endpoint | P11 (AP-25–26) |

## Known Issues — KV Cache seq_add Crash on Qwen3.5 Hybrids (2026-04-15, PATCHED)

architect_general (Qwen3.5-122B-A10B, ports 8083+8183) crashed with assertion failure in `llama-kv-cache.cpp:614`:
```
GGML_ASSERT(hparams.n_pos_per_embd() == 1 && "seq_add() is only supported for n_pos_per_embd() == 1")
```

**Root cause**: Qwen3.5 architecture uses `LLAMA_ROPE_TYPE_IMROPE` (interleaved multi-rope, `n_pos_per_embd() == 4`) — same positional encoding as Qwen3-VL vision models, even in text-only mode. The `seq_add()` and `seq_div()` functions in `llama_kv_cache` had overly conservative assertions blocking any model with `n_pos_per_embd() != 1`. The crash triggered when the server's context checkpoint system called `seq_add` during KV chunk reuse (prompt cache hit with position shift). `get_can_shift()` also returned false, which would have caused `GGML_ABORT` if reached.

**Impact**: architect_general went down around trial 204, causing `routing_distribution` to collapse to `{"frontdoor": 1.0}`. Quality dropped from q≈2.10 to q≈1.14. Trials 204-215 data is tainted (frontdoor-only, no escalation routing). Autopilot's short-term memory has been annotated with operator note explaining the crash.

**Fix (2026-04-15)**: Patched 3 locations in `llama-kv-cache.cpp`:
1. Removed `GGML_ASSERT(n_pos_per_embd() == 1)` from `seq_add()` — the underlying `pos_add()` operates on scalar base position, and K-shift already handles IMROPE correctly (falls back to NEOX-style rotation via `build_rope_shift()`, see `@ngxson` workaround at line 1884)
2. Removed same assertion from `seq_div()`
3. Removed `n_pos_per_embd() > 1` guard from `get_can_shift()` — K-shift graph builder already supports IMROPE

Both NUMA instances relaunched with patched binary. Fix applies to all Qwen3.5 hybrids (QWEN35, QWEN35MOE arches). Dense models (Qwen3, Qwen3MOE) were unaffected (use NEOX rope, `n_pos_per_embd() == 1`).

**Verification needed**: Run seed_batch trials to confirm architect routing restored and quality recovers to q≈2.10.

## Known Issues — Architect Think-Block Loop (2026-04-14, RESOLVED 2026-04-15)

Qwen3.5-122B-A10B on `architect_general` enters degenerate `<think>` block loops during routing decisions. Model closes a think block, emits partial answer, then re-opens `<think>` repeatedly — burning the full 512-token budget per attempt.

**Root cause (revised 2026-04-15)**: The `--jinja` server flag loads Qwen3.5's native chat template, which includes `<think>`/`</think>` block scaffolding. The template itself primes the hybrid SSM+MoE model into think mode. Previous mitigations (`--reasoning off`, `_architect_early_stop()` streaming detection) were insufficient — the jinja template injects thinking preamble before `--reasoning` can suppress it.

**Fix applied (2026-04-15)**: Removed `--jinja` flag from architect_general server launch entirely. Without `--jinja`, llama-server falls back to generic ChatML template which has no thinking scaffolding — model never enters think mode. Also removed now-unnecessary `--reasoning off`. All other roles retain `--jinja`. Change in `orchestrator_stack.py:build_server_command()`.

**Previous mitigations (superseded)**:
- `--reasoning off` server flag (commit 0591952) — insufficient, jinja template still primed thinking
- `_architect_early_stop()` streaming detection (2026-04-14) — band-aid, didn't prevent wasted tokens
- `repeat_penalty`/`temperature` tuning — never applied, no longer needed

## Staleness Notes

- `optuna_orchestrator.py`: TPE/cluster patterns reusable; parameter ranges stale (predate current config/models.py)
- `seed_specialist_routing.py`: Canonical source at `epyc-orchestrator/scripts/benchmark/` (1,449 lines)
- `orchestrator_self_management.md` Phase 9: Deferred Optuna loop; architecture evolved significantly
- `pre-split-optimization-ab-test-plan.md`: Decision function reusable; specific paths broken post-split

## Verification Plan

1. **Smoke test**: `python autopilot.py start --dry-run --max-trials 5`
2. **Seeder integration**: Run 20-question batch, verify reward injection
3. **NumericSwarm**: Create Optuna study, suggest trials, verify cluster selection
4. **PromptForge**: Propose mutation, apply, verify git snapshot
5. **Full loop**: 10 trials across all species, verify journal + Pareto + safety gate
6. **Overnight**: 8-hour unattended run, check hypervolume trend

## Research Intake Update — 2026-04-06

### New Related Research
- **[intake-265] "Omni-SimpleMem: Autoresearch-Guided Discovery of Lifelong Multimodal Agent Memory"** (arxiv:2604.01007)
  - Relevance: AutoResearchClaw is a 23-stage autonomous research pipeline — directly comparable to our 4-species AutoPilot architecture
  - Key technique: Multi-agent debate + self-healing execution; autonomous experiment loop (~50 experiments)
  - Reported results: +411% F1 on LoCoMo, +214% on Mem-Gallery; bug fixes (+175%) > all hyperparameter tuning combined
  - Delta from current approach: Their finding that bug fixes and architectural changes vastly outperform hyperparameter tuning validates prioritizing Species 2 (PromptForge) and Species 3 (StructuralLab) over Species 1 (NumericSwarm). Consider increasing structural species budget allocation. The 23-stage pipeline with debate is more sophisticated than our 4-species approach — may inform future species design.

- **[intake-267] "ByteRover: Agent-Native Memory Through LLM-Curated Hierarchical Context"** (arxiv:2604.01599)
  - Relevance: Agent-native memory where the LLM itself curates knowledge in hierarchical markdown files — validates autopilot state management direction
  - Key technique: Hierarchical Context Tree with importance scoring + recency decay; sub-100ms retrieval
  - Delta from current approach: Our autopilot_state.json is a flat JSON store. ByteRover's hierarchical approach with LLM-driven curation could inform how autopilot manages its experiment journal and Pareto archive for better context retrieval across long runs.

### Deep-Dive Correction (2026-04-06)
**Caveat on intake-265**: The "bug fixes > tuning" headline is misleading. The baseline was catastrophically broken (F1=0.117 vs SimpleMem SOTA 0.432) — a missing `response_format=json_object` caused 9x verbosity. The finding generalizes to "fixing broken systems beats tuning broken systems," not "structural always beats numeric." Our AutoPilot operates on a functioning system where NumericSwarm is in the right regime. **No species budget rebalancing needed from this paper alone.** However, two small improvements validated: (1) add structured deficiency classification to experiment_journal.py error handling, (2) ensure all species populate hypothesis/expected_mechanism journal fields. The 4 autoresearch suitability properties (scalar metrics, modular architecture, fast iteration, version-controlled modifications) are a useful checklist — our AutoPilot satisfies all 4.

## Research Intake Update — 2026-04-12

### New Related Research
- **[intake-327] "Hermes Agent Self-Evolution"** (NousResearch) — DSPy+GEPA skill optimization
  - Relevance: Directly applicable to PromptForge species — evolutionary optimization of skills/prompts without GPU
  - Key technique: GEPA reflective evolutionary search with execution trace analysis
  - Delta from current approach: Our PromptForge uses LLM-guided mutation. GEPA uses evolutionary + Pareto-optimal selection. Their $2-10 per run is API-based; adapting to local models eliminates cost. Guardrails (test validation + human review) are more conservative than our safety gates.
- **[intake-338] "Agent Lightning"** (Microsoft Research) — Zero-code agent optimization
  - Relevance: Three optimization modes (RL, prompt optimization, SFT) map to our species: RL→NumericSwarm, prompt→PromptForge
  - Key technique: Framework-agnostic tracing + optimization. Zero code change adoption.
  - Delta from current approach: Agent Lightning could optimize our orchestrator without modifying existing code. The trajectory-level aggregation addresses our per-question vs per-trajectory eval gap.
- **[intake-344] "LightningRL: Hierarchical Credit Assignment"** (arxiv:2508.03680)
  - Relevance: Solves autopilot evaluation granularity problem — attributes task success to specific orchestrator decisions
  - Key technique: Per-LLM-request credit assignment + reward scoring, compatible with PPO/GRPO
  - Delta from current approach: We evaluate at task-level (T0/T1/T2). LightningRL enables per-step attribution. Could dramatically improve PromptForge mutation signal quality.
- **[intake-345] "GEPA Full Program Adapter: 93% MATH"** (DSPy tutorial)
  - Relevance: Evolves entire program structure (not just prompts) — 93% vs 67% baseline on MATH
  - Key technique: GEPA evolving DSPy signatures, modules, and control flow with as few as 3 examples
  - Delta from current approach: PromptForge only mutates prompt templates. GEPA Full Program Adapter could evolve routing logic, tool definitions, and escalation pipeline. The +26pp improvement is transformative.

### Deep-Dive Synthesis (2026-04-12)
**Cross-cutting finding from 26-entry deep-dive**: Four converging research threads point to a major autopilot upgrade path:
1. **GEPA** (intake-327/345): Reflective trace analysis + evolutionary Pareto search. 35x more efficient than GRPO. 3-example minimum. Compatible with our local inference (Ollama/vLLM format). **Priority #1 for PromptForge upgrade.**
2. **dspy.RLM** (intake-349): Metadata-first context exploration via REPL sandbox. Sub-LM pattern maps to our coder+frontdoor stack. Directly addresses context window limitation for long autopilot runs. **Priority #2 for autopilot infrastructure.**
3. **MiniMax M2.7 self-evolution** (intake-328/329): Three-component harness (short-term memory markdown + self-criticism + forward-looking optimization) over 100+ autonomous rounds. Pattern directly implementable in our controller. Add `short_term_memory.md` per trial, explicit self-feedback step before next proposal, and formalized keep/revert protocol.
4. **Unsloth RLVR** (intake-320): Our eval tower IS an RLVR environment. Formalize T0/T1/T2 as verification functions, not just benchmarks. Design reward signals per tier. If cloud GPU becomes available, export environments for actual model RL training.

**Architectural theme**: All entries converge on "context efficiency through structured indirection" — sandbox over prompt, REPL over context, reflection over gradient, retrieval over fullcontext. Validates our multi-model approach over single-model scaling.

## Research Intake Update — 2026-04-14

### New Related Research
- **[intake-363] "LLM-as-a-Verifier"** (github.com/llm-as-a-verifier)
  - Relevance: General-purpose verification framework using logprob-based scoring with criteria decomposition — directly relevant to AP-27 eval tower formalization as an alternative to LLM-as-a-Judge
  - Key technique: R(t,τ) = (1/CK) Σ p_θ(v_g|t,c,τ)·φ(v_g) — multi-criteria, repeated verification, granularity scaling
  - Reported results: Terminal-Bench 2: 86.4% (from 81.8%), SWE-Bench Verified: 77.8% (from 76.1%)
  - Delta from current approach: AP-27 specifies "state matching, not LLM-as-judge" for verification functions. LLM-as-a-Verifier offers a middle ground — uses LLM logprobs but for structured verification rather than open-ended judgment. Gemini API dependency is a blocker for local deployment.
- **[intake-371] "ThinkPRM: Process Reward Models That Think"** (arxiv:2504.16828)
  - Relevance: Generative PRM that verifies solution steps via verification chain-of-thought — applicable to eval tower step-level attribution
  - Key technique: Fine-tunes long-CoT models as verbalized step-wise reward models; achieves PRM800K parity with only 1% of labels
  - Reported results: 8% better OOD on GPQA-Diamond, 4.5% on LiveCodeBench vs discriminative PRMs
  - Delta from current approach: Our T0/T1/T2 tiers are outcome-level. ThinkPRM enables per-step process reward attribution within evaluation, complementing LightningRL (intake-344) per-step credit assignment.
- **[intake-370] "Aletheia: RLVR for Code Verifiers"** (arxiv:2601.12186)
  - Relevance: Systematic ablation of RLVR training recipes across model scales — directly informs AP-27 verification function design
  - Key technique: Scale-dependent optimization recipes — small verifiers need on-policy training; large need negative samples + thinking traces
  - Reported results: Compute-optimal roadmap for practitioner deployment
  - Delta from current approach: Our eval tower targets are fixed tiers. Aletheia shows that the training recipe matters more than architecture at small scales — relevant if we export environments for RL training per intake-320.
- **[intake-368] "SWE-RM: Execution-Free Feedback for SWE Agents"** (arxiv:2512.21919)
  - Relevance: MoE reward model (30B total, 3B active) providing execution-free feedback — relevant to eval tower reward signal design
  - Key technique: MoE architecture with controlled data composition experiments; classification accuracy and calibration critical for RL
  - Reported results: Qwen3-Coder-Flash 51.6%→62.0%, Qwen3-Coder-Max 67.0%→74.6% on SWE-Bench Verified
  - Delta from current approach: SWE-RM shows TTS performance doesn't guarantee RL effectiveness — our eval tower must separately validate classification accuracy and calibration, not just pass rates.

**Synthesis**: The 5 verification research entries above (intake-363/367/368/370/371) are consolidated into a standalone handoff: [eval-tower-verification.md](eval-tower-verification.md). That handoff provides the implementation plan (EV-1–EV-7) for ECE/AUC metrics, ThinkPRM deployment, cross-family verification, and Scoring Verifiers benchmark integration that these papers motivate. AP-27 now points to that handoff as its implementation plan.

### Future AR-3 Signal: Branching Density (2026-04-15 deep-dive)

intake-378 (arxiv:2604.01702) identifies Propose step ratio as a quality metric for reasoning traces. High branching density (>0.30) indicates unproductive exploration — the model is diverging across alternative approaches rather than converging on a solution.

**Relevance to AR-3**: If a config change (PromptForge mutation, StructuralLab flag, NumericSwarm param) causes higher average branching density in solver outputs, that is a negative signal even if accuracy is unchanged — the model is working harder for the same result, increasing cost.

**Lightweight implementation**: Add branching keyword scan to T0/T1 eval output analysis. Report as `METRIC branching_density: X.XX` via existing `to_grep_lines()` mechanism in `safety_gate.py`. The SafetyGate quality floor could incorporate: reject trials where branching density increases without quality gain.

**Priority**: LOW — only relevant when AR-3 experiments touch solver behavior (prompt mutations, model swaps, reasoning budget changes). Cross-ref: `routing-intelligence.md` (Category C quality signal), `research/deep-dives/sft-generalization-reasoning-patterns.md`.

## Research Intake Update — 2026-04-17

### New Related Research

- **[intake-394] "Evolver: GEP-Powered Self-Evolution Engine for AI Agents"** (repo: EvoMap/evolver)
  - Relevance: directly overlaps with the PromptForge species and the autopilot governance/safety layer — Evolver implements a protocol-bound evolution pattern with primitives (Gene/Capsule/EvolutionEvent JSONL assets, protected source files, strategy presets) that mirror what our autopilot safety gates already need.
  - Key technique: GEP (Genome Evolution Protocol) — auditable, protocol-constrained prompt evolution; strategy preset weighting (innovate/optimize/repair intent mix, e.g. 80/15/5 balanced vs 0/20/80 repair-only); log-signal extraction for selector-driven prompt routing; protected-source-files to prevent self-overwrite.
  - Reported results: none (no benchmarks, no empirical claims in README).
  - Delta from current approach: adds an **auditability-first asset schema** (Gene/Capsule/EvolutionEvent) as a reference to compare against our own PromptForge artifact scheme; the protected-source-files pattern is directly adoptable as a safety gate for autopilot mutations. Not adopt_component (Node.js, tied to evomap.ai hub, no benchmarks). Cross-refs intake-327 (GEPA/DSPy), intake-328 (MiniMax self-evolving).
