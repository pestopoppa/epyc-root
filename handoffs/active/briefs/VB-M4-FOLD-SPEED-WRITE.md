---
schema: epyc.brief.v1
id: VB-M4-FOLD-SPEED-WRITE
box_text_sha: 3be9ab2ed5bf2e4e
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:/mnt/raid0/llm/tmp/refactor-01a16fc3/m4-fold-gates/REGISTRATION-PROPOSAL.md
- epyc-root:scripts/vidya/ingest_sources.py
approach: 'Write-side wiring for: prospective native current-C5/M4 speed source (filed 2026-10-27, codex-refactor-01a16fc3).
  Land the source adapter/producer hook (existing carrier, claim_tuple.grade(), no new ladder; Source in ingest_sources.py
  + README row) with a synthetic-fixture test and refusal controls. Box done-when (live, operational, verified after): the
  next M4 fold-speed or calibration run after the hook ingests with refused=0 and the AK canary for the champion target lists
  its speed claim.

  '
acceptance: python3 -m pytest -q tests/vidya/test_vb_m4_fold_speed_write_wire.py
new_tests:
- tests/vidya/test_vb_m4_fold_speed_write_wire.py
non_goals:
- no retrospective measurement warrant
- no new grading ladder
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:/mnt/raid0/llm/tmp/refactor-01a16fc3/m4-fold-gates/REGISTRATION-PROPOSAL.md: 56d9219eaf1c0fd10f0f02bab84b7dca36da2a53
    epyc-root:scripts/vidya/ingest_sources.py: d2da53a6a45f78f20c2426ff20bb4b15cfbdad61
---
