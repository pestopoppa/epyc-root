---
schema: epyc.brief.v1
id: KPF-62
box_text_sha: a394c4168c780db0
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-llama:tools/server/server-context.cpp
approach: 'Chunk-KV phase 1 attention-only core: server_chunk_store keyed by content hash, libllama range export/inject, RoPE
  shift, selector. First step: the store plus range export/inject unit tests.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KPF\-62\b' handoffs/active/kv-cache-program.md
non_goals:
- kernel edits only on llama.cpp-experimental, never the frozen production tree
tier: sol
grounded:
  at: '2026-11-20'
  blobs:
    epyc-llama:tools/server/server-context.cpp: 07544da91b739bcf8d83f95155841ce39e397ec4
---
