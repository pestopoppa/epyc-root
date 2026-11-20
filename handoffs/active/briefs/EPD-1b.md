---
schema: epyc.brief.v1
id: EPD-1b
box_text_sha: b2aacfca7d703d94
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/routing-program.md
approach: 'First concrete step for: EPD-1b — **(operator-gated, live store)** backfill historical labels: `UPDATE memories
  SET outcome = CASE WHEN q_value > 0.5 THEN ''success'' ELSE ''failure'' END WHERE update_count > 0`. Until then rows. Box
  has no done-when; acceptance is the closest check.

  '
acceptance: python3 -m pytest -q tests/test_epd_1b.py
new_tests:
- tests/test_epd_1b.py
non_goals: []
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/routing-program.md: 9a1bd0abad62d3f58f0d431a191dda25a77841ee
---
