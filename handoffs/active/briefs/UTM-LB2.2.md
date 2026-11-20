---
schema: epyc.brief.v1
id: UTM-LB2.2
box_text_sha: a0c9c77777d2581f
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/memory-program.md
approach: 'First concrete step for: Ingest projector events into the unified trace store. Box has no done-when; acceptance
  is the closest check.

  '
acceptance: python3 -m pytest -q tests/test_utm_lb2_2.py
new_tests:
- tests/test_utm_lb2_2.py
non_goals: []
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/memory-program.md: 5c37bb9338910d1a5015df83dd0417010e4ddfc8
---
