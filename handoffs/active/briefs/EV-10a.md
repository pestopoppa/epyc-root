---
schema: epyc.brief.v1
id: EV-10a
box_text_sha: c62070741acd4a47
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:scripts/autopilot/paired_stats.py
approach: 'Paired skill-vs-no-skill efficacy check (SkillsBench method): report with-minus-without delta per suite for any
  candidate artifact; builds on skill_efficacy_paired_ab.py and paired_stats.py. First step: wire the paired delta report
  with a fixture test.

  '
acceptance: grep -qE '^ *- \[x\] \*\*EV\-10a\b' handoffs/active/eval-tower-program.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:scripts/autopilot/paired_stats.py: faba05796e424014a3291d92432927c6fc28fed4
---
