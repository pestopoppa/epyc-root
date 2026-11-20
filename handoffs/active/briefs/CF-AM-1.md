---
schema: epyc.brief.v1
id: CF-AM-1
box_text_sha: 8ab0788325400371
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/graph/context_arm_ab.py
approach: 'Compare parallel small-model gist extraction with current folding and lossless raw retention. First step: arm definitions
  in context_arm_ab.py and a fixture test; run on the paired cohort.

  '
acceptance: grep -qE '^ *- \[x\] \*\*CF\-AM\-1\b' handoffs/active/context-and-token-economy.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/graph/context_arm_ab.py: 5f04f543e3d659b4f40e3683181386af6c9cae88
---
