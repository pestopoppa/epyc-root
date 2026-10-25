# DS41-1017 lane: TensorFold 1.1.4 seeds (2026-10-24)

**Status: DRAFT. PREPARED, not applied.** The campaign owner copies this file into
`ak-ds41-1017-cpu-decode-20261021/store/inbox/` only after the operator approves the TensorFold 1.1.4 Stage-3 plan
and lifts the 2026-10-24 AK launch hold. These are proposals, not authority.

**Headline for this lane: TensorFold 1.1.4 has nothing on the MXFP4 expert GEMV.** Its FP4 paths are Blackwell
block-scaled FP4 MMA, and its DeepSeek-V4.1 engine changes are host-side four-rank prefill planning: "device assets,
numerical equivalence and serving are still unqualified" (`1b67f7c897`). Seeds S1-S4 in note 30 stand unchanged and
outrank everything here for the current target (N=1 decode, 45-token prompt).

## Seed (record-only on the current target, like note 30's S5)

**D1. `akm-ds41-1017-dsa-indexer-fused-scan`** (bit-exact if the head-sum order is kept; NOT measurable on
`ds41-1017-cpu-t48-nospec`)
- **Mechanism.** Score the lightning indexer in one pass over the compressed index-key cache: for each key, accumulate
  `d[h] = q_h · k` with the query held in registers/L1 for a block of keys (several keys per inner iteration), then
  `s = Σ_h w_h · relu(d[h] · scale)` in the same loop, writing one score per key.
  - This never materialises the `[index heads × keys]` score tensor, and drops the relu, mul and sum-over-heads graph
    nodes.
  - Keep the head and dimension order of the reference so scores are bit-identical, and the `top_k` picks the same keys
    in the same order, ties included.
- **Source.** TensorFold `aa6fbd8903` (#1054), GLM-5.3's Metal DSA scan. "The blocked kernel scores two keys a
  thread: the query is read once for the block". 16,384 keys × 16 rows: 1.59 → 0.14 ms (11.5×, author's Mac, scores
  bit-equal).
- **Where it matters.** DS41-C123 (`deepseek-v41-flash-evaluation.md:1211-1224`) lists the indexer and `top_k` over the
  whole compressed set, on 8 index-source layers, among the costs that grow with context. At the 45-token target they
  are negligible.
- **Expected effect.** Unknown until a depth profile exists. No DS41-1017 node profile exists at all.
- **Falsifier.** At 32k/64k, the indexer nodes (its matmul, relu, weighting and head-sum) are under 2% of decode wall in
  an at-depth `--node-profile`.
- **Actionable only with** the AKX-ALL-12 DS41 attention-graph route on a long-context surface (`--keep-dimensions
  prefill_at_depth` / `--longctx-surface`), alongside DS41-C123.1 (gather-form final attention).
- **Port cost.** Medium: a new CPU op, or a fused path in the indexer subgraph of `deepseek41.cpp`. **Risk**: shared-op
  rules (C112). The reference's indexer K/Q QDQ (DS41-T3.2) changes the inputs, not this op.

## Do NOT re-propose (from TensorFold 1.1.4)

- Routed and shared expert pairing in one pass (TensorFold `0c73b158de`). Its Q38FN analog measured 0% recoverable
  (Q38FN note 62 seed 3). Reopen only if a DS41-1017 node profile shows the shared-expert nodes carrying their own
  barrier or straggler cost of at least 1%.
- A fused residual add + RMS norm (TensorFold `e72a34ae38`). The champion already carries the rmsnorm keeps from the
  old DS41 lane.
- The int8-activation prompt GEMM (TensorFold #1176). This lane already uses q8_0 activations with integer dots.
