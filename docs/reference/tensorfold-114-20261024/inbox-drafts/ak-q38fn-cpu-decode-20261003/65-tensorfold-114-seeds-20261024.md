# Q38FN lane: seeds from TensorFold 1.1.4 (2026-10-24)

**Status: DRAFT. PREPARED, not applied.** The campaign owner copies this file into
`ak-q38fn-cpu-decode-20261003/store/inbox/` only after the operator approves the TensorFold 1.1.4 Stage-3 plan and
lifts the 2026-10-24 AK launch hold. These are proposals, not authority. Source lines are at the v10 tree `ffc1bac82`;
re-resolve them on the champion tip. Re-anchor floors per CH-26b.

**What 1.1.4 adds for this lane: little that is new.** Its CPU-transferable mechanisms are already here:
- sibling projections of one input in one pass is `akm-cpu-struct-sibling-gemv-pack`, a KEEP verdict at 3.5% of wall;
- producers writing what consumers need is `akm-cpu-struct-norm-to-q8-fusion`, KEEP at 5.0%;
- GQA-grouped attention per KV chunk is AKX-ALL-LB3 (a);
- the shared multi-stream verify is native in llama-server.

TensorFold's numbers are external evidence for those, not new seeds. Two narrow seeds remain.

**Census this hangs on (MEASURED, note 62 L10-27).** N=5 verify eval wall 77.7 ms, 4,480 nodes, barriers 5.7 ms.
MUL_MAT 29.4%, MUL_MAT_ID 26.9%, **CPY 9.4% ("copies feeding matmuls")**, GATED_DELTA_NET 8.3%. About 1,800
small/solo nodes cost ~7.7 µs each.

## Ranked seeds

**Q1. `akm-q38fn-cpy-producer-writes-consumer-layout`** (bit-exact; attribution first)
- **Mechanism.** Copies are exact, so a producer that writes directly in the layout and type its matmul consumer reads
  removes a CPY node, its barrier and its memory round-trip. This is TensorFold's pattern across 1.1.4:
  - `b9b23ec9ca`: "the planned decode walk reads q and writes its rows in the activation type";
  - `11e9b4db18`: the producers of the out, o and down projections write the inputs' group sums, so no separate
    launch is needed;
  - `e72a34ae38`: the residual add and RMS norm run in one launch.
- **Step 1 (no build).** Classify the CPY nodes in a `--node-profile` of the champion at N=5 by source op and
  destination consumer: permute→contiguous before `MUL_MAT`, f32→f16/bf16 type casts, conv-state or KV writes.
- **Step 2.** For the largest class whose producer is a graph op under our control (in `src/models/qwen4exp*.cpp`),
  have the producer emit the contiguous/target-type tensor (`ggml_cont` folded into the producer's output view, or a
  producer variant), or let the consumer read the strided view directly.
- **Expected effect.** The ceiling is 9.4% of wall (7.3 ms). Realistic: 2-4%, after the norm-to-q8 KEEP takes its own
  share. Also fewer small nodes, at ~7.7 µs each.
- **Falsifier.** After norm-to-q8-fusion, CPY is under 3% of wall, or the CPY classes are KV-cache `set_rows` / state
  writes that must exist.
- **Correctness.** Bit-exact: greedy identity and node-output byte equality.
- **Port cost.** Low-medium, model-graph level. **Risk**: shared-op changes need the C112 peer check. Graph-only edits
  in `qwen4exp*.cpp` follow note 63's fold rule.
- **Overlap.** Partial with `akm-cpu-struct-norm-to-q8-fusion` (KEEP). This seed covers only the CPY classes that one
  does not remove.
- **Source.** TensorFold `b9b23ec9ca`, `11e9b4db18`, `e72a34ae38` (in v1.1.3...v1.1.4).

**Q2. `akm-q38fn-gdn-prologue-into-chain`** (bit-exact; only if not already in `qwen4exp-fused.cpp`)
- **Mechanism.** Fold the GDN prologue (conv tail, q/k/v/g/β preparation, l2norm) and the gated-norm epilogue into the
  `GATED_DELTA_NET` op, row by row, so those small nodes disappear. This is TensorFold #1217 (`d0d179497e`: front,
  chain and norm in one kernel per value head, producers making the next 16 rows' inputs beside the chain; −19% of the
  GDN block, bit-exact) and `eb0d391600` (a one-window verify round skips the redundant conv commit, because the
  prologue already logged each row's conv tail).
- The CPU GDN op already writes rollback snapshots in the kernel (`ggml/src/ggml-cpu/ops.cpp:11134-11154`), so the
  TensorFold snapshot-copy savings do not apply here. Only the prologue/epilogue node count does.
- **Expected effect.** GDN is 8.3%. The gain comes from the prologue nodes it removes: about 5-10 nodes per GDN layer
  at ~7.7 µs, so 1-3% of wall if the fused graph has not already removed them.
- **Falsifier.** `qwen4exp-fused.cpp` (the `akm-cpu-qwen4exp-fused-decode-nle8` lineage) already merges the GDN
  prologue, or the prologue nodes are under 1% of wall in the node profile.
- **Port cost.** Medium: op signature plus CPU kernel. **Risk**: a shared `ggml/` op, so shape-gate it and peer-check
  (C112).
- **Overlap.** `akm-cpu-small-node-prelude-collapse`, `akm-cpu-qwen4exp-fused-decode-nle8`, solo-rows KEEP. Run the
  falsifier before authoring.

## Evidence for EXISTING seeds and keeps

- **`akm-cpu-struct-sibling-gemv-pack` (KEEP verdict).** TensorFold #1138 (A10): one launch over projections that share
  an input gave −12…−22% per set, bit-exact. The MLP gate+up, already bandwidth-bound, measured *slower* merged. Pack
  the small siblings (ne01 < 192), not gate/up.
- **`akm-cpu-struct-norm-to-q8-fusion` (KEEP).** TensorFold `11e9b4db18`: producer-written sums removed 87% of the sums
  launches for +0.7%.

## Do NOT re-propose

- Routed and shared expert grouping: note 62 seed 3 measured 0% recoverable. TensorFold `0c73b158de` (HIP, fc1 plus
  shared up in one launch) does not change that.
- A CPU FA KV-chunk/row reorder as a new id: `akm-cpu-fa-query-major-row-schedule` was DISCARDED on replicate (−1.10%),
  and GQA grouping is AKX-ALL-LB3 (a).
- Multi-stream shared verify or batched drafting: llama-server already batches every slot's sampled and draft tokens
  (`tools/server/server-context.cpp:500, 3193`) and drafts in one call (`:3143`).
- A PLE gather thread pool: ggml's threadpool is persistent, so TensorFold #1195's defect does not exist here.
