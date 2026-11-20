---
schema: epyc.brief.v1
id: VB-HARVEST-1022.a
box_text_sha: 214c785e64f69f38
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/vidya/ingest_sources.py
approach: 'Write-side wiring for: VB-HARVEST-1022.a: the llama-bench ABA timing source should project the v11-050/051/052
  GPU HOLDs, q38fn armP/armP2 speed, hsf-5p-microbench, c5-gate-b (sign-only, indica. Land the source adapter/producer hook
  (existing carrier, claim_tuple.grade(), no new ladder; Source in ingest_sources.py + README row) with a synthetic-fixture
  test and refusal controls. Box done-when (live, operational, verified after): an llama-bench A/B/A timing source projects
  the listed runs with refused=0 and the AK canary for the 27B GPU target lists one v11 HOLD claim.

  '
acceptance: python3 -m pytest -q tests/vidya/test_vb_harvest_1022_a_wire.py
new_tests:
- tests/vidya/test_vb_harvest_1022_a_wire.py
non_goals:
- no retrospective measurement warrant
- no new grading ladder
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/vidya/ingest_sources.py: d2da53a6a45f78f20c2426ff20bb4b15cfbdad61
---
