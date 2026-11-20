---
schema: epyc.brief.v1
id: CF-AKV-0
box_text_sha: effb70792419f436
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/graph/session_log.py
approach: 'Zero-inference screen: share of resident context held by old tool results per long agent loop, from existing orchestrator
  serving records and REPL traces. First step: a script computing the share per loop and filing a table; stop when computed
  over all stored loops.

  '
acceptance: grep -qE '^ *- \[x\] \*\*CF\-AKV\-0\b' handoffs/active/context-and-token-economy.md
non_goals:
- no scope beyond the box text
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/graph/session_log.py: 41b42f0581971def4e8388e3ac29abf759ab2574
---
