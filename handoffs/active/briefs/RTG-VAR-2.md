---
schema: epyc.brief.v1
id: RTG-VAR-2
box_text_sha: ea067e7303111184
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:orchestration/model_descriptors.yaml
approach: 'First concrete step for: Add a variant dimension to the model descriptor (rewritten 2026-11-09 for descriptor v3).
  Box has no done-when; acceptance is the closest check.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_rtg_var_2.py
new_tests:
- tests/unit/test_rtg_var_2.py
non_goals: []
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:orchestration/model_descriptors.yaml: 404870b26f030b01116a84aee1df7628c272a5fa
---
