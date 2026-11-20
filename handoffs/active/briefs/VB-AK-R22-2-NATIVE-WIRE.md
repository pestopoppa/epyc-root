---
schema: epyc.brief.v1
id: VB-AK-R22-2-NATIVE-WIRE
box_text_sha: 7291fb4557b58512
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/vidya/ingest_sources.py
approach: 'Write-side wiring for: Bind future R22-2 native batched decode calibration records at write/finalize to actual
  model/quant, source, executable, loaded libraries, argv, grant, parallel shape and. Land the source adapter/producer hook
  (existing carrier, claim_tuple.grade(), no new ladder; Source in ingest_sources.py + README row) with a synthetic-fixture
  test and refusal controls. Box done-when (live, operational, verified after): the first post-hook batched-decode calibration
  ingests with refused=0 and the AK canary for the 27B GPU target lists the settled floor.

  '
acceptance: python3 -m pytest -q tests/vidya/test_vb_ak_r22_2_native_wire_wire.py
new_tests:
- tests/vidya/test_vb_ak_r22_2_native_wire_wire.py
non_goals:
- no retrospective measurement warrant
- no new grading ladder
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/vidya/ingest_sources.py: d2da53a6a45f78f20c2426ff20bb4b15cfbdad61
---
