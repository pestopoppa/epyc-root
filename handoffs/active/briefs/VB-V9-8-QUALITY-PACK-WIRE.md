---
schema: epyc.brief.v1
id: VB-V9-8-QUALITY-PACK-WIRE
box_text_sha: 7392e41f9bd6f276
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:.claude/skills/kernel-promotion/scripts/quality_parity.py
- epyc-root:data/vidya/quality-pack-loader-reshape-20261118/full-r2/receipt.json
- epyc-root:scripts/vidya/ingest_sources.py
approach: 'Write-side wiring for: prospectively capture broad quality-parity pack comparisons. Land the source adapter/producer
  hook (existing carrier, claim_tuple.grade(), no new ladder; Source in ingest_sources.py + README row) with a synthetic-fixture
  test and refusal controls. Box done-when (live, operational, verified after): the original full two-arm capture is filed
  with complete bytes/pins and verified cleanup. Native row `handoff-vidya-quality-pack-frontdoor-20261118` must file COMPLETE
  for the live proof.

  '
acceptance: '{ python3 /workspace/.claude/skills/inference-backlog-scheduling/scripts/queue_status.py | grep -F handoff-vidya-quality-pack-frontdoor-20261118
  | grep -q COMPLETE; } && python3 -m pytest -q tests/vidya/test_vb_v9_8_quality_pack_wire_wire.py'
new_tests:
- tests/vidya/test_vb_v9_8_quality_pack_wire_wire.py
non_goals:
- no retrospective measurement warrant
- no new grading ladder
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:.claude/skills/kernel-promotion/scripts/quality_parity.py: 8788f96419140ae8c20e4e10cfc55d2125d8ad4c
    epyc-root:data/vidya/quality-pack-loader-reshape-20261118/full-r2/receipt.json: 97165887b131e73db46305f8450072f2d07105d9
    epyc-root:scripts/vidya/ingest_sources.py: d2da53a6a45f78f20c2426ff20bb4b15cfbdad61
---
