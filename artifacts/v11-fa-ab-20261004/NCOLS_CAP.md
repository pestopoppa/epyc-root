# ncols cap for the D=256 MMA FlashAttention kernel on CDNA2 (gfx90a)

2026-10-04, v11 FA routing A/B (workspace-ec plan). Source read: champion `90c12df42`, arm C `5026470c6`, upstream master `11fe02151`.
Register numbers come from the gfx90a code objects inside each `libggml-hip.so`, via `fa_codeobj_audit.py`, which splits the
`__CLANG_OFFLOAD_BUNDLE__` bundles, runs `clang-offload-bundler --unbundle` for gfx90a, and reads
`llvm-readelf --notes` for `.vgpr_count`, `.agpr_count`, `.vgpr_spill_count`, `.private_segment_fixed_size`.

## Correction to the audit: which config the 27B actually runs

The audit (`v11-fa-path-audit-20261004/REPORT.md` §0.3) names `<256,256,32,2>` as the prefill kernel. For the 27B
(24 Q heads / 4 KV heads, GQA 6) **that is not the kernel CDNA selects**:

- `ggml_cuda_flash_attn_ext_mma_f16_switch_ncols2` (`ggml/src/ggml-cuda/fattn.cu`; champion lines ~140-156, master ~266-282).
  Only Volta and RDNA (`amd_wmma_available`) pick ncols2 by divisibility. CDNA takes the generic ladder
  `gqa_ratio > 4 -> 8`, `> 2 -> 4`, `> 1 -> 2`. So GQA 6 -> **ncols2 = 8** (8 head columns per block, 6 real: 25% of the
  Q columns are padding).
- `ggml_cuda_flash_attn_ext_mma_f16_switch_ncols1<256,256,8>`: rows <= 2 -> `<2,8>`, rows <= 4 -> `<4,8>`, otherwise
  the final line `ggml_cuda_flash_attn_ext_mma_f16_case<DKQ, DV, 64/ncols2, ncols2>` -> **`<256,256,8,8>`** (64 columns).
- MMA is only reached on CDNA for D=256 when `rows * gqa_ratio_eff > 64` (`ggml_cuda_get_best_fattn_kernel`;
  `gqa_ratio_eff` = 2 for GQA 6, i.e. > 32 rows). So for every MMA shape the 27B produces (4-slot verify = 36 rows,
  mixed ubatches, 512-row prefill) v11 runs `<256,256,8,8>`.
- `gqa_ratio_eff = 2` is used only for this crossover threshold, not for the launch. The audit's `ncols2=2` is the
  RDNA/TILE choice: the TILE kernel's `launch_fattn_tile_switch_ncols2` does use divisibility, so 3-32-row verify runs
  TILE `<256,256,*,2>`.
- `<256,256,32,2>` is what a GQA-2 D=256 model would run (and what RDNA would run for GQA 6).

The config row is the same in champion, C and master (`ggml_cuda_fattn_mma_get_config_cdna`, `fattn-mma-f16.cuh`
~line 210-216):

```
GGML_CUDA_FATTN_MMA_CONFIG_CASE(256, 256,  8, 256, 1, 64, 128, 128, 128, 1, true);
GGML_CUDA_FATTN_MMA_CONFIG_CASE(256, 256, 16, 256, 1, 64, 128, 128, 128, 1, true);
GGML_CUDA_FATTN_MMA_CONFIG_CASE(256, 256, 32, 256, 1, 64, 128, 128, 128, 1, true);
GGML_CUDA_FATTN_MMA_CONFIG_CASE(256, 256, 64, 512, 1, 64, 128, 128,  64, 1, true);   // <- 64 columns, 512 threads
```

512 threads = 8 waves of 64 on 4 SIMDs = 2 waves per SIMD. On gfx90a the VGPR and AGPR files are unified (512 per lane
per SIMD), so each wave is capped at 256 registers. The 32-column configs run 256 threads (1 wave per SIMD) and can use 512.

## Champion v10 compile (ROCm 6.2), every D=256 MMA config the 27B can hit

From `audit-champion-90c12df42/fa_kernels.tsv` (`false,false` = no softcap, K≠V view):

| config | columns | threads | VGPR | AGPR | VGPR spilled | scratch B/lane | used by the 27B on v11 when |
|---|---|---|---|---|---|---|---|
| `<256,256,2,8>`  | 16 | 256 | 418 | 162 | 0   | 0    | (≤ 2 rows: vec is chosen instead) |
| `<256,256,4,8>`  | 32 | 256 | 512 | 256 | 67  | 272  | (≤ 4 rows: TILE is chosen instead) |
| **`<256,256,8,8>`** | **64** | **512** | **256** | **0** | **190** | **696** | **36-row verify, mixed, 512 prefill** |
| `<256,256,8,2>`  | 16 | 256 | 414 | 158 | 0   | 0    | — |
| `<256,256,16,2>` | 32 | 256 | 499 | 243 | 0   | 0    | — (patch D) |
| `<256,256,32,2>` | 64 | 512 | 256 | 0   | 314 | 1040 | — (GQA-2 models / RDNA) |

C (`+#28576`, fp32 VKQ on MFMA) and master: see the per-arm tables below. #28576 makes the VKQ accumulators twice as wide
(`tile<16,16,float>` instead of `tile<16,8,half2>`), so expect more pressure, not less.

## What the cap changes (patch D: `2e0f9dd06` + `fa5ebc0c8`, arm D build `gpu-20261004-fa5ebc0c8-D`)

Patch D (`src-d`, branch `experimental/v11-fa-ab-20261004`, `ggml/src/ggml-cuda/fattn.cu`, +85/-3) does three things.
The first cut (`2e0f9dd06`) capped at 32 columns. The arm C/D register audit (below) showed the 32-column config
still spills with #28576, so `fa5ebc0c8` makes 16 the default, with `GGML_CUDA_FA_CDNA_D256_MAX_COLS=32` as the
alternative. The text in items 1-3 describes the first cut; with the default cap of 16, GQA 6 runs `<256,256,8,2>`
for every MMA block.

1. **ncols2 by divisibility on CDNA D=256** (8/4/2, else the upstream ladder): GQA 6 -> ncols2 = 2. That removes the 2
   idle head columns of every block, a 25% compute waste on Q columns.
2. **At most 32 columns per block on CDNA D=256** (`switch_ncols1`: the 32/ncols2 branch also fires for
   `DKQ == 256 && amd_mfma_available && tune`). GQA 6 -> rows <= 8 `<8,2>`, otherwise **`<256,256,16,2>`**:
   1 wave/SIMD, 499 registers, **0 spills** (v10 compile).
3. **Optional crossover knob** `GGML_CUDA_FA_CDNA_D256_MMA_MIN_ROWS=n` (n >= 3, off by default): D=256 takes MMA from
   n rows on, so the same binary measures MMA `<8,2>`/`<16,2>` against TILE in the 9-32-row DFlash2 verify band.
   Padded KV only (keeps the `99f3fffd6` unpadded-KV -> TILE guard).

`GGML_CUDA_FA_CDNA_D256_TUNE=0` restores upstream selection exactly. The binary is its own control, as with
`GGML_CUDA_FA_MASK_SKIP`.

Expected effects (UNMEASURED until the slot):
- 512-row prefill: removes 190 spilled VGPRs (696 B scratch per lane) and the 25% column waste.
- What it costs: half the Q columns per block means K/V tiles are re-read twice as often per query row (16 rows × 2 heads
  per block vs 8 × 8). On a bandwidth-light, compute-heavy prefill that is normally the better trade.
- 36-row verify: `<16,2>` gives 3 blocks of 16 rows (the last one 4/16 used) vs `<8,8>`'s 5 blocks of 8 rows; both waste.
- With `MIN_ROWS=9`, 9-row verify runs `<16,2>` (9 of 16 rows used) on MFMA instead of TILE on the vector ALUs.

Not done: the per-band crossover should be picked by measurement (slot step b runs D with and without `MIN_ROWS=9`).
`(256,256,64)` with 256 threads (np = 1) is the alternative the audit mentions. It is not implemented, because it changes
the np=2 code path and needs a separate correctness pass.

## Per-arm register tables (filled after the builds)

Cells: VGPR / AGPR / **VGPR spilled** / scratch B per lane (no softcap; master has one extra template bool).

| config | cols | A champion ON | B champion OFF | C B+#27870+#28576 | M upstream master 11fe02151 |
|---|---|---|---|---|---|
| `<256,256,8,8>` | 64 | 256/0/**190**/696 | 256/0/**190**/696 | 256/0/**215**/780 | 256/0/**197**/740 |
| `<256,256,16,2>` | 32 | 499/243/**0**/0 | 499/243/**0**/0 | 512/256/**209**/840 | 512/256/**91**/368 |
| `<256,256,32,2>` | 64 | 256/0/**314**/1040 | 256/0/**314**/1040 | 256/0/**285**/908 | 256/0/**330**/1176 |
| `<256,256,8,2>` | 16 | 414/158/**0**/0 | 414/158/**0**/0 | 512/256/**0**/0 | 489/233/**0**/0 |
| `<256,256,4,4>` | 16 | 412/156/**0**/0 | 412/156/**0**/0 | 512/256/**19**/80 | 509/253/**0**/0 |
| `<256,256,4,8>` | 32 | 512/256/**67**/272 | 512/256/**67**/272 | 512/256/**104**/420 | 512/256/**79**/320 |

**Finding:** #28576 (fp32 VKQ) moves the spill boundary. Without it (A/B), the 32-column `<16,2>` fits (0 spills).
With it (C, and master), `<16,2>` spills: 209 VGPRs on our tree, 91 on master. Upstream's prefill config `<8,8>`
spills 215/197. **Only the 16-column `<8,2>` is spill-free with fp32 VKQ.** Hence patch D's second commit
`fa5ebc0c8`: the default cap is now 16 columns, and `GGML_CUDA_FA_CDNA_D256_MAX_COLS=32` keeps the first cut's 32.
The trade-off: 8 query rows × 2 heads per block means K/V is read 2× more often per query row than with `<16,2>`, and
4× more than with `<8,8>`. The slot measures it (perf labels D, D32, D9).
