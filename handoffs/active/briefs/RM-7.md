---
schema: epyc.brief.v1
id: RM-7
box_text_sha: t:16f59ae62e7ffb60
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/proactive_delegation/verifier_adapter.py
- epyc-orchestrator:src/proactive_delegation/review_service.py
approach: 'Ablation on the winning pair: reviewer with vs without verifier-request access (isolates contextual verification
  from a second-opinion effect). Paired on the same tasks, report flips and verifier-request rate. Needs RM-4''s winning pair;
  prep: the flag that disables verifier requests for an arm, tested.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_review_service_no_verifier_arm.py
new_tests:
- tests/unit/test_review_service_no_verifier_arm.py
non_goals:
- no run before a winning pair exists
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/proactive_delegation/verifier_adapter.py: 96c46c4f24925bd47a4adc6f6f2bfa70d4768ee8
    epyc-orchestrator:src/proactive_delegation/review_service.py: b80f42a995029f228c99826e68a86aefad26322b
---
