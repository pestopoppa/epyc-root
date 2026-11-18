# CF-3c native REPL task-suite failure

**2026-11-18 · CANDIDATE · bench.** The first shard stopped when the native graph child exited with code `1`. It completed **6 of 24** scheduled cells, below the protocol’s all-24 coverage requirement. Seven cells were attempted, including one instrument `UNKNOWN`, and 17 were unattempted. The launcher wrote `native/PARTIAL.json` with `coverage_complete: false` and `server_exited: true`. The official `native/RESULT.json` was absent. [Task-suite protocol](../design/cf3c-task-suite-protocol-20261118.md)

## Failure and interpretation

The seventh attempt, `task-06` (`longcot_mini_18/r0/A0`), failed on frontdoor REPL turn 2 with `selected history missing from native request`. The log records an in-band infrastructure error and then `ValueError: incomplete graph/tokenizer capture: ['selected history missing from native request'], requests=2`. The log also records an earlier inference-lock watchdog force-release; these records do not establish a causal role for that watchdog.

Source and captured-request review identifies a capture-check mismatch: the selected history ended with newlines after `Error:`, while the pinned streaming chat adapter calls `user_content.strip()` before constructing the native message (`src/backends/llama_server.py:1881` at orchestrator `12afe2858f9dbd4691447926d6cf1864de64348c`). The guard required the full untrimmed render as a substring. A repair must accept that exact outer-whitespace transformation at the message boundary while continuing to reject changed substantive history. This is an instrument failure, not evidence of a model or policy failure.

All six completed cells belong to the first task. A0, A1-k4, A1-k8, A1-k12, A2 and A3 each scored 1/1 on observed answers, with zero policy activations. Those observations cover one paired task with inactive policies. The incomplete shard supports no arm ranking, scaling-futility determination or adoption conclusion.

The [retained partial summary](cf3c-task-suite-failure-20261118.json) preserves the native per-arm denominators, cost completeness and observed token lower bounds, together with the original partial digest. It is an extract of the recorded run, not a reconstructed measurement warrant.

## Evidence custody

The files below are relative to `/mnt/raid0/llm/tmp/delegation-context-preassembly/cf3c-suite/`. The trial log digest also matches the entry in the partial record’s window manifest.

Before filing the failed row, the complete native tree, sealed packet and earlier qualification receipts were preserved under `/mnt/raid0/llm/tmp/delegation-context-preassembly/cf3c-suite-r2/prior-failed-attempt/`. This keeps the original failed candidate distinct from the repaired instrument. The owner filed coverage FAIL and acknowledged alert `9576517981e8d25dc9e98326`. A successor repeats the frozen tasks and seeds with changed capture instrumentation; its observations must remain separate rather than replace or pool with these partial outcomes.

| Raw file | SHA-256 |
| --- | --- |
| `native/PARTIAL.json` | `5ae7ad2971a1b4cf6a962cc93f991a705ebae461629725ade2eb83413eecc471` |
| `native/window-pn01hzws/task-06/trial.log` | `78843e03ff01df402a72e401cca82d5d699bec10d6c60be610f2f4050596645d` |
