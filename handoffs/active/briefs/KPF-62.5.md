---
schema: epyc.brief.v1
id: KPF-62.5
box_text_sha: 1bb439eaba896533
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-llama:tools/server/server-context.cpp
approach: 'Server wiring: --chunk-store-mib (0=off), kv_chunks request field, isolated-encode on miss, startup self-check
  logged, prompt.approx=true. First step: flag and request field parsing with a test.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KPF\-62\.5\b' handoffs/active/kv-cache-program.md
non_goals:
- kernel edits only on llama.cpp-experimental, never the frozen production tree
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-llama:tools/server/server-context.cpp: 07544da91b739bcf8d83f95155841ce39e397ec4
---
