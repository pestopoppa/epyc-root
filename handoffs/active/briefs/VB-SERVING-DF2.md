---
schema: epyc.brief.v1
id: VB-SERVING-DF2
box_text_sha: 177cfc5e417ab22c
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/vidya/ingest_sources.py
approach: 'Write-side wiring for: wire the write side for three new serving measurement sources. Land the source adapter/producer
  hook (existing carrier, claim_tuple.grade(), no new ladder; Source in ingest_sources.py + README row) with a synthetic-fixture
  test and refusal controls. Box done-when (live, operational, verified after): the next DF2/ngram parity or acceptance run
  after the hook ingests with refused=0 and the AutoPilot canary for the frontdoor role (or the AK canary for the 27B GPU
  target) lists its acceptance claim.

  '
acceptance: python3 -m pytest -q tests/vidya/test_vb_serving_df2_wire.py
new_tests:
- tests/vidya/test_vb_serving_df2_wire.py
non_goals:
- no retrospective measurement warrant
- no new grading ladder
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/vidya/ingest_sources.py: d2da53a6a45f78f20c2426ff20bb4b15cfbdad61
---
