---
schema: epyc.brief.v1
id: TF-DUPID-HS4
box_text_sha: t:69e8c21487e69784
author: owner
written: '2026-11-20'
accepted: owner
where:
- handoffs/active/harness-program.md
- scripts/handoffs/box_index.py
approach: 'List occurrences, assign suffixed IDs to all but the canonical box, update gate/inputs references; owner session
  applies.

  '
acceptance: python3 scripts/handoffs/box_index.py --help
non_goals:
- Do not change box content or ticks
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/harness-program.md: cfddc6c1ce342e7f62e1bef3d4ae488e2441ab83
    epyc-root:scripts/handoffs/box_index.py: e0ba64195ce2ff64092c1971b2b358fe88dcabe1
---
