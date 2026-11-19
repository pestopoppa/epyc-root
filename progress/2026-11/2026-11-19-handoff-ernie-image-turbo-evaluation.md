# 2026-11-19 — handoff ernie-image-turbo-evaluation

## 09:36Z — Publish interleaved LFM 1.2B decode replay; GPU smoke queued

### WG-LFMI-2 — published replay, smoke pending

Published `lfmi2-interleaved-20261119` for `model-evaluation-queue.md:785`, the open combined-replay box (the bare ID also matches the completed GPU-arms box). Publisher returned GPU busy and queued its smoke; no PASS or measurement verdict exists and the task is not ticked. The row preserves 24 rotated native bench legs/72 cells and 20 native server responses across CPU/GPU and both LFM2.5-1.2B-Instruct quants, with separate within-launch and between-launch spread, tokens/task, finish reasons, sampled residency and explicit unknowns. The open task now states its model/build, denominator and futility limits required by task_lint. Source and offline preflight checks passed; main integration corrected the native `backends` key and supplied a keeper-engine launcher. This does not meet the requested smoke-PASS done-when yet.

Existing-file SHA-256 evidence: row.json `aba0bb0372f1cf27ffeb21ff809b7512cb8df89e14bd6913df9a7f74b6b76dae`; run.py `68937a66a11c3e10838eb9c8b56cd9003d76e6032219ccf2693d66fcf6234071`; inputs.json `6ac130d0fcbdd2b9e5ec2cc699f1ad78cb2cb5de75c9a63d8df86c5483a00280`. Files are at `/mnt/raid0/llm/tmp/lfmi2-20261119/`; no source trees, binaries or native logs copied into evidence directories. [no-belief: publication only; smoke queued, no measurement]
