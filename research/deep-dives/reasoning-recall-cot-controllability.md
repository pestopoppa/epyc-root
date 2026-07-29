# Deep Dive: Reasoning Recall and CoT Controllability

**Date**: 2026-03-15
**Intake IDs**: intake-103, intake-120
**Papers**: arxiv:2603.09906, arxiv:2603.05706

---

## Paper 1: Thinking to Recall — How Reasoning Unlocks Parametric Knowledge in LLMs

**Authors**: Zorik Gekhman, Roee Aharoni, Eran Ofek, Mor Geva, Roi Reichart, Jonathan Herzig
**Published**: 2026-03-10 | [arxiv:2603.09906](https://arxiv.org/abs/2603.09906)

### Core Question

Why does chain-of-thought reasoning improve factual recall on *simple, single-hop* questions that require no multi-step decomposition? The paper shows this is not about logical decomposition but about two distinct mechanisms that expand the model's effective parametric recall boundary.

### Methodology

The authors run controlled experiments on Gemini-2.5-Flash (primary) with comparative analysis on Gemini-2.5-Pro and Qwen3-32B. Two benchmarks:
- **SimpleQA-Verified**: Hard factual recall (low baseline accuracy ~20-28%)
- **EntityQuestions**: Entity-centric factual questions (higher baseline ~45-57%)

Key experimental conditions:
- **OFF**: Standard prompting, no reasoning
- **ON**: Standard chain-of-thought reasoning enabled
- **ON Dummy**: Replace reasoning trace with repeated dummy phrase "Let me think." matching original trace length
- **ON Single Dummy**: Single occurrence of "Let me think." (short trace)
- **ON Facts**: Override trace with extracted fact list, regenerate answer
- **OFF Facts**: Provide extracted facts as context with reasoning disabled
- **ON/OFF Dummy Facts**: Replace facts with dummy strings of similar length

### Two Mechanisms Identified

**Mechanism 1 — Computational Buffer**: The model uses generated reasoning tokens to perform latent computation *independent of their semantic content*. Evidence: ON Dummy (meaningless tokens of matching length) substantially outperforms OFF, while ON Single Dummy (short meaningless trace) performs worse. The extra forward passes from longer traces provide computation depth that bypasses the bottleneck of a single forward pass.

- SimpleQA: OFF baseline 0.206 accuracy, ON Dummy improves to 0.262 (+27% relative)
- EntityQuestions: OFF baseline 0.457, ON Dummy improves to 0.554 (+21% relative)

**Mechanism 2 — Factual Priming**: Generating topically related facts acts as a semantic bridge that facilitates correct answer retrieval. Evidence: ON Facts and OFF Facts both substantially outperform dummy variants. ON Facts matches full reasoning ON performance on EntityQuestions while using dramatically less compute.

### The Omega Metric

**Definition**: A weighted-average measure of reasoning effectiveness across the pass@k curve. Captures how much reasoning expands the model's capability boundary at larger k values.

**Formula** (Equation 1):

```
Omega = sum_{k=1}^{N} [k * (pass@k_ON - pass@k_OFF) / pass@k_OFF] * 1 / sum_{k'=1}^{N} k'
```

This is a linearly-weighted average of relative pass@k improvements. Higher k values get more weight because they measure the *boundary* of what the model can produce — whether the correct answer exists anywhere in the model's sample distribution, even if it is not the top-1 choice.

**Key Pattern**: Less capable models benefit more from reasoning. Qwen3-32B shows the highest Omega values; Gemini-2.5-Pro shows the lowest. This is because stronger models already recall more facts at pass@1, leaving less headroom for reasoning to compensate.

**SimpleQA consistently produces higher Omega than EntityQuestions** because its lower OFF baseline means more room for improvement.

**EPYC Relevance**: We can compute Omega on our existing benchmark infrastructure. The formula only requires pass@k curves with reasoning ON vs OFF. This maps to:
1. Run seed_specialist_routing.py with a reasoning model (e.g., Qwen3-32B with thinking enabled)
2. Compare pass@k distributions with `<think>` tags stripped vs preserved
3. Compute Omega per-suite to identify which question types benefit most from reasoning

If Omega is low for a suite, reasoning tokens are wasted — route to a non-reasoning model. If Omega is high, reasoning is critical for that question type.

### Hallucination Cascade Analysis

**Critical finding**: Hallucinating intermediate facts during reasoning increases final-answer hallucination rate.

- SimpleQA: Clean (hallucination-free) traces produce correct answers 41.4% of the time; hallucinated traces only 26.4%
- EntityQuestions: Clean traces 71.1% correct; hallucinated traces 32.2% correct

Regression analysis shows slopes of 0.84 (SimpleQA) and 0.86 (EntityQuestions), indicating a systematic within-question gap. This is not explained by question difficulty — the effect persists after controlling for difficulty.

**Mechanism**: The paper calls this "generative self-retrieval." When the model fabricates an intermediate fact, it primes itself with false context that corrupts downstream retrieval. The factual priming mechanism works in both directions — correct priming helps, incorrect priming hurts.

### Verified-Fact Filtering Results

**Test-Time Selection** — filter generated reasoning traces, keeping only those with verified factual statements:

| Benchmark | Baseline (OFF) | ON (unfiltered) | Only Facts | Only Correct Facts |
|-----------|-----------------|------------------|------------|---------------------|
| SimpleQA-Verified | 27.9% | — | 30.2% (+8.2% rel) | 31.3% (+12.2% rel) |
| EntityQuestions | 56.9% | — | 58.4% (+2.6% rel) | 59.8% (+5.1% rel) |

**Verification Method**: Search-enabled Gemini-2.5-Flash verifies each intermediate fact independently across 100 samples per question.

### Question Complexity Analysis

Complex questions labeled "requires reasoning" showed overlapping confidence intervals with simple questions, indicating that reasoning effectiveness poorly predicts question complexity. The gains stem from parametric recall enhancement, not logical decomposition. This is a counterintuitive but important insight — reasoning helps not because it reasons, but because it computes and primes.

---

## Paper 2: Reasoning Models Struggle to Control their Chains of Thought

**Authors**: Chen Yueh-Han, Robert McCarthy, Bruce W. Lee, He He, Ian Kivlichan, Bowen Baker, Micah Carroll, Tomek Korbak (OpenAI)
**Published**: 2026-03-05 | [arxiv:2603.05706](https://arxiv.org/abs/2603.05706)
**Blog**: [OpenAI — Reasoning models struggle to control their chains of thought, and that's good](https://openai.com/index/reasoning-models-chain-of-thought-controllability/)

### Core Question

Can reasoning models selectively control what appears in their chain-of-thought? If so, this could undermine CoT-based monitoring systems, as models could learn to hide dangerous reasoning from monitors.

### Methodology — CoT-Control Evaluation Suite

The suite contains 14,076 problems drawn from GPQA, MMLU-Pro, HLE, BFCL, and SWE-Bench Verified. Three categories of controllability instructions with three difficulty levels each:

1. **Information Suppression**: "Solve this genetics question without using the word 'DNA' in your reasoning" — tests whether models can avoid verbalizing specific concepts
2. **Information Addition**: "Include a mention of X in your reasoning" — tests whether models can inject arbitrary content
3. **Stylistic Modification**: "Reason in a particular style/format" — tests cosmetic control over CoT structure

### Model-by-Model CoT Controllability Scores

13 reasoning models tested. Key results:

| Model | CoT Controllability | Output Controllability | Ratio |
|-------|--------------------|-----------------------|-------|
| DeepSeek R1 | 0.1% | ~20% (est.) | ~200x gap |
| Qwen3 14B | 0.6% | — | — |
| GPT-OSS 20B | 0.9% | — | — |
| Qwen3 32B | 2.3% | — | — |
| Claude Sonnet 4.5 | 2.7% | 61.9% | 23x gap |
| GPT-OSS 120B | 5.9% | — | — |
| GPT-5 / GPT-5.1 / GPT-5.2 | (figure data) | >=60% | — |
| o3 / o4-mini | (figure data) | — | — |

**Range**: 0.1% to 15.4% across all models. Most models achieve >=60% output controllability and >=70% external reasoning controllability for the same tasks.

### Controllability vs Monitorability Tradeoff

**Core insight**: Low controllability implies high monitorability. If a model cannot suppress specific concepts from its CoT, then a monitor reading the CoT will reliably detect when the model is reasoning about those concepts. This is a *positive* result for AI safety.

**Quantified gap**: CoT controllability is 1-2 orders of magnitude lower than output controllability. Claude Sonnet 4.5 demonstrates a 23x gap (2.7% vs 61.9%). DeepSeek R1 shows a ~200x gap (0.1% vs ~20%).

**Implication**: Models can control what they *say* far more than what they *think*. The reasoning process is, in a meaningful sense, more transparent than the final output.

### Factors Affecting CoT Controllability

**Model size (positive)**: Larger open-weight models exhibit higher CoT controllability with a logarithmic relationship to parameter count. GPT-OSS 120B (5.9%) vs GPT-OSS 20B (0.9%).

**RL training (negative)**: CoT controllability decreases by over an order of magnitude during RL training (shown on OLMo-3-7B-RL-Zero-Math). Math and coding domains show steeper declines than general chat. RL training selects for reasoning effectiveness, not for instruction-following within the CoT.

**Test-time compute (negative)**: Controllability decreases as inference-time compute increases. More thinking = less ability to simultaneously control what is thought.

**Problem difficulty (negative)**: Harder problems reduce controllability further.

**Monitoring awareness**: Models show marginally improved controllability when informed about monitoring, but the effect is small. Adversarial prompt optimization produces minimal controllability improvements.

### Performance Cost of Controllability

Information suppression causes notable accuracy drops of 6.0-16.7 percentage points, while addition and stylistic modifications cause <=2.7pp drops. This suggests suppression is genuinely harder — the model cannot avoid using relevant concepts without also losing the ability to solve the problem.

---

## Cross-Paper Analysis

### The Reasoning Paradox

These two papers together reveal a fundamental tension:

**Paper 1** shows that reasoning tokens serve as a computational buffer and factual primer — they expand the model's effective knowledge boundary. The semantic content matters (factual priming) but even meaningless tokens help (computational buffer).

**Paper 2** shows that the content of reasoning tokens is largely uncontrollable. Models cannot suppress, add, or stylistically modify their CoT with any reliability (0.1-15.4%).

**Combined insight**: Reasoning is effective precisely because it is uncontrollable. The model reasons about what it *needs* to reason about, not what it is *told* to reason about. Attempts to constrain reasoning (e.g., conciseness prompts, topic avoidance) operate in the low-controllability regime.

### What This Means for Conciseness Prompting

Our reasoning compression handoff (reasoning-compression.md) reports that OPSDC achieves 37% token reduction via conciseness prompting with comparable accuracy. Paper 2 says CoT controllability is 0.1-15.4%.

**These are not contradictory.** The key distinction is:

1. **Stylistic/length control** (what conciseness prompting does) is the *easiest* category of controllability. The paper shows stylistic modification causes <=2.7pp accuracy drops, vs 6-16.7pp for suppression. Length reduction is a stylistic property, not information suppression.

2. **CoT-Control measures strict compliance** (e.g., "never use the word X"). Conciseness prompting does not require strict compliance — partial length reduction still saves tokens.

3. **RL-trained reasoning models** (o3, R1, etc.) have the lowest controllability. Models without reasoning-specific RL (Qwen3 in standard mode, Gemini Flash) may be more responsive to conciseness instructions. OPSDC trains the conciseness behavior via self-distillation, bypassing the controllability limitation entirely.

4. **The computational buffer finding** (Paper 1) warns that aggressive compression risks removing useful computation tokens. Easy problems tolerate compression (OPSDC: 56-59% on easy), hard problems resist it (35% on hard, AIME drops 5.4pp). This aligns with our difficulty-adaptive routing signal.

**Recommendation**: Continue conciseness prompting for tier-3 workers. Do NOT attempt to suppress specific reasoning patterns (e.g., "don't reason about X") — this falls in the suppression category with high accuracy cost and near-zero compliance.

---

## EPYC Implications

### 1. Factual Risk Scorer Enhancement

Our `factual_risk.py` currently scores INPUT-side features only (regex-based). Paper 1 suggests an OUTPUT-side complement:

**Verified-Fact Filtering**: After the model generates a response with reasoning, scan the reasoning trace for factual claims and verify them. Traces with hallucinated intermediate facts predict hallucinated final answers (41.4% vs 26.4% accuracy on SimpleQA).

**Implementation path**:
- Add an optional OUTPUT-side hallucination detector to the factual risk pipeline
- Extract factual claims from `<think>` blocks using entity/date/number patterns (similar to existing `_extract_features` but applied to model output)
- Cross-reference claims against high-confidence sources (knowledge graph, search)
- Flag responses where intermediate reasoning contains unverified claims
- This is expensive (requires verification inference) — gate behind `factual_risk.mode = "enforce"` AND high input-side risk score

**Architecture**: This does NOT replace the current input-side scorer. It extends it:
```
Input → factual_risk.assess_risk(prompt)     → input risk score (fast, regex)
Output → factual_risk.verify_reasoning(trace) → output risk score (slow, model-based)
Combined risk = f(input_risk, output_risk)
```

The input-side scorer gates whether to run the expensive output-side verification. Only prompts with medium/high input risk warrant output verification.

### 2. Omega Metric for Routing Decisions

Paper 1's Omega metric can serve as a per-suite routing signal:

- **High Omega suites**: Reasoning substantially helps. Route to reasoning-capable models (Qwen3-32B with thinking, architect tier).
- **Low Omega suites**: Reasoning adds cost but not accuracy. Route to fast non-reasoning models (worker tier).

**Computation**: We can measure Omega using existing infrastructure:
1. For each benchmark suite, generate pass@k curves with reasoning ON vs OFF
2. Compute Omega per-suite using the weighted average formula
3. Store in model_registry.yaml as a per-suite annotation

**This directly maps to our difficulty_signal.py** — if we can predict question type at inference time (which the difficulty classifier already approximates), we can use pre-computed Omega values to decide whether reasoning is worth the token cost.

### 3. Reasoning Compression Strategy Validation

Paper 2 validates our tiered approach:

- **Tier 1 (zero-training) methods are safe**: Conciseness prompting, TrimR pruning, and short-m@k are stylistic/length modifications — the controllability category with lowest accuracy cost (<=2.7pp).
- **Information suppression is dangerous**: Do not try to instruct models to "avoid reasoning about X" or "skip steps Y and Z." This is the 0.1-15.4% controllability regime with 6-16.7pp accuracy cost.
- **RL-trained reasoning models are least controllable**: DeepSeek R1 (0.1%), small Qwen3 RL variants (0.6%). Our conciseness prompts may have minimal effect on these models specifically.
- **Larger models are more controllable**: If we add conciseness prompts, they will have more effect on 32B+ models than on 7B-14B workers. This is inverted from our current deployment — we prompt workers for conciseness but those are the models least likely to comply.

### 4. Quality Detection Pipeline

Paper 1's hallucination cascade finding has direct implications for our `debug_scorer.py`:

- **Current state**: We score final answers. We do not inspect reasoning traces.
- **Opportunity**: For `llm_judge` scoring method, we could incorporate reasoning trace quality as a scoring signal. If the trace contains fabricated facts (detectable via pattern matching for confident factual assertions that contradict the final answer), reduce the quality score.
- **Practical benefit**: During seeding runs, this would identify models that "get lucky" despite poor reasoning, vs models with clean reasoning chains — the latter are more reliable in production.

### 5. Connection to REPL Token Cap

Our REPL token cap (5000 tokens, `ORCHESTRATOR_REPL_TURN_N_TOKENS`) is a crude form of reasoning compression. Paper 1's computational buffer finding suggests:

- **Too-low cap removes useful computation tokens**: The model needs forward passes for latent computation. Truncating at 5000 tokens may cut off the computational buffer effect before it completes.
- **Difficulty-adaptive cap is the right direction**: Our difficulty_signal.py (shadow mode) could eventually modulate the token cap. Easy problems: 2000 tokens. Hard problems: 8000+ tokens.
- **The factual priming effect suggests**: For factual questions, injecting relevant facts into context (RAG-style) could substitute for reasoning tokens. This is the OFF Facts condition, which matched ON Facts performance on EntityQuestions.

---

## Key Numerical Reference

### Paper 1 — Thinking to Recall

| Metric | SimpleQA-Verified | EntityQuestions |
|--------|-------------------|-----------------|
| OFF baseline accuracy | 0.206 (20.6%) | 0.457 (45.7%) |
| ON Dummy accuracy | 0.262 (26.2%) | 0.554 (55.4%) |
| Hallucination-free trace accuracy | 41.4% | 71.1% |
| Hallucinated trace accuracy | 26.4% | 32.2% |
| Verified-fact filtering (facts only) | +8.2% relative | +2.6% relative |
| Verified-fact filtering (correct facts) | +12.2% relative | +5.1% relative |
| Hallucination cascade regression slope | 0.84 | 0.86 |

### Paper 2 — CoT Controllability

| Model | CoT Controllability | Output Controllability |
|-------|--------------------|-----------------------|
| DeepSeek R1 | 0.1% | ~20% |
| Qwen3 14B | 0.6% | — |
| GPT-OSS 20B | 0.9% | — |
| Qwen3 32B | 2.3% | — |
| Claude Sonnet 4.5 | 2.7% | 61.9% |
| GPT-OSS 120B | 5.9% | — |
| Range (all 13 models) | 0.1% — 15.4% | >=60% typical |

| Controllability Category | Accuracy Cost |
|--------------------------|---------------|
| Information Suppression | 6.0 — 16.7pp |
| Information Addition | <=2.7pp |
| Stylistic Modification | <=2.7pp |

---

## Action Items

1. **[Low effort]** Add Omega metric computation to `seed_specialist_routing.py` — run with reasoning ON/OFF, compute per-suite Omega, store results
2. **[Low effort]** Audit conciseness prompts: ensure they use stylistic language ("be concise", "use fewer words") not suppression language ("don't reason about", "skip steps for")
3. **[Medium effort]** Prototype output-side factual verification in `factual_risk.py` — extract claims from `<think>` blocks, verify against search/knowledge
4. **[Medium effort]** Correlate difficulty_signal.py bands with measured Omega values from benchmarks — validate whether difficulty prediction proxies reasoning benefit
5. **[Low effort]** Document in reasoning-compression.md that stylistic compression (TrimR, conciseness) is safe but content suppression is not, citing Paper 2

---

## Sources

- [Thinking to Recall: How Reasoning Unlocks Parametric Knowledge in LLMs — arxiv:2603.09906](https://arxiv.org/abs/2603.09906)
- [Reasoning Models Struggle to Control their Chains of Thought — arxiv:2603.05706](https://arxiv.org/abs/2603.05706)
- [OpenAI Blog: Reasoning models struggle to control their chains of thought, and that's good](https://openai.com/index/reasoning-models-chain-of-thought-controllability/)
- [EmergentMind summary — 2603.09906](https://www.emergentmind.com/papers/2603.09906)
- [Paperium analysis — Thinking to Recall](https://paperium.net/article/en/15426/thinking-to-recall-how-reasoning-unlocks-parametric-knowledge-in-llms)
