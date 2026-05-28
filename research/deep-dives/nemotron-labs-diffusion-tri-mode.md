# Deep Dive: Nemotron-Labs-Diffusion — Tri-Mode Unified AR + Diffusion + Self-Speculation

**Date**: 2026-05-20
**Intake**: intake-576 (tech report PDF — primary), intake-577 (NVIDIA research landing), intake-578 (HF collection)
**Paper**: "Nemotron-Labs-Diffusion: A Tri-Mode Language Model Unifying Autoregressive, Diffusion, and Self-Speculation Decoding" (NVIDIA, 2026-05-19, no arXiv ID — tech report only)
**Authors**: Yonggan Fu et al. (26 authors; NVIDIA core research — Pavlo Molchanov, Jan Kautz, Song Han, Enze Xie; interns from Georgia Tech, University of Hong Kong, MIT)
**Question**: Is the unified-model self-speculation paradigm a viable porting target for the EPYC CPU stack, or does it stay GPU-gated like DFlash?

## Executive Summary

**Tri-mode = one weight set, three decoding strategies, switched at runtime by attention pattern.** AR mode uses causal mask; diffusion mode uses block-wise bidirectional within block + causal across blocks; self-speculation runs diffusion-as-drafter then AR-as-verifier on the *same model* sharing the same KV cache.

**Key delta vs DFlash / DART / Eagle3 / MTP**: the prior work all uses a *separate drafter model* trained or fine-tuned to match a *frozen target*. Nemotron-Diff trains the drafter and verifier as ONE model — no drafter-target alignment problem, no embed/LM-head cost per drafting step, no cross-precision quantization noise (the same Q4_K_M weights would serve both roles).

**Backbone is Ministral3-8B** — a dense LLaMA-family transformer. **NO Delta-Net, NO Mamba, NO SSM**. This is *fundamentally different* from the Qwen3.5 hybrid that killed our DFlash CPU port via the recurrent-verification wall. **The architectural prerequisites for a CPU port are favorable.**

**Reported gains on GPU** (8B Instruct, FP8, batch=1, GB200, paper Fig. 9 / Tab. 10):
- AR baseline: 256 tok/s
- Linear self-speculation (default): **851 tok/s, 3.32× over AR**
- Linear self-speculation (custom CUDA kernels): **1015 tok/s, 3.97× over AR**
- Eagle3 (Qwen3-8B baseline): 354 tok/s, 1.38×
- Diffusion-only: 389 tok/s, 1.52×
- SOL ceiling: 1471 tok/s, 5.75×
- **Acceptance length: 5.46 native / 6.82 LoRA-tuned vs Eagle3 2.75 / Qwen3-9B-MTP 4.24** (avg over 11 SPEED-Bench categories)

**Quality is NOT degraded** — 8B AR mode delivers +0.86% average accuracy over Qwen3-8B AR across 10 benchmarks (GPQA, IFEval, MMLU, HumanEval, MBPP, LCB-CPP, Math500, GSM8K, AIME24, AIME25). Linear SS mode is +0.06% vs Qwen3-8B AR. The diffusion objective is essentially free at AR-mode test time.

**Verdict on CPU portability** (this deep dive's central question): **MUCH more portable than DFlash**, but still 11–20 days of llama.cpp engineering to fully realize, gated on Ministral3 architecture support in our fork. The blocker is not architectural (it's not a hybrid SSM) — it's the attention-pattern switching, the confidence-based sampling loop, and the per-block KV refresh.

---

## 1. What the Architecture Actually Is

### 1.1 Backbone

- **Initialization**: official Ministral3-8B base model (arxiv:2601.08584, NVIDIA 2026). Family: dense decoder-only transformer, LLaMA-family conventions. Vocabulary and embedding dims unchanged through Nemotron-Diff training.
- **Family scale**: 3B / 8B / 14B (Base + Instruct) plus VLM-8B (vision encoder + 2-layer MLP projector w/ 2×2 patch merging, initialized from Ministral3-8B-Instruct-2512 + Nemotron-Labs-Diffusion-8B-Instruct backbone).
- **Training compute**: 256× H100 GPUs. Stage 1 = 1T tokens pure AR continuous pretraining. Stage 2 = 300B tokens joint AR+diffusion (α=0.3). SFT = 45B tokens, joint objective preserved, 16K sequence length, batch size 256.

**Implication for us**: the backbone is *not* a novel architecture. If llama.cpp already supports Ministral3, the model loads with at most minor config-level changes. The trainable surface (LoRA-augmented o_proj, ~36M params, 0.4% of backbone) is a standard adapter pattern.

### 1.2 Training Objective (Joint AR + Diffusion)

The model is trained on a weighted combination of two losses:

```
ℒ(θ) = ℒ_AR(θ) + α · ℒ_diff(θ),     α = 0.3 (empirical sweet spot)
```

Where:

- **AR loss** ℒ_AR: standard left-to-right next-token NLL (causal factorization), eq. (1) in paper.
- **Diffusion loss** ℒ_diff: block-wise masked denoising — partition sequence into B blocks, sample a noise level t ∈ [0,1], corrupt one block's tokens via forward noising q(·|x_b), and minimize per-token log-likelihood with a 1/t reweighting that aligns with the standard masked-diffusion formulation (eq. 2). Conditioning is on clean prefix blocks and the corrupted current block.

**Why α=0.3** (from Tab. 2): both AR-mode and diffusion-mode accuracy peak at α=0.3. Below that (α=0.1), diffusion mode is undertrained. Above (α≥0.5), AR mode degrades. The two objectives are *complementary, not competing* — they rise and fall together across [0.1, 0.5] with no zero-sum trade.

**Two-stage training rationale**: pure AR pretraining first (Stage 1, 1T tokens) anchors left-to-right linguistic priors; joint objective second (Stage 2, 300B tokens). Ablation (Tab. 1, 25B-token CPT from Ministral3-8B):

| Technique (cumulative) | Avg accuracy on coding+math |
|---|---|
| Block-wise attention only (baseline) | 54.23% |
| + Global loss averaging | 56.35% (+2.12) |
| + DP-rank varying masking ratios | 57.06% (+0.71) |
| + Two-stage training (better AR init) | 62.80% (+5.74) |
| + AR loss (the unified objective) | **70.28% (+7.48)** |

**The single biggest gain (+7.48%) comes from preserving the AR loss in the unified training** — confirming that the joint objective is load-bearing, not optional.

### 1.3 Attention Pattern (the architectural switch)

Training uses a **dual-stream input**: noisy stream concatenated with clean stream of the same sequence, fed through a structured attention pattern (Fig. 3 of paper). Four mask regions:

| Region | Mask | Purpose |
|---|---|---|
| Noisy → Noisy | Bidirectional within block, causal across blocks | Standard block-diffusion training |
| Noisy → Clean | Each denoising block b attends to clean prefix blocks x_<b | Clean-context conditioning during denoising |
| Clean → Clean | **Strictly causal** | Enables AR loss in same forward pass — **key novelty vs prior block-diffusion** |
| Clean → Noisy | Masked out | Prevents label leakage |

The strictly-causal clean stream is the contribution that lets both losses share one forward/backward pass. Reference [14] (Set Block Decoding, Meta FAIR, arxiv:2509.04185) is the immediate prior art with joint training; Nemotron-Diff differs in (a) tri-mode inference (esp. self-spec), (b) full model family, (c) SOL analysis.

**At inference time the attention pattern is what selects the mode** — there is no separate model for each mode. The same parameter set serves all three.

---

## 2. The Three Decoding Modes (Algorithms)

### 2.1 Mode 1 — AR Decoding

Standard left-to-right sampling with causal attention: x_i ~ p_θ(· | x_<i). No different from any LLaMA-family model. Preferred for high-concurrency cloud serving where compute (not memory bandwidth) is the bottleneck.

**EPYC status**: zero new infrastructure required. The Nemotron-Diff weights would behave like any Ministral3-8B GGUF in AR mode.

### 2.2 Mode 2 — Block-Wise Diffusion Denoising

```
Initialize: for current block of length B, fill all positions with [MASK]
While block has masked positions:
    1. Run forward pass — model outputs per-position softmax over vocab
    2. Confidence-based commit: for each masked position, if top-1 prob > threshold (default 0.9 per HF model card), commit argmax to that position
    3. (Optional) Trained sampler commits more positions per step (see §2.4)
When block is fully unmasked:
    KV cache for that block is refreshed (clean tokens now)
    Decoding proceeds to next block
```

**Parameters from HF model card 8B**:
- `block_length=32` default
- `threshold=0.9` (confidence cutoff)
- `eos_token_id` triggers stop

**Reported TPF for diffusion-only mode** (8B Instruct, Tab. 5): **2.57× TPF over Qwen3-8B AR while matching accuracy** (63.18 vs 62.75 avg over 10 benchmarks). Note this is *real TPF*, not acceptance rate — diffusion mode commits multiple positions per single forward pass, so real TPF ≈ acceptance rate (no draft+verify cycle cost).

**Per-block KV refresh** is the only KV-cache twist vs standard AR decode. After a block is fully unmasked, the noisy mask-tokens are replaced with clean tokens and the cache for that block is recomputed before the next block begins. Cross-block attention remains causal (cached from prior verified blocks).

### 2.3 Mode 3a — Linear Self-Speculation (the production mode)

This is the headline mode. Algorithm:

```
Let [x_1, ..., x_n] be the verified prefix.
Let k = speculative width (block_length in HF API).

DRAFT PASS (diffusion):
    Append k mask tokens to verified prefix:
        input = [x_1, ..., x_n, m_1, ..., m_k]
    Forward pass with diffusion attention pattern, all k positions denoised in parallel.
    Output: draft tokens [x̂_{n+1}, ..., x̂_{n+k}].

VERIFY PASS (AR):
    Forward pass with causal attention over [x̂_{n+1}, ..., x̂_{n+k}],
    reusing the prefix KV cache.
    Output: AR predictions [x^AR_{n+1}, ..., x^AR_{n+k}].
    Accept longest contiguous prefix where x^AR_{n+j} == x̂_{n+j}.
    The AR prediction at first rejection position is bonus +1 verified token.

COMMIT: each cycle produces between 1 and k+1 tokens.
```

**KV cache: shared between draft and verify** — the prefix KV is computed once and reused for both passes. This is the key efficiency contributor and is non-trivial to implement (the drafter and verifier are running on the *same* set of weights with *different* attention masks over the *same* KV buffer).

**LoRA enhancement** (default in production mode):
- Apply LoRA only to o_proj of attention layers
- Rank 128, α=512 → ~36M trainable params (0.4% of 8B backbone)
- LoRA trained with LK-hybrid distribution-matching loss (eq. 6) + token-level cross-entropy on accepted-prefix + first-rejected position
- Training loss is masked: positions BEYOND first rejection contribute neither to numerator nor denominator (they'd train on counterfactual continuations the deployed loop never observes)
- 90% of training samples use sampled drafter (T=1.0); 10% greedy
- **Empirical effect** (Tab. 6): 14.4% / **32.5%** / 27.6% relative TPF gain at 3B / 8B / 14B scales

**Reported throughput (Tab. 6, 8B Instruct, 10 benchmarks):**

| Setting | Avg TPF |
|---|---|
| Linear SS w/o LoRA | 4.52× |
| Linear SS w/ LoRA | **5.99×** |
| (Per-benchmark range w/ LoRA) | AIME24: 7.44×, Math500: 7.36×, GPQA: 6.64×, IFEval: 5.52×, HumanEval: 5.82× |

**Accuracy is essentially unchanged**: Linear SS avg 62.81% vs AR mode 63.61% (–0.80% — kernel/numerics drift, not algorithmic).

### 2.4 Trained Sampler (for diffusion mode only)

Lightweight 4-layer transformer, hidden dim 384, ~4.8M params (0.06% of backbone). Per-position 144-dim feature: PCA-compressed semantic embeddings of top-3 predictions + output-distribution statistics (top-1 prob, margin, top-3 mass, entropy). Per-position sigmoid head predicts whether the position's current top-1 will match the eventual greedy-converged token.

- Trained on ~20M denoising trajectories from Nemotron-Labs-Diffusion-8B on Nemotron-Post-Training-Dataset-v2 (math/code/STEM/chat subsets) at block lengths B ∈ {8, 32}
- Per-position binary cross-entropy on masked positions
- Cross-position attention is essential — MLP-only ablation drops AUC by 10 percentage points

**Effect** (Fig. 8): shifts the entire diffusion-mode accuracy–TPF Pareto frontier upward. At equal accuracy, 1.3× TPF. At equal TPF, +10.6% accuracy.

### 2.5 Mode 3b — Quadratic Self-Speculation (variant)

Single forward pass that interleaves verification of prior drafts AND drafting of new tokens via a structured attention mask. Cost is O(k²) in attention but **only one forward pass per cycle** instead of two.

- Each iteration consistently produces k speculative tokens even if verification fails early
- Optional **AR-diffusion ensemble verifier**: `p_ens = λ·p_AR + (1-λ)·p_diff` — uses the diffusion prediction at the first inserted mask after each speculative token as a complementary verifier signal
- Tab. 5: TPF 6.38× (8B Instruct), highest of any mode

**Why not default?** FlexAttention with the dedicated quadratic attention mask has less-optimized kernels, so wall-clock throughput in Fig. 1(b) is BELOW linear SS despite higher tokens-per-forward count. With better kernels this would dominate.

**EPYC implication**: irrelevant — we'd never write the FlexAttention kernel on CPU. Linear SS is the production target for any port.

---

## 3. Headline Numbers (Verbatim)

### 3.1 Quality vs SOTA AR baselines (8B Instruct, Tab. 5)

| Model | GPQA | IFEval | MMLU | HumanEval | MBPP | LCB-CPP | Math500 | GSM8K | AIME24 | AIME25 | **Avg** |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Qwen2.5-7B | 37.12 | 74.58 | 74.86 | 77.44 | 81.55 | 12.33 | 75.10 | 91.89 | 13.75 | 6.88 | 54.55 |
| Qwen3-8B | 49.24 | 87.38 | 76.66 | 81.71 | 81.88 | 21.09 | 84.80 | 92.42 | 30.21 | 22.08 | **62.75** |
| Ministral3-8B-Instruct-2512 | 42.87 | 64.31 | 73.90 | 71.04 | 78.97 | 20.76 | 83.60 | 92.42 | 27.71 | 24.58 | 58.02 |
| **NLD-8B AR** | 44.44 | 68.65 | 79.85 | 80.49 | 85.19 | 28.85 | 88.00 | 94.01 | 33.33 | 33.33 | **63.61** |
| **NLD-8B Diff** | 43.94 | 68.32 | 78.71 | 78.66 | 83.86 | 26.16 | 85.80 | 93.03 | 46.67 | 26.67 | 63.18 |
| **NLD-8B Linear SS** | 40.40 | 69.13 | 79.01 | 81.71 | 84.92 | 24.89 | 87.60 | 93.78 | 36.67 | 30.00 | 62.81 |
| **NLD-8B Quad SS** | 44.30 | 71.00 | 79.95 | 79.27 | 85.19 | 27.70 | 88.80 | 94.16 | 33.33 | 36.67 | **64.04** |
| LLaDA-8B Instruct (Diff) | 33.30 | 59.90 | 65.50 | 49.40 | 41.00 | 4.19 | 39.20 | 79.91 | 0.00 | 0.00 | 37.24 |
| Dream-7B Instruct (Diff) | 33.00 | 62.50 | 67.00 | 55.50 | 58.80 | 1.25 | 43.00 | 81.00 | 0.00 | 3.33 | 40.54 |
| SDAR-8B Chat (Diff) | 40.20 | 61.40 | 78.60 | 78.70 | 72.00 | 13.44 | 78.60 | 91.30 | 16.67 | 10.00 | 54.09 |

**Headline reads:**
- AR mode at 63.61% **beats Qwen3-8B AR (+0.86%)**, beats Ministral3-8B-Instruct-2512 (+5.59%) — i.e., the joint training *improves* the AR mode vs the same model trained AR-only.
- Linear SS at 62.81% is +0.06% above Qwen3-8B AR with **~6× the TPF**.
- Other diffusion LMs (LLaDA, Dream, SDAR) are 9–26 points below the AR baselines. **Nemotron-Diff is the first diffusion LM that achieves AR-class accuracy** — a big deal for the diffusion-LM research arc.

### 3.2 Real-Device Speedups (Fig. 9, 8B Instruct, batch=1)

| GPU | Quant | AR | Linear SS | Speedup | Diff | Eagle3 | SOL |
|---|---|---|---|---|---|---|---|
| **GB200** | FP8 | 256 tok/s | **851 tok/s** | **3.32×** | 389 (1.52×) | 354 (1.38×) | 1471 (5.75×) |
| GB200 (custom CUDA) | FP8 | – | **1015 tok/s** | **3.97×** | – | – | – |
| **RTX Pro 6000** | FP8 | 80 tok/s | **277 tok/s** | **3.46×** | 137 (1.71×) | 121 (1.51×) | 567 (7.09×) |
| RTX Pro 6000 | INT4-AWQ-Marlin | 80 | **525 tok/s** | **6.56×** | 204 (2.55×) | 211 (2.64×) | 989 (12.36×) |
| **DGX Spark** | FP8 | 24.7 | **77.5 tok/s** | **3.14×** | 36.5 (1.48×) | – | 176.2 (7.13×) |
| **DGX Spark** | INT4-AWQ-Marlin | 41.8 | **112.5 tok/s** | **2.69×** (vs INT4 AR) | 54.1 (1.30×) | 43.2 (1.03×) | 223.1 (5.34×) |

Notes:
- DGX Spark INT4 AR = 41.8 tok/s. Linear SS INT4 = 112.5 tok/s. **The 4.56× quoted in the HF model card uses FP8 AR as the denominator (24.7 → 112.5).** The honest INT4-vs-INT4 number is 2.69×.
- SOL ceiling is 7–12× over AR depending on hardware/quant — current linear SS leaves substantial room.
- INT4-AWQ-Marlin on DGX Spark suggests AWQ-style INT4 weight quant is supported in the inference path. Not the same as Q4_K_M but adjacent.

### 3.3 Acceptance Length vs MTP / Eagle3 (Tab. 10, SPEED-Bench, k=31)

| Category | NLD Native | NLD LoRA | Eagle3 | MTP (Qwen3-9B) |
|---|---|---|---|---|
| coding | 6.61 | **8.57** | 3.14 | 5.97 |
| math | 6.24 | **8.14** | 2.79 | 4.80 |
| reasoning | 6.18 | **7.99** | 3.40 | 3.68 |
| multilingual | 7.96 | **10.06** | 1.91 | 4.47 |
| humanities | 5.01 | 6.31 | 3.12 | 3.76 |
| qa | 4.01 | 4.65 | 2.63 | 3.50 |
| rag | 5.07 | 6.15 | 3.06 | 4.75 |
| roleplay | 4.66 | 5.54 | 2.10 | 2.32 |
| stem | 5.55 | 7.02 | 2.92 | 4.45 |
| summarization | 4.47 | 5.48 | 2.66 | 3.69 |
| writing | 4.28 | 5.07 | 2.81 | 3.21 |
| **Average** | **5.46** | **6.82** | **2.75** | **4.24** |
| 4-cat avg (math/code/reason/multilingual) | 6.75 | **8.69** | 2.81 | 4.73 |

**The Eagle3 gap is 2.5×** on average and **3× on the four diffusion-friendly categories**. The MTP gap is 1.6×. This is the load-bearing empirical claim that "self-speculation outperforms MTP methods" — it is corroborated by the per-category data.

### 3.4 TPF Scaling Across Model Sizes (Tab. 6 + Tab. 7)

| Scale | NLD w/o LoRA TPF | NLD w/ LoRA TPF | NLD AR acc | Best AR baseline | NLD acc Δ |
|---|---|---|---|---|---|
| 3B | 3.81× | 4.36× | 55.50 | Qwen3-4B: 53.23 | **+2.27** |
| 8B | 4.52× | **5.99×** | 63.61 | Qwen3-8B: 62.75 | **+0.86** |
| 14B | 4.67× | 5.96× | 67.46 | Qwen3-14B: 65.17 | **+2.29** |

**Note the 14B w/ LoRA is barely above 8B — the TPF gains plateau between 8B and 14B.** Likely the 8B is the sweet spot for our hardware once context length, KV size, and per-decode latency all enter the equation.

### 3.5 VLM (Tab. 9, 8B vision-language)

| Mode | AI2D | ChartQA | DocVQA | MMMU | MMMU-Pro-10c | MMMU-Pro-V | MathVista | RealWorldQA | TPF (avg / >100 tok / >200 tok) | Acc |
|---|---|---|---|---|---|---|---|---|---|---|
| LLaDA-V-8B (Diff) | 77.8 | 78.3 | 83.9 | 48.6 | 35.2 | 18.6 | 59.7 | 63.2 | 1.00 | 58.2 |
| NLD-VLM-8B AR | 75.0 | 81.3 | 89.2 | 50.3 | 32.6 | 24.3 | 60.4 | 62.6 | 1.00 | 59.5 |
| NLD-VLM-8B Diff | 74.7 | 76.6 | 88.3 | 50.4 | 31.7 | 22.2 | 58.5 | 60.3 | 2.46 / 2.80 / 3.15 | 57.9 |
| NLD-VLM-8B Linear SS | 74.9 | 81.2 | 89.3 | 50.0 | 32.8 | 24.1 | 60.7 | 62.4 | 3.63 / 6.03 / **7.45** | 59.4 |

**Long-response gain is much larger** — 7.45× TPF on responses >200 tokens. Confirms that the speedup is concentrated in tasks with extended generation (i.e., reasoning, dense captioning, structured output) and is closer to 1× on short factual responses where there are fewer tokens to parallelize over.

The VLM uses **asymmetric dual-stream training** to handle high vision-token counts without paying FLOPs in the noisy half on positions that are never masked (vision tokens) — see eq. (10) in paper.

---

## 4. Speed-of-Light (SOL) Analysis — the ceiling

The paper introduces an **oracle SOL analysis** to compute the maximum acceptance rate / TPF achievable by the diffusion-only mode under an ideal sampler:

1. Define oracle target via **serial denoising** — at each step, commit the masked position with the single highest probability (across positions and vocabulary). B forward passes yield the target sequence t the diffusion model would converge to.
2. Compute **greedy parallel acceptance**: at each iteration, commit *every* position whose top-1 matches the target. If none matches, commit the highest-confidence single position as fallback.
3. Compute **recursive dynamic compaction** (the "true SOL"): rank matched positions by confidence, search for the largest prefix whose commit is *safe* (continuing decoding on remaining positions still arrives at t). Safety is checked recursively, budget 5000 forward passes per block.

**Results** (Tab. 4, 713 SPEED-Bench samples, 11 categories, 8B Instruct):

| Block length | SOL acceptance | Benchmark accuracy |
|---|---|---|
| BL=4 | 2.89× | 64.04% |
| BL=8 | 4.17× | 65.43% |
| BL=16 | 5.68× | 63.18% |
| BL=32 | **7.60×** | 61.81% |

Per-category at BL=32: roleplay 3.49×, summarization 6.02×, writing 6.13×, humanities 6.93×, reasoning 7.22×, rag 7.32×, stem 8.01×, math 9.30×, coding 10.24×, multilingual 11.26×.

**Diffusion SOL real-TPF vs Linear SS real-TPF**: 6.02× vs 3.41× = **76.5% improvement** for diffusion-only over linear SS. Two causes:
1. Diffusion does 1 forward per acceptance step; linear SS does 2 (draft + verify)
2. Linear SS only commits a contiguous prefix; diffusion can commit *any subset* of masked positions

**Implication**: there is meaningful headroom beyond the current 5.99× linear-SS TPF. Closing the gap requires either (a) a better sampler that approaches the oracle, or (b) non-prefix verification (e.g., diffusion-mode verifier that validates non-contiguous subsets).

The paper's first-of-four future directions explicitly calls for closing this gap: "Closing the gap between practical diffusion decoding and its SOL upper bound."

---

## 5. Comparison Against Existing Project Intake (the EPYC lineage)

| Approach | Intake | Drafter–target relationship | KV sharing | CPU port feasibility | Acceptance length | Notes |
|---|---|---|---|---|---|---|
| **Nemotron-Labs-Diffusion** | **intake-576** (this) | **SAME model — attention-pattern switch** | **YES — shared KV** | **HIGH** (Ministral3 backbone, dense) | **5.46 / 6.82 LoRA** | Tri-mode, joint AR+diffusion training |
| DFlash | intake-158 | Separate drafter (0.5B for Qwen3.5-35B, 1B for Qwen3-8B), trained jointly | NO (target features piped via FC) | LOW (per-layer hidden state extraction needed) | 6.49 (τ) | C++ port verified correct; killed by Q4_K_M acceptance collapse (27% per-token) + 75% Delta Net recurrent verify wall on Qwen3.5 hybrid |
| DART | intake-159 | Separate 1-layer drafter + 100GB n-gram trie | NO | LOW–MEDIUM | 3.67–4.08 | GPU-only, less directly relevant than DFlash |
| Lucebox Hub DFlash GGUF port | intake-447, intake-455 | Separate drafter | NO | EXISTS on RTX 3090 (GGUF Q4_K_M) | (downstream of DFlash) | First successful llama.cpp port of block-diffusion drafting — establishes that the GGUF path is real, just hard |
| Gemma 4 MTP drafter | intake-527, handoff `gemma4-mtp-drafter-evaluation.md` | Separate drafter (Gemma4Assistant, 4 layers ~500M for 31B) | Partial (LM head shared) | MEDIUM (ik_llama.cpp PR #1744 path exists) | ~3.5× win on dense single-stream | MTP-1 dense models DO win on EPYC: gemma4-26B-A4B + MTP +2.98× pure-CPU; hybrid recurrent collapse only hits Qwen3.5 |
| Eagle3 (Qwen3-8B) | (referenced in many entries; intake-567 ECHO) | Separate ~450M draft head, recursive drafting | Partial | MEDIUM | 2.75 | Vanilla Eagle3 underperforms AR at bs≈128 per ECHO finding |
| MTP-1 on Qwen3.5 hybrid | `completed/mtp-speculative-decoding.md` | Separate MTP head | Partial | DEAD on hybrid (0.56× — Delta Net wall) | 78.5% accept rate | Same recurrent verify wall as DFlash on Qwen3.5 |

**Two structural differences** that make Nemotron-Diff *more* CPU-portable than DFlash:

1. **No cross-precision quantization mismatch.** DFlash on Q4_K_M dropped to 27% per-token acceptance partly because the drafter conditioned on the target's hidden states, and at Q4_K_M precision the hidden states the drafter expects (BF16 distribution shape) drift from what the target actually produces. In Nemotron-Diff, the drafter and verifier ARE THE SAME WEIGHTS at the same precision. Quantization noise affects both equally — there's no drift to align.

2. **No drafter-target architecture mismatch.** DFlash needs per-layer hidden state extraction from the target into a 5-layer drafter, requiring new llama.cpp API (`llama_get_hidden_state`, intermediate tensor preservation through `ggml_graph_compute`). Nemotron-Diff needs only an attention-pattern switch in the same forward graph.

**Two structural challenges** that still gate CPU portability:

1. **Block-wise diffusion attention mask is non-standard.** llama.cpp assumes causal attention. The diffusion path needs bidirectional-within-block + causal-across-blocks. This is similar to the DFlash sparse attention problem (intake-158 deep-dive §5) — option (c) "ignore bidirectional within block" might work as a degraded first port, then upgrade to a proper structured mask. Estimated 5–10 days.

2. **Confidence-based sampling loop with per-block KV refresh.** Each block iterates multiple times (commit some, denoise again) before moving on. The KV cache for the block is rewritten when the block is finalized. Estimated 5–8 days for a clean implementation.

---

## 6. CPU Portability Assessment

### 6.1 What CPU Port Would Require

| Component | Effort | Risk | Status / Precedent |
|---|---|---|---|
| 1. Ministral3-8B backbone GGUF | 0–1 day | Low | Likely already supported via `convert_hf_to_gguf.py` LLaMA path. Verify by attempting conversion on `nvidia/Nemotron-Labs-Diffusion-8B-Base` |
| 2. Causal AR-mode inference | 0 days | None | Standard llama.cpp |
| 3. Block-wise attention mask (bidirectional within block, causal across) | 5–10 days | Medium | Closest precedent: the DFlash block-sparse attention design in `dflash-dart-diffusion-speculation.md` §5. Option (c) "causal-only fallback" is 0 days to try |
| 4. Confidence-based denoising loop (one block at a time) | 5–8 days | Medium | New; no direct precedent in llama.cpp. State machine + per-block KV management |
| 5. Per-block KV cache refresh after denoising | 2–3 days | Medium | Similar to prefix-cache invalidation, but per-block granularity |
| 6. LoRA loading on o_proj | 1–2 days | Low | Standard LoRA path exists; verify rank-128 / α=512 on o_proj works |
| 7. Linear self-speculation orchestration (2 forward passes with shared KV) | 3–5 days | Medium | `common_speculative` provides verify infrastructure; new: same-model role-switch with shared KV |
| 8. Trained sampler integration (4-layer transformer, 4.8M params) | 2–4 days | Low | Tiny aux model; sigmoid head; could load as separate GGUF |
| **Total for a working Linear SS port** | **15–25 days** | | Excludes Quad SS (FlexAttention kernel, irrelevant for CPU) |
| **Total for diffusion-only mode** | **10–15 days** | | Subset — drop items 7 |

**Vs DFlash CPU port (intake-158 deep dive)**: DFlash was 13–20 days projected and concluded NOT VIABLE at 27% per-token acceptance on Q4_K_M. Nemotron-Diff is comparable engineering effort with **fundamentally more favorable portability prerequisites** (same-model, no cross-precision mismatch, no Delta Net recurrent verify wall).

### 6.2 Critical Unknowns Before Committing CPU Engineering

These are the questions that decide whether a port is worth starting:

1. **Does Q4_K_M preserve the diffusion-mode accuracy floor?** All paper numbers are BF16, FP8, or INT4-AWQ-Marlin. DFlash collapsed to 27% acceptance on Q4_K_M. Nemotron-Diff should be more robust (no cross-precision drift), but the diffusion sampler was trained on BF16 confidence-score distributions — Q4_K_M may shift the threshold sweet-spot. **First experiment after backbone conversion**: run AR-mode PPL Q4_K_M vs BF16, then diffusion-mode confidence distribution histogram Q4_K_M vs BF16.

2. **How does block-wise attention perform when bidirectional-within-block is approximated as causal?** If the degraded mask works at all, the diff between "do it right" and "fast first cut" is large (option c = 0 days, option a = 7 days per DFlash precedent). Worth trying first.

3. **Does Ministral3-8B even load in our llama.cpp fork?** Ministral3 is recent (arxiv:2601.08584, NVIDIA 2026). Need to verify in `llama-cpp-fork-rebase.md` or `llama-cpp-kernel-push-rebase.md` whether the architecture is supported. If not, that's the first blocking gate.

4. **What does linear self-speculation give us on EPYC where AR decode is already 192-thread-parallel?** GPU gains are huge because AR mode is bandwidth-bound; multi-token-per-forward eliminates the BW bottleneck. CPU on EPYC at 192t is also bandwidth-bound for decode (per `feedback_cpu_decode_bw_bound`) so the same logic applies — IF the draft+verify cycle reuses cached weight reads. We need a back-of-envelope: how many GB/s does one Linear-SS cycle read, vs an AR cycle? If close to 1× per cycle and 5–6× tokens per cycle, the win replicates. If draft+verify reads weights twice, the win halves.

5. **Does the LoRA adapter survive Q4_K_M quantization?** The LoRA is BF16 ~36M params. Either keep it BF16 (small overhead) or quantize. Need a sanity check.

### 6.3 Honest Acceptance-Loss Forecast (CPU port)

If the port succeeds, expected behavior on EPYC 9655:
- **AR mode**: indistinguishable from a normal Ministral3-8B GGUF Q4_K_M. Likely ~30–40 t/s single-stream based on similar-size models. Quality matches or beats Qwen3-8B (paper data).
- **Linear SS**: optimistic ~3× speedup → ~90–120 t/s if the draft+verify reuses KV correctly. Pessimistic ~1.5× if KV management eats half the win.
- **Diffusion-only mode**: optimistic ~2× speedup → ~60–80 t/s. The confidence-sampling loop has higher per-block latency variance than linear SS.

**Quality on Q4_K_M is the binding gate** — DFlash precedent says CPU quantization can collapse drafter precision. Nemotron-Diff's same-model drafter should be more robust, but until measured, this is a forecast not a fact.

---

## 7. Strategic Read for EPYC

### 7.1 Why this matters even if we don't port immediately

This is the first diffusion-LM release where:
- The diffusion model **matches AR accuracy** (–0.43% to +5.59% across baselines)
- The unified architecture removes drafter-portability friction
- A multi-size family lets us pick the right point on the size/speed curve
- The training recipe is fully described (Stages 1+2, α=0.3, 1T + 300B tokens, joint loss)

That's a meaningful pivot in the diffusion-LM line. Prior diffusion LMs (LLaDA, Dream, SDAR) were accuracy-deficient by 9–26 points; this one isn't.

### 7.2 What to watch over the next 30–90 days

| Signal | Where to look | Decision impact |
|---|---|---|
| Community llama.cpp port attempt | ggml-org/llama.cpp issues + discussions; HF "GGUF" uploads for Nemotron-Labs-Diffusion-8B | If a port appears, evaluate immediately. Saves 15–25 days. |
| Independent reproduction of 5.99× TPF | HF model card discussions; SGLang / vLLM PRs | Confirms or refutes the headline. Single-source for now. |
| AR-mode quality reproduction on standard benches | LM-Eval-Harness leaderboards, OpenCompass | Q1: does NLD-8B AR really beat Qwen3-8B by +0.86% as the paper claims? This is an **8B-class quality datapoint**, not a production-role replacement signal — our current worker_general is gemma4-26B-A4B Q4_K_M MTP (26B MoE, ~4B active params, swapped 2026-05-08 per `project_worker_general_swap_2026_05_08`), so NLD-8B is too small for that role. The relevant role-replacement comparison would be NLD-14B (66.4% avg) vs gemma4-26B-A4B on our 4-benchmark suite, and even that's a smaller-total-param comparison. |
| Ministral3 ecosystem activity | HF mistralai/Ministral3 collection; ik_llama.cpp PRs | The backbone is more important than the diffusion sugar — if Ministral3 becomes a first-class llama.cpp citizen, our port path opens up. |
| DGX Spark acquisition | `project_dgx_spark_target` memory | If we get a Spark, this is a Day-0 evaluation candidate (Spark is one of the three reported hardware targets in the paper). |

### 7.3 What we should NOT do now

- ❌ Do not start a CPU port until (a) Ministral3 architecture support is confirmed in our fork, (b) Q4_K_M Ministral3-8B AR-mode PPL is healthy, (c) one of the four "critical unknowns" in §6.2 returns a hard No.
- ❌ Do not flag the NVIDIA Nemotron Open Model License as a project blocker (per `feedback_license_not_a_blocker`).
- ❌ Do not generalize the "diffusion-LM is viable" claim to other diffusion releases (LLaDA, Dream, SDAR are confirmed-worse from the same paper's data).
- ❌ Do not propose architecture changes to our orchestrator stack on the basis of this paper alone — verdict is `worth_investigating`, not `new_opportunity`.

### 7.4 What we SHOULD do now

- ✅ Track in `inference-acceleration-index.md` (DONE, intake-576 added 2026-05-20)
- ✅ Track in `gpu-acceleration-path.md` as a parallel candidate to DFlash on DGX Spark (DONE)
- ✅ Cross-reference into `gemma4-mtp-drafter-evaluation.md` as the natural alternative direction if MTP path stalls (DONE)
- 🔲 **30-day Tier 2b re-run**: 2026-06-20 → search "Nemotron-Labs-Diffusion reproduction", "tri-mode self-speculation failures", check ggml-org/llama.cpp for any tracker activity, check HF for any community GGUF uploads.
- 🔲 **Quick win — Ministral3 support audit** (1 hour): verify whether `nvidia/Ministral3-8B-Instruct-2512` loads in our `production-consolidated-v4` kernel via `convert_hf_to_gguf.py`. If yes, the backbone gate is already passed. If no, that's the binding pre-port task.
- 🔲 **Quick win — AR mode quality re-test** (4 hours, post-Ministral3-gate): if Ministral3 loads, convert `nvidia/Nemotron-Labs-Diffusion-8B-Base` AR-only and run our standard 4-benchmark suite. **Goal is to validate the paper's headline claim (NLD-8B AR > Qwen3-8B AR by +0.86%) on Q4_K_M, not to nominate the model for any current production role.** Our worker_general is gemma4-26B-A4B Q4_K_M MTP — an 8B dense model is the wrong size class to replace it. If NLD-14B (66.4% avg) is later converted and bench-tested, *that* is the meaningful role-comparison candidate against worker_general. The 8B AR-mode test is a paradigm-validation step (does joint AR+diffusion training actually preserve AR-mode quality on a CPU quant?) — a necessary precursor to any spec-dec port work, not a deployment proposal.

---

## 8. Reference Genealogy (NVIDIA Diffusion-LM Lineage)

This work is the synthesis of a multi-paper NVIDIA research thread. The same author cluster (Yonggan Fu, Chengyue Wu, Enze Xie, Song Han, Pavlo Molchanov) appears across:

| Paper | arXiv | Contribution |
|---|---|---|
| Fast-dllm | 2505.22618 | Training-free acceleration of diffusion LMs via KV cache + parallel decoding (confidence threshold) |
| Fast-dllm v2 | 2509.26328 | Efficient block-diffusion LLM |
| Efficient-dlm | 2512.14067 | From AR to diffusion LMs and beyond in speed |
| TiDAR | 2511.08923 | Think-in-diffusion, talk-in-AR — the quadratic self-spec predecessor |
| **Nemotron-Labs-Diffusion** | (this, no arXiv) | Tri-mode unified model |

Concurrent prior art:
- **Set Block Decoding** (Meta FAIR, arxiv:2509.04185) — joint diffusion + AR training, the immediate prior art the Nemotron paper differentiates against (tri-mode inference, model family, SOL analysis)
- **Block Diffusion** (Arriola et al., arxiv:2503.09573) — the block-wise diffusion formulation Nemotron extends
- **Your LLM Knows the Future** (Apple, arxiv:2507.11851) — the AR-models-plan-ahead claim Nemotron leans on

Candidates for follow-up intake (relevant arxiv IDs from references):
- 2509.04185 Set Block Decoding (Meta) — concurrent joint training
- 2512.14067 Efficient-dlm (NVIDIA) — direct predecessor
- 2511.08923 TiDAR (NVIDIA) — quadratic self-spec predecessor
- 2505.22618 Fast-dllm (NVIDIA) — confidence-threshold sampling
- 2503.09573 Block Diffusion (Cornell) — the block-wise formulation
- 2604.09557 SPEED-Bench — the benchmark the paper relies on
- 2602.23881 LK losses — the distribution-matching loss used in LoRA drafter training

A future intake pass should pick up Set Block Decoding (2509.04185) and Efficient-dlm (2512.14067) as the highest-priority follow-ups — both are direct precursors and define the design space.

---

## 9. Bottom Line

**Nemotron-Labs-Diffusion is the first diffusion-LM release that earns serious EPYC consideration.** The architecture is dense Ministral3-8B (no Mamba, no Delta Net, no recurrent verify wall), the drafter and verifier share weights (no cross-precision drift), and the reported gains (3.32× on GB200, 2.69× on DGX Spark INT4-vs-INT4) match the spec-dec literature's better numbers.

**It is not deployable today.** No GGUF, no llama.cpp support, no community port. The 15–25 day porting effort is comparable to DFlash but with materially better prerequisites — the structural blockers that killed our DFlash CPU work (recurrent verify wall, cross-precision drift) do not apply here.

**Decision now**: track, monitor for community ports + reproductions, do not start engineering. The two cheap audit tasks (Ministral3 support check, AR-mode quality bench) are the right next moves and decouple the worker-tier replacement opportunity from the harder spec-dec work.

**Decision criteria to revisit**: (a) community llama.cpp port appears, (b) AR-mode quality re-test on Q4_K_M matches the paper's claim that NLD-8B-AR > Qwen3-8B-AR, (c) DGX Spark acquired and we want a Day-0 self-spec validation, (d) MTP path in `gemma4-mtp-drafter-evaluation.md` stalls and we need an alternative direction.

**Memory of contradicting evidence** (for the avoidance of closure-inflation): single-source numbers (NVIDIA-only), no third-party reproductions yet, no llama.cpp port, no Q4_K_M data, no batch>>1 data, sibling Nemotron-3-Nano has open llama.cpp Mamba assertion crashes. Re-run Tier 2b contradicting-evidence search at 30, 60, 90 days post-release.

---

## 10. Open Question (added 2026-05-28) — TiDAR-pattern one-pass variant for CPU

### 10.1 The framing

The user surfaced the right asymmetry: **EPYC 9655 has idle FLOPS and a saturated memory bus** (project_cpu_decode_bw_bound). Diffusion drafting trades BW limitations for FLOP limitations — exactly the opposite of our usual constraint. Worth exploring whether some hybrid arrangement can convert spare FLOPS into effective decode throughput by hiding weight-fetch latency behind diffusion-thinking compute.

### 10.2 Why TiDAR (intake-633) re-enters the conversation

Initial intake dismissed TiDAR as superseded by Nemotron-Labs-Diffusion. Deep-dive 2026-05-28 corrected that:
- TiDAR's "free token slots" mechanism is **latency-plateau exploitation at batch=1 decode** (paper Fig.1). The plateau exists because weight + KV-cache fetch dominates per-step cost — **that is the CPU regime**, not the inverse.
- TiDAR is **single forward pass per cycle**; Nemotron's shipping Linear-SS mode is two-pass. On CPU each pass = one full weight scan, so TiDAR halves per-cycle weight traffic vs Linear-SS.
- TiDAR is the architectural ancestor of Nemotron's *underperforming* Quad-SS mode. Quad-SS underperforms on GPU because FlexAttention kernels for the quadratic mask are unoptimized — **on CPU we write ggml ops either way, so the FlexAttention blocker does NOT carry over**.

### 10.3 Two specific variant proposals for the §6 port plan

**Variant A — Linear-SS port (current §6 plan baseline)**
- Two-pass: draft pass (diffusion) + verify pass (AR). Standard Nemotron shipping mode.
- 5–10 days for the block-wise attention mask, then standard MTP-style integration.

**Variant B — TiDAR-pattern one-pass on dense Ministral3 backbone (NEW)**
- Single forward pass: unified causal+bidirectional mask handles draft + verify in one weight scan.
- Halves per-cycle weight traffic vs Variant A on CPU.
- Accepts the 6–9% HumanEval/MBPP quality cost TiDAR-8B Trust-Diff showed (we may need to verify under our quants).
- Requires writing the structured mask as a ggml op — but we'd need to do something similar for Variant A's block-wise mask anyway.

**Variant C — split-role hybrid (USER PROPOSAL — speculative)**
> "Maybe there's a scenario where we can explore using a diffusion model for thinking and an AR model for generation? Or viceversa?"

This is genuinely novel and worth scoping. Two specific candidates:

- **C1 — diffusion-think + AR-generate**: route a "thinking-budget" prefix segment through a TiDAR/Nemotron diffusion path that fills idle FLOPS with parallel exploration of K candidate continuations, then commit to a single committed candidate and switch to standard AR for the final-answer segment. Aligns with `per-request-reasoning-budget.md` (active handoff): the reasoning budget can be spent on diffusion-thinking, the answer budget on AR-decoding. The roles need not share weights.
- **C2 — AR-think + diffusion-generate**: invert C1. Use AR for the reasoning chain (where serial dependencies dominate and acceptance-length wins are smaller) and diffusion for the final-answer generation (where the answer is often K parallel near-independent tokens — code lines, list items, table cells). Less obviously beneficial because answer segments are usually shorter than reasoning segments on our workloads.

### 10.4 What needs to be measured before any of these is chosen

1. **EPYC decode FLOPS / BW roofline** [USER-GATED]: roofline measurement of compute and memory-bandwidth utilization during AR decode on Q4_K_M gemma4 (or whichever production model is the target backbone). Requires running a live llama-server / llama-cli at decode with AMD-correct perf counters attached (`fp_ret_sse_avx_ops.*` + `amd_df/cs_dispatched_*/` or `pcm-memory` or `AMDuProfPcm`) — see `handoffs/active/cpu-decode-flops-roofline-audit.md` for the resolved AMD Zen 5 event set and Phase 0 calibration steps. Per `feedback_no_concurrent_inference` and `feedback_speed_verify_via_llama_bench`: this is **NOT** an autonomous task — user must explicitly approve the run, and the agent must verify no other inference job is active. Expected output: **achieved FLOPS during decode as fraction of ~9.2 TFLOPS FP32 socket theoretical**; **achieved DRAM BW as fraction of ~614 GB/s socket theoretical (and as fraction of the 460 GB/s measured-aggregate practical ceiling)**. Promotion rule: if achieved FLOPS < 10% AND achieved BW > 70% of theoretical → BW-bound, FLOPS-for-BW trade has real margin. If achieved FLOPS > 30% (e.g. AVX-512 prefetch saturation or thread spin overhead) the trade is narrower.
2. **TiDAR-pattern mask ggml-op complexity** vs Linear-SS mask ggml-op complexity [STATIC ANALYSIS, no inference required]. If they're comparable, Variant B is strictly cheaper than Variant A in long-term throughput on CPU. Read antirez fork + intake-635 minimal reimpl for the TiDAR mask; cross-reference Nemotron paper §4.2 for the Linear-SS mask shape.
3. **Quality cost of TiDAR-pattern under aggressive quant** [USER-GATED, requires perplexity benchmark]: TiDAR loses 6–9% on HumanEval/MBPP at BF16; the gap could widen under Q4_K_M. Cannot be measured without an actual TiDAR or TiDAR-pattern checkpoint at Q4_K_M, which we don't have today — so this question is dormant until either Variant B is built or someone else releases a quantized TiDAR-pattern model.
4. **C1/C2 routing decision overhead** [STATIC + DESIGN, no inference required]: every hybrid scheme has a phase-switch cost. For C1 specifically: how do we decide where the thinking budget ends and the generate budget begins? Per-request reasoning budget heuristic is the obvious gate (already tracked in `per-request-reasoning-budget.md`).

### 10.5 Recommended decision sequence

The sequence below interleaves cheap analytical work (which the agent can do) with user-gated inference work (which the user runs):

1. **[Agent, no inference]** Static analysis of TiDAR-pattern vs Linear-SS mask ggml-op complexity (§10.4.2). One day of code reading.
2. **[Agent, no inference]** C1/C2 routing-gate design sketch using `per-request-reasoning-budget.md` as the substrate (§10.4.4). One day of design note.
3. **[USER]** Run the EPYC FLOPS headroom measurement (§10.4.1) when convenient — full protocol prepared in [`handoffs/active/cpu-decode-flops-roofline-audit.md`](../../handoffs/active/cpu-decode-flops-roofline-audit.md) (exact `perf stat`/`pcm-memory` command, warmup + sustain protocol, findings.md template). Agent does not execute. One-shot, no follow-up bench needed unless the result is borderline.
4. **[Agent]** Synthesize §10.4.1-2-4 outputs into a Variant A vs B vs C1/C2 decision memo. **Promotion rule (matches the audit handoff's decision rule exactly): if achieved FLOPS during decode < 10% of theoretical socket peak (~9.2 TFLOPS FP32) AND achieved DRAM BW > 70% of theoretical socket peak (~614 GB/s, i.e. > ~430 GB/s)** → scope Variant B (TiDAR-pattern one-pass) alongside Variant A (Nemotron Linear-SS) in the §6 port plan. Otherwise stay with Variant A baseline. Defer C1/C2 hybrids until a single-arch variant is working — they compose on top. (Previous "headroom ≥ 30%" wording was ambiguous: "headroom" could mean either idle-FLOPS or achieved-FLOPS. The rule above is in terms of **achieved** fractions of theoretical peak.)
5. **[Agent]** If Variant B is chosen, re-flag intake-635 (community minimal reimpl) as the readable mask-trick reference.

This open question is logged here rather than added to handoffs because (a) it's research-stage, not engineering-ready, and (b) per-project policy index changes require explicit user approval — this is a deep-dive annotation, not a handoff modification.
