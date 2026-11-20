---
schema: epyc.brief.v1
id: URE-2
box_text_sha: 2e9b8b42de67179f
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/trace/__init__.py
- epyc-orchestrator:src/uncertainty_shadow.py
- epyc-orchestrator:src/trace/harness_schema.py
approach: 'First concrete step for: Approval/escalation as harness state. Box has no done-when; acceptance is the closest
  check.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_ure_2.py
new_tests:
- tests/unit/test_ure_2.py
non_goals: []
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/trace/__init__.py: f9fb74bf13949fa82819a5c423d678dda9bfa518
    epyc-orchestrator:src/uncertainty_shadow.py: 0ad41c8eaebc137ec07128359ba5bdfbdaca7e9b
    epyc-orchestrator:src/trace/harness_schema.py: 74a4c434ab19bab67d779f45cc7e32f197e7db1a
---
