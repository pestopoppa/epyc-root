# HIP: add split-K F32 GEMM path for untuned RDNA3 chips

[Primary source](https://github.com/ggml-org/llama.cpp/pull/33167) · intake-3008 · 2026-11-27

Open on 2026-11-27. F32 singleton GEMMs on HIP RDNA3 except gfx1100/generic: K>=2048, unsplit 64x128 tile count <= nsm/2, choose largest 2/4/8/16/32 equal K slices with slice K>=64 and tiles*slices<=4*nsm. One strided batched SGEMM writes partial FP32 outputs and a separate GPU kernel deterministically sums them in slice order, with a disable env guard. Bench only on RX 7700 XT/gfx1101, ROCm 10.2.0 and rocBLAS 5.8.0. The microbench saw 329.9→36.2 us for 64x256 K4608 (32 slices), 160.4→34.4 us for 128x256 K2304 (16), and 308.7→34.3 us for 64x192 K4608 (32), NMSE ~1e-12; Inkling prefill at ub256 ranged +9.0–12.2%, and gains shrank for other model/shape/ubatch. Results compare same backend on/off; thresholds from one GPU. Four shape tests added including K=4600.

handoffs/active/autokernel-loop.md:L4280 @ b93bd31 already owns the two-pass reduction motif in AK-ASM-H7. handoffs/active/model-evaluation-queue.md:L725 @ b93bd31 owns Inkling port. MI210 is gfx90a; exact predicate excludes it, and local rocBLAS must establish an analogous F32 hotspot first. EPYC 9655 CPU has no HIP path and K splitting adds partial write/reduction, so only reconsider if measured small-output CPU GEMM tile parallelism is actually limiting.

The PR was a draft on the review date. At pp512 and ub256 the author reports 693 to 730 t/s on Qwen3.6-35B-A3B. The half-CU bound applies to the initial output tile count. Slice count is selected separately.

## Evidence

- Split-K is gated to selected HIP RDNA3 targets with K at least 2048, excluding the base RDNA3 code. [ggml/src/ggml-cuda/ggml-cuda.cu:L1941-L1947 @ 9384a12](https://raw.githubusercontent.com/abeloin/llama.cpp-mix/9384a12815111ccfa6fb6c34e1f47edad0dc987d/ggml/src/ggml-cuda/ggml-cuda.cu)
- The best 32-slice microbenchmark took 36.2 µs versus 329.9 µs for rocBLAS at the specified shape. [Additional information §Micro benchmark](https://github.com/ggml-org/llama.cpp/pull/33167)

## Scope and local transfer

No independent reproduction of the gfx1101 numbers found. rocBLAS/Tensile table explanation is uploader-reported and does not demonstrate gfx90a behavior; code predicate settles direct applicability.



The existing Q8 atomic-flush determinism task addresses a different type and reduction path. Join actual ffn_gate_inp and skinny F32 dispatches to shape, backend, duration and CU count; bound saved served time against current rocBLAS. If material, compare fixed-order two-pass slice reduction with unsplit reference and repeat identical inputs bitwise.

## Sources surfaced

No additional decision-changing source identified.
