# DTree under V5I: where a tree verify round's extra time goes (2026-11-22)

Read-only analysis. No compute was run. Kernel C17 `1b83c6967`, Qwen3.8-27B-Q8_0 target with the DFlash2-Q8_0 drafter on the MI210.
V5I = `GGML_HIP_Q8_MF=6 MF_MIN=1 MF_SLC=1 MF_INPLACE=1 WVSK_MAX=16`.

## Sources

- C17 tree rerun: `/mnt/raid0/llm/tmp/ak-dtree-batch-rerun-gpu-20261121/out/RESULT.json`. Every arm sets V5I (`arm_env`). The arms are `-fa on -ctk/-ctv f16 --spec-draft-n-max 7 --draft-tree-mode batch`.
- E2 profiler row: `/mnt/raid0/llm/tmp/ak-27b-verify-slope-attr-gpu-20261122/out/RESULT.json`. It ran llama-bench with flat M rows and q8_0 KV.
- E1: `docs/design/e1-dtree-parent-conditional-replay-20261122.md`. Conditional T12 tau is 5.62 against 5.02 for the chain.

## Caveats on the evidence

1. **The rerun has no full-run server logs.** `out/logs/` contains only `*.argv.json`, even though the arms passed `-lv 4`. The only `print_timing` and statistics lines are in `out-smoke/logs/smoke-{L,A}.server.log`, which cover 13 drafts each.
   - The smoke drafter time is `dur g` = 141 to 145 ms over 13 calls, which is about 11 ms per call. That figure includes cold first calls.
   - The steady-state off-forward time is derived as round ms minus the llama-bench forward: 45.5 − 37.7 = **7.8 ms per linear round**. That bounds drafter, sampling, host sync and bookkeeping together.
   - The logs do not give a per-phase split for tree build, mask, accept/gather or the GDN snapshot. The tree-only line items below are therefore **estimates**, and they are marked as such.
2. **The E2 arms did not set V5I.** `job.py` `env()` passes only PATH, HOME, LD_LIBRARY_PATH and FILLER_ID.
   - Up to M=10 its matmuls run `q8wv_small_m`: 31.5 ms at M=8 and 34.9 ms at M=10.
   - At M≥12 they fall to `mmq` at 54.6 to 55.2 ms. That is why E2's wall time jumps 47.9 → 70.2 ms between M=10 and M=12, and why its verdict is NOT_JUDGEABLE.
   - E2's matmul classes therefore do **not** describe V5I. Its non-matmul classes are path-independent and are used below.

## (a) Rows verified per round

| Arm | Rows per verify | Source |
|---|---|---|
| Linear DF2 | **8** (anchor + 7) | `dflash.block_size` = 8 in the GGUF; `--spec-draft-n-max 7` |
| T12 | **12** | batch mode: tree columns = `draft_tree_nodes`, anchor included (`server-context.cpp:339`, `common.h:416`) |
| T16 | **16** | same |
| auto | up to n_max + 10 = **17** | `server-context.cpp:340-341` |

A tree adds 4 rows (T12) or 8 rows (T16) over linear, not 11 or 15. The batch mode also gives every column a rollback slot: `need_n_rs_seq` = cols − 1, which is 11 for T12 and 15 for T16, against 7 for linear.

## (b) Time per round outside the target forward

| Arm | ms per round | llama-bench V5I forward at that width | Outside the forward |
|---|---|---|---|
| L | 45.5 | 37.7 (W8) | **7.8** |
| T12 | 51.4 | 41.3 (W12) | **10.1** |
| T16 | 53.5 | 41.7 (W16) | **11.8** |

Two caveats apply to the forward column. The bench forward has 1 output row and f16 versus q8_0 KV differs, so the column is approximate. Even so, the off-forward overhead **grows by 2.3 ms at T12 and 4.0 ms at T16**. That growth is the tree-only cost: it is not in the matmul slope and not in llama-bench at all.

## (c) Per-op-class breakdown at M=8 vs M=12/16 (E2, non-matmul classes only)

| Class | M=8 (ms) | M=12 (ms) | M=16 (ms) | Δ8→12 | Δ8→16 |
|---|---|---|---|---|---|
| gdn | 1.46 | 2.10 | 2.70 | +0.64 | +1.24 |
| idle_gap | 5.67 | 6.06 | 6.34 | +0.39 | +0.67 |
| fa | 0.91 | 1.11 | 1.17 | +0.19 | +0.26 |
| ssm_conv | 0.31 | 0.42 | 0.48 | +0.11 | +0.17 |
| copy | 1.34 | 1.45 | 1.43 | +0.11 | +0.10 |
| eltwise, norm, quant_act, rope, get_rows, other | — | — | — | +0.18 | +0.24 |
| **Non-matmul total** | | | | **+1.62** | **+2.68** |

The V5I bench slope from W8 to W12 is 3.6 ms. Subtracting the 1.6 ms non-matmul share leaves a **V5I matmul share of about 2.0 ms for 4 extra rows**, or about 0.5 ms per row, which is consistent. At W16 the bench slope is 4.0 ms, of which 2.7 ms is non-matmul, leaving about 1.3 ms of matmul. The matmul share is lower there because the W12→W16 matmul step is roughly flat under WVSK_MAX=16.

The E2 step from M=8 to M=9 is dominated by `q8wv_small_m` at +2.94 ms. That step is a non-V5I artifact and is excluded.

## (d) Budget for T12 − linear = 5.9 ms

| # | Component | ms | Basis |
|---|---|---|---|
| 1 | V5I matmul for the 4 extra rows | 2.0 | bench slope 3.6 minus the E2 non-matmul share |
| 2 | GDN recurrence scaling (gdn + ssm_conv) | 0.75 | E2 measured |
| 3 | Idle gaps and launch overhead scaling | 0.4 | E2 measured |
| 4 | FA with a wider tree mask, plus copy, eltwise and other ops | 0.45 | E2 measured |
| 5 | GDN per-column rollback snapshot and replay (11 slots against 7) | ~1.0 | **estimate**; part of the 2.3 ms residual |
| 6 | Logits and D2H for the extra output rows, plus host argmax and accept/gather | ~0.6 | **estimate**: 4 × 248k vocab, D2H plus a host scan |
| 7 | Tree build, mask build and upload, extra host sync, drafter top-k export | ~0.7 | **estimate**; the rest of the residual |
| | **Total** | **5.9** | |

### Ranked cuts

| Rank | Cut | Est. ms saved |
|---|---|---|
| 1 | GDN snapshot only for the accepted path, with a lazy replay instead of per-column state slots (item 5) | 0.8–1.0 |
| 2 | Device-side argmax and accept on the tree rows, D2H of token ids only rather than logits (item 6) | 0.4–0.5 |
| 3 | Cache the tree mask and topology across rounds and overlap tree build with the drafter tail, removing one host sync (item 7) | 0.4–0.6 |
| 4 | Tree-aware GDN kernel that shares the prefix recurrence across siblings (item 2) | 0.3 |
| 5 | Graph reuse and fused launches for the tree graph (item 3) | 0.2 |

All cuts together save about 2.3 ms, giving T12 ≈ 49.1 ms per round.

### Resulting speedup (T12 against linear at 103.3 tok/s, 45.48 ms and tau 4.70)

| Scenario | ms per round | tau | tok/s | Against linear |
|---|---|---|---|---|
| Today | 51.35 | 4.915 | 95.7 | 0.927 |
| Cuts 1–5 only | 49.1 | 4.915 | 100.1 | 0.97 |
| E1 conditional only (tau × 5.62/5.02 → 5.26) | 51.35 | 5.26 | 102.5 | 0.99 |
| E1 conditional plus cuts 1–3 (−1.9 ms) | 49.4 | 5.26 | 106.5 | **1.03** |
| E1 conditional plus cuts 1–5 | 49.1 | 5.26 | 107.2 | **1.04** |

The break-even round time for conditional T12 is 45.48 × 5.26 / 4.70 = **50.9 ms**. Neither lever wins alone: conditional replay plus at least about 0.5 ms of round-overhead cuts is needed.

### Recommended confirmation

Before any implementation, a V5I re-profile is needed:
- Rerun E2 with the V5I env on every M, so the matmul class is measured rather than inferred.
- Run one T12 server arm with per-phase timers on draft, build, mask, decode, accept and snapshot.
- Persist the full `-lv 4` server logs, which the C17 rerun did not keep.

Together these would replace the three estimated rows (items 5–7) with measurements.

## Measured phase deltas (row ak-dtree-phase-gpu-20261122-r2, 2026-11-22, INCONCLUSIVE)

These replace the estimated rows 5-7 above. 8 ABBA pairs, A/A in band, build 284a03e2d. RESULT.json SHA-256 `8b3d5f9a01b4cc3694af49ae3fdd8a346285f0b48aaecd094e4fd61b63bdfbf3`.

| Arm | ms/round | mean length |
|---|---|---|
| L | 45.59 | 4.706 |
| L2 (A/A) | 45.33 | 4.705 |
| T12 | 50.71 | 4.914 |
| T16 | 52.80 | 5.256 |
| T12 + replay | 55.06 | 4.920 |
| T16 + replay | 57.29 | 5.251 |

Per-phase delta against L, in ms (mean, 95% CI):

| Phase | L2 | T12 | T16 |
|---|---|---|---|
| decode | -0.06 [-0.34, 0.22] | 6.02 [5.67, 6.36] | 9.70 [9.43, 9.96] |
| draft | -0.05 [-0.15, 0.05] | -0.08 [-0.21, 0.05] | -0.16 [-0.26, -0.06] |
| pre | -0.04 [-0.11, 0.03] | 0.00 [-0.19, 0.20] | 0.18 [-0.06, 0.42] |
| post | 0.01 [-0.19, 0.22] | 0.04 [-0.04, 0.11] | 0.27 [0.10, 0.44] |
| iter | -0.05 [-0.26, 0.17] | 6.06 [5.70, 6.41] | 9.97 [9.69, 10.25] |

With replay (T12C / T16C): decode 7.52 / 10.14, pre 1.25 / 1.73, post 1.22 / 1.71, iter 8.74 / 11.85. Replay adds host-side pre/post cost and is slower in every case.

Reading: the tree cost is almost entirely in the decode phase (graph compute), not in draft, tree build or accept. The host-side items 6-7 are about zero.

**The tree track is PARKED, and this confirms it.** T12 costs 5.1 ms per round over L for +0.21 mean length (4.914 against 4.706). Break-even needs about 50.9 ms at tau 5.26, so T12 and T16 are both slower per token than linear.
