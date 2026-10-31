PROPOSED — R23-30

Fresh source: research origin/main, exact base file saved as boundary.before.sh.
Patch: r23-30.patch; new test: scripts/benchmark/test_boundary_20260901_drain.py.
The confirm drain default is 7 workers × 1200 seconds = 8400 seconds; explicit BOUNDARY_KILL_WAIT_S still wins. The dry plan and stop log expose the grace. Invalid derived-budget inputs refuse before any signal.

Validation: baseline-test.log records 7 failed / 3 passed (before final real-child test addition); candidate-test.log records 11 passed. bash -n passes. Tests exercise the original step1 with a virtual 87-minute drain, bounded explicit escalation, survivor refusal and wrong-identity refusal. The additional real-child test sends TERM only to the captured child PID, runs the original /proc checks, waits and proves that PID absent. No runtime service/kernel/store changes.

Owning handoff draft (MAIN applies after code push):
Replace the ORIGINAL R23-30 unchecked line with [x] ✅ 2026-10-31, append code SHA plus scripts/benchmark/test_boundary_20260901_drain.py (11 passed), scratch candidate-test.log, and [no-belief: software-contract-fix]. Body note: configurable worker×measurement grace defaults to 140 min instead of 15 min, preserves explicit deadline and verified-dead stop gate. Do not count before code is merged.

Progress shard draft:
R23-30 boundary confirm drain now budgets serialized lanes (default 7×20 min) and exposes its resolved grace. Eleven offline tests passed, including observed-87-minute virtual drain and real owned-child exit verification. Baseline failed seven new regression cases. Code commit: PENDING LANDING. [no-belief: software-contract-fix]
