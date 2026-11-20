---
schema: epyc.brief.v1
id: VB-AK-PM12-LESSON
box_text_sha: 8c1a2135dca1b534
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/vidya/ingest_sources.py
approach: 'Write-side wiring for: strictly project future AutoKernel lesson-admission receipts through the existing journal
  family. Land the source adapter/producer hook (existing carrier, claim_tuple.grade(), no new ladder; Source in ingest_sources.py
  + README row) with a synthetic-fixture test and refusal controls. Box done-when (live, operational, verified after): the
  first producer-authored lesson-admission receipt projects informationally with refused=0.

  '
acceptance: python3 -m pytest -q tests/vidya/test_vb_ak_pm12_lesson_wire.py
new_tests:
- tests/vidya/test_vb_ak_pm12_lesson_wire.py
non_goals:
- no retrospective measurement warrant
- no new grading ladder
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/vidya/ingest_sources.py: d2da53a6a45f78f20c2426ff20bb4b15cfbdad61
---
