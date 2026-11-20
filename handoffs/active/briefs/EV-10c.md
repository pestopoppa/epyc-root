---
schema: epyc.brief.v1
id: EV-10c
box_text_sha: d9c76265f69921e6
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:scripts/autopilot/skill_efficacy_paired_ab.py
approach: 'Single-artifact admission prefilter (CORE pattern): re-attempt only the originating failure with only the candidate
  artifact before the EV-10a gate. First step: prefilter function and test.

  '
acceptance: grep -qE '^ *- \[x\] \*\*EV\-10c\b' handoffs/active/eval-tower-program.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:scripts/autopilot/skill_efficacy_paired_ab.py: 124018fe481eb0f651f849eb49907f89fe69f9b9
---
