---
schema: epyc.brief.v1
id: KEEPER-GRANT-CAP
box_text_sha: t:12ec474665c1ce3c
author: owner
written: '2026-11-20'
accepted: owner
where:
- scripts/coordination
approach: 'Add a max grant length for non-resumable rows in the grant writer and a warning when estimate has no measured basis;
  test both.

  '
acceptance: python3 .claude/skills/inference-backlog-scheduling/scripts/queue_status.py
non_goals:
- Do not change grants for resumable rows
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/coordination: tree:ece04e5ed8fefdd37703ac3af8525c027b6bc355
---
