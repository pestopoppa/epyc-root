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
