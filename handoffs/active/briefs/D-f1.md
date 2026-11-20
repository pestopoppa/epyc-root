---
schema: epyc.brief.v1
id: D-f1
box_text_sha: 0b8ee4b5891f7af5
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:tests/unit/test_df3_graph_snapshot_writes.py
- epyc-orchestrator:src/graph/helpers.py
approach: 'First concrete step for: Verify the lease under the live 6-worker API. Box has no done-when; acceptance is the
  closest check.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_d_f1.py tests/unit/test_df3_graph_snapshot_writes.py
new_tests:
- tests/unit/test_d_f1.py
non_goals: []
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:tests/unit/test_df3_graph_snapshot_writes.py: c5ffaa43ac71a1338b885b2772698746ac14009e
    epyc-orchestrator:src/graph/helpers.py: eb930e373b30b65239d1a6e4d0b95d2e9eab124a
---
