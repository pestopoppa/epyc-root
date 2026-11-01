# LOOP-49 root components — candidate checkpoint

The source audit from `/mnt/raid0/llm/tmp/ws58-failed-run-audit-20261031/REPORT.md`
is committed in `docs/reports/failed-run-audit-20261031.md`. Lane integration includes
keeper-side qualification run/verify/fingerprint, one canonical shell/Python engine,
READY v2 schema, structured filer outcomes/science scoring, grant-boundary gate and
20 retained-receipt component regressions.

Operator bindings: D1 hard gate, D2 science quota, D3 one canonical allowlisted
engine, D4 disk waits parked and uncounted. Qualification directories, fixtures,
nonce records and `.ended` are immutable retained artifacts. SIGKILL recovery checks
PID plus birth before writing missing terminal custody and never signals a reused PID.

Prepared an **unpinned, live-mode-disabled** v7f review candidate and exact v7e
base/diff in `/mnt/raid0/llm/tmp/loop49-keeper-v7f-candidate/`. Its grant helper
runs the gate immediately before exclusive grant creation, binds concrete CPU/GPU
regions to the qualified manifest, and rechecks launcher PID birth. The gate copy
is self-contained and candidate custody hashes were refreshed. Its keeper tick now
checks `ps` state plus PID birth and immediately records `.ended` for dead launchers.
It does not alter the running keeper; live writer qualification/integration is pending.
Region-binding code and tests are committed as `4554e1d0d`.

Validation checkpoint: `python3 -m unittest tests.coordination.test_loop49_keeper_gate_regions tests.coordination.test_loop49_engine_wrapper_unit -v` (10 passed); Python compilation, `bash -n scripts/coordination/filler_run14.sh`, and `git diff --check` passed. Candidate v7f static tests passed 7/7 and its `SHA256SUMS` verified. No qualification run was attempted because no explicit compute grant was issued. The 20 retained-receipt suite remains grant-gated and unexecuted. GitNexus root index is unavailable/stale; the new gate function has no indexed callers (UNKNOWN risk), and manual review found only additive integration hooks. No runtime/deployment or science claim is made. [no-belief: implementation checkpoint; no measurement result]
