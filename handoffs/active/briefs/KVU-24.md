---
schema: epyc.brief.v1
id: KVU-24
box_text_sha: 57790347afc6b09b
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/kv-cache-program.md
approach: 'Model-keyed capability records replace role-keyed NUMA/spec config. First step: record schema plus loader with
  tests, read-only alongside the role-keyed config.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KVU\-24\b' handoffs/active/kv-cache-program.md
non_goals:
- no scope beyond the box text
tier: sol
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/kv-cache-program.md: 430ad95801c442eb37544739ff60db62ed4d2965
---
