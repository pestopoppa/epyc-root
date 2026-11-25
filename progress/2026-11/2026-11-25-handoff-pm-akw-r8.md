# 2026-11-25 — handoff pm-akw-r8

## 12:33Z — AK waste audit R8: GPU smoke hold ends when the smoke ends

- **AKW-R8 (pipeline-mgmt)**: R8 smoke-hold release + event-driven keeper wake shipped in root 05d00706f (rebased; on origin/main via 8139fc81a), live via deploy_rowflow ac90f161b (unit 1519 passed, replay 91 passed). Batch drops its lock on empty queue; exited-tree SMOKE.lock no longer an occupant; PASS/FAIL/exit/batch-end bump ready/ mtime so the keeper's 5 s poll runs allocate at once; one quiet sample after the keeper's own smoke exit. No keeper script change.
