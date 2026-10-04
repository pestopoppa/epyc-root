<!--
DRAFT ONLY. NEVER post to GitHub or any external service without the operator's explicit go.
This file is a TEMPLATE until gpu_slot_v11fa.sh has run; analyze_slot.py renders it into
<slot_dir>/UPSTREAM-ISSUE-DRAFT.rendered.md. The {{...}} placeholders are filled there, and STATUS
is set by the criteria at the bottom.
-->

STATUS: WARRANTED (criteria met; DRAFT, do not post without operator go)

# HIP / CDNA2 (MI210, gfx90a): FlashAttention after the rocWMMA removal (#26046): D=256 9-27-row batches 1.14-1.24x slower than rocWMMA (TILE); D=128 9-row batches 1.73x slower (MMA)

## Summary

#26046 removed the rocWMMA FlashAttention kernel because "all relevant AMD hardware can use the better kernel in
fattn-mma-f16.cuh". On CDNA2 (MI210, gfx90a), head size 256 now routes as follows (`ggml_cuda_get_best_fattn_kernel`
plus the MMA ncols switches):

| query rows (GQA 6, q8_0 KV) | before #26046 (rocWMMA build) | master |
|---|---|---|
| 1-2 | vec | vec |
| 3-32 | rocWMMA `<256,16,4,64,float>` | **TILE** (no matrix cores) `<256,256,*,2>` |
| > 32 | rocWMMA | MMA `<256,256,8,8>` (64 columns, 512 threads) |

Findings (master vs the rocWMMA build). Slower: single 9 rows, n_kv 16384: 480 -> 549 us (x1.14); single 9 rows, n_kv 131072: 3556 -> 4213 us (x1.18); single 18 rows, n_kv 16384: 798 -> 981 us (x1.23); single 27 rows, n_kv 16384: 796 -> 988 us (x1.24); single 27 rows, n_kv 131072: 6468 -> 7735 us (x1.20); drafter 9 rows, n_kv 2048: 71 -> 122 us (x1.73); drafter 9 rows, n_kv 2304: 72 -> 125 us (x1.73). Faster: single 4 rows, n_kv 16384: x0.61; single 4 rows, n_kv 131072: x0.60; single 36 rows, n_kv 16384: x0.82; single 36 rows, n_kv 131072: x0.49; single 512 rows, n_kv 131072: x0.84; 4x1 4 rows, n_kv 16384: x0.61; 4x1 4 rows, n_kv 131072: x0.60; drafter 64 rows, n_kv 2048: x0.74; drafter 64 rows, n_kv 2304: x0.56.

## Environment

- GPU: AMD Instinct MI210 (gfx90a, CDNA2), 64 GB HBM2e
- ROCm 6.2.0-66 (hipcc / clang from `/opt/rocm`), Linux 6.14.0-37-generic
- llama.cpp master `11fe02151` built with
  `cmake -B build -DGGML_HIP=ON -DAMDGPU_TARGETS=gfx90a -DCMAKE_BUILD_TYPE=Release && cmake --build build -j`
- Comparison build: the same tree before #26046 with `-DGGML_HIP_ROCWMMA_FATTN=ON` (rocWMMA 1.5.0); our downstream tree `90c12df42`, whose CUDA/HIP FA files equal its upstream base `a8dc0e326` plus local patches that do not touch the D=256 path.
- Model shape: Qwen3.x-27B-class attention, head size 256, 24 Q heads / 4 KV heads (GQA 6), q8_0 K/V, `-fa on`.

## Minimal reproduction

Kernel-level, no model needed, using `test-backend-ops` perf mode:
```
./build/bin/test-backend-ops perf -o FLASH_ATTN_EXT -b ROCm0 -p "hsk=256,hsv=256,nh=4,nr23=\[6,1\],kv=16384,nb=9,.*type_KV=q8_0"
```
Our standalone harness (`fa_v11.cpp`, attached) covers the exact shapes (rows 1, 4×1, 9, 18, 27, 36, 512 ×
n_kv 16k/128k, causal mask, prec F32):
```
LD_LIBRARY_PATH=build/bin ./fa_v11 ROCm0 perf
```
End to end:
```
./build/bin/llama-batched-bench -m <27B q4/q8 gguf> -ngl 99 -fa on -ctk q8_0 -ctv q8_0 -kvu -npp 2048 -ntg 128 -npl 1,2,4
```
Non-finite check (DF2-9; only if reproduced on master): not reproduced

## Numbers

Median of 3 alternating rounds, µs per FA op (lower is better); ratio = master / rocWMMA.

| shape | n_kv | rocWMMA (A) us | master us | master/A | TILE/MMA route on master |
|---|---|---|---|---|---|
| single 1 rows | 16384 | 264.0 | 264.3 | 1.00 | vec |
| single 1 rows | 131072 | 1982.7 | 1983.8 | 1.00 | vec |
| single 4 rows | 16384 | 456.4 | 278.0 | 0.61 | TILE |
| single 4 rows | 131072 | 3463.0 | 2070.2 | 0.60 | TILE |
| single 9 rows | 16384 | 480.4 | 549.0 | 1.14 | TILE |
| single 9 rows | 131072 | 3556.5 | 4212.8 | 1.18 | TILE |
| single 18 rows | 16384 | 797.6 | 980.8 | 1.23 | TILE |
| single 18 rows | 131072 | 7248.9 | 7730.2 | 1.07 | TILE |
| single 27 rows | 16384 | 796.0 | 988.1 | 1.24 | TILE |
| single 27 rows | 131072 | 6468.0 | 7735.0 | 1.20 | TILE |
| single 36 rows | 16384 | 1192.6 | 979.5 | 0.82 | MMA |
| single 36 rows | 131072 | 11449.3 | 5603.7 | 0.49 | MMA |
| single 512 rows | 16384 | 10578.3 | 9554.7 | 0.90 | MMA |
| single 512 rows | 131072 | 86439.6 | 72310.4 | 0.84 | MMA |
| 4x1 4 rows | 16384 | 456.6 | 277.5 | 0.61 | TILE |
| 4x1 4 rows | 131072 | 3459.6 | 2066.9 | 0.60 | TILE |
| drafter 1 rows | 2048 | 40.1 | 40.5 | 1.01 | vec |
| drafter 1 rows | 2304 | 42.1 | 41.5 | 0.99 | vec |
| drafter 9 rows | 2048 | 70.6 | 121.9 | 1.73 | MMA |
| drafter 9 rows | 2304 | 72.5 | 125.3 | 1.73 | MMA |
| drafter 64 rows | 2048 | 250.2 | 184.4 | 0.74 | MMA |
| drafter 64 rows | 2304 | 328.9 | 185.5 | 0.56 | MMA |

| check | rocWMMA (A) | master |
|---|---|---|
| server DF2-9 reproducer | pass | n/a (not run) |
| model FA probe | pass | n/a (not run) |
| op harness non-finite cases | 4 | 6 |

## Register pressure: the 64-column D=256 MMA config spills on gfx90a

How we measured: we split `libggml-hip.so` on `__CLANG_OFFLOAD_BUNDLE__`, ran `clang-offload-bundler --unbundle --type=o
--targets=hipv4-amdgcn-amd-amdhsa--gfx90a` on each piece, then read `llvm-readelf --notes` (AMDHSA kernel metadata:
`.vgpr_count`, `.agpr_count`, `.vgpr_spill_count`, `.private_segment_fixed_size`). The script is attached.

| build | kernel | VGPR | AGPR | VGPR spill | SGPR spill | LDS | scratch B |
|---|---|---|---|---|---|---|---|
| gpu-20261004-90c12df42-A | flash_attn_ext_f16<256, 256, 8, 8, false, false> | 256 | 0 | 190 | 30 | 0 | 696 |
| gpu-20261004-90c12df42-A | flash_attn_ext_f16<256, 256, 16, 2, false, false> | 499 | 243 | 0 | 24 | 0 | 0 |
| gpu-20261004-90c12df42-A | flash_attn_ext_f16<256, 256, 32, 2, false, false> | 256 | 0 | 314 | 26 | 0 | 1040 |
| gpu-20261004-90c12df42-A | flash_attn_ext_f16<256, 256, 4, 8, false, false> | 512 | 256 | 67 | 26 | 0 | 272 |
| gpu-20261004-90c12df42-A | flash_attn_ext_f16<256, 256, 8, 2, false, false> | 414 | 158 | 0 | 21 | 0 | 0 |
| gpu-20261004-90c12df42-A | flash_attn_ext_f16<256, 16, 4, 64, float, false> | 192 | 16 | 0 | 0 | 25344 | 0 |
| gpu-20261004-90c12df42-A | flash_attn_tile<256, 256, 16, 2, false> | 37 | 0 | 0 | 0 | 0 | 16 |
| gpu-20261004-90c12df42-A | flash_attn_tile<256, 256, 8, 2, false> | 37 | 0 | 0 | 0 | 0 | 16 |
| gpu-20261004-90c12df42-B | flash_attn_ext_f16<256, 256, 8, 8, false, false> | 256 | 0 | 190 | 30 | 0 | 696 |
| gpu-20261004-90c12df42-B | flash_attn_ext_f16<256, 256, 16, 2, false, false> | 499 | 243 | 0 | 24 | 0 | 0 |
| gpu-20261004-90c12df42-B | flash_attn_ext_f16<256, 256, 32, 2, false, false> | 256 | 0 | 314 | 26 | 0 | 1040 |
| gpu-20261004-90c12df42-B | flash_attn_ext_f16<256, 256, 4, 8, false, false> | 512 | 256 | 67 | 26 | 0 | 272 |
| gpu-20261004-90c12df42-B | flash_attn_ext_f16<256, 256, 8, 2, false, false> | 414 | 158 | 0 | 21 | 0 | 0 |
| gpu-20261004-90c12df42-B | flash_attn_ext_f16<256, 16, 4, 64, float, false> | 37 | 0 | 0 | 0 | 0 | 16 |
| gpu-20261004-90c12df42-B | flash_attn_tile<256, 256, 16, 2, false> | 220 | 0 | 0 | 0 | 27136 | 0 |
| gpu-20261004-90c12df42-B | flash_attn_tile<256, 256, 8, 2, false> | 160 | 0 | 0 | 0 | 17920 | 0 |
| gpu-20261004-5026470c6-C | flash_attn_ext_f16<256, 256, 8, 8, false, false> | 256 | 0 | 215 | 30 | 0 | 780 |
| gpu-20261004-5026470c6-C | flash_attn_ext_f16<256, 256, 16, 2, false, false> | 512 | 256 | 209 | 40 | 0 | 840 |
| gpu-20261004-5026470c6-C | flash_attn_ext_f16<256, 256, 32, 2, false, false> | 256 | 0 | 285 | 27 | 0 | 908 |
| gpu-20261004-5026470c6-C | flash_attn_ext_f16<256, 256, 4, 8, false, false> | 512 | 256 | 104 | 27 | 0 | 420 |
| gpu-20261004-5026470c6-C | flash_attn_ext_f16<256, 256, 8, 2, false, false> | 512 | 256 | 0 | 49 | 0 | 0 |
| gpu-20261004-5026470c6-C | flash_attn_ext_f16<256, 16, 4, 64, float, false> | 37 | 0 | 0 | 0 | 0 | 16 |
| gpu-20261004-5026470c6-C | flash_attn_tile<256, 256, 16, 2, false> | 220 | 0 | 0 | 0 | 27136 | 0 |
| gpu-20261004-5026470c6-C | flash_attn_tile<256, 256, 8, 2, false> | 160 | 0 | 0 | 0 | 17920 | 0 |
| gpu-20261004-fa5ebc0c8-D | flash_attn_ext_f16<256, 256, 8, 8, false, false> | 256 | 0 | 215 | 30 | 0 | 780 |
| gpu-20261004-fa5ebc0c8-D | flash_attn_ext_f16<256, 256, 16, 2, false, false> | 512 | 256 | 209 | 40 | 0 | 840 |
| gpu-20261004-fa5ebc0c8-D | flash_attn_ext_f16<256, 256, 32, 2, false, false> | 256 | 0 | 285 | 27 | 0 | 908 |
| gpu-20261004-fa5ebc0c8-D | flash_attn_ext_f16<256, 256, 4, 8, false, false> | 512 | 256 | 104 | 27 | 0 | 420 |
| gpu-20261004-fa5ebc0c8-D | flash_attn_ext_f16<256, 256, 8, 2, false, false> | 512 | 256 | 0 | 49 | 0 | 0 |
| gpu-20261004-fa5ebc0c8-D | flash_attn_ext_f16<256, 16, 4, 64, float, false> | 37 | 0 | 0 | 0 | 0 | 16 |
| gpu-20261004-fa5ebc0c8-D | flash_attn_tile<256, 256, 16, 2, false> | 220 | 0 | 0 | 0 | 27136 | 0 |
| gpu-20261004-fa5ebc0c8-D | flash_attn_tile<256, 256, 8, 2, false> | 160 | 0 | 0 | 0 | 17920 | 0 |
| build-master-11fe02151 | flash_attn_ext_f16<256, 256, 8, 8, false, false, false> | 256 | 0 | 197 | 29 | 0 | 740 |
| build-master-11fe02151 | flash_attn_ext_f16<256, 256, 16, 2, false, false, false> | 512 | 256 | 91 | 40 | 0 | 368 |
| build-master-11fe02151 | flash_attn_ext_f16<256, 256, 32, 2, false, false, false> | 256 | 0 | 330 | 25 | 0 | 1176 |
| build-master-11fe02151 | flash_attn_ext_f16<256, 256, 4, 8, false, false, false> | 512 | 256 | 79 | 25 | 0 | 320 |
| build-master-11fe02151 | flash_attn_ext_f16<256, 256, 8, 2, false, false, false> | 489 | 233 | 0 | 16 | 0 | 0 |
| build-master-11fe02151 | flash_attn_tile<256, 256, 16, 2, false> | 220 | 0 | 0 | 0 | 27136 | 0 |
| build-master-11fe02151 | flash_attn_tile<256, 256, 8, 2, false> | 160 | 0 | 0 | 0 | 17920 | 0 |

In `ggml_cuda_fattn_mma_get_config_cdna` the 64-column D=256 config runs 512 threads, i.e. 2 waves per SIMD. On gfx90a's
unified VGPR/AGPR file that caps each wave at 256 registers. The 32-column configs (256 threads, 1 wave per SIMD, 512
registers) fit only with fp16 VKQ: `<256,256,16,2>` uses 499 registers with 0 spills before #28576, but spills again
once #28576 makes the VKQ accumulators fp32 (91 VGPRs on master, 209 on our tree + #28576). With fp32 VKQ only the
16-column configs are spill-free (`<256,256,8,2>`: 0 spills on master and on our tree). Note that for GQA 6, CDNA picks
ncols2 = 8 (`gqa_ratio > 4`), so prefill runs `<256,256,8,8>` with 2 of 8 head columns idle, while RDNA/TILE pick
ncols2 by divisibility (2). A divisibility-based ncols2 plus a 16-column cap on CDNA D=256 is a ~30-line change
(our arm D, with the 32-column variant behind an env knob). Our measurement of it:
D single 9r 16384kv x1.14 vs A; D32 single 9r 16384kv x1.14 vs A; D9 single 9r 16384kv x1.35 vs A; D single 9r 131072kv x1.18 vs A; D32 single 9r 131072kv x1.18 vs A; D9 single 9r 131072kv x1.37 vs A; D single 36r 16384kv x1.17 vs A; D32 single 36r 16384kv x0.89 vs A; D9 single 36r 16384kv x1.17 vs A; D single 36r 131072kv x1.02 vs A; D32 single 36r 131072kv x0.53 vs A; D9 single 36r 131072kv x1.02 vs A; D single 512r 16384kv x1.16 vs A; D32 single 512r 16384kv x0.97 vs A; D9 single 512r 16384kv x1.16 vs A; D single 512r 131072kv x1.12 vs A; D32 single 512r 131072kv x0.92 vs A; D9 single 512r 131072kv x1.12 vs A; D drafter 9r 2048kv x1.86 vs A; D32 drafter 9r 2048kv x1.86 vs A; D9 drafter 9r 2048kv x1.85 vs A; D drafter 9r 2304kv x1.79 vs A; D32 drafter 9r 2304kv x1.79 vs A; D9 drafter 9r 2304kv x1.81 vs A

## Possible directions

- Lower the MFMA crossover for D=256 on CDNA (MMA `<8,2>`/`<16,2>` for 9-32 rows instead of TILE), or keep a
  matrix-core path for that band.
- Cap D=256 MMA at 32 columns on CDNA, and/or use ncols2 by divisibility.
- n/a

<!-- Criteria applied by analyze_slot.py:
WARRANTED if at least one holds:
  (N) master produces non-finite FA outputs / target features / logits in the DF2-9 reproducer, the model probe or the
      harness nan mode, in a case where the rocWMMA build (arm A) is finite; or
  (P) on at least one verify/decode/prefill shape, master's median µs is >= 1.10x arm A's median, and the slowest master round
      is still slower than the fastest arm A round (separated beyond the round-to-round spread).
Otherwise: STATUS: NOT WARRANTED (master as shipped is neither broken nor slower on MI210 for these shapes).
-->
