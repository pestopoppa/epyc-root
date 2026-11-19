# BLACKFURY Exact (TensorFold patches, Qwen3.8-27B NVFP4 + DFlash2) — deep dive

**Intake:** intake-2674 · **Source:** https://github.com/Maharajahu/qwen3.8-27b-nvfp4-blackfury-exact-tensorfold @ `2790f0472767beb6952ee90de4db6901a97163bb` · **Read depth:** PARTIAL (README, docs/*.md, CREDITS.md, `tf_qmmf_fp4_pair` in `patches/blackfury-stage44-native.patch`; not read: attention-source generator, most of the patch, SSE result files) · **Date:** 2026-11-17

## What it is
A single-author, Apache-2.0 set of patches on TensorFold `6e9af93` (already dived as intake-1924). It serves Qwen3.8-27B NVFP4 with the DFlash2 drafter on one RTX 5090 under Windows. Receipts are hash-bound with an offline verifier, but there is no independent reproduction and rebuilt binaries were not GPU-run.

## Verified, controlled results
| Change | Result | Evidence |
|---|---|---|
| Paired gate+up FP4 GEMV in one 2D launch (separate CTAs, unchanged summation order) | +0.891% warm decode with DFlash2 (306.80 → 309.53 tok/s), +1.835% without drafter; no prefill gain | docs/blackfury-stage44.md, 32 requests A1-B1-B2-A2, identical token IDs |
| Long-context decode attention split into prefix / causal tail / ordered merge; tail grid 8 → 40 blocks, original reduction order | tail kernel 94.59 → 47.90 µs; +4.58% warm decode at 129k+2k | docs/blackfury-exact.md |
| 12 synchronized branches over a shared cached prefix | +34.21% aggregate (570.78 → 766.07 tok/s), identical token IDs | docs/experimental12.md |

The README's +10.20% compares two separately recorded releases with different attention arithmetic. It is not a controlled delta. An inherited prefill race report is still unresolved.

## Portability to our hardware
- **MI210 (gfx90a):** decode FA runs `flash_attn_ext_vec` with no tile dispatch (C10 trace), so exact-order split-KV for long-context single-stream and DFlash2 verify is the main candidate → INF48-FAVEC-TAIL. Gate+up pairing is launch-overhead class and mostly absorbed by the HIP graph → INF48-GATEUP-PROBE (profile first).
- **CPU (EPYC 9655):** the split-KV fixed-order merge idea is already AKX-ALL-LB3. The citation was added there.
- **NVFP4 / FP4:** `GGML_TYPE_NVFP4` already exists in production ffc1bac82 with CPU and HIP mmvq paths. gfx90a has no FP4 hardware; emulation costs a 16-entry lookup plus an E4M3 scale per 16 elements, the same cost shape as IQ4_NL. It is excluded for the architect role (no Q4-class weights on key roles). Knowledge only.

## AutoKernel loop principles
1. Exact-order lane: a bitwise token-ID identity gate replaces the quality eval → INF06-EXACT-LANE.
2. A-B-B-A interleaving with a fresh process per cell; medians of warm runs.
3. A same-binary microbenchmark is not an end-to-end claim.
4. A control that produces different text does not isolate a kernel effect.

## Dispositions
Dive-surfaced sources were declined as already indexed or dived: TensorFold (intake-1924), DFlash2 blog and z-lab/dflash (indexed), and the NVIDIA Qwen3.8-27B-NVFP4 card (format already in tree; sibling intake-756). The synchronized-branch scheduler is knowledge only (serving work, not kernels). The approximate FP8 attention is declined (approximate and SM120-specific).
