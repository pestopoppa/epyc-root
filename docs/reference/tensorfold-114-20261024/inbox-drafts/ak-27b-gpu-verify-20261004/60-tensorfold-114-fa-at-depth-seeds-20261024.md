# 27B GPU lane: long-context attention seeds from TensorFold 1.1.4 (2026-10-24)

**Status: DRAFT. PREPARED, not applied.** The campaign owner copies this file into
`ak-27b-gpu-verify-20261004/store/inbox/` (single-writer store) only after (a) the operator approves the TensorFold
1.1.4 Stage-3 plan, and (b) the operator lifts the 2026-10-24 "DO NOT LAUNCH AUTOKERNEL" hold. These are proposals,
not authority, and every one faces the critic unchanged. Source lines are at the v10 production tree `ffc1bac82`, so
re-resolve each one on the champion tip (`dcc853b55` C3, or C4 `cdb4d8c77` once it is CAS'd) before authoring. Seeds
tied to older floors are re-anchored first (CH-26b).

**Route and ownership.**
- Every seed below edits the FA dispatch, the `fattn-*` bodies or the q8_0→f16 K/V conversion, which is the
  **AKX-ALL-19 (G3) route**. That route must be admitted, with the DF2-9 reproducer gate, before a candidate can be
  authored. Note 10 §4 assigns FA and KV-convert to the FA session (P5/KVU-19).
- The campaign owner confirms with the KVU owner (kv-unified-stack-rollout.md) that AK may take these, or hands them
  over. Either way the seeds keep these mechanism ids.
- KVU-19b commit 2 (WMMA *sequence* tiles, −14% on aligned 4×8 verify, held out) is a different mechanism. Do not
  re-propose it under these ids.

**What this target must see.** These seeds only show at depth. The default ~300-token surface shows nothing.
- Required: the AKX-ALL-18 (G4) long-context surface (1×80k at N=8, plus N=16 and N=32 and the ragged {1,8,8,8} per
  AKX-ALL-LB2), and production-shape np 4.
- An N=8-only or short-context keep is not promotable.

**Evidence (our own, MEASURED, rocprof B 2026-10-04, `/mnt/raid0/llm/tmp/rocprof-longctx-20261004/results/20261004T081019Z/report.md`).**
At 1×80k, N=8 verify, the step is 120.5 ms. FA takes 29 ms and the kv_convert takes 8 ms, together 31% of the step.
88% of :8083 decode wall is above 32k (AKX handoff header). This was measured before the KVU-19 fold, so re-measure on
the champion.

**Mechanism reading (SOURCE-READ, not measured).** Re-verify each point on the champion.
- `fattn.cu` chooser: at D=256, GQA 6 (`gqa_ratio_eff` 2) and N=8, gfx90a takes the WMMA kernel when rocWMMA is on
  (`ggml_cuda_should_use_wmma_fattn`), else TILE. Record which path runs live (cf. V11-FA-1's ROCWMMA A/B).
- `fattn-wmma-f16.cu:100-103`: each Q head reads K/V at `head / gqa_ratio`, with no GQA packing.
- `fattn-common.cuh:1176-1178`: `blocks_num = (ntiles_x, parallel_blocks, ntiles_z_gqa*K->ne[2]*Q->ne[3])`. Blocks run
  x-fastest, so one head's KV-split chunks (y) are all issued before the next head (z). Six heads each walk the whole
  K/V, about 84 MB of f16 per KV head at 80k against 8 MB of L2.
- `fattn-common.cuh:1022-1041`: when the kernel needs f16, the **whole visible K and V views** are converted with
  `ggml_get_to_fp16_cuda` on every FA call, in every layer, every round.

**Arithmetic (DERIVED).**
- Model shape: 16 attention layers, 4 KV heads, D=256, q8_0.
- At 81,920 tokens, q8 K+V = 2.85 GB and the f16 view = 5.37 GB.
- Convert: 8.2 GB of traffic is 5.0 ms at 1,638 GB/s. The measured 8 ms is consistent.
- FA: one f16 read is 3.3 ms; 6 heads each re-reading is 19.7 ms; compute is 0.26 TFLOP per round, ≤2.8 ms even with N
  padded to 16. The measured **29 ms** is ~9× the single-read floor and ~1.5× the re-read floor, so it is byte- and
  latency-bound, with the GQA re-read the leading explanation.

**Arbiter first (no build; one GPU window, needs a grant).** Before authoring G1, G2 or G3, run rocprof on the
champion at 1×80k, N=8, recording per FA dispatch `FETCH_SIZE` and `TCC_HIT`/`TCC_MISS`, and per convert dispatch its
time.
- `FETCH_SIZE` ≥ 3× the f16 K+V view bytes: the GQA re-read is real, so G2 and then G1.
- `FETCH_SIZE` ≈ 1×: the re-read is already absorbed by L2, so G2 is dead and G1 is only a tile-fill or compute change.
  Re-rank before authoring.
- Convert ≥ 4 ms at 80k: G3 stands.

## Ranked seeds (mechanism ids are new; none exist in this store)

**G2. `akg-fa-gqa-adjacent-grid-order`** (bit-exact; cheapest; rank 1)
- **Mechanism.** Reorder the FA grid so the blocks that read the same K/V chunk are dispatched adjacently: the GQA
  query heads of one KV head, and the KV-split chunk index, become the faster axes, and Q tiles and heads-of-different-KV
  the slower ones. Each block's work is unchanged. This is TensorFold #1219's change (grid `(chunks, key heads, rows)`
  → `(rows, key heads, chunks)`), with GQA heads standing in for their rows.
  - Do it in `launch_fattn` (`fattn-common.cuh:1176-1178`) by remapping `blockIdx` inside the kernel prologue (a
    linear-id permutation), not by changing what any block computes.
  - The stream-k branch (`blocks_num.x = nblocks_stream_k`) stays as it is.
- **Expected effect.** If the arbiter shows the 6× re-read: FA 29 ms → ~5-10 ms at 80k (−8…−20% of the 120.5 ms
  step), growing with depth and nil at ≤8k (TensorFold: 0-3% at 8k, −16% ms/token c=1 and −38% c=4 at 32k, on GB10's
  24 MB L2; ours is 8 MB, so the crossover is earlier).
- **Falsifier.** On the champion after the reorder, `TCC_HIT` rate on FA dispatches rises by less than 20 points, or FA
  time drops by less than the window noise floor at 1×80k. Also check `FETCH_SIZE` < 3× the view in the arbiter.
- **Correctness.** Byte-identical FA outputs against the incumbent on `test-backend-ops -o FLASH_ATTN_EXT` (D=256,
  GQA 6, q8_0, padded and unpadded), the DF2-9 reproducer, greedy identity, and the RI gate (row r alone == row r in N).
- **Port cost.** Low (a few lines plus a contract test). **Risk**: occupancy interaction with `parallel_blocks`
  selection (the waves-efficiency loop at `fattn-common.cuh:1155-1174` assumes nothing about order, so low).
- **Source.** TensorFold `a56d0ce2fa` (commit L10, "The grid is now (rows, key heads, chunks); each block's work is
  unchanged, so the bits are too."); PR #1219 body L7 (synthetic 16 rows 7.62 → 4.67 ms, L2 hit 22.6% → ~100%).

**G3. `akg-fa-q8-kv-tile-widen-no-convert`** (bit-exact by construction; rank 2)
- **Mechanism.** Remove the whole-view q8_0→f16 conversion before multi-row FA (`fattn-common.cuh:1022-1041`).
  Instead, each K/V tile is widened inside the FA kernel as it is staged into LDS, with the same op sequence the
  convert kernel uses (`float(d)*q` → f16 round), so the f16 values in LDS are bit-identical to today's. This is
  TensorFold #1168 / #1080's `F8` staging (`prefill_attention_rows.cuh`: codes and scales loaded a step ahead, widened
  into the slot).
- **Expected effect.**
  - −8 ms at 80k, from deleting kv_convert: −6.6% of the step, +7% tok/s at 80k.
  - FA's own K/V reads drop from 2.0 B to ~1.06 B per element, so if FA stays byte-bound a further cut, up to ~45% of
    FA bytes.
  - Prefill also stops re-converting the whole prefix every ubatch, though that is under 1% of an 80k prefill by
    arithmetic, so claim nothing there.
- **Falsifier.** kv_convert at 1×80k is under 2 ms on the champion; or the in-kernel widen costs more VALU than it
  saves (FA time rises by more than the convert time removed).
- **Correctness.** Byte-identical against the incumbent, the same suite as G2, plus a q8_0 tile edge at n_kv not a
  multiple of the tile.
- **Port cost.** Medium. `fattn-vec` already consumes quantised K directly, so reuse its dequant helpers. The
  WMMA/TILE loaders need a q8_0 staging path. **Risk**: LDS pressure at D=256, and the DF2-9 NaN class (rocWMMA FA pin),
  so the DF2-9 gate is mandatory.
- **Source.** TensorFold PR #1168 body L13/L20; `184a938e3a` (`F8` staging in `prefill_attention_rows.cuh`, diff in
  `dl/split/zig__kernels__cuda__prefill_attention_rows.cuh.diff`).

**G1. `akg-fa-gqa-rows-packed-mfma-tile`** (TOL / ppl-contract; largest; rank 3, after G2 and G3 have measured)
- **Mechanism.** For multi-row verify, put the 6 query heads of a KV head times the N window rows (48 lines at N=8)
  into the M dimension of one MFMA tile (3 × m16), so each q8_0 K/V tile is read once per KV head per round, staged
  and widened in LDS (G3's loader), and the MMA tiles are full rather than N=8 padded to 16. This is TensorFold #1168
  (`attn_one`/`attn_rows`: "the key head's query heads the lines of one m16 tile"; "the tile is read and widened once
  per round rather than once per row"). In llama.cpp the CUDA MMA kernel already packs GQA (`ncols2`, `fattn.cu:113-150`),
  so the port is "ncols2 GQA packing on the gfx90a MFMA path at D=256", not new design.
- **Expected effect.** FA bytes fall to q8 once (2.85 GB, 1.7 ms floor at 80k). With G3, that is up to −20…−28% of the
  80k step (+25…+39% tok/s at 80k), as a ceiling. TensorFold measured 101.9 → 180.4 tok/s decode after a 64k prompt on
  an RTX 5090 (bf16 KV 96.9 → 221.1).
- **Falsifier.** After G2 and G3 have landed, FA at 1×80k is within 1.5× of its q8 single-read floor: nothing is left.
  Or the packed tile needs more than 64 KiB of LDS at D=256 and occupancy collapses.
- **Correctness.** It changes the reduction order, so it is not bit-exact against the incumbent. It must be
  row-invariant (RI gate: each row's output identical alone and in any N, as TensorFold enforces). It goes through the
  ppl/KLD contract, the DF2-9 reproducer, greedy identity *within the candidate* across N, and coherence at production
  prompt length. TensorFold's tensor-core version moved outputs ~0.16% RMS (PR #1168 L25).
- **Port cost.** High: a new MFMA FA tile body at D=256 for wave64, plus the RI fixed K-split. **Risk**: the KVU-19b
  precedent (WMMA sequence tiles −14% and an exactness break), so author it separately switchable and straddle-safe.
- **Source.** TensorFold PR #1168 (`ffa87d9960`, `595c135a74`, `qwen35_attn_tc.cuh`).

**G4. `akg-dflash2-drafter-vocab-span-head`** (output-neutral on the target; low; rank 7 overall)
- **Mechanism.** Compute the DFlash2 drafter's logits only over the vocabulary spans its drafts can come from, then
  fall back to the whole head once a stream's prompt or reply holds a token outside them. Verification decides every
  token, so the target's output is unchanged.
- **Expected effect.** TensorFold: drafter head 450 → 182 µs per round, a round −1.2%, MGSM kept by the fallback. Ours
  is ≤1% of a 75.8 ms round by the head's byte share. Only worth it if `dflash.cpp` computes the full 248k head per
  draft pass.
- **Falsifier.** `dflash.cpp` already projects only the drafter vocabulary (d2t), or the head is under 1% of the round
  in rocprof.
- **Port cost.** Low-medium. **Risk**: τ loss on multilingual if the fallback is wrong. **Source**: `e475e90fb9`.

## Evidence for EXISTING seeds (do not re-seed; attach to their next critic pass)

- **H4 `akg-stack-gdn-attn-projections`.** TensorFold #1138 is the same mechanism, measured on an A10 (sm_86):
  - per set: 27B attention-in 98.6 → 76.7 µs, gated-delta-in 104.7 → 92.1 µs;
  - +2..+7% decode end to end;
  - bit-exact, each projection keeping its own split-K and slice-order sum;
  - **null on GB10**, which keeps per-projection launches;
  - MLP gate+up measured slower merged and was left alone.

  Expect the gain on the tiny projections (k, v, a, b), not on gate/up.
- **H3 / H13 (wide verify).** TensorFold `d9373fef16` / PR #1079 L42: 32 rows on one weight pass 17.8 ms against
  2×16-row tiles 22.3 ms (27B, RTX 5090); "A 64-row tile measured no gain; wide windows are compute-bound here."
- **H7 `akg-fuse-act-quant-into-gemv`.** TensorFold `11e9b4db18`: having the producer kernels write the consumer's
  64-entry group sums removed 5,474 → 686 launches per 256-token reply and gained +0.7% decode. That is the scale to
  expect from launch elimination alone.
- **H8 launch/idle census.** TensorFold's twelve-commit verify-round series (#1079) of bit-exact micro-kernels (16-byte
  loads, next-row prefetch, ILP of 8 keys) gave +15% on a 5090 one-stream ruler. They are latency-class wins that only
  appear once the big byte terms (G1-G3, H1) are gone.

## Do NOT re-propose

- int8-activation MFMA for its *rate* (TensorFold #1176's 4× premise). On CDNA2 int8 MFMA = f16 MFMA (note 10 §0).
- The bf16/f16 exact-integer weight route (TensorFold `ggml.cu`, "weights as A and rows as B"). Note 10 §3.2 settled it:
  no rate advantage on CDNA2, and it costs exact-i32.
- KVU-19b commit-2 WMMA sequence tiles (held out, −14%).
