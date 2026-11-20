---
schema: epyc.brief.v1
id: KPF-62.4
box_text_sha: d1eaaeee4b305d80
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-llama:tools/server/server-context.cpp
approach: 'Sparse recompute by explicit-position batches beside the cache-reuse block; G0 at r=100% bit-identical. First step:
  explicit-position batch path with a G0 bit-identity test.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KPF\-62\.4\b' handoffs/active/kv-cache-program.md
non_goals:
- kernel edits only on llama.cpp-experimental, never the frozen production tree
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-llama:tools/server/server-context.cpp: 07544da91b739bcf8d83f95155841ce39e397ec4
---
