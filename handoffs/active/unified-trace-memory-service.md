# Unified Trace / Memory Service

**Status**: T1-T6 LANDED 2026-05-06 — `epyc-orchestrator/src/trace/` package: SQLite store with FTS5 + 5 indices, agent_audit parser (JSON + legacy text dual-format), autopilot parser (no-op-when-absent for hosts without journals), progress markdown parser, query CLI (`python -m src.trace.cli {ingest,query,stats}`), 13 unit tests. Live ingest of 3477 events from `/workspace/logs` + `/workspace/progress` in <1s; idempotent re-ingest verified. T6 received a first-class trial-context API/CLI refresh on 2026-06-28 (`epyc-orchestrator` `d20f85b7`) via `trial_context(...)` and `python3 -m src.trace.cli trial-context --trial N`, returning exact trial rows plus nearby cross-source timeline context. T7 Hermes ingest deferred until Hermes graduates to daily use.
**Created**: 2026-04-25 (from local-RAG architecture review of friend's stack — "Trace / Memory Service" box)
**Categories**: agent_architecture, knowledge_management, autonomous_research
**Priority**: MEDIUM
**Effort**: ~1–2 inference-free days end-to-end (minimal version: read-only query layer over existing logs)
**Depends on**: nothing — read-only over already-persisted logs. Optional incremental ingest is additive.

> **Fable 5 review (2026-06-12)**: this service is the designated substrate for two new programs: [frontier-f1-real-task-corpus.md](frontier-f1-real-task-corpus.md) task_record capture (W2) and coordination with the per-question eval ledger schema in [evidence-plane-ledger-and-sequential-verdicts.md](evidence-plane-ledger-and-sequential-verdicts.md) — align event schemas before implementing EXM-1.

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
  - **Extend with [intake-809] AutoMem's WRITE half (deep-dive 2026-07-11):** the NapMem surface above is the read/PLAN half; AutoMem's net-new, inference-free contribution is the **LOG/write ops as first-class agent actions** — `APPEND`/`CREATE` + **coordinate/key-keyed `UPSERT` dedup** + auto-synced `status`/`inventory`/`strategy` files (cut per-step memory growth −95% in their NetHack run). Note: `src/trace/` is **read-only by design** (No-write-path non-goal), so this write surface targets an **agent-facing memory tool over autopilot's episodic/strategy store**, not the trace store. Scaffold carries 85–95% of AutoMem's value; its LoRA memory-specialist is deferred (see [[meta-harness-optimization]] P3).
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

- [ ] **UTM-M1 — Adopt the ReasoningBank STORE SHAPE: append-only, raw trajectory retained alongside derived `{title, description, content}` items.** ReasoningBank and intake-899 converge on this independently from opposite directions (one by construction, one by falsification) — the strongest design signal in the set. **This settles the open AP-29 question: promotion must NOT remove raw trajectories from L1.** (Owning gate lives in [`autopilot-continuous-optimization.md`](autopilot-continuous-optimization.md) AP-29.)
- [ ] **UTM-M2 — Scope the dual-layer experience bank as an ADDITIVE upper layer on `src/trace/`.** The per-case lower layer already exists (SQLite + FTS5); what is missing is **pattern distillation** and **similarity retrieval**. FTS5 is lexical, so this needs an embedding column (BGE servers already live on `:8090-8095`). MemoHarness leaves ψ and K undefined and has **no eviction policy at all** — those are OUR design decisions, and an unbounded bank is a real hazard for a long-running autopilot.
- [ ] **UTM-M3 — Adopt SkillOS's three-verb write API (`insert` / `update` / `delete`) plus its "When NOT to Use" section** in every stored skill/pattern record. `delete` as a **first-class, auditable** operation — rather than implicit decay — is the structural difference between SkillOS and every heuristic-management system that underperformed in the same comparisons. Maps onto the existing AutoMem `APPEND`/`CREATE`/`UPSERT` surface; the missing verb is the auditable delete.
- [ ] **UTM-M4 — Mine the Apache-2.0 ReasoningBank repo for the three prompts** (extraction-on-success, extraction-on-failure, binary judge; plus the MaTTS contrast prompt) **and the JSON store schema.** Import prompts + schema only — **not** the BrowserGym/Vertex-coupled harness.

### The measurement that does not exist yet — EPYC-original, blocked on no one

- [ ] **UTM-M5 — Build the PER-WINDOW (non-cumulative) success-rate-vs-store-size instrument.** **No paper in the set reports this curve** — not ReasoningBank (intake-930), not CORE (intake-888), not SkillOS (intake-935), not EvoMemBench (intake-936); SkillOS's own Future Work concedes the gap. ReasoningBank's Figure 1 is **cumulative** and therefore structurally incapable of showing intake-899-style late decay: a per-window curve can fall while the cumulative curve still rises. **This measurement does not exist in the literature, is an EPYC-original deliverable, and is blocked on no external dependency — it is the highest-value item in this section.** Required in any memory A/B before an adoption decision.

### Context-budget competition at long context (intake-936) — NOT the same failure as intake-899

- [x] **UTM-M6 — File the EvoMemBench 128K finding as a distinct failure mode.** Independent third party, **DeepSeek-V3.2 backbone**: at a **128K** context budget, **six of fifteen memory methods score BELOW the no-memory baseline** (worst: MemoryOS **−7.0pp**). Counts by budget are **3 / 4 / 3 at 16K / 32K / 64K and DOUBLE at 128K**. **CRUCIAL: the mechanism is context-budget COMPETITION — injected memory displacing live history — NOT store growth.** It must **not** be conflated with intake-899 (late decay from store growth). Two different diseases; conflating them will produce the wrong fix. ✅ 2026-07-29 — source-backed in `intake-936` (`dive-overturned`): its fixed-update-schedule context-budget sweep isolates prompt-space competition, while intake-899 concerns accumulated-store decay.
- [ ] **UTM-M7 — Make trace/memory retrieval BUDGET-CONDITIONAL (design consequence (a)).** Inject top-k retrieved items **only while live history occupies more than a fraction of the window**, and inject **NOTHING** once the untruncated history fits. Memory that competes with the actual conversation for window space is a net negative at long context.
- [ ] **UTM-M8 — Cap injection as a FRACTION OF REMAINING BUDGET, not a fixed k (design consequence (b)).** A fixed k is exactly the parameterization that produced the sub-baseline scores above, because its cost scales with item size while its benefit does not scale with window pressure.
- [ ] **UTM-M9 — Add a NO-MEMORY control arm to the eval tower for every memory A/B.** Six published methods lose to no-memory at 128K and **would have shipped undetected without one**. Eval-tower rows are a human-amendment-only trust boundary (MEASUREMENT.md) — this is an operator-gated ask, filed here as the owning rationale.

### Correction — ReasoningBank's standing (do not carry "best overall" forward)

- [x] **UTM-M10 — Correct the ReasoningBank standing in every place this repo restates it ✅ 2026-07-29.** Root `683f70de` had introduced the stale wording in intake-930; this correction fixes it: intake-936 places ReasoningBank **LAST of 13** memory methods on **Cross-Episode Knowledge (Easy split)**; the earlier "second behind ACE" reading was **wrong**. It **is** best-among-memory-methods on **In-Episode Execution at 16K / 32K / 128K** — but even there a **long-context baseline beats all fifteen** methods. SkillOS-base also wins the WebShop-like domain, so no family-wide gradient-free ranking remains. Keep the store-shape adoption (UTM-M1), drop the "best overall" framing wherever it appeared.
