---
schema: epyc.brief.v1
id: KVU-14
box_text_sha: 83106c666fa93d96
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/kv-cache-program.md
approach: 'Session-keyed admission hold on shared-pool servers (DESIGN; opens only if dynamic-stack-concurrency G5 finds cross-session
  eviction). First step: check G5 result, then design note.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KVU\-14\b' handoffs/active/kv-cache-program.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/kv-cache-program.md: 430ad95801c442eb37544739ff60db62ed4d2965
---
