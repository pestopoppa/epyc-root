---
schema: epyc.brief.v1
id: HIL-20-DPL-HOLD
box_text_sha: 55ec85092c4818fa
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- docs/design/harness-improvement-loop-design-20261006.md
approach: 'Docs-only: next to the DP-L reference (line 91) record DP-L as decided HOLD; the three candidates stay report-column
  conventions, not protocol text. No done-when; acceptance is the closest check.

  '
acceptance: grep -n 'DP-L' docs/design/harness-improvement-loop-design-20261006.md | grep -i 'HOLD'
non_goals:
- no protocol text, no MEASUREMENT.md amendment
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:docs/design/harness-improvement-loop-design-20261006.md: 6b828808d2c1169b744c7854afa90e86bdcaaf9d
---
