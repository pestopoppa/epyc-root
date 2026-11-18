# C15-GV-BW: why `gv_fattn_kernel` reads KV at 14% of HBM, and two knobs to fix it

Date: 2026-11-18. Owner: autokernel. Handoff: `kernel-champion-and-promotion.md` → C8-1-H17.
Champion read: C14 `llama.cpp-experimental-c14-fa-fold-20261118` @ `eee3da838`, file
`ggml/src/ggml-cuda/fattn-gqa-verify.cu` (read with `git show`; no checkout).
Code: `llama.cpp-experimental-c15-gv-bw-20261118` @ `dfcaa42ff` (fork). Row: `/mnt/raid0/llm/tmp/c15-gv-bw-gpu-20261118`
(prepared, not published).

All numbers below are either quoted from filed rows (cited) or derived from source by arithmetic. Nothing here was run.
Nothing was compiled.

## Shape

Qwen3.8-27B Q8_0, q8_0 KV, hd 256, 24 Q heads over 4 KV heads (G=6). No-draft decode is n_q=1 (6 rows per KV head).
DFlash2 verify is n_q=8 (48 rows).

At C14 both paths take the `PIPE && LATE` q8_0 instantiation `gv_fattn_kernel<true,true,true>`:

- n_q=1 → R=6, 1 MFMA tile, `nwaves = max(1, GV_MIN_WAVES) = 4` → 256 threads per WG.
- n_q=8 → R=48, 3 tiles, also 4 waves.

## What the kernel does per 32-key chunk

Each of the 256 threads loads one 34-byte `block_q8_0` of K and one of V. That is 32 keys × 8 blocks × 2 = 17.4 KB per chunk.
Each thread then dequantizes both blocks into LDS: K as f16 rows into `sK`, and V transposed into `sVt` with 32 scalar
`ds_write_b16` per thread. A barrier follows. Then one wave (n_q=1) or three waves (n_q=8) do the QK MFMA, the online
softmax, a barrier, and the PV MFMA. A final barrier ends the chunk.

`load_raw(c+1)` is issued between the store barrier and the compute, so exactly one chunk is ever in flight per WG.

Splits come from `n_splits = ceil(2*nsm / n_head_kv) = 52` (`fattn-gqa-verify.cu`, launch at about line 753 on C14), and
the grid is 52 × 4 × 1 = 208 WGs.

## Diagnosis

### 1. LDS caps occupancy at 1 WG/CU, so the grid runs in two serial rounds

LDS per WG:

| buffer | size |
|---|---|
| `sK` (32 × 264 half) | 16,896 B |
| `sVt` (256 × 40 half) | 20,480 B |
| `sP` (4 waves × 16 × 40 half) | 5,120 B |
| `smask` | 2,048 B |
| **total** | **44,544 B** |

With 64 KB of LDS per CU, that is 1 WG per CU. So 4 waves per CU, which is one wave per SIMD. The 208 WGs therefore run as
two rounds of 104.

**This is why the C9 split test found "more splits are slower"** (`c9-fa-diag-20261109`: 1x/4x/8x splits =
1.014/0.942/0.899). Extra splits only add rounds and merge work. Residency never rose. That test exercised the split
count, not occupancy, so the occupancy lever was not actually tested.

### 2. Latency-bound: one 17.4 KB chunk in flight per CU

The H17 profile has gv_fattn at 226 GB/s at d128k. Per FA call that is 131,072 × 4 heads × 544 B = 285 MB, or about
1.26 ms. Per WG round that is 0.63 ms over 79 chunks, so **about 8 µs per 32-key chunk**.

By Little's law, 17.4 KB per 8 µs per CU is 2.2 GB/s per CU, which over 104 CUs is the observed 226 GB/s.

The C9 counters agree with this reading:

- `SQ_WAIT_ANY` is 74% of wave cycles;
- MFMA is about 1% busy;
- there are no LDS stalls.

The waves are waiting on memory and barriers, not computing.

To reach 40% of HBM (640 GB/s), the per-CU in-flight bytes per chunk-time must roughly triple. Either more chunks must be
in flight per WG, or more WGs must be resident per CU.

### 3. Uncoalesced q8_0 loads

The lane map is `b = tid/32, key = tid%32`. One wave's load instruction therefore touches 32 different key rows, 272 B
apart (wider still with the cache's head interleave). Each block is only 2-byte aligned, so the LATE path's packed
`uint32_t w[8]` read may lower to unaligned dwords or to ushorts.

This multiplies TA/TD work per byte. It is a secondary cost while latency dominates. It is not addressed here: a
key-contiguous remap (`key = tid/8`) makes the V-transpose LDS store 8-way bank-conflicted (row stride 2,560 B ≡ bank 0),
so it needs a swizzled `sVt` first.

### 4. Not the bottleneck

- **q8_0 dequant cost.** About 64 int8→f16 conversions per thread per chunk. That is a few hundred cycles against an
  8 µs (~13k-cycle) chunk, and MFMA/VALU is about 1% busy.
- **Merge kernel.** It reads 52 × 6 rows × 1 KB = 312 KB per head group, small next to 285 MB.
- **Software pipelining depth.** Only one chunk is prefetched, at every tile count, not "past 8 tiles". `PIPE` is
  restricted to ≤ 8 tiles, which the 27B shapes satisfy. The shipped LATE variant fixed the `s_waitcnt`-right-after-load
  defect (C9: +9.9% at 128k), but the depth is still 1.

### Prior attempts, not repeated

- Target B `GGML_HIP_FA_VEC_LONGCTX_PB` (n_q=1 vec re-split) was REJECTED in r2 (0.95x @32k, 0.90x @128k).
- `GGML_CUDA_FA_GQA_VERIFY_SPLITS` 4x/8x was slower (C9).
- `GGML_HIP_GV_PREFETCH_LATE` is shipped.
- `GGML_HIP_GV_MULTISEQ` is shipped, for np4.

## Variants (default off; `dfcaa42ff`)

Both variants keep the chunk order, the dequant expressions and the MFMA sequence of the LATE path, so **output is bitwise
identical by construction**. The per-element reduction order is unchanged.

1. **`GGML_HIP_GV_PREFETCH_DEPTH=2|3`.** A register ring of PD raw-block slots (`kw/vw[PD][8]`, tails, mask halves). The
   chunk loop is unrolled by PD, so slot indices are compile-time constants and do not spill to scratch. Slot j is
   reloaded with chunk c+PD right after it is consumed. Loads issue in order, so `s_waitcnt vmcnt(n)` waits only for the
   oldest slot.

   With PD in flight per WG, the bytes in flight per CU go from 17.4 KB to 35 or 52 KB. The cost is about 18 extra VGPRs
   per slot. The 256-thread WG has a 512-VGPR budget per lane, so there is room.

2. **`GGML_HIP_GV_LDS_ALIAS=1`** (only when nwaves == 4, which covers both 27B shapes). `sK` and `sVt` share one
   20,480 B buffer:
   - mask and K are stored, then a barrier;
   - QK and softmax run, then the existing barrier;
   - V is dequantized into the same buffer from registers copied out before the slot is reloaded, then a new barrier;
   - PV runs, then the end barrier.

   LDS drops to 27,648 B, and `__launch_bounds__(256, 2)` lets **2 WGs/CU** co-reside. The 208-WG grid then runs in one
   round, and one WG's loads overlap the other's barriers and MFMA. The cost is one extra barrier per chunk.

3. **`al2`** combines both: ALIAS=1 with DEPTH=2.

A split re-tune is not a variant: with ALIAS the default 52 splits already fill 2 WGs/CU exactly, and
`GGML_CUDA_FA_GQA_VERIFY_SPLITS` stays available.

Tests added to `test-backend-ops`, each tagged `[C15-GV-BW]`:

- eval: 27B 24/4 hd256 q8_0 at kv 32768 and 131072, nb 1 and 8, tail 0 and 1000;
- perf: the same shapes at tail 0.

## Expected gain [inferred, not measured]

| level | expectation |
|---|---|
| Op level | If gv_fattn is latency-bound as above, 2–3× bytes in flight should give **1.4–2.0×** at 128k (226 → 320–450 GB/s, 20–28% HBM). The ceiling is the uncoalesced load path. |
| End to end | FA is 26–52% of the step at 128k. A 1.5× op gain gives about +10–20% no-draft decode at d128k, about +4–8% at d32k, and parity at d4k. |
| H17 target | 40% of HBM, giving +55% @128k, likely needs the coalescing/swizzle follow-up as well. |

## Row `c15-gv-bw-gpu-20261118` (prepared, unpublished)

1. In-row HIP build of `dfcaa42ff`, with content proof: both knob strings and the witness line in `libggml-hip.so`.
2. `tbo` correctness for 5 arms (base, pd2, pd3, al, al2), 76 `gqav` cases each, parsed with `rowlib/tbo_parse.py`.
3. Op-level FA us/run and GB/s at 32k and 128k, n_q 1 and 8, in 2 passes per arm.
4. **Stop-on-futility:** if the best op ratio at 128k is below 1.10, e2e is skipped.
5. Best arm only: llama-bench tg64 ABBAABBA at d4k, d32k and d128k, then DFlash2 np1 @32k ABBAABBA.

**KEEP iff** tg d128k ≥ 1.10, d32k ≥ 1.05, d4k ≥ 0.99, DFlash2 ≥ 0.99, and AA-calibrated mean-based identity on the DFlash2
token hash holds. Gate class: futility-only.

## Follow-ups if the op ratio lands but stays short of 40%

- A coalesced lane remap with an XOR-swizzled `sVt` column, so 8 lanes read one contiguous 272 B key row.
- Keeping V int8 in LDS and dequantizing at the MFMA B-fragment load. This would halve LDS again, allowing 3–4 WGs/CU.
