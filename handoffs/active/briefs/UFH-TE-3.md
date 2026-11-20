---
schema: epyc.brief.v1
id: UFH-TE-3
box_text_sha: c6a1dc76b6213551
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- scripts/handoffs/task_lint_core.py
approach: 'Add a lint check flagging handoff sentences claiming a skipped/reused call without one of the classes identity-receipt,
  rate-tau-audited (with audited denominator), none; write the receipt-contract doc section first (none exists). Rule text
  already in the box.

  '
acceptance: pytest tests/handoffs/test_skip_class_lint.py
new_tests:
- tests/handoffs/test_skip_class_lint.py
non_goals:
- no rewrite of existing handoff prose
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/handoffs/task_lint_core.py: 26430be50805c1e6aeb8aa3c5d8f918cb9bd7b22
---
