# Deep Dive: Reasoning Chain Compression for Efficient CoT Inference

**Intake IDs**: intake-125 (S3-CoT), intake-128 (SEER Adaptive Compression)
**Date**: 2026-03-15
**Status**: Research complete, integration paths identified

---

## Executive Summary

These two papers attack the same problem from complementary angles: LLM reasoning chains (CoT) are excessively verbose, and compression can improve both speed and accuracy. S3-CoT discovers a latent "length direction" in model activations and uses it to self-sample shorter training data, then fine-tunes with progressive compression. SEER takes a simpler approach: Best-of-N sampling with MAD-based outlier filtering to build concise training sets, then SFT. Both achieve 20-42% token reduction with accuracy parity or improvement. The key insight shared by both: **shorter is often better** -- failed outputs are consistently longer than successful ones.

For EPYC, the actionable path is SEER-style filtering (no model modification needed, works with any SFT pipeline). S3-CoT's activation steering is architecturally elegant but incompatible with quantized GGUF serving through llama.cpp without significant C++ work.

---

## Paper 1: S3-CoT -- Self-Sampled Succinct Reasoning

**Full title**: "S3-CoT: Self-Sampled Succinct Reasoning Enables Efficient Chain-of-Thought LLMs"
**arXiv**: 2602.01982 (Feb 2026)
**Authors**: Yanrui Du, Sendong Zhao, Yibo Gao, et al.

### 1.1 Core Idea

LLMs have an internal representation direction that controls CoT verbosity. By identifying this Variable-Length Direction (VL-D) in the residual stream, you can steer the model to produce shorter reasoning traces without a teacher model. These shorter traces become self-distillation training data.

### 1.2 Methodology

#### Phase 1: VL-D Identification

For each instruction in the dataset, create two variants:
- `x_l`: instruction + "think step by step in detail" (long CoT prompt)
- `x_s`: instruction + "answer directly and concisely" (short CoT prompt)

Extract activations at the final token position across all layers. Compute the difference-in-means vector at each layer:

```
d^(l) = E[h_n^(l)(x_l) - h_n^(l)(x_s)]
```

Two metrics identify where the VL-D emerges:
- **Mean Separation Strength**: L2 distance between long/short activation pairs per layer
- **Angle Variance**: Angular deviation of direction vectors from their mean (low variance = consistent direction)

The **anchor layer** is where VL-D first becomes measurably consistent. Model-specific findings:

| Model | Anchor Layer | Intervention Layers | Alpha Range |
|-------|-------------|---------------------|-------------|
| Qwen2.5-7B | ~10 | Top 5-10 | -0.1 to -0.3 |
| LLaMA-3-8B | ~8 | Top 5-10 | -0.1 to -0.5 |
| DeepSeek-R1-7B | ~13 | Top 15 | -0.1 to -0.5 |
| Qwen3-Think-4B | ~14 | Top 15 | -0.1 to -0.5 |

#### Phase 2: Activation Steering for Self-Sampling

Apply the intervention during generation:

```
h_i^(l)(x) <- h_i^(l)(x) + alpha * d^(l)
```

- Weak alpha: no effect (Len-R ~ 1.0)
- Moderate alpha: controlled shortening
- Strong alpha: generation collapse (repetition)

Probing on 100 GSM8K samples calibrates the optimal (layers, alpha) pair.

#### Phase 3: Data Filtering

Two verification modes:
1. **Answer verification** (requires gold labels): retain samples matching gold answer. Retention: ~5600/6838 for DeepSeek-R1, ~4560/4564 for Qwen2.5. Accuracy of retained: >99.8%.
2. **Self-consistency verification** (S3-CoT_sc, no gold labels): retain samples where predictions are consistent across variable-length variants. Eliminates gold-answer dependency entirely.

#### Phase 4: Progressive Compression SFT

Training uses dual-cognitive prompts simultaneously:
- **System 1 prompt**: target = compressed CoT (fast thinking)
- **System 2 prompt**: target = original full CoT (deliberate reasoning)

Progressive curriculum over 10 phases:
- Phase 1: Length-Ratio in [0.9, 1.0] (minimal compression)
- Phase 2: [0.8, 1.0]
- ...
- Phase 10: [0.0, 1.0] (full range)

Each phase maintains uniform Len-R distribution via sampling. Checkpoint selection on validation set.

**Training config**: LoRA r=8, alpha=16, 2x A100 80GB. Max generation 65,536 tokens.

### 1.3 Key Results

#### Math Benchmarks

```
Qwen2.5-7B:
┌──────────┬──────────┬────────────┬──────────────┬────────────────┐
│ Benchmark│ Baseline │ Baseline   │ S3-CoT       │ S3-CoT         │
│          │ Acc%     │ Tokens     │ Acc%         │ Tokens         │
├──────────┼──────────┼────────────┼──────────────┼────────────────┤
│ GSM8K    │ 91.83    │ 289.82     │ 93.17        │ 182.80 (-37%)  │
│ MATH     │ 68.50    │ 559.49     │ 70.50        │ 426.91 (-24%)  │
│ AMC23    │ 42.50    │ 846.49     │ 45.83        │ 678.80 (-20%)  │
│ AIME24   │ 14.44    │ 996.75     │ 12.22        │ 800.62 (-20%)  │
└──────────┴──────────┴────────────┴──────────────┴────────────────┘

DeepSeek-R1-7B:
┌──────────┬──────────┬────────────┬──────────────┬────────────────┐
│ Benchmark│ Baseline │ Baseline   │ S3-CoT       │ S3-CoT         │
│          │ Acc%     │ Tokens     │ Acc%         │ Tokens         │
├──────────┼──────────┼────────────┼──────────────┼────────────────┤
│ GSM8K    │ 93.17    │ 1710.27    │ 91.17        │ 1182.04 (-31%) │
│ MATH     │ 93.50    │ 4261.18    │ 92.00        │ 2833.27 (-34%) │
│ AMC23    │ 86.67    │ 6224.23    │ 90.83        │ 5715.74 (-8%)  │
│ AIME24   │ 53.33    │ 14061.22   │ 51.11        │ 12217.53 (-13%)│
└──────────┴──────────┴────────────┴──────────────┴────────────────┘
```

#### Cross-Model Results

- LLaMA-3-8B on GSM8K: 80.17% (+1.3% over baseline), 179.42 tokens (-47%)
- Qwen3-Think-4B on GSM8K: 94.83%, 1029.56 tokens (-32%)

#### AES (Accuracy-Efficiency Score)

```
AES = omega*DeltaLength + beta*|DeltaAcc|  if DeltaAcc >= 0
AES = omega*DeltaLength - gamma*|DeltaAcc| if DeltaAcc < 0
(omega=1, beta=5, gamma=10)
```

Best AES: Qwen2.5-7B at 0.33, outperforming RL baselines.

### 1.4 Ablation: Progressive Curriculum is Essential

Training exclusively on shortest CoTs causes over-compression:
- DeepSeek: -6.4% accuracy drop vs progressive curriculum
- Qwen: -4.5% accuracy drop

### 1.5 Limitations

1. **No quantization discussion**: Paper uses full-precision or LoRA; no mention of GGUF, GPTQ, or INT4/INT8 compatibility
2. **Architecture sensitivity**: DeepSeek-R1 shows "instability in internal properties" from incremental training; VL-D may not exist cleanly in all models
3. **R1-style models**: Both S3-CoT and baselines show slight accuracy degradation on R1-style models
4. **Hyperparameter tuning**: Anchor layer and alpha must be calibrated per model via probing
5. **No inference latency analysis**: Paper reports token counts but not wall-clock time

---

## Paper 2: SEER -- Self-Enhancing Efficient Reasoning

**Full title**: "Reasoning Efficiently Through Adaptive Chain-of-Thought Compression: A Self-Optimizing Framework"
**arXiv**: 2509.14093v2 (Sep 2025, revised Mar 2026)
**Authors**: Kerui Huang, Shuhan Liu, Xing Hu, Tongtong Xu, Lingfeng Bao, Xin Xia

### 2.1 Core Insight: Longer CoT Hurts

GPT-4o compression analysis reveals most CoT content is filler:

| Model | Avg Tokens Before | After Compression | Retained |
|-------|-------------------|-------------------|----------|
| DeepSeek-Qwen-7B | 3,677 | 210 | 5.71% |
| QwQ-32B | 2,311 | 216 | 9.36% |
| Qwen3-8B | 3,456 | 228 | 6.62% |
| gpt-oss-20b | 481 | 149 | 31.11% |

Most models retain **less than 10%** of tokens as meaningful reasoning.

Critical empirical finding: **failed outputs are consistently longer than successful ones**. On HumanEval/129 with DeepSeek-Qwen-7B, failed cases had median 9,489 tokens vs 8,296 for successes (1,193 token gap). This pattern holds across 7B, 14B, and 32B scales.

### 2.2 Methodology

#### Stage 1: Pre-Inference Data Generation

Base model processes training questions with a 16K token budget, generating N=3 candidate solutions per question with full reasoning traces.

#### Stage 2: Best-of-N Sampling

Filter candidates on three criteria:
1. **Correctness**: Only candidates producing correct final answers
2. **Valid CoT**: Non-empty, non-looping reasoning paths (n-gram repetition check, n=30, k=20)
3. **Conciseness**: Among correct options, select shortest CoT

#### Stage 3: Adaptive CoT Filtering (MAD-based)

Distribution-aware threshold using Median Absolute Deviation:

```
lambda_tilde = median(CoT_lengths)
MAD = median(|lambda_i - lambda_tilde|)
cutoff = lambda_tilde + alpha * MAD
```

Default alpha=1. Discard any sample exceeding the cutoff. MAD is more robust to outliers than mean/stddev approaches.

#### Stage 4: SFT

Standard supervised fine-tuning on the filtered dataset. The model internalizes concise reasoning patterns. No architectural modifications, no special inference procedure.

**Training config**: Full-parameter SFT on DeepSeek-R1-Distill-Qwen-7B, 3 epochs, batch size 8, LR 1e-5 with cosine decay, max seq 16,384 tokens. Also compatible with LoRA (retains ~87% of SFT benefits).

### 2.3 Key Results

#### Software Engineering + Math Tasks

```
┌───────────────────┬──────────┬────────────┬──────────┬────────────┬─────────────┐
│ Task              │ Base Acc │ Base Toks  │ SEER Acc │ SEER Toks  │ Compression │
├───────────────────┼──────────┼────────────┼──────────┼────────────┼─────────────┤
│ MathQA-Python     │ 63.7%    │ 1,456      │ 74.9%    │ 877        │ 39.8%       │
│ Defect-Detection  │ 44.7%    │ 1,836      │ 50.5%    │ 785        │ 57.2%       │
│ Code-Search       │ 72.4%    │ 472        │ 77.3%    │ 341        │ 27.8%       │
├───────────────────┼──────────┼────────────┼──────────┼────────────┼─────────────┤
│ Average           │ 60.3%    │ 1,255      │ 67.6%    │ 668        │ 41.6%       │
└───────────────────┴──────────┴────────────┴──────────┴────────────┴─────────────┘
```

#### Baseline Comparison (MathQA-Python)

| Method | Pass@1 | Avg Tokens | Compression |
|--------|--------|-----------|-------------|
| Base | 63.7% | 1,456 | -- |
| Short CoT (prompt) | 55.6% | 1,236 | 15.1% |
| TokenSkip (0.5) | 1.6% | -- | catastrophic |
| TokenSkip (0.8) | -- | -- | partial |
| Naive BoN (N=3) | 73.6% | 1,191 | 18.2% |
| Self-Training | 74.6% | 1,176 | 19.2% |
| **SEER (N=3, a=1)** | **74.9%** | **877** | **39.8%** |

SEER doubles the compression of naive BoN while matching or exceeding accuracy.

#### Loop and Truncation Mitigation

```
┌───────────────────┬────────────────┬────────────────┐
│ Task              │ Base Loops     │ SEER Loops     │
├───────────────────┼────────────────┼────────────────┤
│ MathQA-Python     │ 85 (4.5%)      │ 23 (1.2%)  -73%│
│ Code-Search       │ 15 (0.16%)     │ 1  (0.01%) -93%│
│ Defect-Detection  │ 222 (8.1%)     │ 7  (0.26%) -97%│
└───────────────────┴────────────────┴────────────────┘
```

90.4% of truncation cases are loops (n-gram repetition detection). SEER eliminates 73-97% of loops.

#### Cross-Domain Transfer

Fine-tuned on SE tasks, evaluated on HumanEval and MBPP:
- HumanEval: 82.8-87.8% (vs 78.0% base), ~40% token reduction
- MBPP: 75.7% (vs 73.5% base), ~32% token reduction

Compression behaviors transfer across domains.

### 2.4 Ablation

**BoN size saturation at N=3**: N=1 -> 73.49%, N=3 -> 74.45%, N=5 -> 74.40%. Marginal returns beyond 3.

**MAD filter strictness (alpha)**:
- alpha=2.0: 74.40% acc, 26.4% compression (loose)
- alpha=1.0: 73.50% acc, 39.7% compression (balanced)
- alpha=0.5: 72.76% acc, 42.6% compression (aggressive, -0.74% acc)

**LoRA vs Full SFT**: LoRA achieves 67.71% pass@1 vs 74.88% full SFT. LoRA retains ~87% of benefit at lower compute cost.

### 2.5 Limitations

1. **Single model family**: Only tested on DeepSeek-R1-Distill-Qwen-7B
2. **Domain bias**: Primarily software engineering tasks; math evaluation limited
3. **Hard problems excluded?**: MAD filtering may systematically exclude genuinely difficult problems that require longer reasoning
4. **No dynamic inference**: Compression is baked into the fine-tuned model; cannot adjust at inference time
5. **Prompt sensitivity**: Not fully explored despite fixed-prompt design

---

## Comparative Analysis

### Shared Findings

Both papers confirm the same core insight: **verbose CoT is wasteful and often counterproductive**. Models generate 90%+ filler tokens. Failed attempts are longer than successful ones. Compression improves both efficiency and accuracy up to a point.

### Key Differences

| Dimension | S3-CoT | SEER |
|-----------|--------|------|
| Data generation | Activation steering | Best-of-N sampling |
| Requires gold labels | Optional (S3-CoT_sc mode) | Yes (correctness filter) |
| Model modification | Activation intervention during sampling | None |
| Training method | LoRA with progressive curriculum | Full SFT or LoRA |
| Compression rate | 20-37% (math), ~40% (medical) | 28-57% (SE), ~40% (cross-domain) |
| Accuracy impact | Neutral to slight gain (general), slight loss (R1) | Consistent improvement |
| Architecture scope | Qwen, LLaMA, DeepSeek families | DeepSeek-Qwen only |
| Loop mitigation | Not addressed | 73-97% reduction |
| Inference change | None (post fine-tune) | None (post fine-tune) |
| Compute cost | 2x A100 80GB | Standard SFT hardware |

### Complementarity

The methods are combinable. S3-CoT provides a principled data generation mechanism (activation steering for variable-length traces). SEER provides a robust filtering pipeline (MAD-based outlier removal). A combined pipeline would:
1. Use S3-CoT activation steering to generate variable-length candidates (richer than standard sampling)
2. Apply SEER's MAD filtering to remove outlier-length traces
3. Train with S3-CoT's progressive curriculum

---

## EPYC Integration Analysis

### Integration Path A: SEER-Style Filtering (Low Effort, High Impact)

**What**: Apply Best-of-N + MAD filtering to our existing seeding/fine-tuning pipeline.

**Changes required**:
- Add a filtering stage to `seed_specialist_routing.py` that collects N=3 responses per question, filters for correctness, and applies MAD-based length thresholds
- No llama.cpp changes
- No model architecture changes
- Works with any GGUF model we already serve

**Where in the codebase**:
- `/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/seed_specialist_routing.py` -- add BoN+MAD pipeline
- `/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/question_pool.py` -- tag questions with expected CoT length distribution
- `/mnt/raid0/llm/epyc-orchestrator/src/graph/helpers.py` -- adjust `_repl_turn_token_cap()` dynamically based on task complexity

**Effort**: ~2-3 days implementation, ~1 day validation
**Risk**: Low. Pure data filtering, no model or infrastructure changes.

### Integration Path B: Dynamic Token Budget at Inference Time (Medium Effort)

**What**: Use SEER's finding that failed outputs are longer to implement adaptive token budgets. If the model is generating an unusually long response relative to MAD-based thresholds for that task type, truncate early and retry with a "be concise" system prompt.

**Changes required**:
- Track per-task-type CoT length distributions in the orchestrator
- Add length monitoring to the streaming inference path
- Implement adaptive truncation + retry logic in `src/graph/helpers.py`
- Add task-type classification to route requests to appropriate length profiles

**Where in the codebase**:
- `/mnt/raid0/llm/epyc-orchestrator/src/inference.py` -- streaming length monitor
- `/mnt/raid0/llm/epyc-orchestrator/src/graph/helpers.py` -- adaptive retry with conciseness prompt
- `/mnt/raid0/llm/epyc-orchestrator/src/graph/session_log.py` -- log CoT length statistics for MAD computation

**Effort**: ~3-5 days
**Risk**: Medium. Requires careful threshold tuning per model/task pair.

### Integration Path C: S3-CoT Activation Steering (High Effort, Research-Grade)

**What**: Implement VL-D extraction and activation steering in llama.cpp to dynamically control CoT verbosity during inference.

**Feasibility Assessment**:

The core challenge is that **activation steering requires modifying intermediate layer representations during forward passes**. In llama.cpp:

1. **Layer intervention points**: `llama_decode()` processes through `llm_build_*` functions that construct the compute graph. Intervening requires adding steering vectors as graph operations between layer outputs. This is architecturally possible (similar to how `llama_set_n_layer_exit()` works for self-speculation) but requires:
   - Pre-computed steering vectors stored per-layer (new model metadata or side-loaded tensors)
   - A graph modification in `llama_build_graph()` to add the steering offset
   - An API to set steering strength (alpha) at runtime

2. **Quantization compatibility**: This is the critical blocker. Steering vectors are computed from full-precision activations. When the model is quantized to Q4_K_M or Q6_K:
   - The residual stream is dequantized during forward pass, so intervention CAN happen on the dequantized activations
   - However, the steering vectors were computed from a different precision model -- the VL-D may not transfer cleanly across quantization levels
   - No published research validates this transfer

3. **GGUF format**: Steering vectors would need to be stored alongside the model or in a separate file. The GGUF format supports arbitrary metadata tensors, so this is feasible but requires tooling.

**Where in the codebase**:
- `/mnt/raid0/llm/llama.cpp/src/llama-context.cpp` -- add steering vector storage and graph modification
- `/mnt/raid0/llm/llama.cpp/common/arg.cpp` -- new CLI flags (`--steering-vectors`, `--steering-alpha`)
- `/mnt/raid0/llm/llama.cpp/examples/server/server.cpp` -- API endpoint for dynamic alpha control

**Effort**: ~2-3 weeks C++ work + validation
**Risk**: High. Quantization transfer is unvalidated. Requires per-model VL-D extraction (Python preprocessing step).

### Integration Path D: REPL Pipeline Loop Mitigation (Low Effort, Immediate Value)

**What**: SEER's n-gram loop detection (n=30, k=20) directly addresses a known EPYC failure mode. Our REPL pipeline already has anti-loop detection in session_log.py (code hash repetition), but adding token-level n-gram detection would catch loops within a single generation.

**Changes required**:
- Add n-gram repetition detector to streaming output in `inference.py`
- On loop detection: cancel generation, retry with modified prompt
- Log loop events for MAD baseline computation

**Where in the codebase**:
- `/mnt/raid0/llm/epyc-orchestrator/src/inference.py` -- `_on_chunk_guarded()` already has cancel check; add n-gram monitor
- `/mnt/raid0/llm/epyc-orchestrator/src/graph/session_log.py` -- log loop detection events

**Effort**: ~1 day
**Risk**: Very low. Pure monitoring + early termination.

---

## Compatibility with Current Infrastructure

### Qwen3 Models

- S3-CoT explicitly tests Qwen2.5-7B and Qwen3-Think-4B with good results
- **Qwen3.5 (hybrid SSM/attention)**: S3-CoT's VL-D analysis assumes dense transformer residual streams. Hybrid SSM architectures have fundamentally different activation patterns in Mamba2 blocks. VL-D may not exist in the same form. The attention blocks (every 4th layer in Qwen3.5) would be the only viable intervention points, drastically reducing the intervention surface.
- **Dense Qwen3-32B**: Full compatibility expected. 64 layers provides ample intervention range.
- SEER has no architecture constraints -- works with any model that can generate CoT.

### llama.cpp Serving

- SEER: Fully compatible. No serving changes needed. Only affects training data.
- S3-CoT activation steering: Requires C++ modifications (see Path C above). The `llama_set_n_layer_exit()` API added for HSD/self-speculation provides a precedent for per-layer intervention, but steering is additive modification rather than early exit.

### REPL Pipeline

- Both methods' outputs (shorter CoT) directly benefit the REPL pipeline where truncation is a known issue
- SEER's loop detection is immediately applicable to the `_on_chunk_guarded()` streaming path
- Shorter CoT means fewer tokens consumed by the `_repl_turn_token_cap()` budget, leaving more room for actual code generation

---

## Recommendations

### Immediate (This Sprint)

1. **Implement n-gram loop detection** in streaming inference (Path D). Direct value, minimal risk. SEER parameters: n=30, k=20 (30-gram repeated 20+ times indicates loop).

2. **Prototype SEER filtering** on our existing seeding pipeline. Run 3 candidates per question, apply MAD filtering, measure compression and accuracy on our 23 benchmark suites.

### Near-Term (Next 2 Sprints)

3. **Dynamic token budgets** per task type (Path B). Use accumulated CoT length distributions from inference_tap to compute MAD thresholds. Flag generations exceeding threshold for early termination + retry.

4. **Evaluate S3-CoT's self-consistency mode** as a data quality filter for our seeding pipeline. The no-gold-label requirement is attractive for domains where we lack ground truth.

### Research Track

5. **VL-D extraction for dense Qwen3-32B**: Run the probing analysis on our production model. If a clean VL-D exists, the progressive compression curriculum could produce a "fast-thinking" LoRA adapter that switches the model between verbose and concise modes.

6. **Quantization transfer study**: Extract VL-D from f16 model, apply to Q4_K_M/Q6_K quantized versions, measure whether compression still works. This is the key unknown blocking Path C.

---

## Open Questions

1. **Does VL-D exist in hybrid SSM architectures?** Qwen3.5's Mamba2 blocks process information differently from attention layers. The concept of a unified length direction may not apply.

2. **MAD filtering on hard problems**: Both papers acknowledge that aggressive compression may systematically exclude genuinely difficult problems. For our REPL pipeline (which handles multi-step code generation), this could bias toward simpler solutions.

3. **Combined approach**: Can S3-CoT's activation-steered data generation feed into SEER's MAD filtering? No published work on this combination.

4. **LoRA switching at inference**: S3-CoT's LoRA adapter could theoretically be hot-swapped at inference time to toggle between verbose and concise modes. llama.cpp supports LoRA loading; the question is whether the routing decision (when to use concise mode) can be made reliably before generation starts.

5. **REPL-specific compression**: Both papers evaluate on single-turn tasks. Our REPL pipeline is multi-turn with state accumulation. Compression within individual turns may interact with cross-turn context in unexpected ways.

---

## References

- Du, Y., Zhao, S., Gao, Y., et al. (2026). "S3-CoT: Self-Sampled Succinct Reasoning Enables Efficient Chain-of-Thought LLMs." arXiv:2602.01982.
- Huang, K., Liu, S., Hu, X., et al. (2025/2026). "Reasoning Efficiently Through Adaptive Chain-of-Thought Compression: A Self-Optimizing Framework." arXiv:2509.14093v2.
