---
schema: epyc.brief.v1
id: SC14-B
box_text_sha: 56fadddf56c1d256
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/vidya/ingest_sources.py
approach: 'Write-side wiring for: no promotion has occurred since filing (v9 freeze) and the pre-promotion journal ordering
  still lacks the durable current-trial attestation (confirmed absent in the orche. Land the source adapter/producer hook
  (existing carrier, claim_tuple.grade(), no new ladder; Source in ingest_sources.py + README row) with a synthetic-fixture
  test and refusal controls. Box done-when (live, operational, verified after): the pre-promotion journal ordering carries
  a durable current-trial attestation and `gate.evaluate` gates the first CANDIDATE → BASELINE promotion after the AutoPilot
  spin-up (VB-AP-FIRST-CYCLE).

  '
acceptance: python3 -m pytest -q tests/vidya/test_sc14_b_wire.py
new_tests:
- tests/vidya/test_sc14_b_wire.py
non_goals:
- no retrospective measurement warrant
- no new grading ladder
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/vidya/ingest_sources.py: d2da53a6a45f78f20c2426ff20bb4b15cfbdad61
---
