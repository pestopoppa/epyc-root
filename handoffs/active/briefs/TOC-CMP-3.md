---
schema: epyc.brief.v1
id: TOC-CMP-3
box_text_sha: 549b67de66d1ded1
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/graph/session_summary.py
approach: 'Add the compaction artifact contract to the TOC A/B: six-field execution brief, pinned-governance buffer exempt
  from folding. First step: contract schema and validator with unit tests.

  '
acceptance: grep -qE '^ *- \[x\] \*\*TOC\-CMP\-3\b' handoffs/active/context-and-token-economy.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/graph/session_summary.py: a0441f76772b6ad113645439417fd97336173f4d
---
