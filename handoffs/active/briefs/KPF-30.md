---
schema: epyc.brief.v1
id: KPF-30
box_text_sha: 3f68a392a5d87fda
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-llama:src/llama-kv-cache.cpp
approach: 'Measure the mixed-block fraction with a debug counter in KVU-19a''s block-liveness scan kernel. First step: counter
  patch on the experimental tree and one measurement.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KPF\-30\b' handoffs/active/kv-cache-program.md
non_goals:
- kernel edits only on llama.cpp-experimental, never the frozen production tree
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-llama:src/llama-kv-cache.cpp: c0715cb10a62d81ccd8b53353c071d84e27e3376
---
