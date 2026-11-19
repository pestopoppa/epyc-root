# Public Results Adjudication - 18 Retained Protocol-Tag Rows (INF-85 W3)

Date: 2026-11-10. Owner: AutoKernel (workspace-18) as of 2026-11-11 (adjudication authored by workspace-f2). Production kernel at adjudication: production-consolidated-v10
(`llama-server --version` 10303, `ffc1bac82`).

Source: `epyc-inference-research` `docs/reference/benchmarks/RESULTS.md` (HEAD `a794f5b54`), run through
`scripts/publication/generate_public_results.py` (output to scratch; tracked draft and queue regenerate
byte-identical to the committed queue: 374 rows, 18 `protocol-tag-needed`, 356 `retired_from_public_claims`).
The generator is not changed and no generated output is hand-edited. This document is a decision record only.

## Rules applied

- Claim rule (`MEASUREMENT_POLICY.md`, *The claim rule*): "A decision-gating number = `(metric, protocol-id, n/reps, date, attestation ref)`. A number without a protocol citation is an **observation**: usable for hypotheses, never for keep/revert/deploy/promote/buy/close decisions." No retained row carries a protocol id, so none is a claim as it stands.
- Era registry (`instrument_eras.yaml`): E0 "Pre-canonical bench protocol. All CPU bench claims demote-to-prior" (until 2026-04-26); E5/E6/E8/E9 each state "pre-boundary CPU throughput ... rows ... are demote-to-prior/historical priors ... Do not rescale across this boundary; re-measure within era under P-BENCH/P-QUAL protocols with host attestation." All 18 rows predate 2026-04-26, i.e. sit in E0 and are four kernel promotions behind v10.
- Retroactivity (`MEASUREMENT.md` s6): retro-certify only if "provably produced by a now-named protocol (command/env/reps recorded)"; otherwise demote-to-prior, which "CANNOT gate".
- Quality carve-out (`MEASUREMENT_POLICY.md`, deterministic replay): quality scores can transfer across kernel eras once parity is proven. It does not rescue these quality figures: they are algorithmic-era scores that RESULTS.md itself says were inflated 15-30pp and rescored on 2026-03-09, and no parity pair exists.
- Verdicts: PUBLISH = complete evidence in the current era; HOLD-RERUN = a named rerun can make it publishable and the row is still public-relevant; DROP = superseded, unrecoverable, mislabelled or no claim content.

## Summary

PUBLISH 0, HOLD-RERUN 2, DROP 16.

## Adjudication table

Evidence abbreviations: IR = `epyc-inference-research`. `runs/` = `IR:benchmarks/results/runs/`.

| Line | Section | Row | Value | Evidence found | Verdict | Reason |
|---|---|---|---|---|---|---|
| 46 | Best Results | Qwen3.5-122B-A10B Q4_K_M | 9.2 t/s; quality TBD | Raw: `runs/20260303_170903/qwen35_122b_q4km_baseline.json` (git `8f37c2c76`, 2026-03-29): avg 9.159 t/s over 61 questions, run 2026-03-08. No protocol id, no host attestation, E0-era harness/kernel. Row itself says quality "not yet benchmarked". | HOLD-RERUN | Speed is real and traceable but E0 demote-to-prior, 4 kernel eras stale, unattested. Public-relevant model (largest hybrid MoE on the box). Rerun R1 below. |
| 170 | Concurrent Sweep 2026-02-19 | routing entrypoint (30B MoE) | Aggregate TPS +121.74% | Raw: `IR:benchmarks/results/eval/concurrent_sweep_20260219_144159.{csv,summary.json}` (git `0b6f31125`): n_warmup 2, n_measured 5, n_predict 128; baseline 89.57 -> 198.61 agg t/s at np=2; p95 x1.33. Run on the Feb-2026 ik/pre-v5 stack, no protocol id, no attestation. np=3 rejected by p95 gate. | HOLD-RERUN | The mechanism (np=2 doubles aggregate) is a P-BENCH-3 question and still public-interesting, but the percentage is an E0 observation on a retired frontdoor model/kernel. Rerun R2 below. |
| 171 | Concurrent Sweep 2026-02-19 | coder (32B dense) | Aggregate TPS change "-" | Same summary.json: np=2 candidate +100.92% rejected (p95 x1.977); baseline 41.88 t/s. | DROP | Row asserts no number (rejected candidate, np stays 1); internal-role tuning outcome, model retired from lineup. Nothing to certify. |
| 172 | Concurrent Sweep 2026-02-19 | worker (7B) | Aggregate TPS change "-" | Same summary.json: candidate rejected (p95 >= 1.505). | DROP | As 171: no metric value, internal role tuning, retired model. |
| 359 | Dense Spec Decode (K-sweep) | Qwen2.5-7B + Coder-0.5B | 18.5 -> 46.6 t/s, 2.5x, Q 90% | Only derivation: `IR:research/K_VALUE_OPTIMIZATION.md` (2026-01-16; "empirical testing pending") quoting K24=46.6. All `*spec_draft*` raw from the buggy llama-server timing path were deleted 2026-01-15 (`IR:benchmarks/results/REBENCHMARK_NEEDED.md`: server timing ~28x inflated). | DROP | Raw not recoverable; value is a post-bug "corrected" figure with no banked run. Pre-E0, Qwen2.5-era draft pairing superseded. Quality is algorithmic-era (inflated). |
| 360 | same | Qwen2.5-Coder-32B + qwen25_coder | 3.4 -> 21.3 t/s, 6.3x, Q 93% | Banked raw `runs/20251220_214317/ingest_qwen2_5_coder_32b_spec_draft_qwen25_coder_k24.json`: 17.02 t/s, questions_tested=1 (2026-01-15). 21.3 does not reconcile to any banked run. | DROP | Headline value contradicted by the only surviving raw (17.0, n=1); no protocol; superseded model family. |
| 361 | same | gemma-3-27B + gemma3 | 2.2 -> 19.6 t/s, 8.9x, Q 95% | No banked raw (spec_draft purge); appears only in RESULTS.md and research summaries. | DROP | Unrecoverable raw, E0, retired-from-lineup model; 8.9x spec speedup is exactly the class of figure the timing bug inflated. |
| 362 | same | gemma-3-12b + gemma3 | 9.3 -> 14.8 t/s, 1.6x, Q 97% | As 361. | DROP | As 361. |
| 363 | same | DeepSeek-R1-32B + 1.5B | 2.0 -> 10.1 t/s, 5.1x, Q 94% | As 361. | DROP | As 361. |
| 364 | same | Meta-Llama-3.1-70B + PARD-1B | 2.1 -> 9.0 t/s, 4.3x, Q 93% | As 361. | DROP | As 361. |
| 365 | same | DeepSeek-R1-7B + PARD-1.5B | 10.6 -> 9.9 t/s, 0.9x, Q 88% | As 361. | DROP | As 361; additionally a slowdown row with no current consumer. |
| 366 | same | DeepSeek-R1-14B-Q6KL + PARD-1.5B | 5.1 -> 8.5 t/s, 1.7x, Q 98% | As 361. | DROP | As 361. |
| 367 | same | Qwen2.5-Math-72B + 1.5B | 2.0 -> 7.0 t/s, 3.5x, Q 77% | As 361. | DROP | As 361. |
| 368 | same | Qwen2.5-72B + qwen25 | 1.9 -> 3.0 t/s, 1.6x, Q 91% | As 361. | DROP | As 361. |
| 974 | Production Role Assignments | Qwen3-Coder-30B-A3B + MoE6+spec+lookup | Q 68%; 47.11 t/s | No raw run for 47.11 found in `benchmarks/results` (searched index, reviews, runs). Dagger-marked quality is a 2026-03-09 rescore. Frontdoor MoE4 raw for contrast: 21.96 (2026-01-06), 28.35 (2026-03-07), 25.95 (2026-06-20), all single-config sweeps. | DROP | Expert-reduction (MoE6) + lookup recipe from the retired ik-era frontdoor; production frontdoor and kernel have since changed (E5-E9). No banked raw, quality is rescored-in-place not re-run. |
| 975 | same | Qwen3-Coder-30B-A3B + MoE4 | Q 62%; 17.7 t/s | Raw `runs/*/frontdoor_moe4.json` read 22.0 / 28.4 / 25.9 t/s across runs; 17.7 matches none. | DROP | Value not traceable and disagrees with banked MoE4 runs; superseded recipe. |
| 976 | same | Qwen3.5-35B-A3B Q5_K_S | Q 89%; 12.5 t/s | Raw `runs/20260303_170903/qwen35_q5ks_baseline.json`: 12.476 t/s, 61 q, 2026-03-08, BUT model path is `Huihui-Qwen3.5-35B-A3B-abliterated.i1-Q5_K_S.gguf` (third-party abliterated imatrix quant). `reviews/summary.csv` records that model's quality as 0/0 (0%); 89% has no source. | DROP | Entity mislabelled (abliterated third-party model published as Qwen3.5-35B-A3B); quality unsourced; E0. Publishing would misattribute. A clean 35B-A3B number belongs to the current-lineup rerun, not this row. |
| 977 | same | Qwen3.5-122B-A10B Q4_K_M | Q 86%; 9.2 t/s | Speed duplicates row 46 (same raw, 9.159). Quality 86%: no source in `reviews/summary.csv` or runs (`avg_algorithmic_score` null). | DROP | Speed is covered by row 46 / R1; quality 86% unrecoverable. Duplicate of a HOLD-RERUN row, so no separate rerun. |

## Rerun list (the exact measurements needed to clear the two HOLD-RERUN rows)

Both need: no concurrent inference, `canonical_host_attestation.py` receipt, production kernel v10 binary
proven by content (`verify_llama_cpp.sh` plus `strings`/version `10303`/`ffc1bac82` and
`verify_ggml_linkage.sh`), results logged with the claim grammar. Neither is run by this task.

- **R1 (row 46): Qwen3.5-122B-A10B Q4_K_M decode throughput.** P-BENCH-1 (canonical single-instance decode, llama-bench, `bench_canonical.sh`), v10 CPU kernel from `kernels/production/cpu`, instrument_class `bench`, reps >= 5 (median + MAD; >= 10 only if the claim is an effect under 2%), GGML_IQK recipe as in the registry. Publish as `decode <median> tok/s [P-BENCH-1, n=<reps>, <date>, attest <ref>]` labelled bench-class (not a serving number). If the page must show a serving headline, add one P-BENCH-4 server-native run on the registered recipe; no draft path exists for this hybrid, so the unaccelerated run is the OPTIMUM. Quality column stays blank (a rescore from banked outputs is not a P-QUAL claim).
- **R2 (row 170): slot-concurrency (np) scaling of the production frontdoor model.** P-BENCH-3 (`-np N` sweep; aggregate and per-stream decode, p95), `scripts/benchmark/concurrent_inference_sweep.py` against the CURRENT frontdoor role/model on v10, np in {1,2,3}, n_warmup 2, n_measured >= 5 per np, serving class with the registered recipe (the 2026-02-19 percentage is for a retired model and cannot be rescaled). If R2 is not worth a compute window, retire row 170 instead.

## Notes for the owning session

- Two of the 18 survive as holds only because a clean rerun is cheap; the rest are closed here. W3's "18 retained rows need protocol evidence adjudication" is therefore adjudicated: 0 publish, 2 awaiting R1/R2, 16 to be recorded as retired in `public-results-review-decisions.json` (the overlay is the generator's retire mechanism and is applied by the owning session, not here).
- Out of this scope but noted: the 31 pre-attestation P-BENCH-2 rows were already retired 2026-11-02; with these decisions W3 can publish zero rows until R1/R2 land, so the public page would be empty. If that is unacceptable, R1 plus one fresh P-BENCH-1 sweep of current-lineup models is the cheapest path to a first publishable table.
