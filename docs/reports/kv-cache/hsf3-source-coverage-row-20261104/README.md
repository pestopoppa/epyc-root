# HSF-3 uncaptured-source census row (CPU, read-only)

Status: row published after its synthetic four-CPU smoke passed; the full census is pending. No inference, database writes, service changes, or result publication is claimed.

Purpose: price coverage in the HSF-3 progress-event and SQLite checkpoint sources not covered by the 2026-11-04 serving-call and dispatch snapshots. Output is aggregate-only. It must not contain session IDs/hashes, record IDs, timestamps, names, task text, prompts, or raw rows. This row cannot establish a completion-to-enqueue pair, client brand, return curve, or HSF-3 completion.

Read [PUBLISH_SPEC.md](PUBLISH_SPEC.md) before any run. Defaults are the bounded source locations identified in `handoffs/active/kv-cache-program.md` HSF-3. No tap source was located; tap is out of scope and must not be searched for or supplied speculatively.

The progress reader parses and hashes the same initial-frontier bytes, skips incomplete trailing records, refuses files changed during read, and accounts for oversized records. SQLite runs in a read-only transaction that may see WAL state; DB/WAL stat changes cause refusal, and the output does not claim a logical-snapshot content hash. The launcher is CPU-only, low-priority, one-process, and capped at 10 minutes.

This is preparation only, not permission to run a live census, publish output, or change HSF-3 status.
