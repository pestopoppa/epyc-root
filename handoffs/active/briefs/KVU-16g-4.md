---
schema: epyc.brief.v1
id: KVU-16g-4
box_text_sha: a21630aafc0a0d23
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-llama:tools/server/server-context.cpp
approach: 'Operator decided 2026-11-06: fix the p99 iteration overshoot in the budgeter, then rerun the chosen arm. First
  step: budgeter fix on the experimental tree with a unit test.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KVU\-16g\-4\b' handoffs/active/kv-cache-program.md
non_goals:
- kernel edits only on llama.cpp-experimental, never the frozen production tree
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-llama:tools/server/server-context.cpp: 07544da91b739bcf8d83f95155841ce39e397ec4
---
