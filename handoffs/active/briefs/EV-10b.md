---
schema: epyc.brief.v1
id: EV-10b
box_text_sha: 1762164faa54f6f5
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:scripts/autopilot/eval_tower.py
approach: 'Surrogate-verifier scoring for leak-constrained tasks (CoEvoSkills): independent cross-family verifier writes the
  assertion suite. First step: interface plus fixture test in eval_tower scoring.

  '
acceptance: grep -qE '^ *- \[x\] \*\*EV\-10b\b' handoffs/active/eval-tower-program.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:scripts/autopilot/eval_tower.py: 97a1e3ef88f25b97b8d09f0fd679e87b566d63fc
---
