# EvalPerf endpoint runner

`evalperf_endpoint.py CONFIG.json OUTPUT_DIR` runs native EvalPerf for one coder
and one architect arm, then validates the full native results. Run it through a
compute row; unit tests use simulated endpoints and native outputs.

Prepare the EvalPlus environment and datasets before publishing. The upstream
checkout used during implementation was `evalplus/evalplus` commit
`26d6d00bb1fd0fa37f39c99d5290da67891d1c5e`. Its native profiler preflight must pass
on the allocated host. The endpoint URLs must serve the exact configured model
IDs. The runner does not start or reload endpoints.

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
The native provider does not preserve completion finish reasons, so this runner
cannot distinguish truncation from other correctness failures; preserve native
raw solutions and treat correctness under the declared token cap as the scope.

Output retains per-arm commands, native logs and results, a checkpoint after each
validated arm, and final `RESULT.json`. Correctness uses every sample. Failed or
unprofiled tasks receive no efficiency sentinel. The conditional harmonic mean
of native normalized DPS appears only with at least 30 profiled tasks, following
the handoff's working convention; it is not a ratified comparative protocol.
There is no automatic significance, adoption or role-change verdict.

Before the first measurement row, register this producer in the belief adapter
source table and its owning substrate handoff. Publish only after endpoint
custody, prepared datasets and the native profiler are available for the smoke.
