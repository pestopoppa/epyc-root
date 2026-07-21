# Reviewer Control Plane — Trace Materialization & Durable Execution (H1)

**Status**: active — M1 "observable" milestone owner; no reviewer metric is computable until this lands
**Created**: 2026-07-16 (Architect→Reviewer control-plane series; see index)
**Categories**: agent_architecture, tool_implementation, benchmark_methodology
**Index**: [`reviewer-control-plane-index.md`](reviewer-control-plane-index.md)
**Related**: [`evidence-plane-event-sourcing-and-narrative.md`](evidence-plane-event-sourcing-and-narrative.md) (overlap audit TM-6), [`reviewer-typed-artifacts.md`](reviewer-typed-artifacts.md) (consumes trace categories), [`reviewer-calibration-accounting.md`](reviewer-calibration-accounting.md) (ledger lives in this DB)
**Repo**: all implementation in `epyc-orchestrator` (`/mnt/raid0/llm/epyc-orchestrator`)

## Objective

Materialize the scaffolded-but-never-built unified trace store and make every review-plane decision a durable, replayable, queryable event — including durable cross-restart resume for review gates. This is the report's "trace capture first" ground floor: without it, reviewer calibration (H4) has no substrate.

## Thesis

`src/trace/store.py` (SQLite+FTS5, append-only, DECISION/VERIFY/SAFETY_VERDICT categories) already exists but `data/trace/events.sqlite` was never materialized, and the store is pull/offline (file-tailing ingesters). Meanwhile `persistence.py::SQLiteStatePersistence` is **write-only** (`load_next()` always returns None — it never rehydrates), so no long run survives a process restart. Both gaps close with mostly-existing machinery: build the DB, add REVIEW_* categories + a live `emit()` push path, and wire the **already-declared LangGraph dependency** (`pyproject.toml`: `langgraph>=0.2.0`, `langgraph-checkpoint-sqlite>=2.0.0`; dormant bridge `src/graph/langgraph/bridge.py::run_task_lg(checkpointer=...)`) for durable checkpoints and interrupt/resume (intake-847: adopt_component).

## Prioritized Task List

- [x] **TM-1 — Materialize `data/trace/events.sqlite`** ✅ 2026-07-17 (10,326 rows: agent_audit 4108 / progress 3568 / journal 2649 incl. rotated shards / state 1; 62MB; FTS5 smoke + idempotent re-ingest verified; orchestrator `9958d819`) via `src/trace/cli.py` ingest paths (`ingest_autopilot.py`, `ingest_agent_audit.py`, `ingest_progress.py`); record per-source row counts; FTS5 query smoke.
- [x] **TM-2 — Add review-plane event categories** ✅ 2026-07-17 in `src/trace/store.py`: `REVIEW_DECISION`, `CANDIDATE_PACKAGE`, `VERIFICATION_REPORT`, `REVIEW_ESCALATION`, `PLAN_REMINDER` + `EventSource.REVIEW_PLANE`.
- [x] **TM-3 — Always-on shadow emission** ✅ 2026-07-17 (every review()/review_plan() invocation emits REVIEW_DECISION w/ latency_ms + tokens via emit.py, independent of plan_review acting; orchestrator `30d3232b`) from `ArchitectReviewService.review()`/`.review_plan()`: every invocation emits a trace event regardless of whether `plan_review` *acts* (precedent: tri-role `trinity_role_shadow` telemetry). Include per-decision `latency_ms` + token counts.
- [x] **TM-4 — Live push interface** ✅ 2026-07-17 (`src/trace/emit.py`: write-through with `emit://` synthetic-source namespace — chosen over re-ingest, rationale in module docstring; TracingProcessor 6-method shape, zero deps): add in-process `emit(Event)` to the store (re-implementation of the Agents-SDK `TracingProcessor` 6-method shape over our store — NO new dependency; intake-849 P6). Map their trace_id/group_id → our session_id/trial_id. File-tailing ingesters remain for offline sources.
- [x] **TM-5 — Decision-chain replay** ✅ 2026-07-17 (`query.py::decision_chain` + `decision-chain` CLI subcommand) in `src/trace/query.py`: reconstruct task → plan → review decision → gate results → outcome by session_id/trial_id.
- [x] **TM-6 — Overlap audit vs evidence-plane event-sourcing** ✅ 2026-07-17 (relationship contract documented below + in the evidence-plane handoff): the trace store must remain a queryable index over the same append-only sources, not a second event-sourcing pipeline. Document the relationship in both handoffs.
- [x] **TM-7 — Durable resume (LangGraph component adoption, intake-847)** ✅ 2026-07-17 (`checkpointing.py` + `run_task_lg_durable`/`resume_task_lg`; **AsyncSqliteSaver** — sync SqliteSaver raises NotImplementedError on the async methods run_task_lg uses; dedicated `data/graph_checkpoints.sqlite`; crash + interrupt→Command(resume) proven w/ stub nodes 10/10; SQLiteStatePersistence deprecated): wire `langgraph.checkpoint.sqlite.SqliteSaver` through the existing `run_task_lg(checkpointer=...)` bridge, replacing write-only `SQLiteStatePersistence`. Imports scoped STRICTLY to `langgraph` + `langgraph-checkpoint-sqlite` (minimum-imports; no langchain.agents/prebuilt). **Hazard**: node re-execution on resume — `_execute_turn`/REPL side effects must be idempotent (dovetails `side_effect_tracking` dep of `approval_gates`).
- [x] **TM-7 live parity residual** ✅ 2026-07-21 — live real-node `run_task_lg` now matches `run_task` on the fixed task set `data/trace/parity_task_set.json` before interrupt review-gates are enabled. Official batch retry `BULK-langgraph-tm7-parity-20260721T040534Z` ran through `run_batch_entry.py` with orchestrator `36bfe9b4` after stale output removal: `tm7_realnode_parity.json` reports `overall=PASS`, `n_pass=4/4`, `n_fail=0`, `arm_success_ok=true`, exact output equivalence for all tasks, and `n_parity_chain_coverage_fail=0` using explicit `result_role_history` chains (`len=1` on both arms). This closes only TM-7. TM-8 remains open because trace DB decision-chain coverage is still absent (`n_trace_coverage_fail=4`, trace chain lengths `0/0` on all tasks).
- [ ] **TM-8 — Coverage gate**: % of review invocations producing trace rows over a 50-question replay — must be ~100% before H4 starts. Also verify per-step **phase tags + executor-model-id + reminder events** are recorded (needed for plan-compliance metrics, intake-835).
- [x] **TM-9 — Trace/artifact discipline doc** ✅ 2026-07-17 (section below): session-init protocol (read progress/trace + git log + open items first), compaction/structured-note-taking/checkpoint-summary mandates for long control-plane runs, resume-from-failure over restart.

## Dependency Graph

```text
TM-1 → TM-2 → TM-3 → TM-8 (coverage gate → unblocks H4)
         └→ TM-4 → TM-5
TM-7 (parallel; unblocks interrupt-based review gates in H3)
TM-6, TM-9 (parallel, documentation)
```

## Cross-Cutting Concerns

1. **Evidence-plane alignment** — decision rows must stay reconcilable with the per-question ledger conventions (`evidence-plane-ledger-and-sequential-verdicts.md`); decisions ≈ questions.
2. **Layer A discipline** — the trace store is measurement substrate (Layer A); nothing in it may be mutated by agent-loop code; append-only.
3. **Idempotency-on-resume** is the one real LangGraph migration hazard; do not enable `interrupt()`-based gates (H3) before TM-7's parity validation.

## Key Files / Surfaces

- `src/trace/store.py`, `src/trace/cli.py`, `src/trace/query.py`, `src/trace/ingest_*.py`
- `src/graph/langgraph/bridge.py` (`run_task_lg`), `src/graph/persistence.py` (to be replaced), `src/graph/resume_token.py`
- `src/proactive_delegation/review_service.py` (emission points)
- `data/trace/` (target DB location)

## Reporting Instructions

Record row counts/coverage numbers here; flip checkboxes with `✅ YYYY-MM-DD`; update the index (H0) milestone table when TM-8 passes. Any schema change to trace categories after H4 starts is an instrument change — append an era note, never rewrite.

## Evidence Base (intake)

intake-847 LangGraph adopt_component (gap table: we are behind on durable resume/replay, ahead on interrupt policy) · intake-849 Agents-SDK TracingProcessor pattern (P6) · intake-846 Anthropic long-running-harness discipline · intake-835 phase-tagged trajectories · audit doc `research/deep-dives/2026-07-16-architect-reviewer-control-plane-audit.md`.

## TM-6 — Trace store ↔ evidence-plane relationship (documented 2026-07-17)

**Contract**: the trace store (`data/trace/events.sqlite`) is a **queryable index + decision ledger**, not a second event-sourcing pipeline. Three row classes, one entry path each (no double-sourcing — enforced by the source-key convention):
1. **File-ingested rows** (absolute POSIX `source_path`) — an *index over* the append-only sources of record (autopilot journals incl. rotated shards, agent_audit.log, progress/). The journals remain the autopilot's truth-of-record; re-ingest is idempotent; the store never writes back.
2. **Live review-plane rows** (`emit://` synthetic namespace) — *primary appends* for review decisions/artifacts that have no file source; namespace-separated so they can never collide with (1). The `review_ledger` table is the decision truth-of-record (RC-1), aligned decision≈question with the evidence-plane per-question ledger (RC-7 adapter).
3. The evidence-plane event-sourcing/narrative pipeline (`evidence-plane-event-sourcing-and-narrative.md`) stays authoritative for trial/verdict events; the trace store may INDEX those sources but never re-emits or transforms them into new events.

## TM-9 — Trace/artifact discipline for long control-plane runs (documented 2026-07-17; from intake-846)

Mandated for executor sessions on this series: (1) **session-init protocol** — read progress + `git log` + the owning handoff's open checkboxes + `decision-chain` for the relevant session_id BEFORE editing; (2) **structured note-taking** — durable state goes in typed artifacts/trace events, not conversation context; JSON artifacts with immutable structure + mutable status; (3) **checkpoint summaries** — at each milestone, persist a compact summary (progress entry + checkbox flips) before context grows; (4) **resume-from-failure over restart** — interrupted graph runs resume via the TM-7 checkpointer (`resume_task_lg(thread_id)`), never re-run from zero; deps re-supplied on resume; idempotency hazard documented in `checkpointing.py`.
