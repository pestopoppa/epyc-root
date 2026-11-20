---
schema: epyc.brief.v1
id: KVU-12.4
box_text_sha: 0b874e7596c26b19
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/kv-cache-program.md
approach: 'Re-run decision: one more ABA with a tighter anchor floor, or accept NO_DIFFERENCE (~23% unified-decode gap inside
  a 12% floor). First step: record the accept-NO_DIFFERENCE verdict line unless a decision needs the gap.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KVU\-12\.4\b' handoffs/active/kv-cache-program.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/kv-cache-program.md: 430ad95801c442eb37544739ff60db62ed4d2965
---
