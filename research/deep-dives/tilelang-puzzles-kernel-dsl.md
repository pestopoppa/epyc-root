# TileLang Puzzles + Parent TileLang DSL — GPU-Gated Kernel-Authoring Path

**Intake**: intake-497 (puzzles repo) + parent project tile-ai/tilelang
**Repo**: https://github.com/tile-ai/tilelang-puzzles (215★) · parent https://github.com/tile-ai/tilelang (5.8k★)
**Categories**: hardware_optimization, tool_implementation, local_inference (parent)
**Status**: deep-dive (written 2026-04-28); GPU-gated, no action until GPU acquisition
**Cross-refs**: intake-466 (Triton repo), intake-465 (CUTLASS), intake-464 (FlashAttention-3), intake-310 (CPU+GPU hybrid MoE)
**Parent handoff**: [`gpu-acceleration-path.md`](../../handoffs/active/gpu-acceleration-path.md)

---

## 1. Why this entry exists

The puzzles repo by itself is a 10-script tutorial — purely educational and would not justify a deep-dive on its own. What makes it worth the long write-up is the **parent project, TileLang**, and its position in the GPU kernel DSL landscape we will need to evaluate the day GPU hardware lands. The puzzles are the recommended on-ramp; the deep-dive scopes both.

Treat this document as the GPU-acquisition-day reading list for "should we author kernels in TileLang, Triton, or CUTLASS, and for which kernel families?"

---

## 2. TileLang in one paragraph

TileLang is a **tile-level Pythonic DSL** built on top of TVM that compiles to NVIDIA, AMD, Apple Metal, Huawei Ascend, WebGPU, and (nominally) generic CPU targets. It exposes layout annotations, L2-cache swizzling, software pipelining, rasterization, async copies, and 2:4 sparse tensor cores as first-class primitives, integrates Z3 for symbolic schedule reasoning, and recently added a CuTeDSL backend that lowers to NVIDIA CUTLASS CuTe primitives (Dec 2025). It is developed by **Lei Wang (LeiWang1999)**, **Chengyu Pku (chengyupku)**, and **nox-410** under **Prof. Zhi Yang at Peking University**, with significant contributions from **Microsoft Research** — and is the kernel substrate for two production Microsoft projects: **BitBLAS** (low-bit GEMM) and **AttentionEngine** (kernel library for attention variants).

The credibility-from-source-not-readme memory (`feedback_credibility_from_source_not_readme.md`) cuts both ways here: the puzzles repo's own signals are weak (7 commits, 1 watcher, 5 weeks idle as of 2026-04-28), but the parent project's signals are strong (5.8k stars, MSR-collaboration provenance, two downstream production users at Microsoft, monthly backend additions through 2025-2026). This is the rare case where the educational fork should be scored separately from the substrate.

---

## 3. The tilelang-puzzles curriculum

The puzzles repo is explicitly modelled on **srush/Triton-Puzzles** (Sasha Rush, Cornell), with **SiriusNEO/Triton-Puzzles-Lite** and **LeetGPU** as additional inspirations. The curriculum is:

| Puzzle | Concept introduced |
|--------|-------------------|
| 01-copy.py | Tile launch + global↔shared memory copy + index space |
| 02..09 (intermediate) | Element-wise ops, reductions, layout annotations, softmax, dot product, matrix transpose, online softmax, GEMM via tile MMAs |
| 10 (cap) | FlashAttention — fused softmax(QKᵀ)V with online softmax + tile MMAs |

Only `01-copy.py` is named verbatim in the README, but the curriculum trajectory (Copy → GEMM → FlashAttention) is explicit.

**Setup**: requires `tilelang` Python package + `python3 scripts/check_tilelang_env.py` for GPU validation. ~4-hour walkthrough estimated based on Triton-Puzzles' equivalent runtime.

**On-ramp value**: this is the cheapest path to evaluating whether TileLang is a credible Triton replacement for *our specific* kernel needs. Concrete deliverable: by the end of puzzle 10, a user can read FlashAttention-class kernels in TileLang notation, which matches the cognitive load of reading Dao's Triton FA reference impl.

---

## 4. TileLang vs. the alternatives — kernel DSL matrix

EPYC's GPU-day decision is not "do we use TileLang" — it is "for which kernel families do we author in which DSL". The matrix:

| Kernel family | Hand-tuned reference | Triton | TileLang | CUTLASS / CuTe | What we'd actually use |
|--------------|---------------------|--------|----------|----------------|----------------------|
| Vanilla GEMM | cuBLAS / hipBLASLt | yes | yes | yes (peak) | Library — no DSL |
| FlashAttention | flash-attn (Dao) | reference impl | yes (puzzle 10) | yes (FA3) | flash-attn library; DSL only if customizing |
| MLA decode | flash-attn / FlashInfer | yes | yes (parent README claims FlashMLA-MI300X parity) | yes | TileLang **iff** AMD path; FlashInfer iff NVIDIA |
| Block-sparse attention | FlashInfer | yes | unclear | yes (CuTe) | FlashInfer (intake-458) — DSL only for novel sparsity |
| Low-bit GEMM (Q4/Q6) | BitBLAS | possible | **native (BitBLAS built on TileLang)** | yes | BitBLAS — and BitBLAS *is* TileLang |
| MoE expert grouping | TRT-LLM Wide-EP / Triton | yes | possible | yes (grouped GEMM) | TRT-LLM iff NVIDIA Spark; otherwise Triton/TileLang |
| Spec-dec verify | none standard | yes | possible | yes | Custom — Triton or TileLang |
| Diffusion drafting (DFlash) | research code | yes | unclear | possible | Triton (vLLM reference is Triton-based) |

**Key observation**: the only kernel families where TileLang has a *unique* advantage are:
1. **Low-bit GEMM via BitBLAS** — BitBLAS is a TileLang-native low-bit GEMM library (FP4/INT4/INT8/INT2/INT1 mixed-precision). For the Q4_K_M / Q6_K / Q8_0 quants we already use in llama.cpp, BitBLAS is the natural GPU equivalent. This is the strongest pull.
2. **AMD MI300X parity** — parent README claims TileLang achieves "performance parity with hand-optimized assembly kernels" for FlashMLA on MI300X. If our path is RX 7900 XTX → MI300X (per gpu-acceleration-path.md AMD branch), TileLang is the kernel DSL with the strongest AMD Day-0 story.
3. **Multi-backend portability** — same kernel definition compiles to NVIDIA, AMD, Apple Metal, Ascend, WebGPU. Triton's AMD backend (triton-amd) exists but lags; CUTLASS is NVIDIA-only.

**Where TileLang loses**:
- **NVIDIA-only optimal stack** — if Spark-class (Blackwell + sm_120) hardware is the target, the path is FlashInfer + CUTLASS + TRT-LLM. TileLang's NVIDIA backend is fine but not best-in-class on Blackwell-specific features (warp specialization, WGMMA, FP8) where FA3 / CUTLASS are the reference.
- **Reading other people's kernels** — Triton dominates research-paper accompanying code (FA2/FA3, FlashInfer, MLA decode, log-linear GDN, BackLite). Triton literacy is non-optional for paper consumption regardless of authoring choice.
- **Maturity of CPU backend** — TileLang's "generic CPU targets" claim is unsubstantiated for our use case. No README evidence of AVX-512BW Zen 5 codegen, no NUMA-aware mappings, no proven competition with hand-tuned ggml repack kernels. Per `project_x86_kquant_repack_gaps` and `project_q8_8x8_avx512bw_outcome` memories, our wins came from hand-written AVX-512BW SIMD; TileLang would not credibly emit competitive code there.

---

## 5. The BitBLAS connection — strongest pull

BitBLAS (github.com/microsoft/BitBLAS, Microsoft Research) is "a library to support mixed-precision GEMM" with FP16/FP8 × INT8/INT4/INT2/INT1 combinations, GPTQ/AWQ/Q4F16 dequantization, and is **built on TileLang**. It powers Microsoft's quantization story (used in BitNet b1.58, Ladder, etc.).

**Why this matters for EPYC GPU day**:
- Our production stack runs Q4_K_M / Q6_K / Q8_0 quants from llama.cpp's GGUF format
- On CPU, quantized GEMV is hand-tuned in ggml (Z5 8x8 AVX-512BW kernel landed for Q8_0 — `project_q8_8x8_avx512bw_outcome`)
- On GPU, the natural equivalent is BitBLAS, which means the natural authoring DSL is TileLang (since BitBLAS *is* TileLang code)
- DGX Spark (Blackwell) supports FP4/FP8 native — BitBLAS already exposes those code paths

**Concrete evaluation question for GPU-day**: can BitBLAS load GGUF-Q4_K_M weights directly, or do we need a custom dequant kernel? BitBLAS publishes Q4F16 as one of its mixed-precision modes; the K-grouped (`_K`) llama.cpp quants may need a thin adapter. If yes, BitBLAS is the GPU successor to our current ggml CPU quantization path, and TileLang is the right DSL to author that adapter in.

---

## 6. AMD path implications

Per `gpu-acceleration-path.md` 2026-04-26 update, the GPU candidates are:
- DGX Spark (NVIDIA GB10, Blackwell, $4,699) — primary target
- RX 7900 XTX (AMD RDNA3, $999) — fallback / experimental
- MI300X (AMD CDNA3) — only via cloud / future

If the AMD path activates (RX 7900 XTX as desk hardware, or MI300X cloud bursts for RL training), TileLang's AMD story is a differentiator:

| Backend on AMD | Triton | TileLang | CUTLASS-AMD |
|----------------|--------|----------|-------------|
| RDNA3 (gfx1100 / 7900 XTX) | triton-amd, lagging | yes | no |
| CDNA3 (gfx940/941/942 / MI300X) | yes | yes (FlashMLA parity claim) | no |
| AITER (intake-307) integration | unclear | unclear | n/a |

**Decision rule**: if Spark lands first → TileLang is a parking-lot DSL (FlashInfer + CUTLASS dominate). If RX 7900 XTX or MI300X lands first → TileLang moves to evaluation-priority alongside Triton.

---

## 7. Risks and contradicting evidence

Reflecting the closure-inflation feedback memory and the credibility-from-source pattern, the risks worth recording:

1. **Educational repo signal is weak** — 7 commits in 4 months on the puzzles repo, 1 watcher. Don't treat puzzles maintenance velocity as a proxy for parent-project velocity. Verify parent activity at GPU-day.
2. **No published peer-reviewed paper for TileLang itself** — there are workshop/report-style writeups but no top-venue paper announcing the DSL. Compare to Triton (MAPL'19 Tillet et al.) and CUTLASS (NVIDIA tech reports). Reduces independent-corroboration credibility.
3. **CuTeDSL backend lowers TileLang to CUTLASS** — the December 2025 CuTeDSL backend addition implicitly concedes that for NVIDIA peak performance, CUTLASS is the substrate. TileLang-on-CuTeDSL is a productivity layer, not a peak-performance differentiator on NVIDIA.
4. **Microsoft alignment risk** — BitBLAS and AttentionEngine are both Microsoft projects; if MSR pivots away from TileLang, the parent project loses its strongest production user. Diversification of downstream users is worth tracking.
5. **Multi-backend claims always degrade in production** — "supports NVIDIA, AMD, Apple, Ascend, WebGPU, CPU" is a marketing surface. Each backend has different maturity levels; CPU is almost certainly the weakest. Don't trust portability claims without backend-specific benchmarks.
6. **Triton dominates paper-accompanying code** — independent of any authoring decision, every modern inference paper ships Triton reference implementations. Reading Triton is mandatory; authoring in TileLang doesn't reduce that requirement.

---

## 8. Integration into the GPU-gated backlog

**Action queue (all gated on GPU acquisition)**:

| When | Who | Action | Deliverable |
|------|-----|--------|------------|
| Day-0 (GPU lands) | Engineer onboarding | Run tilelang-puzzles 1-10 in 4 hours | Familiarity baseline |
| Day-1 (NVIDIA path) | Engineer | Compare TileLang FA-puzzle output vs Triton FA reference vs FlashInfer vs FA3 on the actual GPU | Author-DSL decision matrix |
| Day-1 (AMD path) | Engineer | Reproduce TileLang FlashMLA-MI300X parity claim on RX 7900 XTX or MI300X | AMD authoring DSL decision |
| Day-2 | Engineer | Evaluate BitBLAS for GGUF-Q4_K_M / Q6_K dequant + GEMM on target GPU | Q4/Q6 GPU path proven or rejected |
| Day-3+ | Engineer | If BitBLAS works for our quants → adopt as production GPU low-bit GEMM library; author any custom quant kernels in TileLang | GPU low-bit GEMM stack |

**Non-actions**:
- Don't author CPU kernels in TileLang. Stick with hand-tuned ggml + AVX-512BW (per established memories).
- Don't pre-commit to TileLang before GPU lands. The DSL choice is hardware-dependent.

---

## 9. Open questions to resolve at GPU-day

1. Does BitBLAS load GGUF directly, or do we need a llama.cpp → BitBLAS quant adapter?
2. What is TileLang's NVIDIA Blackwell (sm_120) maturity? Does it expose FP4/FP8 native, WGMMA, warp specialization?
3. Does the FlashMLA-MI300X-parity claim hold on RX 7900 XTX (RDNA3)? RDNA3 lacks MI300X's matrix cores; the claim may be CDNA-only.
4. What's the sustained activity signature on the parent TileLang repo at GPU-day vs. now? Is MSR still contributing? Any sign of academic adoption beyond Peking U?
5. Does AttentionEngine (the second MSR consumer of TileLang) cover any attention variants we'd need (sliding window, sink attention, MLA, GLA)?

---

## 10. References

- tile-ai/tilelang-puzzles (this entry, intake-497) — https://github.com/tile-ai/tilelang-puzzles
- tile-ai/tilelang (parent project) — https://github.com/tile-ai/tilelang
- microsoft/BitBLAS (downstream consumer) — https://github.com/microsoft/BitBLAS
- microsoft/AttentionEngine (downstream consumer) — https://github.com/microsoft/AttentionEngine
- srush/Triton-Puzzles (curriculum inspiration) — https://github.com/srush/Triton-Puzzles
- SiriusNEO/Triton-Puzzles-Lite — https://github.com/SiriusNEO/Triton-Puzzles-Lite
- intake-466 (Triton repo, 2026-04-26 GPU curriculum batch)
- intake-464 (FlashAttention-3, arXiv:2407.08608)
- intake-465 (CUTLASS, NVIDIA Tensor Core templates)
- intake-458 (FlashInfer, arXiv:2501.01005)
- intake-307 (AITER for ROCm — AMD inference engine)
- intake-303-309 (rocWMMA + ROCm GEMM curriculum)
