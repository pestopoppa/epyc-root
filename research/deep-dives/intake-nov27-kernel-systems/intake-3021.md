# [FlyDSL] [CI] [a16w4] Support MXFP4 weights on gfx942 (CDNA3)

[Primary source](https://github.com/ROCm/aiter/pull/5583) · intake-3021 · 2026-11-27

Merged 2026-09-22 as baef8156a. Allows E2M1 a16w4 kernels to assemble on gfx942 where native gfx950 v_cvt_scalef32_pk_bf16_fp4 is absent, by selecting the byte-LUT helper at build time through rocm_arch. Threading arch through kernel factory/cache key prevents reusing gfx950 build for gfx942, and forcing K16 on gfx950 does not switch decode. Author MI308X/ROCm 7.14 FlyDSL 0.3.2 reports 1792→0 bad instructions on gfx942, 0→0 on gfx950 target assembly, a lifted-byte-identical FlyDSL surrogate gate 3 fail/2 pass→5 pass; author's AITER suite was blocked by an older aiter_core enum mismatch, and gfx950 execution was not checked in those reported results. Three-commit PR adds tuning and removes the development benchmark script from the merge. Blog's later MI300X reported results are a separate source and no AITER on-target CPU/MI210 claim follows.

No gfx90a AITER build is demonstrated. A small native exact scale/packing oracle and ISA comparison can test MI210 dequant if a target served path warrants it. CPU 9655 uses local existing IQK native code; no AITER adoption.

## Evidence

- A compile-time gfx942 branch selects a byte-permute E2M1 decode. [aiter/ops/flydsl/kernels/moe_2stage_a16wmix/utils.py:L811-L814 @ baef815](https://raw.githubusercontent.com/ROCm/aiter/baef8156aa222809e7aa77801f4b7d064ca94149/aiter/ops/flydsl/kernels/moe_2stage_a16wmix/utils.py)
- In the submitted gfx942 GEMM1 assembly comparison the unsupported-instruction count fell from 1792 to 0. [Test Result table](https://github.com/ROCm/aiter/pull/5583)

## Scope and local transfer

PR is direct implementation evidence, from same vendor/author as blog rather than an independent benchmark. It addresses initial gfx942 assembly failure; successor #6144 supersedes implementation details where gfx942 FP8 conversion is available.



Both IQ4 vector dots already call get_int_from_table_16 with HIP permutes; EXL3 codebooks need their own representation proof. Compare emitted permutes, register pressure, waits and MFMA issue for observed IQ4_XS/NL hot shapes; inventory MMQ separately from MMVQ. Require exact nibble/scale/sign reconstruction and an attributable decode bottleneck before moving decode or extending the design to EXL3.

## Sources surfaced

No additional decision-changing source identified.
