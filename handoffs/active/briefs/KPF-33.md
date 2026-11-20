---
schema: epyc.brief.v1
id: KPF-33
box_text_sha: f871960d1a1d4ada
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-llama:src/llama-kv-cache.cpp
approach: 'P3 gate for KPF-30/32: A/B vs baseline allocator on stated cells. First step: gate manifest; stop on filed verdict.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KPF\-33\b' handoffs/active/kv-cache-program.md
non_goals:
- kernel edits only on llama.cpp-experimental, never the frozen production tree
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-llama:src/llama-kv-cache.cpp: c0715cb10a62d81ccd8b53353c071d84e27e3376
---
