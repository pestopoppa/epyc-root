---
schema: epyc.brief.v1
id: CAFE-2
box_text_sha: 3620ce050d690279
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:/mnt/raid0/llm/tmp/codex-ni-20261026-inf50-window-successor/margin-recovery/results/RESULT.json
- epyc-root:scripts/vidya/ingest_sources.py
approach: 'Write-side wiring for: [ ] **CAFE-2 native cost capture:** capture actual MTP draft and each arm’s target-state
  snapshot/restore, producer-authored state digest and length with independently re. Land the source adapter/producer hook
  (existing carrier, claim_tuple.grade(), no new ladder; Source in ingest_sources.py + README row) with a synthetic-fixture
  test and refusal controls. Box has no code-level done-when; acceptance is the closest check.

  '
acceptance: python3 -m pytest -q tests/vidya/test_cafe_wire.py
new_tests:
- tests/vidya/test_cafe_wire.py
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
