---
schema: epyc.brief.v1
id: VB-KQROUTE-1
box_text_sha: b2e3376923addf4a
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/vidya/ingest_sources.py
approach: 'Write-side wiring for: write side + projection for the GPU kernel-route A/B harness. Land the source adapter/producer
  hook (existing carrier, claim_tuple.grade(), no new ladder; Source in ingest_sources.py + README row) with a synthetic-fixture
  test and refusal controls. Box done-when (live, operational, verified after): the next kernel-route or FA-routing A/B after
  the hook ingests with refused=0 and the AK canary for the 27B GPU target lists its paired claim.

  '
acceptance: python3 -m pytest -q tests/vidya/test_vb_kqroute_1_wire.py
new_tests:
- tests/vidya/test_vb_kqroute_1_wire.py
non_goals:
- no retrospective measurement warrant
- no new grading ladder
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/vidya/ingest_sources.py: d2da53a6a45f78f20c2426ff20bb4b15cfbdad61
---
