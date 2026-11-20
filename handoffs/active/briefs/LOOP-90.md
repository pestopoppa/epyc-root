---
schema: epyc.brief.v1
id: LOOP-90
box_text_sha: 5dec1638197508c2
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:research/refactor-audit-2026-10/packages/wave2.json
- epyc-orchestrator:scripts/autopilot/actions.py
approach: 'D9: autopilot remaining structure (actions.py:1563,1703,1830 etc., planner, journal, reports; B3-10..B3-25, B4-07..B4-18,
  B5-04, B5-05, B5-11 and more). Requires P1 (LOOP-68), P3 and P4 (LOOP-75) merged. Step: B3-10 with a behavioural test through
  the loop harness.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit -x -q -k actions
non_goals:
- no evaluator file edits
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:research/refactor-audit-2026-10/packages/wave2.json: 69d12317bc22636855f108a0f2f3f4c906ec6d6d
    epyc-orchestrator:scripts/autopilot/actions.py: acd36f00abd4af002157101919a0db4f9417deae
---
