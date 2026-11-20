---
schema: epyc.brief.v1
id: LOOP-41
box_text_sha: 0725a540d787d81e
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/system/worktree_gate.py
- epyc-root:scripts/system/worktree_reaper.py
approach: 'Re-run worktree_gate.py after the blocked worktrees age out (about 2026-11-20 to 11-27) and remove only the clean+landed
  ones via the reaper, ledger WORKTREE-WRAP-20261030.md. First step: today''s gate run and a table of which of ~67 are now
  removable. No force removal.

  '
acceptance: grep -q 'LOOP-41.*removed' handoffs/active/engineering-hygiene-backlog.md
non_goals:
- never git worktree remove --force
- no removal of dirty or unlanded trees
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/system/worktree_gate.py: 78f3fe4ce851b1201045a6e0b2e09eaf15bddae6
    epyc-root:scripts/system/worktree_reaper.py: e5b9ecd195cd4ef81dd906a167c7e47f7d2f4505
---
