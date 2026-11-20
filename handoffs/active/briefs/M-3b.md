---
schema: epyc.brief.v1
id: M-3b
box_text_sha: a8dee99bca01d116
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/kv-cache-program.md
approach: 'Resolve depth 4 vs 8 at production context by accruing organic depth-4 traffic (~175). First step: watcher on the
  traffic count and the analysis script.

  '
acceptance: grep -qE '^ *- \[x\] \*\*M\-3b\b' handoffs/active/kv-cache-program.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/kv-cache-program.md: 430ad95801c442eb37544739ff60db62ed4d2965
---
