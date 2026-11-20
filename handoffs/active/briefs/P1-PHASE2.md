---
schema: epyc.brief.v1
id: P1-PHASE2
box_text_sha: 2bb4ca94af538669
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:tests/vidya/test_autopilot_lineup_tier.py
- epyc-root:tests/vidya/test_p1_acceptance_ac8_pool.py
- epyc-root:scripts/vidya/p1_acceptance.py
- epyc-root:tests/vidya/test_p1_acceptance_ac9_counted.py
- epyc-root:scripts/vidya/ingest_sources.py
approach: 'Write-side wiring for: Phase 2 of the belief storage redesign. Land the source adapter/producer hook (existing
  carrier, claim_tuple.grade(), no new ladder; Source in ingest_sources.py + README row) with a synthetic-fixture test and
  refusal controls. Box has no code-level done-when; acceptance is the closest check.

  '
acceptance: python3 -m pytest -q tests/vidya/test_p1_phase2_wire.py tests/vidya/test_autopilot_lineup_tier.py tests/vidya/test_p1_acceptance_ac8_pool.py
new_tests:
- tests/vidya/test_p1_phase2_wire.py
non_goals:
- no retrospective measurement warrant
- no new grading ladder
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:tests/vidya/test_autopilot_lineup_tier.py: a55d2a0bd8a7dc6342693217a90b8fdd7e4c05fc
    epyc-root:tests/vidya/test_p1_acceptance_ac8_pool.py: 31d7ef818d03636fba8c7d49c16939e55a3e6a55
    epyc-root:scripts/vidya/p1_acceptance.py: ed5113288e9bfe9af8c5d142a5525937f343a2bb
    epyc-root:tests/vidya/test_p1_acceptance_ac9_counted.py: 459a4e59be78af25165e878b475ef6a442a7717f
    epyc-root:scripts/vidya/ingest_sources.py: d2da53a6a45f78f20c2426ff20bb4b15cfbdad61
---
