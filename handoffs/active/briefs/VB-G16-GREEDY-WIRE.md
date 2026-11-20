---
schema: epyc.brief.v1
id: VB-G16-GREEDY-WIRE
box_text_sha: 207aa893cfcf837a
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/vidya/ingest_sources.py
approach: 'Write-side wiring for: capture and project future native greedy chunked-versus-recurrent comparisons. Land the
  source adapter/producer hook (existing carrier, claim_tuple.grade(), no new ladder; Source in ingest_sources.py + README
  row) with a synthetic-fixture test and refusal controls. Box done-when (live, operational, verified after): the next G16/G16a
  native run ingests with refused=0 and the AK canary for its target lists the equality claim.

  '
acceptance: python3 -m pytest -q tests/vidya/test_vb_g16_greedy_wire_wire.py
new_tests:
- tests/vidya/test_vb_g16_greedy_wire_wire.py
non_goals:
- no retrospective measurement warrant
- no new grading ladder
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/vidya/ingest_sources.py: d2da53a6a45f78f20c2426ff20bb4b15cfbdad61
---
