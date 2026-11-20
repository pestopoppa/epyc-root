---
schema: epyc.brief.v1
id: KPF-61
box_text_sha: 3ad2cc1ed967046a
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-llama:tools/server/server-context.cpp
approach: 'Chunk-KV phase 1a: reorder planner, exact and hybrid-safe (min run 16, last tokens pinned). First step: planner
  module with unit tests.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KPF\-61\b' handoffs/active/kv-cache-program.md
non_goals:
- kernel edits only on llama.cpp-experimental, never the frozen production tree
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-llama:tools/server/server-context.cpp: 07544da91b739bcf8d83f95155841ce39e397ec4
---
