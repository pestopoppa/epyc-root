---
schema: epyc.brief.v1
id: UTM-M9
box_text_sha: b9244df258e2526a
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/memory-program.md
approach: 'First concrete step for: Add a NO-MEMORY control arm to the eval tower for every memory A/B. Box has no done-when;
  acceptance is the closest check.

  '
acceptance: python3 -m pytest -q tests/test_utm_m9.py
new_tests:
- tests/test_utm_m9.py
non_goals: []
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/memory-program.md: 5c37bb9338910d1a5015df83dd0417010e4ddfc8
---
