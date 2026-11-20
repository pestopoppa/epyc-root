---
schema: epyc.brief.v1
id: HSF-4
box_text_sha: d7b61e7e35489df5
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:wiki/inference-serving.md
approach: 'Reload-vs-re-prefill crossover per lineup model: KV bytes/token and append-prefill FLOPs/token from config, GB
  per PFLOP. First step: calculator script with a unit test for one model, then all lineup models.

  '
acceptance: grep -qE '^ *- \[x\] \*\*HSF\-4\b' handoffs/active/kv-cache-program.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:wiki/inference-serving.md: cdca5e677b8d2baa45036c728930d61500c85b2f
---
