# C15-MMVQ-FUSED-Q8 feasibility: fold activation quantize into MMVQ (2026-11-18)

**Question.** Would folding `quantize_q8_1` into `mul_mat_vec_q` give at least 1% on MI210 27B Q8_0 decode?
**Input.** INF48-GATEUP-PROBE GPU half (`research/deep-dives/inf48-gateup-probe-20261118.md`, root f834d3d24). There,
all activation quantization is 3.56% of decode GPU busy time and each launch is about 4.5 us at 5120 wide.
**Source read.** C14 `llama.cpp-experimental-c14-fa-fold-20261118` @ eee3da838. Read only, through `git show`/`git grep`.

## What the champion already does

- **"Quantize once, reuse for all consumers" is already on by default.** `ggml_cuda_mul_mat_vec_q` in
  `ggml-cuda/mmvq.cu` (around lines 2456-2518) keeps a per-capture `mmvq_q8_1_graph_cache` under HIP graphs. It
  covers Q4_K, Q6_K and Q8_0 with ncols=1. Each later MMVQ that reads the same `src1` reuses the cached q8_1
  buffer and skips its quantize launch. Commits: dd161d519 (+2.135% tg128), c0d42d81c (+1.315%), 61bdb185c (private
  arena). The second half of the idea is therefore already shipped and measured.
- **Gate and up are already one fused launch** that reads one quantized input (`ggml_cuda_mm_fusion_args`, INF48).
- **HIP graphs already hide the launch overhead.** INF48 measured a median idle gap of 0 us before MMVQ launches.
  The 3.56% is kernel busy time, not dispatch gaps.
- **Upstream has nothing comparable.** The C14 history has no fused-quantize MMVQ (searched `git log -i --grep=quantiz`
  and `-S mmvq_q8_1_graph_cache`). Upstream CUDA hides the gap with PDL (`ggml_cuda_pdl_lc/sync`), which is CUDA only.

## What is left and what folding would cost

- 3.56% of 1052 ms over 32 tokens is about 1.17 ms per token. At 4.5 us each, that is about 260 quantizes per token, or
  about 4 per layer across 64 layers. These are the inputs that remain after dedup: attention or GDN input, attention
  output, FFN input, FFN down input. Each has exactly one consumer kernel, or one fused kernel.
- A 4.5 us quantize of 20 KB is pure latency, not bandwidth. Folding removes it, but every MMVQ workgroup then has to
  rebuild the **whole** 5120-wide q8_1 vector itself before its first dot. That means about 20 KB from L2, a 32-lane
  amax/sum reduction, a 5.8 KB LDS write and a barrier. The kernels are `__launch_bounds__(...,1)` with low occupancy,
  so that prologue sits on the critical path of every wave. That is thousands of workgroups for gate+up, and several
  waves even for the 5120x5120-class projections.
- Estimate: removing the kernel saves ≤3.56%. A prologue of about 1-2 us per wave, repeated over the waves of each
  MMVQ, takes most of that back. The FFN-down input (17408 wide, ~68 KB f32 per workgroup) makes it worse.
  **Realistic net ≈ 0-1% of decode, and it can be negative.** The keyed alternative, quantizing in the producer
  epilogue (RMSNorm or GLU writing q8_1 directly), is a different candidate: it changes norm/GLU kernels, not MMVQ.

## Decision

**STOP. Realistic gain is below 1% of decode, under the 1.01 KEEP bar.** No worktree, branch, commit or row was
created. If anyone pursues this further, the better-shaped follow-up is a producer-epilogue q8_1 write (rms_norm/GLU →
q8_1). It removes the same launches without the per-workgroup redundant prologue and should get its own probe.
