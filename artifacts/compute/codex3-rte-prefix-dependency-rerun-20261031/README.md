# RTE-Prefix imported-dependency check — 2026-10-31

This is a narrow integration recheck of the two native-entry controls already present in the accepted RTE harness. It is not a separate task tick, model A/B, semantic-quality result, or measurement claim.

## Source binding

- Harness and tests: orchestrator commit `b85b44f12ec857fc0249bc956e239feadfe92ca4` (the task's final implementation commit). The focused test source and `scripts/benchmark/bench_repl_prefix_stability.py` in the isolated fixture match the exact Git blob SHAs from that commit.
- Parent application source: `bfa87454f482156b27b6e944af95bde46ddf4441`, parent of the RTE commit. The only changed imported modules across the prior test fixture binding (`2f130ee6721eee1dd37ba82e9781233b739f1669`) were overlaid from this parent: `src/repl_environment/context.py` and `src/trace/dependency_log.py`. Both files match their exact Git blobs from `bfa8745`.
- The context change observes native direct tool dispatch; the dependency-log change refuses composite-wrapper aggregation. The native-entry control runs plain Python output and a ZeroDivisionError with no REPL tool call, while the companion control exercises slot receipts and metric refusals. These tests were rerun against the updated imported-source fixture.

## Result and resource envelope

Exactly these two existing tests passed:

```text
tests/unit/test_bench_repl_prefix_stability.py::test_native_turn_capture_executes_code_and_retains_live_context
tests/unit/test_bench_repl_prefix_stability.py::test_slot_and_metrics_fail_closed
```

Result: **2 passed** in 1.56 seconds. Pytest emitted two environment warnings (unknown `asyncio_mode` option from the isolated test dependency bundle; OpenTelemetry `SelectableGroups` deprecation). The supervisor exited 0 after 2.477 seconds, sampled 25 times, measured 131,440,640 bytes peak aggregate RSS, reported no failure, and confirmed child cleanup. RSS is sampled and may miss transients.

Qualified run used `OMP_NUM_THREADS=1`, `PYTHONDONTWRITEBYTECODE=1`, plugin autoload disabled, exactly two logical CPUs (148–149, allowed +24 relocation plus +96 SMT placement for physical pair 28–29), and the original `flock /mnt/raid0/llm/tmp/compute-flags/prep-locks/28-29.lock`. The bounded 300-second lock wait acquired the original lock; live R6 admission passed. No model or GPU was used.

Raw pytest output is gzip-compressed with metadata disabled, preserving the exact bytes while keeping trailing spaces out of the text diff; supervisor output is stored verbatim. Hashes of the control and runner outputs and the exact source files are in `SOURCE-BINDINGS.txt`. A separate two-test pass under the relocated `52-53.lock` is retained in private scratch as supplementary only; it is not the R6 acceptance record. The initial invalid-interpreter launch is likewise preserved privately, not represented as a test result.
