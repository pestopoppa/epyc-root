---
schema: epyc.brief.v1
id: VB-INF50-DRAFT-WIDTH
box_text_sha: 69f04cfacd6855f4
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:/mnt/raid0/llm/tmp/codex-ni-20261026-inf50-window-successor/margin-recovery/results/RESULT.json
- epyc-root:scripts/vidya/ingest_sources.py
approach: 'Write-side wiring for: wire prospective speculative draft-width and p-min observations. Land the source adapter/producer
  hook (existing carrier, claim_tuple.grade(), no new ladder; Source in ingest_sources.py + README row) with a synthetic-fixture
  test and refusal controls. Box done-when (live, operational, verified after): the first post-hook draft-width, p-min or
  SR-6 n_max run ingests with refused=0 and the AutoPilot canary for the frontdoor role lists its acceptance claim.

  '
acceptance: python3 -m pytest -q tests/vidya/test_vb_inf50_draft_width_wire.py
new_tests:
- tests/vidya/test_vb_inf50_draft_width_wire.py
non_goals:
- no retrospective measurement warrant
- no new grading ladder
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:/mnt/raid0/llm/tmp/codex-ni-20261026-inf50-window-successor/margin-recovery/results/RESULT.json: f40f9dc2ac0558d38768e62b4d070652f322eb74
    epyc-root:scripts/vidya/ingest_sources.py: d2da53a6a45f78f20c2426ff20bb4b15cfbdad61
---
