# Champion gain chain, production v10 to C14 (champion) and the C15 candidate

Date: 2026-11-18. Read-only analysis: no runs, no process management; every figure below is copied from a
`RESULT.json` under `/mnt/raid0/llm/tmp/<row>/out/` or from the cited handoff/manifest text (row id given in
each cell). Nothing is recomputed except the products, and each product is labelled.

Operator question: "Doesn't C15 have all the improvements of all the advanced champions? If so don't we know
the improvement from champion to champion and, thus, transitively from v10 to current champion?"

## Short answer

1. Yes, each champion contains all earlier champions' code (each Cn is Cn-1 plus the folds; v10 `ffc1bac82` is an
   ancestor of all of them). But the gain is NOT known by transitivity, because each fold gate measures
   candidate-vs-predecessor on a DIFFERENT set of cells, and many gates were only no-regression gates
   (`>= 0.995` / floor checks) on the cells where the fold did not aim. A chain is unbroken only where the same
   cell was measured whole-candidate at every step.
2. There is no whole-candidate v10-vs-C(n) timing for the GPU models. The only direct v10-vs-champion timing is
   CPU Qwen3.8-Flash-Next (Q38FN) + MTP d4, v10 vs C12 (`c12-cpu-p3-quiet-20261117`).
3. Where the chain is unbroken it is: 27B Q8_0 and A3B Q8_0 GPU llama-bench cells C7r -> C10, and
   Q38FN CPU/GPU MTP d4 serving cells over the C10 -> C12 / C11 -> C14 steps (see sections 3-4).
4. C15 (`b10f91e32` = C14 + FAROWS) has NO valid whole-candidate speed ratio yet (GPU r1 failed its KLD gate
   before decode ran; GPU r2 is running; CPU rows are noise-dominated).

## 1. Chain of champions and what each step folded

Steps before C5 are listed for completeness; they have no whole-candidate speed ratios (sign claims only, section 5).

| Step | Champion sha | Folded (manifest row) | Fold gate rows |
|---|---|---|---|
| v10 base | `ffc1bac82` | production-consolidated-v10 | n/a |
| v10 -> C (dd3d9721c) | `dd3d9721c` | 42 commits: fast repack/pread loader V11-001/002, KVU-19 FA masked-block skip V11-011/013, MMVQ q8_1 arena V11-014, DS41 + AK keeps V11-026.. | V6R-4d GPU no-regression, sign gates |
| -> C2 / C3 / C4 / C5 | `49550eda5` / `dcc853b55` / `cdb4d8c77` / `c72ec82f5` | Nemotron/bolt + CT-12.3b; YaRN K-shift fix V11-100; GPU-LEAK-1c V11-104; fused qwen4exp default-OFF V11-106/107 | c4 gate-e, c5-gate-b (sign), identity |
| C5 -> C6 | `65da39eb1` | llguidance V11-122; iqk Q8_0 CPU prefill route V11-123 (default ON) | `c6-iqkq8pf-fold-gate-20261105`, `c6-iqkq8pf-fp16s-gate-20261106` |
| C6 -> C7r | `62cb6a6af` | MI210 asm/HIP bundle V11-124 (H10, H1b, H12, H13b/c, H11, H15, H5-PORT, topk-moe fix) | `c7r-gate-20261106` |
| C7r -> C8 | `1bda248e3` | GDN chunked prefill V11-125, LCATTN multiseq verify V11-126, n_q=1 GQA verify (MIN_NQ=1 for q8_0 KV) V11-127, token_embd on GPU V11-128, H18 CK hd256 prefill V11-129, H20 prefill GEMM V11-130, rollback guards/recovery/sequential split V11-131..133 | `c8-rbseq-gate-20261108` (whole), intermediate `c8-fold0/2/3/5-gate` |
| C8 -> C9 | `d210f85c2` | serial-verify logits fix V11-134, FA prefetch overlap V11-135 | `c9-fold-gate-20261109`, `c9-fold-cpu-gate-20261109` |
| C9 -> C10 | `7f1bd044b` | 27B `down` GEMM tile override V11-136, IQ3_S zmm dot V11-137, fused zero-row guard V11-138, tbo sentinel V11-139 | `c10-fold-gate-20261109`, `c10-fold-cpu-gate-20261109` |
| C10 -> C11 | `8b9bf3031` | GGML_CPY_BALANCE default ON V11-141 | `c11-fold-nr-20261114` (CPU), `c11-fold-gpu-20261114` (GPU, correctness only) |
| C11 -> C12 | `457d5fc52` | upstream b12421 bundle1 V11-142 | `up-bundle1-cpu-20261115-r2`, `up-bundle1-gpu-20261115-r5` |
| C12 -> C13 | `bda43aa17` | LB4.9 per-head sinks, default-off, compiled out of the shipping recipe V11-143 | no speed row (D0 equivalence, `v11-c13-build-preflight-20261117-r3`) |
| C13 -> C14 | `eee3da838` | INF48 FA bug fix (6 `ggml-cuda/fattn*` files + tests) V11-144 | `c14-fold-build-20261118`, `c14-fold-gpu-20261118-r3` |
| C14 -> C15 (candidate) | `b10f91e32` | FAROWS gather (`230fc0259` + default-ON `67bcc066c` + GPU-only guard `b10f91e32`); NOT in this build: q8_1 v2 `c8f7a85f1`, CPU split-KV `b67125fbd`, CH-33 `4265996a8` | `c15-fold-build-20261118`, `c15-fold-gpu-20261118`(-r2 running), `c15-fold-cpu-20261118`(-r2, -r4) |

## 2. Per-step measured ratios (whole-candidate unless marked)

Ratio = candidate / predecessor, higher is better (per-step decode cost ratios are inverted so >1 is faster).
"WC" = whole-candidate A/B of the two store builds; "no-reg" = measured but only gated as >= floor.

### 2a. GPU, 27B Q8_0 and A3B Q8_0 (llama-bench, MI210)

| Step (row) | 27B pp2048 | 27B pp8192 | 27B tg128 d0 | 27B tg@d32k | 27B tg@d131k | 27B pp2048@d32k | 27B pp2048@d131k | A3B pp2048 | A3B pp8192 | A3B tg128 | A3B tg@d32k | A3B tg@d131k | np4 DFlash2 @d32k (gate shape) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C6 -> C7r (`c7r-gate-20261106`) | 1.0195 | (pp32768 1.1947) | - | - | - | - | - | 1.0380 | - | 1.0601 | - | - | - |
| C7r -> C8 (`c8-rbseq-gate-20261108`, WC) | 1.1724 | 1.2183 | 1.0007 | 1.0915 | 1.2497 | 1.5567 | 2.4348 | 1.2407 | 1.2925 | 0.9976 | 1.0724 | n/m | 1.1969 |
| C8 -> C9 (`c9-fold-gate-20261109`, WC) | 1.0037 | 1.0019 | 1.0315 | 1.0448 | 1.1058 | 1.0003 | 0.9994 | 0.9997 | 0.9992 | 1.0125 | 1.0331 | 1.0730 | 1.0315 |
| C9 -> C10 (`c10-fold-gate-20261109`, WC) | 1.1593 | 1.1803 | 1.0097 | 1.0014 | 0.9969 | 1.1392 | 1.0906 | 0.9990 | 1.0005 | 0.9920 | 0.9983 | 0.9994 | 0.9972 |
| C10 -> C11 (`c11-fold-gpu-20261114`) | no speed row, test-backend-ops only (0 new fails) | | | | | | | | | | | | |
| C11 -> C12 (`up-bundle1-gpu-20261115-r5`) | no 27B/A3B speed row (Q38FN only, see 2c) | | | | | | | | | | | | |
| C12 -> C13 | no GPU row (LB4.9 is CPU iqk, default-off) | | | | | | | | | | | | |
| C13 -> C14 (`c14-fold-gpu-20261118-r3`) | no 27B speed row; 27B C14-vs-C13 KLD exactly 0 (`c14-kld-diag-gpu-20261118-r2`) | | | | | | | | | | | | |
| C14 -> C15 (`c15-fold-gpu-20261118`) | not run (KLD gate failed first); r2 running | | | | | | | | | | | | |

"n/m" = not measured at that step (C8 gate had no A3B d131k cell).

**Chained product, C7r -> C10 (unbroken, three whole-candidate steps):**

| Cell | C7r->C8 x C8->C9 x C9->C10 | Product |
|---|---|---|
| 27B pp2048 | 1.1724 x 1.0037 x 1.1593 | 1.364 |
| 27B pp8192 | 1.2183 x 1.0019 x 1.1803 | 1.441 |
| 27B tg128 d0 | 1.0007 x 1.0315 x 1.0097 | 1.042 (see noise caveat: d0 A/A floor 2.7%, round spread 10%) |
| 27B tg@d32768 | 1.0915 x 1.0448 x 1.0014 | 1.142 |
| 27B tg@d131072 | 1.2497 x 1.1058 x 0.9969 | 1.378 |
| 27B pp2048@d32768 | 1.5567 x 1.0003 x 1.1392 | 1.774 |
| 27B pp2048@d131072 | 2.4348 x 0.9994 x 1.0906 | 2.654 |
| A3B pp2048 | 1.2407 x 0.9997 x 0.999 | 1.239 |
| A3B pp8192 | 1.2925 x 0.9992 x 1.0005 | 1.292 |
| A3B tg128 | 0.9976 x 1.0125 x 0.992 | 1.002 |
| A3B tg@d32768 | 1.0724 x 1.0331 x 0.9983 | 1.106 |
| np4 DFlash2 @d32768 (gate shape, not serving) | 1.1969 x 1.0315 x 0.9972 | 1.231 |

Extending back one step to C6 where the cell was also in the C7r gate: 27B pp2048 1.0195 x 1.364 = 1.391;
A3B pp2048 1.038 x 1.239 = 1.286; A3B tg128 1.0601 x 1.002 = 1.062 (C6 -> C10).

**To C14 and C15 for these cells: the chain is BROKEN after C10.** C11, C12, C13, C14 each had only
correctness / no-regression GPU gates with no 27B/A3B speed cell. The C10 numbers are the last whole-candidate
measurement; "C14 = C10 x (unmeasured)". C15: unmeasured.

Not chainable (different cell families): 27B single-sequence DFlash2 decode was measured only at C6 -> C7r
(`c7r-gate-20261106`: 8k 1.3355, 32k 1.3881, 64k 1.4490); afterwards DFlash2 appears only as the np4 gate-shape
cell above and in the FAROWS A/B (section 6). 27B pp32768 (1.1947) was a C6 -> C7r cell only.
Q38FN GPU tg64 (llama-bench) C6 -> C7r = 1.1368 (same gate); never re-measured.

### 2b. CPU, Q38FN UD-IQ4_XS + MTP d4, t48, np4/262144/f16, llama-server (the serving-shape cells)

Cells: P1 = 54K prompt, P2 = code16k, P3 = code28k (mapping from manifest V11-141: code16k 1.319, code28k 1.257, 54K 1.132).

| Step (row) | Metric | P1 | P2 | P3 | Kind |
|---|---|---|---|---|---|
| **v10 -> C12** direct (`c12-cpu-p3-quiet-20261117`, quiet, 12 visits) | per-step decode cost | not measured quiet | **1.3384** (CI95 1.244-1.440) | **1.2798** (CI95 1.238-1.323) | WC, single direct A/B |
| v10 -> C12 (`c12-cpu-validate-20261116-r5`, contended, DROP) | per-step | 1.0801 | 1.1216 | 0.9763 | WC but noisy; P3 shown to be noise by the quiet row |
| C10 -> C11 (`c11-fold-nr-20261114`, 8 visits) | first-256 decode tok/s | 1.1318 | 1.3185 | 1.2571 | WC, geomean 1.2333 |
| C11 -> C12 (`up-bundle1-cpu-20261115-r2`, 8 visits) | first-256 decode tok/s | 1.0009 | 1.0360 | 1.0091 | WC, geomean 1.0152, KLD 0 |
| C12 -> C13 | n/a | 1 by construction | | | D0: shipped CPU code equivalent (LB4.9 compiled out), NOT a timing |
| C13 -> C14 (`c14-fold-build-20261118`) | n/a | 1 by construction | | | 212/212 CPU objects byte-identical to C13, NOT a timing |
| C14 -> C15 (`c15-fold-cpu-20261118`, r1) | per-step | 0.9223 | 0.9655 | 0.9944 | WC, geomean 0.9602, rule FAIL; CPU objects differ (`llama-graph`, `ggml.c`, kv-cache) |
| C14 -> C15 (`c15-fold-cpu-20261118-r2`) | - | invalid | invalid | invalid | all visits INVALID_CONTENDED |
| C14 -> C15 (`c15-fold-cpu-20261118-r4`, partial, 4 visits) | per-step | 1.3475 | 0.7920 | 1.0205 | per-visit step ms scatter 150-299 ms; not interpretable |

Chain cross-check (derived, mixed metrics, so read as a consistency check only): C10->C11 x C11->C12 gives
P1 1.1328, P2 1.3660, P3 1.2685 versus the direct v10 -> C12 quiet row 1.338 / 1.280 (P2 +2.1%, P3 -0.9%
apart). Implication: v10 -> C10 on this cell is about 0.98-1.01, i.e. essentially all CPU Q38FN MTP gain from v10
is the C11 GGML_CPY_BALANCE fold, plus about 1-4% from bundle1.

**v10 -> C14 CPU Q38FN MTP d4:** P2 about 1.338, P3 about 1.280 (direct v10->C12 measurement, carried to C14 by the
two byte/shipped-code equivalence checks above, not by timing). P1: no valid direct measurement; the derived chain
is 1.133. **v10 -> C15:** the C14 -> C15 CPU ratio is unresolved (r1 0.96 geomean FAIL, r2/r4 contended).

### 2c. GPU, Q38FN UD-IQ4_XS + MTP d4 serving (hybrid, `-ngl 99 --n-cpu-moe 48`), per-step decode cost

| Step (row) | P2 | P3 | geomean | Kind |
|---|---|---|---|---|
| C11 -> C12 (`up-bundle1-gpu-20261115-r5`, PASS) | 1.0639 | 0.9980 | 1.0304 | WC; tok/s ratios 0.8967 / 0.9470 (info) differ because MTP acceptance is nondeterministic; per-step is the gate |
| C12 -> C13 | none | | | no GPU timing row |
| C13 -> C14 (`c14-fold-gpu-20261118-r3`, FAIL P3 0.9734 < 0.98; operator accepted as noise) | 1.0523 | 0.9734 | 1.0121 | WC; visit noise +-15% |
| C14 -> C15 (`c15-fold-gpu-20261118`) | not run | | | KLD gate failed first: Q38FN PPL 3.5925 outside C14 A/A spread [3.5140, 3.5620]; 27B KLD -0.0, top-1 100%. r2 running |

Chained product C11 -> C14 (C12 -> C13 gap treated as no change, because LB4.9 is CPU-only and compiled out; no GPU row proves it):
P2 1.0639 x 1.0523 = 1.120, P3 0.9980 x 0.9734 = 0.972. Neither is distinguishable from 1.0 given the +-15% visit noise
and the failed P3 floor. v10 -> C10 and C10 -> C11 on this GPU cell: not measured (C11 GPU row is test-backend-ops only).
Q38FN GPU v10 -> C14: **unmeasured**.

### 2d. CPU llama-bench no-regression gates (C7r -> C10, shown for completeness)

| Cell | C7r->C8 (`c8-rbseq-cpu-gate-20261108`) | C8->C9 (`c9-fold-cpu-gate-20261109`) | C9->C10 (`c10-fold-cpu-gate-20261109`) | Product |
|---|---|---|---|---|
| Q38FN tg64 | 0.9906 | 1.0069 | 1.0143 | 1.012 |
| Q38FN pp512 | 1.0118 | 0.9992 | 0.9837 (r3 INCONCLUSIVE; operator accepted rounds 2-5) | 0.995 |
| A3B tg128 | 0.9983 | 1.0031 | 0.9900 | 0.991 |
| A3B pp512 | 1.0021 | 1.0808 | 1.0307 | 1.116, DO NOT READ: the C9 CPU library is byte-identical to C8's, so 1.0808 is pure noise |

These are no-regression gates, floor-checked, not speed claims.

### 2e. CPU A3B Q8_0 prefill route, C5 -> C6

iqk Q8_0 prefill (V11-123). llama-server np4 A3B Q8_0 `pf2048`: 1.7028 (`c6-iqkq8pf-fold-gate-20261105`, 3 pairs, candidate
`f3a6a4baa`) and 1.5138 median (`c6-iqkq8pf-fp16s-gate-20261106`, final `65da39eb1`, 5 pairs, per-pair spread 0.57-2.00,
"reported only"). Reference there is C5 + llguidance (`21232569a`), not C5 itself. Decode np1 1.0094 / 1.0012, np4 0.9817 / 1.0279
(band 0.97-1.03, PASS). Cost: +0.2-0.3% PPL (V11-123). Later CPU gates (2d) measure pp512, so the C5 -> C6 prefill gain
cannot be chained forward by timing.

## 3. Direct answer per model/device (headline)

| Model / device / metric | v10 -> C14 | Status |
|---|---|---|
| Q38FN CPU decode, MTP d4 t48 np4, code16k (P2) | about x1.338 (CI 1.244-1.440) | direct whole-candidate v10->C12 (`c12-cpu-p3-quiet-20261117`), carried to C14 by byte/shipped-code equivalence (`c14-fold-build-20261118`, D0). Whole-candidate, not a chain |
| Q38FN CPU decode, code28k (P3) | about x1.280 (CI 1.238-1.323) | same |
| Q38FN CPU decode, 54K (P1) | derived chain about x1.13 only | no valid direct measurement; r5 1.0801 was contended; chain uses mixed metrics |
| Q38FN GPU decode, MTP d4 | unmeasured v10->C11; C11->C14 P2 x1.12, P3 x0.97 | chained whole-candidate for C11->C14 only, within noise; v10->C11 gap |
| 27B Q8_0 GPU no-draft (llama-bench) | C7r->C10: pp2048 x1.36, pp8192 x1.44, tg d0 x1.04, tg@32k x1.14, tg@131k x1.38, pp2048@32k x1.77, pp2048@131k x2.65. v10->C6 and C10->C14: unmeasured | chained whole-candidate C7r->C10; gaps at both ends |
| 27B Q8_0 GPU DFlash2 | C6->C7r only: x1.34 / 1.39 / 1.45 at 8k/32k/64k; np4 gate shape C7r->C10 x1.23 | different cell families, not joinable; not serving-shape |
| A3B Q8_0 GPU | C7r->C10: pp2048 x1.24, pp8192 x1.29, tg d0 x1.00, tg@32k x1.11 | chained whole-candidate; gaps outside C7r..C10; d131k only from C9 |
| A3B CPU prefill (pf2048, Q8_0) | C5->C6 x1.51-1.70 (single step) | whole-candidate for that step only; not chainable |
| Prefill, 27B GPU | included above (pp cells) | see 27B row |

## 4. Gaps (steps with no timing on a cell, gated as no-regression only)

- v10 -> C (dd3d9721c) -> C2 -> C3 -> C4 -> C5: no whole-candidate timing on any cell. Sign claims only (section 5).
- C5 -> C6 -> C7r on GPU 27B/A3B: C6 gate measured CPU A3B/Q38FN only; C7r gate measured vs C6 (partial cell set).
- C10 -> C11 GPU: `c11-fold-gpu-20261114` is test-backend-ops (13695/13754 vs 13706/13762 passed lines, 0 new fails) with no timing.
- C11 -> C12 GPU: Q38FN only (2c); 27B/A3B not run.
- C12 -> C13: no timing on any device (CPU and GPU).
- C13 -> C14 CPU: identity by byte equality, not timing. C13 -> C14 GPU: Q38FN only; 27B has KLD 0 and no timing.
- C14 -> C15: no valid ratio on any cell.

## 5. Pre-C5 sign claims (not chainable; recorded because they are the only numbers)

| Step | Number | Row / source | Strength |
|---|---|---|---|
| v10 -> champion `90c12df42` GPU, MTP model | pp +0.39%, tg -0.46% (floor 2.00%) | V6R-4d.2 (`gpu-champion-ab` `w8083-20261001T121346Z`); V11-003 | no-regression gate on an earlier champion, not on C |
| dd3d9721c -> C `f0c96dc1f`, Q38FN CPU | +1.747% (50.11 -> 50.99 tok/s) | Block B (b), `champion-consolidation-20261020/blockB-20261021` | sign claim only, no calibrated floor |
| b0ba1d427 -> dd3d9721c, Q38FN CPU | +1.758% | Block B (d2) | sign claim only |
| C3 -> C4, 27B A/B (gate e) | pp +0.58% (floor 2.12%), tg -0.00% (floor 2.00%), identity 15/15 | `c4-fold-prep/GATE_e.done` | no-regression |
| C4 -> C5, Q38FN CPU (gate b) | -0.810% (51.45 -> 51.03 tok/s) | `c5-fold-prep/GATE_b.done` | informational sign claim |
| C -> C2, C2 -> C3 | none located (C2's DS41 5-pair compare died, `compare_rc=143`) | CH-20.1 | no verdict |
| DS41 C vs dd3d9721c | -12.821%, VOID (cold page cache) | Block B (a) | not a measurement |

## 6. Single-feature gains NOT captured in any whole-candidate chain

These are A/Bs of one feature (on a base build) or op-level numbers. Do not multiply them into the chain: each
one is already inside the whole-candidate ratio of the step that folded it (section 2), or was measured on a
different base, or is not folded.

| Feature (manifest row) | Number | Row | Where it is already counted / why not |
|---|---|---|---|
| n_q=1 decode on the GQA-packed verify kernel, MIN_NQ=1 for q8_0 KV (V11-127) | 27B no-draft d4096 1.004, d32768 1.08, d131072 **1.25** (15.5 -> 19.4 tok/s); q8_0 KV fold3: 27B tg@d32k 1.111, @d131k 1.251, A3B tg@d32k 1.062 | `c8-decode-x-sweep-20261107-r2`, `c8-fold3-gate-20261108` | inside C7r->C8 `tg@d` cells (1.0915 / 1.2497 / 1.0724) |
| LCATTN multi-seq GQA verify, GV_MULTISEQ (V11-126) | np4 DFlash2 decode aggregate **1.166x @32k, 1.252x @128k** (bars 1.05 / 1.20); verify FA 101 / 122 GB/s vs ~27 GB/s | `c8-lcattn-gate-20261107-r3` (KEEP_A_ONLY) | only the @32k gate-shape lands in the chain (np4 1.1969); the 128k np4 number has no whole-candidate counterpart |
| GDN chunked prefill (V11-125) | op 3.45x (27B) / 4.25x (A3B); 27B pp2048 1.120, pp8192 1.124, A3B pp2048 1.204, pp8192 1.189 | `c8-gdn-gate-20261107-r2` (C8GDN_NO_KEEP, folded by decision) | inside C7r->C8 pp cells |
| H18 CK hd256 long-context prefill (V11-129) | op FA 3.30x @32k, 3.73x @128k; 27B pp2048 d0 1.018, d32768 1.368, d131072 **2.223** (fold5: 1.564 / 2.422) | `c8-h18-gate-20261107` (REJECT as a single gate), `c8-fold5-gate-20261108` | inside pp2048@d cells |
| H20 prefill GEMM (V11-130) | 27B pp2048 1.0485, pp32768 1.0365; A3B 1.019 / 1.016 | `c8-h20-gate-20261107` (H20_NO_KEEP, folded) | inside C7r->C8 |
| token_embd on GPU (V11-128) | neutral: 27B 0.995-1.012, A3B 0.989-1.000; VRAM +1.2 GiB (27B) | `c8-3a-embd-on-gpu-20261107` | placement only |
| FA prefetch overlap (V11-135) | A/B 27B d131072 1.099x, A3B 1.048x (missed 1.10 bar) | V11-135 | inside C8->C9 (1.1058 / 1.073) |
| 27B `down` GEMM tile override (V11-136) | pp2048@d32768 **1.127x**, @d0 1.163x, tg 1.022 / 1.016; op 2.03x | `c10-gemmdown-prefill-ab-20261109`, `c9-gemm-tile-select-20261109` | inside C9->C10 (1.1593 / 1.1392) |
| GGML_CPY_BALANCE (V11-141) | CPU geomean 1.233 vs C10 | `c11-fold-nr-20261114` | this IS the whole-candidate step (2b); the first variant `c11-ssmcpy-cpu-20261114` 1.2250 is the same feature, do not add |
| llguidance sampler (V11-122) | tool-call grammar 3.70-3.93 -> 0.04-0.06 ms/token | SPEC-GRAM.3 `spec-gram3-llg-ab-20261105.json` | per-token sampler cost, no decode tok/s ratio |
| FAROWS gather (C15 candidate, knob `GGML_CUDA_FA_ROWS_GATHER`) | 27B Q8_0 + DFlash2 np4 unified q8_0 KV, >=33k/slot: verify per-step **1.092** (6 pairs 1.077-1.112), decode 0.991 (flat). Earlier r2: decode 1.000, verify 1.095 (indicative, no quiet q3) | `c13-farows-sidechannel-verify-quiet-20261118`, `c13-farows-sidechannel-gpu-20261117-r2` | single-feature A/B on a C13 build, knob off vs on; not a C14->C15 ratio (and C15 turns the knob default-ON). Rule FAIL on greedy identity, operator accepted as KEEP |
| CPU FA split-KV (candidate `b67125fbd`, NOT in C15 `b10f91e32`) | Q38FN MTP d4 per-step geomean P4K 1.1431, P32K 1.2563 (blocks 1.01-1.29) | `c15-cpu-fa-splitkv-speed-20261118-r2` (KEEP) | not folded; default-on decision pending; additive to C14 only after a fold gate |
| q8_1 sum-overflow v2 (`c8f7a85f1`, operator "fold it", NOT in C15 build) | Qwen3-VL-30B Q4_K_M :8086 decode -0.2% mean / -2.6% worst, pp16 -3.6%; 27B untouched | `q81-v2-e2e-gpu-20261118` COST_REAL | cost, not gain |
| iqk Q8_0 CPU prefill (V11-123) | A3B pf2048 1.5138-1.7028 | section 2e | whole-candidate for C5->C6 but not chainable forward |
| C7r bundle pieces (H10, H1b, H12, H13, H15, H5-PORT) | no per-piece pre-registered number | `c7r-gate-20261106` | only the whole bundle is pre-registered evidence (manifest V11-124 note) |

## 7. Caveats and double-counting rules

1. **Never multiply a section-6 number with a section-2 step that contains the feature.** Every C7r->C8, C8->C9,
   C9->C10 whole-candidate ratio already includes the features folded in that step. Multiplying MIN_NQ=1 (+25% @128k)
   or GV_MULTISEQ np4 (+17/+25%) onto the chain would double-count them; the chain value for 27B tg@d131072 is
   1.2497 (C8) x 1.1058 (C9, prefetch) x 0.9969 = 1.378, which already holds the MIN_NQ=1 gain.
2. **Manifest rule CH-16:** per-keep AutoKernel percentages are 5-pair screening numbers, not marginal or additive
   effects (36 per-commit claims compounding to +171.7% against a measured +8.524% block effect). The DS41/AK keeps
   V11-026..042 are therefore excluded entirely from the chain.
3. **Cell families differ per step.** Llama-bench cells (27B/A3B) are single-sequence, np1, f16 or q8_0 KV; Q38FN
   cells are llama-server MTP d4 serving at t48 np4. Do not join a llama-bench ratio to a serving ratio, and do not
   treat the np4 DFlash2 "gate shape" (aggregate decode at d32768) as serving throughput (manifest V11-135 note).
4. **Metric changes inside the Q38FN chain.** C10->C11 and C11->C12 are first-256 decode tok/s ratios; the v10->C12
   direct row and the GPU rows are per-step cost ratios (`predicted_ms/(predicted_n - draft_n_accepted)`).
   MTP acceptance is nondeterministic on GPU, so tok/s and per-step ratios disagree (e.g. C11->C12 GPU P2 0.8967
   tok/s vs 1.0639 per-step). The cross-check in 2b is approximate for that reason.
5. **Noise floors.** 27B d0 tg128 A/A floor 2.7% (C9 gate round spread 10%): the same C7r baseline shows
   1.0007 (rbseq), 1.0060 (fold3), 1.1018 (fold5), 1.0956 (H20 gate) across gates; read C8's d0 tg as flat.
   Q38FN GPU visit noise +-15% (operator-accepted, C14). CPU A3B pp512 chain is dominated by noise (identical C8/C9
   library gave 1.0808). C10 CPU q38 pp512 0.9837 was INCONCLUSIVE and operator-accepted on rounds 2-5.
6. **Failed/accepted gates still carry the recorded ratio.** C7r gate C7R_GATE_FAIL on one PPL sub-check (27B +0.17%
   PPL, accepted); C8 GDN and H20 gates were NO_KEEP and folded by decision; H18 KLD 3.0e-3 (bar set after seeing it);
   C14 GPU r3 FAIL on P3; C12 CPU r5 DROP (noise, overturned by the quiet row). Quality costs are real and unchained:
   v10->C12 CPU Q38FN KLD 0.0425 / top-1 93.5% at equal PPL (routing chaos from rounding-level changes).
7. **Provenance of the chain endpoints.** v10 and C10-era comparisons on GPU 27B use the store builds named in each
   row (e.g. C7r `gpu-20261106-62cb6a6af-c7r`, C8 `gpu-20261108-1bda248e3-c8rbseq`); each gate compared two stores in
   the same run, so ratios are internally paired, but the baseline medians drift between gates (27B tg128 d0 C7r
   median 26.98-31.25 tok/s), so only ratios, never absolute tok/s, are chained.
8. **"C15 has everything" is true of code, not of measurement.** C15 `b10f91e32` is C14 + FAROWS and nothing else
   from the planning list (q8_1 v2, split-KV, CH-33 are separate or later builds). Its own speed is unmeasured.
   The C15 CPU build is not byte-identical to C14 (`llama-graph`, `ggml.c`, kv-cache objects differ), so the
   "CPU carries by identity" argument that holds for C13->C14 does NOT hold for C15; a timing is required, and the
   only complete row (r1, geomean 0.9602) is a FAIL that the later contended rows neither confirm nor refute.
9. **What would close the gaps** (not scheduled by this write-up): a quiet v10-vs-C14 GPU row on 27B and A3B using the
   2a cell set; a Q38FN GPU MTP d4 v10-vs-C14 row; a quiet C14-vs-C15 CPU row. The v11 promotion rows 2-6 in the
   INF-83 draft set (held by operator D8, `v11-promotion-checklist.md`) are exactly these.

## Sources

- `handoffs/active/kernel-champion-and-promotion.md` (origin/main, C5..C14 ledger, fold gates)
- `docs/reference/kernel-manifests/llama-v11-manifest.md` (V11-121..V11-144)
- `handoffs/active/v11-promotion-checklist.md` (carry-in log)
- RESULT.json under `/mnt/raid0/llm/tmp/`: `c7r-gate-20261106`, `c8-rbseq-gate-20261108`, `c8-rbseq-cpu-gate-20261108`,
  `c8-fold3-gate-20261108`, `c8-fold5-gate-20261108`, `c8-gdn-gate-20261107-r2`, `c8-h20-gate-20261107`,
  `c9-fold-gate-20261109`, `c9-fold-cpu-gate-20261109`, `c10-fold-gate-20261109`, `c10-fold-cpu-gate-20261109`,
  `c11-fold-nr-20261114`, `c11-ssmcpy-cpu-20261114`, `c11-fold-gpu-20261114`, `up-bundle1-cpu-20261115-r2`,
  `up-bundle1-gpu-20261115-r5`, `c12-cpu-p3-quiet-20261117`, `c12-cpu-validate-20261116-r5`,
  `c14-fold-build-20261118`, `c14-fold-gpu-20261118-r3`, `c15-fold-build-20261118`, `c15-fold-gpu-20261118`,
  `c15-fold-cpu-20261118` (r1, r2, r4), `c15-cpu-fa-splitkv-speed-20261118-r2`, `c6-iqkq8pf-fold-gate-20261105`,
  `c6-iqkq8pf-fp16s-gate-20261106`.
