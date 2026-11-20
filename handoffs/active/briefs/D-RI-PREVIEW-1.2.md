---
schema: epyc.brief.v1
id: D-RI-PREVIEW-1.2
box_text_sha: 25ced56d79f424e3
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/benchmark/repl_upfront_variant.py
- epyc-orchestrator:scripts/benchmark/own_port_proof.py
- epyc-orchestrator:scripts/benchmark/repl_preview_fixture.py
- epyc-root:docs/reports/dripreview15-upfront-implementation-20261119.md
approach: 'First concrete step for: harder fixture so the comparator can separate renderings. Box done-when: a granted run
  writes the 3-rendering x n=30 tally or a valid-false void with replayed replies.

  '
acceptance: python3 -m pytest -q tests/test_d_ri_preview_1_2.py
new_tests:
- tests/test_d_ri_preview_1_2.py
non_goals: []
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/benchmark/repl_upfront_variant.py: f2e352b7c8c85b6aef55e2d6f9e8370967fa87ea
    epyc-orchestrator:scripts/benchmark/own_port_proof.py: d656c21f63d51962b121549cb63f79839aa53dba
    epyc-orchestrator:scripts/benchmark/repl_preview_fixture.py: 6830c04488569742bcbf5a28b723223bb73ab419
    epyc-root:docs/reports/dripreview15-upfront-implementation-20261119.md: 5b9a8ad6557e32d8b8e053c8ac4809502f283b48
---
