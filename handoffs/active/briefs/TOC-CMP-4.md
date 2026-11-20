---
schema: epyc.brief.v1
id: TOC-CMP-4
box_text_sha: e8e0830e55f48be0
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/graph/context_arm_ab.py
approach: 'Make the compaction A/B reproducible: pre-register MDE 0.10 blocked actions/step, >=30 paired compaction points
  per model x 8-12 repeats, three arms. First step: the pre-registration file plus sample-size test.

  '
acceptance: grep -qE '^ *- \[x\] \*\*TOC\-CMP\-4\b' handoffs/active/context-and-token-economy.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/graph/context_arm_ab.py: 5f04f543e3d659b4f40e3683181386af6c9cae88
---
