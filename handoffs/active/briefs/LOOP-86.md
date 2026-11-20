---
schema: epyc.brief.v1
id: LOOP-86
box_text_sha: 629cd7a50c13f056
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:research/refactor-audit-2026-10/packages/wave2.json
- epyc-orchestrator:src/config/__init__.py
- epyc-orchestrator:src/runtime
approach: 'D5: config/registry/runtime consolidation (A3-03 at config/__init__.py:87,451,723 and A3-10..A3-25). Requires O3
  (LOOP-64) merged. src/runtime/*region_lock* is a live path: for A3-21 fix only the defects (closure reading the loop variable,
  cleanup-flag errors) with tests, no restructuring. Step: A3-03 with test.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit -x -q -k config
non_goals:
- no region_lock restructuring
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:research/refactor-audit-2026-10/packages/wave2.json: 69d12317bc22636855f108a0f2f3f4c906ec6d6d
    epyc-orchestrator:src/config/__init__.py: 571ee5ccf23b6a955ae9b7f7bb96a2a97e3a607b
    epyc-orchestrator:src/runtime: tree:f8bec88340d046c89f461c76c3462c4c12568fca
---
