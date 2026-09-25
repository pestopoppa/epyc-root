# 2026-09-25 — Vidya v10 KV-quant reader and planner consumption

The v10 KV-quant producer had a write-time capture hook, but no Vidya read-side adapter or
ingest name. A dispatched subagent implemented the strict reader and the owning session
reviewed and wired a separate read-only AutoPilot planner block.

- `scripts/vidya/adapters/kv_quant_27b_v10.py` pins the research producer bytes, calls its
  `validate_row()`, refuses a whole malformed sidecar, rehashes the scored summary, and projects
  the producer's rows through the shared `ClaimTuple` ladder. K and V buffers remain separate;
  fixed `-fa on`, depth, and bench-only scope remain visible.
- `cli.py ingest kv-quant-27b-v10-measurement` discovers producer sidecars. The read-only
  `kvq_planner_context.py` renders only a complete 12-row ingested run with folded grades.
  AutoPilot's planner receives that bounded block separately from settled experimental ground.
  AutoKernel's active `loop/run.py` → `AgentPlanner.propose()` path reads it only for the
  matching Qwen3.8-27B-Q8_0 GPU target, with bench-only and no-promotion limits in the prompt.
- The saved September 22 sweep directories contain no `belief_measurements.jsonl` sidecars.
  A default-corpus dry run matched and projected zero rows; the live planner block explicitly
  reports unavailable. No historical evidence was backfilled. The first complete post-hook
  sweep still needs to be run by its stack-down owner and ingested (VB-KVQ-V10-INGEST).

Validation: 127 root Vidya adapter/ingest/ClaimTuple tests, 58 AutoPilot bridge/prompt
tests, and 105 AutoKernel actor tests passed. `make gates` in the orchestrator exited 0; optional shellcheck, shfmt,
markdownlint and NextPLAID checks were unavailable on this host. No production process was
reloaded.

## AutoPilot decision receipt follow-up

The Vidya KV-quant lookup now emits a structured manifest alongside its existing text:
availability, run, as-of frontier, fold state hash, and the 12 claim IDs. AutoPilot reads
the two together once per planner turn and passes the same snapshot to the planner
coordinator. Its existing archive decision row records the trial ID, exposure manifest,
and claim IDs explicitly declared in `autopilot_rationale`; a shown claim is never
counted as relied on by default. Invalid or incomplete manifests fail closed. The
planner prompt names claim IDs and asks for an empty list when they did not influence
the action. No Vidya grade or promotion rule changed. No live KV-quant evidence exists
yet, so this was verified with synthetic ingested records and orchestrator unit tests.

Validation: 8 focused root Vidya tests and 192 orchestrator unit tests passed; Ruff and
Python compile checks passed. No inference process was reloaded.

## Wrap-up state

The reader and both planner paths are implemented. Live decision use awaits the first
successful post-hook sweep; the September 22 files contain no producer-authored sidecar
and cannot be backfilled. `VB-KVQ-V10-INGEST` tracks that run and ingestion.
`VB-KVQ-V10-RECONSIDER` tracks automatic review of archived AutoPilot decisions after
a correction. The AutoKernel agent owns its remaining ingestion and planner receipt path.
