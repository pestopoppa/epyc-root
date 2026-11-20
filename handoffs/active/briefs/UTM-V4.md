---
schema: epyc.brief.v1
id: UTM-V4
box_text_sha: 2a7e3e5c3317832a
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/memory-program.md
approach: 'First concrete step for: Test answer-time evidence distillation independently of memory writing. Box has no done-when;
  acceptance is the closest check.

  '
acceptance: python3 -m pytest -q tests/test_utm_v4.py
new_tests:
- tests/test_utm_v4.py
non_goals: []
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/memory-program.md: 5c37bb9338910d1a5015df83dd0417010e4ddfc8
---
