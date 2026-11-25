# MI210 served-path kernel bandwidth census (2026-11-22)

Status: DRAFT analysis. Existing data only, no compute. [no-belief: analysis of existing rows; no new measurement]

Operator rule (2026-11-22): a GPU kernel whose implied bandwidth is below **1 TB/s** is an optimization surface.
References: MI210 ceiling 1638 GB/s, one value everywhere (operator ruling 2026-11-25, HBM nameplate; replaces the
1500 GB/s measured-stream value set 2026-11-24), V5I dense Q8 about 1.0-1.2 TB/s.

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

| Rank | Model | Kernel class | Shape | n | MB/call | µs | GB/s | vs 1 TB/s | vs 1.638 TB/s | calls/round | recoverable ms/round @1.2 | Status | Seed | Source row |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 27b-q8_0 | vk_launch_tail | ctx8192 | 8 | 0.4 | 12.3 | 34 | -966 | -1604 | 1140 | 13.60 | open_surface | BW-DENSE-M16 | `ak-27b-verify-kernel-roofline-census-gpu-20261124-r2` |
| 2 | 27b-q8_0 | vk_launch_tail | ctx8192 | 4 | 0.3 | 6.0 | 51 | -949 | -1587 | 1140 | 6.57 | open_surface | - | `ak-27b-verify-kernel-roofline-census-gpu-20261124-r2` |
| 3 | 27b-q8_0 | vk_launch_tail | ctx32768 | 4 | 0.3 | 6.0 | 52 | -948 | -1586 | 1140 | 6.52 | open_surface | - | `ak-27b-verify-kernel-roofline-census-gpu-20261124-r2` |
| 4 | 27b-q8_0 | vk_launch_tail | ctx32768 | 8 | 0.4 | 6.0 | 69 | -931 | -1569 | 1140 | 6.49 | open_surface | BW-DENSE-M16 | `ak-27b-verify-kernel-roofline-census-gpu-20261124-r2` |
| 5 | 27b-q8_0 | vk_launch_tail | ctx1024 | 4 | 0.3 | 5.9 | 52 | -948 | -1586 | 1140 | 6.43 | open_surface | - | `ak-27b-verify-kernel-roofline-census-gpu-20261124-r2` |
| 6 | 27b-q8_0 | vk_launch_tail | ctx1024 | 8 | 0.4 | 6.0 | 69 | -931 | -1569 | 1140 | 6.42 | open_surface | BW-DENSE-M16 | `ak-27b-verify-kernel-roofline-census-gpu-20261124-r2` |
| 7 | 27b-q8_0 | vk_launch_tail | ctx32768 | 1 | 0.3 | 5.8 | 45 | -955 | -1593 | 948 | 5.32 | open_surface | - | `ak-27b-verify-kernel-roofline-census-gpu-20261124-r2` |
| 8 | 27b-q8_0 | vk_launch_tail | ctx8192 | 1 | 0.3 | 5.8 | 46 | -954 | -1592 | 948 | 5.27 | open_surface | - | `ak-27b-verify-kernel-roofline-census-gpu-20261124-r2` |
| 9 | 27b-q8_0 | vk_launch_tail | ctx1024 | 1 | 0.3 | 5.8 | 46 | -954 | -1592 | 948 | 5.27 | open_surface | - | `ak-27b-verify-kernel-roofline-census-gpu-20261124-r2` |
| 10 | 27b-q8_0 | gv_fattn_q8kv | ctx32768 | 8 | 83.7 | 289.3 | 289 | -711 | -1349 | 16 | 3.51 | open_surface | BW-DENSE-M16 | `ak-27b-verify-kernel-roofline-census-gpu-20261124-r2` |
| 11 | 27b-q8_0 | gv_fattn_q8kv | ctx32768 | 4 | 79.4 | 269.6 | 294 | -706 | -1344 | 16 | 3.25 | open_surface | - | `ak-27b-verify-kernel-roofline-census-gpu-20261124-r2` |
| 12 | 27b-q8_0 | gv_fattn_q8kv | ctx32768 | 1 | 76.9 | 260.2 | 296 | -704 | -1342 | 16 | 3.14 | open_surface | - | `ak-27b-verify-kernel-roofline-census-gpu-20261124-r2` |
| 13 | 27b-q8_0 | vk_gated_delta_net | ctx8192 | 8 | 4.2 | 65.3 | 64 | -936 | -1574 | 48 | 2.97 | open_surface | BW-DENSE-M16 | `ak-27b-verify-kernel-roofline-census-gpu-20261124-r2` |
| 14 | 27b-q8_0 | dense_verify_aggregate_v5i | 27.02GB | 8 | 27020.0 | 25232.4 | 1071 | +71 | -567 | 1 | 2.72 | ok | BW-DENSE-M16 | `ak-c18-27b-df2-v5i-trace-gpu-20261122` |
| 15 | 27b-q8_0 | vk_actquant | ctx1024 | 8 | 0.2 | 4.4 | 39 | -961 | -1599 | 625 | 2.68 | open_surface | BW-DENSE-M16 | `ak-27b-verify-kernel-roofline-census-gpu-20261124-r2` |
| 16 | 27b-q8_0 | vk_actquant | ctx32768 | 8 | 0.2 | 4.4 | 39 | -961 | -1599 | 625 | 2.67 | open_surface | BW-DENSE-M16 | `ak-27b-verify-kernel-roofline-census-gpu-20261124-r2` |
| 17 | 27b-q8_0 | vk_actquant | ctx8192 | 8 | 0.2 | 4.4 | 39 | -961 | -1599 | 625 | 2.67 | open_surface | BW-DENSE-M16 | `ak-27b-verify-kernel-roofline-census-gpu-20261124-r2` |
| 18 | 27b-q8_0 | served_weight_gemv_v5i | served-v5i | 8 | 33159.9 | 30024.3 | 1104 | +104 | -534 | 1 | 2.39 | ok | BW-DENSE-M16 | `ak-27b-served-decode-profile-gpu-20261125` |
| 19 | 27b-q8_0 | gv_fattn_f16kv | ctx11446 | 8 | 46.9 | 163.1 | 288 | -712 | -1350 | 16 | 1.98 | open_surface | BW-DENSE-M16 | `ak-c18-27b-df2-v5i-trace-gpu-20261122` |
| 20 | 27b-q8_0 | gv_fattn_q8kv | ctx8192 | 8 | 24.9 | 138.0 | 180 | -820 | -1458 | 16 | 1.88 | open_surface | BW-DENSE-M16 | `ak-27b-verify-kernel-roofline-census-gpu-20261124-r2` |
| 21 | 27b-q8_0 | ffn_gate_up_v5i | 17408x5120 | 16 | 94.7 | 93.0 | 1018 | +18 | -620 | 128 | 1.80 | ok | BW-DENSE-M16 | `ak-q8wv-split16-gpu-20261122-r3` |
| 22 | 27b-q8_0 | gv_fattn_q8kv | ctx8192 | 4 | 22.0 | 125.3 | 175 | -825 | -1463 | 16 | 1.71 | open_surface | - | `ak-27b-verify-kernel-roofline-census-gpu-20261124-r2` |
| 23 | 27b-q8_0 | gv_fattn_q8kv | ctx8192 | 1 | 19.7 | 121.2 | 163 | -837 | -1475 | 16 | 1.68 | open_surface | - | `ak-27b-verify-kernel-roofline-census-gpu-20261124-r2` |
| 24 | 27b-q8_0 | vk_actquant | ctx1024 | 4 | 0.1 | 4.5 | 26 | -974 | -1612 | 377 | 1.67 | open_surface | - | `ak-27b-verify-kernel-roofline-census-gpu-20261124-r2` |
| 25 | 27b-q8_0 | vk_actquant | ctx32768 | 4 | 0.1 | 4.5 | 26 | -974 | -1612 | 377 | 1.67 | open_surface | - | `ak-27b-verify-kernel-roofline-census-gpu-20261124-r2` |
| 26 | 27b-q8_0 | vk_actquant | ctx8192 | 4 | 0.1 | 4.5 | 26 | -974 | -1612 | 377 | 1.67 | open_surface | - | `ak-27b-verify-kernel-roofline-census-gpu-20261124-r2` |
| 27 | 27b-q8_0 | vk_actquant | ctx1024 | 1 | 0.0 | 4.5 | 7 | -993 | -1631 | 345 | 1.54 | open_surface | - | `ak-27b-verify-kernel-roofline-census-gpu-20261124-r2` |
| 28 | 27b-q8_0 | vk_actquant | ctx32768 | 1 | 0.0 | 4.5 | 7 | -993 | -1631 | 345 | 1.54 | open_surface | - | `ak-27b-verify-kernel-roofline-census-gpu-20261124-r2` |
| 29 | 27b-q8_0 | vk_actquant | ctx8192 | 1 | 0.0 | 4.5 | 7 | -993 | -1631 | 345 | 1.54 | open_surface | - | `ak-27b-verify-kernel-roofline-census-gpu-20261124-r2` |
| 30 | 27b-q8_0 | ffn_gate_up_v5i | 17408x5120 | 8 | 94.7 | 90.4 | 1047 | +47 | -591 | 128 | 1.47 | ok | BW-DENSE-M16 | `ak-q8wv-split16-gpu-20261122-r3` |
| 31 | 27b-q8_0 | ffn_gate_up_v5i | 17408x5120 | 4 | 94.7 | 90.1 | 1052 | +52 | -586 | 128 | 1.43 | ok | BW-DENSE-M16 | `ak-q8wv-split16-gpu-20261122-r3` |
| 32 | 27b-q8_0 | vk_gated_delta_net | ctx1024 | 8 | 4.2 | 32.0 | 132 | -868 | -1506 | 48 | 1.37 | open_surface | BW-DENSE-M16 | `ak-27b-verify-kernel-roofline-census-gpu-20261124-r2` |
| 33 | 27b-q8_0 | vk_gated_delta_net | ctx32768 | 8 | 4.2 | 30.9 | 137 | -863 | -1501 | 48 | 1.31 | open_surface | BW-DENSE-M16 | `ak-27b-verify-kernel-roofline-census-gpu-20261124-r2` |
| 34 | 27b-q8_0 | gv_fattn_q8kv | ctx1024 | 8 | 3.0 | 69.7 | 43 | -957 | -1595 | 16 | 1.07 | open_surface | BW-DENSE-M16 | `ak-27b-verify-kernel-roofline-census-gpu-20261124-r2` |
| 35 | 27b-q8_0 | gv_fattn_q8kv | ctx1024 | 4 | 2.9 | 66.7 | 44 | -956 | -1594 | 16 | 1.03 | open_surface | - | `ak-27b-verify-kernel-roofline-census-gpu-20261124-r2` |
| 36 | 27b-q8_0 | gv_fattn_q8kv | ctx1024 | 1 | 2.8 | 65.4 | 43 | -957 | -1595 | 16 | 1.01 | open_surface | - | `ak-27b-verify-kernel-roofline-census-gpu-20261124-r2` |
| 37 | 27b-q8_0 | ffn_down_v5i | 5120x17408 | 16 | 94.7 | 93.1 | 1017 | +17 | -621 | 64 | 0.91 | ok | BW-DENSE-M16 | `ak-q8wv-split16-gpu-20261122-r3` |
| 38 | 27b-q8_0 | vk_q8sk_mul_mat | ctx32768:q8sk_mul_mat:g3840x64 | 8 | 0.4 | 9.0 | 40 | -960 | -1598 | 96 | 0.83 | open_surface | BW-DENSE-M16 | `ak-27b-verify-kernel-roofline-census-gpu-20261124-r2` |
| 39 | 27b-q8_0 | vk_q8sk_mul_mat | ctx8192:q8sk_mul_mat:g3840x64 | 8 | 0.4 | 7.8 | 46 | -954 | -1592 | 96 | 0.72 | open_surface | BW-DENSE-M16 | `ak-27b-verify-kernel-roofline-census-gpu-20261124-r2` |
| 40 | 27b-q8_0 | vk_gated_delta_net | ctx8192 | 4 | 4.0 | 18.4 | 218 | -782 | -1420 | 48 | 0.72 | open_surface | - | `ak-27b-verify-kernel-roofline-census-gpu-20261124-r2` |

### CPU (EPYC 9655, NPS4) — open surface below 75% of the measured ceiling (operator-tunable `cpu.flag_frac`)

| Rank | Model | Op class | Config | MB/step | ms/step | GB/s | Ceiling GB/s | % of ceiling | Share of step | recoverable ms @80% | Status | Seed | Source row |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | q38fn-ud-iq4xs-cpu | forward_m1_dense | quarter-24t | 5700 | 94.00 | 60.6 | 129.0 | 47% | - | 38.77 | open_surface | CPU-Q38FN-M1-DENSE | `epyc-root docs/design/q38fn-cpu-verify-weight-reuse-20261122.md (aed195fda) r3` |
| 2 | q38fn-ud-iq4xs-cpu | MUL_MAT:gdn_proj | quarter-24t | 2247 | 25.86 | 86.9 | 129.0 | 67% | 26.4% | 4.08 | open_surface | - | `ak-q38fn-cpu-d32k-gemv-diag-20261123` |
| 3 | q38fn-ud-iq4xs-cpu | MUL_MAT_ID:exps_gate_up | quarter-24t | 679 | 9.22 | 73.7 | 129.0 | 57% | 10.2% | 2.64 | open_surface | - | `ak-q38fn-cpu-gap-census-20261122` |
| 4 | q38fn-ud-iq4xs-cpu | MUL_MAT:other_weight | quarter-24t | 719 | 9.54 | 75.4 | 129.0 | 58% | 9.1% | 2.57 | open_surface | - | `ak-q38fn-cpu-d32k-gemv-diag-20261123` |
| 5 | q38fn-ud-iq4xs-cpu | MUL_MAT_ID:exps_gate_up | quarter-24t | 679 | 8.60 | 78.9 | 129.0 | 61% | 8.8% | 2.02 | open_surface | - | `ak-q38fn-cpu-d32k-gemv-diag-20261123` |
| 6 | q38fn-ud-iq4xs-cpu | MUL_MAT:other_weight | quarter-24t | 719 | 8.33 | 86.3 | 129.0 | 67% | 10.4% | 1.36 | open_surface | - | `ak-c21-census-refresh-cpu-20261124-r4` |
| 7 | q38fn-ud-iq4xs-cpu | MUL_MAT:fullattn_proj | quarter-24t | 635 | 7.25 | 87.6 | 129.0 | 68% | 7.2% | 1.09 | open_surface | - | `ak-q38fn-cpu-d32k-gemv-diag-20261123` |
| 8 | q38fn-ud-iq4xs-cpu | MUL_MAT_ID:exps_down | quarter-24t | 483 | 5.51 | 87.8 | 129.0 | 68% | 5.8% | 0.82 | open_surface | - | `ak-q38fn-cpu-d32k-gemv-diag-20261123` |
| 9 | a3b-q8_0-cpu | MUL_MAT:shared_expert@ubench | quarter-24t | 3 | 0.05 | 66.3 | 129.0 | 51% | - | 0.74 | open_surface | - | `ak-a3b-cpu-mmid-gateup-ubench-20261122-r2` |
| 10 | a3b-q8_0-cpu | MUL_MAT:shared_expert@ubench | quarter-24t | 3 | 0.05 | 66.8 | 129.0 | 52% | - | 0.72 | open_surface | - | `ak-a3b-cpu-mmid-gateup-ubench-20261122-r2` |
| 11 | q38fn-ud-iq4xs-cpu | MUL_MAT:shared_expert | quarter-24t | 251 | 3.11 | 80.6 | 129.0 | 62% | 2.9% | 0.68 | open_surface | - | `ak-q38fn-cpu-d32k-gemv-diag-20261123` |
| 12 | a3b-q8_0-cpu | MUL_MAT:shared_expert@ubench | quarter-24t | 3 | 0.05 | 69.2 | 129.0 | 54% | - | 0.65 | open_surface | - | `ak-a3b-cpu-mmid-gateup-ubench-20261122-r2` |
| 13 | a3b-q8_0-cpu | MUL_MAT:shared_expert@ubench | quarter-24t | 3 | 0.05 | 70.1 | 129.0 | 54% | - | 0.63 | open_surface | - | `ak-a3b-cpu-mmid-gateup-ubench-20261122-r2` |
| 14 | q38fn-ud-iq4xs-cpu | MUL_MAT:shared_expert | quarter-24t | 251 | 2.77 | 90.5 | 129.0 | 70% | 3.5% | 0.34 | open_surface | - | `ak-c21-census-refresh-cpu-20261124-r4` |
| 15 | q38fn-ud-iq4xs-cpu | MUL_MAT:moe_router | quarter-24t | 252 | 2.77 | 90.8 | 129.0 | 70% | 3.0% | 0.33 | open_surface | - | `ak-q38fn-cpu-d32k-gemv-diag-20261123` |
| 16 | q38fn-ud-iq4xs-cpu | MUL_MAT:moe_router | quarter-24t | 252 | 2.75 | 91.4 | 129.0 | 71% | 3.4% | 0.31 | open_surface | - | `ak-c21-census-refresh-cpu-20261124-r4` |
| 17 | a3b-q8_0-cpu | MUL_MAT:shexp_down@ubench | quarter-24t | 1 | 0.02 | 61.8 | 129.0 | 48% | - | 0.30 | open_surface | - | `ak-a3b-cpu-shexp-verify-gap-20261123-r2` |
| 18 | a3b-q8_0-cpu | MUL_MAT:shexp_down@ubench | quarter-24t | 1 | 0.02 | 65.4 | 129.0 | 51% | - | 0.26 | open_surface | - | `ak-a3b-cpu-shexp-verify-gap-20261123-r2` |
| 19 | q38fn-ud-iq4xs-cpu | MUL_MAT_ID:exps_down | quarter-24t | 483 | 4.94 | 97.9 | 129.0 | 76% | 6.2% | 0.25 | ok | - | `ak-c21-census-refresh-cpu-20261124-r4` |
| 20 | a3b-q8_0-cpu | MUL_MAT:shared_expert@ubench | quarter-24t | 3 | 0.04 | 87.4 | 129.0 | 68% | - | 0.24 | open_surface | - | `ak-a3b-cpu-mmid-gateup-ubench-20261122-r2` |
| 21 | a3b-q8_0-cpu | MUL_MAT:shexp_down@ubench | quarter-24t | 1 | 0.02 | 69.8 | 129.0 | 54% | - | 0.21 | open_surface | - | `ak-a3b-cpu-shexp-verify-gap-20261123-r2` |
| 22 | a3b-q8_0-cpu | MUL_MAT_ID:exps_gate_up@ubench | quarter-24t | 68 | 0.67 | 102.4 | 129.0 | 79% | - | 0.21 | ok | - | `ak-a3b-cpu-mmid-gateup-ubench-20261122-r2` |
| 23 | a3b-q8_0-cpu | MUL_MAT:shared_expert | quarter-24t | 138 | 1.54 | 89.4 | 129.0 | 69% | 3.8% | 0.21 | open_surface | CPU-A3B-SHEXP | `a3b-cpu-gap-census-20261121` |
| 24 | q38fn-ud-iq4xs-cpu | MUL_MAT:lm_head | quarter-24t | 528 | 5.33 | 99.2 | 129.0 | 77% | 6.1% | 0.21 | ok | - | `ak-q38fn-cpu-d32k-gemv-diag-20261123` |
| 25 | a3b-q8_0-cpu | MUL_MAT_ID:exps_gate_up@ubench | quarter-24t | 84 | 0.82 | 102.6 | 129.0 | 80% | - | 0.18 | ok | - | `ak-a3b-cpu-mmid-gateup-ubench-20261122-r2` |
| 26 | a3b-q8_0-cpu | MUL_MAT:shexp_down@ubench | quarter-24t | 1 | 0.01 | 74.6 | 129.0 | 58% | - | 0.17 | open_surface | - | `ak-a3b-cpu-shexp-verify-gap-20261123-r2` |
| 27 | a3b-q8_0-cpu | MUL_MAT_ID:exps_gate_up@ubench | quarter-24t | 35 | 0.34 | 102.0 | 129.0 | 79% | - | 0.17 | ok | - | `ak-a3b-cpu-mmid-gateup-ubench-20261122-r2` |
| 28 | a3b-q8_0-cpu | MUL_MAT_ID:exps_down | quarter-24t | 357 | 3.62 | 98.7 | 129.0 | 76% | 8.9% | 0.16 | ok | - | `a3b-cpu-gap-census-20261121` |
| 29 | q38fn-ud-iq4xs-cpu | MUL_MAT:gdn_proj | quarter-24t | 2247 | 21.92 | 102.5 | 129.0 | 80% | 27.4% | 0.14 | ok | - | `ak-c21-census-refresh-cpu-20261124-r4` |
| 30 | q38fn-ud-iq4xs-cpu | MUL_MAT:indexer | quarter-24t | 39 | 0.51 | 77.0 | 129.0 | 60% | 0.6% | 0.13 | open_surface | - | `ak-c21-census-refresh-cpu-20261124-r4` |
| 31 | a3b-q8_0-cpu | MUL_MAT_ID:exps_gate_up | quarter-24t | 713 | 7.03 | 101.4 | 129.0 | 79% | 17.7% | 0.12 | ok | CPU-A3B-MMID | `a3b-cpu-gap-census-20261122-r2` |
| 32 | q38fn-ud-iq4xs-cpu | MUL_MAT:indexer_weight | quarter-24t | 39 | 0.49 | 80.0 | 129.0 | 62% | - | 0.11 | open_surface | - | `ak-q38fn-cpu-d32k-gemv-diag-20261123` |
| 33 | a3b-q8_0-cpu | MUL_MAT_ID:exps_gate_up@ubench | quarter-24t | 18 | 0.18 | 101.6 | 129.0 | 79% | - | 0.11 | ok | - | `ak-a3b-cpu-mmid-gateup-ubench-20261122-r2` |
| 34 | a3b-q8_0-cpu | MUL_MAT:gdn_proj | quarter-24t | 1069 | 10.43 | 102.5 | 129.0 | 80% | 25.7% | 0.07 | ok | - | `a3b-cpu-gap-census-20261121` |
| 35 | q38fn-ud-iq4xs-cpu | MUL_MAT:fullattn_proj | quarter-24t | 635 | 6.23 | 102.0 | 129.0 | 79% | 7.8% | 0.07 | ok | - | `ak-c21-census-refresh-cpu-20261124-r4` |
| 36 | a3b-q8_0-cpu | MUL_MAT:shexp_down@ubench | quarter-24t | 1 | 0.01 | 97.5 | 129.0 | 76% | - | 0.03 | ok | - | `ak-a3b-cpu-shexp-verify-gap-20261123-r2` |
| 37 | q38fn-ud-iq4xs-cpu | MUL_MAT:lm_head | quarter-24t | 528 | 5.13 | 102.9 | 129.0 | 80% | 6.4% | 0.01 | ok | - | `ak-c21-census-refresh-cpu-20261124-r4` |
| 38 | a3b-q8_0-cpu | MUL_MAT:fullattn_proj | quarter-24t | 300 | 2.87 | 104.4 | 129.0 | 81% | 7.1% | 0.00 | ok | - | `a3b-cpu-gap-census-20261121` |
| 39 | a3b-q8_0-cpu | MUL_MAT:lm_head | quarter-24t | 540 | 4.88 | 110.7 | 129.0 | 86% | 12.0% | 0.00 | ok | - | `a3b-cpu-gap-census-20261121` |
| 40 | a3b-q8_0-cpu | MUL_MAT_ID:exps_gate_up@ubench | quarter-24t | 52 | 0.50 | 103.8 | 129.0 | 80% | - | 0.00 | ok | - | `ak-a3b-cpu-mmid-gateup-ubench-20261122-r2` |

### Roofline parity (gap x share of step)

Ceilings (operator 2026-11-25, one per device): MI210 1638 GB/s, CPU quarter-24t 129 GB/s, CPU full host 520 GB/s. Shares: 27B per 45.7 ms round (C18 trace), A3B GPU per 34 ms busy step (C14), CPU per census step. A3B GPU is a candidate lane, not served (operator 2026-11-25).

| # | Path | Op | Ours % roofline | Best ref % | Ref | Gap pp | Share of step | Score (pp) | Covered by | C21 refresh | Source |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | flash-next-cpu | forward m1 dense (UD-IQ4_XS) | 47 | 88 | cpu-avx512-gemv | 41 | 14.0% | 5.7 | Q38P-1; INF-70; AKX-ALL-25 | yes | q38fn-cpu-verify-weight-reuse-20261122 r3 (quarter-24t; served NUMA_FULL needs full-host ceiling) |
| 2 | 27b-df2-mi210 | gv_fattn + merge (verify FA) | 11 | 88 | cuda-flashdecode | 77 | 7.1% | 5.5 | ak-gvfattn-lds/splits/served rows; G3 | yes | same + ak-g3-trace-read-20261124 (130-235 GB/s at 8-16k) |
| 3 | a3b-mtp-cpu | MUL_MAT_ID exps_gate_up | 73 | 88 | cpu-avx512-gemv | 15 | 18.7% | 2.8 | AK-CPU-A3B-MMID (NO_LEVER) | - | a3b-cpu-gap-census-20261121 |
| 4 | a3b-mtp-cpu | gdn_proj | 79 | 88 | cpu-avx512-gemv | 9 | 25.7% | 2.2 | **none** | - | a3b-cpu-gap-census-20261121 |
| 5 | a3b-mtp-cpu | shared expert N>=2 | 53 | 88 | cpu-avx512-gemv | 35 | 3.8% | 1.3 | AK-CPU-A3B-SHEXP-VERIFY-GAP | - | ak-a3b-cpu-mmid-gateup-ubench-20261122-r2 |
| 6 | a3b-mtp-cpu | MUL_MAT_ID exps_down | 77 | 88 | cpu-avx512-gemv | 11 | 8.9% | 1.0 | **none** | - | a3b-cpu-gap-census-20261121 |
| 7 | a3b-mtp-cpu | fullattn_proj | 81 | 88 | cpu-avx512-gemv | 7 | 7.1% | 0.5 | **none** | - | a3b-cpu-gap-census-20261121 |
| 8 | a3b-mtp-cpu | lm_head | 86 | 88 | cpu-avx512-gemv | 2 | 12.0% | 0.3 | **none** | - | a3b-cpu-gap-census-20261121 |
| 9 | 27b-df2-mi210 | verify dense Q8 GEMV/GEMM (q8mf6, V5I) | 65 | no published measurement | cuda-gemv | - | 55.2% | - | V5I base; C21 V2 RRS fold | yes | ak-c18-27b-df2-v5i-trace-gpu-20261122 |
| 10 | 27b-df2-mi210 | GDN recurrence (fused tree GDN) | 12 | no published measurement | cuda-scan | - | 4.6% | - | speculative-decoding.md batched tree GDN lane | yes | C18 trace; bytes approximate |
| 11 | 27b-df2-mi210 | actquant (q8mf_pre_i8 + q8sk_quantize) | 35 | no published measurement | cuda-fused-tail | - | 4.6% | - | AK-BW-27B-ACTQUANT-FUSE | - | C18 trace |
| 12 | 27b-df2-mi210 | launch-bound tail (eltwise/norm/copy/rope/conv) | 35 | no published measurement | cuda-fused-tail | - | 14.7% | - | **none** | - | C18 verify 40.07 ms minus named classes |
| 13 | 27b-df2-mi210 | attn_k/v 1024x5120 (q8sk) | 17 | no published measurement | cuda-gemv | - | 1.4% | - | AK-BW-27B-ATTN-KV-CONCAT | - | C18 trace |
| 14 | 27b-df2-mi210 | lm_head 248320x5120 | 65 | no published measurement | cuda-gemv | - | 2.8% | - | **none** | - | C18 trace (AT_FLOOR) |
| 15 | 27b-df2-mi210 | draft q8ip_permute | 35 | no published measurement | cuda-fused-tail | - | 0.9% | - | AK-BW-27B-DRAFT-Q8IP-PERMUTE | - | C18 trace |
| 16 | a3b-mtp-cpu | router (CPU) | - | 88 | cpu-avx512-gemv | - | - | - | AK-CPU-C22-LEVERS (router BF16 shadow) | - | not in census: needs a row |
| 17 | a3b-mtp-mi210 (not served) | FA / gv (10 layers, f16 KV) | 11 | 88 | cuda-flashdecode | 77 | 4.1% | 3.2 | AK-RF-A3B-GV-ATTN; seed 25-ak-kernel-triage-20261124 | yes | C14 share; GB/s borrowed from 27B gv_fattn |
| 18 | a3b-mtp-mi210 (not served) | MUL_MAT_ID experts n=3 | 48 | 58 | cuda-moe | 10 | 11.6% | 1.2 | ak-mmid-mf-gpu-20261122 (4297a2caa); MMID-HELPER-N10 | yes | ak-mmid-split16-gpu-20261121-r4 |
| 19 | 27b-df2-mi210 (not served) | drafter BF16 hipBLAS (not served; training deferred) | 9 | no published measurement | cuda-gemv | - | 0.0% | - | DF2-11-BF16-FIX (done); DF2-FT-1 deferred | - | DF2-11-BF16-TRACE-PROF |
| 20 | a3b-mtp-mi210 (not served) | dense MMVQ (attn, GDN proj, shexp, lm_head) | 14 | no published measurement | cuda-gemv | - | 26.8% | - | AK-BW-CENSUS-MI210-ROWS (C18 A3B trace, attribution) | yes | C14 h-18 profile; attribution unresolved |
| 21 | a3b-mtp-mi210 (not served) | router mul_mat_f F32 [2048,256] | 1 | no published measurement | cuda-gemv | - | 13.5% | - | AK-RF-A3B-ROUTER-FUSE; seed 25-ak-kernel-triage-20261124 | yes | C14 (pre MMVF cap knob 79650eeab) |
| 22 | a3b-mtp-mi210 (not served) | quantize_q8_1 | 35 | no published measurement | cuda-fused-tail | - | 9.1% | - | **none** | yes | C14 |
| 23 | a3b-mtp-mi210 (not served) | k_bin_bcast / scale | 35 | no published measurement | cuda-fused-tail | - | 7.1% | - | **none** | yes | C14 |
| 24 | a3b-mtp-mi210 (not served) | router chain softmax/argsort/get_rows | 35 | no published measurement | cuda-fused-tail | - | 5.6% | - | **none** | yes | C14 |
| 25 | 27b-df2-mi210 (not served) | q4_0 KV attention (gv_fattn, q4_0 KV) | - | 71 | cuda-flashdecode-q4kv | - | - | - | ak-gvfattn-q4kv-gpu-20261124 | - | not yet measured; row ak-gvfattn-q4kv-gpu-20261124 supplies ours; compare at batch 32-128 |

Top unworked gaps (served, no box or row): a3b-mtp-cpu gdn_proj (2.2); a3b-mtp-cpu MUL_MAT_ID exps_down (1.0); a3b-mtp-cpu fullattn_proj (0.5); a3b-mtp-cpu lm_head (0.3)

References:

- `cpu-avx512-gemv` 88% [measured] (% of measured sustained bandwidth (likwid load, 1 socket)): DERIVED from measured, llama.cpp discussion #11733: Llama-3.1-70B F16 tg128 x 141.1 GB weights over likwid-load bandwidth, 1 socket: 9374F 176/185.3=95%, 9175F 332/378.3=88%, 9654 309/359.9=86%. Caveats: F16 not Q8; likwid not STREAM; warm-up workaround applied. Quantized MoE: Mixtral-8x22B Q8_0 on 9175F ~74% (active bytes estimated).
- `cuda-flashdecode` 88% [measured] (% of HBM peak (H200 measured; upper bracket H100/B200)): MEASURED, intake-2870 (arXiv 2611.30027): FA4 FP8 decode attention 85-89% of peak at batch>=8 on H200; plain device copy of the same bytes 87-89% on H200 (copy ceiling); ref = 88% midpoint of FA4 FP8 and the copy ceiling. Upper bracket: FlashInfer BF16 decode >90% on H100/B200 (FOSCAR, arXiv 2611.09722, intake-2879). Operator-approved figures.
- `cuda-flashdecode-q4kv` 71% [measured] (% of HBM peak (H200 measured, batched)): MEASURED, intake-2870 (arXiv 2611.30027): best 4-bit KV attention kernel 67-75% of peak at batch 32-128 on H200; ref = 71% midpoint of 67-75%. Deployed vLLM NVFP4 only 10-20% on H200. Operator-approved figures. Benchmarks row ak-gvfattn-q4kv-gpu-20261124.
- `cuda-fused-tail` no published measurement (brackets, end-to-end: megakernel_e2e_h100 78%, rmsnorm_large_h100 83%, vllm_sglang_e2e_h100 50%) [no-published-measurement] (% of HBM peak / whole-step proxy): No per-kernel figure at decode shapes. Large-shape H100 (AutoKernel arXiv:2603.21331 Sec 7.1/Table 4): rmsnorm 83% at 8192x8192, ~51% at 4096^2; softmax ~50%; rotary ~17-18%. Whole-step launch-bound proxy: intake-448 (HazyResearch Megakernels), vLLM/SGLang ~50% of H100 bandwidth, fused megakernel 78%. Ours remains a fixed 35 proxy.
- `cuda-gemv` no published measurement (brackets, end-to-end: exl2_e2e_l4 75.4%, llamacpp_e2e_rtx5090 80%, marlin_awq_e2e_l4 28.9%, pytorch_bf16_e2e_h100 26.9%) [no-published-measurement] (% of HBM peak): No per-kernel %-of-peak for quantized decode GEMV on H100/A100 found. Marlin (arXiv:2408.11743; github IST-DASLab/marlin README) gives only speedup vs FP16 (3.87x ideal to bs 16-32, A10). Brackets, all end-to-end: llama.cpp CUDA ~80% SOL, RTX 5090, gpt-oss-20b MXFP4 (llama.cpp discussion #17621); ExLlamaV2 4.25bpw 75.4% / AutoAWQ-Marlin 28.9% of int4 floor, L4 (arXiv:2605.30571 Table 7); PyTorch bf16 26.9%, H100 (same paper, Table 8).
- `cuda-moe` 58% [measured] (% of HBM peak (H200 measured, decode)): MEASURED, arXiv:2609.04244 (MonoMoE) Sec 4.3, Qwen3.5-35B-A3B-FP8 on H200: MonoMoE 21.20/37.51/49.06/57.99% of peak at B=1/2/4/8 (vLLM Triton baseline 10.62/19.36/30.78/45.07%); Table 1 baseline fused_moe BW 20.0/46.1/62.8/60.1% at BS 1/4/8/16. ref = best published kernel at B=8. Corroboration: Cursor warp-decode, B200 B=32, 58% of measured 6.8 TB/s copy peak.
- `cuda-scan` no published measurement [no-published-measurement] (% of HBM peak): No tuned GDN/Mamba decode kernel reports %-of-peak (fla, Mamba2 SSD papers report speedups). Only measured datum: NVLabs PyTorch reference GDN decode, 1 layer hv=32 d=128 FP32 state, H100 285 us/token for 4,194,304 B, i.e. 14.7 GB/s = 0.44% (arXiv:2603.05931 Tables II, IV). Untuned, not a parity ref.

Batch dependence of reference %-of-peak: Reference %-of-peak is batch-dependent: compare our nb=1 / nb=8 attention cells against batch-appropriate references, not the batched ceilings above. Source: intake-2870 (arXiv 2611.30027), H200, operator-approved.

| Kernel | % of peak | Batch |
|---|---|---|
| FA4 FP8 decode attention | 85-89 | >=8 |
| best 4-bit KV kernel | 18-38 | 1 |
| best 4-bit KV kernel | 67-75 | 32-128 |
| plain device copy (same bytes) | 87-89 | any (ceiling) |
| deployed vLLM NVFP4 | 10-20 | n/a |

### Bandwidth surfaces (ranked by saving ms/step)

Target 88 % of ceiling. Ceilings: GPU MI210 1638 GB/s, CPU quarter-24t 129 GB/s, CPU full host 520 GB/s. saving = step_ms x share x max(0, 1 - ours/target). Owner **none** = no box/row/seed works it: propose there first. STALE = a KEEP touched a parity-only surface; its ours % predates that KEEP, re-measure before ranking on it.

| # | Op · path | Family | Share | Ours % | Saving ms/step | Owner | Status | Step source |
|---|---|---|---|---|---|---|---|---|
| 1 | verify dense Q8 GEMV/GEMM (q8mf6, V5I) · 27b-df2-mi210 | dense-q8-gemv | 55.2% | 65.4 | 6.48 | V5I base; C21 V2 RRS fold | covered | fixed: 27B C18 verify round |
| 2 | launch-bound tail (eltwise/norm/copy/rope/conv) · 27b-df2-mi210 | launch-bound-tail | 14.7% | 4.2 | 6.38 | **none** | open | fixed: 27B C18 verify round |
| 3 | gv_fattn + merge (verify FA) · 27b-df2-mi210 | flash-attn-verify | 7.1% | 11.2 | 2.84 | ak-gvfattn-lds/splits/served rows; G3 | covered | fixed: 27B C18 verify round |
| 4 | actquant (q8mf_pre_i8 + q8sk_quantize) · 27b-df2-mi210 | act-quantize | 4.6% | 2.4 | 2.05 | AK-BW-27B-ACTQUANT-FUSE | covered | fixed: 27B C18 verify round |
| 5 | GDN recurrence (fused tree GDN) · 27b-df2-mi210 | gdn-recurrence | 4.6% | 12.2 | 1.83 | speculative-decoding.md batched tree GDN lane | covered | fixed: 27B C18 verify round |
| 6 | gdn_proj · flash-next-cpu | dense-iq4xs-gemv | 27.4% | 79.5 | 1.71 | **none** | open | derived (unverified): sum(us x calls)/sum(share_of_round), census n1 rows; no served tok/s row |
| 7 | other_weight · flash-next-cpu | dense-iq4xs-gemv | 10.4% | 66.9 | 1.61 | **none** | open | derived (unverified): sum(us x calls)/sum(share_of_round), census n1 rows; no served tok/s row |
| 8 | MUL_MAT_ID exps_gate_up · a3b-mtp-cpu | mmid-moe | 18.7% | 72.9 | 1.30 | AK-CPU-A3B-MMID (NO_LEVER) | covered | derived (unverified): sum(us x calls)/sum(share_of_round), census n1 rows; no served tok/s row |
| 9 | gdn_proj · a3b-mtp-cpu | dense-q8-gemv | 25.7% | 79.5 | 1.00 | **none** | open | derived (unverified): sum(us x calls)/sum(share_of_round), census n1 rows; no served tok/s row |
| 10 | shared expert N>=2 · a3b-mtp-cpu | dense-q8-gemv | 3.8% | 53.1 | 0.61 | AK-CPU-A3B-SHEXP-VERIFY-GAP | covered | derived (unverified): sum(us x calls)/sum(share_of_round), census n1 rows; no served tok/s row |
| 11 | exps_down · flash-next-cpu | mmid-moe | 6.2% | 75.9 | 0.55 | **none** | open | derived (unverified): sum(us x calls)/sum(share_of_round), census n1 rows; no served tok/s row |
| 12 | attn_k/v 1024x5120 (q8sk) · 27b-df2-mi210 | dense-q8-gemv | 1.4% | 16.8 | 0.53 | AK-BW-27B-ATTN-KV-CONCAT | covered | fixed: 27B C18 verify round |
| 13 | fullattn_proj · flash-next-cpu | dense-iq4xs-gemv | 7.8% | 79.1 | 0.51 | **none** | open | derived (unverified): sum(us x calls)/sum(share_of_round), census n1 rows; no served tok/s row |
| 14 | MUL_MAT_ID exps_down · a3b-mtp-cpu | mmid-moe | 8.9% | 76.5 | 0.47 | **none** | open | derived (unverified): sum(us x calls)/sum(share_of_round), census n1 rows; no served tok/s row |
| 15 | shared_expert · flash-next-cpu | dense-iq4xs-gemv | 3.5% | 70.2 | 0.45 | **none** | open | derived (unverified): sum(us x calls)/sum(share_of_round), census n1 rows; no served tok/s row |
| 16 | moe_router · flash-next-cpu | moe-router | 3.4% | 70.9 | 0.43 | **none** | open | derived (unverified): sum(us x calls)/sum(share_of_round), census n1 rows; no served tok/s row |
| 17 | lm_head · flash-next-cpu | lm-head-gemv | 6.4% | 79.8 | 0.39 | **none** | open | derived (unverified): sum(us x calls)/sum(share_of_round), census n1 rows; no served tok/s row |
| 18 | lm_head 248320x5120 · 27b-df2-mi210 | lm-head-gemv | 2.8% | 65.3 | 0.33 | **none** | open | fixed: 27B C18 verify round |
| 19 | fullattn_proj · a3b-mtp-cpu | dense-q8-gemv | 7.1% | 80.9 | 0.23 | **none** | open | derived (unverified): sum(us x calls)/sum(share_of_round), census n1 rows; no served tok/s row |
| 20 | indexer · flash-next-cpu | dense-iq4xs-gemv | 0.6% | 59.7 | 0.13 | **none** | open | derived (unverified): sum(us x calls)/sum(share_of_round), census n1 rows; no served tok/s row |
| 21 | lm_head · a3b-mtp-cpu | lm-head-gemv | 12.0% | 85.8 | 0.12 | **none** | open | derived (unverified): sum(us x calls)/sum(share_of_round), census n1 rows; no served tok/s row |
| 22 | draft q8ip_permute · 27b-df2-mi210 | act-quantize | 0.9% | - | - | AK-BW-27B-DRAFT-Q8IP-PERMUTE | needs_measurement | fixed: 27B C18 verify round |
| 23 | router (CPU) · a3b-mtp-cpu | moe-router | - | - | - | AK-CPU-C22-LEVERS (router BF16 shadow) | needs_measurement | derived (unverified): sum(us x calls)/sum(share_of_round), census n1 rows; no served tok/s row |
| 24 | indexer_weight · flash-next-cpu | dense-iq4xs-gemv | - | 62.0 | - | **none** | open | derived (unverified): sum(us x calls)/sum(share_of_round), census n1 rows; no served tok/s row |
| 25 | q4_0 KV attention (gv_fattn, q4_0 KV) · 27b-df2-mi210 | flash-attn-verify | - | - | - | ak-gvfattn-q4kv-gpu-20261124 | needs_measurement (not served) | fixed: 27B C18 verify round |
| 26 | k_bin_bcast / scale · a3b-mtp-mi210 | launch-bound-tail | 7.1% | - | - | **none** | needs_measurement (not served) | fixed: A3B C14 busy step |
| 27 | quantize_q8_1 · a3b-mtp-mi210 | act-quantize | 9.1% | - | - | **none** | needs_measurement (not served) | fixed: A3B C14 busy step |
| 28 | router chain softmax/argsort/get_rows · a3b-mtp-mi210 | moe-router | 5.6% | - | - | **none** | needs_measurement (not served) | fixed: A3B C14 busy step |

Family rank (score = sum of weight x saving ms/step over every path; `-` = unpriced, never guessed; knob = serving-knob arm, hypothesis = hand-written idea priced from census rows on every device it touches):

| # | Family | Kind | Score ms/step | Paths | Unpriced |
|---|---|---|---|---|---|
| 1 | dense-q8-gemv | family | 8.85 | 27b-df2-mi210, a3b-mtp-cpu, a3b-mtp-mi210 | 0 |
| 2 | launch-bound-tail | family | 6.38 | 27b-df2-mi210, a3b-mtp-mi210 | 1 |
| 3 | dense-iq4xs-gemv | family | 4.42 | flash-next-cpu | 1 |
| 4 | hypothesis:27-ak-27b-tail-fusion-groups-20261124 | hypothesis | 3.22 | 27b-df2-mi210 | 0 |
| 5 | flash-attn-verify | family | 2.84 | 27b-df2-mi210, a3b-mtp-mi210 | 1 |
| 6 | mmid-moe | family | 2.31 | a3b-mtp-cpu, a3b-mtp-mi210, flash-next-cpu | 0 |
| 7 | act-quantize | family | 2.05 | 27b-df2-mi210, a3b-mtp-mi210 | 2 |
| 8 | gdn-recurrence | family | 1.83 | 27b-df2-mi210 | 0 |
| 9 | lm-head-gemv | family | 0.83 | 27b-df2-mi210, a3b-mtp-cpu, flash-next-cpu | 0 |
| 10 | moe-router | family | 0.43 | a3b-mtp-cpu, a3b-mtp-mi210, flash-next-cpu | 2 |
| 11 | drafter-gemm | family | 0.00 | 27b-df2-mi210 | 0 |

<!-- BW-CENSUS:END -->
