# Do #27870 and #28576 touch a path the champion runs today (ROCWMMA ON)?

2026-10-04, operator question relayed by the coordinator. Static analysis of champion `90c12df42` and the two picks as
applied on `experimental/v11-fa-ab-20261004` (`e9b3b04df`, `5026470c6`).

## What each PR touches

| PR | commit (pick) | files | code path | effect |
|---|---|---|---|---|
| #27870 divergent barrier | `b74f590ea` (`e9b3b04df`) | `fattn-mma-f16.cuh` only (+48/-48) | **MMA kernel only**: the np > 1 parallel-warp meta combine at the end of `flash_attn_ext_f16_process_tile`. Warps with `threadIdx.y % np != 0` now take part in the shuffles and barriers instead of skipping the block. | Every MMA config with np > 1. On CDNA, all D=256 configs have np = 2. |
| #28576 fp32 VKQ on MFMA | `bfdc32183` (`5026470c6`) | `fattn-mma-f16.cuh` only (+5/-3) | **MMA kernel only, MFMA (CDNA) only**: `mma_tile_sizes` `T_C_VKQ` `tile<16,8,half2>` → `tile<16,16,float>` (VKQ accumulators fp16 → fp32), `VKQ_C` array size, and the CDNA config `(64,64,64)` occupancy 4 → 3. | Every MMA kernel compiled for gfx90a. |

Neither touches vec (`fattn-vec.cuh`), TILE (`fattn-tile.cuh`), WMMA (`fattn-wmma-f16.cu`), the dispatcher (`fattn.cu`),
`fattn-common.cuh` or the converters.

## Which kernel the champion (ROCWMMA ON) runs for each of our shapes

`ggml_cuda_get_best_fattn_kernel` (champion `fattn.cu` ~408-605): the WMMA branch catches every head size except
40/72/192/320/512/576 whenever `K->ne[1] % 256 == 0`. It returns vec for ≤ 2 rows and WMMA otherwise. MMA is reachable
on gfx90a only for:
- unpadded KV (`K->ne[1] % 256 != 0`) at D ≤ 128 above 8/16 effective rows;
- D = 192;
- D = 320 at ≤ 3 rows.

D = 256 with unpadded KV goes to TILE (the `99f3fffd6` guard), and D = 512/576 go to TILE.

Is the KV ever unpadded in our serving? No:
- `llama-context.cpp:287-293`: `n_ctx` and `n_ctx_seq` are padded to 256.
- `llama-kv-cache-iswa.cpp:73`: the SWA cache size is padded to 256.
- `llama_kv_cache::get_n_kv` (`llama-kv-cache.cpp:1265-1275`) returns `min(cells.size(), max(256, PAD(used, 256)))`.

So every cache-backed FA op has `K->ne[1] % 256 == 0`.

| our shape (production :8083 = Qwen3.8-27B + DFlash2 drafter) | D, GQA | champion ON runs | v11 / arms B, C run |
|---|---|---|---|
| target decode, 1-2 rows | 256, 6 | vec | vec |
| target 4×1 batched decode, 3-32-row verify (9/18/27) | 256, 6 | WMMA | TILE |
| target 36-row verify, mixed ubatch, 512 prefill | 256, 6 | WMMA | **MMA `<256,256,8,8>`** |
| DFlash2 drafter (`dflash` arch: 5 layers, 32/8 heads, D=128, SWA 2048, iSWA KV cache), 1-2 rows | 128, 4 | vec | vec |
| drafter block (block_size 8 → 9 rows) and its prefill/encode chunks | 128, 4 | WMMA | **MMA** (D ≤ 128 and rows × 4 > 16, i.e. ≥ 5 rows), TILE at 3-4 rows |

**Conclusion: on the ON route the champion runs no MMA kernel for any production shape. Both picks are therefore
irrelevant to the champion as configured today**, and the A+ arm (ON + picks) was skipped as the operator's rule
directs. Their libraries would differ only in MMA device code that the ON champion never launches for these shapes.

Where the picks do matter: the OFF / v11 route. There MMA serves the target's > 32-row shapes and **also the drafter's
9-row block** (D=128 MMA, which the audit did not list). C vs B in the slot answers whether they fix DF2-9 there.
Folding them into the champion now would be behaviour-neutral for current serving, but it would pre-stage v11 code. That
is the operator's call, with no measurement risk on the ON route.

Caveat (outside current serving): cache-less FA graphs, such as vision encoders or rerankers built with
`build_attn_inp_no_cache`, have `K->ne[1] = n_tokens`, i.e. unpadded. On the ON champion they reach MMA at D ≤ 128,
so the picks would matter for such a model on GPU. None is on the MI210 lineup today.
