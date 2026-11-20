---
schema: epyc.brief.v1
id: TB-6-ROUTER
box_text_sha: 7ca9537cdfc01e6e
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/backends/serving_params.py
approach: 'Wire the np x budget surface into the router (gate met 2026-11-09). First step: surface loader plus router hook
  behind a default-off flag, with a test.

  '
acceptance: grep -qE '^ *- \[x\] \*\*TB\-6\-ROUTER\b' handoffs/active/context-and-token-economy.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/backends/serving_params.py: bc1361d931cf2e226e9cbdef19e936742c112c93
---
