---
schema: epyc.brief.v1
id: DHM-5.2
box_text_sha: 25c0443e4b40891e
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/memory-program.md
approach: 'First concrete step for: paired first-call probe for Codex subagent and opencode. Box has no done-when; acceptance
  is the closest check.

  '
acceptance: python3 -m pytest -q tests/test_dhm_5_2.py
new_tests:
- tests/test_dhm_5_2.py
non_goals: []
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/memory-program.md: 5c37bb9338910d1a5015df83dd0417010e4ddfc8
---
