---
schema: epyc.brief.v1
id: CFI-2
box_text_sha: 4c5af1d108ca633c
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/api/routes/chat.py
- epyc-orchestrator:src/api/routes/chat_review.py
- epyc-orchestrator:src/api/services/episodic_switch.py
approach: 'First concrete step for: decide the memory-k widening needed to reach 256-token blocks on the episodic path. Box
  has no done-when; acceptance is the closest check.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_cfi_2.py
new_tests:
- tests/unit/test_cfi_2.py
non_goals: []
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/api/routes/chat.py: f5b585c6c630d4001b279ea37be22e908fe3b54f
    epyc-orchestrator:src/api/routes/chat_review.py: fc8495c0bb75d9c0ed13f453581efbc6b4fd72e0
    epyc-orchestrator:src/api/services/episodic_switch.py: 04df22fa3d8f339962946a50bd4090c56a8bed9e
---
