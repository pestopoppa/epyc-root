---
schema: epyc.brief.v1
id: E-6b
box_text_sha: 274b4654e9ff59dd
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/backends/serving_params.py
approach: 'Retest the budget cap on a NON-saturated suite (E-6 ran on gpqa_diamond_cot at ~85-90%). First step: choose the
  suite and run manifest; stop on paired result.

  '
acceptance: grep -qE '^ *- \[x\] \*\*E\-6b\b' handoffs/active/context-and-token-economy.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/backends/serving_params.py: bc1361d931cf2e226e9cbdef19e936742c112c93
---
