---
schema: epyc.brief.v1
id: KVU-15b
box_text_sha: c863c940a3542fc7
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/kv-cache-program.md
approach: 'Measure cache-credit misses on the serving records. First step: script over serving records filing the miss rate.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KVU\-15b\b' handoffs/active/kv-cache-program.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/kv-cache-program.md: 430ad95801c442eb37544739ff60db62ed4d2965
---
