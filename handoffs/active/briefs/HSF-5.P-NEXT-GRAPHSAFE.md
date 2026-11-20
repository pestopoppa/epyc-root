---
schema: epyc.brief.v1
id: HSF-5.P-NEXT-GRAPHSAFE
box_text_sha: c598b4ffb04a61f2
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-llama:src/llama-kv-cache.cpp
approach: 'Prototype graph-safe host-KV mirror copy variants that keep graphs reused and cut the copy term (+5.2% at 93260118d).
  First step: first variant built on the experimental tree and measured.

  '
acceptance: grep -qE '^ *- \[x\] \*\*HSF\-5\.P\-NEXT\-GRAPHSAFE\b' handoffs/active/kv-cache-program.md
non_goals:
- kernel edits only on llama.cpp-experimental, never the frozen production tree
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-llama:src/llama-kv-cache.cpp: c0715cb10a62d81ccd8b53353c071d84e27e3376
---
