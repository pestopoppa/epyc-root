# 2026-11-22 — handoff triattention-kv-selection

## 00:53Z — Prepared continuation of automatically filed partial CPU sparse end-to-end row.

Row lsa-cpu-sparse-e2e-20261121-r2 ended rc=75 at deadline; auto-filed partial. Five valid f16 gate pairs yield geometric mean 1.09172 and 95% lower bound 1.07056; this is provisional because required greedy quality remains unmeasured. Checkpoint results.jsonl SHA-256 a2d21a1c5ab9349e178f0933b44f420aa03e32c0991a564856c30aaae8ee1653. q0/q2 were reserved idle contention probes, not a hung job; contamination recorded and cell p50 gates passed. Published continuation lsa-cpu-sparse-e2e-20261122-r3 using the original checkpoint and identical pinned inputs; publish queued smoke rather than returning PASS. Resume only once smoke passes or fails; remaining descriptive q8 and quality phases precede verdict. Original input files were retained by partial reaper.

## 03:13Z — Handle filed r3 partial and initiate r4 continuation

LSA-CPU-SPARSE-E2E: r3 ended rc=75 at the grant window boundary and was automatically filed partial; no final RESULT.json. Checkpoint has five valid f16 gate pairs and two q8 pairs; the third q8 dense cell was interrupted. q0/q2 were intentionally idle contention controls, with valid q8 cell p50 1.13–1.29%; contamination alerts do not by themselves invalidate those cells under the registered p50 <=15% rule. Initiated r4 publication using the same checkpoint and registered three-quarter shape; smoke completion remains to be handled. Evidence: filing-done/lsa-cpu-sparse-e2e-20261122-r3.verdict.json; out/results.jsonl in /mnt/raid0/llm/tmp/lsa-cpu-sparse-e2e-20261121-r2.

## 04:38Z — File completed LSA CPU sparse end-to-end quality-gated verdict

LSA-CPU-SPARSE-E2E: filed r4 rc=0 DROP_QUALITY; f16 32k 5-pair geomean 1.09172 (95% CI 1.07211–1.11169), speed gate passed but greedy differs at token 56 of 64; KLD mean 0.001919, p99 0.008681. q8 descriptive geomean 1.34605 (3 pairs); no 64k measurement. RESULT.json SHA-256 3cf11edd4607947d59b01be56ecd03f0a3f54a09b0b4efda9603ba6849fa3edb. Contention alerts acknowledged: q0/q2 are registered idle controls and cells passed p50 gate.

## 05:12Z — Publish continuation of EA pooling screen after window-ended partial result

EA-POOL-SCREEN: prior row ak-ea-pool-screen-gpu-20261121 ended rc=75 at its window boundary and was filed partial; continuation ak-ea-pool-screen-gpu-20261122-r2 reuses its checkpoint and was published, with GPU smoke queued because the GPU is busy. No screen verdict yet.

## 08:35Z — File inconclusive EA pooling screen continuation

EA-POOL-SCREEN: filed ak-ea-pool-screen-gpu-20261122-r2 inconclusive (rc=0, FUTILITY_INPUT, RemoteDisconnected); server log ends with second interrupt during item 7 CE10. Per-arm n=7–8, insufficient for registered verdict; no box tick. RESULT.json SHA-256 2cb48c9a12423f2e16dc33cf877b22d426fa41a61cf4505fa5684b68feed8f3c; results.jsonl SHA-256 c34551e60eff87a0e3f96296fcf9b5a862dbc6bf7a4c968c433fa67ded8f35b1. Filed with no reclaim to preserve checkpoint.

## 09:57Z — Handle stopped EA pooling screen row and continuation collision

EA-POOL-SCREEN: r3 stopped rc=75 during i7-CE10 and was auto-filed WITHDRAWN; no scientific verdict. A separate publisher had already published r4 and started its smoke when this session attempted continuation; left its live row intact. r4 smoke PASS remains unconfirmed.
