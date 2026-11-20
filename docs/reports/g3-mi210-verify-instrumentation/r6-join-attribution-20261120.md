# G3 R6 missing-residency-join attribution (2026-11-20)

The retained native capture has two independent failure modes: dispatches outside complete observation intervals, and fewer than two distinct valid observations inside an invocation. Added explicit failure lists and distinct counts to `sysfs_residency.correlate`; qualification predicates and historical UNKNOWN are unchanged. This diagnoses capture coverage, not GPU absence or kernel selection.

| Cell | Dispatches | Bounded | Missing overlap only | Missing persistence only | Both |
|---|---:|---:|---:|---:|---:|
| q8_0-d1 | 5260 | 740 | 1170 | 717 | 2633 |
| q8_0-d4 | 2230 | 661 | 1549 | 3 | 17 |
| q4_0-d1 | 4810 | 716 | 1124 | 641 | 2329 |
| q4_0-d4 | 2080 | 623 | 1447 | 1 | 9 |

All **14,380** original join statuses, valid-sample counts and overlap counts reproduced exactly using the original native timestamps and retained samples. No native inference or new measurement was run. This is a census of the retained four cells; there is no sampling-error estimate or generalization beyond them. Question: which existing join predicate prevents complete coverage? Stop on exhaustive attribution and exact original-field agreement; refuse on missing records or any mismatch.

The fast sampler explicitly waits 1 ms after each sequential collection. An asynchronous sampler provides no guarantee that every dispatch overlaps a complete collection, or that short invocations contain two such collections. The d4 failures are overwhelmingly overlap failures even where persistence succeeds; simply increasing request length already failed to resolve this. No wider timestamp window or persistence waiver is justified. A future diagnostic must arrange dispatch-synchronous residency capture, preserving invocation bounds, two distinct observations, process/device identity and independent environment controls. Merely removing the sleep cannot guarantee coverage.

Validation: **120/120 model-free tests PASS** in this diagnostic directory. New regression scenarios cover success, overlapping duplicates, gaps despite persistence, wrong identity, out-of-window/nonpositive samples and no observations. GitNexus unavailable (lane unindexed); direct caller search finds the timed analyzer as the production consumer of this additive output. Existing compiled runtime and raw evidence remain untouched.

Original evidence (no copied logs):

- Result `/mnt/raid0/llm/tmp/df2/g3-six-native-r6-20261120/RESULT.json`, SHA-256 `4cbfd3a5d7c80dce3ce4c0679fd7bd1b659f6e5d67e63111d0a43e9646710631`.
- q8_0-d1: `/mnt/raid0/llm/tmp/df2/g3-six-native-r6-20261120/runs/attempt-i3ku1ym_/capture/q8_0-d1/fast-residency.jsonl`, SHA-256 `6be03a88630c00c09aaeec44811423a43341432c41052a0cbf7edf11bce1befd` (9297 observations).
- q8_0-d4: `/mnt/raid0/llm/tmp/df2/g3-six-native-r6-20261120/runs/attempt-i3ku1ym_/capture/q8_0-d4/fast-residency.jsonl`, SHA-256 `8850f581e996ef4e2c1119e040a9a4cb55745e7d9e972d204deb7a120c2dd3c7` (8999 observations).
- q4_0-d1: `/mnt/raid0/llm/tmp/df2/g3-six-native-r6-20261120/runs/attempt-i3ku1ym_/capture/q4_0-d1/fast-residency.jsonl`, SHA-256 `31e4ecb0b833b8d3ab151715fffdbb33f995026cb17e0812e0840222315a5136` (8867 observations).
- q4_0-d4: `/mnt/raid0/llm/tmp/df2/g3-six-native-r6-20261120/runs/attempt-i3ku1ym_/capture/q4_0-d4/fast-residency.jsonl`, SHA-256 `5d1e0bf57a988a87c61e874162f2ecfd0c7ff9041fc4eb0ca64f893d670d3e8f` (8445 observations).

Source SHA-256:
- `sysfs_residency.py`: `be182b2b247fae2bf6c3e6db40d5d89c6fa6e59e4a0410b8d1146f287af60149`.
- `test_sysfs_residency.py`: `775d32d077e56fadd96d8db3947a8e848588a6baf4065ec577308213bf434031`.

Existing G3 instrumentation source registration and VB-SERVING-DF2 wiring apply; no new measurement producer or grading rule. Future native row source manifests must bind the changed analyzer source. Parent G3 stays open; original protocol `vec_observed=null`.

[no-belief: diagnostic attribution and model-free tests; original endpoint UNKNOWN]
