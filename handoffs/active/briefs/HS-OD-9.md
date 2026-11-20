---
schema: epyc.brief.v1
id: HS-OD-9
box_text_sha: d5058f4086029c5c
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/api/routes/chat.py
approach: 'Replace constant Retry-After (5/10 in api/__init__.py ~L367-421, 30 in routes/chat.py) with expected_wait_s from
  the single DAR-LAT-1 admission-ledger estimator; hold when estimate fits budget, else 503 with Retry-After=ceil(s) plus
  retry-after-ms and retry_after_basis outside epyc.failure_provenance.v1; one VB-V1-BACKPRESSURE receipt per bounce. Blocked
  on HS-OD-8 and DAR-LAT-1 landing; line anchors drifted.

  '
acceptance: pytest tests/unit/test_backpressure_derived_delay.py
new_tests:
- tests/unit/test_backpressure_derived_delay.py
non_goals:
- no second occupancy model
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/api/routes/chat.py: f5b585c6c630d4001b279ea37be22e908fe3b54f
---
