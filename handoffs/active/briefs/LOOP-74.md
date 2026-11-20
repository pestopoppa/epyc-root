---
schema: epyc.brief.v1
id: LOOP-74
box_text_sha: e0170935560d89f7
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:research/refactor-audit-2026-10/packages/wave1.json
- epyc-orchestrator:scripts/autopilot/experiment_journal.py
- epyc-orchestrator:tests/conftest.py
approach: 'O7 rest: A6-M1 (experiment_journal.py:1123, trace emit/store: runtime stores must be isolated in tests), A6-03
  (tests/conftest.py:40,43,96), A6-12, A6-11, A6-17; A6-13 belongs to O8 only. Requires LOOP-66 merged. Step: isolate the
  runtime stores per test with a fixture, then one finding per commit with test.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit -x -q -k journal
non_goals:
- no CI workflow
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:research/refactor-audit-2026-10/packages/wave1.json: bb376c30536182d94ec0a5257025cef934db2098
    epyc-orchestrator:scripts/autopilot/experiment_journal.py: f988ab5fa34a7fce411525996a861dfd1369c88f
    epyc-orchestrator:tests/conftest.py: 42d3a8eb67e62164dfa23cd1772470680315aff0
---
