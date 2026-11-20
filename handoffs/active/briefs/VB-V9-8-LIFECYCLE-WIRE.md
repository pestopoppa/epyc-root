---
schema: epyc.brief.v1
id: VB-V9-8-LIFECYCLE-WIRE
box_text_sha: 11acc62234b5e883
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/benchmark/kernel_promotion_resident_runner.py
- epyc-root:scripts/vidya/ingest_sources.py
approach: 'Write-side wiring for: prospectively capture resident/fresh promotion-instrument diagnostics. Land the source adapter/producer
  hook (existing carrier, claim_tuple.grade(), no new ladder; Source in ingest_sources.py + README row) with a synthetic-fixture
  test and refusal controls. Box has no code-level done-when; acceptance is the closest check. Native row `vb-v9-8-lifecycle-native-20261118`
  must file COMPLETE for the live proof.

  '
acceptance: '{ python3 /workspace/.claude/skills/inference-backlog-scheduling/scripts/queue_status.py | grep -F vb-v9-8-lifecycle-native-20261118
  | grep -q COMPLETE; } && python3 -m pytest -q tests/vidya/test_vb_v9_8_lifecycle_wire_wire.py'
new_tests:
- tests/vidya/test_vb_v9_8_lifecycle_wire_wire.py
non_goals:
- no retrospective measurement warrant
- no new grading ladder
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/benchmark/kernel_promotion_resident_runner.py: 1c07f30e9ae465647e662ac6a64c8e870a279941
    epyc-root:scripts/vidya/ingest_sources.py: d2da53a6a45f78f20c2426ff20bb4b15cfbdad61
---
