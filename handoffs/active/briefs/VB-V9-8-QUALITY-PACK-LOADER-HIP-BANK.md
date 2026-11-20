---
schema: epyc.brief.v1
id: VB-V9-8-QUALITY-PACK-LOADER-HIP-BANK
box_text_sha: 3718fc0226af5f3d
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/vidya/ingest_sources.py
approach: 'Write-side wiring for: capture and strictly admit the four-item architect-general HIP production bank with the
  native loader-reshape fixture. Land the source adapter/producer hook (existing carrier, claim_tuple.grade(), no new ladder;
  Source in ingest_sources.py + README row) with a synthetic-fixture test and refusal controls. Box has no code-level done-when;
  acceptance is the closest check. Native row `handoff-vidya-quality-pack-architect-general-hip-loader-bank-20261118` must
  file COMPLETE for the live proof.

  '
acceptance: '{ python3 /workspace/.claude/skills/inference-backlog-scheduling/scripts/queue_status.py | grep -F handoff-vidya-quality-pack-architect-general-hip-loader-bank-20261118
  | grep -q COMPLETE; } && python3 -m pytest -q tests/vidya/test_vb_v9_8_quality_pack_loader_hip_bank_wire.py'
new_tests:
- tests/vidya/test_vb_v9_8_quality_pack_loader_hip_bank_wire.py
non_goals:
- no retrospective measurement warrant
- no new grading ladder
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/vidya/ingest_sources.py: d2da53a6a45f78f20c2426ff20bb4b15cfbdad61
---
