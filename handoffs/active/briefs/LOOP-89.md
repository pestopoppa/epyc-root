---
schema: epyc.brief.v1
id: LOOP-89
box_text_sha: 68ff0999edc45c35
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:research/refactor-audit-2026-10/packages/wave2.json
- epyc-orchestrator:tests/conftest.py
approach: 'D8: orchestrator test-suite consolidation (A6-10 at tests/conftest.py:117,156,178,199 plus A6-05..A6-20, B5-18).
  Runs LAST among orchestrator packages (touches many test files). Step: confirm all other orchestrator packages are merged,
  then consolidate conftest fixtures one finding per commit with the full suite green.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit --collect-only -q
non_goals:
- no start before the other orchestrator packages merge
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:research/refactor-audit-2026-10/packages/wave2.json: 69d12317bc22636855f108a0f2f3f4c906ec6d6d
    epyc-orchestrator:tests/conftest.py: 42d3a8eb67e62164dfa23cd1772470680315aff0
---
