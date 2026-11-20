---
schema: epyc.brief.v1
id: TOKEN-AUDIT-6-PER-ROW-ACCOUNTING
box_text_sha: 8bd8a6c189bc259e
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/coordination/churn/file_result.py
- epyc-root:scripts/coordination/churn/tokens_per_task.py
- epyc-root:docs/reports/coordination/token-efficiency-audit-20261106.md
approach: 'file_result.token_accounting (381b409e2) attributes owner-session tokens per session-day, not per row. Add rollout-window
  to row-run-window matching in tokens_per_task.py: attribute rollout tokens whose time span falls within the row''s run window,
  write the figure into the filing record, with unknown (never zero) when windows are ambiguous or overlap with another row.
  Test with two overlapping rows.

  '
acceptance: python3 -m pytest -q scripts/coordination/tests/test_tokens_per_row.py
new_tests:
- scripts/coordination/tests/test_tokens_per_row.py
non_goals:
- no per-session-day regression
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/coordination/churn/file_result.py: 0393b1b8aa75653ee7beb98c89194d35f9455ce5
    epyc-root:scripts/coordination/churn/tokens_per_task.py: 37e95ea0a19da87920567b09959935662e23f924
    epyc-root:docs/reports/coordination/token-efficiency-audit-20261106.md: 9d80ad333472cffc83b29dd3c4789273c896f237
---
