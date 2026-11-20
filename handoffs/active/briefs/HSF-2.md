---
schema: epyc.brief.v1
id: HSF-2
box_text_sha: b13d39a2280fcf32
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:scripts/server/orchestrator_stack.py::_build_role_command
approach: 'Add --metrics to the CPU llama-server argv in the main role builder (today only the GPU shadow lane builder at
  ~1355 emits it). Ship only inside the next signed stack-change package, never an ad-hoc relaunch.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_cpu_role_command_metrics.py
new_tests:
- tests/unit/test_cpu_role_command_metrics.py
non_goals:
- no live relaunch of any server
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:scripts/server/orchestrator_stack.py: a2e1f4ba481e9b9068ec80b7ae4e829884932a8c
---
