---
schema: epyc.brief.v1
id: LOOP-88
box_text_sha: 0d5ec99488bf47b3
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:research/refactor-audit-2026-10/packages/wave2.json
- epyc-orchestrator:src/cli_orch.py
- epyc-orchestrator:src/api/routes/dashboard_topology.py
approach: 'D7: orchestrator scripts structure: src<->scripts layering, sys.path hacks, duplicated helpers (A5-03 at cli_orch.py:26,
  dashboard_topology.py:19, config/models.py:529; A5-08, A5-09, A5-13..A5-25, A5-M3). Requires O6 (LOOP-69) merged. scripts/server/orchestrator_stack.py
  is a live path: no structural edit there (LOOP-92 holds those). Step: A5-03 with an import-layering test.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit -x -q -k import
non_goals:
- no orchestrator_stack.py edit
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:research/refactor-audit-2026-10/packages/wave2.json: 69d12317bc22636855f108a0f2f3f4c906ec6d6d
    epyc-orchestrator:src/cli_orch.py: c871a1ef022a9ff86b4f43bd168449ec4c7cea55
    epyc-orchestrator:src/api/routes/dashboard_topology.py: 21ab1ff683623568d812a532e57d1298921438f7
---
