# Unified Trace / Memory Service

**Scratch**: `/mnt/raid0/llm/tmp/unified-trace-memory-service/` · worktrees: `/mnt/raid0/llm/worktrees/unified-trace-memory-service-*`

**Status**: T1-T6 LANDED 2026-05-06 — `epyc-orchestrator/src/trace/` package: SQLite store with FTS5 + 5 indices, agent_audit parser (JSON + legacy text dual-format), autopilot parser (no-op-when-absent for hosts without journals), progress markdown parser, query CLI (`python -m src.trace.cli {ingest,query,stats}`), 13 unit tests. Live ingest of 11,963 events (re-counted 2026-09-07) from `/workspace/logs` + `/workspace/progress` in <1s; idempotent re-ingest verified. Note that the append-only property covers the `event` table and its ledgers (INSERT OR IGNORE) but NOT the co-located `working_state` table (`harness_schema.py:570`, `:755` `UPDATE … SET superseded = 1`). T6 received a first-class trial-context API/CLI refresh on 2026-06-28 (`epyc-orchestrator` `d20f85b7`) via `trial_context(...)` and `python3 -m src.trace.cli trial-context --trial N`, returning exact trial rows plus nearby cross-source timeline context. T7 Hermes ingest deferred until Hermes graduates to daily use.
**Created**: 2026-04-25 (from local-RAG architecture review of friend's stack — "Trace / Memory Service" box)
**Categories**: agent_architecture, knowledge_management, autonomous_research
**Priority**: MEDIUM
**Effort**: ~1–2 inference-free days end-to-end (minimal version: read-only query layer over existing logs)
**Depends on**: nothing — read-only over already-persisted logs. Optional incremental ingest is additive.

> **Fable 5 review (2026-06-12)**: this service is the designated substrate for two new programs: [frontier-f1-real-task-corpus.md](../completed/frontier-f1-real-task-corpus.md) task_record capture (W2) and coordination with the per-question eval ledger schema in [evidence-plane-ledger-and-sequential-verdicts.md](evidence-plane-ledger-and-sequential-verdicts.md) — align event schemas before implementing EXM-1.

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

- [x] **T1: Schema + ingest skeleton** — `epyc-orchestrator/src/trace/store.py` with the SQLite schema above + `ensure_schema()` + idempotent upsert helpers. Unit tests on synthetic records. ~2 h.
- [x] **T2: agent_audit.log parser** — Parse `logs/agent_audit.log` produced by `scripts/utils/agent_log.sh` (lines like `[ts] [session_uuid] [task_name] [status]`). Emit normalized events. ~2 h.
- [x] **T3: autopilot journal parser** — Parse `autopilot_journal.tsv` (one row per trial) + `autopilot_journal.jsonl` (full detail). Cross-link via `trial_id`. Optionally include `autopilot_state.json` snapshots as `category=controller_snapshot` events. ~2 h.
- [x] **T4: progress/ markdown parser** — Walk `progress/YYYY-MM/*.md` for date-keyed sessions; treat each top-level `## ` heading as a session record with `summary` from the heading and `detail_json` from the section body. Where a sibling `.jsonl` exists, prefer that for granular events. ~2 h.
- [x] **T5: CLI + Python API** — `python -m epyc.trace query [--from TS] [--to TS] [--session ID] [--trial N] [--role R] [--category C] [--text "..."] [--limit N]` returning ranked event rows. Python module exports `query(...)` returning dicts. ~2 h.
- [x] **T6: Cross-source join recipes** — Document 3–4 high-value recipes in the handoff body or a `docs/` page: (a) "all events for trial N" (autopilot + agent_audit by time range), (b) "session timeline for date D" (progress + agent_audit), (c) "all failures + their preceding 5 actions". ~1 h. **2026-06-28 refresh**: `trial_context(...)` and `python3 -m src.trace.cli trial-context --trial N` now provide the primary trial recipe directly, with exact trial events and configurable nearby agent/progress/autopilot context.
- [ ] **T7 (optional): Hermes session ingest** — Walk `~/.hermes/sessions/*.json` if present, normalize into events. Gated on whether Hermes goes into production use (currently CLI-only validation). ~2 h. Defer until Hermes outer-shell graduates from validation to daily use.
- [x] **UTM-P1 — Add pairing keys to the unified trace event schema**: harness identity, seed, and a horizon/turn ordinal, at `src/trace/store.py:94-197`. Today **two runs cannot be paired on the same task across harnesses at all**, and `EventSource.HERMES_SESSION` (`store.py:36`) is a declared constant with **no ingester and no producer** — the dead constant is T7's stub. This blocks ANY cross-harness comparison, not just one metric, and it bites the moment HS-4 closes and a second harness goes live (soft-blocks HS-4 follow-through). **Schema-only change, no inference.** `intake-1341#04`. Zero compute. ✅ 2026-09-17 — orchestrator `dd24ed10` (on `origin/main`): event schema v2 adds nullable `harness` / `seed` / `turn_ordinal` / `task_key` plus a per-row `schema_version` (`src/trace/store.py` `EVENT_SCHEMA_VERSION`, `EVENT_PAIRING_COLUMNS`, `migrate_event_pairing_columns`). v1 stores migrate by idempotent additive ALTER with no back-fill (legacy rows read `schema_version` NULL = "never captured"); `query()` NULL-projects the columns on an unmigrated store and gains pairing filters; new `paired_runs(task_key, seed=...)` returns `{turn_ordinal: {harness: [events]}}`; the live-emit content key includes the pairing keys only when set (pre-v2 keys unchanged); `ReviewTracingProcessor` threads `harness`/`seed`/`task_key` from `Trace.metadata` and `turn_ordinal` from span data. `task_key` was added beyond the three named keys because "same task" has no other cross-harness identity. Tests: `tests/unit/test_trace_pairing_keys.py` (13); 180 adjacent trace/ledger tests green.
  - [x] **UTM-P1a — wire producers to stamp the pairing keys**: no live producer sets `harness`/`seed`/`turn_ordinal`/`task_key` yet (the AutoPilot live push `autopilot_live` and the eval tower are the first candidates; the file ingesters have nothing to stamp). Until one does, `paired_runs()` returns `{}` on the real store. Zero compute.
    ✅ 2026-09-17 (orchestrator `9a7181f2`) — **first producer wired: the review plane**
    (`ArchitectReviewService`, all 12 emit sites, source `review_plane`). Chosen as the cheapest HONEST
    producer after checking the two the box named: `autopilot_live` can stamp only `harness` (a `JournalEntry`
    has no RNG seed, no turn index, and `trial_id` is autopilot-only), and the eval tower emits no trace events
    at all today. The review plane already emits live AND carries a real cross-harness identity in
    `TaskIR.task_id`. Stamps `harness` on every row (injectable; `None` → NULL), `task_key` on `review()` as
    pass-through of `spec["task_id"]`, and `turn_ordinal` from `step_index` on `build_plan_reminder`.
    Everything else stays NULL = "never captured" — in particular **`task_key` is never derived from
    `subtask_id`** ("S1" recurs across unrelated tasks; a fabricated key would silently pair unrelated runs,
    which is worse than an empty pairing). `src/trace/` needed no change. 24 tests, including two harnesses
    pairing through a real store and legacy v1 rows reading back unstamped beside new ones.
    - [x] **UTM-P1a.2 — second producer, so `paired_runs()` is cross-harness on real data.** Three named
      candidates: `review_replay_50.py` passing `harness="review_replay"` + `task_key=q["task_id"]` (needs
      `review_candidate` to accept `task_key`) so replay pairs against live on the corpus id; the delegator
      passing its review-iteration index as `turn_ordinal`; and UTM-P1b's Hermes ingest using the same
      `TaskIR.task_id` convention. One producer alone can only pair a harness against itself.
      ✅ 2026-09-17 (orchestrator `7887e7ae`) — candidates 1 and 2 wired; UTM-P1b dropped from scope (Hermes was
      not selected). Replay stamps `harness="review_replay"` + `task_key` = the corpus `task_id`; the delegator
      passes its per-step review-iteration index as `turn_ordinal`. Deliberately NOT stamped: the RD-10b
      final-aggregate review and the parallel step executor, both one-shot — a `0` there would be an invented
      ordinal, so they stay NULL. 8 tests, incl. a real temp store where `paired_runs("rr50-001")` returns both
      harnesses; 302 passed across the adjacent slices.
      - [ ] **UTM-P1a.3 — make the pairing reachable on REAL data.** The keys are now stamped on both sides, but
        three things still stand between that and a real pairing, and none is a stamping problem:
        (a) **separate stores** — replay writes its own `--trace-db` and `run_shadow` *unlinks* a pre-existing DB
        under the TM-8 fresh-run rule, while `paired_runs()` reads ONE `db_path`; needs a non-destructive replay
        mode or a merge/attach step, and the destructive default is the part to decide first;
        (b) **no shared ids** — live tasks carry TaskIR/uuid ids, not `rr50-NNN`, so nothing feeds the pinned
        corpus through the live path;
        (c) **turn alignment** — delegator rows land on ordinals 0..n and replay rows on NULL, so a real pairing
        would be cross-harness but not turn-aligned until replay drives a looped review.
        Running the replay itself needs inference, so this is gated on a window.

  - [x] ~~**UTM-P1b — T7 (Hermes ingest) must stamp `harness="hermes"` plus `task_key`/`seed`/`turn_ordinal`** when it lands, or Hermes rows cannot be one side of a pair.~~ (closed 2026-10-29 audit: OBSOLETE → unified-trace-memory-service.md ~line 131: "UTM-P1b dropped from scope (Hermes was not selected)" (orchestrator 7887e7ae, 2026-09-17))

### Research intake 2026-10-22 — Locals + Beacon (intake-2386..2460)

- [x] **UTM-LB1 — Verify the existing conversation backup is live and covers each of the nine dev-harness stores, read-only: confirm the nightly cloud-llm-vault sync (02:00Z, immutable), the 14 retained ai-sessions tarballs in claude-backups (backup.log status) and the micron snapshots (keep 60) are current, then check per store whether the vault or a tarball holds it and from which date: Claude Code transcripts with subagent transcripts, ~/.claude/history.jsonl, the Claude memory dirs, Codex rollouts, the Codex state sqlite, opencode.db, the per-agent agent_audit shards and orchestrator logs, serving_calls.jsonl and planner_archive; report every store NOT covered as a gap for the operator; build no parallel backup, copy nothing and change no retention setting (live ~/.claude/projects keeps about 30 days, but the vault retains transcripts from 2026-08-02) (intake-2389, intake-2397).** ✅ 2026-10-22
  - Checker: `scripts/system/backup_coverage.py report|precondition` (read-only; root branch `f8/locals-b1-root-20261022`).
    Job is LIVE: backup.log `STATUS OK` 2026-10-22T02:16:37Z, LAST_STATUS 11:43Z (an extra root-owned run at 11:28Z
    also wrote `opencode-{epyc,host-daniele}-20261022-132850.db.zst` — not logged in backup.log); vault 31G/34194 files
    immutable. Coverage (tarball = `ai-sessions-20261022-132850` listing): Claude transcripts+subagents COVERED (vault
    6681 files, content from 2026-02-03; tarball 1854); Claude memory COVERED (vault 443, tarball 381); Codex rollouts
    COVERED (vault 20548, content from 2026-04-13; tarball 20548); opencode.db PARTIAL (one-off .db.zst only);
    NOT COVERED: `~/.claude/history.jsonl`, Codex `state_5`/`thread_history_1` sqlite, agent_audit shards + orchestrator
    logs, `serving_calls.jsonl`, `planner_archive.jsonl` (all only on raid0 md127; micron snapshots hold the vault only).
    Job anomalies: only 6 of 14 ai-sessions tarballs on disk (Oct 4–17 missing although ROTATE logs "kept 14"); no
    BACKUP/STATUS lines 2026-08-03..10-03 (62 d; rsync code-23 errors on immutable host/claude dirs); host:claude count
    flat at 1714–1715 since 10-04; `/mnt/micron` not mounted in the container (only the log attests 31 snapshots).
  - [x] **UTM-LB1.D — operator decision on the uncovered stores** — operator 2026-10-22: "Ignore this. I'm handling it through my root filesystem agent." Backup coverage is owned outside this repo; no backup work here. NIB2-LB1.2 waits on the operator's root-agent outcome. ✅ 2026-10-22
    Options: (A) extend the EXISTING root cron job's include list to history.jsonl, the Codex state sqlite (online
    `.backup`, not a raw copy of a live WAL db), `/workspace/logs/agent_audit*.log`, orchestrator `logs/` incl.
    serving_calls + planner_archive, and make the 2026-10-22 opencode `.db.zst` step nightly + logged — one job, no
    parallel backup; cost ~+0.5–1 GB/night (opencode zst 0.64 GB, codex sqlite ~8 GB raw → compressed). (B) accept
    raid0-only for the small derived logs (agent_audit 1.9 MB, planner_archive 12 MB, serving_calls 188 KB are
    reproducible-ish telemetry) and back up only history.jsonl + opencode — cheapest, loses audit history on a disk
    loss. (C) status quo — every uncovered store dies with md127; the opencode event reaper keeps pruning an uncovered
    store. Recommendation: (A), plus explain the missing Oct 4–17 tarballs and the 62-day gap. The operator owns the
    root cron job; no agent builds a backup.
    **Update 2026-10-22 (operator, root-filesystem agent delivered):** opencode is now covered by hourly consistent
    `sqlite3 .backup` snapshots, read-only (root:root 0444, `journal_mode=DELETE`, full cumulative history, at most ~1 h
    stale; nightly zstd + 72 hourly copies on `/mnt/micron/opencode-vault`): `/mnt/raid0/llm/opencode-db/{epyc.db,host-daniele.db}`
    (symlink to `/mnt/raid0/llm/opencode/readonly/`). Claude Code + Codex stay in `/mnt/raid0/llm/cloud-llm-vault/{host,twyne,epyc}/{claude,codex}/`.
    **Scope ruling: mine EVERYTHING** — both opencode DBs and Claude/Codex from host, twyne and epyc; every Unit/event/session
    record carries a `source` tag (`epyc|host|twyne`). `backup_coverage.py` counts `opencode_db` as `covered` while the newest
    snapshot is under 3 h old (judged by snapshot freshness, not the nightly job). Mining readers open snapshots only
    (`?mode=ro` + `PRAGMA query_only=1`, one retry, never the `event` table) and REFUSE the live stores
    (`~/.local/share/opencode`, `/mnt/raid0/llm/opencode/<src>/`); `dh_privacy` lists `/mnt/raid0/llm/opencode{,-db}` as never-write roots.
    Code: root `f8/opencode-ro-root-20261022`, orchestrator `f8/opencode-ro-orch-20261022`, research `f8/opencode-ro-research-20261022`.
- [x] **UTM-LB2 — Build the private dev-harness transcript projector reading from the existing backup (cloud-llm-vault copies and the ai-sessions tarballs; live stores only for data newer than the last nightly sync) over Claude Code JSONL, Codex rollouts and opencode V1/V2, read-only, into events with OTel GenAI names in detail_json (operation, tool call id, usage normalized to inclusive OTel input tokens per each harness's convention with the raw tuple kept, conversation and agent lineage), Beacon-style collection_method and observed/inferred fidelity markers, keyed-HMAC 64-token block hashes, Claude usage dedupe by message id, Codex usage read from token_usage_record (never summed token_count), spawn-vs-fork edge kinds, a composite source-schema key per session, the semconv commit stamped, and a session-to-commit join from commit hashes in tool results; outputs private only (intake-2387, intake-2403, intake-2419, intake-2434#record, intake-2438).** ✅ 2026-10-22
  - `scripts/dev_harness/{dh_sources,projector,dh_privacy}.py`; outputs `dev-harness-{event,session,commit-join,projection-run}.v1`
    under `/mnt/raid0/llm/private/dev-harness-traces/projections/<run>/` (0700/0600; content → keyed-HMAC 64-token
    block hashes, key in `keys/`). Semconv stamped `semantic-conventions-genai@9ffc7e00` (gen-ai-dev/1.42.0-dev).
    Sample run `sample-20261022` (8 Claude + 8 Codex + 4 opencode main sessions, 66 units incl. 46 subagents, 16006
    events, 2.2 s, 64 MB RSS, nice 19); 27 tests in `tests/dev_harness/`. The sample read the live db `immutable=1`; since
    2026-10-22 opencode is read from the read-only snapshots `/mnt/raid0/llm/opencode-db/{epyc,host-daniele}.db`
    (`?mode=ro`), default tenant is all of `epyc,host,twyne`, outputs land under `events/<harness>/<source>/` (see UTM-LB1).
  - [x] **UTM-LB2.1 — Full-corpus projector + AgentRun run** under `nice -n 19`, off the inference windows:
    `python3 scripts/dev_harness/projector.py --claude 0 --codex 0 --opencode 0 --max-file-mb 0 --run-id full-<date>`
    then the same flags on `agentrun.py`; the default `--tenant all` already covers epyc, host and twyne plus both opencode snapshot DBs (`--opencode 0`). Estimate from the
    sample (~45 MB/s single core): ~31 GB vault → ~12–15 min each, ~6 GB + ~4.5 GB private output (raid0 has 608 GB).
  - *(2026-10-22 13:33Z, workspace-f8.)* ✅ 2026-10-22 projection COMPLETE, run `full-20261022T1310Z`: 42,744 units (claude_code 4,907, codex 20,547, opencode 17,290), 3.2M events, 4,066 commits joined, 858 s; private output only. Evidence: `/mnt/raid0/llm/private/dev-harness-traces/projections/full-20261022T1310Z/run.json`.
  - [ ] **UTM-LB2.2 — Ingest projector events into the unified trace store** (`src/trace/`, new EventSource for
    dev-harness events, detail_json passthrough, dedupe on (source_path, source_line)), private DB path only.
- [x] **UTM-LB3 — Point the agent_audit ingester at the per-agent agent_audit shard files; its default is the frozen legacy /workspace/logs/agent_audit.log (src/trace/ingest_agent_audit.py:24) (intake-2387).** ✅ 2026-10-22
  - orchestrator `08670ddd` (branch `f8/locals-b1-orch-20261022`): `parse_source()` reads every
    `agent_audit*.log` under `/workspace/logs` (same glob as root `agent_log_files()`), CLI `--agent-audit` takes a
    file or a dir; 18 passed in `tests/unit/test_trace_store.py`.
- [x] **UTM-LB4 — Run one short claude -p session with the console OTel exporter and every content toggle off, to list the fields this harness version emits (ttft, hook events, compaction, agent lineage); persist no setting and change no global env (intake-2419).** ✅ 2026-10-22
  - *(2026-10-22, workspace-f8 / clerical.)* `claude -p` authenticates headless here with no env or settings change. One session (`claude -p "Reply with the single word ok." --max-turns 1`), env on that one command only: `CLAUDE_CODE_ENABLE_TELEMETRY=1 OTEL_METRICS_EXPORTER=console OTEL_LOGS_EXPORTER=console OTEL_METRIC_EXPORT_INTERVAL=1000 OTEL_LOGS_EXPORT_INTERVAL=1000 OTEL_LOG_USER_PROMPTS=0 OTEL_LOG_TOOL_DETAILS=0 OTEL_LOG_TOOL_CONTENT=0`; rc 0, output scratch removed. Content toggles hold: `prompt`, `prompt_text`, `response` all `<REDACTED>` (lengths still emitted: `prompt_length`, `response_length`). METRICS: `claude_code.session.count`, `.token.usage`, `.cost.usage`, `.active_time.total` (attrs: model, effort, query_source, type, start_type). LOG EVENTS (`event.name` + `event.sequence`, `event.timestamp`, `prompt.id`, `session.id`): `api_request` (`ttft_ms`, `duration_ms`, `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_creation_tokens`, `cache_creation_5m_tokens`, `cache_creation_1h_tokens`, `cost_usd`, `cost_usd_micros`, `model`, `effort`, `speed`, `query_source`, `request_id`, `client_request_id`); `hook_registered` (`hook_event`, `hook_source`, `hook_type`); `hook_execution_start` (`hook_event`, `hook_name`, `hook_source`, `num_hooks`, `managed_only`); `hook_execution_complete` (`total_duration_ms`, `num_success`, `num_blocking`, `num_non_blocking_error`, `num_cancelled`, `num_outputs_persisted`, `stdout_chars`, `additional_context_chars`, `system_message_chars`, `initial_user_message_chars`); `user_prompt` (`prompt_length`, `message.uuid`); `assistant_response` (`response_length`, `message.uuid`, `request_id`); `mcp_server_connection` (`status`, `transport_type`, `server_scope`, `duration_ms`, `is_plugin`); `plugin_loaded` (`plugin.name`, `plugin.scope`, `has_hooks`, `has_mcp`, `skill_path_count`, `agent_path_count`, `command_path_count`); `managed_settings_resolved`. Resource attrs on every record: `user.id`, `user.email`, `user.account_id`, `user.account_uuid`, `organization.id`, `service.name`, `service.version`, `terminal.type`, `os.type`, `os.version`, `host.arch` (identifying: strip before any commit). GAPS in this one-turn session: no compaction event, no agent/sub-agent lineage field (no `agent_id`/`parent`), no tool-call events (no tool ran). Those need a longer session with a tool and a sub-agent; `ttft_ms` and hook timing ARE present, which closes the console-field check for those two.
  - [x] UTM-LB4.1 — close the two remaining OTel field gaps: one short `claude -p` session, same per-command env and content toggles off, that runs one tool call (a read-only Bash) and spawns one sub-agent; record the tool-call event fields and whether any agent/sub-agent lineage field (`agent_id`, parent id) appears. Strip resource identity attrs before anything is committed; persist no setting. Cloud tokens only, no local compute. (filed 2026-10-22, f8 evening wrap-up) ✅ 2026-10-24
    - Compaction via OTel: not filed because forcing a compaction needs a context-filling session, and the transcript projector already records compaction boundaries from the JSONL (`dh_sources.py` `compact_boundary` / opencode `compacted` -> `operation=compaction`).
    - *(2026-10-24, workspace-f8 sweep.)* **Ran one `claude -p` session** (CLI 2.1.308, `--model haiku --max-turns 6`, cwd a scratch dir under `/mnt/raid0/llm/tmp`, so no project settings). It used the same per-command env as UTM-LB4, set on that command only, and saved no setting. It made one read-only `ls` Bash call and spawned one built-in general-purpose sub-agent. rc 0, 64 records.
      - **The raw output is deleted.** It carried `user.email`, account/org ids and `session.id` on every record. Only an identity-free field-name summary was kept, in `/mnt/raid0/llm/tmp/f8-utm-lb41-20261024/fields_summary.json`.
      - **Tool-call events.**
        - `tool_decision` carries `tool_name`, `tool_use_id`, `decision`, `source`, `tool_source`, `permission_mode` and `classifier_verdict`.
        - `tool_result` carries `tool_name`, `tool_use_id`, `success`, `duration_ms`, `tool_input_size_bytes` and `tool_result_size_bytes`.
        - The content toggles held: neither event carries arguments or output.
      - **Lineage.** No event carries `agent_id` or any parent id.
        - The sub-agent shares the parent's `session.id`.
        - The only marker on its `api_request` and `assistant_response` is `query_source` = `agent:builtin:general-purpose`, plus `agent.name` on `api_request` and on the token and cost metrics.
        - A new event, `subagent_completed`, carries `agent_type`, `agent.source`, `is_async`, `is_built_in`, `model`, `final_model`, `model_swapped`, `duration_ms`, `total_tokens` and `total_tool_uses`. It has no id that links it to the spawning `Agent` tool call.
        - **Gap:** `tool_decision`/`tool_result` carry neither `query_source` nor `agent.name`. A tool call made INSIDE the sub-agent (it called `SubagentHandback`) cannot be told apart from a parent call. The only way to separate them is the `tool_use_id` join to the transcript JSONL, which does keep sidechain lineage.
      - Other events seen: `managed_settings_resolved`, `mcp_server_connection`, `plugin_loaded` and `retention_sweep`.
      - Bearing on the trigger-gated "Native harness OTel" item: OTel-only fields the transcripts lack are `ttft_ms`, per-request `duration_ms`, tool `duration_ms` and `tool_decision` `source`/`classifier_verdict`. Lineage is the reverse case, a field the transcripts carry and OTel lacks.

Trigger-gated (no checkbox until the trigger fires):
- Local pushback judge calibration and SWE-chat in-the-wild checks — open once the operator labels the 100-item sheet (and, for SWE-chat, provides an HF login) (intake-2397#record, intake-2406#record).
- Anchored replay A/B with a validated local user simulator, trim-vs-full memory index A/B, reactive hook hints, CODESKILL-prompt candidate pilot, precondition-gated session selection, Beacon rubric as a local typed-decision workload, a raw-trajectory arm and the SkillBank student-memory arm — open when the lesson time-series pilot shows a measurable lesson effect or none for prose-only lessons (intake-2396#record, intake-2410#record, intake-2427#record, intake-2431#record).
- Check-after-write in the REPL and tests-as-judge best-of-K — open when recorded sessions show a high test-run step fraction or batched decode supports K>1 (intake-2386#record).
- LLM layer of the local failure-mode clustering (small-model facet extraction and naming via llama-server; OpenClio's prompts as reference, write from scratch because OpenClio is vLLM-bound and Kura has no licence; cluster-purity check on a hand-labelled sample; summary-first fallback) and a local rubric judge or self-hosted Docent viewer — open when the no-LLM baseline (DHM-7) shows clusters worth naming and operator labels exist (intake-2443#record, intake-2444#record, intake-2446#record, intake-2447#record).
- Native harness OTel (hook timing, TRACEPARENT into actors) and semconv re-check — open after the console field check lists gaps the transcripts leave, or when the GenAI spec leaves Development (intake-2403#record, intake-2419#record).

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

## Evaluation capture versus RL eligibility — 2026-10-04

Operator-approved clarification from [P3 operational integration](../../research/intake-stage3-plan-2026-10-03-decision-tools.md#p3-operational-integration--exercise-both-real-tool-loops-and-improve-sft-input-selection) and [K6/K9](../../research/intake-stage3-plan-2026-10-03-decision-tools.md#why-the-general-critiques-are-beliefs-not-work-packets), plan `3911ec91`: UTM is a provenance/query service, not a training rollout engine. Harness/task/seed/turn pairing supports evaluation joins; generic trace validity does not establish exact original token IDs, behavior-logprob or authoritative-mask eligibility for off-policy RL. Evaluation, independently verified complete offline-SFT targets and off-policy RL remain separate consumer contracts. Original behavior logprobs are unnecessary for offline SFT and mandatory only for the distinct off-policy RL consumer.

[M3](../../research/intake-stage3-plan-2026-10-03-decision-tools.md#broader-follow-ons--distinct-from-the-immediate-integrations) requires a named model/workload/objective and eligible original rollouts before full multi-harness RL; implement exact-token export only for that actual consumer. TU-MH-1 and S2-CGE-1 retain their respective evaluation and SFT owners. UTM-P1a.3 remains the existing real-data pairing task, including its store, shared-ID, turn-alignment and inference-window conditions. This clarification adds no implementation checkbox or schema/export work.

## Cross-References

- **Autopilot memory** (peer, distinct concern): [`autopilot-continuous-optimization.md`](autopilot-continuous-optimization.md) § Memory Architecture (episodic store + skill bank + strategy store).
- **Hermes conversation logs** (peer, distinct concern): [`hermes-outer-shell.md`](../completed/hermes-outer-shell.md) § Two-Layer Memory Architecture.
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

## Deep-Dive Task Proposals — 2026-05-25 (intake-607 Code-as-Agent-Harness §3.2.1 / §3.2.3)

The Code-as-Agent-Harness memory taxonomy (§3.2) reframes two design choices for the trace/episodic stores. Audit pass converts the brainstorm into concrete schema/query additions.

- [x] **EXM-1 — Index FAILED trajectories as first-class avoidance cases.** §3.2.3 (experiential memory; ExpeL / Evo-Memory / MemGovern) argues failures should be stored and *retrieved for pattern-matched avoidance*, not just logged. We have a `failure_graph` (partial). Extend the unified trace store with a queryable "failure case" view: given a current (task, context) signature, return prior failed trajectories with similar signatures so a role can avoid repeating them. Minimum fields for a `failure_case` view/table: `failure_id`, `task_signature`, `suite`, `role_path`, `tool_sequence_hash`, `files_touched`, `error_class`, `root_cause_label`, `avoidance_advice`, `evidence_event_ids`, `resolved_by_event_id`, `governance_level`, and `validity_score`. Retrieval should combine lexical FTS, structured filters, and optional embedding similarity only after a cheap first pass. *(Highest-value here — cheap, reuses the store.)* **DONE 2026-06-27** in `epyc-orchestrator` `f470c519`: the schema already had the minimum `failure_case` fields; this slice added `failure_case_fts`, rebuild-on-schema-ensure for existing rows, insert-time indexing, exact-match-first lexical retrieval, and `_match_type`/`_matched_terms` annotations so callers can explain why a prior failure was surfaced. GitNexus impact was LOW for `find_failure_cases` and `insert_failure_case`; `GovernanceLevel` was LOW (`impactedCount=20`, import-level dependants). Validation: `python3 -m py_compile src/trace/harness_schema.py tests/unit/test_harness_schema.py`; `uv run ruff check src/trace/harness_schema.py tests/unit/test_harness_schema.py`; `uv run pytest -q tests/unit/test_harness_schema.py tests/unit/test_trace_store.py` -> `30 passed`.
- [x] **EXM-2 — Externalize working state (LLMs fail at latent-state persistence).** §3.2.1 cautions that raw LLMs lose working state across long horizons, so working memory should be *externalized* rather than held in-context. Audit where the orchestrator relies on the model to "remember" mid-task state vs. where it externalizes to the trace/scratchpad store; pull the former into the store where cheap. Add a `working_state` record family with `state_id`, `scope` (`request|trial|session|handoff`), `owner`, `key`, `value_json`, `created_from_event_id`, `expires_at`, and `supersedes_state_id`. Complements context-folding (which evicts) by keeping authoritative state outside the window. **DONE 2026-06-27** in `epyc-orchestrator` `25b3d4fc`: the scoped `working_state` table and supersession helpers already existed; this slice closed the missing lifecycle rule by marking expired live rows `superseded=1` before reads/writes so stale state is preserved for history but no longer returned as current. GitNexus impact was LOW for `set_working_state`, `get_working_state`, and `WorkingStateScope`. Validation: `python3 -m py_compile src/trace/harness_schema.py tests/unit/test_harness_schema.py`; `uv run ruff check src/trace/harness_schema.py tests/unit/test_harness_schema.py`; `uv run pytest -q tests/unit/test_harness_schema.py tests/unit/test_trace_store.py` -> `32 passed`.
- [x] **EXM-3 — Governed-experience tier (MemGovern).** Distinguish *governed* experiences (human-reviewed/approved outcomes) from raw trajectories when scoring retrieval relevance, so high-trust cases outrank noisy ones. Ties to the URE-2 approval-as-harness-state record in [`decision-aware-routing.md`](decision-aware-routing.md). Proposed levels: `raw`, `auto_verified`, `human_reviewed`, `approved_baseline`, `deprecated`. Retrieval should down-rank raw failures when a governed resolution exists, and should never present deprecated advice without a warning. **DONE 2026-06-27** in `epyc-orchestrator` `2af20d53`: `find_failure_cases()` now annotates retrieval rows with `_governance_rank` and `_governance_warning`; raw rows warn when a governed alternative exists for the same task signature, and deprecated rows warn when explicitly included. GitNexus impact was LOW for `find_failure_cases` and `GovernanceLevel` (`impactedCount=20`, import-level dependants). Validation: `python3 -m py_compile src/trace/harness_schema.py tests/unit/test_harness_schema.py`; `uv run ruff check src/trace/harness_schema.py tests/unit/test_harness_schema.py`; `uv run pytest -q tests/unit/test_harness_schema.py tests/unit/test_trace_store.py` -> `34 passed`.

**Audit refinements / missed gaps**:

1. **Failure retrieval can cause negative transfer.** EXM-1 must show why a prior failure is similar and what changed since then. Include content hashes/config snapshot IDs where possible; stale failures should be marked `suspected` rather than blindly retrieved.
2. **Avoidance advice needs provenance.** A failure case without evidence event IDs and a resolution link is just folklore. Keep it searchable, but do not elevate it to governed memory.
3. **Working state needs lifecycle rules.** EXM-2 should distinguish short-lived request state from durable handoff state. Add expiry/supersession so the store does not become an unbounded pile of stale scratchpad facts.
4. **Governance should affect ranking, not delete history.** Raw and deprecated records remain auditable; ranking and warnings handle trust. This preserves forensic value after regressions.
5. **Unify with HLE/BSV schemas.** Failure cases should link to harness metrics, oracle adequacy, behavior signatures, and URE approval records via event IDs so a future query can answer: "what failed, why was it accepted, who/what approved it, and what behavior changed?"

Roll-up: [`routing-and-optimization-index.md`](routing-and-optimization-index.md) P24 § Additional task additions. Source: intake-607 `deep_dive` in `research/intake_index.yaml`.

## Shared Harness/Trace Schema — OWNED HERE (gap-fix 2026-05-25)

**This handoff owns the single shared event schema** that the 2026-05-25 intake-607 cluster (HLE / BSV / URE / EXM) all write to. Four handoffs independently assumed a common trace/journal event family; without a designated owner that becomes four divergent schemas and the promised cross-queries ("what failed, why was it accepted, what behavior changed?") break. The schema lives in `epyc-orchestrator/src/trace/store.py` + `src/trace/harness_schema.py` (extends the existing T1–T6 store) and MUST be implemented **before** the consuming tasks (HLE-1, HLE-4, BSV-1, URE-2) land their writes. *(Implemented + tested; MERGED to epyc-orchestrator main 2026-05-26, tip `15350fe`.)*

| Record family | Owning task | Written by | Read by |
|---|---|---|---|
| `harness_metrics` (execution_fidelity, feedback_interpretation, planning_stability, memory_coherence, recovery_rate + `evidence_event_ids`, `confidence`, `metric_schema_version`) | HLE-1 (meta-harness) | eval tower / trace ingest | HLE-4 (autopilot Pareto), HALO/P20 |
| `oracle_adequacy` (`oracle_type`, `coverage_claim`, `known_blind_spots`, `shortcut_risk`, `requires_external_answer`, `deterministic`, `reviewed_by`) | HLE-2 (meta-harness) | suite registration | HLE-1/HLE-4, autopilot gating |
| `behavior_signature` (per-sentinel outcome, answer hash, route/tool/escalation path hashes, latency/token buckets, harness-metrics ref, oracle-adequacy version) | BSV-1 (autopilot) | archive accept path | BSV-2/BSV-3 diff |
| approval/escalation record (`request_id`, uncertainty components, trigger reason, approval boundary, linked behavior_signature) | URE-2 (decision-aware-routing) | router/escalation | EXM-3 governance, audit |
| `failure_case` + `working_state` (fields enumerated in EXM-1/EXM-2 above) | EXM-1/EXM-2 (here) | trace ingest | role retrieval, all of the above |

**Contract rules**: (1) every record carries `metric_schema_version` and is keyed by stable `event_id`; (2) cross-references use `event_id` links, never duplicated payloads; (3) schema changes are additive + versioned (no silent field repurposing); (4) consumers must tolerate missing fields (`signature_confidence=partial` for backfilled rows). Implementation order is pinned in [`routing-and-optimization-index.md`](routing-and-optimization-index.md) P24 § "Implementation spine".

## Research Intake Update — 2026-07-11

### New Related Research
- **[intake-800] "From Passive Retrieval to Active Memory Navigation"** (arxiv:2607.05794, "NapMem"; **Alibaba Qwen team** + ShanghaiTech — deep-dive corrected the first-pass "Microsoft Research" attribution)
  - Relevance: reframes long-term memory from system-level passive retrieval to an **agent-navigated structured action space** — directly informs how this service exposes trace/memory to consuming agents rather than only storing it.
  - Key techniques worth mining (adopt_patterns, not a drop-in): (1) **four-tier provenance pyramid** (L1 raw conversations → L2 typed memory records `fact/event/instruction/preference` → L3 topic tracks → L4 user profile) mirroring our tiered event families; (2) memory exposed as **5 tools** (`search_records/search_conversation/get_records/get_conversation/read_file`) — a plain store API, no model-specific machinery; (3) **RRF hybrid vector+keyword retrieval** at k=60 (weaker than [[colbert-reranker-web-research]], which already exceeds it — contrast not adoption); (4) an RL (GRPO) **tool-call-frugality reward** (3.97→2.15 calls/query; unnecessary GPQA-D calls 34.51%→6.90%).
  - **Deep-dive (2026-07-11) load-bearing finding:** the Table-4 ablation, read on the conversational-memory subset that matches our use case (LoCoMo+LongMemEval), shows the **borrowable store+navigation half contributes MORE than the RL policy** (+11.94 vs +7.92 L-J); prompt-only navigation over the same store reaches **~89% of full-system quality**. So we do **NOT** need their (unreleased) trained 9B — **adopt_patterns confirmed, not adopt_component**. RL's durable unique value is call-frugality, a later optional efficiency lever.
  - Reported (self-graded L-J, no code release): LongMemEval F1 57.41 / L-J 80.33; 4.83 GiB storage vs Mem0's 10.44. Credibility 3. Note metric non-comparability: not comparable to MemPalace 96.6% R@5 (intake-326) — NapMem is orthogonal (navigation interface), not better/worse.
- [ ] Operator-review candidate: prototype a **read-only 5-tool navigation surface over the already-landed `src/trace/` FTS5 store — NO RL** (search/get by `event_id` + `read_file` on a progress summary), plus an **RRF(k=60) hybrid** fusing FTS5 lexical + a vector index (existing BGE embedders :8090-8095). ~89%-of-value path; days of inference-free work. Cadence to copy: records flush at 1/2/4/5-turn boundaries; tracks >20 new records; profile >50.
  - [x] Read-only navigation primitive landed in `epyc-orchestrator` commit `d364835a`: `src/trace/navigation.py` exposes `search_records`, `search_conversation`, `get_records`, `get_conversation`, allowlisted/size-bounded `read_file`, and pure RRF(k=60) fusion over caller-supplied vector candidates. No ingestion/schema/runtime mutation and no embedding-server calls. ✅ 2026-07-11
  - [x] CLI access for the five read tools landed in `epyc-orchestrator` commit `e1e6d271`: `trace search-records`, `trace search-conversation`, `trace get-records`, `trace get-conversation`, and `trace read-file`, covered by `tests/unit/test_trace_cli.py`. ✅ 2026-07-11
  - Note 2026-09-16 (sub-trace-bm25), **integrated** (orchestrator merge `21172688`, pushed in `d748b4c7`): `query(text=...)` / `search_records` claimed bm25 ranking but ordered by `ts_utc DESC`, so a limited search kept the newest matches and RRF fused a recency rank. Fixed on orchestrator branch `sub/trace-bm25-20260916` at `6302b381`: text queries now default to bm25 ranking applied before LIMIT; an explicit `order="recency"` option (CLI `--order`) is available; filter-only callers are unchanged and now pass recency explicitly. No recorded result used the old ordering: CME-4's retriever (research `ccc41d4b`) fetches every match and re-ranks by bm25 itself, and UTM-B2/B4 have not been run.
  - **Extend with [intake-809] AutoMem's WRITE half (deep-dive 2026-07-11):** the NapMem surface above is the read/PLAN half; AutoMem's net-new, inference-free contribution is the **LOG/write ops as first-class agent actions** — `APPEND`/`CREATE` + **coordinate/key-keyed `UPSERT` dedup** + auto-synced `status`/`inventory`/`strategy` files (cut per-step memory growth −95% in their NetHack run). Note: `src/trace/` is **read-only by design** (No-write-path non-goal), so this write surface targets an **agent-facing memory tool over autopilot's episodic/strategy store**, not the trace store. Scaffold carries 85–95% of AutoMem's value; its LoRA memory-specialist is deferred (see [[meta-harness-optimization|completed ledger]] P3).
  - [x] AutoMem write-schema primitive landed in `epyc-orchestrator` commit `bf315b11`: `orchestration/repl_memory/memory_actions.py` adds default-inert `APPEND`/`CREATE`/`UPSERT` actions with coordinate/key dedup and generated `status`/`inventory`/`strategy`/`plan`/`log` projections under the agent-facing memory path. `src/trace/` remains read-only. ✅ 2026-07-11

## Research Intake Update — 2026-07-16

### New Related Research — GCP "always-on memory agent" (adopt_patterns, one transferable idea)
- **[intake-825] "Always-On Memory Agent"** (GoogleCloudPlatform/generative-ai demo; Google ADK + Gemini + plain SQLite)
  - Correction to the first-pass assumption: the sample uses **plain SQLite with NO vector DB and NO embeddings** (a deliberate non-RAG stance) + Google ADK — NOT Vertex AI Agent Engine / Memory Bank. That makes the *pattern* portable but the *stack* irrelevant to us.
  - Transferable pattern (adopt_patterns, not a component): a **timer-triggered background consolidation loop** (default 30-min) that scans *unconsolidated* memories, generates cross-cutting insights, and compresses — gated by an **ingest-time 0–1 importance score** — over a two-state (unconsolidated→consolidated) store. Analogous to sleep-time-compute / autopilot-nightshift overnight passes; conceptually already covered by intake-155 (AgentFold) and intake-413/418 (hierarchical memory distillation), so novelty is low.
  - Fit vs the landed `src/trace/` surface: this service is **read-only by design**; a consolidation/insight pass is a *write/derive* step, so it targets the **agent-facing memory store** (the AutoMem write half above / B1 User Modeling per [[delta-mem-reproduction]]), not the trace store. Zero empirical results (demo-grade) — pattern-adoption only.
- [ ] Operator-review candidate: consider an **importance-scored background consolidation pass** (periodic insight-generation + compaction over the agent-facing episodic/strategy store) as an optional extension of the AutoMem write surface — inference-free, mirrors the GCP loop, and is distinct from the read-only trace store.

## Research Intake Update — 2026-07-29 (agent-memory dives: ReasoningBank / CORE / SkillOS / EvoMemBench)

_Via `/research-intake` Stage-4 (intake-930 ReasoningBank, intake-888 CORE, intake-935 SkillOS, intake-936 EvoMemBench; intake-899 is the internal falsification precedent). All external figures are OBSERVATION-grade under MEASUREMENT.md. These items target the **agent-facing** experience/memory layer and the trace store's retrieval surface — `src/trace/` itself stays read-only._

### Store shape and layering

- [x] **UTM-M1 — Adopt the ReasoningBank STORE SHAPE: append-only, raw trajectory retained alongside derived `{title, description, content}` items.** ✅ 2026-07-29 — `epyc-orchestrator`'s default-inert `MemoryActionStore` now has an additive `pattern` channel. Each non-tombstone pattern requires an immutable bounded `source_event_ids` list, `title`, `description`, `content`, applicability boundary (`when_not_to_use`), `embedding_version`, and explicit `retention_state`; it is persisted to the append-only JSONL ledger and rendered as a separate projection. Existing raw trajectories remain authoritative in their current stores; no trace migration, embedding backfill, runtime wiring, or live BGE request occurred. The legacy high-blast-radius `SkillBank` contract was deliberately left untouched.
- [x] **UTM-M2 — Scope the dual-layer experience bank as an ADDITIVE upper layer on `src/trace/`. ✅ 2026-07-29** The per-case lower layer remains `src/trace`'s read-only `events.sqlite` + FTS5 store. The upper layer is a separate agent-memory ledger: immutable raw-event references plus derived pattern records, each with source-event ids, an applicability boundary, embedding version, and retention state. Retrieval must fuse FTS5 and vector candidates only at an explicit agent-facing consumer; it must not mutate or become a dependency of trace ingestion/query. Start with bounded per-pattern provenance and a declared capacity/eviction policy before any embedding backfill; no live BGE request, trace-store migration, or runtime wiring is authorized by this scope.
- [x] **UTM-M3 — Adopt SkillOS's three-verb write API (`insert` / `update` / `delete`) plus its "When NOT to Use" section** in every stored skill/pattern record. ✅ 2026-07-29 — default-inert `MemoryActionStore` now accepts append-only `DELETE` tombstones: a matched delete removes the current generated projection but retains the prior row, tombstone rationale, actor, and `previous_event_id` in `memory_actions.jsonl`; a missing delete is a non-mutating `missing` result. Strategy records require and render a `When Not To Use` applicability boundary. Focused suite: `tests/unit/test_memory_actions.py` 11 passed.
- [x] **UTM-M4 — Mine the Apache-2.0 ReasoningBank repo for the three prompts** (extraction-on-success, extraction-on-failure, binary judge; plus the MaTTS contrast prompt) **and the JSON store schema.** ✅ 2026-07-29 — source audit of `google-research/reasoning-bank`: `SUCCESSFUL_SI` / `FAILED_SI` each cap non-overlapping generalizable items at 3 with `{Title, Description, Content}` Markdown fields; `build_text_eval_prompt` is the binary judge (`Status: success|failure`) with completeness, grounding, and exact-target checks; `PARALLEL_SI` is the MaTTS contrast prompt (success/failure comparison, ≤5 transferable items). `induce_memory.py` persists JSONL rows with `task_id`, `query`, `think_list`, `action_list`, `status`, `memory_items`, and `template_id`. Import prompts + schema only — **not** the BrowserGym/Vertex-coupled harness.

### The measurement that does not exist yet — EPYC-original, blocked on no one

- [x] **UTM-M5 — Build the PER-WINDOW (non-cumulative) success-rate-vs-store-size instrument.** ✅ 2026-07-29 — `epyc-orchestrator` `05e0b8bf` adds read-only `scripts/analysis/memory_store_growth_curve.py`: chronological, non-cumulative success rate per window, cumulative store size, and unknown outcomes reported separately from a SQLite `mode=ro` connection. Focused suite `tests/unit/test_memory_store_growth_curve.py` 2 passed; Ruff and `git diff --check` clean. Output is observation-grade until a named protocol and attestation exist; it gates no adoption decision by itself. **No paper in the set reports this curve** — not ReasoningBank (intake-930), not CORE (intake-888), not SkillOS (intake-935), not EvoMemBench (intake-936); SkillOS's own Future Work concedes the gap. ReasoningBank's Figure 1 is **cumulative** and therefore structurally incapable of showing intake-899-style late decay: a per-window curve can fall while the cumulative curve still rises.

### Context-budget competition at long context (intake-936) — NOT the same failure as intake-899

- [x] **UTM-M6 — File the EvoMemBench 128K finding as a distinct failure mode.** Independent third party, **DeepSeek-V3.2 backbone**: at a **128K** context budget, **six of fifteen memory methods score BELOW the no-memory baseline** (worst: MemoryOS **−7.0pp**). Counts by budget are **3 / 4 / 3 at 16K / 32K / 64K and DOUBLE at 128K**. **CRUCIAL: the mechanism is context-budget COMPETITION — injected memory displacing live history — NOT store growth.** It must **not** be conflated with intake-899 (late decay from store growth). Two different diseases; conflating them will produce the wrong fix. ✅ 2026-07-29 — source-backed in `intake-936` (`dive-overturned`): its fixed-update-schedule context-budget sweep isolates prompt-space competition, while intake-899 concerns accumulated-store decay.
- [x] **UTM-M7 — Make trace/memory retrieval BUDGET-CONDITIONAL (design consequence (a)).** ✅ **Re-implemented and integrated 2026-09-16** (`sub-utm-m78`, orchestrator `74418b3c`, merge `d748b4c7` on `main`; `tests/unit/test_trace*.py` 44 passed). The original 2026-07-29 tick was false: `select_budgeted_records()` had never been committed to any epyc-orchestrator ref. — `src/trace/navigation.py` now provides default-off `select_budgeted_records()`: it returns no retrieval rows when `history_is_truncated` is false (the untruncated history fits), and otherwise requires the caller to declare both history/window tokens and the pressure threshold. It does not search, infer token counts, call embeddings, or inject prompts; caller wiring remains a separately reviewed change.
- [x] **UTM-M8 — Cap injection as a FRACTION OF REMAINING BUDGET, not a fixed k (design consequence (b)).** ✅ **Re-implemented and integrated 2026-09-16** (same change as UTM-M7: orchestrator `74418b3c`, merge `d748b4c7`). The 2026-07-29 tick was false (code never committed). — the same pure selector admits only rows carrying an explicit positive `estimated_tokens` value and caps their total at `remaining_budget_fraction × (window_tokens - history_tokens)`. This makes unknown token cost fail closed and prevents a fixed count from overrunning a nearly-full context. No runtime retrieval/injection behavior changed.
- [ ] **UTM-M9 — Add a NO-MEMORY control arm to the eval tower for every memory A/B.** Six published methods lose to no-memory at 128K and **would have shipped undetected without one**. Eval-tower rows are a human-amendment-only trust boundary (MEASUREMENT.md) — this is an operator-gated ask, filed here as the owning rationale.

### Correction — ReasoningBank's standing (do not carry "best overall" forward)

- [x] **UTM-M10 — Correct the ReasoningBank standing in every place this repo restates it ✅ 2026-07-29.** Root `683f70de` had introduced the stale wording in intake-930; this correction fixes it: intake-936 places ReasoningBank **LAST of 13** memory methods on **Cross-Episode Knowledge (Easy split)**; the earlier "second behind ACE" reading was **wrong**. It **is** best-among-memory-methods on **In-Episode Execution at 16K / 32K / 128K** — but even there a **long-context baseline beats all fifteen** methods. SkillOS-base also wins the WebShop-like domain, so no family-wide gradient-free ranking remains. Keep the store-shape adoption (UTM-M1), drop the "best overall" framing wherever it appeared.

## 2026-08-07 — verifiable memory operations, default-inert shadow path (intake-1008#record, intake-1015#record, intake-1017#record, intake-1018#record, intake-1022#record, intake-1023#record)

- [ ] **UTM-V1 — Complete the append-only memory-operation envelope and state-transition engine.** Add
  typed `ADD|UPDATE|DELETE|RETRIEVE|FILTER|SELECT_EPISODE|SUMMARIZE|NOOP` proposals over the existing
  raw-event authority. Every operation carries operation/session/actor ids, immutable source-event
  references, before/after value hashes, version and supersession links, applicability boundary,
  proposer/verifier versions, `proposed|validated|committed|rejected|rolled_back` state, and error or
  rollback provenance. `UPDATE` creates a new version; soft `DELETE` creates a tombstone and preserves
  history; physical privacy erasure is a separate explicit state and must not be claimed from a
  tombstone. Implement restore/rollback and stale-fencing fixtures. Existing raw traces are never
  overwritten or made unrecoverable.

- [ ] **UTM-V2 — Add a local scoped write proposer, not an authoritative writer.** Combine Mem0's
  user/agent/run scoping, recent-message context, top-k conflict retrieval, and four-way mutation
  proposal with VerMem's stronger envelope. Record actor versus subject so one model's inference
  cannot silently become another actor's fact. Run in shadow on recorded traces first; compare
  proposed operations with current append-only behavior and human-labelled cases. Do not copy the
  current Mem0 branch's ADD-only default as the target and do not allow lossy facts to replace raw
  evidence.

- [ ] **UTM-V3 — Separate structural and semantic verification and calibrate both.** Structural checks
  deterministically enforce schema, scope, provenance, version, tombstone, rollback, source existence,
  and transition legality. A separately versioned semantic judge scores local operation correctness
  and global memory coherence. Build human-labelled conflicting, stale, poisoned, private, strategically
  manipulated, duplicate, missing-source, and delete/restore cases; report false-pass/false-fail by
  class. The released VerMem rule verifier is only the structural baseline and cannot inherit the
  paper's DeepSeek semantic-verifier result.
  - 2026-10-21 UTM-V7 criteria added here: the profile-write audit checklist ([docs/reference/profile-write-audit-checklist.md](../../docs/reference/profile-write-audit-checklist.md)) applies to ProfileStore and `user_conclude` writes (one fact per entry, about the target user, no conversational mechanics, no paraphrase duplicates, references and dates resolved).

- [ ] **UTM-V4 — Test answer-time evidence distillation independently of memory writing.** Preserve
  Memory-R1's manager/distiller separation: retrieve a bounded candidate set, then have the answer
  path select evidence with source ids before answering. Sweep the retrieval/distillation budget
  rather than assuming sixty entries is optimal. Score answer quality, evidence precision/recall,
  unsupported claims, tokens, latency, and raw-source recoverability against no-distiller retrieval.

- [ ] **UTM-V5 — Emit per-operation credit in shadow, without RL training.** Record deterministic
  structural result, calibrated local/global semantic result, downstream task outcome, evidence
  recall, operation cost, and rollback/recovery outcome as separate fields. Compare task-only credit
  with operation-level credit. No learned policy may consume this signal until deterministic and
  supervised baselines, conversation-isolated splits, verifier calibration, and reproducible data
  show a measured advantage; the official Memory-R1 repository currently releases no training code.

- [ ] **UTM-V6 — Run a complete memory evaluation matrix with a mandatory no-memory control.** Include
  no-memory/raw full context, current append-log retrieval, current Context-Folding, Mem0-style shadow
  proposals, VerMem operations, answer distillation, and the CF-AM-1 parallel-gist arm. Measure within-
  task, crash/restart, cross-session, conflict/staleness, poisoning, actor scope, tombstone, physical
  erasure, rollback, and raw-evidence recovery. Account for extraction, write, embedding, retrieval,
  answer, verifier, training (if later permitted), tokens, latency, wall time, and storage separately.
  Use conversation-level splits and repeated end-to-end seeds; judge repeats alone are not uncertainty.

## 2026-09-07 — memory-service surface + the BEAM/Tulving retrieval arm (research-intake)

- [ ] **UTM-B1 — Register the already-built read surface as a model-facing `ms.search` / `ms.expand`
      tool** (`intake-1316#record`). `src/trace/navigation.py` already IS an ms-shaped read surface
      (`search_records`, `search_conversation`, `get_records`, `get_conversation`, allowlisted
      `read_file`, pure RRF k=60) with no ingest, no schema mutation and no embedding call. **The
      gap is registration, not construction.** Correction to the bearing dive text: it is not
      "zero consumers" — re-grepped 2026-09-07, it has exactly **one non-test consumer,
      `src/trace/cli.py:22`**, and **no MCP registration and no orchestrator wiring**. That is the
      gap.
- [ ] **UTM-B2 — Expose the FTS5 store + `navigation.py` (RRF k=60) as the memory backend for a
      BEAM 128K run** (`intake-1330#record`) — the cheapest first-party test of the append-only-log
      thesis. BEAM's driver reuses one retriever/prefix across all 20 questions of a conversation
      with no cross-question accumulation, so the arm is embarrassingly parallel and
      order-independent. COMPUTE-GATED: filed, not run.
- [ ] **UTM-B3 — Record the ingest FILTER in the run artifact as a first-class experimental
      parameter, not plumbing** (`intake-1337#record`). Record exactly which turns were indexed and at
      what granularity: a silent role filter or chunking choice moves the score more than the
      retrieval algorithm does. COMPUTE-GATED rider on UTM-B2.
- [x] **UTM-B4 — Route the Tulving `retrieved` arm through this surface** — the backend half of
      CME-4 in [conversational-memory-eval-instrument.md](conversational-memory-eval-instrument.md)
      (`intake-408#record`). Zero compute to write. ✅ 2026-10-07 — MAIN accepted [existing source and original23/23](../../artifacts/ni08/utm-b4-tulving-source-20261007/README.md).

**Note on UTM-M9** (mandatory no-memory control arm for every memory A/B, above): it is already
flagged in-file as an operator-gated MEASUREMENT.md trust-boundary ask. M-12a/M-12b satisfy its
intent; **do not tick UTM-M9** — the eval-tower registration is the operator's.

## MAIN-reviewed JEV refinement — 2026-10-06 (UTM-V3)

Prepare the semantic-verifier case manifest and mocked parser/readout fixtures using the existing `judge_redundancy.py` fixture/receipt pattern: frozen case and rubric hashes, explicit criterion outcomes, unresolved parse/transport failures and denominators, and reader agreement reported separately from accuracy against gold. Reuse `Question`/`DecisionResult` only for genuinely closed rubric choices; memory payloads and explanations remain source data. Structural schema/scope/provenance/transition checks remain deterministic host checks.

UTM must author and adjudicate its own human-labelled conflicting, stale, poisoned, private, manipulated, duplicate, missing-source and delete/restore cases. CJ's synthetic rubric truth does not transfer to memory semantics. Mocked conformance proves representation and failure handling only; the separately versioned live semantic judge still needs UTM-V3's per-class false-pass/false-fail calibration. Add no belief grading ladder and grant no write authority. UTM-M9's human-amendment-only eval-tower gate remains unchanged.


- [x] **UTM-V3-SYNTHETIC — characterize native structural/parser/readout contracts without semantic gold.** ✅ 2026-10-06 — [Contract and source acceptance](../../docs/reference/utm-synthetic-conformance-contract.md), original CI37444684189 TRUE2/2;8store categories/5parser batches/6attempts. Generated readout is captured at execution. Source/privacy/scope/freshness/poisoning/manipulation remain unassessed, dangling source IDs characterized rather than declared safe. Human semantic calibration, live judge and UTM-M9 remain open.

## Read-only registration source companion — 2026-10-07

- [x] **UTM-B1-SOURCE — prepare the existing read-only trace navigation registrar and synthetic MCP/SQLite controls.** Exact `ms.search`/`ms.expand` tool names, declared session_id, fixed default read store and no model-selected paths, writes or embeddings. Keep the default orchestrator MCP catalog unchanged until catalog-growth acceptance; source registrar is explicit and uninvoked. Actual off-host FastMCP schema/defaults and synthetic SQLite navigation controls through VB-UTM-B1-CONFORMANCE. Parent model-facing registration and real consumers remain open. ✅ 2026-10-07 — MAIN accepted [published source and original5/5](../../artifacts/ni08/utm-b1-read-only-mcp-source-20261007/README.md).

2026-10-07 MAIN source finding: UTM-B4 is already implemented by the checked CME-4 backend in current Research `de02a21d88e006dd542b7a1a56bf8090a27de1f3`: chapter Events in a private SQLite store, existing `navigation.search_records` candidate retrieval and FTS BM25 selection, default retrieved-arm construction and missing-source refusal. VB-UTM-B4-CONFORMANCE now owns a prospective full synthetic native capture, including the four trace-dependent cases with an exact APP source path; no skipped control will count. UTM-B4 source routing is now checked after MAIN accepted original23/23; real-data/model quality remains unassessed. UTM-B3's prospective filter/count source remains executable independently of the future real BEAM run; its historical COMPUTE-GATED rider does not gate source authoring.

- [x] **UTM-B3-SOURCE — add prospective BEAM memory ingest provenance to question/run artifacts.** Preserve all flattened role/content messages in source order, record zero-based half-open indexed range, normalized role/message/chunk counts and exact pair-chunk granularity for retrieved arms. Label the full-history arm without claiming a retriever lookup; no historical backfill or real BEAM outcome. MAIN-reviewed isolated Research source180a772445e2c227979998cdec9b7a50ae5aa54e; actual synthetic module validation through VB-UTM-B3-CONFORMANCE precedes publication. Parent real experimental run remains open. ✅ 2026-10-07 — MAIN accepted [source and original21/21](../../artifacts/ni08/utm-b3-beam-provenance-source-20261007/README.md).

## 2026-10-20 — lesson-revision A/B spec (intake-1999#record)

- [x] **UTM-R1 — Lesson-revision A/B spec (design only; no run).** Arm B revises retrieved lessons after a labelled outcome using only the lesson's source trajectory plus the outcome as feedback, as append-only supersession built on the existing `superseded` retention state and `previous_event_id` (`orchestration/repl_memory/memory_actions.py:30,268 @5d4ad2c0`); arm A is forward-only reflection; both keep a raw-trace baseline and a no-memory control (UTM-V6 matrix, UTM-M9 stays operator-gated and unticked). Instruments: M-12, BEAM M-12b and UTM-B4 under P-AB-1, with N >= 100 per arm and run-local CI and MDE declarations. Report a grounded/leaked/unsupported audit of revised claims on a sample; a counterfactual same-instance replay is allowed only as a labelled diagnostic upper bound, never an arm (`intake-1999#record`). Fixtures required at filing: two consecutive opposite-sign single-instance outcomes must not oscillate the stored lesson (recency flip), and a revision that ignores an unused notepad entry is reported (`intake-2149#03`). Record the decision whether revision runs as a background or idle-time job (not serve-time) at result time, with no compute claim now. ✅ 2026-10-20
  UTM-R1 readout addendum (UTM-R2, 2026-10-21), two report lines: (a) revised-lesson reuse rate = retrieved-and-used after revision / retrieved-after-revision, defined on the existing `superseded` and `previous_event_id` fields, an adoption proxy and not a quality measure (intake-117#record); (b) the write-side cost line (LLM calls plus input and output tokens over every memory-construction call, judge excluded) beside the read-side injected-token line (intake-2311#record).
- [x] **UTM-R2 — UTM-R1 reporting addendum: revised-lesson reuse rate and write-side cost.** Add to the UTM-R1 readout: revised-lesson reuse rate equals retrieved-and-used after revision over retrieved-after-revision, defined on the existing superseded and previous_event_id fields, as an adoption proxy and not a quality measure (intake-117#record); and the write-side cost line (LLM calls plus input and output tokens over every memory-construction call, judge excluded) beside the read-side injected-token line (intake-2311#record). Acceptance: both lines are in the UTM-R1 readout text. Estimate: 0.2 day. ✅ 2026-10-21
- [ ] **UTM-V7 — Profile-write precision audit checklist from the Honcho deriver rubric.** Define the ProfileStore and `user_conclude` write-audit checklist from the Honcho deriver prompt (`src/deriver/prompts.py:67-86 @607438d`): one fact per entry; the fact is about the target user; no conversational mechanics; no paraphrase duplicates; references and dates resolved. Apply by deterministic checks where possible and a human-labelled sample otherwise; add it to the UTM-V3 criteria. Reference intake-2237#record. Acceptance: the checklist is filed, the deterministic checks have unit tests, and one audit run over the current profile store is reported. Estimate: 1 day.
  - 2026-10-21 `dpf-skill` NOT ticked. Checklist filed: [profile-write-audit-checklist](../../docs/reference/profile-write-audit-checklist.md); deterministic checks + unit tests in orchestrator `09396bbe` (`src/user_modeling/write_audit.py`, `tests/unit/test_profile_admission.py`). The one audit run is VACUOUS, not a pass: `features().user_modeling` is off and no `user_profiles.db` exists ([result](../../artifacts/dpf-skill-20261021/utm_v7_audit.json) = `store_not_found`). Run `python -m src.user_modeling.write_audit` once a profile store exists, then tick.
