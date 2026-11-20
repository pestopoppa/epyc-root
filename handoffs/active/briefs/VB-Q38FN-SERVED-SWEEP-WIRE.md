---
schema: epyc.brief.v1
id: VB-Q38FN-SERVED-SWEEP-WIRE
box_text_sha: 30d22f5513c5bb53
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/vidya/ingest_sources.py
approach: 'Write-side wiring for: wire the manual served thread x depth sweep records as a belief-kernel source. Land the
  source adapter/producer hook (existing carrier, claim_tuple.grade(), no new ladder; Source in ingest_sources.py + README
  row) with a synthetic-fixture test and refusal controls. Box done-when (live, operational, verified after): the next Q38FN
  served sweep or transfer A/B after the hook ingests with refused=0 and the AK canary for the Q38FN CPU target lists its
  rate claim.

  '
acceptance: python3 -m pytest -q tests/vidya/test_vb_q38fn_served_sweep_wire_wire.py
new_tests:
- tests/vidya/test_vb_q38fn_served_sweep_wire_wire.py
non_goals:
- no retrospective measurement warrant
- no new grading ladder
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/vidya/ingest_sources.py: d2da53a6a45f78f20c2426ff20bb4b15cfbdad61
---
