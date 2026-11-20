---
schema: epyc.brief.v1
id: UTM-V1-STORE
box_text_sha: 514a889aeba3439e
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/memory-program.md
approach: 'First concrete step for: map committed UTM-V1 operations onto MemoryActionStore and replay real traces. Box has
  no done-when; acceptance is the closest check.

  '
acceptance: python3 -m pytest -q tests/test_utm_v1_store.py
new_tests:
- tests/test_utm_v1_store.py
non_goals: []
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/memory-program.md: 5c37bb9338910d1a5015df83dd0417010e4ddfc8
---
