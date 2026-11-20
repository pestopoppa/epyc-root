---
schema: epyc.brief.v1
id: VB-SR8-DRAFT-ACCEPTANCE-WIRE
box_text_sha: 2fe584629e3ca78c
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:docs/reports/sr8-edit-spec/native_worker.py
- epyc-root:scripts/vidya/ingest_sources.py
approach: 'Write-side wiring for: project the SR-8 native edit-speculation writer through the existing SC50 draft-acceptance
  class. Land the source adapter/producer hook (existing carrier, claim_tuple.grade(), no new ladder; Source in ingest_sources.py
  + README row) with a synthetic-fixture test and refusal controls. Box has no code-level done-when; acceptance is the closest
  check.

  '
acceptance: python3 -m pytest -q tests/vidya/test_vb_sr8_draft_acceptance_wire_wire.py
new_tests:
- tests/vidya/test_vb_sr8_draft_acceptance_wire_wire.py
non_goals:
- no retrospective measurement warrant
- no new grading ladder
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:docs/reports/sr8-edit-spec/native_worker.py: a9ec0d4a598612e360616bd0ca8e807b49be6a17
    epyc-root:scripts/vidya/ingest_sources.py: d2da53a6a45f78f20c2426ff20bb4b15cfbdad61
---
