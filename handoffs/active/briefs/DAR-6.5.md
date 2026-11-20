---
schema: epyc.brief.v1
id: DAR-6.5
box_text_sha: 5950f47f8a9cf773
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/bradley_terry.py
approach: 'First concrete step for: J14 in bulk-inference). Box has no done-when; acceptance is the closest check.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_dar_6_5.py
new_tests:
- tests/unit/test_dar_6_5.py
non_goals: []
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/bradley_terry.py: 80e0b5cd85fcca73e8cb27e0e8e3e98025539b9b
---
