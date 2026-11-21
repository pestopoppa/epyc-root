---
schema: epyc.brief.v1
id: AKPL-P5
box_text_sha: t:57de4d209f93e301
author: owner
written: '2026-11-21'
accepted: auto
where:
- .claude/skills/row-owner-loop/references
approach: 'Run the handback checklist mechanically (branch contains sha, ready/ exists, tests ran); classify RESULT/launcher.out
  failures with AK-FAILRULE-1 rules; route harness failures via the session bus to pipeline-mgmt.

  '
acceptance: every subagent hand-back carries a machine VERIFIED/UNVERIFIED stamp and harness failures no longer consume a
  main-thread turn.
non_goals: []
tier: local
grounded:
  at: '2026-11-21'
  blobs:
    epyc-root:.claude/skills/row-owner-loop/references: tree:6e9b8aea536855bb4458119614c05a568190601a
---
