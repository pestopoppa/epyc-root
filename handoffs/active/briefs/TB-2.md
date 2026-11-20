---
schema: epyc.brief.v1
id: TB-2
box_text_sha: cb6c9c3016f6d1a4
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/backends/serving_params.py
approach: 'Test whether one mostly-ok budget captures >=90% of each model''s curve. First step: analysis script over TB-1
  curves with a fixture test; no new inference.

  '
acceptance: grep -qE '^ *- \[x\] \*\*TB\-2\b' handoffs/active/context-and-token-economy.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/backends/serving_params.py: bc1361d931cf2e226e9cbdef19e936742c112c93
---
