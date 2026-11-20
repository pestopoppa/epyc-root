---
schema: epyc.brief.v1
id: TOC-CMP-11
box_text_sha: ed7ea16606278fb5
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/backends/serving_params.py
approach: 'Thread thinking_budget_tokens through ChatRequest per role (plumbing exists per 2026-11-09 audit). First step:
  confirm per-role passthrough with a unit test in serving_params.

  '
acceptance: grep -qE '^ *- \[x\] \*\*TOC\-CMP\-11\b' handoffs/active/context-and-token-economy.md
non_goals:
- no scope beyond the box text
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/backends/serving_params.py: bc1361d931cf2e226e9cbdef19e936742c112c93
---
