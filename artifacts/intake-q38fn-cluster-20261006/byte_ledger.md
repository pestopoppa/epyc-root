# GB10 byte ledger for Q38FN (Qwen3.8-Flash-Next) decode, from jschmied/qwen38-flash-next-gb10 @ 9b3fd4c

Everything MiB unless stated. Source figures: notes/speed-of-light.md L19-27 (sizes), L76-82 (measured expert unions), L84-95 (K=3 floor parts), kcost2 table L2190-2194 (measured cycles). Cells marked `interp` or any floor/ratio column are MY derivation from those figures (floor model re-implemented in ledger.py and reproduces the repo's K=3 45.2 ms and K=5 52.9-54.4 ms). Bandwidth: 220 GB/s unless stated.

## 1. Per-cycle ledger by K (R = K+1 verify rows, c=1, one request)

Fixed terms: dense 4,463 = FP8 dense 2,551 + BF16 leftovers 1,912 (HC mixers 1,209, shared experts 450, router 120). lm_head 606 (one FP8 [248320x2560] pass per verify, independent of R). GDN state 210 (floor-model r+w; fp32 RecoverSSM actual 324 = 1.54 ms; bf16 state in prod halves it). QSA 50. Drafter(K) = K x (173 BF16 MTP dense + 45 NVFP4 32k draft-head slice + 10 experts x 2.637) + one 4-row absorb (35.7-10 extra experts); at K=3 = 801 MiB (repo 739-828). Expert MiB = E(R) x 48 layers x 2.637.

| K | R=K+1 | E meas/interp | E indep | dense MiB | expert MiB (meas) | expert MiB (indep) | lm_head MiB | drafter MiB | GDN MiB | QSA MiB | total MiB | floor ms @220 | floor ms @220 if indep E | floor ms @273 | floor ms @236 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2 | 16.3 (interp) | 19.8 | 4463 | 2064 | 2507 | 606 | 312 | 210 | 50 | 7706 | 36.7 | 38.8 | 29.6 | 34.2 |
| 2 | 3 | 21.7 (interp) | 29.4 | 4463 | 2748 | 3724 | 606 | 557 | 210 | 50 | 8634 | 41.2 | 45.8 | 33.2 | 38.4 |
| 3 | 4 | 26.6 (meas) | 38.8 | 4463 | 3367 | 4917 | 606 | 801 | 210 | 50 | 9497 | 45.3 | 52.7 | 36.5 | 42.2 |
| 4 | 5 | 32.0 (interp) | 48.1 | 4463 | 4052 | 6086 | 606 | 1045 | 210 | 50 | 10427 | 49.7 | 59.4 | 40.0 | 46.3 |
| 5 | 6 | 37.2 (interp) | 57.1 | 4463 | 4715 | 7233 | 606 | 1290 | 210 | 50 | 11333 | 54.0 | 66.0 | 43.5 | 50.4 |
| 6 | 7 | 42.3 (interp) | 66.0 | 4463 | 5359 | 8358 | 606 | 1534 | 210 | 50 | 12222 | 58.3 | 72.5 | 46.9 | 54.3 |
| 7 | 8 | 47.3 (meas) | 74.7 | 4463 | 5987 | 9460 | 606 | 1778 | 210 | 50 | 13094 | 62.4 | 79.0 | 50.3 | 58.2 |

Measured-expert-union points: R=4 (26.6) and R=8 (47.3) only (plus R=16 82.5, R=1 10.0). R=2,3,5,6,7 are piecewise log-log interpolation. Independent column = 512(1-(1-10/512)^R).

## 2. Measured step time vs floor, per K (kcost2, prod config incl. RecoverSSM, F4, HC fusion; 2 starts averaged)

| K | floor ms/cycle @220 | measured code ms/cycle | ratio code | measured prose | ratio prose | code tok/cycle (derived) | code measured tok/s | code floor tok/s | prose tok/cycle | prose tok/s meas | prose floor tok/s |
| 1 | 36.7 | 43.8 | 1.19 |45.2 | 1.23 | n/a | n/a | n/a | n/a | n/a | n/a |
| 2 | 41.2 | 49.65 | 1.21 |51.4 | 1.25 | 2.70 | 54.3 | 65.6 | 2.23 | 43.5 | 54.3 |
| 3 | 45.3 | 55.05 | 1.22 |56.9 | 1.26 | 3.40 | 61.7 | 75.1 | 2.57 | 45.2 | 56.9 |
| 4 | 49.7 | 59.5 | 1.20 |61.6 | 1.24 | 3.91 | 65.8 | 78.8 | 2.67 | 43.3 | 53.7 |
| 5 | 54.0 | 64.75 | 1.20 |67.6 | 1.25 | 4.38 | 67.6 | 81.0 | 2.85 | 42.2 | 52.8 |
| 6 | 58.3 | 69.35 | 1.19 |72.55 | 1.25 | 4.72 | 68.0 | 81.0 | 2.65 | 36.5 | 45.5 |
| 7 | 62.4 | 74.45 | 1.19 |77.05 | 1.23 | 5.00 | 67.1 | 80.1 | 2.93 | 38.0 | 46.9 |

tok/cycle is cycle_ms / ms_per_tok from the same kcost2 table (derived); 'floor tok/s' = tok/cycle / floor_ms. K=1 cycle is from kdiag (no-async static K1: 43.8 code / 45.2 prose). Prose K=6/7 tok/cycle looks noisy (different replies per K, ms/tok 27.4/26.3).
Reading: ratio is flat at 1.19-1.22 (code) and 1.23-1.26 (prose); the unexplained gap is ~8-11 ms per cycle, nearly independent of K. Marginal floor cost per extra K is 4.1-4.4 ms vs measured +4.8 ms.
At 220 GB/s a floor built with INDEPENDENT routing (col 'floor if indep E') is 66.0 ms at K=5 and 79.0 ms at K=7, i.e. ABOVE the measured 64.8 / 74.5 ms cycles: independence is excluded by their own timing at their own 220 calibration (at 236 GB/s K=5 indep floor = 61.5, no longer excluded).

## 3. K=3 anatomy (warm, prod): where 54.9 ms goes vs 45.2 floor

| part | floor ms | measured ms | note |
|---|---|---|---|
| MoE grouped GEMM (aux streams, target E=26.6 + drafter) | ~16.9 | 18.2 (20.6-20.7 in node trace incl. glue) | 1.08x; only 4.6 of 20.7 ms overlaps main stream |
| FP8 blockwise GEMM (dense + lm_head) | 15.1 | 16.3 (14.9 after RecoverSSM) | 1.08x |
| BF16 GEMM/GEMV (HC mixers, shared expert, router, drafter dense) | ~11.6 | 16.7 (16.2 after) | 1.44x; mid-size reads carry ~fixed overhead; shared/router contend with MoE on DRAM (201 GB/s combined) |
| GDN state (update/verify + commit) | 1.0-1.03 | 1.5 -> 0.85 verify + 1.05 commit | commit at 224 GB/s (floor); verify 145-148 GB/s latency-bound |
| other (routing, finalize, elementwise, norms, QSA, NVFP4 head, quant) | - | ~5.3 | small kernels critical-path 3.5 ms (4m); QSA 0.58 + 0.39 gaps |
| GPU idle (union of streams) | 0 | 2.4-2.55 (4%) ; 1.8 in later trace | ~0.6 launch gaps in eager GDN, 0.2 QSA |
| total | 45.2 | 55.0 profiled / 54.2-54.4 cycle / 54.9 warm unprofiled | ratio 1.20-1.21 (1.31 on the 09-24 stack at 59.2) |
| cold-start paging (not steady state) | - | +5-6 | ~0.2 ms/major PLE fault x 27-32; fixed by WILLNEED readahead |

## 4. Achieved GB/s by kernel class (author-measured, GB10, L2 flushed unless noted)

| kernel | GB/s | source line | note |
|---|---|---|---|
| FP8 in_proj_qkvz / qkv_proj | ~205-212 (1.04-1.06x of 220-floor time) | L102-103 | 190.7 us floor |
| FP8 out_proj/o_proj (15.7 MB) | ~199 standalone (78.9 us, 1.10x) / ~164 in-model (96.1 us, 1.34x) | L104, L275 | mid-size overhead |
| FP8 lm_head 636 MB | ~234 | L122 | 0.94-0.95x of 220 floor |
| NVFP4 MoE block (L3/L4, 26.6 experts) | 0.98-1.11x floor | L121-122 | |
| HC combine_norm / gate_mix / finalizeMoeRouting | 234 / 219 / 224 | L1686-1688 | prefill chunk |
| doActivation | 270 | L1689 | L2-assisted |
| RecoverSSM commit | 224 | L716-717 | the DRAM floor |
| GDN verify kernel | 145-148 | L725-726, L734 | latency-bound |
| HC mixer down/up in-model | 40.5 / 33.9 us vs 30.2 / 29.8 floor | L189-190 | |
| BF16 in_proj_ba 96x2560 | ~22 (7.8x floor) | L194 | launch-bound |
| TF EXL3 expert kernel, decode windows | 192-214 (1-64 rows) | L3403 | 87-95% of 224 |
| TF dense EXL3 linear / k,v 0.8 MB | 160-205 / 45-48 | L3253, L3410 | |
| TF fp16 HC mixes | 203-239, but 96x2560 at 22 | L3409-3410 | 1.25 GB per forward |

## 5. Attainable-bandwidth calibration ('220 GB/s' / det-231)

* det-201 (notes/determinism-investigation.md ~L4200-4243): bwprobe = one bf16 GEMV (2560x10240, M=1 and M=4), idle box: 212.8/214.2/215.0 (M=1), 206.2-206.8 (M=4); 78% of 273.
* det-231 (L5882-5990): 62 s gpuflip probe, no model, decode-shaped bf16 GEMV: 218.6-219.7 GB/s, max/min 1.01x, 0 of 31 s below midpoint. This is the '220'. It was run to rule out a reported GB10 slow state (66-80 GB/s) and CLOSED as not present on their box (kernel 6.17.0-1031 / driver 580.173.02; box later moved to 7.0.0-1019 / 580.178.04, not re-probed).
* Context points: 64 MB device copy 239-242 GB/s (reporter's boxes, both fast and slow states); 218.5 GB/s read+write copy (TF midm_bench, authors' box); independent streaming roof 235.8-237.6 GB/s (86%, cudafast survey); best in-model kernels 224-234.
* So 220 = 80.6% of 273; plausible stream roof ~236-242 (86-89%). Floors at 236 are 6.8% lower (K=3 42.2 ms, ratio 1.30 not 1.21).

## 6. Expert-routing correlation (what replaces an independence assumption)

| window rows | measured distinct experts/layer | independent-uniform | ratio |
|---|---|---|---|
| target 4 (c=1 K=3) | 26.6 (median 27, n=69,648) | 38.8 | 0.69 |
| target 8 (c=2) | 47.3 | 74.7 | 0.63 |
| target 16 (c=4) | 82.5 | 138.6 | 0.60 |
| drafter 1 row | 10.0 | 10.0 | 1.00 |
| drafter 4 rows (absorb of verified tokens) | 35.7 | 38.8 | 0.92 |

* Extra verify row ~ +4.9 experts x 48 layers = ~3.3 ms (two-thirds of a draft position's marginal cost). K=5 6-row 37.2 is interpolated, never captured.
* Layer-summed coverage probe (prompt tokens, MTP off, 74.9 M pairs): per-expert max/min 3.7x, p90/p10 1.8x, 0 of 512 experts under 10k. A skew-only independent model fitted to R=4 would need lognormal sigma ~2.16 (max/min ~2e6) and then predicts 43.7 at R=8 and ~69 at R=16 -> skew cannot be the whole story; within-window token-to-token correlation is needed (MY analysis).
* R=16 decomposition (MY analysis): 4 independent requests of 26.6 give 98.4 under uniform popularity (0.71 of independent) and the measured 82.5 is a further 0.84x (cross-request popularity overlap).
* Caveats: traffic mix = c=1 essays, c=4, agent loop (population average); only one layer-summed skew probe; raw capture not in repo. No per-prompt-type (code vs prose) split of E.

## 7. Other ledger rows

* Plain decode (no spec): dense 4,463 + lm_head 606 + 10 experts x 48 x 2.637 (1,266) + GDN 210 + QSA 50 = 6,595 MiB = 6.44 GiB = 6.93 GB -> 31.4 ms @220 (31.8 tok/s), 25.3 ms @273 (39.5 tok/s); repo says '6.6 GiB' (label slip; its 31.5/25.4 ms match 6.93 GB). Last measured no-spec 40.2 ms/tok (older stack, 1.28x).
* c=4 K=3 (MY arithmetic): E(16)=82.5 -> experts 10,443 MiB, dense+lm_head shared 5,069, drafter (dense/head shared x3 steps + experts ~35 x3) ~931, state 4x210, QSA 4x50 => ~17,482 MiB, ~83.3 ms/cycle floor, 4x2.53 tokens => ~121 tok/s floor vs measured 99.6 ms -> ~101 tok/s (1.20x).
* K=5 single-Spark ceilings at 220/236/273 GB/s (floor 54.0 / 50.4 / 43.5 ms): 4.37 accepted -> 81 / 87 / 100 tok/s (measured 65.7-68.4); 5.1 accepted -> 94 / 101 / 117; 5.5 -> 102 / 109 / 126. Dual-Spark TP2: repo has no measurement; only quoted MiaAI figures (64 tok/s single stream, k-curve 25.9/43.4/52.6/59.1/65.8).
* Drafter dense BF16 ~125 MB/draft step (qkv 81 MB + hc-collapse 52 MB): FP8/NVFP4 versions were measured and rejected (acceptance -0.06..-0.09 outweighs -0.9..-1.3 ms).
* Launch/sync: one host sync/cycle <= ~0.8 ms; async scheduling null (nothing to hide at ~64 ms cycles); TensorFold single stream 97.6% GPU-busy with graphs (0.29 ms idle/token), 88.3% eager.
* PLE: 16 rows x 160 B = 2,560 B/token; bandwidth-negligible, latency/paging-bound (cold +5-6 ms/step, warm 0).
