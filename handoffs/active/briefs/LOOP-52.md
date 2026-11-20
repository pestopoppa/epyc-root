---
schema: epyc.brief.v1
id: LOOP-52
box_text_sha: 615ae1174ede5d38
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:.claude/skills/inference-backlog-scheduling/scripts/queue_status.py
- epyc-root:scripts/coordination/rowflow/publish_row.py
approach: 'Done when queue_status.py shows >=2 runnable READY rows per bin per worker. Step: read the current queue_status
  output, name the bins below 2, and publish (or request through the owner sessions) enough rows through publish_row.py (epyc.row.v3);
  this is a backlog-readying task per the never-stop-readying rule. Acceptance parses the READY counts.

  '
acceptance: python3 .claude/skills/inference-backlog-scheduling/scripts/queue_status.py | grep -i ready
non_goals:
- no padded estimates
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:.claude/skills/inference-backlog-scheduling/scripts/queue_status.py: a53b581b6ea822907905ad9bc5c2262159169870
    epyc-root:scripts/coordination/rowflow/publish_row.py: f71787bda4ff97f509d88afd008069379d1d6500
---
