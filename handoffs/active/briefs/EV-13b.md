---
schema: epyc.brief.v1
id: EV-13b
box_text_sha: de2b5fa6196964eb
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:data/review_f1/SEMANTIC_MATCHER_SPEC.md
approach: 'Run leg for EV-13: Augment-v1 145-bug set plus PR set per box; semantic matcher rides the run leg. First step:
  batch-manifest entry.

  '
acceptance: grep -qE '^ *- \[x\] \*\*EV\-13b\b' handoffs/active/eval-tower-program.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:data/review_f1/SEMANTIC_MATCHER_SPEC.md: a1c31d0d1b1de50c5dd659c13c01bc20dd12c9cd
---
