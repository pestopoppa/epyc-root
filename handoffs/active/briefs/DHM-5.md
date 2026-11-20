---
schema: epyc.brief.v1
id: DHM-5
box_text_sha: d8c2675f07192070
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/dev_harness/mine_dhm51.py
- epyc-root:tests/dev_harness/test_mine_dhm51.py
- epyc-root:docs/design/dev-harness-mining-results-20261022.md
- epyc-root:data/dev_harness/mining-full-20261022T1310Z.aggregate.json
approach: 'First concrete step for: Measure the always-on prefix (CLAUDE.md plus the MEMORY.md index) in tokens per turn from
  transcript usage fields, per harness (intake-2408, intake-2410). Box has no done-when; acceptance is the closest check.

  '
acceptance: python3 -m pytest -q tests/test_dhm_5.py tests/dev_harness/test_mine_dhm51.py
new_tests:
- tests/test_dhm_5.py
non_goals: []
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/dev_harness/mine_dhm51.py: c00a2c2ff7fb7a1eec7ba73ab3c7d9838666d8d3
    epyc-root:tests/dev_harness/test_mine_dhm51.py: 2da32b9115700bb50d19e72d3b0d8d94879c17cf
    epyc-root:docs/design/dev-harness-mining-results-20261022.md: 45c30416ed4cad116b963a842b020bd7ccaa134f
    epyc-root:data/dev_harness/mining-full-20261022T1310Z.aggregate.json: f7c0607cb8fa4ab46ee73dbb987d9cd2babdae47
---
