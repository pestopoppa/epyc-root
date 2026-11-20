---
schema: epyc.brief.v1
id: DAR-5
box_text_sha: 45af9a938904fb33
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/routing-program.md
approach: 'First concrete step for: Precondition is a reward carrying a wall-clock speed axis (above), since the cost-dominated
  majority is where most traffic lives and the current reward cannot price it. Scope once the reward carries t. Box has no
  done-when; acceptance is the closest check.

  '
acceptance: python3 -m pytest -q tests/test_dar_5.py
new_tests:
- tests/test_dar_5.py
non_goals: []
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/routing-program.md: 9a1bd0abad62d3f58f0d431a191dda25a77841ee
---
