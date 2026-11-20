---
schema: epyc.brief.v1
id: RCP-W3
box_text_sha: 882151be1e6a9b71
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:scripts/analysis/reviewer_calibration_report.py
approach: 'RC-8 smoke slice: status-quo self-review in shadow over ~100-200 nearmiss-v1 rows (/mnt/raid0/llm/datasets/nearmiss-corpus-v1/).
  First step: slice selector and manifest.

  '
acceptance: grep -qE '^ *- \[x\] \*\*RCP\-W3\b' handoffs/active/eval-tower-program.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:scripts/analysis/reviewer_calibration_report.py: 78caea861e9957c173bccbf508fd2df76ce3b337
---
