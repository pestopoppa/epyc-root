# KVU-19b design note: per-sequence KV iteration for batched FlashAttention on `--kv-unified`

Branch `experimental/fa-maskskip-batched-20261004` (on top of KVU-19a `experimental/fa-maskskip-20261003`):
`1bceceb05` (hint + vec one-row-per-block routing) and `c7f5ac9ad` (WMMA sequence-aligned query tiles).

**Decision: option (b), in two pieces, plus a shape-only graph hint.** (a) needs host knowledge the backend does not
have without a sync; (c) is a KV-cache redesign. Expected effect: batched decode (every row its own sequence) drops to
the no-kvu work; drafted verify gains only where tiles straddled sequences (aligned 4x8 is already at no-kvu cost after
KVU-19a — see the cost model).

## Problem

KVU-19a decides liveness per query TILE: a 256-cell KV block is skipped when every row of the tile has -INF over it.
When one ubatch carries rows of several sequences, a tile spans several sequences and its live set is the union of
their cells, so nothing is skipped. On the MI210 for D=256 q8_0 (the 27B, gemma-3) the kernel choice makes this worse:

| batch | kernel today | what it costs |
|---|---|---|
| batched decode, 4 seqs x 1 row | WMMA, one 16-column tile, q8_0->f16 conversion of every live cell | the union of all 4 sequences in f16 (2 B/elem) plus the conversion (read 1.06 + write 2 B/elem), 12 of 16 columns empty |
| no-kvu reference, same batch | vec, one row per block, native q8_0 | each row reads only its own cells (1.06 B/elem) |

That is why `llama-batched-bench` 4x decode gave S_TG 444 (kvu) vs 551 (no-kvu) on the KVU-19a build: the bytes moved
per step differ by about 2x on the attention part, and the per-tile skip cannot help because the tile IS the union.

## Cost model that decided the design

- WMMA cost per tile is proportional to the number of live KV blocks it iterates, independent of how many of its
  columns are real. So for WMMA, splitting a merged tile (A+B) into per-sequence tiles (A),(B) leaves the total work
  `|A|+|B|` unchanged when the sequences' rows are contiguous and aligned to the tile width. It only saves work when a
  tile STRADDLES sequences unevenly (e.g. rows [A:1][B:8][C:8][D:8] in 16-wide tiles: A+B+2C+D -> A+B+C+D).
- The large win is for batched decode (every row a different sequence): switch from WMMA to the vec kernel with one
  query row per block. Each row then iterates only over its own blocks via the KVU-19a scan (with ncols1=1 the
  per-tile flags ARE per-row flags), in native q8_0, with no conversion pass. That is exactly the no-kvu work.

## Options evaluated

- **(a) split the launch per sequence on the host**: needs the row -> sequence map on the host. The mask is device
  data; reading it back means a sync per FA op and breaks CUDA/HIP graphs. Rejected as stated. Kept its useful part:
  the host only needs a SHAPE-level fact (how many sequences share the rows) to pick the kernel, see the hint below.
- **(b) per-row block lists in the kernels**: adopted in two pieces.
  1. vec: one query row per block (`cols_per_block=1`) when every row is a different sequence. No kernel change at all.
  2. WMMA: query tiles that never span two sequences, planned on the device (`flash_attn_plan_seq_tiles`): a per-row
     scan, a one-block planner (row r starts a new segment when r and r-1 share less than half of the smaller live
     set), and the OR of each tile's rows. The kernel reads `(first row, n rows)` from `tile_rows`; empty slots exit.
     The grid is a function of shapes only (`ntiles_plain + n_seq - 1` slots), so CUDA/HIP graphs stay valid.
- **(c) reorder/compact KV per sequence**: changes the KV cache layout and every backend (that is upstream draft
  #29510's territory). Out of scope for a kernel patch.

## The hint (the one non-kernel change)

`ggml_flash_attn_ext_set_n_seq(op, n)` stores in `op_params[4]` how many distinct sequences share the query rows
(0 = unknown). `llama-graph.cpp` sets it to `ubatch.n_seqs_unq` when the KV has one stream (`--kv-unified`) and the
ubatch has more than one sequence. It is reuse-safe: `n_seqs_unq` is part of `llm_graph_params::allow_reuse`, and
`ggml-cuda` re-captures a CUDA graph when a node's op_params change. Every other backend ignores it, and it never
changes what is computed (the mask alone decides which cells a row sees). Routing rule:
`n_seq >= ne01 > 1`, one stream, mask-skip shapes OK and `n_kv >= GGML_CUDA_FA_MASK_SKIP_MIN_KV` -> vec, 1 row/block.

## Exactness

- The routing and the tiling do not depend on `GGML_CUDA_FA_MASK_SKIP`, so skip on vs off stays bit-identical.
- Per-sequence WMMA tiles do not change any row's result: in the WMMA kernel each column is independent (MFMA output
  elements, per-row softmax, per-row VKQ), `parallel_blocks` is chosen from the PLAIN tiling so a row sees the same
  KV partition, and a skipped block contributes exactly 0 (max unchanged, scale exp(0)=1, sum +0). So
  `GGML_CUDA_FA_SEQ_ROWS=1` vs `=0` is bit-identical for WMMA cases (checked in the GPU slot).
- The vec routing is a kernel change (vec instead of WMMA) for those batches: not bit-identical to the old kernel,
  checked against the CPU reference (nmse) and by test-backend-ops.

## Knobs

- `GGML_CUDA_FA_SEQ_ROWS=0` turns both per-sequence layouts off (== KVU-19a behaviour, in-binary A/B control).
- `GGML_CUDA_FA_MASK_SKIP=0` / `GGML_CUDA_FA_MASK_SKIP_MIN_KV` as in KVU-19a.
- Per-sequence WMMA tiles are planned for batches of at most 512 rows (`FATTN_SEQ_TILES_MAX_ROWS`).

## CPU

The CPU FA already iterates per row for batches below 64 rows (`one_chunk`, with KVU-19a's 64-cell -INF run skip),
which covers batched decode and drafted verify. Only the tiled path (>= 64 rows, prompt processing) groups rows, and
there at most one 64-row tile per sequence boundary straddles. No CPU change: not worth its risk.

## Not covered

- tile and MMA kernels (head sizes 40/72/192/320/512/576 on this host) keep per-tile liveness (they take the
  `tile_rows` argument but ignore it); MMA with `nstages > 1` (NVIDIA Ampere+) still does not skip at all.
- Batches with 2..N rows per sequence and small N (e.g. 4 seqs x 2 rows) stay on WMMA: the vec kernel with 2 rows per
  block would need its own sequence-aligned tiles. Not on any measured path.
