---
schema: epyc.brief.v1
id: KPF-32
box_text_sha: fab07a576aa4a742
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-llama:src/llama-kv-cache.cpp
approach: 'Affine allocator in find_slot (llama-kv-cache.cpp:901-1075): per-sequence cursor. First step: cursor prototype
  on the experimental tree with the existing kv-cache unit tests green.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KPF\-32\b' handoffs/active/kv-cache-program.md
non_goals:
- kernel edits only on llama.cpp-experimental, never the frozen production tree
tier: sol
grounded:
  at: '2026-11-20'
  blobs:
    epyc-llama:src/llama-kv-cache.cpp: c0715cb10a62d81ccd8b53353c071d84e27e3376
---
