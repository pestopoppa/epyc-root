# HSF-3 source-schema mapping and NI32 proposal — 2026-10-05

This is a read-only schema mapping against the published NI10 producer/adapter
at root commit `d61ae218f4b8e8c9d14e1e8361eabd740c745534` and orchestrator
commit `b01ab9933c289a7c5a361050e153f5e486791acd`; app source inspection used
the current orchestrator checkout at `300cf5817edccc4f82089f0faa477828496068b6`.
No log payloads or SQLite rows were read.

The current producer accepts `epyc.orchestrator.serving_call.v1` records. It
binds session identity from `caller.trace_keys.x_session_id` or
`caller.session_id`, role from `role`, explicit class from
`caller.client_class` (otherwise `unknown`), completion from `ts_end` plus
`outcome=ok` and `dispatched=true`, and the next call's exact admission time
from `queue.enqueue_ts_epoch`. Its `staging_proxy` fallback is separately
labelled and computed from `ts_start - queue.pre_dispatch_wait_ms`; it is not
an exact enqueue. Other JSONL schemas are not converted into gap rows. The
existing tap-key counter only records non-serving-call records carrying
`request_keys.x_session_id` as keyed without native enqueue.

The three other HSF-3 sources do not independently provide the full pairing
contract:

- Structured tap events emit `event`, `ts`, `ts_epoch`, and the tap metadata,
  including `role` and request keys. Start/end event times are present, but the
  event schema shown in `runtime/inference_tap.py` does not carry the serving
  record's backend-admission timestamp or explicit client class. A tap-only
  extraction therefore cannot claim exact next-enqueue gaps or class-specific
  samples.
- Progress entries serialize `event_type`, `task_id`, `timestamp`, agent role
  and `data`. Session lifecycle events put `session_id` in `data`; terminal
  task entries have completion time but do not bind an explicit session ID in
  the entry contract. Neither shape gives the same call-level enqueue plus
  explicit client class used by the serving-call adapter.
- `/chat` checkpoints carry `session_id`, `created_at`, and `trigger` (plus
  checkpoint state). Those timestamps describe checkpoint events, not backend
  call completion or enqueue, and the record has no role or client class.

**NI32 proposal — assert source boundaries before any source integration.** Add
small synthetic schema fixtures for tap start/end JSONL records, progress
session/terminal entries, and checkpoint-shaped records. Assert which current
producer counters classify tap-keyed records, that the other schemas are
counted as non-native, and that none can produce a gap pair or `ClaimTuple`
without the required native completion/enqueue/session/role/class bindings.
Keep the `serving_call.v1` exact-enqueue and labelled-proxy fixtures as positive
controls. Do not parse production tap files or the SQLite database, infer
missing joins, change the source class/grade, or report distributions from
these fixtures. Any future use of these sources needs a separately bounded
read/census plan after native field linkage is demonstrated.

Relevant source files: `scripts/harness/session_gap_measure.py`,
`scripts/vidya/adapters/session_intercall_gap.py`, orchestrator
`src/runtime/inference_tap.py`, `src/llm_primitives/inference.py`,
`orchestration/repl_memory/progress_logger.py`, `src/session/models.py`, and
`src/session/sqlite_store.py`. This proposal does not close HSF-3 or its
later-window replicate.
