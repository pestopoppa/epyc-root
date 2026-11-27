# Bringing MXFP4 MoE to AMD Instinct MI300 Series GPUs with FlyDSL

[Primary source](https://rocm.blogs.amd.com/artificial-intelligence/gfx942-moe-mxfp4/README.html) · intake-3007 · 2026-11-27

AMD measured AITER a16w4 GEMM1 and GEMM2 on one MI300X, E=896/model_dim=3584/inter_dim=384/topk=16, BF16 activation+SwiGLU, synthetic Gaussian weights/inputs and random routing, forcing BF16 activations across token counts. SQ/ATT/source lines identified E2M1 decode as the dominant issue cost. The gfx942 LUT uses four v_perm_b32 byte lookups plus eight interleaves per eight weights, restores signs and scales with E8M0 via f32 multiply and truncation. RX-independent developmental software baseline was never merged. Seven token points from 1 to 8192: GEMM1 2.2–2.4x and GEMM2 1.7–2.5x, kernel times only, latest smaller gain for GEMM2 as dependency waits surface. Bit check: GEMM2 one-hot readback checked 22,020,096 weights, all 64,768 byte/scale pairs, finite scales 0x00–0xFC, nonzeros bit-identical to reference; -0 sign unobservable and 0x00 flushed to zero in both, leaving 76,208 departures from the mathematical reference; FD–FF excluded. #6144 replaces most byte permutes with FP8 convert (gfx942) and #8184 proposes 21 vs 28 VALU instructions; neither is an independent corroboration of the blog baseline.

handoffs/active/rocm-kernel-authoring.md:L2588-L2598 @ b93bd31 documents live CPU/GPU MXFP4 scale semantics; handoffs/active/cpu-decode-roofline-program.md:L251 @ b93bd31 owns XFER-4b. MI210 can port plain byte-LUT logic into the actual GGUF gfx90a dequant family if trace/ISA shows relevant compute cost on MXFP4 expert paths. Existing GPU and CPU code use different equivalent scale forms except 0xFF, making the native oracle and full local scale semantics mandatory. AITER's gfx942-specific FlyDSL runtime or FP8 convert isn't a source of target speed; EPYC 9655 can reconsider LUT/SIMD only inside native iqk if current CPU prefill exposes a decode bottleneck. Served read bandwidth stays the same.

Local source check at frozen ffc1bac82: ggml/src/ggml-cuda/vecdotq.cuh:34 implements the HIP table with AMD byte permutes; both IQ4 vector-dot functions call it. The open question is placement and instructions on the active path. This observation does not establish optimized EXL3 decode.

## Evidence

- At the tested MI300X geometry, against the reference software decode, the LUT sped up GEMM1 by 2.2×–2.4× and GEMM2 by 1.7×–2.5×. [Summary, HTML L1475](https://rocm.blogs.amd.com/artificial-intelligence/gfx942-moe-mxfp4/README.html)
- The performance comparator was a same-call-site development implementation absent from shipped AITER. [Limitations, HTML L1461](https://rocm.blogs.amd.com/artificial-intelligence/gfx942-moe-mxfp4/README.html)
- Nonzero decoded weights matched the software decoder bit for bit in the one-hot GEMM2 readback. [Checking Bit-Exactness on MI300X, HTML L1238](https://rocm.blogs.amd.com/artificial-intelligence/gfx942-moe-mxfp4/README.html)
- The reported speedups cover GEMMs alone. [Limitations, HTML L1462](https://rocm.blogs.amd.com/artificial-intelligence/gfx942-moe-mxfp4/README.html)

## Scope and local transfer

The AMD Limitations section narrows the headline. AITER release lineage corroborates implementation and supersedes this baseline, while indexed relays repeat AMD's result. No independent MI210/9655 reproduction found.



Both IQ4 vector dots already call get_int_from_table_16 with HIP permutes; EXL3 codebooks need their own representation proof. Compare emitted permutes, register pressure, waits and MFMA issue for observed IQ4_XS/NL hot shapes; inventory MMQ separately from MMVQ. Require exact nibble/scale/sign reconstruction and an attributable decode bottleneck before moving decode or extending the design to EXL3.

## Sources surfaced

- https://github.com/ROCm/aiter/pull/5583
