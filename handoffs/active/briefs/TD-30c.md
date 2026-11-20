---
schema: epyc.brief.v1
id: TD-30c
box_text_sha: e15b3d61f155c983
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/inf70/harness1/gate_arms.py
- epyc-root:tests/inf70/test_harness1_gate_arms.py
- epyc-root:artifacts/gpu-block-27b-20261004/runners/q38_t7.py
- epyc-orchestrator:src/classifiers/quality_detector.py
approach: 'First concrete step for: embedder-based excerpt option for the judge (operator suggestion, 2026-10-04). Box done-when:
  the option exists behind a parameter with tests, and on the TD-30b set it agrees with the labels at least as often as the
  positional excerpt, at an equal judged-token budget.

  '
acceptance: python3 -m pytest -q tests/test_td_30c.py tests/inf70/test_harness1_gate_arms.py
new_tests:
- tests/test_td_30c.py
non_goals: []
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/inf70/harness1/gate_arms.py: c9e8e7a32e21335ed7b734b8c5a7535037f729a8
    epyc-root:tests/inf70/test_harness1_gate_arms.py: a6ba21ecaca3c68c09743c019e9a350c35f5170f
    epyc-root:artifacts/gpu-block-27b-20261004/runners/q38_t7.py: 0b0406caddc014ab3de81e9c064435cc7eff8783
    epyc-orchestrator:src/classifiers/quality_detector.py: ba7db6dd1caa1c2b30746245f114a8290c010470
---
