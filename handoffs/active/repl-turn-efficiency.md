# REPL Turn Efficiency — Frecency Discovery + Combined Operations

**Status**: in-progress (S1a-c done, S2a-b done, S3a done 2026-04-11, S4 pending inference)
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

- [ ] S3a: Prototype contextual suggestions (behind feature flag `REPL_SUGGESTIONS`, default OFF)

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
