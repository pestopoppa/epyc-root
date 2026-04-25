# Unified Trace / Memory Service

**Status**: stub (proposal — not yet started)
**Created**: 2026-04-25 (from local-RAG architecture review of friend's stack — "Trace / Memory Service" box)
**Categories**: agent_architecture, knowledge_management, autonomous_research
**Priority**: MEDIUM
**Effort**: ~1–2 inference-free days end-to-end (minimal version: read-only query layer over existing logs)
**Depends on**: nothing — read-only over already-persisted logs. Optional incremental ingest is additive.

## Objective

Collapse the three fragmented audit/trace formats we already write — `logs/agent_audit.log`, `progress/YYYY-MM/*.md` (+ JSONL), and autopilot's `autopilot_state.json` + `autopilot_journal.{tsv,jsonl}` — into a single queryable provenance store with a thin Python/CLI API. After a long autopilot or nightshift run, "why did we decide X?" should be one query, not a walk across three formats with three different schemas.

## Why This Matters

| Question post-nightshift | Files we currently walk |
|---|---|
| "When did this trial fail and what was the species?" | `autopilot_journal.jsonl` + `autopilot_state.json` |
| "What was the agent doing in the 2-hour window before the regression?" | `agent_audit.log` (timestamps) + `progress/2026-04/2026-04-DD.md` (narrative) |
| "Why was this Pareto entry accepted?" | `autopilot_journal.tsv` (one row per trial) + `journal.jsonl` (full detail) + safety_gate logs in `agent_audit.log` |
| "Which evidence sources were consulted for this decision?" | `progress/` narrative + `agent_audit.log` task starts/ends + (no provenance link) |
| "Did this conversation reference a prior session's findings?" | Hermes `MEMORY.md` + our `progress/` — no shared timeline |

Three data points, three formats, no join keys. The gap is acute during autopilot debugging (per `feedback_phased_plan_gates.md` — "Long multi-phase plans MUST re-audit at phase start") and during multi-day handoff continuity.

## What "Unified" Means Here

A read-only **query layer** over the existing files — not a replacement, not a migration. The source files keep their current writers (`agent_log.sh`, autopilot's `experiment_journal.py`, the progress markdown convention). The new layer:

1. Ingests on demand from the existing files (or incrementally via tail-watch).
2. Normalizes records into a single SQLite schema with stable join keys (timestamp range, session_id, trial_id, role, file_path mentioned).
3. Exposes a small query API and CLI.

This is **not** a memory architecture upgrade for autopilot or Hermes — both retain their domain-specific stores (autopilot's `repl_memory/strategy_store.py`, Hermes's `MEMORY.md`). The unified service is for cross-source *provenance queries*, not for production routing or evolutionary memory.

## Sources to Ingest

| Source | Format | Cadence | Granularity |
|---|---|---|---|
| `logs/agent_audit.log` | tab/space-separated text | streaming (append on every `agent_task_start/end`) | per-action |
| `progress/YYYY-MM/YYYY-MM-DD.md` | markdown narrative | manual (post-session) | per-day session summary |
| `progress/YYYY-MM/YYYY-MM-DD.jsonl` | JSONL (where present) | streaming during sessions | per-task |
| `epyc-orchestrator/orchestration/autopilot_journal.tsv` | TSV | per-trial | per-trial summary row |
| `epyc-orchestrator/orchestration/autopilot_journal.jsonl` | JSONL | per-trial | full per-trial detail |
| `epyc-orchestrator/orchestration/autopilot_state.json` | JSON snapshot | per-trial | controller state at trial boundary |
| (optional) Hermes `~/.hermes/sessions/*.json` | JSON | per-session | conversation transcript + tool calls |

**Schema (minimum viable)**:

```sql
CREATE TABLE event (
  id INTEGER PRIMARY KEY,
  ts_utc TEXT NOT NULL,           -- ISO8601 with microseconds
  source TEXT NOT NULL,           -- 'agent_audit' | 'progress' | 'autopilot_journal' | 'autopilot_state' | 'hermes_session'
  source_path TEXT NOT NULL,      -- file the record came from
  source_line INTEGER,            -- line number where applicable
  session_id TEXT,                -- agent_log session UUID, autopilot trial id, etc.
  trial_id INTEGER,               -- autopilot trial number where applicable
  role TEXT,                      -- orchestrator role / species / agent task type
  category TEXT,                  -- task_start | task_end | mutation | safety_verdict | pareto_accept | session_summary | ...
  status TEXT,                    -- success | failure | skip | null
  summary TEXT,                   -- short human-readable line
  detail_json TEXT                -- full record as JSON for downstream parsing
);

CREATE INDEX event_ts ON event(ts_utc);
CREATE INDEX event_session ON event(session_id);
CREATE INDEX event_trial ON event(trial_id);
CREATE INDEX event_source ON event(source);
```

Two virtual tables (FTS5) for full-text search across `summary` and `detail_json`.

## Architecture (proposed)

```
existing writers (unchanged):
  agent_log.sh ──> logs/agent_audit.log
  experiment_journal.py ──> autopilot_journal.{tsv,jsonl} + autopilot_state.json
  manual / hooks ──> progress/YYYY-MM/*.md + .jsonl
                                      │
                                      ▼
                       ┌──────────── ingest workers ─────────────┐
                       │  parse → normalize → upsert into SQLite │
                       └───────────────────┬─────────────────────┘
                                           ▼
                                  data/trace/events.sqlite (+FTS5)
                                           ▲
                       ┌───────────────────┴─────────────────────┐
                       │  query CLI / Python API                  │
                       │   - by time range                        │
                       │   - by session_id / trial_id             │
                       │   - by role / category / status          │
                       │   - full-text over summary + detail_json │
                       └──────────────────────────────────────────┘
```

**Ingest model**: idempotent batch from current file state on every invocation (small enough corpus that a full re-ingest takes seconds). Optional `--watch` mode (inotify or polled tail) for live append. Records are keyed by `(source_path, source_line)` for dedup.

## Work Items

- [ ] **T1: Schema + ingest skeleton** — `epyc-orchestrator/src/trace/store.py` with the SQLite schema above + `ensure_schema()` + idempotent upsert helpers. Unit tests on synthetic records. ~2 h.
- [ ] **T2: agent_audit.log parser** — Parse `logs/agent_audit.log` produced by `scripts/utils/agent_log.sh` (lines like `[ts] [session_uuid] [task_name] [status]`). Emit normalized events. ~2 h.
- [ ] **T3: autopilot journal parser** — Parse `autopilot_journal.tsv` (one row per trial) + `autopilot_journal.jsonl` (full detail). Cross-link via `trial_id`. Optionally include `autopilot_state.json` snapshots as `category=controller_snapshot` events. ~2 h.
- [ ] **T4: progress/ markdown parser** — Walk `progress/YYYY-MM/*.md` for date-keyed sessions; treat each top-level `## ` heading as a session record with `summary` from the heading and `detail_json` from the section body. Where a sibling `.jsonl` exists, prefer that for granular events. ~2 h.
- [ ] **T5: CLI + Python API** — `python -m epyc.trace query [--from TS] [--to TS] [--session ID] [--trial N] [--role R] [--category C] [--text "..."] [--limit N]` returning ranked event rows. Python module exports `query(...)` returning dicts. ~2 h.
- [ ] **T6: Cross-source join recipes** — Document 3–4 high-value recipes in the handoff body or a `docs/` page: (a) "all events for trial N" (autopilot + agent_audit by time range), (b) "session timeline for date D" (progress + agent_audit), (c) "all failures + their preceding 5 actions". ~1 h.
- [ ] **T7 (optional): Hermes session ingest** — Walk `~/.hermes/sessions/*.json` if present, normalize into events. Gated on whether Hermes goes into production use (currently CLI-only validation). ~2 h. Defer until Hermes outer-shell graduates from validation to daily use.

## Open Questions

1. **Append-only vs mutable**: SQLite is mutable; the source files are append-only-ish. Should the unified store mirror append-only semantics (never UPDATE rows, only INSERT or skip duplicates)? **Tentative answer**: yes — append-only with `(source_path, source_line)` dedup. Easier to reason about, no data loss on re-ingest.
2. **Retention**: keep all history forever, or roll older months out? Source files are already authoritative, so the unified store can be regenerated. **Tentative answer**: keep all history while size is small (<1 GB); add a rolloff policy only if the store grows beyond that.
3. **Hermes session ingest**: do we need it for the v1, or is it a follow-up? **Tentative answer**: defer (T7 marked optional). Not needed until Hermes is in regular use.
4. **Live tail**: is on-demand re-ingest enough, or do we need an inotify watcher? **Tentative answer**: on-demand for v1. Re-ingest cost should stay below 5 s for typical sizes; revisit if it doesn't.
5. **Coupling with autopilot's strategy_store**: autopilot already has FAISS-indexed strategy retrieval (`repl_memory/strategy_store.py`). The unified trace store is **not** a replacement — strategy_store retrieves *insights*, not *events*. Cross-link: include trial_id in both so a strategy_store insight can link back to its source events here.

## Non-Goals (explicit)

- **Not a memory architecture upgrade for autopilot** — autopilot's evolutionary memory (episodic store, skill bank, strategy store) is unchanged.
- **Not a replacement for Hermes's MEMORY.md / Honcho** — those are for user/conversation modeling, distinct concern.
- **No write path** — the unified store never writes back to source files. Source files remain the single source of truth.
- **No auth/scopes** — single-user, local-only.
- **Not a real-time dashboard** — query API only. A dashboard could be built on top later if useful.

## Cross-References

- **Autopilot memory** (peer, distinct concern): [`autopilot-continuous-optimization.md`](autopilot-continuous-optimization.md) § Memory Architecture (episodic store + skill bank + strategy store).
- **Hermes conversation logs** (peer, distinct concern): [`hermes-outer-shell.md`](hermes-outer-shell.md) § Two-Layer Memory Architecture.
- **Existing audit infra**: `scripts/utils/agent_log.sh` (writer) + `scripts/utils/agent_log_analyze.sh` (current analysis CLI — narrower scope than the unified service).
- **Routing & optimization index**: `routing-and-optimization-index.md` § Cross-Cutting Concerns 5 ("Conversation Logs Feed All Three") — the unified service operationalizes that cross-cutting concern.

## Key Files (proposed)

| Path | Purpose |
|---|---|
| `epyc-orchestrator/src/trace/store.py` | SQLite schema + upsert helpers (T1) |
| `epyc-orchestrator/src/trace/ingest_agent_audit.py` | T2 parser |
| `epyc-orchestrator/src/trace/ingest_autopilot.py` | T3 parser |
| `epyc-orchestrator/src/trace/ingest_progress.py` | T4 parser |
| `epyc-orchestrator/src/trace/query.py` | T5 query API |
| `epyc-orchestrator/scripts/trace/cli.py` | `python -m epyc.trace ...` CLI (T5) |
| `data/trace/events.sqlite` | Output store (gitignored — derived data) |
