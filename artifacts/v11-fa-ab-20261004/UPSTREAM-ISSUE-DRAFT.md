<!--
DRAFT ONLY. NEVER post to GitHub or any external service without the operator's explicit go.
This file is a TEMPLATE until gpu_slot_v11fa.sh has run; analyze_slot.py renders it into
<slot_dir>/UPSTREAM-ISSUE-DRAFT.rendered.md. The {{...}} placeholders are filled there, and STATUS
is set by the criteria at the bottom.
-->

STATUS: {{STATUS}}

# HIP / CDNA2 (MI210, gfx90a): D=256 FlashAttention after the rocWMMA removal (#26046): {{HEADLINE}}

## Summary

#26046 removed the rocWMMA FlashAttention kernel because "all relevant AMD hardware can use the better kernel in
fattn-mma-f16.cuh". On CDNA2 (MI210, gfx90a), head size 256 now routes as follows (`ggml_cuda_get_best_fattn_kernel`
plus the MMA ncols switches):

| query rows (GQA 6, q8_0 KV) | before #26046 (rocWMMA build) | master |
|---|---|---|
| 1-2 | vec | vec |
| 3-32 | rocWMMA `<256,16,4,64,float>` | **TILE** (no matrix cores) `<256,256,*,2>` |
| > 32 | rocWMMA | MMA `<256,256,8,8>` (64 columns, 512 threads) |

{{FINDINGS_PARAGRAPH}}

## Environment

- GPU: AMD Instinct MI210 (gfx90a, CDNA2), {{GPU_INFO}}
- ROCm {{ROCM_VERSION}} (hipcc / clang from `/opt/rocm`), Linux {{KERNEL}}
- llama.cpp master `{{MASTER_SHA}}` built with
  `cmake -B build -DGGML_HIP=ON -DAMDGPU_TARGETS=gfx90a -DCMAKE_BUILD_TYPE=Release && cmake --build build -j`
- Comparison build: the same tree before #26046 with `-DGGML_HIP_ROCWMMA_FATTN=ON` (rocWMMA 1.5.0); our downstream tree `{{CHAMPION_SHA}}`, whose CUDA/HIP FA files equal its upstream base `a8dc0e326` plus local patches that do not touch the D=256 path.
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
Non-finite check (DF2-9; only if reproduced on master): {{NAN_REPRO_COMMAND}}

## Numbers

Median of 3 alternating rounds, µs per FA op (lower is better); ratio = master / rocWMMA.

{{PERF_TABLE}}

{{NAN_TABLE}}

## Register pressure: the 64-column D=256 MMA config spills on gfx90a

How we measured: we split `libggml-hip.so` on `__CLANG_OFFLOAD_BUNDLE__`, ran `clang-offload-bundler --unbundle --type=o
--targets=hipv4-amdgcn-amd-amdhsa--gfx90a` on each piece, then read `llvm-readelf --notes` (AMDHSA kernel metadata:
`.vgpr_count`, `.agpr_count`, `.vgpr_spill_count`, `.private_segment_fixed_size`). The script is attached.

{{REGISTER_TABLE}}

In `ggml_cuda_fattn_mma_get_config_cdna` the 64-column D=256 config runs 512 threads, i.e. 2 waves per SIMD. On gfx90a's
unified VGPR/AGPR file that caps each wave at 256 registers. The 32-column configs (256 threads, 1 wave per SIMD, 512
registers) fit only with fp16 VKQ: `<256,256,16,2>` uses 499 registers with 0 spills before #28576, but spills again
once #28576 makes the VKQ accumulators fp32 (91 VGPRs on master, 209 on our tree + #28576). With fp32 VKQ only the
16-column configs are spill-free (`<256,256,8,2>`: 0 spills on master and on our tree). Note that for GQA 6, CDNA picks
ncols2 = 8 (`gqa_ratio > 4`), so prefill runs `<256,256,8,8>` with 2 of 8 head columns idle, while RDNA/TILE pick
ncols2 by divisibility (2). A divisibility-based ncols2 plus a 16-column cap on CDNA D=256 is a ~30-line change
(our arm D, with the 32-column variant behind an env knob). Our measurement of it:
{{PATCH_D_SUMMARY}}

## Possible directions

- Lower the MFMA crossover for D=256 on CDNA (MMA `<8,2>`/`<16,2>` for 9-32 rows instead of TILE), or keep a
  matrix-core path for that band.
- Cap D=256 MMA at 32 columns on CDNA, and/or use ncols2 by divisibility.
- {{EXTRA_DIRECTION}}

<!-- Criteria applied by analyze_slot.py:
WARRANTED if at least one holds:
  (N) master produces non-finite FA outputs / target features / logits in the DF2-9 reproducer, the model probe or the
      harness nan mode, in a case where the rocWMMA build (arm A) is finite; or
  (P) on at least one verify/decode/prefill shape, master's median µs is >= 1.10x arm A's median, and the slowest master round
      is still slower than the fastest arm A round (separated beyond the round-to-round spread).
Otherwise: STATUS: NOT WARRANTED (master as shipped is neither broken nor slower on MI210 for these shapes).
-->
