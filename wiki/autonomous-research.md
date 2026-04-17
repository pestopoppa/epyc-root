# Autonomous Research

**Category**: `autonomous_research`
**Confidence**: verified
**Last compiled**: 2026-04-17
**Sources**: 22 documents (1 deep-dive, 15 intake entries, 6 handoffs)

## Summary

Autonomous research in the EPYC context refers to systems that can propose, execute, evaluate, and learn from optimization experiments without human intervention. The project's AutoPilot is a continuous optimization loop with 4 optimizer species (Seeder for dynamic per-role eval and Q-value training, NumericSwarm for Optuna NSGA-II parameter search, PromptForge for LLM-guided prompt mutation, StructuralLab for flag and routing model lifecycle experiments), a tiered evaluation tower (T0: 10 questions in 30s, T1: 100 questions in 5m, T2: 500+ questions in 30m), a 4D Pareto archive (quality x speed x -cost x reliability), safety gates with quality floor and per-suite regression guards, and an Evolution Manager species for knowledge distillation into a FAISS+SQLite strategy store.

The central insight synthesized across all research sources is that **knowledge distillation must be a separate, explicit step after every optimization trial -- not just metric recording**. EvoScientist (intake-108) provides the strongest evidence: its three-agent pipeline (Researcher, Engineer, Evolution Manager) with two persistent memory modules achieves +10.17 percentage points in code execution success rates through strategy distillation alone, and removing all evolution channels causes -45.83 average gap. The Evolution Manager's three channels -- Idea Direction Evolution (what abstract principle led to success), Idea Validation Evolution (why ideas failed with LLM-analyzed reasons), and Experiment Strategy Evolution (generalizable strategies from code search trajectories) -- address the specific gap identified in the EPYC AutoPilot: species were effective optimizers but memoryless beyond the Pareto archive and Optuna's internal state. This has been addressed by implementing an Evolution Manager species that runs every 5 trials, distilling knowledge via LLM summarization into a retrievable strategy store.

A second critical insight comes from AgentRxiv (intake-131): retrieval-augmented iteration dramatically improves convergence. Removing access to prior research causes performance to plateau at 73.4-73.8% on MATH-500, while with N=5 paper retrieval it continues improving to 78.2%. Multi-lab parallel research (3 labs) reaches the same milestone in 7 papers instead of 23, trading 3x cost for proportionally faster wall-clock discovery. The EPYC AutoPilot implemented this via strategy store retrieval and cross-species fertilization, closing the "passive journal" gap where the experiment journal was comprehensive but never queried by species during proposal generation.

A convergent wave of research in April 2026 brought four significant upgrades to the autopilot infrastructure: GEPA evolutionary prompt optimization (intake-327/335, 35x more efficient than GRPO, works with 3 examples, compatible with local inference), dspy.RLM metadata-first context exploration, MiniMax M2.7-style self-evolution with short-term memory and self-criticism (intake-328/329), and Unsloth RLVR environment-first RL design (intake-320). All four are integrated as of 2026-04-12 (AP-18 through AP-25).

## Key Findings

- **The Evolution Manager pattern addresses the largest gap in automated optimization.** EvoScientist's ablation study quantifies the value: without Idea Direction Evolution -22.50 average gap (novelty and feasibility hurt most), without Idea Validation Evolution -20.00 (feasibility disproportionately harmed), without all evolution -45.83. Strategy distillation alone (ESE) yields +10.17pp code execution success rate (34.39% to 44.56%). The core insight: raw trial metrics do not capture why things worked or failed. The Evolution Manager observes trial histories and distills abstract, generalizable strategies before storage -- it never executes experiments or generates ideas, only observes and distills. [evoscientist-multi-agent-evolution.md](../research/deep-dives/evoscientist-multi-agent-evolution.md)

- **Retrieval-augmented iteration dramatically improves convergence.** AgentRxiv's protocol is simple: embed current goal, cosine similarity against accumulated findings, return top-N, inject into proposal context. The difference is material: performance plateaus without retrieval and continues improving with it. The quality gate is critical -- AgentRxiv's biggest weakness (hallucinated papers polluting the knowledge base) is already addressed in the EPYC architecture by the safety gate that prevents bad results from entering the archive. [agent-architectures-paperclip-agentrxiv.md](../research/deep-dives/agent-architectures-paperclip-agentrxiv.md)

- **GEPA evolutionary optimization is 35x more efficient than GRPO for prompt evolution.** GEPA (Genetic-Pareto Prompt Evolution) uses reflective trace analysis with Actionable Side Information (ASI) to guide mutations. It works with as few as 3 examples, is compatible with local inference (Ollama/vLLM format), and costs ~$2-10 per optimization run. Integrated into PromptForge at 30% of trials as a `gepa` mutation type. AR-3 journal will collect comparison data to determine optimal GEPA-to-LLM mutation ratio. [intake-327, intake-335, intake-345]

- **Self-criticism loops and short-term memory improve autonomous optimization quality.** MiniMax M2.7's 3-component harness (short-term memory markdown, explicit self-criticism, forward-looking optimization) over 100+ autonomous rounds showed 30% improvement. The EPYC AutoPilot adopted this with a `ShortTermMemory` class (markdown persistence) and rule-based `generate_self_criticism()` function in the controller. [intake-328, intake-329]

- **Bug fixes vastly outperform hyperparameter tuning on broken baselines.** Omni-SimpleMem (intake-265) showed +175% improvement from bug fixes versus all hyperparameter tuning combined. This generalizes to "fixing broken systems beats tuning broken systems." The actionable takeaway for the functioning EPYC AutoPilot is structured deficiency classification (AP-14): auto-populate `deficiency_category` from SafetyGate violation type to enable pattern detection in PromptForge. [intake-265](https://arxiv.org/abs/2604.01007)

- **The eval tower IS an RLVR environment.** Unsloth's Reinforcement Learning with Verifiable Rewards framework maps 1:1 to the T0/T1/T2 evaluation tiers. Formalizing these as verification functions with deterministic reward signals per tier (not just benchmarks) enables actual model RL training if cloud GPU becomes available. The eval_tower already provides the environment interface; the missing piece is the reward function formalization. [intake-320](https://unsloth.ai/blog/rl-environments)

- **The "Mismanaged Geniuses" hypothesis validates compositional optimization.** Frontier LLMs are already superhuman on the hardest exams (IMO, IOI). The key variable is decomposition space design, not model capability -- a 4B RLM achieved 100% on MRCRv2 via composition. This provides theoretical foundation for the autopilot's approach of optimizing orchestration intelligence rather than scaling model size. The bottleneck is how you manage the model, not the model itself. [intake-312](https://alexzhang13.github.io/blog/2026/mgh/)

- **Agent Lightning provides framework-agnostic agent optimization with hierarchical credit assignment.** Three optimization modes (RL, prompt optimization, SFT) map to existing species. Its trajectory-level aggregation addresses the per-question vs per-trajectory eval gap. LightningRL's hierarchical credit assignment enables per-request reward attribution, dramatically improving PromptForge mutation signal quality compared to aggregate suite-level metrics. [intake-338](https://github.com/microsoft/agent-lightning)

- **Multi-agent collective intelligence achieves superlinear speedup on some tasks.** SiliconSwarm (intake-248) ran 6 autonomous agents on 6 Macs collaboratively optimizing ANE inference, achieving 6.31x faster than Apple CoreML via a 9-step optimization loop and shared memory. The pattern (query swarm, edit, build, verify, benchmark, publish) maps to parallel autopilot instances sharing an experiment journal. [intake-248]

- **AutoResearch suitability requires four properties.** Scalar metrics, modular architecture, fast iteration cycles, and version-controlled modifications. The EPYC AutoPilot satisfies all four, confirming it is in the right structural class for autonomous optimization. The single-file modification constraint from AutoResearch (intake-148) and the program.md strategy separation from PraxLab (intake-149) both validate existing autopilot design patterns. [intake-148, intake-149]

- **Execution trace feedback provides +15 points over score-only feedback.** The Meta-Harness ablation (intake-244) shows: scores only 34.6% median accuracy, scores + text summaries 34.9%, full filesystem access to traces 50.0%. This is implemented as Tier 1 in the autopilot via inference_tap.log trace injection into PromptForge's failure context. [meta-harness-optimization.md handoff]

- **Phase 5 seeder refactor: per-role eval replaces 3-way eval (2026-04-17).** The original 3-way eval (SELF:direct, SELF:repl, ARCHITECT) built Q-values for 3 abstract action classes, not per-model. This caused 96% uniform Q-values because the signal was too coarse. The refactored seeder dynamically discovers active roles from `model_registry.yaml` via `discover_active_roles()` and tests each role individually with `force_mode=""` (natural mode selection) and `allow_delegation=True`. Rewards are keyed by role name (e.g., "frontdoor", "architect_general"), building per-model Q-values. The eval tower remains end-to-end (`force_role=""`) to measure system-level routing quality. **Adaptation surface for stack changes**: `seeding_types.py` is the only file requiring manual updates (port mappings via `ROLE_PORT`, exclusions via `SEEDING_EXCLUDED_ROLES`, key-to-role aliases via `_REGISTRY_KEY_TO_ROLE`). Role discovery reads `server_mode` section of `model_registry.yaml` dynamically. When roles are removed, discovery adapts automatically; when renamed, update `_REGISTRY_KEY_TO_ROLE`; when consolidated, old Q-values persist harmlessly. [scripts/benchmark/seeding_types.py, scripts/benchmark/seeding_eval.py, scripts/autopilot/species/seeder.py]

- **DAR-1 reveals 96% uniform Q-values -- Q-scorer has barely learned preferences.** Regret analysis on 7,211 routing decisions (Apr 10-14) shows Q-value spread is <0.001 for 96% of decisions. Selection score spread is non-trivial (median 0.107) but comes entirely from cost/similarity features, not Q-values. 3,355 learned vs 3,856 rules/classifier decisions. The implication: contrastive Q-updates (DAR-2) are essential to accelerate Q-learning from sparse signal. [progress/2026-04/2026-04-15.md](../progress/2026-04/2026-04-15.md)

- **Contrastive Q-score approach addresses uniform Q-value pathology.** DAR-2 adds `_compute_contrastive_adjustment()` to `q_scorer.py` -- an additive contrastive term capped at +/-0.1 that sharpens decision boundaries. Feature-flagged `CONTRASTIVE_Q_UPDATES` (ON by default). Every new routing decision gets decision-boundary sharpening, accelerating Q-learning from the near-zero signal discovered by DAR-1. [progress/2026-04/2026-04-15.md](../progress/2026-04/2026-04-15.md)

- **Package I created for post-AR-3 decision-aware routing validation.** Three tasks: I1 (DAR-3 SPO+ exploration -- 10% epsilon-greedy for counterfactual data), I2 (DAR-4 bilinear scorer A/B -- model-feature-conditioned Q vs per-action Q-tables), I3 (EV-5 ThinkPRM-1.5B T2 process verification). Package I requires isolated measurement because routing behavior modifications would contaminate other eval runs. [bulk-inference-campaign.md](../handoffs/active/bulk-inference-campaign.md)

- **Eval tower verification framework advancing (EV-1/2/6 code complete).** EV-1 adds `confidence` field to QuestionResult. EV-2 adds ECE/AUC computation in `_aggregate()`. EV-6 adds cross-family verification constraint (`VERIFICATION_FAMILIES` dict + `check_cross_family()`). ECE/AUC metrics auto-accumulate in journal on AR-3 restart. EV-3 (Scoring Verifiers benchmark download), EV-4 (calibration baseline), and EV-5 (ThinkPRM-1.5B deployment) remain pending. AP-27 now points to eval-tower-verification.md as its implementation plan. [eval-tower-verification.md](../handoffs/active/eval-tower-verification.md)

## Actionable for EPYC

### High Priority (next compute session)
1. **AR-3 continuation** -- relaunch with all new infrastructure (GEPA optimizer, short-term memory, self-criticism, hybrid eval, DAR-2 contrastive Q-updates ON by default, ECE/AUC auto-accumulation). State at trial_counter=46. Hybrid eval (T0 fast-reject + T1 real gate) gives honest signal per trial.
2. **AP-21: GEPA vs LLM mutation decision** -- after 50+ AR-3 trials, compare GEPA vs LLM mutation acceptance rates and Pareto frontier contributions. If GEPA dominates, increase ratio from 30% to 100%.
3. **AP-14: Structured deficiency classification** -- add `deficiency_category` enum to JournalEntry. Auto-populate from SafetyGate violation type. Enables pattern detection (Omni-SimpleMem finding: structured defect classification is prerequisite for targeted fixes).
4. **Package I (post-AR-3)** -- Decision-aware routing validation: DAR-3 SPO+ exploration (counterfactual data), DAR-4 bilinear scorer A/B, EV-5 ThinkPRM-1.5B T2 verification. Must run isolated from other eval.

### Medium Priority
4. **AP-15: Species field verification audit** -- verify all 5 species (including Evolution Manager) populate `hypothesis` + `expected_mechanism` during AR-3. Missing fields reduce strategy distillation quality.
5. **AP-16: Instruction token budget tracking** -- count tokens in all loaded .md templates using LlamaTokenizer. Alert if instruction ratio > 20% of context window. Prerequisite for AP-17 structural pruning.
6. **AP-26: Test dspy.RLM for autopilot tasks** -- long-horizon benchmark analysis where metadata-first context exploration avoids context window limits.
7. **AP-27: Formalize eval tower tiers as RLVR verification functions** with deterministic reward signals per tier. Foundation for future model RL training.

### Lower Priority
8. **AP-17: Structural pruning in StructuralLab** -- new `structural_prune` action type for block-level deletions from .md prompt files. Depends on AP-16 providing the baseline token budget data.
9. **Parallel autopilot instances** -- run 2-3 instances with different species configurations sharing a common experiment journal. AgentRxiv shows 3x cost but proportionally faster wall-clock discovery. Requires journal locking or append-only protocol.
10. **Heartbeat-driven invocation** -- convert autopilot from continuous loop to schedule-driven invocation with accumulated context (Paperclip pattern). More resource-efficient for overnight runs but less responsive.

### Blocked
11. **AP-21** blocked on AR-3 trial data (need 50+ trials with GEPA mixture).
12. **Hard-negative training data** (intake-176) blocked on 500+ MemRL memories for routing classifier retraining.
13. **EV-7 (AP-27 RLVR integration)** blocked on EV-1-4 completion + Ouro P7 results. EV-1/2/6 code complete; EV-3/4/5 need inference.

## Open Questions

- DAR-1 shows 96% uniform Q-values after 7,211 decisions -- how many additional routing decisions (with DAR-2 contrastive updates active) are needed before Q-values become discriminative?
- What is the optimal GEPA-to-LLM mutation ratio? Initial setting is 30% GEPA. AR-3 data will resolve this empirically.
- Can GEPA Full Program Adapter evolve routing logic, tool definitions, and escalation pipeline (not just prompts)? The +26pp MATH improvement (93% vs 67% baseline) suggests transformative potential, but the EPYC orchestrator's complexity far exceeds a single DSPy program.
- Should the autopilot controller use persistent short-term memory across AR-3 sessions, or reset between sessions? Current implementation persists as markdown.
- What is the right trial cadence for the Evolution Manager species? Currently every 5 trials. Too frequent wastes compute on distillation; too infrequent loses temporal locality of insights.
- How should parallel autopilot instances share the experiment journal without write conflicts? Append-only protocol (simpler, eventual consistency) vs explicit file locking (stronger guarantees, deadlock risk).
- Is the Meta-Harness finding (+15pts from traces) reproducible with a 32B local model doing diagnostic reasoning, or does it require Opus-class capability? The original paper tested only Opus.

## Related Categories

- [Agent Architecture](agent-architecture.md) -- the autopilot optimizes the orchestrator's agent configuration
- [Routing Intelligence](routing-intelligence.md) -- Seeder species generates per-role eval data that trains routing Q-values
- [Memory Augmented](memory-augmented.md) -- strategy store and episodic memory are the autopilot's learning infrastructure
- [Tool Implementation](tool-implementation.md) -- GEPA and code mutation use tool infrastructure for experiments

## Source References

- [EvoScientist deep dive](../research/deep-dives/evoscientist-multi-agent-evolution.md) -- three-agent pipeline, Evolution Manager with IDE/IVE/ESE channels, knowledge distillation ablation evidence (-45.83 gap without evolution, +10.17pp from ESE alone)
- [Paperclip & AgentRxiv deep dive](../research/deep-dives/agent-architectures-paperclip-agentrxiv.md) -- shared knowledge accumulation protocol, retrieval-augmented iteration results (plateau without retrieval, continued improvement with N=5), multi-lab parallel 3x cost tradeoff
- [autopilot-continuous-optimization.md](../handoffs/active/autopilot-continuous-optimization.md) -- primary handoff tracking all autopilot infrastructure, 4+1 species, safety gates, GEPA integration, self-criticism, strategy store
- [meta-harness-optimization.md](../handoffs/active/meta-harness-optimization.md) -- execution trace feedback (+15pts ablation), code mutation search space with allowlist + ast.parse safety, GEPA as search algorithm
- [reasoning-compression.md](../handoffs/active/reasoning-compression.md) -- OPSDC difficulty adaptation as potential autopilot routing signal
- [intake-108](https://arxiv.org/abs/2603.08127) EvoScientist -- Evolution Manager, knowledge distillation, three agent pipeline (new_opportunity, high relevance)
- [intake-131](https://arxiv.org/abs/2503.18102) AgentRxiv -- collaborative autonomous research, shared preprint server, 13.7% MATH-500 improvement (worth_investigating)
- [intake-132](https://arxiv.org/abs/2503.21248) ResearchBench -- LLM scientific discovery benchmark, inspiration retrieval task decomposition (worth_investigating)
- [intake-148](https://github.com/karpathy/autoresearch) AutoResearch -- single-GPU autonomous ML experiments, single-file modification constraint (worth_investigating)
- [intake-149](https://github.com/Hamza-Mos/praxlab) PraxLab -- program.md strategy separation, SQLite experiment memory (worth_investigating)
- [intake-248] SiliconSwarm@Ensue -- 6-agent collective intelligence, 6.31x CoreML speedup, 9-step optimization loop (new_opportunity, high relevance)
- [intake-265](https://arxiv.org/abs/2604.01007) Omni-SimpleMem -- autoresearch-guided discovery, bug fixes > tuning (+175%), 23-stage pipeline (worth_investigating)
- [intake-312](https://alexzhang13.github.io/blog/2026/mgh/) Mismanaged Geniuses Hypothesis -- orchestration over model power, 4B RLM achieves 100% MRCRv2 (worth_investigating, high relevance)
- [intake-327](https://github.com/NousResearch/hermes-agent-self-evolution) Hermes Agent Self-Evolution -- DSPy+GEPA skill optimization, ~$2-10 per run, no GPU required (new_opportunity, high relevance)
- [intake-329](https://www.minimax.io/news/minimax-m27-en) MiniMax M2.7 -- 3-component self-evolution harness, 30% improvement over 100+ rounds (worth_investigating)
- [intake-335](https://github.com/gepa-ai/gepa) GEPA Implementation Repository (already_integrated)
- [intake-338](https://github.com/microsoft/agent-lightning) Agent Lightning -- zero-code agent optimization, RL+prompt+SFT modes, hierarchical credit assignment (new_opportunity, high relevance)
- [eval-tower-verification.md](../handoffs/active/eval-tower-verification.md) -- AP-27 implementation plan (EV-1-7), ECE/AUC metrics, Aletheia RLVR recipes, ThinkPRM deployment, cross-family verification
- [bulk-inference-campaign.md](../handoffs/active/bulk-inference-campaign.md) -- Package I for post-AR-3 decision-aware routing validation (DAR-3/4 + EV-5)
- [progress/2026-04/2026-04-15.md](../progress/2026-04/2026-04-15.md) -- DAR-1 regret analysis results (96% uniform Q-values), DAR-2 contrastive Q-score implementation, AR-3 restart prep
