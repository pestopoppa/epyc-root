---
schema: epyc.brief.v1
id: AKPL-P6
box_text_sha: t:76eb9a6d86d32289
author: owner
written: '2026-11-21'
accepted: auto
where:
- scripts/coordination/taskflow/select.py
approach: 'Detect unresolved gate: deps, holds and caps from rowflow/taskflow state; draft the decision package per the operator
  decision-package contract; the owner sends it.

  '
acceptance: 'each AskUserQuestion in a week traces to a detector event. Promotion remains outside scope: the pipeline ends
  at a ratify package the operator signs (kernel-promotion skill).'
non_goals: []
tier: local
grounded:
  at: '2026-11-21'
  blobs:
    epyc-root:scripts/coordination/taskflow/select.py: 039141ad68150f4571ad4a578ad86aebe9125d65
---
