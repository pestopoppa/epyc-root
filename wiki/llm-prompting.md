# LLM Prompting

**Category**: `llm_prompting`
**Confidence**: verified (CPU/prompting findings) · observation (2026-07-06 CoT-scaffold GPU-study numbers — single-sample, no protocol-id per MEASUREMENT.md)
**Last compiled**: 2026-07-06 (⚠️ 2026-07-06 CoT-scaffold-injection subsection flagged for human review — see Key Findings)
**Sources**: 14 documents (2 deep-dives, 1 active handoff, 11 intake entries across llm_prompting/prompt_optimization/prompt_sensitivity/instruction_following)

## Summary

Prompting research relevant to the EPYC stack divides into two sharply different domains. The first -- reasoning control and conciseness steering -- has direct production value and is backed by rigorous empirical and theoretical work. The second -- broader prompt engineering techniques including emotional stimuli, personas, and narrative framing -- is largely inapplicable to our workload, with the literature consistently showing that popular techniques either fail to replicate or actively degrade performance under controlled evaluation.

The most important finding sits at the intersection of two complementary papers. "Thinking to Recall" (arXiv:2603.09906) demonstrates that chain-of-thought tokens serve a dual purpose that goes beyond logical decomposition. First, they act as a **computational buffer**: even replacing reasoning traces with meaningless dummy tokens ("Let me think.") repeated to matching length improves accuracy by 21-27% over no reasoning. The extra forward passes provide latent computation that bypasses single-pass bottlenecks, independent of semantic content. Second, they serve as **factual primers**: generating topically related facts bridges retrieval gaps, with the "OFF Facts" condition (providing extracted facts as context without reasoning) matching full reasoning performance on EntityQuestions. These mechanisms explain why chain-of-thought helps on simple factual recall tasks that require no multi-step decomposition -- a persistent puzzle in the literature.

"Reasoning Models Struggle to Control Their Chains of Thought" (arXiv:2603.05706, OpenAI) then reveals that this reasoning process is largely uncontrollable. Across 13 models, CoT controllability ranges from 0.1% (DeepSeek R1) to 15.4%, while output controllability exceeds 60% for the same models. The gap is 1-2 orders of magnitude. Claude Sonnet 4.5 demonstrates a 23x gap (2.7% vs 61.9%); DeepSeek R1 shows ~200x. The combined insight is that reasoning is effective precisely because it is uncontrollable -- the model reasons about what it *needs* to, not what it is *told* to. This is a positive result for monitoring (low controllability implies high monitorability) but a constraint for prompt engineering.

For EPYC specifically, these findings validate a clear strategy: continue using stylistic/length modifications (conciseness prompting, explicit word limits) which carry low accuracy cost (2.7pp or less), and explicitly avoid information suppression ("don't reason about X") which carries 6-17pp cost at near-zero compliance. The activation steering domain offers a middle path through SEAL-style linear control vectors, deployable today on dense Qwen3/Qwen2.5 via llama.cpp's existing `--control-vector` infrastructure, though blocked on our primary Qwen3.5 hybrid SSM model. The broader prompting literature -- emotional stimuli tested across 6+ papers, personas tested across 162 roles, narrative framing -- shows no replicable gains on code generation, mathematical reasoning, or factual QA.

## Key Findings

### Reasoning Control: The Dual Mechanism

- **CoT serves as computational buffer, not just logical decomposition**: Replacing reasoning traces with dummy tokens ("Let me think.") repeated to matching length improves accuracy by 21-27% over no reasoning (SimpleQA: 20.6% to 26.2%; EntityQuestions: 45.7% to 55.4%). A single "Let me think." (short trace) performs worse than the length-matched version, confirming that the number of forward passes matters, not the semantic content. [reasoning-recall-cot-controllability.md](../research/deep-dives/reasoning-recall-cot-controllability.md)

- **Factual priming is a distinct and separable mechanism**: Providing extracted facts as context without any reasoning (OFF Facts condition) matches full reasoning performance on EntityQuestions. This implies RAG-style fact injection can substitute for reasoning tokens on factual questions -- the computational buffer and factual priming are separable, and for factual tasks, priming alone suffices. [reasoning-recall-cot-controllability.md](../research/deep-dives/reasoning-recall-cot-controllability.md)

- **Hallucinated intermediate facts cascade to final answers**: Clean (hallucination-free) reasoning traces produce correct answers at 41.4% versus 26.4% for hallucinated traces on SimpleQA. The regression slope of 0.84-0.86 indicates a systematic within-question effect, not explainable by difficulty. When the model fabricates an intermediate fact, it primes itself with false context that corrupts downstream retrieval -- the factual priming mechanism works in both directions. [reasoning-recall-cot-controllability.md](../research/deep-dives/reasoning-recall-cot-controllability.md)

- **Verified-fact filtering improves accuracy by 5-12% relative**: Filtering reasoning traces to keep only those with verified factual statements yields +8.2% relative on SimpleQA and +5.1% on EntityQuestions. This suggests an output-side quality signal: traces containing unverified factual assertions predict hallucinated final answers. [reasoning-recall-cot-controllability.md](../research/deep-dives/reasoning-recall-cot-controllability.md)

### Controllability Constraints

- **CoT controllability is 1-2 orders of magnitude below output controllability**: Across 13 models tested with 14,076 problems across three controllability categories (suppression, addition, stylistic). Models control what they say far more than what they think. This is a fundamental architectural property, not a training artifact. [reasoning-recall-cot-controllability.md](../research/deep-dives/reasoning-recall-cot-controllability.md)

- **Stylistic modification is the safest controllability category**: Accuracy cost of 2.7pp or less, versus 6-17pp for information suppression. Our conciseness prompting falls in this category. The key distinction: we tell the model *how long* to respond, not *what to think about*. [reasoning-recall-cot-controllability.md](../research/deep-dives/reasoning-recall-cot-controllability.md)

- **RL-trained reasoning models are the least controllable**: CoT controllability decreases by over an order of magnitude during RL training (measured on OLMo-3-7B-RL-Zero-Math). DeepSeek R1 at 0.1%, small Qwen3 RL variants at 0.6%. This is inverted from our deployment: we prompt workers (7B-14B RL-trained models) for conciseness, but they are the models least likely to comply. Conciseness prompts have more effect on 32B+ models than on 7B-14B workers. [reasoning-recall-cot-controllability.md](../research/deep-dives/reasoning-recall-cot-controllability.md)

- **Test-time compute reduces controllability further**: More thinking equals less ability to simultaneously control what is thought. Harder problems also reduce controllability. Monitoring awareness produces only marginal improvements. [reasoning-recall-cot-controllability.md](../research/deep-dives/reasoning-recall-cot-controllability.md)

### Activation Steering

- **FlowSteer achieves +6.0% accuracy with 14.5% token reduction at best**: Using nonlinear activation transport via flow matching on DeepSeek-R1-1.5B (AMC23). 5.4x better distributional alignment than the SEAL linear baseline. Training requires 1,000-3,600 contrastive pairs, single GPU, under 24 hours. The flow MLP adds only ~1.8 TPS overhead with net latency improvement from shorter outputs. [flowsteer-concise-reasoning.md](../research/deep-dives/flowsteer-concise-reasoning.md)

- **SEAL linear baseline is deployable today on dense models**: llama.cpp supports `--control-vector` and `--control-vector-scaled` with per-layer F32 tensors added to the residual stream via `ggml_add()`. The `tools/cvector-generator/` tool exists for generating vectors from contrastive pairs. Works on Qwen3-32B (`qwen3.cpp` has `build_cvec()`), Qwen2.5 (`qwen2.cpp` has `build_cvec()`). Quantized GGUF is compatible since control vectors operate on the F32 residual stream. [flowsteer-concise-reasoning.md](../research/deep-dives/flowsteer-concise-reasoning.md)

- **Qwen3.5 hybrid SSM has no control vector support**: `qwen35.cpp` does not call `build_cvec()`. Even if added, 75% of Qwen3.5 layers are recurrent (gated delta net), not standard transformer residual connections. A steering vector computed from attention-layer activations would be applied to a fundamentally different computational pathway. Same blocker affects S3-CoT activation steering. [flowsteer-concise-reasoning.md](../research/deep-dives/flowsteer-concise-reasoning.md)

### The Omega Metric

- **Less capable models benefit more from reasoning**: Qwen3-32B shows the highest Omega values (reasoning benefit relative to non-reasoning baseline); Gemini-2.5-Pro shows the lowest. Stronger models recall more at pass@1, leaving less headroom for reasoning to compensate. SimpleQA consistently produces higher Omega than EntityQuestions because its lower OFF baseline means more room for improvement. [reasoning-recall-cot-controllability.md](../research/deep-dives/reasoning-recall-cot-controllability.md)

- **Omega is computable on existing infrastructure**: Run seeding benchmarks with reasoning ON versus OFF, compute per-suite weighted average of relative pass@k improvements. High Omega suites need reasoning models (architect tier); low Omega suites waste tokens on reasoning (worker tier). Maps directly to routing decisions.

### CoT-Scaffold Injection: transplanted reasoning is a COST lever, not a capability transplant (2026-07-06) — ⚠️ COMPILE-FLAGGED FOR HUMAN REVIEW

> **Review flag (project-wiki writer-evidence policy):** model-compiled from the GPU CoT-scaffold study close-out; **not adopted until human or measured review**. Every accuracy/token number is an **OBSERVATION** (single MI210, single-sample seed 42, n=10–48 cells, no protocol-id per MEASUREMENT.md). Sources: [GPU CoT-scaffold sidecar (full arc)](../handoffs/active/gpu-cot-scaffold-sidecar.md), [scaffold autopilot cost-lever deployment (DESIGN)](../handoffs/active/scaffold-autopilot-cost-lever-deployment.md), [progress 2026-07-06 CoT study complete](../progress/2026-07/2026-07-06-cot-study-complete.md).

The completed study asked whether a small, fast reasoner's chain-of-thought, **injected into a larger worker's prompt** (as an assistant-prefix continuation or a context-advisory plan), raises the worker's answer quality more per token than the worker's own thinking. The result cleanly separates three distinct claims:

- **Capability transplant is FALSIFIED — transplanted reasoning does not transplant capability.** Handing a model a pre-made reasoning trace neither unlocks tasks it fails nor is cost-free (it occasionally derails a task it would have passed). Single-shot injection was net-negative in both strength regimes on code (generator≈beneficiary: net −2 to −9; generator>beneficiary Qwable→gemma: net −3, 1 rescue of 21). This is the field consensus, not a local artifact: "Reasoning that Travels" (arXiv:2605.28913) frames injected reasoning as a capability **amplifier, not a substitute** — success tracks the *receiver's* latent capability — and reasoning is **elicited, not installed** (LIMO/s1). This extends the page's Omega finding: a scaffold can only amplify a receiver that already has headroom to reason.
- **As a COST lever the scaffold is robust and architecture-independent.** It caps the expensive worker's own reasoning tokens at ~**100–175** vs the **3,000–9,000** it burns thinking on its own — a **20–50× reduction of expensive-device tokens**, the reasoning offloaded to the fast (GPU) reasoner. This held across sparse-MoE 35B, dense-GDN 27B (176 vs 9041), and pure-dense gemma-31B (98 vs 3049). The objective it serves is "approximate own-think quality at lower **blended** wall-clock," which pays whenever the worker would over-reason on a slow device.
- **The QUALITY benefit is HEADROOM-CONDITIONAL and must be gated.** The scaffold rescues weak-and-overthinking beneficiaries (35B GPQA 48→73%, +25pp; dense-GDN 27B 6→9/10) but **no-ops an already-saturated one** (gemma-31B 8=8) — again the Omega pattern (less-capable-and-overthinking gains, saturated does not). So it is a **conditional, episodic-memory-gated lever** (apply only where the cheap no-think path fails and the beneficiary over-reasons), not an always-on booster.
- **Injection mode is format-native, not a literal foreign tag; a distilled generator beats a vanilla reasoner.** Cross-family transfer requires delivering the reasoning into the *target's own reasoning slot* — a literal foreign `<think>` prefix does NOT transfer (gemma 63% vs its own no-think 81.5%, Pareto-dominated) while the native `<|channel|>thought` slot lifts +11.1pp / 0 regressions. And a **CoT-distilled generator beats a vanilla reasoner** as the scaffold source (+11.1pp @ 0.58× tokens) — distillation adds value at the source, consistent with the training-distillation findings.
- **Verifier/selector (reasoner grades N candidate answers, best-of-N) is MARGINAL on this stack.** The reasoner doing *its own* task (grade/rank, never transplant) sidesteps the transplant problem, but captured only **+2pp of an +8pp structural ceiling** across three benches — because the beneficiary's errors are mostly **systematic** (per-question bimodal: all-N-candidates-right or all-wrong), and best-of-N only recovers *stochastic* errors. Judgment is sound (93–100% selection accuracy) but inert without a gap. Not worth deploying as-is.

### Broader Prompt Engineering (Low Applicability)

- **Emotional stimuli show inconsistent results across 4+ papers**: EmotionPrompt claims 8% improvement, NegativePrompt claims 12.89%, StressPrompt finds inverted-U performance. All tested on different benchmarks with no cross-validation. No replicable gains on code generation, mathematical reasoning, or factual QA -- the task types that constitute our workload. [intake-196, intake-197, intake-205, intake-224]

- **Personas do not improve factual performance**: Testing 162 roles across 2,410 factual questions shows no improvement from system-prompt personas. Role-playing degrades performance in 7/12 datasets for Llama3. The Jekyll and Hyde framework (ensembling role-playing and neutral prompts) partially mitigates degradation but does not improve over neutral baseline. [intake-225, intake-226]

- **GEPA outperforms GRPO by 6% average with 35x fewer rollouts**: Genetic-Pareto prompt evolution with natural language reflection (Actionable Side Information). Outperforms MIPROv2 by over 10%. Directly relevant to autopilot PromptForge species and now integrated at 30% of PromptForge trials. Compatible with local inference (Ollama/vLLM format). 3-example minimum. [intake-240](https://arxiv.org/abs/2507.19457)

- **Gradient-based prompt optimization reduces sycophancy from 79.24% to 49.90%**: RESGA and SAEGA align prompts with persona directions via mechanistic interpretability. Requires access to model internals for gradient computation -- incompatible with GGUF serving. Research-grade only. [intake-214](https://arxiv.org/abs/2601.02896)

## Actionable for EPYC

### Implemented

- **Conciseness prompting with explicit word limits**: Upgraded from vague "be concise" to format-specific numeric limits across all role prompts. Worker_general: MC answers under 1 sentence, factual under 15 words, open under 60 words. Worker_math: MC letter+1 sentence, numeric under 50 words, proof under 100 words. Architect: under 150 tokens. Coder: code only. Based on CCoT 30-60 word sweet spot and TALE findings.
- **Model-tier-differentiated conciseness**: Architect has aggressive limits, frontdoor stays elaborative (user-facing), coder uses code-only format, thinking model suffix reduced to "Think step by step in think tags. Answer portion: under 50 words."
- **Autopilot PromptForge with GEPA**: LLM-guided mutation supplemented by GEPA evolutionary Pareto optimization at 30% trial share. Comparing acceptance rates in AR-3 journal.
- **Conciseness prompt audit for suppression language**: Verified all prompts use stylistic language, not suppression. No "don't reason about X" or "skip steps" patterns.

### Planned

- **Omega metric as routing signal**: Pre-compute per-suite Omega values from seeding benchmarks with reasoning ON/OFF. Route high-Omega suites to reasoning-capable models, low-Omega suites to fast non-reasoning models. Partially completed: 2026-04-09 evaluation found 7/10 suites where tools/REPL hurt accuracy.
- **SEAL control vectors for Qwen3-32B**: 2-day experiment. Contrastive pair generator (80 problems) and evaluation script (scaling sweep at 0.3/0.5/0.7) prepared. Awaiting model servers.
- **Output-side factual verification**: For high-risk prompts, scan reasoning traces for factual claims and verify against search/knowledge. Hallucinated intermediate facts predict hallucinated final answers. Gate behind high input-side risk score. Architecture: input-side scorer (fast, regex) gates whether to run expensive output-side verification.
- **GEPA ratio decision (AP-21)**: Conditional on AR-3 data. If GEPA trials dominate Pareto frontier after 50+ trials, increase from 30% to 100%. If no improvement, keep mixed or revert.

### Not Actionable

- **Emotional stimuli / persona engineering**: No replicable gains on code, math, or factual QA across 6+ papers and 162 tested roles.
- **FlowSteer MLP-based steering**: No llama.cpp infrastructure for ODE solve at intervention points. SEAL linear baseline is the deployable subset.
- **Gradient-based prompt optimization (RESGA/SAEGA)**: Requires model-internal gradient access. Incompatible with GGUF serving.
- **POSIX sensitivity analysis** (intake-201): Measures prompt sensitivity indices. Theoretically useful for identifying fragile instructions but no clear path to production deployment.

## Open Questions

- Does the inverted controllability finding (larger models more controllable, but we prompt smaller workers) mean we should shift conciseness prompting effort to architect-tier models instead? Or does the difficulty band routing make this moot (easy problems go to workers where brief responses are natural)?
- Can RAG-style fact injection substitute for reasoning tokens on our factual QA suites, given the OFF Facts condition matches reasoning performance? This could eliminate the need for reasoning on factual tasks entirely.
- What is the minimum reasoning budget below which accuracy drops sharply, independent of content quality? The computational buffer finding implies a floor where even dummy tokens matter.
- How does the computational buffer interact with our token budgets? If even meaningless tokens help by 21-27%, truncating at 1500 tokens for easy problems may be cutting into useful computation.
- What is the right GEPA-to-LLM-mutation ratio for PromptForge? The 35x fewer rollouts claim was not benchmarked against LLM-guided mutation specifically.
- Should we invest in `build_cvec()` support for Qwen3.5 (1-hour C++ change) given that 75% of layers are recurrent and steering effectiveness is unknown?

## Related Categories

- [Cost-Aware Routing](cost-aware-routing.md) -- Reasoning compression and difficulty-adaptive budgets are the production application of controllability findings; Omega metric bridges prompting and routing; the CoT-scaffold is an episodic-memory-gated reasoning-effort cost lever (offload reasoning to a fast device, gate to weak-and-overthinking task-classes)
- [Hardware Optimization](hardware-optimization.md) -- the CoT-scaffold study ran on the MI210 (small GPU-resident reasoner + CPU-hosted worker); the GPU-side detail, verifier/selector characterization, and blended-cost mechanism live there
- [Context Management](context-management.md) -- Conciseness prompting reduces context pressure; reasoning trace handling is a context management concern; SEER's loop detection is both prompting and context hygiene
- [Context Extension](context-extension.md) -- Longer context windows may reduce the need for aggressive conciseness prompting; the computational buffer finding suggests minimum context thresholds

## Source References

- [FlowSteer Concise Reasoning](../research/deep-dives/flowsteer-concise-reasoning.md) -- Nonlinear activation steering via flow matching; SEAL linear baseline; llama.cpp `--control-vector` compatibility; Qwen3.5 `build_cvec()` blocker; intervention layer selection
- [Reasoning Recall + CoT Controllability](../research/deep-dives/reasoning-recall-cot-controllability.md) -- Computational buffer (21-27% from dummy tokens); factual priming mechanism; hallucination cascade (41.4% vs 26.4%); Omega metric; controllability spectrum (0.1-15.4%); suppression vs stylistic cost gap
- [Reasoning Compression handoff](../handoffs/active/reasoning-compression.md) -- Conciseness prompt upgrades to explicit word limits; GEPA integration; TrimR evaluation; SEAL control vector prep
- [intake-196](https://arxiv.org/abs/2307.11760) EmotionPrompt -- Emotional stimuli for LLMs (not applicable to our task types)
- [intake-197](https://arxiv.org/abs/2405.02814) NegativePrompt -- Negative emotional stimuli (not applicable)
- [intake-200](https://arxiv.org/abs/2602.21223) Pragmatic Influence -- Hierarchical framing shifts behavior; no clear production application
- [intake-201](https://arxiv.org/abs/2410.02185) POSIX -- Prompt sensitivity index measurement framework
- [intake-205](https://arxiv.org/abs/2409.17167) StressPrompt -- Inverted-U performance under stress conditions (not applicable)
- [intake-209](https://arxiv.org/abs/2410.19221) Story of Thought -- Narrative structures show gains on GPQA/JEEBench, limited applicability
- [intake-214](https://arxiv.org/abs/2601.02896) RESGA/SAEGA -- Gradient-based prompt optimization via mechanistic interpretability; incompatible with GGUF
- [intake-224](https://openreview.net/forum?id=Luq7xtaYeD) Emotional Stimuli Types -- Further emotional prompting evaluation (not applicable)
- [intake-225](https://arxiv.org/abs/2311.10054) Personas Do Not Help -- 162 roles, no improvement on factual questions
- [intake-226](https://arxiv.org/abs/2408.08631) Persona Double-Edged Sword -- Role-playing degrades 7/12 datasets for Llama3
- [intake-240](https://arxiv.org/abs/2507.19457) GEPA -- Genetic-Pareto prompt evolution, 35x fewer rollouts, outperforms MIPROv2 by 10%+
- [GPU CoT-Scaffold Sidecar (full arc)](../handoffs/active/gpu-cot-scaffold-sidecar.md) -- G1/G2/verifier/dense-generalization arc; single-shot capability-transplant falsified both regimes; scaffold = 20–50× CPU-token cost lever; quality headroom-conditional; format-native-slot injection required cross-family; distilled>vanilla generator; verifier/selector marginal (systematic-not-stochastic errors)
- [Scaffold Autopilot Cost-Lever Deployment (DESIGN)](../handoffs/active/scaffold-autopilot-cost-lever-deployment.md) -- episodic-memory-gated deployment of the scaffold as a `capability_registry` cost lever inside autopilot's 4D Pareto (quality/speed/−cost/reliability); blended GPU+CPU cost accounting; NOT implemented
- [Progress 2026-07-06 — CoT study complete](../progress/2026-07/2026-07-06-cot-study-complete.md) -- three-arch × three-lever close-out (GPQA scaffold quality +25pp/−0/no-op table; verifier 3-bench marginal; deployment implication)
- [Reasoning that Travels (arXiv:2605.28913)](https://arxiv.org/abs/2605.28913) -- transplanted reasoning is a capability amplifier not substitute; success tracks the receiver's latent capability (the literature match for the scaffold headroom-conditionality)
- [GenRM / GenPRM verifier literature](https://arxiv.org/abs/2408.15240) -- generative verifier best-of-N (GenRM 2408.15240; GenPRM 2504.00891 — a 1.5B PRM beats GPT-4o as a judge); the "reasoner does its own task" mode, marginal on our systematic-error workloads

## Compiled Update — 2026-07-29: prompt and policy text as the optimized artifact — and what a compile costs

**Confidence**: the cost line and the optimizer-of-record decision are
**verified** as project decisions with cited derivations; every external score
below is **observation-grade** under MEASUREMENT.md and gates nothing on its own.

### The prompt-optimizer of record is GEPA-class, and it makes compile-small / deploy-large viable

The decisive property is **cross-model transfer**: prompts optimized on a
**Qwen3-8B** scored **+9.00 aggregate on GPT-4.1-Mini**, beating every optimizer
tuned *directly* on that larger model. That is what makes **compiling on a cheap
local model and deploying to a larger one** economically viable on a CPU-first
host — the compile does not have to run against the deployment target.
Correspondingly, **BootstrapFewShot\*** is marked **superseded** for 2026-era
instruct models, and **MIPROv2** buys only **+2.6** on Qwen3-8B while
**regressing** on AIME/LiveBench.
[`autopilot-continuous-optimization.md`](../handoffs/active/autopilot-continuous-optimization.md) §AP-29c

### The standing cost line for any prompt-program compilation

10–20 trials over 150–300 validation examples ≈ **1.5k–6k program runs ≈ 5k–25k
LM calls** (independently cross-checked at 1,839–7,051 rollouts). On this host
that is **hours to days per compile**, so a compile is budgeted as a
**region-locked campaign** and **never** as a background task. Any proposal that
treats prompt optimization as free is priced against this line.
[`harness-selection-and-integration.md`](../handoffs/active/harness-selection-and-integration.md) §HS-11

### Prompt text is where the effect lives — a measured 19× over the training objective

The sharpest evidence in this batch that prompt engineering is the load-bearing
lever rather than a finishing touch comes from a distillation paper's own
ablations: the **training objective** is worth **~2pp** over plain cross-entropy,
while a change to the **teacher prompt** is worth **~38pp**. The mechanism is
different from ours but the ordering is the finding — when an approach couples a
prompting change to an algorithmic change, attribute carefully before adopting
the algorithm. Full context in
[Training & Distillation](training-distillation.md).
[`swarm-dataset-distillation.md`](../handoffs/blocked/swarm-dataset-distillation.md) §Premise correction

### Run-level policy as an editable natural-language document

A harness design expressing run-level policy as an editable **document** (with
mechanisms left in code) reports reductions of **60.10k→2.90k tokens / 68→3
files**, **47.50k→1.40k / 5→1**, and **10.50k→0.80k / 3→1** across three agent
systems. **Carry the design, not the numbers** — every arm ran on a closed
frontier mini model. The genuinely novel transfer question is whether an
**open-weight** model can *interpret* such a policy faithfully; nothing in the
source establishes it. Usefully, their adherence metrics (Workflow Preservation,
Stage Coverage, Ordered Workflow, Artifact Contract, Tool Call Success,
Information Handoff Recall) score **policy adherence without a benchmark score**,
so drift is measurable on **saved traces** and is deterministic-replay eligible —
a probe that costs no new inference. Their own red flag travels with it:
**Information Handoff Recall drops to 0.32/0.55 under parent-child execution even
on a frontier model.**
[`harness-selection-and-integration.md`](../handoffs/active/harness-selection-and-integration.md) §HS-8, §HS-9

### A judge prompt's accuracy has a plateau — budget it accordingly

An LLM-judge write gate measures at **72.7% accuracy**, and the source's own
simulation shows ground-truth labels buy only **+4.8pp of a 13.4pp effect**, with
the **70–90% band forming a plateau**. The prompting consequence is direct: spend
the **cheapest adequate local model** on judge prompts of this shape rather than
escalating to a frontier call. This does **not** generalize to every gate — where
an admission test is genuinely load-bearing the budget argument reverses, so the
plateau finding is scoped to the gate it was measured on.
[`autopilot-continuous-optimization.md`](../handoffs/active/autopilot-continuous-optimization.md) §AP-29a

### Source References

- [`autopilot-continuous-optimization.md`](../handoffs/active/autopilot-continuous-optimization.md) — AP-29c (GEPA-class optimizer of record; cross-model transfer; MIPROv2/BootstrapFewShot superseded) and AP-29a (judge-accuracy plateau and the cheapest-adequate-judge rule)
- [`harness-selection-and-integration.md`](../handoffs/active/harness-selection-and-integration.md) — HS-11 compile cost line; HS-8/HS-9 policy-as-document reductions, the open-weight interpretation gap, and the replay-eligible adherence metrics
- [`swarm-dataset-distillation.md`](../handoffs/blocked/swarm-dataset-distillation.md) — the ~2pp objective vs ~38pp teacher-prompting decomposition
- [`progress/2026-07/2026-07-29.md`](../progress/2026-07/2026-07-29.md) — session record of the dive that produced the prompting-over-objective correction
