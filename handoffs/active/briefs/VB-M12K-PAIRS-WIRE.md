---
schema: epyc.brief.v1
id: VB-M12K-PAIRS-WIRE
box_text_sha: 8227565dbd8a4c2d
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/benchmark/frontdoor_memory_pairs.py
- epyc-root:scripts/benchmark/m12k_frontdoor_memory_ab.py
- epyc-root:tests/benchmark/test_frontdoor_memory_pairs.py
- epyc-root:tests/benchmark/test_m12k_unserved.py
- epyc-root:scripts/vidya/ingest_sources.py
approach: 'Add adapter for paired frontdoor memory results: native error receipts (HTTP code/body, routed roles, UNSERVED
  pair voids, futility denominators), per-request seeds and effective memory-switch receipts, store/serving config, exact-or-unknown
  token usage; no invented seed/switch echoes; grade via claim_tuple.grade(), no significance claim. Box has no done-when;
  acceptance is the closest check: new adapter test on offline fixtures; producer receipt integration and native canary stay
  operational.

  '
acceptance: python3 -m pytest -q tests/vidya/test_m12k_pairs_adapter.py tests/benchmark/test_frontdoor_memory_pairs.py tests/benchmark/test_m12k_unserved.py
new_tests:
- tests/vidya/test_m12k_pairs_adapter.py
non_goals:
- no historical warrant
- no second ladder
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/benchmark/frontdoor_memory_pairs.py: 1f4fad9393fe24210b8c933b6a94840bee75976e
    epyc-root:scripts/benchmark/m12k_frontdoor_memory_ab.py: d48f5e8dbee9262a55752fb2839e6bc59362011f
    epyc-root:tests/benchmark/test_frontdoor_memory_pairs.py: 524b6e31745be91d180cfe4049f4af3dbde40f31
    epyc-root:tests/benchmark/test_m12k_unserved.py: 6d06cf133a39b0871e48382579fca4efd5b7ace6
    epyc-root:scripts/vidya/ingest_sources.py: d2da53a6a45f78f20c2426ff20bb4b15cfbdad61
---
