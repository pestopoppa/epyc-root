---
schema: epyc.brief.v1
id: ROWFLOW2-SHADOW-WEEK
box_text_sha: 451fe7822bae689e
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/coordination/rowflow2/run_shadow.sh
- epyc-root:docs/design/rowflow2-20261105.md
approach: 'Question: does rowflow2 decide the same as the live keeper for 7 consecutive days? Run run_shadow.sh continuously
  (restarted 2026-11-09; churn_up starts it at bring-up), review each diff-<date>.md in /mnt/raid0/llm/tmp/rowflow2-shadow/,
  classify every disagreement, close the design-doc gaps (stop-file check, live CLI, filler successor, D11/D12, unmapped rows)
  against the switch-over criteria. Stop when 7 consecutive clean days or a disagreement class blocks. No tokens beyond review.

  '
acceptance: python3 .claude/skills/inference-backlog-scheduling/scripts/queue_status.py >/dev/null && ls /mnt/raid0/llm/tmp/rowflow2-shadow
  | grep -c '^diff-'
non_goals:
- no cutover in this box
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/coordination/rowflow2/run_shadow.sh: 1aebac65901a36cf4f5270b18442f14b421ba944
    epyc-root:docs/design/rowflow2-20261105.md: b6189f226ff8fc5200cdad96ae695f62cbed2187
---
