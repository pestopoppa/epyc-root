---
schema: epyc.brief.v1
id: VB-MOE-RT10-CAPTURE-LINK
box_text_sha: 9cd6691834a26e77
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/vidya/ingest_sources.py
approach: 'Write-side wiring for: integrate the prospective DS41 original-attempt capture extension of the existing MoE routing
  source. Land the source adapter/producer hook (existing carrier, claim_tuple.grade(), no new ladder; Source in ingest_sources.py
  + README row) with a synthetic-fixture test and refusal controls. Box done-when (live, operational, verified after): the
  next DS41 routing-tap capture after the hook ingests with refused=0 and the AK canary for the DS41 CPU target lists its
  EOR claim.

  '
acceptance: python3 -m pytest -q tests/vidya/test_vb_moe_rt10_capture_link_wire.py
new_tests:
- tests/vidya/test_vb_moe_rt10_capture_link_wire.py
non_goals:
- no retrospective measurement warrant
- no new grading ladder
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/vidya/ingest_sources.py: d2da53a6a45f78f20c2426ff20bb4b15cfbdad61
---
