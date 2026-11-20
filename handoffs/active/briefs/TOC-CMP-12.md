---
schema: epyc.brief.v1
id: TOC-CMP-12
box_text_sha: ac2108ad66a50820
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/backends/serving_params.py
approach: 'Step 3 fix: force </think> / suppress think scaffold at budget=0 for hybrid SSM; needs running server. First step:
  reproduce on current code with a unit test of thinking_budget handling.

  '
acceptance: grep -qE '^ *- \[x\] \*\*TOC\-CMP\-12\b' handoffs/active/context-and-token-economy.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/backends/serving_params.py: bc1361d931cf2e226e9cbdef19e936742c112c93
---
