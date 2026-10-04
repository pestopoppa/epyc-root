# FOLD.md: KVU-19b, FlashAttention masked-KV skip for BATCHED decode across sequences (`--kv-unified`)

Builds on KVU-19a (`/mnt/raid0/llm/tmp/fa-maskskip-20261003/FOLD.md`). Fold owner: workspace-89 (DS41/AutoKernel lane).
**Not merged into any champion branch. GPU-unvalidated until `gpu_slot2.sh` has run** (no GPU was used for this work).

## What it is

| | |
|---|---|
| branch | `experimental/fa-maskskip-batched-20261004`, pushed to `fork` (github.com/pestopoppa/llama.cpp) |
| base | `a0d0ae238` = tip of `experimental/fa-maskskip-20261003` (KVU-19a, on champion `90c12df42`) |
| commit 1 | `1bceceb05` `ggml-cuda: one query row per block for batched decode across sequences of a unified KV cache`. ggml API `ggml_flash_attn_ext_{set,get}_n_seq` (op_params[4] hint), `src/llama-graph.cpp` sets it to `ubatch.n_seqs_unq` for a single-stream KV with >1 sequence, CUDA/HIP routes "every row a different sequence" batches to the vec kernel with one row per block. Test: 29 `test_flash_attn_ext_unified` cases with the hint. |
| commit 2 | `c7f5ac9ad` `ggml-cuda: WMMA FlashAttention query tiles that follow the sequences of a unified KV cache`. Device planner (`flash_attn_plan_seq_tiles`) + per-tile OR, `tile_rows` kernel argument (WMMA uses it, the other kernels ignore it). Test: 29 cases with several rows per sequence, even and uneven. |
| store builds | `kernels/builds/gpu-20261004-c7f5ac9ad` and `kernels/builds/cpu-20261004-c7f5ac9ad`, same recipes as KVU-19a / champion (gfx90a-house-v1, native-openmp-gcc15-cpu-v1), from `src-store` (clone --shared, detached, clean), `build_store.sh`. |
| runtime knobs | `GGML_CUDA_FA_SEQ_ROWS=0` turns both KVU-19b layouts off (== KVU-19a). `GGML_CUDA_FA_MASK_SKIP=0` / `GGML_CUDA_FA_MASK_SKIP_MIN_KV` as KVU-19a. Arms in one binary: defaults (19b), `SEQ_ROWS=0` (19a), `SEQ_ROWS=0 MASK_SKIP=0` (unpatched kernels + SW-9). |

Commit 2 depends on commit 1 (the hint). Commit 1 depends on KVU-19a commit `ac97e305a`. Fold all three GPU commits
(plus `a0d0ae238` CPU if wanted), in order.

## Design (short; full note `DESIGN.md`)

- Per-tile liveness (19a) cannot skip when one query tile spans several sequences: its live set is the union.
- Batched decode (every row its own sequence) -> vec kernel, one row per block: each row iterates over its own blocks
  only, native q8_0, no FP16 conversion = the `-no-kvu` work. This is where the 444 vs 551 tok/s gap came from.
- Several rows per sequence (drafted verify, decode + prompt chunk) -> WMMA tiles cut at sequence boundaries. WMMA
  cost is per live block per tile, so this only pays where tiles straddled sequences (uneven drafts, mixed batches);
  an aligned 4x8 verify is already at no-kvu cost after 19a. Simulated on the test masks: 36 -> 28 blocks for
  [1,8,8,8] rows, 206 -> 192 for a 512-row mixed batch, unchanged for aligned 4x8.
- Graph-safe: the hint is a function of the ubatch shape (`n_seqs_unq` is in the reuse key; CUDA graphs re-capture on
  op_params changes), grids depend on shapes only, the plan is device data.
- Exactness: routing/tiling never depend on `GGML_CUDA_FA_MASK_SKIP` -> skip on vs off bit-identical. WMMA sequence
  tiles keep each row's arithmetic and KV partition -> bit-identical to `SEQ_ROWS=0`. The vec routing is a kernel
  change for those batches (checked vs CPU reference and test-backend-ops).

## Evidence so far (CPU-side only; nice 19, ionice -c3, taskset 160-183, <= 24 threads)

- Store builds `gpu/cpu-20261004-c7f5ac9ad` (build 10312): linkage PASS, recipes identical to KVU-19a, executable sets match.
- Builds: HIP dev build of each commit compiles clean (only pre-existing warnings); `libggml-hip.so` carries
  `GGML_CUDA_FA_SEQ_ROWS`. CPU dev build clean.
- CPU FA harness v2 (141 cases: the KVU-19a cases + 54 multi-sequence cases with the hint): **141/141 bit-identical**
  (dev build AND store `cpu-20261004-c7f5ac9ad`)
  to the KVU-19a CPU store build `cpu-20261003-a0d0ae238` (CPU ignores the hint). These outputs (`harness/out_cpu`) are
  the reference for the GPU slot.
- llama side (gemma-3-1b, CPU, `p3batch` with `P3_PRINT_HINT=1`): FA hint = 4 in every step graph of a 4-sequence
  kvu batch (decode, 4x8 verify, [1,8,8,8]); 0 for single-sequence prefill; 0 with `kv_unified=false`.
- Planner logic simulated in Python on the test masks (`sim/plan_sim.py`): no tile spans two sequences unless their
  cells share most blocks (where merging is free); never exceeds the slot budget.
- Nothing has run on the GPU. Bit-exactness on GPU, test-backend-ops ROCm0 and all speedups are UNMEASURED.

## GPU slot (needs the main session to release the MI210; small loads, about 3 GiB VRAM, 45-60 min)

`/mnt/raid0/llm/tmp/fa-maskskip-batched-20261004/gpu_slot2.sh` -> `slot2-<ts>/summary.txt`:
1. exactness, harness v2 on ROCm0: on==skipoff, seqoff==alloff, seqoff==k19a all bit-identical; on vs seqoff
   bit-identical except vec-routed cases; every arm vs CPU reference nmse < 5e-4;
2. kernel micro-bench, 27B shape: single-sequence regression rows, and 4 seqs x {16k, 80k} x {1, 8 rows} kvu, uneven
   kvu, and per-sequence streams (the no-kvu target), arms base / k19a / on / seqoff, 3 rounds;
3. `p3batch` gemma-3-1b, 4x16k: draft 1 / 8 / [1,8,8,8], arms k19a / on / seqoff / no-kvu;
4. `llama-batched-bench` -kvu vs -no-kvu, npl 4 (the KVU-19a slot shape; target: on -kvu S_TG ~ -no-kvu 551);
5. `test-backend-ops -o FLASH_ATTN_EXT -b ROCm0`, plus the unified cases with `MIN_KV=0` and with `SEQ_ROWS=0`.

Expectations to falsify: 4x1 kvu kernel time ~ streams time (vs ~2x on k19a); batched-bench -kvu S_TG within ~5% of
-no-kvu; 4x8 aligned on ~ seqoff; [1,8,8,8] on < seqoff; single-sequence rows unchanged vs k19a.

## Production relevance (honest scope)

The :8083 collapse (0.52 tok/s total, 4x80k, `kvu16b/20261004T032520Z`) was measured on v10, which has neither 19a nor
19b, during staggered prefills (first tokens at +181/525/1070 s): mixed prefill+decode ubatches and per-tile unions
over 308k cells. 19a removes most of that (single-sequence and prompt-chunk tiles); 19b removes the remaining
batched-decode cost and straddling tiles. Neither changes the drafter, scheduling or prefill policy; a full-scale
27B re-measurement (P3 harness, needs an exclusive window) is still required before claiming the production number.

## Fold instructions (workspace-89)

```bash
git fetch fork experimental/fa-maskskip-batched-20261004
git cherry-pick ac97e305a a0d0ae238   # KVU-19a (if not folded yet)
git cherry-pick 1bceceb05 c7f5ac9ad   # KVU-19b
```
Gates on the folded candidate: house recipes; `test-backend-ops -o FLASH_ATTN_EXT -b ROCm0` all pass (also with
`GGML_CUDA_FA_MASK_SKIP_MIN_KV=0`); harness exactness as in slot step 1; P3 B (batched-bench -kvu vs -no-kvu) on the 27B.
Trial `git cherry-pick ac97e305a a0d0ae238 1bceceb05 c7f5ac9ad` onto the DS41 accumulator `b3e0b0902` (throwaway
detached worktree, removed, no push): **clean**, all four applied without conflicts. 19b also touches
`src/llama-graph.cpp` and `ggml.h/ggml.c` (outside FA).
