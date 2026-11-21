---
schema: epyc.brief.v1
id: AKPL-P2
box_text_sha: t:5a10412196b55356
author: owner
written: '2026-11-21'
accepted: auto
where:
- .claude/skills/row-owner-loop/scripts/row_scaffold.py
- scripts/coordination/rowflow/publish_row.py
approach: 'Build on row_scaffold.py (estimate-from-history default from P0) and publish_row.py; chain rows carry lineage=<cand>,
  supersedes and gate: deps; the gate evaluator (P1) files each link.

  '
acceptance: a management-session candidate (e.g. a C17 fold check) is driven end to end by the chain with the owner only approving
  the publish.
non_goals: []
tier: local
grounded:
  at: '2026-11-21'
  blobs:
    epyc-root:.claude/skills/row-owner-loop/scripts/row_scaffold.py: a524b6353fc864fbabd002960b1a2454c29bd897
    epyc-root:scripts/coordination/rowflow/publish_row.py: ca5e94fa0074523fbfaa57d54be2d34868abae78
---
