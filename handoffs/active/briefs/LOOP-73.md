---
schema: epyc.brief.v1
id: LOOP-73
box_text_sha: c5876fa925a25498
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:research/refactor-audit-2026-10/packages/wave1.json
- epyc-orchestrator:src/api/routes/dashboard.py
approach: 'O5: dashboard request-path cost and silent-empty panels (A1-04, A1-08, A1-13, A1-11, A1-21; dashboard.py:6333,
  7218, 7420, 4041, 5390, 5618). Dashboard work runs on the event loop per connected client: measure before/after for A1-04/A1-08,
  move blocking IO off the loop, make empty panels report an explicit unknown/empty-reason. Dashboard plane rule applies (/api/health
  fold).

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit -k dashboard
non_goals:
- no new dashboard pages
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:research/refactor-audit-2026-10/packages/wave1.json: bb376c30536182d94ec0a5257025cef934db2098
    epyc-orchestrator:src/api/routes/dashboard.py: 098e5c95f705b8c12517db2a1c04b9dd89910511
---
