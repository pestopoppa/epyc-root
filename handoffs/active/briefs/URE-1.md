---
schema: epyc.brief.v1
id: URE-1
box_text_sha: 18b10be612d6d10d
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/uncertainty_shadow.py
approach: 'First concrete step for: Uncertainty-quantified escalation signal. Box has no done-when; acceptance is the closest
  check.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_ure_1.py
new_tests:
- tests/unit/test_ure_1.py
non_goals: []
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/uncertainty_shadow.py: 0ad41c8eaebc137ec07128359ba5bdfbdaca7e9b
---
