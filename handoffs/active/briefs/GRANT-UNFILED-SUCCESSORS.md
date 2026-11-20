---
schema: epyc.brief.v1
id: GRANT-UNFILED-SUCCESSORS
box_text_sha: e7df4b0f4d749ee6
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:.claude/skills/inference-backlog-scheduling/scripts/queue_status.py
- epyc-root:scripts/coordination/churn/filing.py
approach: 'Table /mnt/raid0/llm/tmp/rtg22-grant-unfiled-20261109.md lists 12 disk-refused rows needing owner successors and
  4 needing cancel confirmation. Step: for each row publish a successor (smaller footprint or after-reclaim) through publish_row.py
  with supersedes, or message the owner session to confirm cancel; file the refusal terminals. Deprioritize means republish
  successor, never WITHDRAWN.

  '
acceptance: grep -q 'GRANT-UNFILED' handoffs/active/engineering-hygiene-backlog.md
non_goals:
- no row withdrawal
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:.claude/skills/inference-backlog-scheduling/scripts/queue_status.py: a53b581b6ea822907905ad9bc5c2262159169870
    epyc-root:scripts/coordination/churn/filing.py: 7f447cb13f38175f59eab8eb3fbcf4f08ecec945
---
