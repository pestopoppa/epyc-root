# Sakana "Sparser, Faster, Lighter LLMs" — Deep Dive

**Date**: 2026-05-08
**Trigger**: deep-dive follow-up to research-intake batch ingesting arxiv:2603.23198, the Sakana publication blog (`pub.sakana.ai/sparser-faster-llms/`), and `github.com/SakanaAI/sparser-faster-llms`.
**Intake entries covered**: intake-529 (paper), intake-530 (blog), intake-531 (repo).
**Companion**: this is the GPU-stack analogue of the dynamic-activation-sparsity neighborhood enumerated in `kolinko-effort-engine-deep-dive.md`. Sakana's paper is one of the explicit re-surface triggers (#3) recorded there.

---

## TL;DR

The initial intake assessment was directionally right but contained six factual errors and missed three structural blockers. After source-level inspection of the paper, the actual TwELL CUDA kernels, the SparseLM HF checkpoint configs, and the repo metadata:

- **Verdict: `worth_investigating` (unchanged) but narrowed to "design-reference-only".** No production-stack adoption path exists today.
- **Relevance: LOW for the paper (confirmed) and re-classified as MEDIUM with tight caveats for the blog and repo.** The actionable artifact is the TwELL bit-layout for any future ReLU-FFN training campaign on CPU — not the SparseLM checkpoints, which are 2 048-context dense toys.
- **Credibility: 3 across all three** (intake-531 lowered from 4 — single author, 4 commits, no tests, no CI, no benchmarks checked in).
- **Three structural blockers compound**: (1) MoE vs dense FFN architecture mismatch, (2) SwiGLU vs ReGLU activation mismatch, (3) speedups quoted vs dense BF16 — never against Q4_K_M which is what we actually run.

---

## Verified Facts (paper, repo, HF Hub)

### Authors

Edoardo Cetin, Stefano Peluchetti, **Emilio** Castillo, Akira Naruse, Mana Murakami, Llion Jones. arXiv submission **2026-03-24**. (Initial intake had "Andrea Castillo" in intake-531 — corrected.)

### Models

Four **dense** transformers — **NOT MoE**. Trained **from scratch** at Chinchilla-optimal token budgets (10B / 20B / 30B / 40B for the 0.5B / 1B / 1.5B / 2B models respectively).

- HF Hub slugs: `SakanaAI/SparseLM0.5B`, `SparseLM1B`, `SparseLM1.5B`, `SparseLM2B`. (No dash; intake URL guesses missed this.)
- `architectures: ["SparseLlamaForCausalLM"]`, `model_type: "llama_sparse_relu"`.
- 38 layers, hidden 2 048, intermediate 5 632 (verified for 2B).
- **`max_position_embeddings: 2048`** — research-grade context, not production-deployable.
- Format: safetensors, BF16 dense weights. **Sparsity is a runtime property, not baked into weight tensors.**
- License on HF: **Apache-2.0** (repo is MIT — license mix; flag for any redistribution).

### Architecture (FFN block)

Three-matrix gated FFN: `h_u = x W_u; h_g = ReLU(x W_g); h = h_u ⊙ h_g; y = h W_d`. **Structural twin of SwiGLU with σ = ReLU instead of SiLU** ("ReGLU" / "gated-ReLU"). Critical: the `config.json` `hidden_act: "silu"` field is a leftover from the Llama base config that the custom `sparse_models.py` overrides with `nn.ReLU()`. Stock `AutoModelForCausalLM` will NOT load these correctly without `auto_map` or vendoring `sparse_models.py`.

### TwELL format (ground-truth from `matmul_d2t.cu` + `twell.py`)

- **Per-non-zero unit**: one `uint32_t` packed as `(col_idx[15:0], bf16_value[31:16])`.
- **Per-row metadata**: `c_packed[row][0]` stores the per-row NNZ count (atomic-incremented during D2T fill); entries `[row][1..]` are the packed `(idx, val)` pairs.
- **Tile geometry (compile-time)**: `T_m=128`, `T_n=256`, `T_k=64` — WGMMA-friendly tile shape. Compressed tile width `T_n_compressed ∈ {32, 64, 128}` for compression factors 8 / 4 / 2 (default = 8). At TS8: `QUEUE_SIZE=4`, payload slots `256/8 - 1 = 31` per row.
- **Hopper-only floor**: kernels emit `wgmma.mma_async.sync.aligned.m64n256k16.f32.bf16.bf16`, `cp.async.bulk.tensor.2d.shared::cluster.global.tile.mbarrier::complete_tx::bytes`, `mbarrier.try_wait.parity.acquire`, `mapa.shared::cluster`, `barrier.cluster.{arrive,wait}`, `setmaxnreg.dec.sync.aligned`, `mov.u32 %0, %clusterid.x`. **SM 90A required** (not just sm_90 — the `a` extensions). `NUM_SMs=132` hardcoded for H100. RTX 4090 (sm_89), A100 (sm_80), MI300 — all out.
- **`OUT_DIM=2048` is hardcoded** in `matmul_t2d.cu` — kernel specialized to SparseLM's 2 048 hidden dim. Porting to other dims requires template re-instantiation.
- **D2T (training-time pack)** fuses with up-projection so the dense post-ReLU hidden vector is never materialized. Co-design.
- **T2D (inference-time read)** is the bandwidth-bound pass — 153 lines, **no WGMMA/TMA**, plain CUDA cores with `__shfl_sync` + `__ldcs/__stcs`. **This is the path that maps cleanly to AVX-512BW on EPYC.**

### Headline numbers (Table 1 at L1=2e-5)

| Scale | Inference Δ vs dense BF16 | Training Δ | Peak memory Δ | Energy/token Δ |
|-------|--------------------------|------------|---------------|-----------------|
| 0.5B  | +17.0%                   | −1.5%      | **−19.2%**    | −11.8%          |
| 1B    | +18.1%                   | +7.1%      | **−25.5%**    | ~−14%           |
| 1.5B  | +18.8%                   | +11.6%     | **−28.1%**    | ~−16%           |
| 2B    | **+20.5%**               | **+21.9%** | **+22.3%** ⚠ | −17.0%          |

⚠ The 2B memory regression is the most striking anomaly. Either an extraction error in our fetch or a real instability. It directly contradicts the blog's "memory reductions scale with size" framing.

### What the paper does NOT do

- **No comparison vs INT8 / INT4 / FP8 / Q4_K_M.** Speedups are entirely vs dense BF16. This is the most important caveat for our stack.
- **No head-to-head numerical comparison vs DejaVu / TEAL / ProSparse / Q-Sparse / CATS** — they're cited but not benchmarked against.
- **No CPU benchmark of any kind.**
- **No MoE variant.**
- **No finetune-from-existing-weights variant** — explicitly listed as future work.
- **No speculative-decoding integration angle.**
- **No proper ablation of L1 coefficient** beyond the chosen 2e-5.

### Repo reality

- **4 commits total** by `Aladoro` (Cetin, all 4). One open PR `#1` ("Add training kernels") by `emcastillo` (Castillo) opened 2026-04-24, sitting unreviewed for 7+ days at intake.
- **No tests, no CI, no setup.py / pyproject.toml, no precompiled wheels.** JIT-built via `torch.utils.cpp_extension.load`.
- Default branch is **`master`**, not `main` (intake initial guess was wrong; redirected by GitHub).
- 47 stars, 4 forks, repo size 1.8 MB, last commit 2026-04-22. **Publication-drop, not active project** — silent for 16 days at intake.
- HF model cards are **empty README.md** files; no usage instructions, no benchmarks.

---

## Refuted or Adjusted vs Initial Intake

| Initial claim | Reality | Severity |
|---------------|---------|----------|
| 3 model scales (0.5B / 1.5B / 2B) | 4 scales (added 1B) | minor — fixed in revised entry |
| "Andrea Castillo" (intake-531) | "Emilio Castillo" (intake-529, intake-530 had it right) | minor — fixed |
| "static sparse pretrained checkpoints" (intake-531) | **Dynamic per-token activation sparsity; weights are dense BF16** | **major — fundamental misframing, fixed** |
| ">95% sparsity" (blog) vs ">99%" (paper sub-agent) | Both true at different layers/thresholds; **average activation sparsity** at L1=2e-5 is the right one-line claim | minor — clarified |
| "H100 targeted" | **SM 90A required** (uses WGMMA / TMA / cluster — not just sm_90) | major — A100/RTX 4090 ruled out, was glossed over |
| "stars 46, ~4 commits" | 47 stars, 4 commits **all by single author** (Cetin) | minor — single-author bus factor was understated |
| "MIT license" | Repo MIT, **HF weights Apache-2.0** | minor — license mix flagged |
| "Speedups up to 30%" (blog) | **+17.0% / +18.1% / +18.8% / +20.5%** at L1=2e-5 (Table 1). The blog's 30% is a peak/best-case framing, not the typical operating point | medium — relevance argument should use 17–20% |
| "Memory reduction scales with size" (blog) | **2B model shows +22.3% memory REGRESSION** in Table 1 — anomaly | major — direct counter-evidence to blog framing |
| Comparisons made implicit "vs current SOTA" | **All vs dense BF16 only.** No quantized baseline anywhere | **major — the apples-to-apples for our stack is vs Q4_K_M, which the paper does not do** |
| Credibility 4 (intake-531) | Lowered to **3** — single author, 4 commits, no tests, no CI, empty HF cards | minor — closer alignment with paper credibility |

---

## New Findings (not in initial intake)

1. **The "no quantization baseline" gap is the headline.** Q4_K_M loads ~0.5 bytes/weight; sparse-BF16 at 99% sparsity loads ~0.16 BF16 bytes/weight = ~0.32 bytes/weight effectively (header + index overhead). The arithmetic is *close*, but Q4_K_M has the **structured-load advantage** (256-element super-blocks with shared scales/mins, contiguous reads, no gather). Indirect-addressed sparse loads break super-block alignment — either duplicate the super-block scale per non-zero index (memory blow-up) or read full super-blocks anyway (no BW saving). **This is the dominant blocker for any naïve TwELL-on-Q4_K_M port.**

2. **The architectural cascade**: production stack is **MoE** (Qwen3 30B-A3B, Coder-30B, Next-80B, REAP-246B). Sakana models are **dense gated-MLP**. TwELL skips post-ReLU zeros within a single FFN; MoE skips entire experts. **The two compute-saving regimes are not orthogonal-stackable in any way the paper demonstrates** — Sakana would need an MoE-TwELL variant, which doesn't exist.

3. **Activation function incompatibility**. Production drafters/targets use SiLU/SwiGLU (Qwen, Llama-3, Mistral). TwELL needs ReLU. Adopting forces either retraining FFN as ReGLU (cost: full pretrain) or using SparseLM checkpoints directly (cost: 2 048-context toy model that can't replace any production role).

4. **Draft-target compatibility implications.** Even if SparseLM-2B were used as a drafter for a SwiGLU target (Qwen3 30B-A3B Coder), the activation-function mismatch causes guaranteed logit drift independent of vocab/embedding alignment. Acceptance rate would collapse. SparseLM cannot be a drop-in drafter in the current stack.

5. **The L1=2e-5 op-point is single-point.** No Pareto sweep at L1=1e-4, 1e-5, 5e-5 in the throughput table. We don't know if 2e-5 is the sweet spot or just a chosen one — and it's the only one with the +17–20% number attached.

6. **The T2D-only path IS portable in principle.** 153 lines, plain CUDA cores, BF16 + FP32 accumulation, gather-style read. AVX-512BW gather + `_mm512_dpbf16_ps` (Zen 5 supports AVX512_BF16) is a clean target. **Estimated port cost: 1–2 dev-weeks for a T2D-only AVX-512BW reference**, more for fused MLP. D2T is impractical to port (uses cluster/TMA).

7. **Hilbert-curve tile scheduling for SM occupancy** is novel for this kernel class — interesting design point, but CPU has no analog (CCD/thread pinning is already hand-tuned).

8. **Energy measurement is GPU-only** — pynvml + nvidia-smi fallback in `energy_utils.py`. Any CPU port would need separate RAPL/perf/powercap instrumentation.

9. **The headline novelty is the kernel co-design, not the algorithm.** L1-induced ReLU activation sparsity is well-trodden (ReLUfication / ProSparse / TurboSparse / CATS). The contribution is the fused TwELL D2T+T2D pipeline aligned to WGMMA/TMA/cluster on Hopper. Engineering, not a paradigm shift.

10. **Single-author bus factor**. 4/4 commits by Cetin alone. No second-party engagement except one stalled PR. This is a publication artifact, not a maintained library.

---

## Revised Assessment

### intake-529 (paper, arxiv:2603.23198)

- **Novelty: medium (unchanged).** Algorithmic class is incremental on ReLUfication / ProSparse. Kernel engineering is real but Hopper-specific. The empirical "scaling helps sparsity" claim from 0.5B → 2B is interesting but single-lab single-recipe and contradicted by NimbleEdge at production scales.
- **Relevance: LOW (confirmed).** Concrete reasoning: H100-only kernels, no quantized baseline, requires from-scratch pretraining we don't do, ReLU vs SwiGLU breaks every production model. The 2B memory regression is an anomaly that further weakens the scaling claim.
- **Credibility: 3 (unchanged).** Sakana brand + Llion Jones + open code give weight; but no head-to-head vs DejaVu/TEAL/ProSparse, modest +20% over BF16 vs ">99% sparse" framing, 2B memory anomaly, and missing quantized baseline are all flags.
- **Verdict: worth_investigating (narrowed).** Track for re-surface triggers. Do NOT open a port handoff today.

### intake-530 (blog)

- **Novelty: medium (unchanged).** Blog adds the 0.5B → 2B scaling-helps-sparsity framing not present in initial paper extraction.
- **Relevance: medium (unchanged but caveats sharpened).** Blog framing is product-marketing-adjacent — peak speedups (30%) are quoted instead of typical (17–20%), and the 2B memory regression is omitted. Useful counter-evidence to NimbleEdge's modern-LMs-lose-sparsity thesis recorded in intake-528.
- **Credibility: 3 (unchanged).**
- **Verdict: worth_investigating (narrowed).**

### intake-531 (repo)

- **Novelty: high → keeping high.** The TwELL bit layout (16-bit idx + 16-bit BF16, per-row NNZ header, 256-tile width) is genuinely new kernel engineering and well-modularized. Hilbert-curve tile scheduling is novel for this class.
- **Relevance: medium (unchanged but caveats sharpened).** The T2D-only AVX-512BW port path is real (1–2 dev-weeks) but gated on having a ReLU-FFN model in our stack — which we don't and won't without pretraining.
- **Credibility: 4 → 3 (lowered).** Single-author, 4 commits, no tests, no CI, no setup.py, empty HF model cards, single open PR stalled 7+ days. Reproducibility plausible but unverified by anyone outside Sakana.
- **Verdict: worth_investigating (narrowed to "format-spec reference for any future ReLU-FFN CPU training experiment").**

### Cross-cutting

The structural blockers (MoE vs dense, SwiGLU vs ReGLU, no quantized baseline) compound. **Each one alone could be worked around; together they form a wall.** The only world where this work becomes immediately actionable for EPYC is one where: (a) someone releases an MoE+ReLU+sparse-trained checkpoint that maps to a draft or target role, and (b) a CPU sparse-FFN execution path exists for some other reason. Neither exists today.

---

## Refined Re-surface Triggers (machine-readable)

1. **Existing-weight finetune variant** of the L1 sparsification recipe. Paper lists this as future work; until it lands, retraining-from-scratch is the cost.
2. **Combined sparse + INT4 / Q4_K kernel result vs Q4_K_M dense baseline.** The apples-to-apples we need. As long as the only baseline is dense BF16, the relevance to our quantized stack is unanswerable.
3. **MoE variant of TwELL.** Activation sparsity on top of expert sparsity could compound; Qwen3 30B-A3B is the obvious target.
4. **A Qwen-family or DeepSeek-family checkpoint** released using this recipe (not Sakana's 0.5B–2B from-scratch toys). Until then, no usable production weight exists.
5. **CPU port by anyone** (even a slow reference implementation) demonstrating BW savings under indirect-addressed gather on an EPYC-class chip. Validates whether the +17–20% GPU number translates.
6. **Internal pretraining-from-scratch campaign** in our project. L1 regularization is a trivial addition if we ever pretrain — this remains the cheapest entry point.
7. **Sorted-bucket repack format** lands in ggml for unrelated reason → trailing-skip / TwELL packing become reusable design references (shared with intake-528 trigger #1).
8. **Dynamic-activation-sparsity family re-enters scope** (intake-528 trigger #3) → revisit Sakana's iso-quality scaling claim against modern weights as part of that family review.

---

## Open Questions Still Outstanding

1. **Is the 2B memory regression (+22.3%) a Table-1 extraction error or a real instability?** Confirming requires reading Section 5 of the PDF. If real, it inverts the blog's "scaling helps" framing.
2. **Down-projection load pattern under TwELL.** The kernel is co-fused with up-projection; the down-projection BW saving step (sparse → dense via gather of `W_d` rows) is the actual bandwidth-shedding moment. Need Section 4 for the kernel-level access pattern.
3. **Perplexity / downstream-eval gap quantified.** "Negligible" is asserted but the threshold and tasks aren't quantified in our extraction. Needs Section 5 + appendix.
4. **L1 sweep behavior.** L1=1e-4 (max) was sparser per the appendix tease but not in the throughput table. Pareto frontier unclear.
5. **Head-to-head vs DejaVu / TEAL / ProSparse / Q-Sparse on the same 0.5B–2B scale.** The paper cites them; no numerical comparison.
6. **SparseLM-2B downstream-eval benchmarks.** HF model cards are empty. We don't know HumanEval / MMLU / GSM8K numbers vs Qwen3-1.7B at matched compute.
7. **Whether `mm_t2d_kernel` actually scales to non-2048 OUT_DIM** without re-engineering. The 2048 hardcode is suspicious for a "general" kernel.
8. **AVX512_BF16 availability on Zen 5.** Verify EPYC 9655 supports `_mm512_dpbf16_ps` before scoping any T2D port. (Memory `project_zen5_vnni_vs_maddubs` notes VPMADDUBSW vs VPDPBUSD trade-offs; analogous BF16 question.)

---

## What Changes Downstream

1. **Three intake entries revised** (529 / 530 / 531) with corrected facts, sharpened justifications, and `deep_dive:` pointer to this document.
2. **Handoff `cpu-shape-specialized-gemv-decode.md`**: existing Research Intake Update section (added 2026-05-08 by initial intake) gets a deep-dive addendum noting the revised credibility on the repo, the no-quantization-baseline blocker, and the SwiGLU-vs-ReGLU wall.
3. **`feedback_closure_inflation`** continues to apply: the deep-dive avoids generalizing from "CPU port is feasible" to "CPU port is justified" — the format is portable, but the use case is not present.
4. **No new handoff stubs.** The trigger conditions for opening one (Qwen/DeepSeek-family ReLU-trained checkpoint, MoE-TwELL variant, finetune-from-existing-weights recipe, internal pretraining campaign) are all absent.

---

## References

- Initial intake batch: `research/intake_index.yaml` intake-529, intake-530, intake-531 (ingested 2026-05-08).
- Adjacent deep-dive: `research/deep-dives/kolinko-effort-engine-deep-dive.md` (intake-528, dynamic-activation-sparsity neighborhood, 2026-05-08).
- Production handoff with this batch's Research Intake Update section: `handoffs/active/cpu-shape-specialized-gemv-decode.md`.
- Counter-evidence anchor: NimbleEdge sparsity white paper / ICLR 2025 SLLM workshop materials (recorded in intake-528 contradicting_evidence).
- Sakana lab cluster: intake-474 (Trinity), intake-493 (Conductor), intake-511 (KAME).
- Block-sparse MoE prior art: intake-467 (MegaBlocks).
