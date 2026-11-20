---
schema: epyc.brief.v1
id: UTM-V6
box_text_sha: 2e1d2099b47dca19
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/memory-program.md
approach: 'First concrete step for: Run a complete memory evaluation matrix with a mandatory no-memory control. Box has no
  done-when; acceptance is the closest check.

  '
acceptance: python3 -m pytest -q tests/test_utm_v6.py
new_tests:
- tests/test_utm_v6.py
non_goals: []
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/memory-program.md: 5c37bb9338910d1a5015df83dd0417010e4ddfc8
---
