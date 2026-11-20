---
schema: epyc.brief.v1
id: UFH14-A4a
box_text_sha: 2649751da234a4b2
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:docs/reports/ufh14-a4a-split-task-20261104/proxy3.patch
- epyc-root:docs/reports/ufh14-a4a-split-task-20261104/replay_controls.py
- epyc-root:docs/reports/ufh14-a4a-split-task-20261104/README.md
approach: 'Root cause found: the restoration matcher in the C95 harness proxy3.py requires a single content part but the recorded
  truncated task has three input_text parts (prefix, marker, suffix). proxy3.patch widens it to len in (1,3) with exact-match
  refusals; 11+12 offline controls passed. Step: apply the patch to the maintained proxy3.py (path in source-hashes.json),
  rerun replay_controls.py, then rerun the paired 27B C4 run (treatment must finish within 2700 s) and report cache_n/prompt_n/prompt_s
  per arm, descriptive only.

  '
acceptance: python3 -I docs/reports/ufh14-a4a-split-task-20261104/replay_controls.py
non_goals:
- no keep verdict
- no cache-performance claim before the paired run
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:docs/reports/ufh14-a4a-split-task-20261104/proxy3.patch: 2e8ea308c3c3c2de7add7f5980e5a6f1cfd21361
    epyc-root:docs/reports/ufh14-a4a-split-task-20261104/replay_controls.py: e2bacd26f34ae7abdcc1b80d2605b3da631ea584
    epyc-root:docs/reports/ufh14-a4a-split-task-20261104/README.md: 45e425b1f5d418724c680ad4f0fc1b1d196f6ad5
---
