---
schema: epyc.brief.v1
id: VB-EXP09-SPILL-WRITE
box_text_sha: f06765960f6489ec
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/vidya/ingest_sources.py
approach: 'Write-side wiring for: Project native EXP-09 spill-summary evaluation records through the existing measurement
  source class. Land the source adapter/producer hook (existing carrier, claim_tuple.grade(), no new ladder; Source in ingest_sources.py
  + README row) with a synthetic-fixture test and refusal controls. Box has no code-level done-when; acceptance is the closest
  check.

  '
acceptance: python3 -m pytest -q tests/vidya/test_vb_exp09_spill_write_wire.py
new_tests:
- tests/vidya/test_vb_exp09_spill_write_wire.py
non_goals:
- no retrospective measurement warrant
- no new grading ladder
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/vidya/ingest_sources.py: d2da53a6a45f78f20c2426ff20bb4b15cfbdad61
---
