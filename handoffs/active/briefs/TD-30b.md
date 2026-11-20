---
schema: epyc.brief.v1
id: TD-30b
box_text_sha: c5e987569de60e3d
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/inf70/harness1/gate_arms.py
- epyc-root:tests/inf70/test_harness1_gate_arms.py
- epyc-root:artifacts/gpu-block-27b-20261004/runners/q38_t7.py
- epyc-root:artifacts/tdcoh-20261109/H_A1_vs_H_B1.verdict.json
approach: 'First concrete step for: calibrate the judge. Box done-when: each backend has a sealed calibration row (`calibration_id`,
  agreement on the seeded labels, backend, build, scoring), and the uncalibrated refusal lifts only for those backends.

  '
acceptance: python3 -m pytest -q tests/test_td_30b.py tests/inf70/test_harness1_gate_arms.py
new_tests:
- tests/test_td_30b.py
non_goals: []
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/inf70/harness1/gate_arms.py: c9e8e7a32e21335ed7b734b8c5a7535037f729a8
    epyc-root:tests/inf70/test_harness1_gate_arms.py: a6ba21ecaca3c68c09743c019e9a350c35f5170f
    epyc-root:artifacts/gpu-block-27b-20261004/runners/q38_t7.py: 0b0406caddc014ab3de81e9c064435cc7eff8783
    epyc-root:artifacts/tdcoh-20261109/H_A1_vs_H_B1.verdict.json: 1072183cb3e5e16c3cb1065ba485fb8b10c04a87
---
