---
schema: epyc.brief.v1
id: HYBRID-PREFIX-REUSE
box_text_sha: 9177bd0c3f3d1e7d
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-llama:tools/server/server-context.cpp
approach: 'Make multi-turn prefix caching hit on hybrid GDN production models via prefill-only boundary checkpoint (coarse
  --checkpoint spacing, absorbing HPR-B-SIM-FIX-2). First step: the boundary-checkpoint arm in the fork build with a hit-rate
  measurement.

  '
acceptance: grep -qE '^ *- \[x\] \*\*HYBRID\-PREFIX\-REUSE\b' handoffs/active/kv-cache-program.md
non_goals:
- kernel edits only on llama.cpp-experimental, never the frozen production tree
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-llama:tools/server/server-context.cpp: 07544da91b739bcf8d83f95155841ce39e397ec4
---
