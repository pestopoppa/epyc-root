---
schema: epyc.brief.v1
id: TD-30a
box_text_sha: 3ddbc0ccbab32013
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:tests/unit/test_coherence_judge.py
- epyc-root:scripts/inf70/harness1/gate_arms.py
- epyc-root:tests/inf70/test_harness1_gate_arms.py
- epyc-root:artifacts/tdcoh-20261109/H_A1_vs_H_B1.verdict.json
approach: 'First concrete step for: merge the champion-sidecar judge backend to orch main. Box done-when: it is merged with
  tests green, the API is reloaded, and a call log shows the backend selection recorded.

  '
acceptance: python3 -m pytest -q tests/test_td_30a.py tests/inf70/test_harness1_gate_arms.py
new_tests:
- tests/test_td_30a.py
non_goals: []
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:tests/unit/test_coherence_judge.py: c5bb5a6ecd9a2bdcabb7c6ee26da4868e162be21
    epyc-root:scripts/inf70/harness1/gate_arms.py: c9e8e7a32e21335ed7b734b8c5a7535037f729a8
    epyc-root:tests/inf70/test_harness1_gate_arms.py: a6ba21ecaca3c68c09743c019e9a350c35f5170f
    epyc-root:artifacts/tdcoh-20261109/H_A1_vs_H_B1.verdict.json: 1072183cb3e5e16c3cb1065ba485fb8b10c04a87
---
