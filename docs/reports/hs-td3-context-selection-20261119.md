# HS-TD-3 paired context-selection screen — 2026-11-19

The completed frozen authored panel preserves exact-answer correctness while reducing the answer context. Selector cost makes the typed path slower on this run. Filing verdict: pass for completion of the prospective descriptive comparison; this is not a benefit threshold, promotion gate or live-task acceptance.

All 36 scheduled requests completed (12 selection, 12 baseline answers, 12 typed answers), rc=0 at 2026-11-19T07:10:58Z. Both answer arms score 12/12 correct with 0/12 unknown; paired wins/losses/ties are 0/0/12. Selection is schema-valid and matches the authored file set on 12/12 tasks. Higher exact correctness is better; lower bytes and total call wall time are better. Unknowns retain the planned denominator; smoke is excluded.

| Quantity | Baseline | Typed |
|---|---:|---:|
| Correct / planned | 12/12 | 12/12 |
| Unknown | 0 | 0 |
| Answer-context serialized bytes, summed | 5101 | 1897 |
| Answer call wall time, summed (s) | 28.368282 | 25.172022 |
| Selector call wall time, summed (s) | 0 | 67.346045 |
| Answer plus selector call wall time (s) | 28.368282 | 92.518066 |

Answer-context bytes fall by 62.81%. The typed answer calls alone save 3.196260 s, but selector calls add 67.346045 s: the combined recorded call sum is 3.261 times baseline (+64.149784 s). These are descriptive single-run timings, with no uncertainty estimate or population speed claim.

The byte metric counts serialized files sent to answer calls only. The selector receives the candidate contents; these bytes are not included in that reduction. Thus the result does not establish lower total prompt traffic. The wall metric sums HTTP call intervals, including selector calls on the typed path; it is not end-to-end task latency including preparation, server startup or all assembly overhead.

| Case | Baseline correct | Typed correct | Selected file set exact | Selector confidence | Baseline call s | Typed answer + selector s |
|---|---|---|---|---:|---:|---:|
| context-00 | True | True | True | 1.0 | 1.532305 | 4.196675 |
| context-01 | True | True | True | 1.0 | 1.550333 | 3.793107 |
| context-02 | True | True | True | 1.0 | 2.101819 | 7.370816 |
| context-03 | True | True | True | 1.0 | 2.477649 | 7.082424 |
| context-04 | True | True | True | 1.0 | 2.274796 | 7.885500 |
| context-05 | True | True | True | 1.0 | 2.217847 | 9.449374 |
| context-06 | True | True | True | 1.0 | 2.112372 | 7.574662 |
| context-07 | True | True | True | 1.0 | 2.464844 | 7.352260 |
| context-08 | True | True | True | 1.0 | 2.919284 | 9.162585 |
| context-09 | True | True | True | 1.0 | 3.680385 | 11.952997 |
| context-10 | True | True | True | 1.0 | 2.452541 | 8.394790 |
| context-11 | True | True | True | 1.0 | 2.584108 | 8.302876 |

Confidence is logged, uncalibrated self-report. Tasks are twelve authored integer configuration questions, not live coding tasks; both arms reach the accuracy ceiling. The worker is Qwen3.6-35B-A3B-MTP-Q8_0 on frozen-v10 CPU without MTP. Answer order alternates by case, with selection always first. The baseline was prepared using default all-file `edit_transaction.assemble_context` at epyc-orchestrator commit `273ba3ff85347c6429b5b86a6200073010d3f703`, source blob `ea7aeaa122e543f53e61e4eba3d33ec4b906546d`. Typed assembly uses the selected distinct closed-set file IDs and verbatim content. This panel supports a bounded task-quality A/B only; it cannot establish live-task quality, generalization or production value.

Evidence remains native; no source tree or raw record copy is included:

- Row: `hs-td3-context-selection-cpu-v1-20261119`; native summary `/mnt/raid0/llm/tmp/repl-turn-efficiency/hs-td3-context-v1/RESULT.json`, SHA-256 `cdaa41b4422918df4db6d394e9b7308e1cf5a83c6e54579df6d7b7ed8a1f330f`.
- Native original requests, responses and confidence: `/mnt/raid0/llm/tmp/repl-turn-efficiency/hs-td3-context-v1/results.jsonl`, SHA-256 `28ce4383e284f44b37c4f70a6dba1c1868d14fa33eba910342dfe47474bfce1c`. Only full-phase records enter this comparison.
- Native custody and individual call files are under `/mnt/raid0/llm/tmp/repl-turn-efficiency/hs-td3-context-v1` and located by each original record.
- Runner `scripts/harness/hs_td3_probe.py`, git blob `5e4d4ecca4da7b5ab880eb94add74664f9a129a2`.
- Frozen v10 CPU server SHA-256 `4483bcfc92c5c3bb0005df31e1c668cb565d49f7b40ba94f4df5a126cbbb648c`.

Existing prospective typed-decision belief enrollment remains authoritative; this committed conclusion is an observation [belief: cc], without a new measurement warrant, grading ladder or read-side wiring claim.
