---
schema: epyc.brief.v1
id: KVU-10
box_text_sha: 66209123a1c9f93c
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/kv-cache-program.md
approach: 'Roll -kvu to other roles in the inventory''s order. First step: next role in the inventory; launcher recipe change
  plus smoke.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KVU\-10\b' handoffs/active/kv-cache-program.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/kv-cache-program.md: 430ad95801c442eb37544739ff60db62ed4d2965
---
