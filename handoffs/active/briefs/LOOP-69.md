---
schema: epyc.brief.v1
id: LOOP-69
box_text_sha: 52c32aa81acbad32
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:research/refactor-audit-2026-10/packages/wave1.json
- epyc-orchestrator:scripts/autopilot/operator_candidates
approach: 'Adversarial review then merge of refactor/scripts-cleanup (O6). First finish the A5-11 WIP commit and run the suites
  covering the A5-01/A6-19/A5-05 deletions; confirm each deleted script is unreferenced (grep including cron/shell and cross-repo)
  and that one-shot ratifiers deleted were applied (artifacts/operator). Reviewed variant refactor/scripts-cleanup-reviewed-01a16fc3
  (27 ahead).

  '
acceptance: cd /workspace/repos/epyc-orchestrator && git merge-base --is-ancestor refactor/scripts-cleanup-reviewed-01a16fc3
  origin/main
non_goals:
- no edit of scripts/server/orchestrator_stack.py (live path)
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:research/refactor-audit-2026-10/packages/wave1.json: bb376c30536182d94ec0a5257025cef934db2098
    epyc-orchestrator:scripts/autopilot/operator_candidates: tree:277ee374f3db3675da34fb4e96d121ef103d1361
---
