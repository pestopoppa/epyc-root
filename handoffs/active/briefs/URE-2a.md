---
schema: epyc.brief.v1
id: URE-2a
box_text_sha: bbfcc1b88baf1397
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/routing-program.md
approach: 'First concrete step for: Non-authoritative live cascade shadow. Box has no done-when; acceptance is the closest
  check.

  '
acceptance: python3 -m pytest -q tests/test_ure_2a.py
new_tests:
- tests/test_ure_2a.py
non_goals: []
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/routing-program.md: 9a1bd0abad62d3f58f0d431a191dda25a77841ee
---
