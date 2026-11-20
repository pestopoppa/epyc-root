---
schema: epyc.brief.v1
id: TB-6
box_text_sha: f7cedf6d249c24d8
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/backends/serving_params.py
approach: 'Concurrency-aware admission control (VRAM and bandwidth guard) in the router/orchestrator. First step: admission
  predicate with unit tests over np x budget surface inputs.

  '
acceptance: grep -qE '^ *- \[x\] \*\*TB\-6\b' handoffs/active/context-and-token-economy.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/backends/serving_params.py: bc1361d931cf2e226e9cbdef19e936742c112c93
---
