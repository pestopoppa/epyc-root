# EvalPerf endpoint runner

`evalperf_endpoint.py CONFIG.json OUTPUT_DIR` runs native EvalPerf for one coder
and one architect arm, then validates the full native results. Run it through a
compute row; unit tests use simulated endpoints and native outputs.

Prepare the EvalPlus environment and datasets before publishing. The upstream
checkout used during implementation was `evalplus/evalplus` commit
`26d6d00bb1fd0fa37f39c99d5290da67891d1c5e`. Its native profiler preflight must pass
on the allocated host. The endpoint URLs must serve the exact configured model
IDs. By default the runner consumes existing endpoints. An arm with `launch`
starts its own endpoint for that arm and stops it before the next arm; it never
reloads the serving stack.

The optional `launch` object contains `argv` (an argument array, without a shell),
`library_dir`, `startup_timeout_s` (1–300), and nonempty `inputs`. Each input is
`{"path": "/prepared/input", "stat": [st_dev, st_ino, st_size, st_mtime_ns]}`
captured **after** verifying the source/build/model identity during preparation.
Include the executable, mapped libraries, every model shard and any template.
Stat revalidation detects replacement; it does not establish build provenance
or GPU residency. Those proofs remain required in the row's native capture.
Pass the reserved loopback port, configured model alias and granted thread count
explicitly in `argv`; the process inherits the row's CPU affinity. Owned URLs
must use `http://127.0.0.1:PORT/v1`. An occupied port is refused before spawn.
Preserve the exclusive bind behavior of the server; the pre-spawn port probe
does not reserve the port against another process racing to bind it.
The runner records the launch command, library path, prepared input identities
and server log per arm, and appends the captured PID to `FILLER_PIDFILE` when set.

The prepared scratch environment at
`/mnt/raid0/llm/tmp/ernie-image-turbo-evaluation/evalperf/venv` passed upstream's
`simple_test_profiler()` on 2026-11-19. Cirron 0.4 imports `pkg_resources`, so it
requires `setuptools<81` in this environment (prepared version 80.10.2).
This preflight opens the counter; it is not a model result or an instruction
count validation on generated code. Datasets and full native compatibility must
still be prepared and checked before publication.

Example configuration (paths and endpoint model IDs must be filled from prepared
inputs, not copied as a runnable row):

```json
{
  "source": "/prepared/evalplus-source",
  "source_commit": "26d6d00bb1fd0fa37f39c99d5290da67891d1c5e",
  "python": "/prepared/venv/bin/python",
  "task_manifest": "/prepared/evalperf-task-ids.json",
  "task_manifest_sha256": "SHA256_OF_JSON_LIST_OF_118_TASK_IDS",
  "n_samples": 10,
  "min_correct": 10,
  "temperature": 1.0,
  "parallel": 1,
  "max_new_tokens": 2048,
  "arm_timeout_s": 14400,
  "arms": [
    {"role": "coder", "model": "EXACT_SERVED_ID", "base_url": "http://127.0.0.1:8083/v1"},
    {"role": "architect", "model": "EXACT_SERVED_ID", "base_url": "http://127.0.0.1:8074/v1"}
  ]
}
```

Ten samples is an explicit bounded configuration, not upstream's default of 100.
Book compute from the prepared endpoints' measured generation cost; the example
deadline is a cap, not an ETA. Both arms use all 118 pinned tasks. No partial
cohort, truncated process result or invalid hardware profile yields COMPLETE.
Validation checks every sample's boolean profile flag, instruction count and
scores, requires the configured native profile count, and recomputes each task's
DPS means from its profiled samples. Unprofiled samples cannot carry efficiency
scores; malformed evidence in an unscored task also rejects the result. These
checks follow the pinned native `evalplus/evalperf.py` output contract.
The native provider does not preserve completion finish reasons, so this runner
cannot distinguish truncation from other correctness failures; preserve native
raw solutions and treat correctness under the declared token cap as the scope.

Output retains per-arm commands, native logs and results, a checkpoint after each
validated arm, and final `RESULT.json`. Correctness uses every sample. Failed or
unprofiled tasks receive no efficiency sentinel. The conditional harmonic mean
of native normalized DPS appears only with at least 30 profiled tasks, following
the handoff's working convention; it is not a ratified comparative protocol.
There is no automatic significance, adoption or role-change verdict.

Each native invocation runs in an owned process group. SIGTERM or SIGINT to the
runner stops that group, escalates to SIGKILL after the cleanup grace period,
and reaps the direct child before propagating cancellation. Failed, timed out or
cancelled arms never produce COMPLETE; a previously validated arm checkpoint
remains on disk.

Before the first measurement row, register this producer in the belief adapter
source table and its owning substrate handoff. Publish only after endpoint
custody, prepared datasets and the native profiler are available for the smoke.
