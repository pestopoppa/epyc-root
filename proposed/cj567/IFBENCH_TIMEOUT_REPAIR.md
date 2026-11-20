CJ-6a capture timeout repair (2026-11-20)

The v7 verdict (`docs/evidence/ifbench-cj6a-v7-20261120/verdict.json`,
blob available through this change's git object) binds the historical worker and
server log. It records 1,337 decoded tokens at 1.12 tokens/sec before the fixed
1,200-second client timeout. This supports a capture-budget mismatch diagnosis,
not a benchmark score or proof that every request would complete.

`ifbench_timeout_repair.repair(source_bytes)` renders a repair only for worker
SHA-256 `2a29128dfdb6282a0006369597399d12a6c57c4f80d924b845a701d4395ced62`.
It changes the admission guard and transport together and records the selected
request budget in each future exposure. The accompanying
`ifbench_capture_budget.py` must be installed beside a future rendered worker.
Rendering neither writes the source nor executes it. No running row or sealed
runtime was changed.

For 4,096 tokens, a prospective planning floor of 0.5 tokens/sec plus 120 seconds
for prefill gives an 8,312-second request budget. Thirty seconds of cleanup must
also fit strictly inside the worker's existing deadline (which already ends
20 seconds before the grant). Smoke keeps its 120-second transport limit and
now reserves cleanup too. The planning floor is an explicit engineering
assumption, not a measured lower bound. Slower requests can still time out;
transport errors remain UNKNOWN and do not trigger a retry. The parent stop,
server-death, grant-loss, and no-redraw guards remain in place.

Offline validation:

    python3 -m unittest discover -s proposed/cj567 -p test_ifbench_capture_budget.py -v

Six tests passed, including a fake transport completing a 4,096-token response
at the previously observed rate after the old timeout, a request that exceeds
its budget with exactly one transport call, exact deadline/reserve boundaries,
and integration against the SHA-pinned historical worker. Integration compiles
and executes its repaired nested request function without starting the worker,
checks admission before exposure, and preserves every no-redraw path. The
pinned integration test skips on systems without the historical worker; it ran
and passed here. No generation or cohort exposure occurred.

Prompt 36 remains UNKNOWN, the terminated cohort stays closed, and strict/loose
scores remain UNKNOWN. This repair is ready for a separately declared future
exposure protocol; it does not authorize reusing or redrawing the old cohort.
