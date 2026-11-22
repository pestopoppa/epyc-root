# 2026-11-22 — handoff triattention-kv-selection

## 00:53Z — Prepared continuation of automatically filed partial CPU sparse end-to-end row.

Row lsa-cpu-sparse-e2e-20261121-r2 ended rc=75 at deadline; auto-filed partial. Five valid f16 gate pairs yield geometric mean 1.09172 and 95% lower bound 1.07056; this is provisional because required greedy quality remains unmeasured. Checkpoint results.jsonl SHA-256 a2d21a1c5ab9349e178f0933b44f420aa03e32c0991a564856c30aaae8ee1653. q0/q2 were reserved idle contention probes, not a hung job; contamination recorded and cell p50 gates passed. Published continuation lsa-cpu-sparse-e2e-20261122-r3 using the original checkpoint and identical pinned inputs; publish queued smoke rather than returning PASS. Resume only once smoke passes or fails; remaining descriptive q8 and quality phases precede verdict. Original input files were retained by partial reaper.

## 03:13Z — Handle filed r3 partial and initiate r4 continuation

LSA-CPU-SPARSE-E2E: r3 ended rc=75 at the grant window boundary and was automatically filed partial; no final RESULT.json. Checkpoint has five valid f16 gate pairs and two q8 pairs; the third q8 dense cell was interrupted. q0/q2 were intentionally idle contention controls, with valid q8 cell p50 1.13–1.29%; contamination alerts do not by themselves invalidate those cells under the registered p50 <=15% rule. Initiated r4 publication using the same checkpoint and registered three-quarter shape; smoke completion remains to be handled. Evidence: filing-done/lsa-cpu-sparse-e2e-20261122-r3.verdict.json; out/results.jsonl in /mnt/raid0/llm/tmp/lsa-cpu-sparse-e2e-20261121-r2.
