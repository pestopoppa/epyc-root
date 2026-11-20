---
schema: epyc.brief.v1
id: RTG-EP-1
box_text_sha: abb77762a6df6356
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/routing-program.md
approach: 'First concrete step for: Prove the AMDGPU/MIGraphX execution provider on gfx90a. Box has no done-when; acceptance
  is the closest check.

  '
acceptance: python3 -m pytest -q tests/test_rtg_ep_1.py
new_tests:
- tests/test_rtg_ep_1.py
non_goals: []
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/routing-program.md: 9a1bd0abad62d3f58f0d431a191dda25a77841ee
---
