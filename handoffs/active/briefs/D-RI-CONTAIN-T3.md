---
schema: epyc.brief.v1
id: D-RI-CONTAIN-T3
box_text_sha: d634e967ce0df5a2
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/memory-program.md
approach: 'First concrete step for: Owned cgroup memory and pids limits. Box has no done-when; acceptance is the closest check.

  '
acceptance: python3 -m pytest -q tests/test_d_ri_contain_t3.py
new_tests:
- tests/test_d_ri_contain_t3.py
non_goals: []
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/memory-program.md: 5c37bb9338910d1a5015df83dd0417010e4ddfc8
---
