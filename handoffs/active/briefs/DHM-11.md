---
schema: epyc.brief.v1
id: DHM-11
box_text_sha: f15b4ee61525c083
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/memory-program.md
approach: 'First concrete step for: Hook coverage for Codex and opencode in general. Box has no done-when; acceptance is the
  closest check.

  '
acceptance: python3 -m pytest -q tests/test_dhm_11.py
new_tests:
- tests/test_dhm_11.py
non_goals: []
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/memory-program.md: 5c37bb9338910d1a5015df83dd0417010e4ddfc8
---
