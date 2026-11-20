---
schema: epyc.brief.v1
id: KVU-16g
box_text_sha: d6f80f8cb47b6961
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-llama:tools/server/server-context.cpp
approach: 'Decode-aware prefill budget on llama-server (Sarathi-style) on the experimental tree. First step: budgeter change
  with row-5c A/B manifest.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KVU\-16g\b' handoffs/active/kv-cache-program.md
non_goals:
- kernel edits only on llama.cpp-experimental, never the frozen production tree
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-llama:tools/server/server-context.cpp: 07544da91b739bcf8d83f95155841ce39e397ec4
---
