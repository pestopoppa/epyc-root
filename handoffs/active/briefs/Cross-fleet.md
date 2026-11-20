---
schema: epyc.brief.v1
id: Cross-fleet
box_text_sha: 93f0802d2aa62ade
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/eval-tower-program.md
approach: 'Implement arm-parallelism for rebaselines (operator-endorsed 2026-07-23; trigger-gated). First step: scheduler
  change running independent arms on disjoint quarters, with a unit test of arm packing.

  '
acceptance: grep -qE '^ *- \[x\] \*\*Cross\-fleet\b' handoffs/active/eval-tower-program.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/eval-tower-program.md: bb00cad949830eca2617a6993062fa6973a6a1df
---
