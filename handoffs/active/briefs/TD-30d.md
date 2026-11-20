---
schema: epyc.brief.v1
id: TD-30d
box_text_sha: 1cd578002f3c0c72
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/inf70/harness1/gate_arms.py
- epyc-root:tests/inf70/test_harness1_gate_arms.py
- epyc-root:artifacts/gpu-block-27b-20261004/runners/q38_t7.py
- epyc-orchestrator:src/classifiers/quality_detector.py
approach: 'First concrete step for: migrate the coherence consumers. Box done-when: items 1 and 2 produce `epyc.coherence_gate.v1`
  verdicts and items 3–5 are each recorded as done or not-needed.

  '
acceptance: python3 -m pytest -q tests/test_td_30d.py tests/inf70/test_harness1_gate_arms.py
new_tests:
- tests/test_td_30d.py
non_goals: []
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/inf70/harness1/gate_arms.py: c9e8e7a32e21335ed7b734b8c5a7535037f729a8
    epyc-root:tests/inf70/test_harness1_gate_arms.py: a6ba21ecaca3c68c09743c019e9a350c35f5170f
    epyc-root:artifacts/gpu-block-27b-20261004/runners/q38_t7.py: 0b0406caddc014ab3de81e9c064435cc7eff8783
    epyc-orchestrator:src/classifiers/quality_detector.py: ba7db6dd1caa1c2b30746245f114a8290c010470
---
