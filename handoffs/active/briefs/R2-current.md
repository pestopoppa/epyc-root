---
schema: epyc.brief.v1
id: R2-current
box_text_sha: e6d66fdf2e7201fb
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/eval-tower-program.md
approach: 'Accrue a current-era trusted per-question ledger sufficient for a reproducible >=40-item core selection; do not
  use the July-3 candidate. First step: ledger-accrual checkpoint script and a selection predicate test.

  '
acceptance: grep -qE '^ *- \[x\] \*\*R2\-current\b' handoffs/active/eval-tower-program.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/eval-tower-program.md: bb00cad949830eca2617a6993062fa6973a6a1df
---
