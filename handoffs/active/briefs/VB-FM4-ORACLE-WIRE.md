---
schema: epyc.brief.v1
id: VB-FM4-ORACLE-WIRE
box_text_sha: 2a929fce32c60a98
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/coordination/session_oracle.py
- epyc-root:scripts/experiments/fm4/task_acceptance.py
- epyc-root:scripts/experiments/fm4/run_gate.py
- epyc-root:scripts/experiments/fm4/native_canary.py
- epyc-root:scripts/vidya/ingest_sources.py
approach: 'Write-side wiring for: capture structured session-oracle parent joins. Land the source adapter/producer hook (existing
  carrier, claim_tuple.grade(), no new ladder; Source in ingest_sources.py + README row) with a synthetic-fixture test and
  refusal controls. Box done-when (live, operational, verified after): Model-free tests show session_oracle.py writes those
  fields, never labels a child successful from delivery or unrelated parent gates alone, and keeps prior verdicts. Native
  row `vb-fm4-codex-native-20261118` must file COMPLETE for the live proof.

  '
acceptance: '{ python3 /workspace/.claude/skills/inference-backlog-scheduling/scripts/queue_status.py | grep -F vb-fm4-codex-native-20261118
  | grep -q COMPLETE; } && python3 -m pytest -q tests/vidya/test_vb_fm4_oracle_wire_wire.py'
new_tests:
- tests/vidya/test_vb_fm4_oracle_wire_wire.py
non_goals:
- no retrospective measurement warrant
- no new grading ladder
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/coordination/session_oracle.py: aa66813611b0741946b51a9685bf8fde8440ba43
    epyc-root:scripts/experiments/fm4/task_acceptance.py: 46061ad0768e10683c9b1917e9b788fcbd8a6f56
    epyc-root:scripts/experiments/fm4/run_gate.py: 5bde11d7c69a6b5bca0286565455a54f94df3ce2
    epyc-root:scripts/experiments/fm4/native_canary.py: 96a65ed693f038605842e998c519c01291500c76
    epyc-root:scripts/vidya/ingest_sources.py: d2da53a6a45f78f20c2426ff20bb4b15cfbdad61
---
