---
schema: epyc.brief.v1
id: PM-REPLAN-C-SOAK
box_text_sha: t:aca46a5baf84d6f3
author: intake
written: '2026-11-24'
accepted: auto
where:
- epyc-root:docs/design/rowflow-replanning-scheduler.md
- epyc-root:scripts/coordination/rowflow/rowflow.py
approach: 'Run C in shadow as section 11 of the design doc lays out: REPLAN-SHADOW lines and replan-plan.json each tick, no
  grant writes, plus the nightly replay gate on that day''s trace. Read the six criteria per day from those artifacts, no
  compute beyond the nightly replay. Enforce only after 7 consecutive passing days, behind REPLAN_MODE=enforce with fallback
  to B (shadowed) or greedy on any solver exception or timeout. Reservation B stays RESERVATION_MODE=shadow.

  '
acceptance: a soak report shows 7 shadow days meeting all six criteria of docs/design/rowflow-replanning-scheduler.md section
  11, and rowflow.py on origin/main has REPLAN_MODE = "enforce" with the live keeper start time after that deploy
non_goals: []
tier: local
grounded:
  at: '2026-11-24'
  blobs:
    epyc-root:docs/design/rowflow-replanning-scheduler.md: b4f44a12eb54ec2613a1740987a7bdd254535a27
    epyc-root:scripts/coordination/rowflow/rowflow.py: b854ad584380c3d0347cd2a740b0b11199cf6ad8
---
