# 2026-11-21 pipeline-mgmt (overnight 2026-11-20 night to 2026-11-21)

Operator ask: keep AutoKernel compute flowing. This wrap-up (wrap 4) records the keeper and rowflow fixes, the disk reclaim and the lessons. All commits below are pushed.

## Keeper and rowflow fixes

- `466e6b97a` `rowflow.py release` verb; `.ended` grants are never holds.
- `5dc723189` drain priority inversion: a rank-110 host drain held q0-q2 against rank-22/35/40 rows. `drain_outranks`, `rank_fragment_ok` and build-held rows now count in `drain_blocker`.
- `ee7a5897b` build-wait records need a live pid; 30-min TTL cap (a pid-null record had held q0-q2).
- `39e5e2f59` any-of regions are a hard allow-list (lsa-e2e-bound-r1 had been granted q0 outside any-of q1,q2).
- `ee68ff642` owner withdrawals filed by the sweep are labelled WITHDRAWN-FILED (source of three false-alarm reports).
- `e3b776c20` q3-pocket build claims (`--cpus 72-87`) never book 88-95.
- `d97d50518` deferred-drain cap is S, not now+2h.
- `a15b0e09f` idle build claims auto-released after 30 min under 5%.
- `f99820820` GPU smoke batch is no longer blocked by DISK-PAUSE.
- `263ff22b1` keeper vault churn (basename collision) created ~47G/day of superseded copies in .trash-reap and caused DISK-PAUSE from 05:21Z. Deployed with operator approval; keeper re-pinned (5d00f437) and restarted 10:51Z.
- `156faf1fd` caps never go below min_window+300. Deploy in progress at checkpoint.
- `b49540695` publish_row no longer trips the NIB2-108 hook, plus a deploy scan gate.
- scratch_lease root split.
- Keeper v13 re-pinned twice, with operator approval.

## Disk

- Operator approved purging 3,321 superseded trash entries: 162G to 204G free, DISK-PAUSE lifted.
- Operator approved the scratch reclaim (225 stale tmp dirs, 85 clean worktrees, both trash roots): 283G free.
- 25G of root-owned entries remain in .trash and need operator sudo.

## Lessons

- `deploy_rowflow.sh` takes its replay harness from the invoking tree: deploy from a fresh origin/main worktree, not /workspace (box filed: DEPLOY-FROM-REF).
- Never chain worktree cleanup after a push (2 commits were lost and redone).
- No pgrep by name: a self-matching wait loop hung a deploy.
- The alarm script needed three fixes.

## Still open

- `quiet_guard_regions` spec field (contention-guard rows show as UNDERUSED): being built, not landed at wrap time (box filed: KEEPER-QUIET-GUARD).
- 4 pre-existing handoff_sessions test failures.
- The taskflow canary is paused for AutoKernel compute (RTG-100 row Next action already says so).
