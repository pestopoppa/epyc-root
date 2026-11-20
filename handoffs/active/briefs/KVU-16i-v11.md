---
schema: epyc.brief.v1
id: KVU-16i-v11
box_text_sha: 49f803a56154a683
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/kv-cache-program.md
approach: 'At v11 promotion re-measure :8083 runtime term on the v11 build and lower it. First step: measurement manifest,
  conditional on v11 build.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KVU\-16i\-v11\b' handoffs/active/kv-cache-program.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/kv-cache-program.md: 430ad95801c442eb37544739ff60db62ed4d2965
---
