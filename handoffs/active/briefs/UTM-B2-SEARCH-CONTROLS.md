---
schema: epyc.brief.v1
id: UTM-B2-SEARCH-CONTROLS
box_text_sha: e86d093641e074ef
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/memory-program.md
approach: 'First concrete step for: [non-inference] Extend ms.search with an optional time range applied before scoring, a
  stateful exclude-seen-sessions set, count-only and group-by-session modes, limit/offset and a snippet clip, and m. Box has
  no done-when; acceptance is the closest check.

  '
acceptance: python3 -m pytest -q tests/test_utm_b2_search_controls.py
new_tests:
- tests/test_utm_b2_search_controls.py
non_goals: []
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/memory-program.md: 5c37bb9338910d1a5015df83dd0417010e4ddfc8
---
