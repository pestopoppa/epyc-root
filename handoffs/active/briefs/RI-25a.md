---
schema: epyc.brief.v1
id: RI-25a
box_text_sha: 03a6bb2505acd8da
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:scripts/validate/stack_change_guard.py
- epyc-orchestrator:src/graph/session_log.py
- epyc-orchestrator:src/graph/langgraph/nodes.py
approach: 'First concrete step for: capture replayable delegation records. Box has no done-when; acceptance is the closest
  check.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_ri_25a.py
new_tests:
- tests/unit/test_ri_25a.py
non_goals: []
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:scripts/validate/stack_change_guard.py: 977bb7c97a125ccbd159e98cf621306d6e4933eb
    epyc-orchestrator:src/graph/session_log.py: 41b42f0581971def4e8388e3ac29abf759ab2574
    epyc-orchestrator:src/graph/langgraph/nodes.py: 36971766989136a6e71d8249af2e505598dbfb36
---
