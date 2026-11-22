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

## 15:07Z — Resume EA-POOL-SCREEN after filed partial r4

EA-POOL-SCREEN: r4 ended rc=75 after its window and was filed partial (results SHA-256 1adc0bf3e0b40848f18a552fb4060c0508e7b3f778495f52cb4dc81c7b0200ed); the registered screen is incomplete. Prepared r5 using the saved item results and started publish/smoke; no scientific verdict yet. Exact top-k remains unavailable on this build.

## 15:10Z — Publish EA-POOL-SCREEN r5 continuation and pass smoke

EA-POOL-SCREEN: continuation ak-ea-pool-screen-gpu-20261122-r5 was published and passed its smoke on 2026-11-22 15:09:35Z (PASS.json SHA-256 832c2a53177242b6f1517bfafaf3ef839a74480f0fdc1ef9e62448f10774a11b); it is grantable. Its 88 banked result records match r4 (SHA-256 1adc0bf3e0b40848f18a552fb4060c0508e7b3f778495f52cb4dc81c7b0200ed). The scientific screen remains incomplete.

## 22:31Z — Resume EA-POOL-SCREEN after filed partial r5

EA-POOL-SCREEN r5 ended rc=75 and was filed partial. Its 111 banked records have SHA-256 3a713e8262b3a42fc3056c16047a7af8decb98c5f4ae23b773078bcf6b753136. Prepared r6 from that checkpoint and started publication and smoke; the screen has no final scientific verdict.

## 22:46Z — Complete publication of EA-POOL-SCREEN r6

EA-POOL-SCREEN r6 publication smoke passed at 2026-11-22T22:45:00Z; row ak-ea-pool-screen-gpu-20261122-r6 is grantable. PASS evidence: /mnt/raid0/llm/tmp/compute-flags/dryrun/ak-ea-pool-screen-gpu-20261122-r6/PASS.json; full scientific verdict awaits its result.
