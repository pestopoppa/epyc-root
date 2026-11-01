# Refactor-owned stale launcher withdrawal

Date: 2026-11-01 UTC

The retained 00:57Z fleet audit found 87 STALE-ARMED records resolving to 87 distinct rows; 0 were dispatchable at emission. The exact refactor-owned scope was 20 rows (19 owner=`codex-refactor-01a16fc3`, one owner=`refactor`). All 20 recorded launcher PIDs were absent at audit time. The complete pre-change inventory and exact IDs/PIDs are in `PRE-WITHDRAWAL-AUDIT.md` and `PRE-WITHDRAWAL-QUEUE.json`.

The 19 dead-launcher rows were changed to CANCELLED in `compute-flags/FILLERS.md`. The recent C6 IQKFA remainder row was instead moved to BACKLOG and held with the reason `LOOP49 + RSS correction (redeclare >=12 GiB before re-arm)`, preserving the measurement for a qualified successor. Its former quarter-queue entry was removed, exact launcher PID 2544834 was SIGTERM'd after matching the recorded PID birth and argv, and process absence was verified. The temporary exact-operation HOLD was removed after the changes were complete; no other HOLD files remain.

A fresh `queue_status.py --owner codex-refactor-01a16fc3 --json` check at 01:08Z reports 0 STALE-ARMED rows for this owner and C6 in BACKLOG. Other owners' stale rows were not touched. The new yarn-oolong stale row observed after the original audit was also left untouched. This action does not claim the fleetwide ~80 rows are resolved.

No launcher, result, grant, source, or evidence file was deleted or renamed. The captured queue snapshots are retained as audit evidence.
