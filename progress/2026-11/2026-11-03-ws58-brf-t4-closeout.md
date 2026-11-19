# 2026-11-03 — ws58: BRF-T4 pilot close-out (backlog refactor 2026-11)

No new compute. The results of the four D3 pilots were recorded against each pilot's predeclared rule. All verdicts are operational screens, never gate results.

| Pilot | Row | Verdict | Key numbers |
|---|---|---|---|
| EXP-09 | `brf-exp09-pilot-20261102` | REVISE (harness); BRF-T4-EXP09 ticked | Futility look after 37/48 cells: verified-quote 6.592/9 vs control 9.717/12. Accuracy: control 0.81, verified-quote 0.732, shape-header 0.50, pointer-only 0.271. All 5 parse failures were answers truncated at 256 tokens. On parsed paired items, verified-quote 0.824 vs control 0.808. |
| EXP-04 | `brf-exp04-pf1-crossover-pilot-20261102-r3` | REVISE; run invalid on GPU arms; not ticked | 0/4 GPU cells valid. A2: `-cmoe` is not a llama-bench flag. A1 mapped the unlisted store `libggml-hip.so` (`daf086c2a805…`, 2026-10-27, not in SHA256SUMS). A1-disabled/A0 0.859 (2K) and 0.959 (8K). |
| CAP-04 | `brf-cap04-pilot-20261102-v3` | REVISE (budget derivation); BRF-T4-CAP04 ticked | 76/76 units, all validity checks pass. Nested-prefix CHK 0/4, so no derived 8k/16k cell counts and TB-4 is UNCOVERED. 32k: frontdoor 0.50, critic 0.25 (2/12 truncated inside thinking); E: L2 0.95 = L3 0.95 at +1178 tokens. |
| EXP-01 | `brf-exp01-trellis-build-20261102` | No verdict | The BUILD ended rc=4: IQ2_KT needs an imatrix. No arms, and MEASURE was never published. `build_job.sh` was repaired in scratch; the BUILD `-r2` republish is pending. |

BRF-T4-R stays open (EXP-01 residual). The review table is in `handoffs/active/backlog-refactor-2026-11.md` → *T4 owner review — 2026-11-03*.

Finding for the operator (not fixed; the store is frozen): `kernels/builds/gpu-20260921-ffc1bac82/bin/libggml-hip.so` is an unversioned regular file (68,101,784 B, mtime 2026-10-27, sha256 `daf086c2a805a8cac8ab800198762a379e3d6852342f86539bf7d83837280d80`). It differs from the listed `libggml-hip.so.0.16.0` (`f26a166b8ea3…`) and is absent from SHA256SUMS. `llama-bench` maps both. `verify_kernel_store.sh` passes, because it checks linkage, not unlisted files.
