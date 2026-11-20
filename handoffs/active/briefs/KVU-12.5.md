---
schema: epyc.brief.v1
id: KVU-12.5
box_text_sha: 2331f71ebdc77d5e
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:/mnt/raid0/llm/tmp/cal-1025/kvu12-5-np8/VERDICT.json
approach: 'File a clean np8 L64k unified vs split pair on one CPU quarter, GPU idle on both arms (operator decision 2026-10-25).
  First step: pair manifest.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KVU\-12\.5\b' handoffs/active/kv-cache-program.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:/mnt/raid0/llm/tmp/cal-1025/kvu12-5-np8/VERDICT.json: 9a8e1a545de598636e3b725c2688ebe88713ef62
---
