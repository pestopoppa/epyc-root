# LLM Prompting

**Category**: `llm_prompting`
**Confidence**: verified
**Last compiled**: 2026-04-13
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

- [Cost-Aware Routing](cost-aware-routing.md) -- Reasoning compression and difficulty-adaptive budgets are the production application of controllability findings; Omega metric bridges prompting and routing
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
