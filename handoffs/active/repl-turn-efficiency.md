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
4. **ColGREP bridge**: ColGREP (CLI colbert search) is BLOCKED on upstream ONNX panic. Frecency provides a cheap alternative temporal signal while ColGREP is down.

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
  - Status: Already integrated (GTE-ModernColBERT-v1 swap completed per colbert-zero-research-integration). ColGREP CLI still blocked on upstream ONNX panic per existing notes. Frecency fallback remains active.
  - Action: Monitor v1.2.0 for ONNX panic fix that would unblock ColGREP CLI bridge

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
