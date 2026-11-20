---
schema: epyc.brief.v1
id: HG-2
box_text_sha: t:3569a58a54909ecd
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/proactive_delegation/policy_reducer.py
- epyc-orchestrator:src/proactive_delegation/verifier_adapter.py
- epyc-orchestrator:src/proactive_delegation/escalation_sink.py
approach: 'Verifier-disagreement rule: reviewer vs a CONCLUSIVE gate conflict escalates (fa/fr_candidate events already fire
  mechanically per H3 RD-3); conflicts with an INCONCLUSIVE gate stay with the reviewer. Encode as a pure function in policy_reducer.py
  with a truth-table unit test (reviewer verdict x gate state x conclusive flag).

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_policy_reducer_disagreement.py
new_tests:
- tests/unit/test_policy_reducer_disagreement.py
non_goals:
- no enforce flip
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/proactive_delegation/policy_reducer.py: ef0244aaf50936ee3d3dcedcdede90afdb77370c
    epyc-orchestrator:src/proactive_delegation/verifier_adapter.py: 96c46c4f24925bd47a4adc6f6f2bfa70d4768ee8
    epyc-orchestrator:src/proactive_delegation/escalation_sink.py: 202ce44ef9bde80c984fb3ffdbe6096ac60c7a58
---
