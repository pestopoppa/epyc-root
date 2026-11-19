# 2026-11-19 pipeline-mgmt (overnight 11-18 evening to 11-19 morning)

## Commits (all on origin/main, deployed)
- 79ca2ec6d dispatcher: auto-unpark cap counts only consecutive fruitless unparks; a productive turn resets it.
- 0f7d48e89 dispatcher: EVENT-STALE-DROP; filed-and-recorded run-end events purged before resume/auto-unpark (240 of 549 dropped on first pass).
- 3e9f5aa71 scoped operator-ratify releases (`rows` scoping, UNSCOPED warning, `allow_unpark`).
- 1f6209ba5 / 4d25fe3c0 rowflow `smoke_cpus` and GPU-q3 guard (earlier; now recorded).

## Registry ops (data only)
- 69 sessions parked 11-17 re-tagged auto-eligible (operator approved).
- 9 autokernel/autopilot sessions operator-gated (dedicated sessions own that work). A code_only mode was drafted and abandoned.

## Environment
- /workspace synced to origin/main (operator approved; backups /mnt/raid0/llm/tmp/pm-wsync-20261119/). guard_production_kernel hook now live. Local-only uncommitted settings.json edit (AskUserQuestion hook) left uncommitted.

## Measured outcome (22:35Z to 08:45Z)
- 347 Codex turns: 155 productive, 192 NOOP (mostly stale-event acks, motivating EVENT-STALE-DROP).
- Refused spawns 177 (prior 24 h) -> 0. 60 auto-unparks; net-progress park fired 8x; FRESH-INSTEAD-OF-RESUME 2x.
- Codex idle 00:20-02:00Z until the re-tag.

## Handoff edits (churn-pipeline.md)
- Ticked: PROD-KERNEL-HOOK-NOT-LIVE.
- Added done: HS-UNPARK-CAP-FRUITLESS, HS-EVENT-STALE-DROP, HS-SCOPED-RATIFY-RELEASE, ROWFLOW-SMOKE-CPUS-AND-GPU-Q3-GUARD, REGISTRY-RETAG-AND-AK-GATE.
- Added open: KEEPER-RESIDENT-TENANT-ACCOUNTING, PLACEMENT-DECLARE-ONLY-COST-BASED.

## Coordination
- W1 upstream PR failed (no CreatePullRequest permission): AutoKernel's box, untouched. AK ratify bundle fixed (a60ac5edc), awaiting operator signature.

## Wiki
- Manifest check only: 57 stale sources (21 handoff-active, 28 progress, 8 docs); 30 added, 27 changed, 0 removed. Compile not run (large).
