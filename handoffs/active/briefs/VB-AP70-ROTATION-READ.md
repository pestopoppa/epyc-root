---
schema: epyc.brief.v1
id: VB-AP70-ROTATION-READ
box_text_sha: 7c3478e92c3e475b
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/vidya/adapters/autopilot_journal.py
- epyc-root:scripts/vidya/ingest_sources.py
approach: 'Write-side wiring for: strictly carry prospective AP-70 rotation-boundary records through the existing AutoPilot
  journal adapter. Land the source adapter/producer hook (existing carrier, claim_tuple.grade(), no new ladder; Source in
  ingest_sources.py + README row) with a synthetic-fixture test and refusal controls. Box done-when (live, operational, verified
  after): a producer-written rotation plan/boundary/pair/summary set projects with refused=0 and the AutoPilot canary lists
  its summary claim.

  '
acceptance: python3 -m pytest -q tests/vidya/test_vb_ap70_rotation_read_wire.py
new_tests:
- tests/vidya/test_vb_ap70_rotation_read_wire.py
non_goals:
- no retrospective measurement warrant
- no new grading ladder
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/vidya/adapters/autopilot_journal.py: f552fed8f58fa1f1a5a9f9724c3028438373c36a
    epyc-root:scripts/vidya/ingest_sources.py: d2da53a6a45f78f20c2426ff20bb4b15cfbdad61
---
