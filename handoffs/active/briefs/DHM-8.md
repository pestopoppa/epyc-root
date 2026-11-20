---
schema: epyc.brief.v1
id: DHM-8
box_text_sha: 9063ee4988343371
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/memory-program.md
approach: 'First concrete step for: Guard the glob rm -rf class with a hook (D9, per-change operator ack required; file the
  proposal, do not apply). Box has no done-when; acceptance is the closest check.

  '
acceptance: python3 -m pytest -q tests/test_dhm_8.py
new_tests:
- tests/test_dhm_8.py
non_goals: []
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/memory-program.md: 5c37bb9338910d1a5015df83dd0417010e4ddfc8
---
