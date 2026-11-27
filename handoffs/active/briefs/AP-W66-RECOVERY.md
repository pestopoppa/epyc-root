---
schema: epyc.brief.v1
id: AP-W66-RECOVERY
box_text_sha: t:41dc90bbad3aca9d
author: planning
written: '2026-11-27'
accepted: auto
where:
- epyc-root:docs/reports/autopilot-w66-replay-plan.md
- epyc-orchestrator:src/trace/l2/loop_detectors.py
approach: 'Use the successful late edit as a negative control and the repeated greps as a positive control. Score the first
  intervention against changes on disk and test outcomes. Use the partial patches to evaluate one bounded corrective turn
  with its true guidance history. See the recovery section of the replay plan for the pilot endpoints.

  '
acceptance: an offline report records false interventions on accepted traces, missed loops, actionable corrections, remaining
  budgets and a bounded fresh-task pilot plan with acceptance, paid-cost and wall-time endpoints.
non_goals: []
tier: local
grounded:
  at: '2026-11-27'
  blobs:
    epyc-root:docs/reports/autopilot-w66-replay-plan.md: ec15417f839d78efe2cc894c3d9a77e3c8fc43d9
    epyc-orchestrator:src/trace/l2/loop_detectors.py: dbb0ccc58c3f6dc158ef25ee6d1c19f5a2f16651
---
