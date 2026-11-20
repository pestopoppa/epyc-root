---
schema: epyc.brief.v1
id: LOOP-92
box_text_sha: f89f0bf9c5ec15b8
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:research/refactor-audit-2026-10/packages/wave1.json
- epyc-orchestrator:scripts/server/orchestrator_stack.py
approach: 'Restructure scripts/server/orchestrator_stack.py (A5-10, A5-16, A5-17, A5-19); blocked while it is a live path
  on the host (workspace-58, 2026-10-24); run only when the file is quiet. Step: check quietness (no running orchestrator_stack.py
  process by a captured PID view, last-commit age), then implement the ready plans with the stack tests green. Never kill
  processes.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_orchestrator_stack_import_is_argv_safe.py
non_goals:
- no edit while the stack is live
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:research/refactor-audit-2026-10/packages/wave1.json: bb376c30536182d94ec0a5257025cef934db2098
    epyc-orchestrator:scripts/server/orchestrator_stack.py: a2e1f4ba481e9b9068ec80b7ae4e829884932a8c
---
