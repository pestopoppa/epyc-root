# Cost-Aware Routing

**Category**: `cost_aware_routing`
**Confidence**: verified
**Last compiled**: 2026-04-13
**Sources**: 20 documents (1 deep-dive, 3 active handoffs, 16 intake entries)

## Summary

Cost-aware routing in the EPYC stack addresses a fundamental pathology of reasoning LLMs: they allocate compute inversely to problem difficulty. On trivially easy problems like "2+3=?", QwQ-32B generates 901 tokens across 13 redundant solution attempts -- a 1,953% token overhead where 95.7% of compute is pure waste. This is not an edge case: across difficulty levels, 50-70% of reasoning tokens contribute nothing to reaching the correct answer, and 92% of correct answers appear in the first solution round. The distinctness ratio of later solution attempts decays rapidly, falling 11.5 percentage points from round 3 to round 4+. After three attempts, additional reasoning is overwhelmingly redundant.

The theoretical foundation for addressing this comes from the Conditional Information Bottleneck (CIB) framework, which formally proves that flat token budgets are suboptimal. CIB's Proposition 4.1 shows that linear length penalties correspond to a uniform vocabulary prior -- implicitly assuming all tokens carry equal information, when in reality filler tokens ("Let me think about this...") and essential reasoning tokens ("Therefore x = 3 by substitution") have vastly different information content. The optimal compression objective maximizes the information the reasoning trace provides about the answer *beyond what the prompt already tells us*, while minimizing redundant information leakage from the prompt into the trace. CIB dominates the Pareto frontier: at DLER-7B scale, it achieves 53.5% accuracy at -8% tokens or 52.9% at -32%, outperforming both L1-Exact (51.5% at -29%) and L3L1 (39.7% at -65%).

The practical consequence is a three-tier compression strategy: zero-training methods (conciseness prompting, TrimR pruning, short-m@k parallel generation), activation steering (SEAL/FlowSteer control vectors on dense models), and training-based methods (OPSDC self-distillation, CIB semantic cost training). Each tier trades implementation complexity for compression quality. The EPYC orchestrator has implemented all of tier 1 and has infrastructure for tier 2, while tier 3 remains blocked on GPU training access.

A critical recent finding reshapes the entire routing cost model: the Omega metric evaluation (2026-04-09) revealed that tools and REPL pipelines *hurt* accuracy on 7 of 10 benchmark suites. Agentic tasks suffered -54.5pp, coding -44pp, general QA -26pp, and math -26pp when routed through tool-equipped paths versus direct generation. Only hotpotqa (+12pp) and gpqa (+6pp) benefited. The "cost" of routing to a tool path is not just tokens -- it is accuracy. Default routing should prefer direct mode, with REPL/tool use opt-in for known-beneficial task types.

The EPYC orchestrator has a three-band difficulty classifier (easy/medium/hard) in shadow mode at recalibrated thresholds (0.15/0.35), band-adaptive token budgets (1500/3500/7000) gated behind enforce mode, a reasoning length alarm that cancels and re-generates when think blocks exceed 1.5x the band budget, and an autopilot system continuously optimizing routing via a 4D Pareto archive. The missing piece is validation of the recalibrated thresholds -- the original 0.3/0.6 split produced 92% easy / 0% hard classification, which is useless for routing.

## Key Findings

### The Overthinking Problem

- **50-70% of reasoning tokens are waste**: Outcome efficiency (xi_O) across QwQ-32B ranges from 41.9% on trivial problems (ASDIV) to 32.8% on very hard problems (AIME24). Process efficiency (xi_P) is somewhat better but still shows 59.8% on trivial and 58.4% on very hard -- substantial compute wasted even on diverse exploration. [overthinking-info-bottleneck.md](../research/deep-dives/overthinking-info-bottleneck.md)

- **92% of correct answers appear in the first solution round**: The first round comprises less than 60% of total tokens but contains nearly all correct answers. Solution round 4+ has 11.5% lower distinctness ratio than round 3 -- later rounds restate what was already tried. The empirical ceiling for useful reasoning depth is approximately 3 solution rounds. [overthinking-info-bottleneck.md](../research/deep-dives/overthinking-info-bottleneck.md)

- **Easy problems suffer more from overthinking than hard ones**: Within MATH500, levels 1-2 (easy) trigger 3.7 solution rounds on average while levels 4-5 (hard) trigger 3.0 rounds. The compute allocation is inverted from what efficiency demands. [overthinking-info-bottleneck.md](../research/deep-dives/overthinking-info-bottleneck.md)

### Theoretical Foundation

- **Flat token budgets are provably suboptimal** (CIB Proposition 4.1): Linear length penalties assume all tokens carry equal information -- a uniform vocabulary prior. The optimal approach assigns semantic cost via surprisal under a language model prior: low-surprisal tokens (predictable filler) are cheap to compress, high-surprisal tokens (novel reasoning) are expensive. CIB eliminates the former while preserving the latter. [overthinking-info-bottleneck.md](../research/deep-dives/overthinking-info-bottleneck.md)

- **Three distinct compression mechanisms identified**: CIB training produces (1) algorithmic generalization -- discovering mathematically superior solution paths, (2) elimination of exploration bloat -- removing trial-and-error loops and self-verification tautologies, and (3) syntactic noise filtering -- stripping conversational scaffolding while preserving computational logic. These correspond to progressively finer-grained waste identification. [overthinking-info-bottleneck.md](../research/deep-dives/overthinking-info-bottleneck.md)

- **Information density analysis validates the semantic cost approach**: Baseline models show information density valleys at ~0.1 nats (predictable filler tokens). CIB-trained models raise the floor to 0.2+ nats -- every retained token carries at least 0.2 nats of information about the answer. This is the measurable signal of effective compression. [overthinking-info-bottleneck.md](../research/deep-dives/overthinking-info-bottleneck.md)

### Compression Methods by Tier

- **SEER's MAD-based filtering doubles naive compression**: Best-of-N sampling with Median Absolute Deviation outlier filtering achieves 39.8% compression versus 18.2% for naive BoN at matched or better accuracy. N=3 saturates -- marginal returns beyond 3 candidates are negligible. MAD is more robust than mean/stddev for skewed length distributions. [reasoning-compression-s3cot-adaptive.md](../research/deep-dives/reasoning-compression-s3cot-adaptive.md)

- **Failed outputs are consistently longer than successful ones**: SEER confirms across 7B, 14B, and 32B scales. On HumanEval/129 with DeepSeek-Qwen-7B, failed cases had median 9,489 tokens versus 8,296 for successes. Length is a negative quality signal, motivating reasoning length alarms. [reasoning-compression-s3cot-adaptive.md](../research/deep-dives/reasoning-compression-s3cot-adaptive.md)

- **Easy problems tolerate aggressive compression; hard problems resist it**: OPSDC achieves 56-59% compression on easy problems with accuracy parity or improvement. Hard problems tolerate only 35% compression with 3.4-5.4pp accuracy drops on AIME-class tasks. This validates difficulty-adaptive budgets. [intake-110]

- **SimPO with FCS+Reflection achieves 37-48% token reduction**: Across difficulty levels, accuracy is preserved (only -0.2% on MATH500). For fine-tuning scenarios, this is the empirically validated recipe: shortest correct response as positive, longest correct response as negative. [overthinking-info-bottleneck.md](../research/deep-dives/overthinking-info-bottleneck.md)

- **TrimR is valuable on hard tasks, irrelevant on easy ones**: Evaluation (2026-04-09) showed GPQA: full 58.3% vs think-strip 52.6% vs trimr 45.7% (thinking helps ~6pp). GSM8K: all strategies identical at 66% (model barely generates think tokens on easy math). Aligns perfectly with difficulty-adaptive routing. [reasoning-compression handoff]

### Routing Intelligence

- **Tools/REPL hurt accuracy on 7/10 suites**: Omega metric evaluation found agentic tasks -54.5pp, coder -44pp, general -26pp, math -26pp when using tools versus direct generation. Only hotpotqa (+12pp) and gpqa (+6pp) benefit. The implication is that default routing should prefer direct mode, with tool use as an opt-in for known-beneficial task types. [reasoning-compression handoff]

- **OPSDC's length ratio is a free difficulty signal**: Comparing output length with and without a conciseness prompt yields a difficulty estimate at zero additional cost. Large ratio = easy (compressible); small ratio = hard (reasoning is load-bearing). Alternatively, just add a conciseness instruction: short output = easy, long output = hard. [intake-110]

- **Explicit word limits outperform vague conciseness**: intake-276 deep-dive revealed that "be concise" prompts are the weakest tested form. Explicit numeric limits (e.g., "answer in under 15 words for factual questions") based on CCoT's 30-60 word sweet spot significantly outperform open-ended brevity instructions. Worker prompts have been upgraded accordingly. [reasoning-compression handoff]

## Actionable for EPYC

### Implemented (Production)

- **Q-scorer with sweep-verified TPS baselines**: Calibrated quality scoring for routing, using benchmark-derived throughput baselines per model/quant combination.
- **Difficulty classifier** (`difficulty_signal.py`): 7 regex features producing 3-band classification. Shadow mode with recalibrated thresholds (0.15/0.35 for ~40/40/20 split).
- **Band-adaptive token budgets**: `_repl_turn_token_cap()` returns 1500/3500/7000 by difficulty band when enforce mode is active. Derived from overthinking efficiency metrics.
- **Conciseness prompting with explicit word limits**: Format-specific limits on worker_general.md (MC: letter+1 sentence, factual: under 15 words, open: under 60 words) and worker_math.md (MC: letter+1 sentence, numeric: under 50 words, proof: under 100 words). Architect has aggressive "<150 tokens" limit. Coder uses "code only".
- **N-gram loop detection**: `detect_think_block_loop()` catches repetition within reasoning traces.
- **Reasoning length alarm**: `_check_reasoning_length_alarm()` cancels and re-generates when think blocks exceed 1.5x band budget. Double-gated (feature flag + enforce mode), retry includes conciseness nudge.
- **Answer-tag stop sequences**: `<answer></answer>` XML tags with `</answer>` in stop sequences eliminate post-answer rumination loops across all benchmark prompts.
- **OAA metric**: `eval_metrics.py` with alpha-penalized excess token scoring and per-token intelligence metric for benchmark evaluation.

### In Progress

- **Difficulty signal validation at new thresholds**: Original 0.3/0.6 thresholds yielded 92% easy / 0% hard -- useless. Recalibrated to 0.15/0.35 for ~40/40/20 split. Medium prompts take 29% longer (p50 36s vs 25s), confirming signal has predictive value. Full re-validation pending before enforce mode activation.
- **SEAL control vector generation for Qwen3-32B**: Contrastive pair generator (80 problems) and evaluation script (scaling sweep at 0.3/0.5/0.7) prepared. Awaiting model servers. Works via existing `--control-vector` flag in llama.cpp on dense models. Blocked on Qwen3.5 hybrid SSM (no `build_cvec()` in `qwen35.cpp`).
- **Autopilot GEPA integration**: GEPA evolutionary prompt optimization now runs 30% of PromptForge trials via `OrchestratorGEPAAdapter`. 35x fewer rollouts than GRPO. Comparing acceptance rates against LLM mutation in AR-3 journal.

### Planned

- **Enforce mode activation**: Route easy problems to worker tier (fast, cheap), hard problems to architect tier (expensive, accurate). Requires validated difficulty signal at new thresholds.
- **Direct-mode-first routing**: Based on Omega findings, default routing should prefer direct generation over REPL/tool paths. Tool use opt-in only for known-beneficial types (hotpotqa, gpqa).
- **Outcome efficiency telemetry** (xi_O per band): Instrument REPL turns with total tokens, correctness, and first-correct tokens. Calibrate band thresholds until xi_O is roughly uniform (target 60-70%) across bands.
- **Information density monitoring**: Track token-level log-probabilities during generation. Rolling surprisal below 0.2 nats for 50+ consecutive tokens indicates filler. Start with post-hoc analysis before real-time stopping.
- **Surprisal-based adaptive stopping** (Phase 3, research-grade): If information density monitoring shows a clear filler detection signal, replace token cap entirely with content-aware stopping. The CIB framework predicts this should be strictly better than any fixed budget.

### Not Actionable

- **CIB semantic token cost training**: Requires GRPO training with frozen language model prior on GPU. Theoretically optimal but requires training infrastructure we do not operate.
- **FlowSteer nonlinear activation steering**: MLP ODE solve at intervention points has no llama.cpp infrastructure. Only the weaker SEAL linear baseline is deployable, and only on dense models.
- **CoLaR latent reasoning compression**: Model-level training at 1B-1.5B scale only. Incompatible with speculative decoding.
- **TALE dynamic budget estimation**: A/B test (2026-04-11) showed static word limits outperform TALE on OAA metric (static -3.48 vs TALE -5.95). Pre-pass adds latency without benefit. Deferred.

## Open Questions

- What are the recalibrated difficulty thresholds' predictive power? The 0.15/0.35 split needs validation against benchmark accuracy before enforce mode can be activated.
- Does the Omega finding (tools hurt on 7/10 suites) replicate with the current orchestrator version? Specific model and tool configurations may have improved since evaluation.
- Can OPSDC's length-ratio difficulty signal be used at runtime, or is it too expensive (requires generating two responses)?
- How does TrimR interact with speculative decoding acceptance rates? Pruning reasoning tokens changes the distribution, which may affect draft model alignment.
- What is the right enforcement strategy for band-adaptive budgets -- hard truncation, soft penalty (reduced temperature), or retry with conciseness nudge? The current reasoning length alarm uses retry, but the optimal approach may vary by difficulty band.
- Is the ~5pp accuracy drop on AIME-class problems under any compression method an irreducible cost of the task structure, or can per-problem adaptive budgets (finer than per-band) recover it?
- Should the autopilot shift budget allocation from NumericSwarm to PromptForge/StructuralLab based on the finding (intake-265) that architectural changes outperform parameter tuning on broken baselines?

## Related Categories

- [Context Management](context-management.md) -- Compression techniques reduce context pressure, which is the primary cost driver; tool output compression is a routing-adjacent optimization
- [LLM Prompting](llm-prompting.md) -- Conciseness prompting is a tier-1 zero-cost routing optimization; controllability research bounds its effectiveness, especially on RL-trained workers
- [Context Extension](context-extension.md) -- Larger effective context windows change the cost calculus for routing by reducing the need for aggressive compression

## Source References

- [Overthinking + Information Bottleneck](../research/deep-dives/overthinking-info-bottleneck.md) -- xi_O/xi_P efficiency metrics, CIB theory (Propositions 4.1/4.2), difficulty-adaptive budgets, surprisal-based filler detection, three compression mechanisms
- [Reasoning Compression (S3-CoT + SEER)](../research/deep-dives/reasoning-compression-s3cot-adaptive.md) -- SEER MAD-based filtering, failed-longer-than-successful finding, integration paths A-D, n-gram loop parameters
- [FlowSteer Concise Reasoning](../research/deep-dives/flowsteer-concise-reasoning.md) -- SEAL linear baseline compatibility, Qwen3.5 hybrid SSM blocker, FlowSteer MLP infeasibility
- [CoLaR Latent Compression](../research/deep-dives/colar-latent-compression.md) -- Latent compression trade-offs, not-actionable assessment
- [Reasoning Compression handoff](../handoffs/active/reasoning-compression.md) -- OPSDC analysis, 3-tier approach taxonomy, TrimR/Omega evaluation results, all action items
- [Autopilot Continuous Optimization handoff](../handoffs/active/autopilot-continuous-optimization.md) -- 4D Pareto archive, species-based optimization, GEPA integration, safety gates
- [intake-110] OPSDC -- 57-59% compression with accuracy gains; difficulty adaptation is emergent; length-ratio routing signal
- [intake-125] S3-CoT -- Self-sampled activation steering; progressive curriculum; VL-D in residual stream
- [intake-126] FlowSteer -- Nonlinear activation steering; SEAL linear baseline; +6% accuracy at 14.5% reduction
- [intake-127] TrimR -- Verifier-based inference-time pruning; valuable on hard tasks, irrelevant on easy
- [intake-128] SEER -- Best-of-N + MAD filtering; N=3 saturation; 73-97% loop elimination
- [intake-129] short-m@k -- Parallel generation with early stopping; 34.5% more accurate than longest chains
- [intake-130] Overthinking analysis -- 50-70% token waste; inverse difficulty allocation; distinctness ratio decay
- [intake-133] CIB theory -- Formal unification of budget forcing; Pareto-dominant compression; semantic token cost
- [intake-134] CoLaR -- Latent reasoning embeddings; 2-5x chain reduction; speculative decoding incompatibility
- [intake-276] Brevity constraints -- Explicit word limits outperform vague conciseness instructions
