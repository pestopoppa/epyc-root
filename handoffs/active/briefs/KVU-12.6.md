---
schema: epyc.brief.v1
id: KVU-12.6
box_text_sha: 9590758d96891678
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/kv-cache-program.md
approach: 'Explain the np8 L64k decode collapse (26.71 to 10.18 tok/s): np8 L48k cell and np4 equal-token cell, separate pool
  occupancy from np/L. First step: two-cell manifest.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KVU\-12\.6\b' handoffs/active/kv-cache-program.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/kv-cache-program.md: 430ad95801c442eb37544739ff60db62ed4d2965
---
