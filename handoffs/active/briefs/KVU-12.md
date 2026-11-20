---
schema: epyc.brief.v1
id: KVU-12
box_text_sha: a3a3589091f1aa70
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:/mnt/raid0/llm/tmp/cal-1025/kvu12-5-np8/VERDICT.json
approach: 'np x ctx on CPU (TB-6 successor, Flash-Next) only if needed. First step: decide need from the filed KVU-12.x results;
  if needed, one sweep manifest.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KVU\-12\b' handoffs/active/kv-cache-program.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:/mnt/raid0/llm/tmp/cal-1025/kvu12-5-np8/VERDICT.json: 9a8e1a545de598636e3b725c2688ebe88713ef62
---
