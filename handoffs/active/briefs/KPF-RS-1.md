---
schema: epyc.brief.v1
id: KPF-RS-1
box_text_sha: 7aebcdba8735239f
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-llama:tools/server/server-context.cpp
approach: 'Recurrent-state hash conformance after checkpoint restore and fork: seven complete source-bound impacts first (model-free).
  First step: impact scan over the seven items.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KPF\-RS\-1\b' handoffs/active/kv-cache-program.md
non_goals:
- kernel edits only on llama.cpp-experimental, never the frozen production tree
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-llama:tools/server/server-context.cpp: 07544da91b739bcf8d83f95155841ce39e397ec4
---
