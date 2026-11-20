---
schema: epyc.brief.v1
id: VB-AK-WM3-REPLAY-WIRE
box_text_sha: 68ebb6e3d95bb7ae
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/vidya/ingest_sources.py
approach: 'Write-side wiring for: Wire the write side of the AK-WM-3 offline exploration-policy replay before its next run.
  Land the source adapter/producer hook (existing carrier, claim_tuple.grade(), no new ladder; Source in ingest_sources.py
  + README row) with a synthetic-fixture test and refusal controls. Box done-when (live, operational, verified after): the
  next replay''s output passes the planning-context canary.

  '
acceptance: python3 -m pytest -q tests/vidya/test_vb_ak_wm3_replay_wire_wire.py
new_tests:
- tests/vidya/test_vb_ak_wm3_replay_wire_wire.py
non_goals:
- no retrospective measurement warrant
- no new grading ladder
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/vidya/ingest_sources.py: d2da53a6a45f78f20c2426ff20bb4b15cfbdad61
---
