---
schema: epyc.brief.v1
id: KVU-16h-runner
box_text_sha: 21a1dcacaab0110f
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/kv-cache-program.md
approach: 'Bench runners give n_max: 0 (no-draft) arms their own server launch. First step: runner change with a test in the
  first runner of the inventory.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KVU\-16h\-runner\b' handoffs/active/kv-cache-program.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/kv-cache-program.md: 430ad95801c442eb37544739ff60db62ed4d2965
---
