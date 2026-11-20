---
schema: epyc.brief.v1
id: TD-1d.0
box_text_sha: 39d4be8349276047
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/typed_decisions/bench.py
approach: 'First concrete step for: OWNER/OPERATOR: re-settle the acceptance. Box has no done-when; acceptance is the closest
  check.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_td_1d_0.py
new_tests:
- tests/unit/test_td_1d_0.py
non_goals: []
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/typed_decisions/bench.py: aedccc576d4c87a6c21bad03368dbe375356cf08
---
