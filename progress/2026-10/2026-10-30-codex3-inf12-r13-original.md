# INF-12 R13 original run: partial native results

The original normal GPU run `20261030T143833Z-2507566` started 14:38:33 UTC and stopped at its work deadline at 15:06:30 (launcher END 15:06:31), rc 75, while processing the first base source, `Accurate_Retrieval/eventqa_131072`. The child exited 143 and was reaped; cleanup covered the direct child only and descendants were not censused. The later 15:12:28 rearm shares the output namespace and overwrote `LAST-RUN`; it is a separate run.

The observed native JSONL has 16 distinct rows (IDs 0–15) for base `eventqa_131072` against 500 expected for that source and 3,671 across 22 pinned sources per arm. The observed base native eventqa recall and exact match are 11/16 (0.6875); mean F1 is 0.8134858197, substring exact match 0.6875, ROUGE-L F1 0.8284428903, and ROUGE-L recall 0.8492063492. These are also the sample-weighted means over the 16 observed base rows; they do not represent full-population performance. No DeltaMem results were observed in the original run. All other source/arm coverage is zero observed, not a measured score. The audit contains the full source population and raw metric sums.

The JSONL mtime is 15:05:48 UTC, before the original stop, and its SHA-256 is `93027f349ed913c27040aa6932399eca9a39f43d76a8795eabe02fcb4bd5ec95`. It was copied after the later rearm started; no independent original-end snapshot was taken, so the exact original-boundary content and any unknown cases cannot be independently established from this snapshot. This partial coverage provides no base-versus-DeltaMem comparison or Gate 2 verdict. [belief: cc]

Audit: `artifacts/inf12-r13-original-audit-20261030.json`; native run, child, cleanup, and separate rearm paths are recorded there.
