---
schema: epyc.brief.v1
id: VB-AK-R24-9-REPEAT
box_text_sha: fe44c60e5edaeb4b
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/vidya/ingest_sources.py
approach: 'Write-side wiring for: project prospectively captured same-code excursion findings through the existing AutoKernel
  experiment family. Land the source adapter/producer hook (existing carrier, claim_tuple.grade(), no new ladder; Source in
  ingest_sources.py + README row) with a synthetic-fixture test and refusal controls. Box done-when (live, operational, verified
  after): a producer-sealed same_code_excursion row projects as measurement_invalid with refused=0.

  '
acceptance: python3 -m pytest -q tests/vidya/test_vb_ak_r24_9_repeat_wire.py
new_tests:
- tests/vidya/test_vb_ak_r24_9_repeat_wire.py
non_goals:
- no retrospective measurement warrant
- no new grading ladder
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/vidya/ingest_sources.py: d2da53a6a45f78f20c2426ff20bb4b15cfbdad61
---
