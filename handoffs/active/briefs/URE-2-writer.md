---
schema: epyc.brief.v1
id: URE-2-writer
box_text_sha: 17fdfb8bbce5a290
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/api/routes/v1_escalation.py
- epyc-orchestrator:src/api/routes/openai_compat.py
- epyc-orchestrator:src/api/models/openai.py
approach: 'First concrete step for: live writer for non-shadow escalations plus the EXM-3 link. Box has no done-when; acceptance
  is the closest check.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_ure_2_writer.py
new_tests:
- tests/unit/test_ure_2_writer.py
non_goals: []
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/api/routes/v1_escalation.py: 5d190615b72b59e896e5385b67f0e4c6476008e7
    epyc-orchestrator:src/api/routes/openai_compat.py: f83a4473bda2e3e0b064f2fbe373e1755069c4b3
    epyc-orchestrator:src/api/models/openai.py: 13841f37fbdef376972d16e9e8d8206b0c50ed52
---
