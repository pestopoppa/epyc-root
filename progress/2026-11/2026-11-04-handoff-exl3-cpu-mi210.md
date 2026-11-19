# 2026-11-04 — handoff exl3-cpu-mi210

## 07:20Z — Fix EXP01 smoke contamination and publish isolated rerun

Filed six terminal rows: build original/r2/r3 fail; r4 inconclusive; r5 pass; pilot r2 inconclusive. The pilot mixed one 4-thread smoke speed sample with 11 official 24-thread samples, invalidating its main ratio; withdrew the post-hoc cold-launch exclusion and EXPAND interpretation. Repaired separate smoke and official output routing, reject mismatched resume allocations and native n_threads. Publisher SMOKE PASS on CPUs 0-3; published brf-exp01-trellis-pilot-20261104-r3 with unchanged four arms, repetitions, item set, estimator and stop rules. Official output /mnt/raid0/llm/tmp/brf-exp01/run-r3/results.jsonl. Code and filing evidence archived at artifacts/compute/exp01-pilot-smoke-isolation-20261104/. EXP01-PILOT stays open for the new result.

## 07:20Z — Fix EXP01 smoke contamination and publish isolated rerun

Filed six terminal rows: build original/r2/r3 fail; r4 inconclusive; r5 pass; pilot r2 inconclusive. The pilot mixed one 4-thread smoke speed sample with 11 official 24-thread samples, invalidating its main ratio; withdrew the post-hoc cold-launch exclusion and EXPAND interpretation. Repaired separate smoke and official output routing, reject mismatched resume allocations and native n_threads. Publisher SMOKE PASS on CPUs 0-3; published brf-exp01-trellis-pilot-20261104-r3 with unchanged four arms, repetitions, item set, estimator and stop rules. Official output /mnt/raid0/llm/tmp/brf-exp01/run-r3/results.jsonl. Code persisted in scripts/experiments/exp01-pilot/ and filing evidence in docs/evidence/exp01-pilot-smoke-isolation-20261104.json. EXP01-PILOT stays open for the new result.

## 07:22Z — Acknowledge duplicate EXP01 r2 end; await isolated rerun

Duplicate r2 event acknowledged with its existing inconclusive verdict retained. No new measurement or box completion claimed. EXP01-PILOT awaits the already smoke-passed and running isolated successor brf-exp01-trellis-pilot-20261104-r3; use its official run-r3 results for the port/futility decision.

## 07:23Z — Acknowledge already-filed EXP01 build-r3 event

Duplicate build-r3 end acknowledged; existing fail verdict retained (missing shared-expert imatrix entry). The completed build-r5 supersedes it. EXP01-PILOT awaits the running, smoke-passed isolated measurement brf-exp01-trellis-pilot-20261104-r3.

## 07:24Z — Acknowledge already-filed EXP01 build-r2 event

Duplicate build-r2 event acknowledged; retain its existing fail verdict for incomplete importance-matrix coverage. Build-r5 supplies the completed prerequisite. The isolated pilot brf-exp01-trellis-pilot-20261104-r3 is running; no new evidence or task completion claimed.

## 07:33Z — Complete bounded EXP01 pilot with inconclusive disposition

Filed isolated r3 inconclusive (rc=0): all 12 speed launches used 24 threads in the grant; IQ4KT/Q4KM=0.9630 band [0.9436,0.9824], IQ2KT/IQ2XXS=0.9610 [0.9392,0.9828]. Neither predeclared stopping condition reached by the three-launch-per-arm cap. Paired quality: 12 both correct, 10 both wrong, 2 IQ4KT-only, 0 Q4KM-only; 14/24 versus 12/24, exact paired p=0.5. Completed the bounded pilot box; T2/T3 and port remain undecided. Preserved original raw records and hashes in docs/evidence/exp01-pilot-r3-20261104/; findings and concrete optional follow-up in docs/findings/exp01-trellis-proxy-pilot-20261104.md. Registered prospective source wiring without retroactive measurement warrant. Duplicate build-r5 event acknowledged with its existing pass retained.

## 07:37Z — Acknowledge superseded EXP01 build-r4 event

Duplicate build-r4 receipt acknowledged; its existing inconclusive verdict remains unchanged. EXP01-PILOT was completed and filed at cc76988485246dbfaf9757dcc7b1cdc195dfe02d. T2/T3 stay open; no port trigger or extended compute authorization follows from the bounded pilot. The concrete extension decision package remains docs/findings/exp01-trellis-proxy-pilot-20261104.md.

## 15:24Z — Acknowledge already-filed EXP01 pilot-r3 event

Duplicate pilot-r3 event acknowledged; existing inconclusive verdict and completed bounded pilot remain unchanged. IQ4KT/Q4KM 0.9630 [0.9436,0.9824]; the port trigger and futility rule were not met. The concrete follow-up decision package remains in docs/findings/exp01-trellis-proxy-pilot-20261104.md.

## 15:54Z — Preserve the filed EXP01 speed extension

The already-filed, already-ticked EXP01-EXT row brf-exp01-trellis-ext-20261104-r4 completed rc=0 with eight interleaved launches per arm on CPUs 0-23 and 24 native threads. IQ4KT/Q4KM tg128=0.9530, operational band [0.9373,0.9687]; neither declared stop fired and no quality items were run. Extension is inconclusive, port remains on hold and formal T2/T3 gates remain open. Corrected the linked findings report, replacing the now-executed proposal with the actual result, and retained native JSON, logs, end record and manifest with hashes. This is committed-conclusion evidence, not a retroactive measurement tuple. Duplicate FILED receipt acknowledged.
