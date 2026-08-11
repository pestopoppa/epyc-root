# Handoff: MI210 MFMA for compute-bound paths (prefill / diffusion / high-batch)

**Status**: **CLOSED-BY-ARITHMETIC for decode** (2026-08-03) — the 2026-07-04 `MfmaUtil ≈ 0%` observation is
now explained, not merely measured; see §"Compute roofline" below. **OPEN for prefill/diffusion** on the
original measure-first gate. **Created**: 2026-07-04 (MI210 campaign follow-on).
**Owner tree**: `/mnt/raid0/llm/llama.cpp-experimental` (kernel work here, never production-v6). **Substrate**: MI210 gfx90a/CDNA2 — has fp16/bf16/int8 **MFMA matrix cores**. All numbers OBSERVATION.
**Context doc**: `fable5-window2-findings-05b-mi210-inference-architecture.md` §9 (the GDN-MFMA-decode KILL, and why MFMA is alive for compute-bound regimes).

## UPDATE 2026-07-04 — measurement gate FAILED on both paths; DEFER (with data)

Kernel-thread `a8afd338` ran the decisive pre-build rocprofv2 measurement. **Neither candidate meets the acceptance criterion (high VALUBusy + idle matrix cores):**
- **Prefill** (`-p 1024`): dominant GEMM is ALREADY rocBLAS/Tensile fp16 **MFMA** HGEMM (`MI32x32x8`, AccVGPR=208). VALUBusy **3.55%** (vector ALU near-idle), MemUnitBusy **78.5%** → memory-bound, MFMA already the workhorse. No idle matrix cores.
- **High-batch decode** (`-npl 128`): batched GEMM is `mul_mat_q` MMQ **int8-MFMA** (AccVGPR=128). VALUBusy **16.8%** (not compute-bound), MemUnitBusy 48%; and **43% of batch-128 time is non-GEMM elementwise/norm** + 20% memory-bound GEMV.

→ MFMA kernel-authoring **DEFERRED** — matrix cores are already engaged on both. The 2026-07-04 profile also suggested an orthogonal high-batch elementwise/norm fusion lever, but the strict frozen-v9 refresh on 2026-08-11 **falsified it**: actual norm + activation + elementwise share is 1.490% at B=128, not the coarse 43% non-GEMM remainder. **Reopen the MFMA build only if a NEW compute-bound path appears** (a diffusion/DiT serving path — `ernie-image-turbo`; or gfx90a training [unverified]); the measure-first gate below still stands. Original objective kept for the record.

## Compute roofline — the blank spot, closed by arithmetic (2026-08-03, research-intake)

_Via `/research-intake` Stage-2b (intake-944/947 dive-I, plus AMD's own GEAK `perf_knowledge/hardware/cdna2_mi200/` KB).
**No peak-FLOPs figure or ridge point existed anywhere in the six MI210/autokernel handoffs before this.**
All four rates are **`[D]` derived from spec**, not measured — they reproduce AMD's published figures exactly,
but any citation must carry the `[D]`._

| Quantity | MI210 (gfx90a, 104 CU @ 1.7 GHz) | Note |
|---|---|---|
| fp16 / bf16 matrix | **172.2 TFLOPS `[M]` measured** · 181.0 `[D]` derived | derived = 104 CU × 1024 FLOP/clk × 1.7 GHz; **measured 2026-08-03 = 95.1% of it** |
| int8 matrix | **181.0 TOPS** `[D]` | **CDNA2 does NOT double int8** — unlike CDNA3 |
| fp32 matrix / vector | 45.3 / 22.6 TFLOPS `[D]` | |
| FP8 / FP4 / TF32 | **none** | no matrix-core support on gfx90a at any rate |
| **Ridge — measured basis (USE THIS)** | **120.1 FLOP/byte `[M]`** | 172.2 TFLOPS ÷ 1433.3 GB/s, **both measured 2026-08-03** |
| Ridge — spec basis | 110.5 FLOP/byte `[D]` | 181.0 TFLOPS ÷ 1.638 TB/s; correct on its own basis, use for cross-vendor |
| ~~Ridge — mixed basis~~ | ~~126.3~~ **SUPERSEDED 2026-08-03** | divided spec FLOPS by measured BW; retired once both terms were measured |

**Peak FLOPS is measured, so the ridge is no longer mixed-basis.** 172.2 TFLOPS against 181.0 derived is
**95.1%**, and the shortfall is **clock, not architecture**: the implied sustained clock is **1.617 GHz**
against the 1.7 GHz boost the derivation assumed. **The `104 CU × 1024 FLOP/clk` arithmetic is
confirmed** — only the clock assumption was optimistic. Receipt
`epyc-inference-research/data/mi210-mfma-peak/20260803T143200Z/`, committed `a2b4e9fc`.

Measurement quality: the occupancy sweep is **flat from 104 blocks (416 waves, one per SIMD) to 3328
blocks** (172.13–172.32), so the matrix cores are **issue-limited, not occupancy-limited** — a real
plateau rather than a grid artifact. Spread across timed reps 0.02%. The emitted ISA carries exactly
`UNROLL=8` `v_mfma_f32_16x16x16f16` instructions, which is the check a peak-FLOPS microbenchmark most
needs: **a loop optimized away reports infinite throughput.**

For contrast the RTX PRO 6000 Blackwell fp16 ridge is **281** (FP4 ridge 1124) — **the MI210 is the more
bandwidth-balanced part**, so a bandwidth-directed program is the arithmetically correct one here.

**Two standing questions this converts from deferred to closed:**

1. **`MfmaUtil ≈ 0%` at batch-1 is CORRECT BEHAVIOUR, not a defect.** Batch-1 arithmetic intensity is
   fp16 1.00 / Q8_0 1.88 / Q4_K 3.56 / IQ2 5.19 FLOP/byte — **31–113× below the knee**. At that AI the
   matrix units cannot exceed ~1.7–3.2% busy *at any bandwidth*. The 2026-07-04 profile was reading the
   physics, not a missed optimization.
2. **The batch knee is now predictable:** `B* = ridge × bytes_per_weight / 2`. On the **measured basis
   (use this)** → **Q4_K 34, Q8_0 64, bf16 120**; on the spec basis → Q4_K 31, Q8_0 59, bf16 110. Above
   `B*`, bandwidth attainment stops being the right ceiling and the matrix roofline takes over.

   **Still honest about what the knee does and does not settle.** The measured bf16 knee is **B≈96–128**,
   and the measured-basis prediction (120) falls inside it — as did both earlier candidates (110, 126).
   Measuring peak FLOPS removed the *basis* ambiguity; it did **not** sharpen the knee, because the
   observation interval is wider than the spread between candidates. Narrowing the observed knee is what
   would settle it, and nothing in the current program turns on the answer.

**Defect to carry — do not import AMD's own number.** GEAK's `perf_knowledge/hardware/cdna2_mi200/memory.md`
computes `362 TF / 1.6 TB/s ≈ 226 FLOP/byte` as a **per-GCD** ridge, while its own `arch.md` labels the same
362.1 TF figure **per-OAM (both GCDs)**. **Off by 2×. Use ~110–113, never 226.** The KB is useful and
first-class for gfx90a, but it is not error-free.

**K9 consequence, banded:** authoring MFMA *decode* kernels is worth **0, with certainty — do not build.**
That is the same conclusion the 2026-07-04 measurement reached, now with a mechanism instead of a counter.

## Arch-independent scheduling lessons (HipKittens, intake-947 — free, apply today)

Harvested from a CDNA3/4 paper with **zero mentions of gfx90a**, but these five are architectural rather
than generation-specific, so they transfer without a port. **Do not vendor the framework** — its register
tile is bit-identical to the one already in our frozen v8 (`ggml/src/ggml-cuda/mma.cuh:127,144`:
`get_i = tid%16`, `get_j = 4*(tid/16)+l`, `ne=4` — the same object as HK's `rt_base`), so every technique
below composes onto our existing fragments with **zero layout re-derivation**.

1. **Do NOT wave-specialize.** AMD statically divides registers across all waves, so producer waves consume
   registers without contributing output: measured 4 producers / 8 consumers = **893 TFLOPs** vs
   0 producers / 8 consumers = **1610**. Architectural, not gfx950-specific.
2. **8-wave ping-pong before 4-wave interleave** — ~90% of the performance at ¼ the code (48 LoC vs 183).
   Mechanism: offset-barrier team split (team 1 takes an extra `s_barrier` so it runs one cluster behind),
   `s_setprio(1)/(0)` bracketing MFMA blocks, `sched_barrier(0)` after each cluster, and a mirror-image
   parity restore before the epilogue **or the workgroup hangs**.
3. **Swizzle HBM-side, not LDS-side.** No single swizzle serves both `ds_write_b64` and `ds_read_b128`. We
   already call the direct-to-LDS intrinsic on gfx90a (`mmvq.cu:538,602`) but **deposit linearly**; HK
   inverts the swizzle into the *global* offset because a fixed-mapping DMA cannot XOR the LDS address.
   That is the concrete mechanism, and it is what we add when the LDS consumer becomes a 2-D MFMA tile read.
4. **HIPCC will not feed AGPRs to matrix-core instructions** even though the hardware supports it, forcing
   redundant `v_accvgpr_read`. A live compiler tax on gfx90a — and exactly the kind of thing C4 should
   learn to recognize.
5. **Chiplet swizzling is a non-issue** for the single-GCD MI210 — one fewer knob, not a loss. But the
   *L2-locality* half of grid swizzle does apply, and it **must be swept, not set**: measured WGM none
   1016.6 TFLOPs → 2 +6.6% → 4 +9.1% → **8 +9.6%** → **32 −13.9%**. Pure launch-order reordering, zero
   kernel-body change.

**Honest negative, recorded so it is not re-derived:** for a *dequant* gap HipKittens has **nothing** — its
quantized path is gfx950 hardware block-scaling (`mfma_scale_f32_*_f8f6f4`), with no software dequant
anywhere. Its cross-lane reductions are a plain `__shfl_down` ladder with no DPP/permlane, i.e. **worse than
what we would write** — a place we can beat it.

## Objective

The GDN-MFMA *decode* kernel was KILLED by profile: `gated_delta_net_cuda` @B=32 is memory/latency/occupancy-bound (MemUnitBusy 65.2%, VALUBusy 15.7%, MfmaUtil 0%), so MFMA has no compute headroom to exploit *in decode*. **But MFMA is the right lever for COMPUTE-bound paths**, which we have not optimized:
- **Prefill** — measured VALUBusy ~50% (vs 15.7% decode): far more ALU-active → MFMA-addressable. Long-context TTFT is the payoff (ingest role, big-prompt frontdoor).
- **Diffusion** — DiT image-gen (ERNIE-Image-Turbo on GPU) and block-diffusion drafters (DFlash): parallel denoise over a block, non-causal attention = large dense GEMMs = classic MFMA workload.
- **High-batch decode** — as batch grows, decode leaves the BW edge and becomes compute-bound (why bf16 batches better — fp16 runs native on matrix cores). The batched GEMM already routes to MMQ-MFMA; the question is whether it's fully utilizing MFMA.

## Decisive pre-build measurement (do this FIRST — don't build blind)

Profile MFMA utilization + the compute/memory split for each candidate path, to confirm MFMA is the bottleneck before authoring:
1. **Prefill**: rocprofv2 on `llama-batched-bench -npp 8192 -ntg 8` (long-prompt, decode-light) — MfmaUtil, VALUBusy, MemUnitBusy on the main GEMM kernels. If VALUBusy high + MfmaUtil low → MFMA GEMM path is a win. (Use rocprofv2 `--plugin file`; rocprof v1 SQ/TA counters read zero on this box.)
2. **High-batch decode**: rocprofv2 on `llama-batched-bench -npl 64/128` — is the batched MMQ path already MFMA-saturated (MfmaUtil high → no win) or MFMA-idle (win)?
3. **Diffusion**: N/A until a diffusion serving path exists (ERNIE DiT on ROCm/HIP is a separate pipeline task — `ernie-image-turbo-evaluation.md`); scope when that lands.

Acceptance to proceed to kernel work: a candidate path shows **high VALUBusy + low MfmaUtil** (compute-bound, matrix-core-idle). Otherwise defer.

## Kernel work (conditional on the measurement)

- Route the compute-bound GEMMs (prefill FFN/attention, diffusion denoise, high-batch expert GEMM) through **MFMA intrinsics** (`__builtin_amdgcn_mfma_*` / rocWMMA), matching CDNA2 tile shapes (16x16x16 / 32x32x8). rocBLAS/hipBLASLt Tensile kernels already MFMA-tune GEMM — check whether forcing the Tensile path for prefill beats llama.cpp's MMQ (we saw MMQ *beat* rocBLAS for batch-1 decode, but prefill is the opposite regime).
- Correctness: `test-backend-ops` + PPL/output parity.

## Cross-links / caveats

- This is **forward-looking**: prefill isn't today's complaint and there's no diffusion serving path yet, so this is lower-urgency than the single-stream dequant kernel (`mi210-q8-dequant-gemv-roofline.md`). Start with the *measurement* (cheap), gate the build on it.
- Ties to the DFlash port question (`fable5-window2-findings-05b` §2): if DFlash block-diffusion drafting is ever pursued on GPU, its denoise is exactly this compute-bound MFMA regime.
- Ties to gfx90a training viability [unverified] — training is compute-bound, MFMA-central.

## Key files
`ggml/src/ggml-cuda/mmq.cu` (MMQ-MFMA batched GEMM), `ggml/src/ggml-cuda/fattn*` (attention), `gated_delta_net.cu` (the decode kernel that was KILLED — reference for the memory-bound contrast). Prior profile: `/mnt/raid0/llm/tmp/mi210-build/campaign/finish/RESULTS.md` (Part B).

## Progress checklist

- [ ] DEFERRED (with data): reopen MFMA build only if a new compute-bound path appears (measurement gate failed both paths)
- [x] Close the compute-roofline blank spot from spec arithmetic: 181.0 TFLOPS fp16/bf16, 181.0 TOPS int8 (no doubling), ridge 110.5 FLOP/byte, all marked `[D]` ✅ 2026-08-03 — via /research-intake Stage-2b
- [x] Explain `MfmaUtil ≈ 0%` at batch-1 as correct behaviour (AI 1.0–5.2 FLOP/byte, 31–113× below the knee) rather than a defect ✅ 2026-08-03
- [x] Derive `B* = 110.5 × bytes_per_weight / 2` (Q4_K 31, Q8_0 59, bf16 110) and check it against the measured bf16 knee at B≈96–128 ✅ 2026-08-03
- [x] Record the 2× per-GCD/per-OAM defect in AMD's GEAK `cdna2_mi200/memory.md` so its 226 FLOP/byte is never imported ✅ 2026-08-03
- [x] Import the arch-independent HipKittens scheduling lessons (no wave-specialization, 8-wave ping-pong, HBM-side swizzle, AGPR/HIPCC tax, sweep-don't-set grid swizzle) ✅ 2026-08-03
- [x] Measure the launch-order/L2 half of HipKittens WGM on a standalone gfx90a proxy before touching MMQ ✅ 2026-08-11 — 240 balanced samples per none/2/4/8/16/32 cell, bit-exact outputs, device claim + 250 ms telemetry, and rocprofv2 dispatch verification found WGM16 best at **+9.823%** (paired bootstrap 95% CI 9.754–9.977%). WGM8/32 were close; WGM2 regressed. This proves launch-order locality matters but is diagnostic-only, not an MMQ keep. Receipt `/mnt/raid0/llm/autokernel/probes/inf36-wgm-gfx90a-20260811-r3/receipt.json`, SHA-256 `d9de5ede02a2ba849b1ffc4362d405a76c45279d907784ecf322ca8a133f7986`; research `f371fc83`.
- [x] **Measure peak FLOPS with a gfx90a MFMA microbenchmark** ✅ 2026-08-03 — **172.2 TFLOPS**, 95.1% of the derived 181.0, implied sustained clock 1.617 GHz. This was the last derived-from-spec denominator; **every roofline constant this project uses is now measured.** Receipt `data/mi210-mfma-peak/20260803T143200Z/`, research `a2b4e9fc`
- [x] Peak-FLOPs figures no longer need the `[D]`-only citation restriction — the measured value supersedes it for all internal use; the derived figure remains the right one for cross-vendor spec-to-spec comparison ✅ 2026-08-03
- [x] Sweep grid-swizzle WGM on the real stream-k MMQ launch with correctness, wall-time, and L2/TCC
  evidence ✅ 2026-08-11 — r1 is retained as a failed/no-op pilot because the initial remap sat outside
  the CDNA stream-k launch path. In admitted r2, pure tile-order decoding moved into stream-k and
  none/2/4/8/16/32 each passed **43/43** Q4_K correctness cases. WGM0 remained fastest; every nonzero
  cell regressed wall time by **1.286–4.050%**. The mechanism result agrees: WGM8 reduced all-MMQ TCC
  hit rate **67.304% → 59.849%** while read requests changed **+0.201%**; Q4_K alone lost **7.903
  points**. Retain WGM0 and do not commit the negative experimental source. Admitted directory:
  `/mnt/raid0/llm/autokernel/probes/inf36-mmq-wgm-gfx90a-20260811-r2`; receipt SHA-256 values:
  correctness `8065674e876ab84e58518d3084ec7671b22f007c558c40781413ec827bf71ffe`, wall time
  `af57d087f307d2ec423c3168bb0ad66efc22a81ef613877e805db105331a8cec`, counters
  `0dc3d4d01aba790f7b0f1035771d929f940661f29334fdf2db59a4b2ba8a8adf`. The trace-period
  counter pilot aborted and is excluded; the successful counter-only captures are admitted.
- [x] **Profile-select the B=64/128 elementwise/norm fusion lever through AutoKernel.** ✅ 2026-08-11 —
  `run_autokernel_g15_profile.py` captured clean frozen-v9 `rocprof` v1 timestamp maps with exact
  kernel/family/adjacent-cluster tables. The strict verdict-bearing share (norm + activation +
  elementwise only) is **1.837% at B=64 and 1.490% at B=128**, so both cells mechanically return
  `FALSIFIED_PROFILE_TARGET` against the predeclared 20% floor. B=128 is instead matrix 54.881%,
  gather/scatter 18.631%, recurrent 17.464%, and copy/convert 4.726%. The top actual fusion cluster,
  `op_add -> rms_norm_f32<1024>`, is only **0.491%**. Receipt:
  `/mnt/raid0/llm/autokernel/probes/inf36-g15-profile-v9-20260811-r4/receipt.json`, SHA-256
  `d7a0c8c257c2a59435b95c39b988485a8283d709d83ef7397b3c67ee7ec8cca9`. G15 is closed no-go;
  gather/scatter and recurrent work remain distinct mechanisms and must not be relabelled as fusion.
