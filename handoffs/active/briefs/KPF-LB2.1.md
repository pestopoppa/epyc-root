---
schema: epyc.brief.v1
id: KPF-LB2.1
box_text_sha: 0ceb5bcb40c0937b
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/kv-cache-program.md
approach: 'Exercise the opencode V2 (session_message) reader on real rows once a migrated row exists; V2 path is currently
  fixture-tested only. First step: check the live DB for V2 rows and run the reader against them.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KPF\-LB2\.1\b' handoffs/active/kv-cache-program.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/kv-cache-program.md: 430ad95801c442eb37544739ff60db62ed4d2965
---
