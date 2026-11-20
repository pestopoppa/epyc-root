---
schema: epyc.brief.v1
id: TB-3
box_text_sha: 48be666333822d52
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/backends/serving_params.py
approach: 'Audit production ceilings against the TB-1 knees: cross-reference each role''s live max-tokens vs knee. First step:
  audit script producing a table from registry plus curves.

  '
acceptance: grep -qE '^ *- \[x\] \*\*TB\-3\b' handoffs/active/context-and-token-economy.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/backends/serving_params.py: bc1361d931cf2e226e9cbdef19e936742c112c93
---
