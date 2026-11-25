---
schema: epyc.brief.v1
id: PM-REPLAY-RECEIPT-ENFORCE
box_text_sha: t:6badde1cfd7700b4
author: wrap-up
written: '2026-11-25'
accepted: owner
where:
- scripts/coordination/tests/test_ak_gate.py
approach: 'Find PREFLIGHT_ENFORCE replay_receipt, set enforcing, rewrite the 3 off-asserting tests to assert on, run ak_gate
  suite and replay gate

  '
acceptance: python3 -m pytest scripts/coordination/tests/test_ak_gate.py
non_goals: []
tier: local
grounded:
  at: '2026-11-25'
  blobs:
    epyc-root:scripts/coordination/tests/test_ak_gate.py: 69c0b62f85b9ea8a48797591a4ad626fce442bc8
---
