# MI210 served-path kernel bandwidth census (2026-11-22)

Status: DRAFT analysis. Existing data only, no compute. [no-belief: analysis of existing rows; no new measurement]

Operator rule (2026-11-22): a GPU kernel whose implied bandwidth is below **1 TB/s** is an optimization surface.
References: HBM peak about 1.6 TB/s, measured stream ceiling about 1.5 TB/s, V5I dense Q8 about 1.0-1.2 TB/s.

Scope: the C18 champion (`74c18e2d8`).
- **27B DF2**: Qwen3.8-27B Q8_0 + DFlash2 with V5I env (`GGML_HIP_Q8_MF=6, _INPLACE=1, _MIN=1, _SLC=1, GGML_HIP_Q8_WVSK_MAX=16`).
- **A3B**: Qwen3.6-35B-A3B-MTP-Q8_0. This is the file on disk; the brief says "Qwen3.5". MTP n_max 2, so verify uses n=3 rows.

**Caveat: no source row ran on the C18 binary.** Each row is labelled with its own binary below. Byte counts come
from the GGUF tensor shapes (`gguf-py` reader). Q8_0 is 34 B per 32 weights.

## Sources

| Row / file | Binary | V5I | Used for |
|---|---|---|---|
| `ak-q8wv-split16-gpu-20261122-r3` (arm V) | 57a935901 (C17+split16) | yes | 27B dense per-shape µs, n=1..16 |
| `ak-27b-verify-slope-attr-gpu-20261122` | C17 1b83c6967 | **no** | 27B non-dense op-class ms/forward (llama-bench, d0, M rows) |
| `ak-dtree-phase-gpu-20261122` | 284a03e2d | yes | 27B served round: 45.7 ms/round for the L arm, draft 5.3 ms |
| `ak-mmid-split16-gpu-20261121-r4` | 7abce4563 (C17+split16) | n/a | A3B MUL_MAT_ID µs and GB/s, `moe_step_ms` |
| `research/deep-dives/mi210-next-hotspots-20261118.md` and `autokernel/loop/data/gpu_serving_shares_v1.json` | C14 / C8-h17 | no | A3B n=4 shares (34 ms/step busy), 27B FA share by depth |
| `docs/design/v5i-a3b-0988-diagnosis-20261122.md` (worktree `ak-v5i-a3b-diag-20261122`) | — | — | A3B expert occupancy U(n) and expert bytes |

## 27B DF2: per verify forward at M=8 (n=16 in brackets)

Per-round reference: 45.7 ms/round (dtree L arm, V5I). That is roughly 37 ms of verify forward, 5.3 ms of drafter, and
the rest host-side.

| Op class | Calls/fwd | MB/call | µs/call V5I n8 [n16] | GB/s n8 [n16] | ms/fwd n8 | ms recoverable at 1.2 TB/s n8 [n16] |
|---|---|---|---|---|---|---|
| ffn gate+up 17408x5120 | 128 | 94.7 | 90.4 [93.0] | 1047 [1018] | 11.57 | 1.47 [1.80] |
| ffn down 5120x17408 | 64 | 94.7 | 88.7 [93.1] | 1067 [1017] | 5.68 | 0.63 [0.90] |
| GDN attn_qkv 10240x5120 | 48 | 55.7 | 53.3 [56.1] | 1045 [993] | 2.56 | 0.33 [0.46] |
| GDN attn_gate 6144x5120 | 48 | 33.4 | 35.6 [36.6] | **939 [913]** | 1.71 | 0.37 [0.42] |
| GDN ssm_out 5120x6144 | 48 | 33.4 | 34.2 [36.9] | **976 [906]** | 1.64 | 0.30 [0.43] |
| attn_q 12288x5120 | 16 | 66.8 | 64.5 [68.2] | 1036 [981] | 1.03 | 0.14 [0.20] |
| attn_output 5120x6144 | 16 | 33.4 | 34.2 [36.9] | **976 [906]** | 0.55 | 0.10 [0.14] |
| **dense total** | 368 | 25.7 GB | — | **1037 [996]** | 24.74 [25.76] | **3.34 [4.38]** |
| attn_k/v 1024x5120, lm_head 248320x5120 (1.35 GB) | 34 + 1 | 5.6 / 1351 | **not measured** | ? | ? | lm_head alone is ≥1.13 ms at 1.2 TB/s; gap |
| GDN recurrence | 48 | ~6 (state r+w, approximate) | 30 [56] | ~200 (approximate) | 1.46 [2.70] | ~1.2 [~2.4], approximate |
| FA verify (gv_*) | 16 | KV-depth dependent | d0 0.91 ms/fwd | — | 0.91 at d0 | 5% of busy at d8k, 14% at d32k, 27% at d131k (h17) |
| quant_act (q8_1) | ~370 | small | — | launch-bound | 2.44 | fusion lever, not a bandwidth one |
| eltwise / norm / copy / get_rows / rope / ssm_conv / other | ~1000 | KB-scale | — | launch-bound | 8.6 | fusion lever |
| idle gaps inside the forward | — | — | — | — | 5.67 | host/launch |
| drafter forward (DF2, 5 layers, 2.05 GB) | 1/round | — | — | ≥2.05 GB / 5.3 ms ≈ 390 GB/s upper bound (includes host) | 5.3 | **unknown split**; ≤3.6 if drafter weights reach 1.2 TB/s |

How to read this:
- V5I lifts dense Q8 to about 1.04 TB/s at M=8 and about 1.0 TB/s at M=16. It holds about 1.1 TB/s only at n=1. **The
  6144-class shapes (33 MB) sit below 1 TB/s at every n≥8.**
- The non-dense classes come from a non-V5I row. They do not depend on V5I, but they are C17, not C18.

## A3B MTP: per verify step, n=3 (rows of the n=4 C14 profile marked)

The reference step is 34 ms of busy time at n=4 (C14, h-18 profile). Busy fraction was only 0.48-0.53 under llama-bench `-r 5`.

| Op class | Bytes/step | ms/step | GB/s | Gap | ms recoverable at 1.2 TB/s |
|---|---|---|---|---|---|
| MUL_MAT_ID experts (gate_up + down), n=3 | U(3)≈23 experts × 134 MB ≈ 3.08 GB | 3.95 (`moe_step_ms` OFF n3) | ≈780; per op: gate_up 814, down 750; n=1: 571 / 637 | −220 to 1 TB/s, −720 to 1.5 | **1.38** (n=4: 1.6) |
| Router `mul_mat_f` F32 [2048,256] ×40 (n=4) | 84 MB | 4.6 (13.4%) | **≈18** | huge | **≈4.5**, launch/shape bound |
| Router chain softmax/argsort/get_rows/... (n≥2) | KB | 1.9 (5.6%) | launch-bound | — | ≈1.35 (L1 fusion) |
| Dense MMVQ (attention, GDN projections, shared experts, lm_head), n=4 | ≈2.04 GB weights | 9.1 (26.9%) | **≈224 apparent** | — | up to ~7; **attribution unresolved** (620 calls/step > 251 tensors, so the trace window likely includes MTP draft passes) |
| quantize_q8_1 | small | 3.1 (9%) | launch-bound | — | fusion (EPI-Q8) |
| k_bin_bcast / scale | small | 2.4 (7%) | launch-bound, 4.6 µs × ~520 | — | ≈2 (L3 fusion) |
| FA / gv (10 layers, f16 KV) | ctx dependent | ≈1.4 (4%) | — | — | ctx dependent |

## Ranked by recoverable ms × frequency (every round)

| # | Lever | Model | ms/round | % of round | Covered by |
|---|---|---|---|---|---|
| 1 | Router F32 GEMV for [2048,256] at n≥2: a single fused router+topk kernel with 64-row tiles and one launch per layer | A3B | ≤4.5 (C14 figure, **pre-knob**) | ≤13% | **Largely covered**: MMVF CDNA cap knob `GGML_HIP_MMVF_CDNA_MAX_NE11` (`79650eeab`, KEEP, A3B D=4 +13.6%) landed in C16, after the C14 trace. Residual on C18 unknown until BW-3 trace |
| 2 | 27B dense V5I M=8..16: stay ≥1.15 TB/s. Use split-K for the 33 MB 6144-class shapes (fewer CUs are idle on the tail) and fuse gate+up into one 189 MB launch | 27B | 3.3-4.4 | 7-10% | V5I covers the base. Split16 is FAIL_CORRECTNESS (r3) and is superseded by V5I at n≥12. Gate+up fusion is new |
| 3 | A3B dense MMVQ, if the 224 GB/s holds: route n=3 dense through V5I/q8wv or the MMVQ wide-row path | A3B | ≤7 (unverified) | ≤20% | V5I (A3B 0.988 is mostly noise). Needs the trace row below first |
| 4 | MUL_MAT_ID bandwidth: group slots by expert, use 128-bit loads, keep one q8_1 activation for the gate+up pair. Target ≥1.0-1.2 TB/s at n 3-16 | A3B | 1.4-1.6 | 4-5% | **4297a2caa** (row `ak-mmid-mf-gpu-20261122`, pending, no `out/` yet); split16 covers n 9-16 only |
| 5 | GDN recurrence at M rows: keep the state in LDS/registers across the M tokens and write only the snapshots the DF2 rollback needs | 27B | ≈1.2-2.4 | 3-5% | none. FAROWS-INPLACE and H12 do not touch GDN. Bytes approximate: needs a state-size check |

The tail (eltwise, norm, copy and quant: about 11 ms/fwd on 27B and 5-7 ms on A3B) is launch-bound, not
bandwidth-bound. Fusion work (EPI-Q8, add+rms_norm) recovers more there than any bandwidth fix.

## Missing data, and the rows that would fill it

1. **C18 27B DF2 rocprofv3 kernel trace, V5I env ON**, served llama-server dtree L arm at np1 and ctx about 8k. It
   gives the lm_head, attn_k/v, drafter forward, GDN bytes, and the FA share at served depth. Suggested row:
   `ak-c18-27b-df2-v5i-trace-gpu`.
2. **C18 A3B MTP rocprofv3 trace (n=3)** on the C18 binary, with the window split into draft and verify by the
   per-dispatch grid. It settles the 224 GB/s dense attribution and whether the router MMVF knob is live. V5I env needs
   two arms (ON and OFF), because V5I takes the dense A3B matmuls.
3. test-backend-ops perf on C18 for `MUL_MAT q8_0 m=248320 k=5120 n=1..16` and `m=1024 k=5120` (lm_head, k/v), V5I
   ON. Fold it into row 1 as one extra unit.
4. `ak-mmid-mf-gpu-20261122` results for lever 4. It is still pending.

**Correction (same day):** the A3B router row is a C14 measurement that predates the MMVF cap knob, which is now in C16/C18. Treat lever 1 as residual-only. Ranking by confidence: 2, 4, 5, 3, 1. AutoKernel seeds: research `scripts/kernel_rnd/autokernel/loop/seeds/hypotheses/21-bw-census-mi210-20261122.md`.

## CPU census (EPYC 9655 Zen 5, NPS4), added 2026-11-22

- **Ceiling (measured):** 259.8 GB/s read-sum on a half at 48 threads, measured in the same window as `q38p1-c13-20261117-r4`.
  The quarter value (24 threads) is **129.9 GB/s, derived as half/2**; no fresh per-quarter read-sum row exists, and that row is pending.
  The C0 figure of 66 GB/s per node is an older epoch and is not used.
- **Flag:** an open surface is anything below `cpu.flag_frac` = **0.75** of the ceiling. This is a starting threshold;
  **the operator can tune it** in the census JSON.
- **Top CPU levers:**
  1. Q38FN one-row forward: 61 GB/s, 47% of the quarter ceiling. The analysis doc's 55% used an assumed 110 GB/s. The
     dense part is worth about 10-18% of a round. Already covered by the C-series / INF-70 / AKX-ALL-25 streaming work, so it is linked, not duplicated.
  2. A3B CPU expert gate_up: 94 GB/s (72%), about 0.7 ms/step.
  3. A3B CPU shared expert: 89 GB/s (69%), about 0.2 ms/step.
  All other A3B families are at ≥76%.
- **Seeds:** research `seeds/hypotheses/22-bw-census-cpu-20261122.md`. The other CPU-served registry roles are not yet in
  the census; each needs a gap-census row first.

The tables below are generated by `census_update.py` from the committed census JSON. They show the baseline; the live
copy is at `/mnt/raid0/llm/tmp/ak-bw-census/`.

## Draft handoff box text (for the operator to file; not added)

- [ ] **BW-1 A3B router fused GEMV+topk** [inference] At A3B MTP verify n≥2, the F32 router `mul_mat_f` [2048,256]
  runs at about 18 GB/s (4.6 ms/step, 13.4%, C14 trace). Confirm the MMVF router knob is in C18, then replace the router
  matmul and the topk chain with one fused per-layer kernel. Gate: op µs at n=3,4,8 ≥2x, then A3B MTP e2e with 8 ABBA
  pairs and the CI rule. Est. +8-13% A3B. · done when: op gate verdict + e2e verdict recorded.
- [ ] **BW-2 27B V5I M=8-16 ≥1.15 TB/s** [inference] At M=8..16, V5I dense runs at 0.91-1.07 TB/s, with the 6144-class
  shapes below 1 TB/s. Try split-K for the ≤34 MB shapes and a fused gate+up launch. Gate: cells in
  `ak-q8wv-split16-gpu-20261122-r3` format, then 27B DF2 e2e with V5I env. Est. 3.3-4.4 ms/round (7-10%). · done when: op
  + e2e verdict.
- [ ] **BW-3 A3B dense attribution trace** [inference] Run the C18 A3B MTP rocprofv3 trace at n=3 with V5I ON and OFF.
  Decide whether dense MMVQ really runs at about 224 GB/s, and if so route it through V5I or q8wv. · done when: the trace
  is filed and the lever is confirmed or dropped.
- [ ] **BW-4 MMID bandwidth (4297a2caa)**: read `ak-mmid-mf-gpu-20261122` when it lands. Bar: ≥1000 GB/s at n≥4
  (currently 750-850). · done when: verdict filed.
- [ ] **BW-5 GDN multi-row state residency** [non-inference then inference] Keep the GDN state on-chip across the M
  verify rows and write only the rollback snapshots. First confirm the bytes from the state size and the RS_REPLAY mode.
  Est. 1.2-2.4 ms/round on 27B. · done when: byte check + op gate.

## Generated census table

<!-- BW-CENSUS:BEGIN generated by census_update.py -->

### GPU (MI210)

| Rank | Model | Kernel class | Shape | n | MB/call | µs | GB/s | vs 1 TB/s | vs 1.5 TB/s | calls/round | recoverable ms/round @1.2 | Status | Seed | Source row |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 27b-q8_0 | ffn_gate_up_v5i | 17408x5120 | 16 | 94.7 | 93.0 | 1018 | +18 | -482 | 128 | 1.80 | ok | BW-DENSE-M16 | `ak-q8wv-split16-gpu-20261122-r3` |
| 2 | 27b-q8_0 | ffn_gate_up_v5i | 17408x5120 | 8 | 94.7 | 90.4 | 1047 | +47 | -453 | 128 | 1.47 | ok | BW-DENSE-M16 | `ak-q8wv-split16-gpu-20261122-r3` |
| 3 | 27b-q8_0 | ffn_gate_up_v5i | 17408x5120 | 4 | 94.7 | 90.1 | 1052 | +52 | -448 | 128 | 1.43 | ok | - | `ak-q8wv-split16-gpu-20261122-r3` |
| 4 | 27b-q8_0 | ffn_down_v5i | 5120x17408 | 16 | 94.7 | 93.1 | 1017 | +17 | -483 | 64 | 0.91 | ok | BW-DENSE-M16 | `ak-q8wv-split16-gpu-20261122-r3` |
| 5 | 27b-q8_0 | ffn_gate_up_v5i | 17408x5120 | 3 | 94.7 | 84.0 | 1127 | +127 | -373 | 128 | 0.66 | ok | - | `ak-q8wv-split16-gpu-20261122-r3` |
| 6 | 27b-q8_0 | ffn_down_v5i | 5120x17408 | 8 | 94.7 | 88.7 | 1067 | +67 | -433 | 64 | 0.63 | ok | BW-DENSE-M16 | `ak-q8wv-split16-gpu-20261122-r3` |
| 7 | 27b-q8_0 | ffn_gate_up_v5i | 17408x5120 | 1 | 94.7 | 83.6 | 1133 | +133 | -367 | 128 | 0.60 | ok | - | `ak-q8wv-split16-gpu-20261122-r3` |
| 8 | 27b-q8_0 | ssm_out+attn_output_v5i | 5120x6144 | 16 | 33.4 | 36.9 | 906 | -94 | -594 | 64 | 0.58 | open_surface | BW-DENSE-M16 | `ak-q8wv-split16-gpu-20261122-r3` |
| 9 | 27b-q8_0 | ffn_down_v5i | 5120x17408 | 4 | 94.7 | 86.5 | 1094 | +94 | -406 | 64 | 0.49 | ok | - | `ak-q8wv-split16-gpu-20261122-r3` |
| 10 | 27b-q8_0 | gdn_attn_qkv_v5i | 10240x5120 | 16 | 55.7 | 56.1 | 993 | -7 | -507 | 48 | 0.46 | open_surface | BW-DENSE-M16 | `ak-q8wv-split16-gpu-20261122-r3` |
| 11 | 27b-q8_0 | ffn_down_v5i | 5120x17408 | 1 | 94.7 | 86.1 | 1100 | +100 | -400 | 64 | 0.46 | ok | - | `ak-q8wv-split16-gpu-20261122-r3` |
| 12 | 27b-q8_0 | gdn_attn_gate_v5i | 6144x5120 | 16 | 33.4 | 36.6 | 913 | -87 | -587 | 48 | 0.42 | open_surface | BW-DENSE-M16 | `ak-q8wv-split16-gpu-20261122-r3` |
| 13 | 27b-q8_0 | ffn_down_v5i | 5120x17408 | 3 | 94.7 | 85.4 | 1108 | +108 | -392 | 64 | 0.42 | ok | - | `ak-q8wv-split16-gpu-20261122-r3` |
| 14 | 27b-q8_0 | ssm_out+attn_output_v5i | 5120x6144 | 8 | 33.4 | 34.2 | 976 | -24 | -524 | 64 | 0.41 | open_surface | BW-DENSE-M16 | `ak-q8wv-split16-gpu-20261122-r3` |
| 15 | 27b-q8_0 | gdn_attn_gate_v5i | 6144x5120 | 8 | 33.4 | 35.6 | 939 | -61 | -561 | 48 | 0.37 | open_surface | BW-DENSE-M16 | `ak-q8wv-split16-gpu-20261122-r3` |
| 16 | 27b-q8_0 | ssm_out+attn_output_v5i | 5120x6144 | 4 | 33.4 | 33.5 | 999 | -1 | -501 | 64 | 0.36 | open_surface | - | `ak-q8wv-split16-gpu-20261122-r3` |
| 17 | 27b-q8_0 | gdn_attn_qkv_v5i | 10240x5120 | 8 | 55.7 | 53.3 | 1045 | +45 | -455 | 48 | 0.33 | ok | BW-DENSE-M16 | `ak-q8wv-split16-gpu-20261122-r3` |
| 18 | 27b-q8_0 | ssm_out+attn_output_v5i | 5120x6144 | 3 | 33.4 | 33.0 | 1014 | +14 | -486 | 64 | 0.33 | ok | - | `ak-q8wv-split16-gpu-20261122-r3` |
| 19 | 27b-q8_0 | ssm_out+attn_output_v5i | 5120x6144 | 1 | 33.4 | 32.8 | 1019 | +19 | -481 | 64 | 0.32 | ok | - | `ak-q8wv-split16-gpu-20261122-r3` |
| 20 | 27b-q8_0 | gdn_attn_gate_v5i | 6144x5120 | 3 | 33.4 | 34.1 | 979 | -21 | -521 | 48 | 0.30 | open_surface | - | `ak-q8wv-split16-gpu-20261122-r3` |
| 21 | 27b-q8_0 | gdn_attn_gate_v5i | 6144x5120 | 4 | 33.4 | 33.5 | 996 | -4 | -504 | 48 | 0.27 | open_surface | - | `ak-q8wv-split16-gpu-20261122-r3` |
| 22 | 27b-q8_0 | gdn_attn_gate_v5i | 6144x5120 | 1 | 33.4 | 32.7 | 1023 | +23 | -477 | 48 | 0.23 | ok | - | `ak-q8wv-split16-gpu-20261122-r3` |
| 23 | 27b-q8_0 | gdn_attn_qkv_v5i | 10240x5120 | 4 | 55.7 | 51.2 | 1087 | +87 | -413 | 48 | 0.23 | ok | - | `ak-q8wv-split16-gpu-20261122-r3` |
| 24 | 27b-q8_0 | gdn_attn_qkv_v5i | 10240x5120 | 3 | 55.7 | 50.9 | 1095 | +95 | -405 | 48 | 0.21 | ok | - | `ak-q8wv-split16-gpu-20261122-r3` |
| 25 | 27b-q8_0 | attn_q_v5i | 12288x5120 | 16 | 66.8 | 68.2 | 981 | -19 | -519 | 16 | 0.20 | open_surface | BW-DENSE-M16 | `ak-q8wv-split16-gpu-20261122-r3` |
| 26 | 27b-q8_0 | gdn_attn_qkv_v5i | 10240x5120 | 1 | 55.7 | 49.7 | 1120 | +120 | -380 | 48 | 0.16 | ok | - | `ak-q8wv-split16-gpu-20261122-r3` |
| 27 | 27b-q8_0 | attn_q_v5i | 12288x5120 | 8 | 66.8 | 64.5 | 1036 | +36 | -464 | 16 | 0.14 | ok | BW-DENSE-M16 | `ak-q8wv-split16-gpu-20261122-r3` |
| 28 | 27b-q8_0 | attn_q_v5i | 12288x5120 | 3 | 66.8 | 63.5 | 1052 | +52 | -448 | 16 | 0.12 | ok | - | `ak-q8wv-split16-gpu-20261122-r3` |
| 29 | 27b-q8_0 | attn_q_v5i | 12288x5120 | 4 | 66.8 | 62.5 | 1070 | +70 | -430 | 16 | 0.11 | ok | - | `ak-q8wv-split16-gpu-20261122-r3` |
| 30 | 27b-q8_0 | attn_q_v5i | 12288x5120 | 1 | 66.8 | 60.8 | 1099 | +99 | -401 | 16 | 0.08 | ok | - | `ak-q8wv-split16-gpu-20261122-r3` |

### CPU (EPYC 9655, NPS4) — open surface below 75% of the measured ceiling (operator-tunable `cpu.flag_frac`)

| Rank | Model | Op class | Config | MB/step | ms/step | GB/s | Ceiling GB/s | % of ceiling | Share of step | recoverable ms @80% | Status | Seed | Source row |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | q38fn-ud-iq4xs-cpu | forward_m1_dense | quarter-24t | 5700 | 94.00 | 60.6 | 129.9 | 47% | - | 39.15 | open_surface | CPU-Q38FN-M1-DENSE | `epyc-root docs/design/q38fn-cpu-verify-weight-reuse-20261122.md (aed195fda) r3` |
| 2 | a3b-q8_0-cpu | MUL_MAT_ID:exps_gate_up | quarter-24t | 713 | 7.59 | 94.0 | 129.9 | 72% | 18.7% | 0.73 | open_surface | CPU-A3B-MMID | `a3b-cpu-gap-census-20261121` |
| 3 | a3b-q8_0-cpu | MUL_MAT:shared_expert | quarter-24t | 138 | 1.54 | 89.4 | 129.9 | 69% | 3.8% | 0.21 | open_surface | CPU-A3B-SHEXP | `a3b-cpu-gap-census-20261121` |
| 4 | a3b-q8_0-cpu | MUL_MAT_ID:exps_down | quarter-24t | 357 | 3.62 | 98.7 | 129.9 | 76% | 8.9% | 0.18 | ok | - | `a3b-cpu-gap-census-20261121` |
| 5 | a3b-q8_0-cpu | MUL_MAT:gdn_proj | quarter-24t | 1069 | 10.43 | 102.5 | 129.9 | 79% | 25.7% | 0.15 | ok | - | `a3b-cpu-gap-census-20261121` |
| 6 | a3b-q8_0-cpu | MUL_MAT:fullattn_proj | quarter-24t | 300 | 2.87 | 104.4 | 129.9 | 80% | 7.1% | 0.00 | ok | - | `a3b-cpu-gap-census-20261121` |
| 7 | a3b-q8_0-cpu | MUL_MAT:lm_head | quarter-24t | 540 | 4.88 | 110.7 | 129.9 | 85% | 12.0% | 0.00 | ok | - | `a3b-cpu-gap-census-20261121` |

<!-- BW-CENSUS:END -->
