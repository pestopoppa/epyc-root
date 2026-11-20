---
schema: epyc.brief.v1
id: TOC-CMP-15
box_text_sha: 0de3eb233128072c
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/graph/context_arm_ab.py
approach: 'Replace the seven-policy bake-off with the narrower CF-3c A/B the code poses (arms per box). First step: arm config
  in context_arm_ab.py and run manifest.

  '
acceptance: grep -qE '^ *- \[x\] \*\*TOC\-CMP\-15\b' handoffs/active/context-and-token-economy.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/graph/context_arm_ab.py: 5f04f543e3d659b4f40e3683181386af6c9cae88
---
