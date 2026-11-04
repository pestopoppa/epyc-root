# HSF-3 source-coverage census successor (r3)

**Purpose:** repeat the bounded aggregate-only coverage census of progress events and the chat checkpoint database after `kvu-hsf3-source-coverage-r2-20261104` stopped at rc75 `disk-floor` before its full census result. This prices the documented sources only. It cannot produce inter-call gaps, class breakdowns, a return curve, or HSF-3 completion. No inference, service change, database write, raw-row output, or publication is authorized by this preparation.

## Inputs and custody

- Progress JSONL: `/mnt/raid0/llm/epyc-orchestrator/logs/progress/*.jsonl`. The pinned census reads each file only to its initial `fstat` size frontier, hashes and parses the same bytes, skips incomplete trailing records, skips lines over 1 MiB, and refuses incomplete or changing frontiers.
- Checkpoint database: `/mnt/raid0/llm/epyc-orchestrator/orchestration/repl_memory/sessions/sessions.db`. The pinned census uses SQLite `mode=ro`, `query_only`, and one read transaction. Main and WAL stats are compared before and after the query; any change rejects the result. This is per-source snapshot stability, not a cross-source atomic snapshot or logical database content hash.
- Tap remains out of scope; no source path is searched for or inferred.
- The only runtime code is the regular-file copy `census.py` in this private r3 scratch, byte-identical to the pinned r2 census and sealed by SHA-256 in the launcher. No checkout source is used.

No source identifiers, session-ID hashes, record IDs, timestamps, names, task text, prompts, or raw rows may be emitted. The existing census output is restricted to aggregate counts, schema-presence booleans, source-class custody metadata and interpretation. Do not publish `RESULT.json` verbatim; any later filing requires separate review and an aggregate summary.

## Execution and output separation

The launcher registers `kvu-hsf3-source-coverage-r3-20261104` with `filler_run15.sh`. Its publisher smoke runs the pinned census against live sources and writes only to the externally supplied `FILLER_DRYRUN_RESULT_PATH`; this smoke snapshot is not first progress and is distinct from the full result. At grant, one bounded, low-priority census runs with a 10-minute timeout and writes exclusively to this packet's new `RESULT.json`. Output creation is exclusive; missing progress input, unstable/incomplete sources, query failures, and collisions are errors.

The completed result must match schema `hsf3_source_coverage_census.v1` and mode `read_only_aggregate_only`. The original decision rule remains: source coverage only; no joins, proxy timestamps, gap-pair or client-class inference. HSF-3 still requires at least 50 properly keyed/classed sessions per reported basis in each of two independent windows. No percentile, TTL, or completion claim follows from this census.

## Preparation boundary

This packet contains the JSON publication row, publication spec, launcher, and pinned regular-file census copy. No census, synthetic smoke, publication, handoff edit, or compute was performed. Existing synthetic controls remain in the r2 packet and are not treated as live source evidence.
