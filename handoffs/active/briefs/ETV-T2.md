---
schema: epyc.brief.v1
id: ETV-T2
box_text_sha: cb0b4ff21efd833d
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:scripts/autopilot/eval_tower.py
approach: 'Report-only trajectory/outcome divergence counter for tool_use sentinels. First step: counter over existing trial
  records emitting a count line, with a fixture test.

  '
acceptance: grep -qE '^ *- \[x\] \*\*ETV\-T2\b' handoffs/active/eval-tower-program.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:scripts/autopilot/eval_tower.py: 97a1e3ef88f25b97b8d09f0fd679e87b566d63fc
---
