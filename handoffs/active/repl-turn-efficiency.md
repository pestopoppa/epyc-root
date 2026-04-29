# REPL Turn Efficiency — Frecency Discovery + Combined Operations

**Status**: in-progress (S1a-c done, S2a-b done, S3a done 2026-04-11, S4 pending inference, S5 analysis done 2026-04-12, S6a-f done 2026-04-16)
**Created**: 2026-04-09 (from research intake: intake-295, intake-301)
**Priority**: MEDIUM
**Categories**: agent_architecture
**Depends on**: None (independent workstream)

---

## Objective

Reduce REPL tool invocations per task from ~8-11 to ~4-5 turns through:
1. Frecency-weighted file discovery (temporal signal for navigation)
2. Combined operations (batch multi-step patterns in single calls)
3. Contextual suggestions (append next-likely commands to output)

---

## Motivation — The Omega Problem

Package B Phase 4 Omega metric (2026-04-09): **7/10 suites — REPL tools HURT accuracy** (direct > REPL). Worst: agentic -54pp, coder -44pp, general -26pp. Only hotpotqa +12pp and gpqa +6pp benefit.

WS-1/WS-3 address this from the prompt side (tighter tool-use policy). This handoff addresses the structural side: make each tool invocation more valuable by returning better results (frecency) and doing more per turn (combined ops).

**Risk**: Contextual suggestions (S3) may worsen the Omega problem by encouraging more tool use. Must feature-flag and gate on Omega improvement.

---

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-295 | FFF.nvim: Frecency-Based Fuzzy File Finder | medium | worth_investigating |
| intake-301 | AXI: Agent eXperience Interface | medium | already_integrated (TOON core); design principles remain |

---

## S1: Frecency File Discovery (intake-295)

EPYC's REPL currently has **zero temporal signal** for file navigation. All discovery is semantic (NextPLAID `code_search`) or regex (`grep`/`peek`). No recency or frequency weighting exists.

FFF.nvim's frecency + combo-boost pattern fills this gap:

- **Data model**: `{path: str, access_count: int, last_access: float, frecency_score: float}`
- **Storage**: SQLite in `epyc-orchestrator/data/file_recency.db` (survives reboots, unlike tmp/)
- **Scoring**: `score = freq_weight * ln(access_count + 1) + recency_weight * exp(-age_hours / half_life)`
- **Combo boost**: Track `(query, file)` pairs; amplify score on repeat access patterns

### Integration points

1. **`_list_dir()`** (`file_exploration.py:181`): Sort entries by frecency score (dirs first, then frecency within each group)
2. **`code_search()`** (`code_search.py`): Multiply NextPLAID semantic score by recency boost for recently-modified files
3. **Governance layer**: At root-repo level, frecency could prioritize which handoffs/progress files agents check first
4. **ColGREP bridge**: ColGREP (CLI colbert search) was BLOCKED on upstream ONNX panic in v1.0.6; **unblocked 2026-04-29 by upgrade to v1.2.0** (see Research Intake Update — 2026-04-14 below). Frecency remains a complementary temporal signal regardless.

### Work items

- [x] S1a: Implement `file_recency.py` module with frecency scoring + SQLite persistence — ✅ 2026-04-09. `FrecencyStore` class, SQLite at `data/file_recency.db`, scoring formula with combo boost, 10 tests.
- [x] S1b: Wire into `_list_dir()` with feature flag (`REPL_FRECENCY`) — ✅ 2026-04-09. Lazy import, dir-first then frecency sort, graceful degradation.
- [x] S1c: Wire into `code_search()` with recency boost multiplier (feature-flagged) — ✅ 2026-04-09. Score × (1 + 0.3 × frecency), re-sorted. 7 wiring tests.

---

## S2: Combined Operations (intake-301)

AXI's combined-operations principle: batch multi-step REPL patterns into single calls, reducing round-trips. AXI achieved 4.5 turns/task vs typical 8-11.

### Approach

1. **Mine autopilot logs** for high-frequency multi-tool turn patterns (e.g., `list_dir` immediately followed by `peek`, `grep` followed by `code_search`)
2. **Define combined operations** for top-3 patterns (e.g., `peek_grep`: peek + grep in single output, `explore_dir`: list_dir + peek top-N files)
3. **Implement as new methods** on `REPLEnvironment` that call multiple existing methods and return consolidated output
4. **TOON-encode** the combined output using existing `toon_encoder.py`

### Work items

- [x] S2a: Mine autopilot logs for multi-tool turn patterns — ✅ 2026-04-09. `inference_tap.log` does NOT exist; used `autopilot.log` + `seeding_diagnostics.jsonl`. Finding: only web_search (94.8%) and search_wikipedia (5.2%) used. File exploration tools never called. 85% sessions zero-tool. Report: `docs/repl_pattern_analysis.md`.
- [x] S2b: Implement combined operations as REPL mixin (feature-flagged) — ✅ 2026-04-09. `_CombinedOpsMixin` with `batch_web_search` (addresses 5727 web_search→web_search bigrams), `search_and_verify` (171 bigrams), `peek_grep` (preemptive). Feature flag `REPL_COMBINED_OPS`. 18 tests.

---

## S3: Contextual Suggestions (intake-301)

After each tool output, append 2-3 likely next commands based on frecency data + tool co-occurrence statistics.

### Design

- **Source**: Frecency data (S1) + tool co-occurrence from autopilot logs (S2a)
- **Format**: Brief TOON-encoded suggestion block at end of output
- **Risk**: Suggestions may bias model toward tool use when direct reasoning is better — directly conflicts with the Omega finding. **Must gate on Omega improvement.**

### Work items

- [x] S3a: Prototype contextual suggestions (behind feature flag `REPL_SUGGESTIONS`, default OFF) — ✅ 2026-04-11. Implemented `suggestions.py` (`_SuggestionsMixin`, co-occurrence engine, 17 tests). Feature flag `REPL_SUGGESTIONS` (default OFF).

---

## S4: Benchmark

- [ ] S4: A/B benchmark turn count reduction on seeding harness — measure turns/task, token cost/task, accuracy delta

---

## S7: ColGREP CLI Integration as `code_search()` Replacement (2026-04-29)

Triggered by intake-355 v1.2.0 unblock (see Research Intake Update — 2026-04-14 above). Scoping decision: replace `code_search()` only — `doc_search()` stays on NextPLAID GTE since ColGREP is code-focused via tree-sitter and a poor fit for prose.

### Bench results (2026-04-29)

- **Indexing**: 312 code units in `/mnt/raid0/llm/epyc-orchestrator/src` indexed in **13.6 s wall-clock** (CPU, no CUDA, ~1800% CPU saturated across 18 cores). 30 MB index at `~/.local/share/colgrep/indices/`. v1.2.0's 7× pipelined-indexing speedup is real.
- **Query latency**: cold 220 ms ± 3 ms per query (5/5 trials), warm identical (no daemon mode → no warm benefit, but also no penalty). Subprocess+ONNX-runtime startup is amortized into ColBERT inference well. ~2× slower than typical NextPLAID HTTP path (~100 ms in-container Python client) but invisible at human REPL timescales.
- **Quality (7-query A/B vs known-target ground truth)**: 6/7 top-1 dead-on (`file_recency.py`, `toon_encoder.py`, `code_search.py`, `combined_ops.py`, `repl_environment/context.py`, `dspy_signatures/frontdoor.py` in top-3). The 7th (NUMA pinning) returned the actual NUMA wrappers (`lightonocr_llama_server.py`, `backends/llama_server.py`) rather than the orchestrator caller — arguably *better* than the hint.
- **Hybrid scoring quirk**: ColGREP fuses FTS5 + ColBERT via Reciprocal Rank Fusion, so result scores are unbounded fused values (~1–5 range) not the normalized 0–1 NextPLAID returns. Frecency boost (0.3 × score multiplier) still rank-stable. Only flag if downstream code makes assumptions about score scale.

### Wiring

- [x] `_colgrep_search()` helper in `src/repl_environment/code_search.py` — subprocess-call to `/mnt/raid0/llm/UTILS/bin/colgrep search ... --json`, normalizes results to existing schema (file/lines/score/unit/signature), forces CPU via `NEXT_PLAID_FORCE_CPU=1`.
- [x] `REPL_COLGREP` env flag (default OFF) gates routing in `_code_search()`. `_doc_search()` unaffected.
- [x] Configurable via `REPL_COLGREP_BIN` (default `/mnt/raid0/llm/UTILS/bin/colgrep`) and `REPL_COLGREP_PATH` (default orchestrator `src/`).
- [x] Falls back to NextPLAID on missing binary, timeout (10 s), non-zero exit, or malformed JSON — callers always get a valid response shape.
- [x] 7 new tests in `tests/unit/test_code_search.py::TestColgrepIntegration` (flag-off baseline, flag-on routing, 4 fallback paths, doc_search isolation). Full suite: **27/27 pass**.
- [x] Live smoke test passed: `REPL_COLGREP=1` against the indexed orchestrator returned correct top-3 results with AST metadata.

### Container sunset evaluation (2026-04-29) — initial verdict: NO-GO; revised after live A/B: GO with caveats

29-query at-scale eval (`/mnt/raid0/llm/UTILS/colgrep_ab_eval.py`) ran from this environment. **NextPLAID containers (8088/8089) were unreachable from the overlay env**, so the initial eval was colgrep-only.

**Gates verified:**

| Gate | Result | Notes |
|---|---|---|
| Fallback rate on diverse stress | **0/29** | No runtime errors across symbol queries, concept queries, gibberish, special chars, very long queries, empty-corpus queries. All returned valid response shapes. |
| Fallback paths actually engage | **✓** | Unit tests cover all four (`missing binary`, `timeout`, `non-zero exit`, `bad JSON`); each falls back to NextPLAID. 7/7 tests pass. |
| Latency steady-state | **p50 224 ms, p95 ~272 ms** | Tight distribution after first query. **First-query cold-start outlier ~2.3 s** (model load on first subprocess) — relevant if many sessions are short-lived. |
| Top-1 quality (alpha=0.95) | **10/14 = 71%** | Up from 9/14 = 64% at default alpha=0.75; the bump from alpha tuning fixes 3 of 5 misses caused by FTS5 re-ranking `__init__.py` re-exports above the actual definition file. Remaining misses: corpus-structural (e.g. `FinalSignal` query → `restricted_executor.py` instead of `types.py`). |

**Gates NOT verified (cannot from this env):**

| Gate | Why not |
|---|---|
| Live A/B vs running NextPLAID | Connection refused on `localhost:8088` and `:8089` from this overlay. NextPLAID baseline on the same query set is the missing comparator. |
| Quality parity | 71% top-1 in isolation says nothing about NextPLAID's number on the same set — could be higher, lower, or equal. |
| Behavior under concurrent load | Single-process subprocess test only; multi-agent contention untested. |
| Incremental re-index on commit | Not yet wired. |

**Initial verdict: NO-GO on container sunset.** The 71% top-1 quality is below the "≥ parity with no regression" threshold I'd want before retiring infrastructure that's working today, and we have no NextPLAID baseline to compare against. ColGREP is **production-viable as an opt-in** (set `REPL_COLGREP=1`) but not a confident replacement yet.

### Live A/B addendum (2026-04-29, post-verdict)

User started just `nextplaid-code` (port 8088) via a one-shot launcher (`/mnt/raid0/llm/UTILS/launch_nextplaid_code_only.py`) so a paired comparison became possible from this env. Note the index-scope mismatch: NextPLAID-code indexed **8826 documents** (whole project incl. `tests/`, `scripts/`, `orchestration/`, etc per the original Phase 5 scope); colgrep indexed **312 units** in `src/` only.

Two API shims were needed for the run (NOT applied to production code):

1. `next_plaid_client` package not in this env → `pip install next-plaid-client==1.0.8` (closest available to server cpu-1.0.4).
2. Production `code_search.py` calls `client.search_with_encoding()`, but PyPI clients ≥1.0.8 renamed it to `client.search()`. A.B. script monkey-patches `NextPlaidClient.search_with_encoding = NextPlaidClient.search` at import time. Functionally equivalent for our query shape.

**Paired results (n=14 ground-truth queries, identical input):**

| Engine | Top-1 | Top-3 | p50 latency | p95 latency |
|---|---|---|---|---|
| colgrep | **10/14 (71%)** | **13/14 (93%)** | 964 ms (cold; 224 ms steady when warm) | 2.8 s |
| NextPLAID | 2/14 (14%) | 4/14 (29%) | 190 ms | 5.5 s |
| Top-1 agreement | 0/14 | — | — | — |

ColGREP wins **decisively** on quality (~5× better top-1, ~3× better top-3). NextPLAID lost 8/14 queries to landings in `tests/` files (e.g. `tests/unit/test_repl_executor.py`, `tests/integration/test_model_tool_compliance.py`) — i.e. test code that mentions the queried symbol heavily. This is a **corpus-scope problem, not a ranking-engine problem**: NextPLAID indexed the whole project; colgrep only indexed `src/`.

NextPLAID is ~5× faster on p50 (190 ms vs 964 ms cold) but has worse worst-case (5.5 s vs 2.8 s). For a per-turn REPL invocation the absolute difference (~770 ms) is invisible to humans but real for high-frequency tool loops.

**Revised verdict: GO on sunset, with caveats.**

The strict-equivalence comparison hasn't been done — we'd need to re-index NextPLAID against `src/` only to know whether NextPLAID-on-clean-corpus could match colgrep. But that's a fairness exercise, not a production decision. For the actual `code_search()` use case (production-code retrieval, not test code), colgrep's narrower scope is **a feature, not a limitation** — it produces better results because the corpus is cleaner.

Reasons to GO:
1. Quality: 5× better top-1, 3× better top-3 on production-code queries.
2. Operational simplicity: one Rust binary vs Docker container with separate Python client. 30 MB index vs 1.86 M embeddings (~31 GB resident).
3. Hybrid scoring: FTS5 + ColBERT fusion handles symbol queries that pure ColBERT misses.

Caveats:
1. ~770 ms cold-start hit per query (subprocess + ONNX load). Acceptable for human-paced REPL; relevant for high-frequency batch use. Mitigation: sidecar daemon (follow-up #2).
2. Apples-to-apples engine comparison (same corpus scope) not done. NextPLAID could close most of the quality gap if re-indexed on `src/` only, but that's a separate experiment.
3. `doc_search()` stays on NextPLAID (port 8089) — colgrep is code-focused.

**Sunset action**: switch `REPL_COLGREP=1` from opt-in to default; keep NextPLAID container running for one rollout window with `engine: nextplaid` fallback events tracked in `_exploration_log`; if no fallback events for ~1 week of normal traffic, retire the code container (free ~31 GB RAM). NextPLAID-docs (port 8089) untouched.

### 2026-04-29 (later) — Default flipped to colgrep

`_colgrep_enabled()` semantics flipped: default ON; explicit `REPL_COLGREP=0`/`false`/`off` opts back into NextPLAID. Module docstring + comment updated to reflect new default. Two new tests added (`test_explicit_off_uses_nextplaid`, `test_explicit_false_uses_nextplaid`); legacy `test_flag_off_uses_nextplaid` reframed as `test_flag_unset_uses_colgrep_by_default`. Shared `repl` fixture sets `REPL_COLGREP=0` so existing NextPLAID-shape tests keep passing without modification. **Full suite: 29/29 pass.**

End-to-end smoke confirmed:
- `REPL_COLGREP` unset → `engine: colgrep` in response (default ON works).
- `REPL_COLGREP=0` → `engine` field absent (NextPLAID path engages, opt-out works).

The user explicitly chose ship-now over the 1-week soak I recommended. Rationale captured: trust in the 5× quality signal outweighs cold-start regression risk; flag mechanism allows instant rollback via env var. Soak telemetry still applies — if `_exploration_log` shows fallback events or quality complaints surface, set `REPL_COLGREP=0` in the orchestrator runtime env to revert without redeploy.

**Concrete defaults shipped in code:**
- `REPL_COLGREP_ALPHA=0.95` (overridable via env). Default 0.75 over-ranks `__init__.py` re-exports for symbol queries; 0.95 fixes most cases.
- All four fallback paths preserved.
- `engine: "colgrep"` field in response lets `_exploration_log` track per-query engine; NextPLAID fallbacks omit it.

NextPLAID docs container (port 8089) stays — `doc_search()` remains on it regardless.

### Follow-ups (priority order)

1. ~~**Run host-side A/B** — only the orchestrator runtime can hit both engines simultaneously. Same 29-query script, swap engines per query, log to JSONL, compute paired top-1 deltas.~~ — **DONE 2026-04-29** (see "Live A/B addendum" above; results triggered the GO verdict and default flip).
2. **Cold-start daemon decision** — see [§ Cold-start daemon options](#s7-cold-start-daemon-options) below for the full evaluation. Defer the work; revisit only if soak telemetry shows the hit is real.
3. **Pin a versioned binary path** (e.g. `/mnt/raid0/llm/UTILS/bin/colgrep-1.2.0`) so future upgrades are explicit.
4. **Incremental re-indexing on commit** (tree-sitter is fast; should be <5 s for typical commits).
5. **Investigate the corpus-structural misses** (`FinalSignal` query missing `types.py`) — possibly improvable with `--code-only` or a tighter `--exclude-dir` filter on test/`__pycache__` dirs.

### S7: Cold-start daemon options

**The cost being mitigated.** Every `_colgrep_search()` call spawns a fresh `colgrep` subprocess that loads ONNX runtime + the LateOn-Code-edge ColBERT weights from `~/.cache/onnxruntime` / `~/.cache/huggingface`. Measured cost on EPYC 9655 (CPU, no CUDA, model files already on disk):

| Phase | Cost | Notes |
|---|---|---|
| First subprocess after long idle | **~2.3 s** | Worst case (29-query stress, query 1 hit 2.3 s) |
| Steady-state cold | **~770 ms** (live A/B p50) to **~220 ms** (small-index solo eval p50) | Wide range driven by index size + query length |
| Per-query *engine* time minus startup | hundreds of ms | ColBERT inference + index lookup |

The `subprocess+ONNX-load` portion is not amortized across queries: each subprocess starts from a clean OS process state, so even back-to-back queries pay it.

**Build-trigger criteria.** Don't build a daemon unless soak data shows at least one of:
1. p50 `code_search()` latency ≥ 600 ms across a full seeding run (`_exploration_log` median), AND
2. ≥ 20 % of REPL turns issue ≥ 2 `code_search()` calls (high-frequency pattern where cold-start compounds), OR
3. A single agent role is consistently making ≥ 1 `code_search()` per second for ≥ 30 s (batch workload).

If none of those hold, subprocess-per-query is the right shape and a daemon is gold-plating.

**Path A — homegrown sidecar wrapper.** A small long-lived process that imports/spawns colgrep once, keeps the model resident, and exposes a Unix-socket (or stdin/stdout JSON-RPC) protocol for queries.

- Pros: full control over lifecycle, easy to integrate with `orchestrator_stack.py`'s existing process model, minimal new dependencies.
- Cons: we'd be re-implementing what NextPLAID already gives us as a service. Risk of drifting from upstream colgrep semantics on every CLI bump.
- Effort: ~1 engineering day if Python wrapper that holds an `onnxruntime.InferenceSession` open. Closer to ~2-3 days if we want the wrapper to also share the index handle and handle re-indexing under load.
- Concrete sketch: socket-server in Python that lazily imports `next_plaid_client` (since it's the same engine as colgrep), holds a `NextPlaidClient` against a local index dir, and answers `{query, k, alpha}` requests in JSON. `_colgrep_search()` switches from `subprocess.run([colgrep, ...])` to `socket.send_json(...)`. Fall back to subprocess if the socket isn't there.

**Path B — upstream Python SDK CLI (recommended if we end up needing this).** v1.2.0 of NextPlaid shipped a `next-plaid` Python SDK CLI:

```bash
pip install "next-plaid-client[cli]"
next-plaid index list
next-plaid search "query" --index code -k 5
```

Per the v1.2.0 release notes (2026-04-10): *"A new `next-plaid` CLI provides full SDK parity: index management, document add/delete, search (semantic/keyword/hybrid), metadata operations, encoding, and reranking. Designed for agents: non-interactive flags, `--dry-run`/`--yes` for destructive ops, stdin support, and actionable errors. Ships with 80 unit tests."*

This is the same engine family colgrep uses. Long-lived shape: run a small Python service that holds the SDK client open against a local index directory, accept queries over a socket. Net effect: the **homegrown sidecar in Path A but with upstream-maintained internals** instead of our own ONNX wrangling. Same trade-offs vs Path A, minus the maintenance risk.

- Pros: upstream-maintained engine; index format is compatible with whatever colgrep produced (same NextPlaid core); 80 unit tests upstream; SDK already pinned in our orchestrator dep set (`pyproject.toml` lists `next_plaid_client` transitively via `code_search.py`).
- Cons: we're back to having a long-lived Python process that needs lifecycle management — i.e. an `orchestrator_stack.py` entry — which is the operational simplicity we just gained by adopting colgrep CLI. The sunset of `nextplaid-code` Docker would partly walk-back here (still smaller: no Docker, just a venv'd Python process).
- Effort: ~1 day. Most of the work is the wrapper + socket protocol + `orchestrator_stack` integration, not the SDK itself.

**Decision rule:** if the build-trigger criteria above fire, prefer Path B over Path A unless we have a specific reason to deviate (e.g., wanting CLI semantics exactly because they match the published colgrep behavior). Either path keeps the `_code_search()` integration shape unchanged from the consumer's perspective — the `engine: "colgrep"` field can stay as the user-visible signal even if the wire path is now socket-to-daemon.

**Where to put it if/when it ships.** Sidecar belongs in `epyc-orchestrator/scripts/server/` (same directory as `orchestrator_stack.py`); Python wrapper code goes in `epyc-orchestrator/src/repl_environment/colgrep_daemon_client.py` so `_colgrep_search()` can switch transports based on a feature flag (`REPL_COLGREP_DAEMON_SOCKET=/run/colgrep.sock` or similar) with subprocess as fallback.

Eval script + raw outputs preserved at `/mnt/raid0/llm/UTILS/colgrep_ab_eval.py`.

---

## Key Files

| Resource | Path |
|----------|------|
| REPL environment | `epyc-orchestrator/src/repl_environment/` |
| File exploration | `epyc-orchestrator/src/repl_environment/file_exploration.py` |
| Code search | `epyc-orchestrator/src/repl_environment/code_search.py` |
| Parallel dispatch | `epyc-orchestrator/src/repl_environment/parallel_dispatch.py` |
| Tool descriptions | `epyc-orchestrator/src/prompt_builders/constants.py` |
| TOON encoder | `epyc-orchestrator/src/services/toon_encoder.py` |
| Autopilot logs | `epyc-orchestrator/logs/inference_tap.log` |

---

## Cross-References

| Handoff | Relationship |
|---------|-------------|
| [tool-output-compression.md](tool-output-compression.md) | Complementary: definition compression + turn reduction |
| [meta-harness-optimization.md](meta-harness-optimization.md) | AP-16 instruction budget tracking applies to combined-op descriptions |
| [routing-and-optimization-index.md](routing-and-optimization-index.md) | WS-2 Omega re-measurement validates turn efficiency gains |
| [colbert-reranker-web-research.md](colbert-reranker-web-research.md) | ColGREP blocked; frecency is alternative temporal signal |
| [research-evaluation-index.md](research-evaluation-index.md) | Tracked under P6 |
| [autopilot-continuous-optimization.md](autopilot-continuous-optimization.md) | P11/AP-25: dspy.RLM integration — REPL patterns (metadata-first context, SUBMIT()) |

## S5: dspy.RLM REPL Patterns (cross-ref autopilot P11)

(cross-reference analysis complete 2026-04-12, implementation proposals ready for prioritization)

Source: intake-331 (predict-rlm), intake-349 (dspy.RLM). DSPy infrastructure installed in AP-18 (`src/dspy_signatures/`), RLM dual-LM config wired in AP-25 (`configure_rlm` — coder as main LM, frontdoor as sub_lm). AP-26 (RLM integration testing) still pending inference.

### Pattern Mapping

| dspy.RLM Pattern | Current REPL Feature | Gap |
|---|---|---|
| Metadata-first exploration (sub_lm scans workspace structure before main LM acts) | `_RoutingMixin._recall()` — MemRL episodic retrieval returns Q-value-ranked past tasks + `_route_advice()` for routing decisions | No workspace scan tool. Multi-turn `list_dir` chains waste turns because `_recall()` only searches episodic memory (past tasks), not the live file tree. Models must chain `list_dir` -> `peek` -> `list_dir` to orient, often 3-4 turns before productive work begins. |
| SUBMIT() termination (explicit success signal with structured output) | `FINAL("answer")` signal (`context.py:169`) raises `FinalSignal` exception to halt REPL loop; enforces `min_exploration_calls` gate | No `STUCK("reason")` signal. When a model hits a dead end (wrong file, missing context, tool error), it either wastes turns retrying or emits a low-quality `FINAL`. The only escape hatch is `_escalate(reason)`, which requests a different model entirely — there is no lightweight "I need help with X" signal that stays within the current turn budget. |
| `llm_query_batched()` + `asyncio.gather()` (concurrent LLM inference for independent sub-queries) | `parallel_dispatch.py` — `ThreadPoolExecutor` for concurrent read-only tool calls (AST-analyzed, max 4 workers); `llm_batch()` / `llm_batch_async()` in `LLMPrimitives` for multi-prompt inference | No concurrent LLM inference batching at the REPL tool level. `parallel_dispatch.py` parallelizes tool calls (peek, grep) but not LLM calls. `llm_batch()` exists in primitives but is not exposed as a REPL combined-op. Models that need multiple sub-queries (e.g., "summarize sections A, B, C") must call `llm_call()` sequentially or know to use `delegate(parallel=True)`, which has high overhead (full context injection per item). |

### Improvement Proposals

**Gap 1 — Workspace scan tool (`workspace_scan`)**

Add a `_workspace_scan(query)` method to `_CombinedOpsMixin` that performs metadata-first exploration in a single turn: `list_dir` of project root + frecency-ranked file list + `code_search` hit summary. This mirrors dspy.RLM's sub_lm pre-scan where the cheap model gathers workspace structure before the main model commits to an action plan. The frontdoor model (already configured as `sub_lm` in `configure_rlm`) could power the scan via `dspy.context(lm=sub_lm)`, keeping main model context clean. Implementation: extend `_CombinedOpsMixin` with a new method that chains `list_dir(".")` + `FrecencyStore.top_k(10)` + `code_search(query, limit=5)` into a single TOON-encoded result. Estimated effort: 4-6 hours (method + tests + feature flag).

> **Independent validation (added 2026-04-24, intake-451)**: the meta-harness official-code deep-dive surfaced that the published `terminal_bench_2` artifact uses an analogous one-shot workspace snapshot during environment bootstrapping to keep the agent from burning turns on orientation. That is the same pattern as Gap 1 here, arrived at independently by Stanford IRIS Lab. See [`research/deep-dives/meta-harness-official-reference-code.md`](../../research/deep-dives/meta-harness-official-reference-code.md) for the cross-validation. No change to priority — already HIGH impact/MEDIUM effort — but lowers our uncertainty that this is the right shape.

**Gap 2 — `STUCK("reason")` signal**

Add a `STUCK(reason, context={})` function alongside `FINAL()` in `context.py`. When called, it does NOT terminate the REPL loop. Instead it: (a) logs the stuck reason to `_exploration_log`, (b) queries `_recall()` for similar stuck situations and their resolutions, (c) returns a guidance block with suggested recovery actions (from co-occurrence data in `_SuggestionsMixin`), and (d) resets the turn counter partially so the model gets a few more attempts. This is lower-cost than `_escalate()` (which swaps models) and more structured than the model just retrying blindly. Implementation: add `_stuck()` to `_ContextMixin` in `context.py`, wire episodic recall for recovery patterns. Estimated effort: 6-8 hours (signal + recovery logic + tests + prompt update to teach models about STUCK).

**Gap 3 — REPL-level `llm_batch` combined-op**

Expose `llm_batch()` as a first-class REPL tool rather than requiring models to know about `LLMPrimitives` internals. Add `_batch_llm_query(prompts, role)` to `_CombinedOpsMixin` that wraps `llm_primitives.llm_batch()` with TOON encoding, exploration counting, and the same feature flag as other combined ops. For async contexts (future), bridge to `llm_batch_async()` with `asyncio.gather()` — the implementation already exists in `primitives.py:707` but is unreachable from the REPL sandbox. Estimated effort: 3-4 hours (thin wrapper + tests; the hard work is already done in `LLMPrimitives`).

### Dependencies

| Dependency | Status | Required For |
|---|---|---|
| AP-18: DSPy signatures installed (`src/dspy_signatures/`) | Done (2026-04-12) | All S5 proposals (DSPy import path) |
| AP-25: `configure_rlm(main_lm, sub_lm)` | Done (2026-04-12) | Gap 1 (sub_lm for workspace scan) |
| AP-26: RLM integration testing | Pending (needs inference) | Validating sub_lm scan quality |
| S1a: `FrecencyStore` | Done (2026-04-09) | Gap 1 (frecency-ranked file list in scan) |
| S3a: `_SuggestionsMixin` | Done (2026-04-11) | Gap 2 (co-occurrence data for recovery suggestions) |
| S2b: `_CombinedOpsMixin` | Done (2026-04-09) | Gaps 1 and 3 (host mixin for new methods) |
| S4: A/B benchmark | Pending | Measuring turn reduction from all S5 proposals |

### Priority Ranking (impact per effort hour)

1. **Gap 3 — `_batch_llm_query` combined-op** (HIGH impact / LOW effort). 3-4 hours. The underlying `llm_batch()` already works; this is purely a REPL exposure issue. Every multi-sub-query task (common in agentic/coder suites) benefits immediately. Unblocked now.
2. **Gap 1 — `workspace_scan` tool** (HIGH impact / MEDIUM effort). 4-6 hours. Directly targets the 3-4 wasted orientation turns observed in file-exploration tasks. Blocked on AP-26 for sub_lm quality validation, but can be built with frecency-only fallback first.
3. **Gap 2 — `STUCK("reason")` signal** (MEDIUM impact / MEDIUM-HIGH effort). 6-8 hours. Reduces wasted turns on dead-end paths, but the recovery logic (episodic recall for similar stuck situations) adds complexity. Should be built after Gap 1/3 prove the combined-op pattern works at the REPL level.

## S6: Specialist REPL Bug Fixes + Observability (2026-04-16)

Session discovered and fixed 3 systemic bugs causing ~25% wasted specialist REPL turns (810/3227 calls), plus added web_search/web_fetch to REPL globals and role-aware specialist prompts.

- [x] S6a: Fix `extract_code_from_response` dropping bare `"""` lines (473 NameErrors) — `code_utils.py`
- [x] S6b: Fix `CALL("run_python_code")` routing through registry instead of REPL globals (182 ValueErrors) — `context.py`
- [x] S6c: Fix dedup guard `continue` → `break` (63 wasted turns) — `chat_delegation.py`
- [x] S6d: Add `repl_turn_errors` tracking to delegation stats + `specialist_repl_errors` anomaly signal — `chat_delegation.py`, `anomaly.py`
- [x] S6e: Add `web_search()` REPL global + document in `root_lm_system.txt` — `combined_ops.py`, `environment.py`, `root_lm_system.txt`
- [x] S6f: Role-aware `_build_compact_specialist_prompt` — search roles get web tool docs + REPL math guidance — `chat_delegation.py`

See: `progress/2026-04/2026-04-16.md` for full details.

---

## Research Intake Update — 2026-04-14

### New Related Research
- **[intake-355] NextPlaid/ColGREP** (github:lightonai/next-plaid)
  - Relevance: NextPlaid is the deployed multi-vector search engine backing code_search() and docs retrieval (ports 8088/8089). ColGREP adds semantic code search for terminal/agents. v1.2.0 released 2026-04-10.
  - Key update: ColGREP now offers native Claude Code integration. Combines regex filtering with semantic ranking via ColBERT-style multi-vector embeddings (~300 embeddings per code unit, MaxSim scoring). Fully local, single Rust binary.
  - Status (2026-04-29): **CLI bridge unblocked.** v1.0.6 panicked on ONNX/GPU init because EPYC has no CUDA/cuDNN. v1.2.0 changelog: "panic-based error output during GPU initialization is replaced with clear fallback messages" + new `--force-cpu` / `NEXT_PLAID_FORCE_CPU` knob. Validated end-to-end: `colgrep init` + `colgrep search` on a 2-file sample falls back to CPU cleanly (`cuDNN not found, encoding will use CPU.`) and returns correctly ranked semantic results. Binary installed at `/mnt/raid0/llm/UTILS/bin/colgrep` (v1.2.0, 80 MB). NextPLAID-backed `code_search()` integration unchanged (GTE-ModernColBERT-v1 swap remains active per colbert-zero-research-integration).
  - Action: Decide whether to wire ColGREP into the REPL as a new tool (e.g. `colgrep_search()`) or as a *replacement* for one of the existing search paths. Per the Omega finding, prefer replacement over additive surface. Full orchestrator-codebase index not yet run — defer until decision is made. Default index path is `~/.local/share/colgrep/indices/`; if running at scale, symlink to RAID first (per archived `nextplaid-phase5-upgrade.md` note).

## Research Intake Update — 2026-04-17

### New Related Research

- **[intake-397] "Open Agents — Vercel-Labs Reference App for Background Coding Agents"** (repo: vercel-labs/open-agents)
  - Relevance: durable workflow with reconnect-to-stream semantics as a model for long-running REPL sessions surviving disconnects; explicit control-plane / execution-sandbox separation.
  - Key technique: Vercel Workflow SDK multi-step durable runs with streaming + cancellation + reconnect; snapshot-based sandbox hibernate/resume; GitHub-integrated branch→commit→PR flow driven by the agent.
  - Delta: patterns (durable-reconnect, snapshot-resume, control-plane separation) are directly analogous to the REPL turn-efficiency goal of stable long-horizon sessions without wasted turns on reconnection.

- **[intake-399] "GenericAgent: minimal self-evolving autonomous agent framework"** (repo: lsdefine/GenericAgent)
  - Relevance: 9 atomic tools + 100-line agent loop + <30K context budget is a concrete reference for minimizing wasted turns by reducing decision surface.
  - Key technique: minimal atomic tool set with dynamic tool creation via `code_run`; layered L0–L4 memory replaces full-context scanning.
  - Delta: design pressure toward smaller tool surfaces and skill crystallization of repeat tasks (so repeat requests become one-line invocations instead of multi-turn re-derivations).

## Research Intake Update — 2026-04-24

### New Related Research

- **[intake-454] "hermes-agent v2026.4.23 (v0.11.0)"** (`github.com/NousResearch/hermes-agent/releases/tag/v2026.4.23`)
  - Relevance: release adds `/steer <prompt>` mid-run course correction that avoids aborting the turn — directly relevant to per-turn efficiency work. Also adds compressor smart-collapse + dedup + anti-thrashing which reduces context churn across turns.
  - Key technique: mid-run steer without turn termination; compressor fallback-to-main-model chain (503/404) that prevents context-corruption retries.
  - Delta: `/steer` is an alternative to the "abort + restart with correction" pattern; evaluate whether it reduces net turns in the ~3-5-turn corrections we see in transcripts. Compressor fallback chain removes a class of "compressor failed → retry whole turn" waste.

- **[intake-451] "Meta-Harness (official reference code)"** (`github.com/stanford-iris-lab/meta-harness`)
  - Relevance: scaffold-evolution example in terminal_bench_2 is a reference for systematically searching over REPL workflow scaffolds (tool-use templates, planning prompts) instead of hand-tuning.
  - Delta: potential Tier-3 work — apply meta-harness scaffold-search to the REPL harness itself once Tier-1/2 skill-crystallization baseline is stable.

- **[intake-450] "Venice Skills — Agent Skills for the Venice.ai API"** (`github.com/veniceai/skills`)
  - Relevance: ≤500-line SKILL.md rubric with explicit "gotchas" section — directly applicable to the skill-crystallization output format.
  - Delta: adopt the authoring rubric as the canonical template when crystallizing repeat REPL flows into skills.

## Research Intake Update — 2026-04-26

### New Related Research

- **[intake-473] "@mariozechner/pi-agent-core — Stateful TypeScript Agent Runtime"** (`github.com/badlogic/pi-mono/tree/main/packages/agent`)
  - Relevance: ships **steering vs follow-up as two distinct named primitives** — exactly the user-typed-mid-response vs user-typed-after-response split that this handoff currently lacks vocabulary for. `steer(message)` injects before the next assistant turn (drained at every turn boundary while the agent is running); `followUp(message)` queues for after the agent would otherwise stop (drains only when no more tool calls remain). Two queues, not one. Preserves the ordering distinction the Omega problem is sensitive to.
  - Key technique: each queue has a `mode: "all" | "one-at-a-time"` switch. Default `one-at-a-time` is a backpressure model — if the user types 4 messages while the LLM is mid-response, the agent absorbs one per turn rather than seeing all 4 jammed together at the next turn boundary. Order preserved, but agent isn't overloaded with bursty input. The mode is mutable at runtime via setter.
  - Delta from current approach: this handoff's S3 contextual-suggestions work feature-flags the suggestion injection because it might worsen Omega; the pi-agent-core mode switch is the same problem framed as a first-class API knob rather than a hidden flag. Adopt the *vocabulary* (steer / follow-up / queue mode) in the orchestrator's request-handling layer even before any code port — naming alone clarifies whether a given REPL-turn change is steering (mid-flight) or follow-up (post-completion) and lets the Omega gate target the right one.
  - Implementation refs (if porting):
    - `agent.ts:113-144` — `PendingMessageQueue` with `drain()` semantics that differ by mode.
    - `agent.ts:252-280` — `steer` / `followUp` / `clearSteeringQueue` / `clearFollowUpQueue` / `hasQueuedMessages` API surface.
    - `agent-loop.ts:165, 218, 222` — twice-per-turn polling pattern that lets steer arrive without losing the in-flight tool batch.
  - Deep-dive: `research/deep-dives/pi-agent-core-stateful-ts-runtime.md`
