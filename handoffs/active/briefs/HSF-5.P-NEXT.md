---
schema: epyc.brief.v1
id: HSF-5.P-NEXT
box_text_sha: 40f4dd8e414e9f35
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-llama:src/llama-kv-cache.cpp
approach: 'Decide the host KV mirror''s fate: attribute the +4.17% decode cost (copy/sync/scatter term, graph-safe variants)
  or retire HSF-5.P. First step: device-time attribution per term; output is a keep/retire verdict line.

  '
acceptance: grep -qE '^ *- \[x\] \*\*HSF\-5\.P\-NEXT\b' handoffs/active/kv-cache-program.md
non_goals:
- kernel edits only on llama.cpp-experimental, never the frozen production tree
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-llama:src/llama-kv-cache.cpp: c0715cb10a62d81ccd8b53353c071d84e27e3376
---
