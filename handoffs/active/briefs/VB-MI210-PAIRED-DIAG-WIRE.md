---
schema: epyc.brief.v1
id: VB-MI210-PAIRED-DIAG-WIRE
box_text_sha: 6b55004af6476ff6
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/vidya/producers/mi210_native_deploy.py
- epyc-root:data/vidya/mi210-paired-wire-20261117/q38-smoke-event.json
- epyc-root:data/vidya/mi210-paired-wire-20261117/deployment.json
- epyc-root:scripts/vidya/ingest_sources.py
approach: 'Write-side wiring for: prospectively capture MI210 serving paired diagnostics. Land the source adapter/producer
  hook (existing carrier, claim_tuple.grade(), no new ladder; Source in ingest_sources.py + README row) with a synthetic-fixture
  test and refusal controls. Box done-when (live, operational, verified after): strict readback, patch-application and shared-grade
  controls pass; no real measurement or planning-context acceptance is implied. Native row `vb-q38-preflight-planner-20261118`
  must file COMPLETE for the live proof.

  '
acceptance: '{ python3 /workspace/.claude/skills/inference-backlog-scheduling/scripts/queue_status.py | grep -F vb-q38-preflight-planner-20261118
  | grep -q COMPLETE; } && python3 -m pytest -q tests/vidya/test_vb_mi210_paired_diag_wire_wire.py'
new_tests:
- tests/vidya/test_vb_mi210_paired_diag_wire_wire.py
non_goals:
- no retrospective measurement warrant
- no new grading ladder
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/vidya/producers/mi210_native_deploy.py: b49e92db548d8f21b0be19af314e26c0495966a7
    epyc-root:data/vidya/mi210-paired-wire-20261117/q38-smoke-event.json: 17124f5cee37a68a93b295273989cbc992c9d6be
    epyc-root:data/vidya/mi210-paired-wire-20261117/deployment.json: 410391154ac826ba54fd016b63eaccde167ca10c
    epyc-root:scripts/vidya/ingest_sources.py: d2da53a6a45f78f20c2426ff20bb4b15cfbdad61
---
