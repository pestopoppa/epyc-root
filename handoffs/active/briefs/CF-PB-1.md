---
schema: epyc.brief.v1
id: CF-PB-1
box_text_sha: d687c5770d14ce53
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/graph/session_summary.py
approach: 'Plan-boundary compaction trigger priced by local break-even: rewrite cost = re-prefill tokens (prefix-cache invalidation)
  vs per-request savings. First step: the break-even function with unit tests using measured local prefill rates.

  '
acceptance: grep -qE '^ *- \[x\] \*\*CF\-PB\-1\b' handoffs/active/context-and-token-economy.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/graph/session_summary.py: a0441f76772b6ad113645439417fd97336173f4d
---
