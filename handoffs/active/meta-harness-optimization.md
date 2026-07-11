# Meta-Harness: Automated Harness Optimization

**Status**: COMPACTED 2026-05-28; J9 validation closed 2026-06-12; Meta-Harness implementation/coordination queue closed 2026-07-11. Remaining EV-10 validation lives in Package K/operator-run inference work.
**Created**: 2026-04-01
**Updated**: 2026-07-11
**Priority**: HIGH (upgraded 2026-07-08 per rec-001: literature sweep confirms meta-harness as central paradigm)
**Categories**: agent_architecture, benchmark_methodology
**Parent index**: [routing-and-optimization-index.md](routing-and-optimization-index.md)
**Completed ledger**: [meta-harness-optimization-completed-through-2026-05-28.md](../completed/meta-harness-optimization-completed-through-2026-05-28.md)

## Executor Start Here

Do not rebuild the full Meta-Harness outer loop now. The targeted proposer, trace, new-file mutation, AutoMem schema-evolution lane, harness-search scoping, HTIR, SEAGym, and SkillOpt/EV-10 coordination items are closed. Remaining work belongs to the owning validation lanes: EV-10 Package K paired A/B, N2/J11 restart-gated eval evidence, and separate BSV/URE trace follow-through. The first observe-only harness metric validation pass is complete and did not justify letting current rule metrics affect acceptance or Pareto selection. AutoMem's MI210 LoRA specialist remains deferred until the local scaffold/schema path shows value on our suites.

## Outstanding Tasks

- [x] **MH-7 contrastive traces**: upgrade `eval_tower.capture_recent_traces()` to `capture_contrastive_traces(k_success=2, k_failure=2)` once MH-6 can absorb richer inputs. ✅ 2026-07-11
- [x] **MH-9 new-file mutation type**: add directory-scoped `new_file` mutation support after MH-6/7 define the cost/quality contract; include traversal and collision tests. ✅ 2026-07-11
- [x] **HLE-3 / J9 fixed-model harness lane**: observe-only analysis closed 2026-06-12 over 580 metric-bearing trials from `/mnt/raid0/llm/tmp/autopilot_journal_snapshot_1781290411.jsonl`. `execution_fidelity` and `planning_stability` separate keep/revert but mostly mirror existing task-quality/safety signals, so they remain diagnostic/advisory. `feedback_interpretation`, `memory_coherence`, and `recovery_rate` stay dashboard-only. No HLE metric is eligible for Pareto promotion before N2 ledger/sequential verdict redesign.
- [x] **SkillOpt / EV-10 coordination**: keep the skill-efficacy gate work in [eval-tower-verification.md](eval-tower-verification.md) and the next AR-3 restart plan; do not mix it into MH-6/7/9 without an explicit feature flag. ✅ 2026-07-11

## Dependency Forks

| Outcome | Next action |
|---|---|
| HLE metrics separate accepted vs rejected configs and missingness <=20% | Eligible for HLE-4 promotion as guardrail/co-objective in [autopilot-continuous-optimization.md](autopilot-continuous-optimization.md) only if they also show independent predictive signal after N2 ledger/sequential verdict redesign. |
| HLE metrics show no signal or high missingness | Keep dashboard-only; never use as a hard gate. |
| MH-6 improves proposer discipline without regressions | Proceed to MH-7 contrastive traces. |
| MH-7 trace volume hurts cost or proposer quality | Keep raw recent traces as fallback and tune `k_success/k_failure`. |
| MH-9 new-file mutations create safety or review overhead | Keep edit-only allowlist until a stronger isolation story exists. |

## Completed Scope

| Scope | Result | Ledger |
|---|---|---|
| Tier 1 execution-trace feedback | Landed. | [completed ledger](../completed/meta-harness-optimization-completed-through-2026-05-28.md) |
| Tier 2 code mutation search space | Landed with allowlist, syntax validation, rollback, safety gate, and simplicity criterion. | [completed ledger](../completed/meta-harness-optimization-completed-through-2026-05-28.md) |
| MH-4 GEPA search eval | Folded into AR-3 Package D. | [completed ledger](../completed/meta-harness-optimization-completed-through-2026-05-28.md) |
| MH-5 Agent Lightning telemetry pattern | Landed as `TelemetryCollector`/OTLP-compatible records. | [completed ledger](../completed/meta-harness-optimization-completed-through-2026-05-28.md) |
| MH-6 proposer-prior template | Landed in `PromptForge._build_code_mutation_prompt()` with explicit read order, `expected_quality_delta`, `expected_cost_delta`, and no-task-specific-hints output contract. Focused PromptForge/GEPA tests passed. | orchestrator `9da18568` |
| MH-7 contrastive traces | Landed in `eval_tower.capture_contrastive_traces(k_success=2, k_failure=2)` with contrastive trace-bank labeling, trial-end state refresh, and PromptForge preference over recent-trace fallback. Validation: focused pytest suite (171 passed), Ruff format/check, and `git diff --check` on touched orchestrator/test files. | orchestrator session checkpoint 2026-07-11 |
| MH-9 new-file mutation support | Landed with bounded `new_file` mutation proposals under the existing code-mutation safety surface, parent-directory dirty checks, traversal/collision rejection, fresh-file apply/revert handling, and `FileExistsError` skip coverage. | orchestrator `88639b1f` |
| AutoMem schema-evolution new-file lane | Landed as a directory-scoped extension to MH-9: `PromptForge` may now create default-inert schema/scaffold modules under `orchestration/repl_memory/schema_evolution/`, and the planner-facing code-mutation schema advertises that root. No SafetyGate, Pareto, blacklist, threshold, planner spend-breaker, or live-runtime behavior changed. | orchestrator `775703a0` |
| MH-10 agentic harness-search scoping | Closed as a contract, not a live loop: agentic task-generation may propose prompt-free, verifier-backed harness candidate manifests, but self-generated tasks enter audit/OOD views only until human-curated and validated against W2/W3/real-suite baselines. Implementation targets are `select_real_suite_v1.py`, `materialize_real_suite_v1.py`, `eval_task_coverage_report.py`, `eval_tower_seagym_views.py`, and future proposer/report tooling; no SafetyGate/Pareto/baseline admission changes. | root handoff checkpoint 2026-07-11 |
| MH-12 SEAGym evaluation views | Landed observe-only EvalTower result accounting in `scripts/autopilot/eval_tower_seagym_views.py`: classifies compact `EvalResult.question_results` / journal-shaped eval payloads into train, validation, test, replay, and OOD views without changing `_aggregate`, `_eval_question`, `_compact_question_result`, SafetyGate, Pareto admission, or baseline calibration. Validation: `pytest tests/unit/test_eval_tower_seagym_views.py tests/unit/test_eval_tower_concurrency_metrics.py -q` (32 passed), Ruff check/format on new files. | orchestrator `8d4e5146` |
| SkillOpt / EV-10 coordination | Closed as an ownership and flag-isolation boundary: EV-10a decision logic and default-off accept-path wiring remain in `scripts/autopilot/skill_efficacy.py` and `scripts/autopilot/actions.py` behind `AUTOPILOT_SKILL_EFFICACY_GATE`; Package K `K-SKILL-1` owns deploy/restart and paired A/B validation. The flag was not enabled, no live autopilot restart was performed, and the planner spend breaker remains opt-in/off. | root handoff checkpoint 2026-07-11 |
| HLE-1/HLE-2 observe-only fields | Schema and rule-based defaults landed in orchestrator commits `931e43c` and `9222a19`; J9 analysis closed 2026-06-12 with diagnostic-only verdict. | [completed ledger](../completed/meta-harness-optimization-completed-through-2026-05-28.md) |

## Key Files

- `/mnt/raid0/llm/epyc-orchestrator/scripts/autopilot/species/prompt_forge.py`
- `/mnt/raid0/llm/epyc-orchestrator/scripts/autopilot/eval_tower.py`
- `/mnt/raid0/llm/epyc-orchestrator/scripts/autopilot/eval_task_coverage_report.py`
- `/mnt/raid0/llm/epyc-orchestrator/scripts/autopilot/eval_tower_seagym_views.py`
- `/mnt/raid0/llm/epyc-orchestrator/scripts/autopilot/hle_metrics.py`
- `/mnt/raid0/llm/epyc-orchestrator/scripts/tasks/select_real_suite_v1.py`
- `/mnt/raid0/llm/epyc-orchestrator/scripts/tasks/materialize_real_suite_v1.py`
- [autopilot-continuous-optimization.md](autopilot-continuous-optimization.md)
- [bulk-inference-campaign.md](bulk-inference-campaign.md)
- [eval-tower-verification.md](eval-tower-verification.md)
- [unified-trace-memory-service.md](unified-trace-memory-service.md)

## Reporting Instructions

After MH or HLE work, update this handoff with the code path, feature flag, validation command, observe-only result, and promotion/parking decision. Mirror priority changes in [routing-and-optimization-index.md](routing-and-optimization-index.md), Package J in [bulk-inference-campaign.md](bulk-inference-campaign.md), and [master-handoff-index.md](master-handoff-index.md) if queue priority changes.

## Research Intake Update — 2026-07-08: Literature Expansion (rec-001)

### Meta-Harness Optimization — Full Literature Sweep

**14-paper deep-dive** (intake-784 through intake-797) confirms meta-harness as the central unifying paradigm. Three clusters converge on the same insight: **harness engineering > model weights**.

**Cluster A — Agentic Harness Search (adopt_selectively)**:
- **Meta-Harness** (intake-784, arxiv 2603.28052, Stanford): outer-loop searches over harness code; +7.7pt on text classification at 4x fewer tokens; +4.7pt on IMO-level math across 5 held-out models. Agentic proposer with filesystem experience access.
- **MCE** (intake-787, arxiv 2601.21557): bi-level CE optimization with agentic crossover; 5.6-53.8% improvement (mean 16.9%). Meta-level agent refines skills over execution history.
- **AFlow** (intake-788, arxiv 2410.10762): MCTS over code-represented workflows; +5.7% avg across 6 benchmarks.

**Cluster B — Self-Improvement Loops (worth_investigating)**:
- **DGM** (intake-785, arxiv 2505.22954): self-code-modification + empirical validation; SWE-bench 20%→50%, Polyglot 14.2%→30.7%. Archive-based evolution with parallel exploration tree.
- **SIA** (intake-789, arxiv 2605.27276): combines harness + weight updates; LawBench +25.1%, GPU kernel +12.4%. **CAUTION**: weight updates inapplicable to our CPU stack; harvest harness-only patterns.
- **STOP** (intake-786, arxiv 2310.02304): recursive scaffolding self-improvement; seed improver bootstraps itself. COLM 2024.

**Cluster C — Harness Diagnostics & Evaluation (adopt_selectively)**:
- **SEAGym** (intake-790, arxiv 2606.17546): evaluation environment for self-evolving harnesses; train/validation/test/replay/OOD views; finds frequent updates may fail to improve held-out performance.
- **HarnessFix** (intake-793, arxiv 2606.06324): trace-grounded diagnosis; HTIR intermediate representation; +6.3% to +18.4% improvement. Failure attribution to specific harness artifacts.
- **KernelBench** (intake-796, arxiv 2606.20128): seeded fuzzing for kernel correctness; catches 9/9 buggy kernels, passes 15/15 controls.

**Synthesis — Actionable for EPYC**:
1. **MH-10 harness-search scoping**: Meta-Harness methodology applied to our own seeding pipeline — agentic harness proposer with filesystem experience access for evaluation task generation. Gate: validation against curated baseline (SkillsBench v3 caution: self-generated skills are net-negative -1.3pp).
2. **MH-11 HTIR failure attribution**: HarnessFix's HTIR (Harness-aware Trace IR) normalizes trajectory evidence into step-level data-flow/control-flow. Directly harvestable for our eval-tower critic to attribute failures to specific harness artifacts.
3. **MH-12 SEAGym evaluation views**: train/validation/test/replay/OOD views from SEAGym are applicable to our eval-tower verification. Prevents the "frequent updates fail to improve held-out" anti-pattern.

- [x] **MH-10 agentic harness search scoping** — adapt Meta-Harness proposer contract for our seeding pipeline; gate on curated-baseline validation. ✅ 2026-07-11
  **Scope decision**: MH-10 is a candidate-generation/audit lane, not a live autonomous benchmark-writing gate. The proposer may draft `harness_task_candidate.v1` manifests that name source evidence (`task_record_ref`, question-pool row, HTIR failure record, eval coverage deficit), workload class, target suite/capability, intended SEAGym view, verifier/scoring method, expected quality/cost delta, and privacy class. It must not emit raw private prompt text into committed manifests, synthesize unverifiable answers, or promote self-generated tasks into SafetyGate/Pareto/baseline selection.

  **Read-order contract**: proposer inputs are, in order, (1) real-suite/F1 curated manifests and W2/W3 baseline evidence, (2) EvalTower coverage deficits from `eval_task_coverage_report.py`, (3) HTIR/contrastive failure clusters from MH-11, (4) SEAGym view accounting from MH-12, and (5) StrategyStore/Pareto stepping-stone hints. Outputs must state `no_task_specific_hints=true` and cite why the candidate generalizes beyond one observed prompt.

  **Gate contract**: generated candidates start in `audit` or `ood` views only. A candidate can move toward validation/test only after deterministic/programmatic/code-execution scoring exists, privacy is local-safe, and a curated-baseline comparison against W2/W3/`real_suite_v1` shows no per-class or per-suite negative delta. Any eventual live accept path must remain feature-flagged, reuse EV-10/SkillsBench negative-transfer discipline, and require human-curate confirmation before entering gate material.
- [x] **MH-11 HTIR failure attribution** — implement harness-aware trace IR for eval-tower critic. ✅ 2026-07-11
  Landed in orchestrator commit `b9fcdf5e` (`Add harness trace IR for PromptForge context`); focused Ruff, `py_compile`, and pytest validation passed on the touched orchestrator files, and the post-commit preflight stayed non-restart-safe so autopilot was not restarted.
- [x] **MH-12 SEAGym evaluation views** — add train/validation/test/replay/OOD views to eval-tower. ✅ 2026-07-11
  Landed as observe-only result/journal payload accounting in orchestrator commit `8d4e5146` (`Add observe-only SEAGym eval views`); it deliberately avoids the high/critical inline scoring path and has no SafetyGate/Pareto/baseline effect.

### Prior Research (2026-07-02)

### New Related Research
- **[intake-753] "Don't Train the Model, Evolve the Harness"** (HF Space, Joel Niklaus; applies Meta-Harness = intake-244 / arXiv 2603.28052)
  - **Relevance:** An external, empirical instance of *our exact loop* on a frozen open-weight model — DeepSeek-V4-Pro lifted 0% → 80.1% held-out pooled-criterion on Harvey's Legal Agent Benchmark with **zero weight changes**, purely by evolving the harness. Maps ~1:1 onto our HLE-3/J9 fixed-model harness lane.
  - **Key techniques worth adopting:** (1) **prefer deterministic-code mechanisms over prompt edits** for weak/frozen models — 5 of the top 6 accepted harnesses were code, not prompts (validates our Tier-2 code-mutation search over pure PromptForge prompt-editing); (2) cost-aware scoring `pooled_criterion + 0.5·all_pass − 0.005·tokens_per_million` + copy-and-adapt accepted-frontier inheritance; (3) **3-trial noise-margin promotion** (≥1 pt clears incumbent) — mirrors our resolution-aware / mad_noise gate; (4) **tune the harness per-served-model** — code fixes transferred across families (V4-Flash +14.4 pts) but prompt playbooks did NOT (Nemotron-3 Ultra +0.4 pts).
  - **Reported results:** dev pooled 63.1→83.3; held-out test 63.4→80.1; beat external harnesses on the same model (Pi 45.4, Goose 23.2, mini-swe-agent 3.5).
  - **Delta from current approach:** we already run this loop (PromptForge proposer + eval_tower + cost-aware Pareto); the additive value is the code>prompt mechanism-preference finding and the per-model-transfer caveat. **MEASUREMENT.md caveat:** single legal benchmark, LLM-judge scoring, non-peer-reviewed → observations to shape the proposer contract, NOT to gate promote/revert without local re-measurement.
  - **Reference-chased expansion (intake this run):** Darwin Gödel Machine (arXiv 2505.22954) — self-code-rewriting evolutionary agents, directly relevant to autopilot species/strategy generation.

## Research Intake Update — 2026-07-11

### New Related Research
- **[intake-798] "The Gemma Challenge and the Case for Agent Collabs"** (HF blog; Patiño, Tunstall, Sanseviero, von Werra — HF + Google DeepMind)
  - Relevance: this is a live, 6-day, 100+ agent *autoresearch harness* run (optimize gemma-4-E4B TPS under a quality gate). Its documented failure modes are exactly the ones our meta-harness / autopilot exploration loop must defend against.
  - Key patterns to harvest (operator-review candidates, not imperatives — external source):
    - **Agent Collapse (exploration failure):** agents converged fast onto a narrow set of optimization axes and avoided harder avenues (custom quant, large kernels, engine changes). Attributed to (a) weak exploration taste and (b) **message-board "context rot"** — a long shared log self-reinforces early topics as newcomers read/post similar ideas. → Our PromptForge proposer + Pareto selection should be probed for the same monoculture collapse; consider an explicit exploration-bonus / novelty term and diversity-preserving proposal sampling (ties to MH-7 contrastive traces: feed *contrastive* success+failure traces, not just recent ones, to break the reinforcement loop).
    - **Metric self-policing / reward-hacking:** a PPL-only gate was gameable (agents held PPL under threshold while degrading the model); a subgroup flagged it and self-restricted to lossless. Operators then layered MMLU-Pro + GPQA-Diamond gates. → Corroborates our eval-tower safety-gate posture; argues for **layered/rotating quality gates** and treating "held the cheap gate but no downstream check" as a first-class safety signal. External corroboration: SpecBench/TRACE/BenchJack (2026) show proxy metrics are provably hackable and RL post-training raised exploit rates 0.6%→13.9%.
    - **Taskforces + channels/threads** to counter collapse and message-flood — a structural analogue to our workflow-pressure / T3 planner-visible topics; suggests giving autopilot topic-scoped attention rather than one flat journal.
    - **Agent trace sharing for attribution + failure reuse** ("learn from failed attempts, don't repeat mistakes") — directly overlaps HALO trace-loop + unified-trace-memory + our episodic-memory gating.
  - Delta from current approach: our meta-harness optimizes a single harness in isolation; the collab frames a *population* of harnesses sharing a persistent workspace + leaderboard, with HITL steering agents out of hopeless loops. The anti-collapse and gate-hardening lessons transfer directly even at our single-daemon scale.
  - Numbers are OBSERVATION-grade (challenge-internal, GPU, self-reported) — do not gate.

## Research Intake Update — 2026-07-11 (batch 2)

### New Related Research
- **[intake-809] "AutoMem: Automated Learning of Memory as a Cognitive Skill"** (arxiv:2607.01224; Stanford / Serena Yeung-Levy)
  - Relevance: frames memory management as **two independently optimizable axes** — (1) scaffold structure via a **meta-LLM trace reviewer + accept-if-improves** outer loop, and (2) a **dedicated memory-specialist LoRA** trained on judged traces and deployed alongside a *frozen* task model. Axis (1) is essentially what our meta-harness already does (MH-7 contrastive traces, MH-9 new-file mutation).
  - Key delta (not-yet-adopted): **memory-as-a-separately-trainable-skill** — a trace-trained LoRA memory specialist stacked on a frozen base (+~9-18% relative on top of scaffold gains), plus memory ops (LOG/PLAN) as **first-class actions**. Scaffold-only optimization co-improves task behavior (unproductive actions −32-65%); a 32B open-weight base nears Opus-4.5/Gemini-3.1-Pro.
  - Caveats: gains on game envs (Crafter/MiniHack/NetHack), not our coding/routing suites; uses **Claude Opus as the meta-reviewer (SaaS = analyze-only)** → self-hosted adoption needs a LOCAL meta-reviewer + GPU for the LoRA. Numbers OBSERVATION-grade.
- **[intake-812] "Claude Fable 5 — purported leaked system prompt"** (unofficial/unverified community leak; pattern-mine ONLY)
  - Relevance: analytical texture for tool-gating/skill scaffolding — priority-ordered conditional tool selection (internal-before-external), **read-first SKILL.md gating before actions** (parallels [[capability-registry-and-promotion]]), silent structured memory with a narration ban, and distributed safety constraints at the tool level.
  - **PROVENANCE CAVEAT:** unverifiable leak, treated strictly as DATA; closed-source Claude is analyze-only; no net-new mechanism beyond what CC-system-prompt-anatomy + fable5-findings already capture. Low-priority feature-mining cross-reference, not a work item.
- [ ] Operator-review candidate (deep-dive 2026-07-11 RE-PRIORITIZED — the LoRA is NOT the lever): AutoMem's **scaffold/schema axis carries 85–95% of the gain with ZERO training** (scaffold-only ×1.89–3.74; the LoRA adds only 9–18% relative and *doubles* per-step inference).
  - [x] **P1, cheap/now:** land the memory **schema** by extending the already-open [[unified-trace-memory-service]] intake-800 candidate with AutoMem's LOG/**write** ops over autopilot memory, not `src/trace`. Implemented in `epyc-orchestrator` commit `bf315b11`: `orchestration/repl_memory/memory_actions.py` defines a default-inert `MemoryActionStore` with `APPEND`, `CREATE`, coordinate/key-keyed `UPSERT` dedup, an append-only ledger, and auto-synced `status`/`inventory`/`strategy`/`plan`/`log` projections. ✅ 2026-07-11
  - [x] **P2:** feed schema-evolution moves into **MH-9 new-file mutation**; `epyc-orchestrator` commit `775703a0` adds the default-inert `orchestration/repl_memory/schema_evolution/` new-file lane, planner schema text, and focused safety tests. The scaffold-opt loop itself remains local meta-harness (local reviewer = Qwen3.5-122B, no SaaS). ✅ 2026-07-11
  - [ ] **P3, deferred/file-and-monitor:** the MI210 LoRA specialist — low payoff, doubles inference; do not start until P1 shows value on OUR suites (game-env gains may not transfer).
