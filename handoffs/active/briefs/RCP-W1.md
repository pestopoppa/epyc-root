---
schema: epyc.brief.v1
id: RCP-W1
box_text_sha: e218499b37903fca
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:scripts/server/affinity_preflight.py
approach: 'Reference-lineup relaunch via orchestrator_stack.py under three-gates discipline, affinity_preflight.py live-affinity
  check, flip review_decision_shadow ON. First step: preflight run and relaunch manifest.

  '
acceptance: grep -qE '^ *- \[x\] \*\*RCP\-W1\b' handoffs/active/eval-tower-program.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:scripts/server/affinity_preflight.py: b68a78dd3da9d9c31e549042f297592eb32ca269
---
