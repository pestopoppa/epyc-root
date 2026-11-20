---
schema: epyc.brief.v1
id: HSF-1
box_text_sha: 55c5035ab46c37a5
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/kv-cache-program.md
approach: 'Write a launch-phase receipt on every production GPU launch (measured swap cost C per model). First step: receipt
  writer in the GPU launcher with a unit test of the receipt schema, then verify on the next launch.

  '
acceptance: grep -qE '^ *- \[x\] \*\*HSF\-1\b' handoffs/active/kv-cache-program.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/kv-cache-program.md: 430ad95801c442eb37544739ff60db62ed4d2965
---
