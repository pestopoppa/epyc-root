# HSF-3 source-coverage publication spec (task8)

**Purpose:** price whether progress events and the chat checkpoint database can supply any HSF-3 input. This is a bounded read-only coverage census. It cannot produce inter-call gaps, a class breakdown, a return curve, or HSF-3 completion. No inference, service change, database write, raw-row output, or publication is part of the run.

## Inputs and boundaries

- Progress JSONL: `/mnt/raid0/llm/epyc-orchestrator/logs/progress/*.jsonl`; each file is read only through its initial `fstat` size frontier. The scan hashes and parses the same byte stream; incomplete trailing records are not parsed. Files changing during the read are rejected. A line over 1 MiB is counted as oversize and skipped.
- Checkpoint database: `/mnt/raid0/llm/epyc-orchestrator/orchestration/repl_memory/sessions/sessions.db`; SQLite `mode=ro`, `query_only`, one read transaction. SQLite may include WAL state. Main and WAL file stats are checked across the query; any change rejects the result. Custody reports stat stability only, not a hash of the logical database snapshot.
- Tap is out of scope: no source path was located. The census must not search for one or accept a speculative path.

No source identifiers, hashes of session IDs, record IDs, timestamps, names, task text, prompts, or raw rows may be emitted. JSON output contains only aggregate counts, schema-presence booleans, source-class custody metadata, and the stated interpretation.

## Execution

The registered `launcher.sh` runs through `filler_run15.sh`. Its smoke branch is selected inside `job.sh` and uses only disposable JSONL/SQLite fixtures; it writes a numeric `progress.files` record to `FILLER_DRYRUN_RESULT_PATH` for rowflow progress accounting. At grant, `job.sh` runs one Python census process under a 10-minute timeout, low CPU priority, and idle I/O priority, writing the aggregate to the new `RESULT.json` path. The census refuses an empty progress glob, incomplete or changing source frontiers, DB/query failures, and output collisions.

Review `RESULT.json` for the v1 schema and aggregate-only allowlist before any filing. Never publish it verbatim if it contains fields beyond this allowlist; publish a short aggregate summary and this method reference only.

## Interpretation / publication gate

Counts are source-coverage pricing only. Progress events do not independently provide a model completion, next enqueue, role, or client class; checkpoint schema/counts do not establish those fields or valid pair joins. Do not infer proxy timestamps or join the sources. Any result with no complete HSF-3 field set remains a coverage gap and routes as already specified by the handoff; no percentile or TTL conclusion follows.

Synthetic-only validation verifies the aggregate schema, scalar/malformed JSON accounting, oversized-line accounting, empty-input refusal, read-only SQLite access, and privacy of output. It must not use live source paths. A granted census does not authorize publication or change HSF-3 status.
