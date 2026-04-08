# Deep Dive: KV Cache Selection/Eviction Cluster (intake-284, 287, 288) + Training Methods (285, 286)

**Date**: 2026-04-08
**Scope**: All 5 entries from intake batch 284-288
**Purpose**: Validate initial intake assessments against full paper methodology and results

---

## intake-284: TriAttention — ASSESSMENT REVISED

### Initial Assessment
novelty=high, relevance=high, credibility=3, verdict=new_opportunity

### Revised Assessment
novelty=high, relevance=high, **credibility=4** (↑), verdict=new_opportunity

### Critical Finding: The "Matches Full Attention" Headline Is Nuanced

The abstract claims TriAttention "matches Full Attention reasoning accuracy" — this is true **at the throughput-matched operating point** (where you trade budget for throughput parity). At a fixed 2048-token KV budget:

| Benchmark | Full Attention | TriAttention (2048) | SnapKV | R-KV |
|-----------|---------------|---------------------|--------|------|
| AIME25 | 40.8% | **32.9%** (−7.9pp) | 20.0% | 17.5% |
| AIME24 | 57.1% | **42.1%** (−15.0pp) | 34.6% | 25.4% |
| MATH500 | 69.6% | **68.4%** (−1.2pp) | 49.2% | 46.4% |

**Interpretation**: TriAttention is decisively the best KV eviction method — it roughly halves the gap between baselines and Full Attention on AIME, and is near-lossless on MATH500. But "matches" Full Attention is only accurate at specific operating points, not across the board.

### Methodological Strengths (Confirmed)

1. **Q/K concentration is real**: Mean Resultant Length R ≈ 0.977–0.980 across tested models. This is an intrinsic property, not an artifact.
2. **Ablation validates trigonometric scoring**: Removing S_trig collapses AIME24 from 42.1% → 18.8% (−23.3pp). The trig series is doing the heavy lifting.
3. **Calibration is robust**: Works with 50K-960K tokens of ANY data (even "Google homepage HTML"). Model-intrinsic property means calibration data quality doesn't matter.
4. **Architecture breadth**: Validated on GQA (Qwen3-8B), standard MHA (DeepSeek), AND Multi-head Latent Attention with 940 heads (GLM-4.7-Flash). Broader than initially assessed.
5. **Future offset evaluation**: Scores across geometric distance offsets D={1,2,4,...,2^16}, making it robust to token position within the sequence.

### Methodological Concerns

1. **No quantization interaction tested**: The paper doesn't discuss combining TriAttention with KV quantization. For our stack (Hadamard + q4_0/q8_0), this is the critical unknown. Does trigonometric scoring still work on quantized K vectors? The scoring uses pre-RoPE centers (offline) and current K norms (online) — the norm signal would degrade under quantization.
2. **Scoring overhead unquantified**: The paper doesn't separate scoring cost from throughput measurements. The window-based pruning triggers every 128 tokens — unknown if this introduces latency spikes.
3. **Recursive reasoning degrades beyond depth 18**: On their recursive memory benchmark, TriAttention lags Full Attention at extreme recursion depth. For multi-turn reasoning chains, this could compound.
4. **vLLM-only**: Apache 2.0 licensed Python/CUDA code. A llama.cpp port would require:
   - C++ implementation of trigonometric scoring (pure math — feasible)
   - Integration with llama.cpp's KV cache eviction path (if it exists — need to check)
   - Per-model calibration files (offline, one-time)

### Credibility Upgrade: 3 → 4
- Song Han lab (MIT/NVIDIA) = major authority (+1)
- Published within 12 months (+1)
- Code released, Apache 2.0 (+1 corroboration)
- Validated on 5 model architectures including MLA (+1 breadth)
- No peer review yet (no +2)
- Total: 4 (High tier)

### Key Question for Our Stack
**Can trigonometric scoring operate on Hadamard-rotated, q4_0-quantized K vectors?** The scoring uses ||k_f|| (key norms per frequency band) as an online signal. Hadamard rotation preserves norms (orthogonal transform). q4_0 quantization introduces norm error. The interaction is: Hadamard preserves → q4_0 degrades → net effect unknown. This is the #1 question for our stack.

---

## intake-285: In-Place TTT — ASSESSMENT HOLDS

### Initial Assessment
novelty=medium, relevance=low, credibility=5, verdict=not_applicable

### Revised Assessment
No changes. Assessment confirmed.

### Key Details

- **Mechanism**: Modifies W_down (MLP final projection) during inference via chunk-wise gradient updates. The update rule is W_down^(i+1) = W_down^(i) + η·V̂^T·Z, using a 1D conv to generate NTP-aligned targets from future token embeddings.
- **ICLR 2026 confirmed**: Peer-reviewed, Tianle Cai co-author (known for TTT line).
- **Results are modest**: +4.4% on RULER at 64K (Qwen3-4B), +2.1% (LLaMA-3.1-8B). Orthogonal to YaRN (can stack for +1.2% additional).
- **Numerical stability concern**: Requires clipping mechanism (τ=1e-5 Frobenius norm threshold) to prevent unbounded weight growth. Fast weights reset at document boundaries.

### Why Not Applicable (Confirmed)

1. **Fundamentally incompatible with GGUF serving**: GGUF models have fixed, quantized weights. In-Place TTT requires mutable FP32/FP16 W_down matrices updated at inference time.
2. **No quantization discussion**: Paper doesn't address INT8/FP8/GGUF compatibility at all.
3. **Memory overhead undisclosed**: Storage of W_down updates (d_model × d_ff per layer) adds memory pressure — exactly the opposite direction from our KV cache compression work.
4. **The "drop-in" claim is misleading**: For any serving framework that assumes immutable weights (llama.cpp, vLLM with GGUF, TensorRT-LLM), this is NOT a drop-in.

### One Redeeming Insight
The chunk-wise update mechanism (512-1024 tokens) is compatible with context parallelism. If a future model is trained with In-Place TTT and released as a GGUF, the TTT layers would need to be emulated somehow — but this is speculative. **No action needed.**

---

## intake-286: RLSD — ASSESSMENT REVISED

### Initial Assessment
novelty=low, relevance=medium, credibility=2, verdict=worth_investigating

### Revised Assessment
**novelty=medium** (↑), relevance=medium, **credibility=3** (↑), verdict=worth_investigating

### Why Novelty Upgraded: low → medium

The initial assessment treated RLSD as "yet another self-distillation paper." The deep dive reveals a genuinely novel theoretical framework:

1. **Theorem 1 (KL Decomposition)**: Proves OPSD's objective decomposes as ℒ_OPSD = ℒ* + I(Y_t; R | X, Y<t), where the mutual information gap is θ-independent and irreducible. This is a **new result** that explains why OPSDC (intake-110) and all OPSD variants eventually collapse.

2. **Impossibility Trilemma (Theorem 3)**: Under shared parameters, three properties cannot coexist: (a) objective stability, (b) sustained improvement, (c) leakage-free training. This is a fundamental impossibility result, not incremental.

3. **Bayesian Evidence Ratio (Theorem 4)**: Shows the token-level weight w_t = P_T/P_S equals a sequential Bayesian belief update about the reference answer. This connects self-distillation to Bayesian inference in a non-obvious way.

The direction-magnitude decomposition (use RLVR for direction, self-distillation for magnitude) is a principled fix that follows directly from the theory, not an ad-hoc combination.

### Results in Context

- Tested on Qwen3-VL-8B (multimodal) — single model, limited scope
- +2.32% over GRPO, +4.69% over base on VL benchmarks — meaningful but not dramatic
- 32x NVIDIA H200 (4 nodes × 8 GPUs) — massive compute, completely out of our reach
- No inference-time efficiency metrics — doesn't tell us if models produce shorter/better reasoning traces

### Credibility Upgrade: 2 → 3
- Published within 12 months (+1)
- Strong theoretical framework with formal proofs (+1)
- CAS + JD.COM + Microsoft Research authors — decent authority (+1)
- Limited empirical scope (single model/domain) — no additional corroboration
- No peer review yet
- Total: 3 (Medium tier)

### What's Extractable for Our Stack

1. **OPSD instability is now theoretically understood**: If we ever evaluate OPSDC-distilled checkpoints (from intake-110), we should expect models distilled for >20 steps to show degradation. Look for checkpoints that used early stopping.
2. **The direction/magnitude decomposition could explain checkpoint quality differences**: Some GGUF reasoning models may have been trained with better credit assignment (RLSD-like) vs. uniform advantage (GRPO). No way to detect this from weights alone, but it explains variance.
3. **Still training-only**: No inference-time implications confirmed.

---

## intake-287: LongFlow — ASSESSMENT REVISED

### Initial Assessment
novelty=medium, relevance=high, credibility=2, verdict=worth_investigating

### Revised Assessment
novelty=medium, **relevance=medium** (↓), credibility=2, verdict=worth_investigating

### The 11.8x vs TriAttention's 2.5x: Apples to Oranges

This is the most important correction. The numbers are NOT comparable:
- **LongFlow's 11.8x**: System-level throughput vs. vanilla (full KV, no compression). Measured with custom Triton kernel fusing attention+eviction.
- **TriAttention's 2.5x**: Throughput at the accuracy-matched operating point (where both achieve same accuracy as Full Attention on AIME25).

At comparable compression ratios (80% compression = 3.2K budget from 16K), LongFlow's accuracy degradation is ~0.08-1.3% — but this is on DIFFERENT benchmarks (GSM8K, MATH, etc.) than TriAttention's AIME focus.

**Direct comparison impossible**: LongFlow doesn't test against TriAttention, and their benchmark suites only partially overlap.

### Methodological Strengths

1. **Zero-overhead scoring**: ||α·v||₁ is literally an intermediate result of standard attention computation. No additional computation needed — the metric falls out for free.
2. **Custom kernel is impressive**: 47ms → 8ms attention latency on Qwen3-8B (batch=128, seq=3200). The fused approach (FlashAttention + scoring + eviction in one kernel) is architecturally cleaner than TriAttention's plugin.
3. **Static memory scheme**: No fragmentation from dynamic eviction — important for production deployment.

### Relevance Downgrade: high → medium

**Critical limitation for our stack**: The paper explicitly states scoring is "most reliable when consecutive decoding queries are similar" and degrades under "abrupt distribution shifts (topic switches, tool-use interleaving, highly stochastic decoding)."

Our orchestrator pipeline involves:
- Multi-turn tool-use conversations
- Mixed reasoning/retrieval/coding tasks
- Topic switching between orchestrator roles

This failure mode directly impacts our use case. TriAttention's trigonometric scoring (based on stable pre-RoPE centers) is inherently more robust to query distribution shifts because it doesn't depend on query similarity.

### Other Concerns
- GQA not discussed — gap for our GQA models
- No quantization interaction — same gap as TriAttention
- Triton kernel = Python/CUDA — same portability issue as TriAttention for llama.cpp

---

## intake-288: Expected Attention — ASSESSMENT REVISED

### Initial Assessment
novelty=medium, relevance=medium, credibility=3, verdict=worth_investigating

### Revised Assessment
novelty=medium, **relevance=high** (↑), **credibility=4** (↑), verdict=worth_investigating

### Why Relevance Upgraded: medium → high

Three factors make Expected Attention more practically useful than initially assessed:

1. **Flash Attention compatible**: SnapKV and H2O require materializing the full attention matrix — incompatible with Flash Attention. Expected Attention works without materialization. This is critical for any production deployment.

2. **Explicit quantization orthogonality**: The paper explicitly discusses combining with KV quantization (KIVI, KVQuant, NQKV). No other paper in this cluster addresses this. Quote: "quantization methods orthogonal to Expected Attention... making it possible to integrate them." This directly validates our Hadamard + selection stacking hypothesis.

3. **GQA/MQA explicitly supported and tested**: Validated on Qwen3-8B (GQA), Gemma3-12B (GQA). Per-head adaptive compression is built in — "allowing more important heads to retain more KV pairs."

4. **KVPress library**: 20+ methods standardized with public HuggingFace leaderboard. Even if we don't use Expected Attention itself, KVPress is the right benchmarking tool for evaluating all KV selection approaches.

### Results Deep Dive

The numbers are strong — especially on prefill (which TriAttention doesn't focus on):

| Task | Expected Attention | SnapKV | TOVA | Gap |
|------|-------------------|--------|------|-----|
| RULER 4K (Qwen3-8B, 50%) | **94.7** | 55.7 | 77.6 | +39pp vs SnapKV |
| RULER 16K (Qwen3-8B, 50%) | **92.7** | 62.8 | 76.2 | +29.9pp vs SnapKV |
| MATH-500 12x compress (Qwen-R1-7B) | **0.49** | — | — | — |

On decode (reasoning): At 12x compression, MATH-500 accuracy is 0.49 (vs 0.55 at 2x). Graceful degradation.

### Methodological Concern

The Gaussian assumption (h ~ N(μ, Σ)) is approximate. The paper acknowledges heavy-tailed outliers exist. For models with outlier-heavy activation patterns (some LLaMA variants), the closed-form approximation may degrade. However, they tested on LLaMA-3.1-8B successfully, suggesting practical robustness.

### Credibility Upgrade: 3 → 4
- Published Oct 2025 — within 12 months (+1)
- KVPress library released with public leaderboard — independent corroboration (+1)
- Tested on 6 models across 3 architectures — breadth (+1)
- CC BY 4.0 license (+0)
- No formal peer review but library has community adoption (+1)
- Total: 4 (High tier)

### Positioning vs TriAttention

| Dimension | TriAttention | Expected Attention |
|-----------|-------------|-------------------|
| Scoring basis | Pre-RoPE trigonometric centers | Gaussian MGF closed-form |
| Flash Attention | Not discussed | Compatible |
| Quantization | Not discussed | Explicitly orthogonal |
| GQA | Supported | Supported + per-head adaptive |
| Prefill | Not focused | Excellent (94.7% RULER) |
| Decode | Primary focus (AIME) | Good (MATH-500) |
| Calibration | Offline Q/K centers | Online buffer (128 tokens) |
| Overhead | Unknown (pruning every 128 tok) | Minimal (O(n·d²)) |
| Implementation | vLLM plugin | PyTorch hooks (not optimized) |
| Library | Standalone | KVPress (20+ methods) |

**Assessment**: For our stack, Expected Attention may be MORE practically useful than TriAttention due to Flash Attention compatibility and explicit quantization discussion, despite TriAttention having stronger decode-phase results on mathematical reasoning.

---

## Revised Recommended Actions

### Priority Reorder Based on Deep Dive

1. **[HIGH] Evaluate KVPress library on our models** (was #3, now #1)
   - KVPress includes 20+ methods with standardized benchmarking
   - Can evaluate TriAttention, Expected Attention, SnapKV, H2O, etc. in one framework
   - Directly tests on Qwen-series models we use
   - Expected Attention's explicit quantization orthogonality means we can test selection + Hadamard stacking immediately in Python before any llama.cpp port

2. **[HIGH] Validate Q/K concentration on our models** (unchanged)
   - Run TriAttention's calibration on Qwen2.5-7B
   - Verify R ≈ 0.98 holds for our specific model
   - Test whether Hadamard rotation preserves the concentration property (it should — orthogonal transform)

3. **[HIGH] Test selection + quantization stacking** (new action)
   - Use KVPress framework to evaluate: Expected Attention (50% selection) + KV quantization
   - Measure combined memory reduction and quality impact
   - This directly validates the ~21x combined hypothesis from the handoff stub

4. **[MEDIUM] Assess llama.cpp portability for Expected Attention** (refined from TriAttention-only)
   - Expected Attention may be easier to port: Gaussian statistics + softmax, no trigonometric machinery
   - Flash Attention compatible = can work with llama.cpp's FA path
   - Per-head adaptive compression maps to llama.cpp's head structure

5. **[LOW] Monitor LongFlow** (downgraded)
   - Topic-switch failure mode is a concern for our orchestrator workloads
   - 11.8x headline is not comparable to TriAttention's 2.5x — different measurement basis
   - Still interesting for pure-generation workloads but less relevant to our mixed pipeline

6. **[SKIP] In-Place TTT** — confirmed not applicable
7. **[MONITOR] RLSD** — theoretical insights valuable; watch for RLSD-trained GGUF checkpoints
