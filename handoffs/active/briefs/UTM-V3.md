---
schema: epyc.brief.v1
id: UTM-V3
box_text_sha: bec55a4708faaa25
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/user_modeling/tools.py
- epyc-orchestrator:src/user_modeling/__init__.py
- epyc-orchestrator:src/user_modeling/write_audit.py
approach: 'First concrete step for: Separate structural and semantic verification and calibrate both. Box has no done-when;
  acceptance is the closest check.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_utm_v3.py
new_tests:
- tests/unit/test_utm_v3.py
non_goals: []
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/user_modeling/tools.py: 9ee6d0604a498501e00a5b4523d46bff2e154bb0
    epyc-orchestrator:src/user_modeling/__init__.py: 94aa6822f31f8c6847fb293d996c5ee67533b192
    epyc-orchestrator:src/user_modeling/write_audit.py: 4d01a3527edc3819e0c4e61b19352553f51fb549
---
