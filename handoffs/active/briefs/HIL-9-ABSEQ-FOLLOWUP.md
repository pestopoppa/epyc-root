---
schema: epyc.brief.v1
id: HIL-9-ABSEQ-FOLLOWUP
box_text_sha: 86c1f9949f5c36eb
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- docs/design/harness-improvement-loop-design-20261006.md
approach: 'Docs-only: add a line to the HIL-2 pre-first-suite-run checklist (section at line 52) recording HIL-9 item 11 as
  resolved, no-amendment; state P-AB-1 stays fixed-N. Box has no runnable done-when; acceptance is the closest check.

  '
acceptance: grep -n 'item 11' docs/design/harness-improvement-loop-design-20261006.md | grep -i 'no-amendment'
non_goals:
- no protocol or MEASUREMENT.md change
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:docs/design/harness-improvement-loop-design-20261006.md: 6b828808d2c1169b744c7854afa90e86bdcaaf9d
---
