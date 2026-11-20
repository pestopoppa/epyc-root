---
schema: epyc.brief.v1
id: KPF-42
box_text_sha: 44c3a419c29610c5
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-llama:src/llama-kv-cache.cpp
approach: 'P4 gate A/B vs KVU-19b on KVU-18 cells (0/1/2/3 neighbours), 4x16k and 4x80k. First step: gate manifest.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KPF\-42\b' handoffs/active/kv-cache-program.md
non_goals:
- kernel edits only on llama.cpp-experimental, never the frozen production tree
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-llama:src/llama-kv-cache.cpp: c0715cb10a62d81ccd8b53353c071d84e27e3376
---
