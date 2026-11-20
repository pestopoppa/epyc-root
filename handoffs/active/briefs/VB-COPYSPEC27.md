---
schema: epyc.brief.v1
id: VB-COPYSPEC27
box_text_sha: 890d9baff6f2bb25
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/benchmark/copyspec_27b.py
- epyc-root:tests/benchmark/test_copyspec_27b.py
- epyc-root:scripts/vidya/ingest_sources.py
- epyc-root:scripts/vidya/adapters/README.md
approach: 'Add adapter projecting the native COPYSPEC-27B request census through the draft-acceptance carrier and claim_tuple.grade();
  register Source + README row. Box has no done-when; acceptance is the closest check: new adapter test on a synthetic census
  fixture. The native planning-context canary (row df2-copyspec-27b-gpu-20261120) is operational and stays out of this brief.

  '
acceptance: python3 -m pytest -q tests/vidya/test_copyspec_27b_adapter.py
new_tests:
- tests/vidya/test_copyspec_27b_adapter.py
non_goals:
- no GPU run
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/benchmark/copyspec_27b.py: 10fff29058652130cf2da9a7cf7330da0d77feb5
    epyc-root:tests/benchmark/test_copyspec_27b.py: ae8d9bb8c46a9a91b9f2581a8db45bff8b0602b1
    epyc-root:scripts/vidya/ingest_sources.py: d2da53a6a45f78f20c2426ff20bb4b15cfbdad61
    epyc-root:scripts/vidya/adapters/README.md: e3c2ef4730581badb912189e13072542bc78a2cf
---
