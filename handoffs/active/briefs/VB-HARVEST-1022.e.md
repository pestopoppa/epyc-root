---
schema: epyc.brief.v1
id: VB-HARVEST-1022.e
box_text_sha: b048a27257e68f36
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/vidya/ingest_sources.py
approach: 'Write-side wiring for: VB-HARVEST-1022.e: no adapter yet for the following, so each needs a source row: REFINE
  2026-11-03 (ws58): KEEP only the AK-target rows (inf48-g10, inf42-g1 frontdoor rec. Land the source adapter/producer hook
  (existing carrier, claim_tuple.grade(), no new ladder; Source in ingest_sources.py + README row) with a synthetic-fixture
  test and refusal controls. Box done-when (live, operational, verified after): each listed run has a source row and its records
  project with refused=0.

  '
acceptance: python3 -m pytest -q tests/vidya/test_vb_harvest_1022_e_wire.py
new_tests:
- tests/vidya/test_vb_harvest_1022_e_wire.py
non_goals:
- no retrospective measurement warrant
- no new grading ladder
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/vidya/ingest_sources.py: d2da53a6a45f78f20c2426ff20bb4b15cfbdad61
---
