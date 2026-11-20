---
schema: epyc.brief.v1
id: KVU-7
box_text_sha: 1faf02f9b2f04c6e
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-llama:tools/server/server-context.cpp
approach: 'MTP pool-full exception as a v11 experimental-kernel candidate at ffc1bac82. First step: patch on experimental
  tree with a pool-full test.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KVU\-7\b' handoffs/active/kv-cache-program.md
non_goals:
- kernel edits only on llama.cpp-experimental, never the frozen production tree
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-llama:tools/server/server-context.cpp: 07544da91b739bcf8d83f95155841ce39e397ec4
---
