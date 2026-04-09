# LangGraph Migration — Orchestration Graph

**Status**: phase-2-complete
**Created**: 2026-03-15
**Updated**: 2026-04-05
**Source**: intake-146 (LangGraph), deep-dive `research/deep-dives/langgraph-ecosystem-comparison.md`

## Objective

Migrate from pydantic_graph to LangGraph for the orchestrator's agent graph. The 7 typed nodes across 4 model tiers already function as mini-agents that escalate/delegate to each other — LangGraph formalizes this with subgraph composition, durable checkpointing, interrupt() flexibility, and state immutability with reducers, while preserving our domain-specific features (MemRL, escalation ladder, feature flags, think-harder, 5-layer context management).

## Background

Our orchestrator is a heterogeneous multi-agent system built on pydantic_graph v1.56.0 with compile-time type-safe transitions (Union return types). LangGraph provides a superset of graph execution capabilities. Deep-dive analysis (2026-03-15) identified 5 architectural gaps where LangGraph is stronger; Gaps 2-4 (subgraph composition, interrupt flexibility, state immutability) are the primary motivation.

## Current Architecture (pydantic_graph)

### Graph Topology

**Singleton**: `epyc-orchestrator/src/graph/graph.py:31` — `Graph[TaskState, TaskDeps, TaskResult]`

```
FrontdoorNode  ──(self-loop)───────► FrontdoorNode
               ──(escalate)────────► CoderEscalationNode
               ──(final)──────────► End[TaskResult]

WorkerNode     ──(self-loop)───────► WorkerNode
               ──(escalate)────────► CoderEscalationNode
               ──(final)──────────► End[TaskResult]

CoderNode      ──(self-loop)───────► CoderNode
               ──(escalate/model)──► ArchitectNode
               ──(final)──────────► End[TaskResult]

CoderEscalationNode ──(self-loop)──► CoderEscalationNode
                    ──(escalate)───► ArchitectCodingNode
                    ──(final)──────► End[TaskResult]

IngestNode     ──(self-loop)───────► IngestNode
               ──(escalate)────────► ArchitectNode
               ──(final)──────────► End[TaskResult]

ArchitectNode         ──(self-loop)► ArchitectNode (terminal)
                      ──(final)────► End[TaskResult]

ArchitectCodingNode   ──(self-loop)► ArchitectCodingNode (terminal)
                      ──(final)────► End[TaskResult]
```

### Key Files

| File | Path | Purpose |
|------|------|---------|
| Graph singleton | `src/graph/graph.py` | `orchestration_graph`, `run_task()`, `iter_task()` |
| Node classes | `src/graph/nodes.py` | 7 node classes, `select_start_node()` |
| State | `src/graph/state.py` | `TaskState` (~50 fields), `TaskDeps`, `TaskResult`, `GraphConfig` |
| Helpers | `src/graph/helpers.py` | ~2100 lines: `_execute_turn()`, escalation, REPL, context management |
| Persistence | `src/graph/persistence.py` | `SQLiteStatePersistence` (implements `BaseStatePersistence`, serializes 8 fields) |
| Approval gate | `src/graph/approval_gate.py` | `should_halt()`, `HaltState`, `ApprovalCallback` protocol |
| Resume token | `src/graph/resume_token.py` | Compact base64url crash recovery token |
| Session log | `src/graph/session_log.py` | Append-only `TurnRecord` journal per task |
| Error classifier | `src/graph/error_classifier.py` | `classify_error()` → `ErrorCategory` |
| Escalation helpers | `src/graph/escalation_helpers.py` | `detect_role_cycle()` |
| Compat bridge | `src/graph/_compat.py` | `EscalationContext` ↔ `TaskState` mapping |
| REPL tap | `src/graph/repl_tap.py` | Debug logging to `/mnt/raid0/llm/tmp/repl_tap.log` |

### Execution Model

1. `run_task()` → `orchestration_graph.run(start_node, state, deps)` — one-shot to completion
2. `iter_task()` → `orchestration_graph.iter(start_node, state, deps)` — async context manager, yields per node (**exists but NOT used in production streaming**)
3. Each node's `run()` calls `_execute_turn()` (the ~2100-line core loop), then returns `SameNode()`, `EscalationTargetNode()`, or `End[TaskResult]`
4. Production streaming (`/chat/stream`) is decoupled from graph iteration — SSE events are generated inside `_execute_turn()` via `primitives.llm_call()` streaming, not from `iter_task()`

### Strengths to Preserve

- Compile-time type-safe transitions (Union return types catch invalid edges at import time)
- Error taxonomy + 3-tier escalation ladder with think-harder ROI pre-escalation
- MemRL learned routing (Q-value based specialist selection)
- 43+ feature flags with live toggle via `/config` + env vars
- 5-layer context management (hard preview, stale clearing, session log, compaction, solution file)
- Budget enforcement with graceful degradation (per-turn caps, band-adaptive, max escalation limits)
- Workspace state blackboard (shared across delegation/escalation turns)

## What LangGraph Migration Provides

### 1. Subgraph Composition (PRIMARY MOTIVATION)
Each of our 7 nodes already acts as a mini-agent. LangGraph subgraphs formalize this: isolated state, clean I/O schema boundaries, nestable. Adding a new agent type becomes "compose a new subgraph" instead of "modify the monolithic 7-node graph + add Union variants to every related node."

### 2. Durable Checkpointing
State snapshot at every node transition with pluggable backends (SQLite, Postgres, Redis). Time-travel debugging: replay from any transition, fork execution. Our current `SQLiteStatePersistence` only captures 8 fields and `resume_token` captures ~10 — both are lossy.

### 3. interrupt() at Any Node
Pause execution anywhere for human review/modification/injection. Our `ApprovalCallback` only triggers at escalation boundaries (tier crossing) and high-cost roles. Can't interrupt mid-task for "this code looks risky."

### 4. State Immutability + Reducers
Clean merge semantics for concurrent updates. Full state history timeline. Enables future parallel node execution (e.g., running coder and researcher simultaneously on different subproblems).

### 5. Agent Protocol Compliance
LangGraph Platform implements Agent Protocol (Runs/Threads/Store). Maps to our existing concepts: Run ↔ task execution, Thread ↔ session persistence, Store ↔ episodic memory.

## Pre-Migration Steps (Implementable Now)

These improvements work with or without LangGraph migration. They reduce migration friction and provide immediate value.

### Step 1: Full State Snapshots at Node Transitions — COMPLETE (2026-03-16)

**Implementation**:
- Feature flag: `state_history_snapshots` (off by default, env `ORCHESTRATOR_STATE_HISTORY_SNAPSHOTS`)
- `persistence.py`: Renamed `_state_to_dict()` → `_state_to_dict_minimal()`, added `_state_to_dict_full()` that iterates all `dataclasses.fields(state)` (skips `task_manager`, `pending_approval`; `Role` enum → `str()`; unknown types → `repr()`). Dispatcher `_state_to_dict()` checks feature flag.
- `helpers.py`: Added `_log_state_snapshot(ctx, role)` — writes `{"type": "turn_snapshot", "turn": N, "role": "...", "state": {...}}` via `session_store.save_checkpoint()` or falls back to `log.debug()`. Wired into `_execute_turn()` immediately after `state.turns += 1`.
- **Tests**: 4 new tests in `test_graph_persistence_adapter.py` — full round-trip, Role enum, skip fields, flag dispatch (8 vs ~48 keys)
- **Rollback**: Flag off → existing 8-field minimal snapshots unchanged

### Step 2: interrupt() Generalization — COMPLETE (2026-03-16)

**Implementation**:
- Feature flag: `generalized_interrupts` (off by default, env `ORCHESTRATOR_GENERALIZED_INTERRUPTS`)
- Validation: requires `approval_gates` + `resume_tokens` (errors on misconfiguration)
- `approval_gate.py`: Added `HaltReason.INTERRUPT_CONDITION`, `InterruptCondition` protocol (`should_interrupt(state, artifacts) -> str | None`), `check_interrupt_conditions()` (first-trigger-wins, exception-safe), `request_approval_for_interrupt()` (mirrors escalation pattern with resume token)
- `state.py`: Added `interrupt_conditions: list[Any]` field to `TaskDeps`
- `helpers.py`: Wired into `_execute_turn()` after state snapshot, before REPL — checks conditions, requests approval on trigger, returns early with `"Interrupted: ..."` on reject
- **Tests**: 7 new tests in `test_approval_gate.py` — HaltReason member, empty/trigger/none/exception conditions, no-callback auto-approve, reject with correct halt state
- **Rollback**: Flag off → existing escalation-only approval gates unchanged

### Step 3: Agent Protocol Naming Alignment

**What**: Documentation-only decision. When we next change the API surface, align naming:
- `/chat` request → "Run"
- Session persistence → "Thread"
- Episodic/strategy stores → "Store"

No code changes. Record in this handoff for future API work.

## Migration Strategy

### Phase 1: Hybrid — LangGraph Subgraph via Bridge Node ✅ 2026-04-05

**Entry criteria**: Pre-migration Steps 1-2 complete and validated. ✓ (2026-03-16, 11 tests passing)

**Completed**: 2026-04-05. Full LangGraph StateGraph with all 7 nodes, conditional edges, feature-flagged bridge, 24 tests passing, zero regression on 190 existing graph tests.

**Implementation**:
- `langgraph>=0.2.0` + `langgraph-checkpoint-sqlite>=2.0.0` added to `pyproject.toml`
- `src/graph/langgraph/` module created with 4 files:
  - `state.py` — `OrchestratorState` TypedDict with 3 custom reducers (artifacts, workspace_state, think_harder_roi), `task_state_to_lg()` / `lg_to_task_state()` converters, config constants extracted to `LangGraphConfig`
  - `nodes.py` — 7 async node functions calling same `_execute_turn()` as pydantic_graph nodes, `RunnableConfig` typed, `_build_ctx()` reconstructs duck-typed `GraphRunContext`
  - `graph.py` — `build_orchestration_graph()` builds `StateGraph[OrchestratorState]`, conditional edges via `next_node` field, `run_task_lg()` drop-in replacement for `run_task()`, edge validation dicts (`VALID_TRANSITIONS`, `INVALID_TRANSITIONS`)
  - `bridge.py` — `run_task_auto()` dispatches to LG or PG backend based on `langgraph_bridge` feature flag
- Feature flag: `langgraph_bridge` (env: `ORCHESTRATOR_LANGGRAPH_BRIDGE`, default: `False`)
- 24 tests: state round-trip (5), edge validation (4), bridge dispatch (2), node routing (2), reducers (5), graph construction (3), feature flag (3)

**Goal**: Prove LangGraph works within our infrastructure (llama-server, FAISS, httpx async, feature flags) by running one subgraph alongside the existing pydantic_graph.

**Approach**:
1. Add `langgraph>=0.2.0` and `langgraph-checkpoint-sqlite` to `pyproject.toml`
2. Create `src/graph/langgraph/` directory with:
   - `bridge.py` — pydantic_graph `BaseNode` subclass that invokes a LangGraph compiled graph
   - `state.py` — LangGraph `TypedDict` state for the subgraph (minimal subset of TaskState)
   - `nodes.py` — LangGraph node functions for the subgraph
3. The bridge node:
   - Receives `GraphRunContext[TaskState, TaskDeps]` from pydantic_graph
   - Extracts relevant fields into LangGraph TypedDict state
   - Calls `compiled_graph.ainvoke(lg_state)` or `.astream(lg_state)`
   - Maps LangGraph result back to pydantic_graph state
   - Returns appropriate Union type (End, or next pydantic_graph node)
4. Wire bridge node into `orchestration_graph` as an additional node option

**Key concerns to validate**:
- **Streaming**: LangGraph's `.astream_events()` yields per-node events. Our SSE adapter is decoupled from graph iteration, so the bridge node can stream internally via `primitives.llm_call()` as current nodes do. No conflict.
- **TaskDeps passthrough**: Bridge node receives deps via `ctx.deps` (pydantic_graph injection). LangGraph nodes access them via the state dict or a closure. Pass deps as a non-serialized field in LangGraph config, NOT in the checkpointed state.
- **Feature flags**: Check `features()` inside LangGraph node functions, same as current nodes. Feature flags live outside the graph framework.
- **Async compatibility**: LangGraph is fully async. Our `_execute_turn()` uses `asyncio.to_thread()` for sync `primitives.llm_call()` and REPL execution. Same pattern works inside LangGraph node functions.

**Validation gate**: Bridge node handles a representative task end-to-end. Existing 9 graph test files pass unchanged. New test file covers bridge → LangGraph subgraph → bridge return.
**Rollback**: Remove bridge node from `orchestration_graph` nodes list. Delete `src/graph/langgraph/`. Remove langgraph from deps.

### Phase 2: State Migration — TaskState → LangGraph TypedDict

**Entry criteria**: Phase 1 bridge working in production (shadow mode).

**Goal**: Define the full LangGraph state equivalent to `TaskState` with reducer functions for every field.

**Full field-by-field reducer audit** (from `src/graph/state.py`):

| # | Field | Type | Reducer | Notes |
|---|-------|------|---------|-------|
| 1 | `task_id` | `str` | replace | Set once at init, never changes |
| 2 | `prompt` | `str` | replace | Set once at init |
| 3 | `context` | `str` | replace | Set once at init |
| 4 | `current_role` | `Role\|str` | replace | Updated on every role transition |
| 5 | `consecutive_failures` | `int` | replace | Reset on success, incremented on failure |
| 6 | `consecutive_nudges` | `int` | replace | Reset/incremented per turn |
| 7 | `escalation_count` | `int` | replace | Monotonically increasing but with reset logic |
| 8 | `role_history` | `list[str]` | append (`operator.add`) | Append-only via `record_role()` |
| 9 | `escalation_prompt` | `str` | replace | Set on escalation, cleared on success |
| 10 | `last_error` | `str` | replace | Overwritten each turn |
| 11 | `last_output` | `str` | replace | Overwritten each turn |
| 12 | `last_code` | `str` | replace | Overwritten each turn |
| 13 | `artifacts` | `dict[str,Any]` | **custom merge** | Per-turn tool outputs, nudges, escalation signals. Keys overwritten per turn but some accumulate. Reducer: deep-merge with latest-turn wins on conflict. |
| 14 | `task_ir` | `dict[str,Any]` | replace | Set once by routing, read-only thereafter |
| 15 | `task_type` | `str` | replace | Set once at init |
| 16 | `turns` | `int` | replace | Monotonically increasing counter |
| 17 | `max_turns` | `int` | replace | Set once at init |
| 18 | `gathered_files` | `list[str]` | append (`operator.add`) | Accumulated file paths across turns |
| 19 | `last_failure_id` | `str\|None` | replace | Overwritten on each failure |
| 20 | `anti_pattern_warning` | `str` | replace | Set/cleared per turn |
| 21 | `task_manager` | `TaskManager` | **exclude from state** | DI-injected tool, not graph state. Move to deps/config. |
| 22 | `delegation_events` | `list[dict]` | append (`operator.add`) | Append-only delegation log |
| 23 | `compaction_count` | `int` | replace | Monotonically increasing |
| 24 | `compaction_tokens_saved` | `int` | replace | Monotonically increasing |
| 25 | `context_file_paths` | `list[str]` | append (`operator.add`) | Accumulated context paths |
| 26 | `last_compaction_turn` | `int` | replace | Updated on compaction |
| 27 | `session_log_path` | `str` | replace | Set once at init |
| 28 | `session_log_records` | `list[Any]` | append (`operator.add`) | Append-only turn records |
| 29 | `session_summary_cache` | `str` | replace | Overwritten every 2 turns |
| 30 | `session_summary_turn` | `int` | replace | Updated with summary |
| 31 | `scratchpad_entries` | `list[Any]` | append (`operator.add`) | Append-only insights |
| 32 | `repl_executions` | `int` | replace | Monotonically increasing counter |
| 33 | `aggregate_tokens` | `int` | replace | Monotonically increasing counter |
| 34 | `resume_token` | `str` | replace | Overwritten at each snapshot |
| 35 | `pending_approval` | `Any` | replace | Transient — set during halt, cleared on resume |
| 36 | `think_harder_config` | `dict\|None` | replace | Set/cleared per escalation attempt |
| 37 | `think_harder_attempted` | `bool` | replace | Set per role attempt |
| 38 | `think_harder_succeeded` | `bool\|None` | replace | Set after attempt |
| 39 | `think_harder_roi_by_role` | `dict[str,dict]` | **custom merge** | Per-role EMA stats. Reducer: merge dicts, latest values per role win. |
| 40 | `think_harder_min_expected_roi` | `float` | replace | Config constant, never modified |
| 41 | `think_harder_min_samples` | `int` | replace | Config constant |
| 42 | `think_harder_cooldown_turns` | `int` | replace | Config constant |
| 43 | `think_harder_ema_alpha` | `float` | replace | Config constant |
| 44 | `think_harder_min_marginal_utility` | `float` | replace | Config constant |
| 45 | `tool_required` | `bool` | replace | Set once by routing |
| 46 | `tool_hint` | `str\|None` | replace | Set once by routing |
| 47 | `difficulty_band` | `str` | replace | Set once by routing |
| 48 | `grammar_enforced` | `bool` | replace | Set/cleared per turn |
| 49 | `cache_affinity_bonus` | `float` | replace | Set once by routing |
| 50 | `workspace_state` | `dict[str,Any]` | **custom merge** | Global blackboard. Reducer: version-aware merge — higher `version` wins on conflict; `broadcast_log` appends; lists (`proposals`, `commitments`, etc.) use union-merge. |

**Summary**: 42 fields use simple `replace` (default in LangGraph). 5 fields use `append` (operator.add). 3 fields need custom merge reducers (`artifacts`, `think_harder_roi_by_role`, `workspace_state`). 1 field (`task_manager`) should be moved out of state entirely. 5 fields (rows 40-44) are config constants that should move to `GraphConfig` or `TaskDeps`.

**Structural cleanup opportunity**: Move config constants (think_harder_min_*, rows 40-44) to `GraphConfig`. Move `task_manager` (row 21) to `TaskDeps`. This reduces state to ~44 true state fields.

**Validation gate**: Automated test that runs the same task through pydantic_graph TaskState and LangGraph TypedDict state, comparing field values at each node transition. All ~50 fields must round-trip correctly.
**Rollback**: LangGraph state definition is additive — pydantic_graph TaskState remains the source of truth until Phase 3.

**Phase 2 — ✅ COMPLETE 2026-04-05**:
- **Critical bug fixed**: `_state_update()` was returning full lists for `operator.add` fields, causing exponential growth. Now returns deltas via `snapshot_append_lengths()` / `state_update_delta()`.
- **`_SKIP_TO_LG`** expanded: `segment_cache`, `compaction_quality_monitor` added (non-serializable `Any` fields from CF Phase 1+/3b).
- **`_result`** declared in `OrchestratorState` (was injected without declaration).
- **`APPEND_FIELDS`** constant with parity check against `OrchestratorState` `operator.add` annotations.
- **44 tests total** (24 Phase 1 + 20 Phase 2): reducer delta correctness, full 50-field round-trip, 5 dual-run validation scenarios (success, self-loop, escalation, max-turns, budget), `_SKIP_TO_LG` coverage.

### Phase 3: Node-by-Node Migration — INFRASTRUCTURE COMPLETE (2026-04-09)

**Entry criteria**: Phase 2 state definition validated; dual-state comparison tests passing. ✓

**Migration order** (simplest → most complex, based on transition count and escalation complexity):

1. **IngestNode** — Fewest transitions (self-loop + ArchitectNode + End). No mid-chain complexity.
2. **ArchitectNode** — Terminal node (self-loop + End only). No outgoing escalation.
3. **ArchitectCodingNode** — Terminal node (self-loop + End only).
4. **WorkerNode** — Self-loop + CoderEscalationNode + End. Straightforward escalation.
5. **FrontdoorNode** — Same pattern as Worker but is the primary entry point. Migrate after Worker validates the pattern.
6. **CoderNode** — Adds model-initiated escalation (`_escalation_requested` artifact). More complex transition logic.
7. **CoderEscalationNode** — Middle of escalation chain (Worker→CoderEscalation→ArchitectCoding). Must handle both incoming and outgoing escalation.

**Per-node migration pattern**:
1. Create LangGraph node function in `src/graph/langgraph/nodes.py` that calls the same `_execute_turn()` helper
2. Define conditional edges matching the Union return type
3. Feature flag `langgraph_<node_name>` controls which backend runs
4. **Dual-run validation**: Run both backends for same input, compare state after execution
5. Once validated, flip flag to LangGraph backend as default

**Critical**: `_execute_turn()` in `helpers.py` (2100 lines) is the shared core logic. It does NOT need to change — LangGraph node functions call it the same way pydantic_graph nodes do. The migration is at the graph framework level, not the node logic level.

**Phase 3 Infrastructure — ✅ COMPLETE 2026-04-09**:

Implementation of the per-node dispatch infrastructure. All 7 nodes can now be individually migrated to LangGraph via feature flags.

- **7 per-node feature flags** added to `src/features.py`: `langgraph_ingest`, `langgraph_architect`, `langgraph_architect_coding`, `langgraph_worker`, `langgraph_frontdoor`, `langgraph_coder`, `langgraph_coder_escalation`. Env vars: `ORCHESTRATOR_LANGGRAPH_<NODE_NAME>`. All default to `False`.
- **`_run_via_langgraph()` helper** added to `src/graph/nodes.py` — converts pydantic_graph `ctx` to LangGraph state dict, calls the LG node function, maps `next_node` back to pydantic_graph return type (End, self-class, or escalation target).
- **Per-node dispatch** wired into each node's `run()` method — `if _get_features().langgraph_<node>: return await _run_via_langgraph(ctx, "<node>")`. Pydantic_graph remains the outer loop; individual node logic is swappable.
- **`_NEXT_NODE_TO_PG` mapping** — `next_node` strings → pydantic_graph node classes, populated after class definitions.
- **48 Phase 3 tests** in `tests/unit/test_langgraph_phase3.py`:
  - 14 feature flag dispatch tests (flag on/off per node)
  - 26 dual-run parity tests (success, self-loop, escalation, max-turns per node)
  - 5 `_run_via_langgraph` helper tests (End return, self-loop, escalation, unknown node, state round-trip)
  - 1 cross-backend escalation test (Worker LG → CoderEscalation PG)
  - 2 mapping completeness tests
- **Zero regression**: 44 Phase 1+2 tests pass, 146/149 existing graph tests pass (3 pre-existing failures unrelated to migration)

**Next step**: Flip per-node flags to `True` one at a time (IngestNode first), validate with production shadow traffic, then proceed down the migration order.

**Validation gate**: All 9 graph test files pass with LangGraph backend. Dual-run comparison shows identical state evolution for a representative task set.
**Rollback**: Per-node feature flags revert to pydantic_graph backend. No node logic was changed.

### Phase 4: Remove pydantic_graph

**Entry criteria**: All 7 nodes running on LangGraph for ≥1 week in production. No state divergence detected in dual-run comparisons.

**Steps**:
1. Remove pydantic_graph node classes (keep as reference in git history)
2. Remove bridge infrastructure
3. Remove dual-run comparison infrastructure
4. Remove per-node feature flags (LangGraph is now the only backend)
5. Drop `pydantic-graph` from `pyproject.toml`
6. Activate native LangGraph features:
   - Checkpointing with SQLite backend (replaces our `SQLiteStatePersistence`)
   - `interrupt()` at any node (replaces our `approval_gate.py` extensions from Step 2)
   - Subgraph composition for future agent types
7. Update `generate_mermaid()` to use LangGraph's built-in visualization

**Validation gate**: Full test suite green. Latency regression test shows <5ms overhead per node transition. Production stability for 1 week.
**Rollback**: Git revert to Phase 3 state (all nodes on LangGraph but pydantic_graph still present).

## Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|-----------|
| **~50 state field migration** — reducers must match current mutation semantics | High | Field-by-field audit above. Automated dual-state comparison tests. Phased rollout per node. |
| **Type safety regression** — pydantic_graph catches invalid transitions at import time; LangGraph validates at runtime | Medium | Add exhaustive edge validation tests that run in CI. Test every valid transition AND every invalid transition (expect error). Catches what Union types caught at import. |
| **Feature flag integration** — LangGraph has no concept of feature flags | Low | Feature flags live OUTSIDE the graph framework. Node functions check `features()` internally, same as today. Conditional edges can wrap feature flag checks. No architectural conflict. |
| **Checkpoint overhead** — per-node-transition state serialization | Low | Checkpoints happen per node transition (max 7 nodes per task), not per token. Full state serialization is <1ms for ~50 fields. Inference takes seconds. Overhead is negligible. Benchmark in Phase 1 to confirm. |
| **Test coverage** — 9 graph test files + integration tests depend on pydantic_graph execution model | High | Dual-run strategy during Phase 3: same test input, both backends, compare. Tests are rewritten only in Phase 4. Graph test files: `test_graph_helpers.py`, `test_graph_integration.py`, `test_graph_mermaid.py`, `test_graph_nodes.py`, `test_graph_persistence_adapter.py`, `test_graph_router_cold_start.py`, `test_graph_router_integration.py`, `test_graph_router_predictor.py`, `test_orchestration_graph.py`. |
| **helpers.py coupling** — 2100 lines of shared logic imported by all nodes | Low | `_execute_turn()` and all helpers are framework-agnostic — they operate on `TaskState` and `TaskDeps` directly, not on pydantic_graph constructs. LangGraph nodes call the same helpers. No change needed. |
| **Streaming compatibility** — SSE streaming is decoupled from graph iteration | Low | Current SSE streaming happens inside `_execute_turn()` via `primitives.llm_call()`. This doesn't change. LangGraph's `.astream_events()` is an additional capability we gain, not a replacement for our current streaming path. |
| **pydantic_graph + langgraph coexistence** — dependency conflict during hybrid phase | Low | Both packages depend on pydantic but use different graph runtimes. No namespace collision. Verified: pydantic-graph v1.56.0 is from pydantic-ai (pydantic_graph module), LangGraph is from LangChain (langgraph module). |
| **MemRL / episodic memory / SkillBank invalidation** — stored memories become stale after migration | None | All stored data is framework-agnostic (role strings, domain JSON, BGE embeddings). No pydantic_graph internals in any SQLite table or FAISS index. Memory population and Q-scoring happen outside the graph layer. Only requirement: LangGraph nodes call `progress_logger.log_escalation()` at same lifecycle points as current nodes. |

## Resolved Open Questions

| Question | Answer | Validation |
|----------|--------|------------|
| **SQLite checkpointer?** | Yes — `langgraph-checkpoint-sqlite` uses aiosqlite. Can use a separate DB file alongside our existing session store (different schema). Sharing the same file is possible but unnecessary — separate files reduce coupling. | Install in Phase 1, test with our SQLite path. |
| **Streaming from llama-server?** | Not a concern. LangGraph node functions call `primitives.llm_call()` which handles streaming internally via httpx SSE. LangGraph doesn't touch our inference layer. | Verified by architecture: LangGraph wraps node functions, doesn't replace them. |
| **Compile-time transition safety?** | Lost. LangGraph validates edges at runtime. **Accepted tradeoff**: add CI-time edge validation tests (test every valid AND invalid transition). The compile-time safety was a nice-to-have; runtime validation with good tests is sufficient. | Add edge validation test suite in Phase 1. |
| **Minimum LangGraph version?** | ≥0.2.0 for: `interrupt()`, `Command(resume=...)`, subgraph state schema, `.astream_events()`. Check latest stable at implementation time and pin. | Pin in pyproject.toml during Phase 1. |
| **interrupt() with async httpx?** | Yes. `interrupt()` raises `GraphInterrupt` exception caught by the LangGraph runtime. It doesn't matter what the node was doing internally. For clean shutdown: `httpx.AsyncClient` requests are already cancelable via the `cancel_check` ContextVar. On interrupt, the current inference call completes or times out, then the interrupt takes effect. | Test with mock async node in Phase 1. |
| **How do TaskDeps pass through?** | Via LangGraph's `config` parameter (not checkpointed state). Pass `{"configurable": {"deps": task_deps}}` to `compiled_graph.ainvoke()`. Node functions access via `config["configurable"]["deps"]`. This matches LangGraph's recommended pattern for non-serializable dependencies. | Implement in Phase 1 bridge node. |
| **MemRL / episodic memory / SkillBank — reset or reseed needed?** | **No.** All stored data is framework-agnostic. Episodic store `context` JSON contains only business-domain fields (`task_type`, `objective`, `priority`). `action` field stores role strings (`"frontdoor"`, `"coder_escalation"`). FAISS indices store BGE embeddings of domain text, not graph internals. Memory population happens outside the graph layer (pipeline stages call `log_task_completed()` and Q-scoring). The MemRL interface is Protocol-based (`MemRLSuggestor`, `HypothesisGraphProtocol`) with no pydantic_graph coupling. **Only migration work**: LangGraph node functions must call `progress_logger.log_escalation()` and `_update_hypothesis_graph()` at the same lifecycle points — these are 2 call sites in `helpers.py` (~lines 600-622) operating on generic `TaskState`/`TaskDeps`. | Verified by schema audit: `sessions/episodic.db` `memories` table stores only role strings + domain JSON; `sessions/skills.db` stores principles/titles; FAISS stores float32 vectors + UUID id_maps. |

## Dependencies

| Package | Version | Purpose | License |
|---------|---------|---------|---------|
| `langgraph` | ≥0.2.0 | Core graph runtime | Apache-2.0 |
| `langgraph-checkpoint-sqlite` | latest | SQLite persistence backend (aiosqlite) | Apache-2.0 |

**Coexistence**: `pydantic-graph` (from pydantic-ai) and `langgraph` (from LangChain) use different module namespaces (`pydantic_graph` vs `langgraph`). Both depend on pydantic but don't conflict. Safe to have both during hybrid phase.

**No conflicts with**: httpx, FAISS, uvicorn, fastapi, or any current orchestrator dependency.

## Success Criteria

- [ ] All 195 existing test files pass (zero regression)
- [ ] New subgraph capability works end-to-end via bridge pattern
- [ ] Checkpoint/replay works for any failed task (time-travel debugging)
- [ ] interrupt() works at any node, not just escalation boundaries
- [ ] No measurable latency regression (< 5ms overhead per node transition)
- [ ] Feature flags control all new behavior (full rollback to pydantic_graph possible at any phase)
- [ ] Dual-state comparison shows identical evolution for representative task set

## Non-Goals

- NOT migrating MemRL, feature flags, or context management INTO LangGraph — these remain our domain layer sitting above the graph framework
- NOT adopting LangGraph Platform (cloud hosting) — we run local inference
- NOT changing the API surface — `/chat` and `/v1/chat/completions` stay the same
- NOT rewriting node logic — `_execute_turn()` and helpers are framework-agnostic, only the graph routing/transition layer changes
- NOT pursuing LangChain (parent ecosystem) — LangGraph is standalone
- NOT wiring SSE streaming through the graph in this migration — streaming path stays independent (see Streaming Architecture below)

## Appendix A: Test Strategy — Dual-Backend Comparison

### Current Test Landscape (Graph-Specific)

| File | Tests | pydantic_graph Coupling | Migration Work |
|------|-------|------------------------|----------------|
| `test_graph_helpers.py` | 16 | **Zero** — uses `SimpleNamespace` as `ctx`, duck-types `GraphRunContext` | None — passes as-is |
| `test_graph_nodes.py` (helper tests) | ~117 | **Zero** — tests pure functions (`_classify_error`, `_extract_final_from_raw`, etc.) | None — passes as-is |
| `test_graph_nodes.py` (async node tests) | 9 | **High** — calls `orchestration_graph.run(FrontdoorNode(), state, deps)` directly | Parametrize with backend fixture |
| `test_orchestration_graph.py` | 7 | **Medium** — calls `run_task()` (wraps `orchestration_graph.run()`) | Parametrize `run_task` import |
| `test_graph_persistence_adapter.py` | 10 | **High** — imports `pydantic_graph.End`, `BaseStatePersistence` | Write parallel LangGraph persistence tests |
| `test_graph_mermaid.py` | ~3 | **High** — tests `orchestration_graph.mermaid_code()` | Replace with LangGraph visualization |
| `test_graph_integration.py` | 17 | **Zero** — tests MemRL `GraphEnhancedStore/Retriever`, not graph framework | None — passes as-is |
| `test_graph_router_*.py` (3 files) | ~15 | **Zero** — tests MemRL routing, not graph execution | None — passes as-is |

**Summary**: ~150 of 176 graph-related tests have zero pydantic_graph coupling. Only ~26 tests need migration work.

### Dual-Backend Test Architecture

**Step 1: Extract node logic into standalone functions** (prerequisite for Phase 3)

```python
# src/graph/node_logic.py (new file, extracted from nodes.py)
async def frontdoor_logic(state: TaskState, deps: TaskDeps) -> NodeDecision:
    """Core frontdoor logic, framework-agnostic."""
    output, error, is_final, artifacts = await _execute_turn(...)
    if is_final: return NodeDecision("end", result=_make_end_result(...))
    if _should_escalate(...): return NodeDecision("escalate", target="coder_escalation")
    return NodeDecision("retry")
```

Both pydantic_graph `BaseNode.run()` and LangGraph node functions delegate to these. Tests can call the logic functions directly without any graph framework.

**Step 2: Parametrize integration tests**

```python
@pytest.fixture(params=["pydantic_graph", "langgraph"])
def run_graph(request):
    if request.param == "pydantic_graph":
        from src.graph import run_task
        return run_task
    else:
        from src.graph.langgraph import run_task as lg_run_task
        return lg_run_task
```

Both `run_task` implementations accept `(state: TaskState, deps: TaskDeps, start_role) -> TaskResult`. The `MockREPL`, `MockPrimitives`, and `MockREPLResult` infrastructure is already backend-agnostic.

**Step 3: State evolution comparison**

After each `run_task()`, compare these observable fields across backends:
- `result.success` (bool), `result.turns` (int), `result.answer` (str)
- `state.escalation_count` (int), `state.role_history` (list[str])
- `state.consecutive_failures` (int at termination)

**Caveat**: `MockREPL` consumes results sequentially (index-based). Both backends must call `_execute_turn()` in the same order for mocks to produce the same results. LangGraph's execution is sequential (no parallel branches in our graph), so this holds.

**Step 4: Edge validation tests (replacing compile-time safety)**

```python
# test_edge_validation.py
VALID_TRANSITIONS = {
    "FrontdoorNode": {"FrontdoorNode", "CoderEscalationNode", "End"},
    "WorkerNode": {"WorkerNode", "CoderEscalationNode", "End"},
    "CoderNode": {"CoderNode", "ArchitectNode", "End"},
    ...
}
INVALID_TRANSITIONS = {
    "FrontdoorNode": {"ArchitectNode", "CoderNode", "IngestNode"},
    ...
}

def test_valid_transitions():
    for source, targets in VALID_TRANSITIONS.items():
        for target in targets:
            assert graph.has_edge(source, target)

def test_invalid_transitions_rejected():
    for source, invalids in INVALID_TRANSITIONS.items():
        for target in invalids:
            assert not graph.has_edge(source, target)
```

Run in CI to catch edge definition errors that pydantic_graph's Union types currently catch at import time.

## Appendix B: Checkpoint Performance Benchmarking Plan

### What to Measure

LangGraph checkpoints state at every node transition. For our graph: max 7 node transitions per task (typical: 1-3). The question is whether checkpoint I/O adds measurable latency.

### Benchmark Methodology

**Micro-benchmark** (Phase 1, before production rollout):

```python
import time, json, dataclasses

state = TaskState(prompt="x" * 2000, workspace_state={...full...}, ...)

# Measure serialization
t0 = time.perf_counter_ns()
blob = json.dumps(dataclasses.asdict(state), default=str)
t_serialize = (time.perf_counter_ns() - t0) / 1e6  # ms

# Measure SQLite write
t0 = time.perf_counter_ns()
cursor.execute("INSERT INTO checkpoints VALUES (?, ?, ?)", (thread_id, ts, blob))
conn.commit()
t_write = (time.perf_counter_ns() - t0) / 1e6  # ms

# Measure deserialization
t0 = time.perf_counter_ns()
loaded = json.loads(blob)
t_deserialize = (time.perf_counter_ns() - t0) / 1e6  # ms
```

**Expected results** (based on ~50 fields, ~5KB JSON):
- Serialization: <0.5ms
- SQLite write (WAL mode, local NVMe): <1ms
- Deserialization: <0.3ms
- **Total per checkpoint: <2ms**

**Context**: A single `primitives.llm_call()` takes 2-30 seconds (depending on model tier and output length). REPL execution takes 0.1-30 seconds. Checkpoint overhead of <2ms per node transition is <0.01% of total task time.

**Macro-benchmark** (Phase 3, during dual-run validation):

Run 100 representative tasks through both backends. Measure wall-clock time per task. Acceptable regression: <5ms per node transition (35ms worst-case for a 7-node task).

### What Could Go Wrong

- **Large state fields**: `workspace_state` and `artifacts` can grow unbounded. Mitigation: cap serialized size (truncate large string fields, skip ephemeral artifacts). LangGraph's `langgraph-checkpoint-sqlite` uses msgpack by default (faster than JSON).
- **Checkpoint read amplification**: LangGraph reads the latest checkpoint to construct state before each node. For SQLite WAL on NVMe, this is <1ms. Not a concern unless we switch to network-attached storage.
- **FAISS/TaskManager in state**: `task_manager` (row 21 in audit) should NOT be serialized — move to deps. FAISS objects would break serialization. Verified: no FAISS objects live in `TaskState`.

## Appendix C: SSE Streaming Architecture — Migration Compatibility

### Current Architecture: Two Independent Code Paths

```
Non-streaming (/chat)                    Streaming (/chat/stream)
─────────────────────                    ────────────────────────
_handle_chat()                           generate_stream() / generate()
  → _execute_repl()                        → _stream_repl() [manual for-loop]
    → run_task()                             → primitives.llm_call() [blocking]
      → orchestration_graph.run()            → repl.execute(code)
        → FrontdoorNode.run()                → yield SSE events
          → _execute_turn()                  → escalation logic (inline)
            → primitives.llm_call()          → yield done_event()
            → repl.execute(code)
      → TaskResult
  → ChatResponse
```

**Critical finding**: The SSE streaming path (`stream_adapter.py:_stream_repl()` and legacy `chat.py:generate()`) is **completely independent** of pydantic_graph. It implements its own manual REPL turn loop, calls `primitives.llm_call()` and `repl.execute()` directly, and emits SSE events. It does NOT call `run_task()`, `iter_task()`, or any graph machinery.

**`iter_task()` is defined but never called from any API route.** It's dead code reserved for future use.

### What This Means for Migration

**Zero streaming changes required during Phases 1-4.** The streaming path doesn't touch pydantic_graph, so swapping the graph framework has no effect on it.

### Feature Parity Gap (Pre-Existing, Not Migration-Related)

The streaming REPL loop in `_stream_repl()` is a manually maintained duplicate of the graph node logic. It **lacks**:
- Session log (`session_log.py` TurnRecord tracking)
- Context compaction (`_maybe_compact_context`)
- Scratchpad entries
- Budget pressure warnings
- Workspace state blackboard
- Difficulty-band token caps
- Think-harder ROI regulation
- Full escalation helper suite

This is a pre-existing gap, not introduced by migration. However, migration creates an opportunity:

### Post-Migration Opportunity: Unified Streaming via Graph Iteration

After Phase 4, we could wire the streaming endpoint to use LangGraph's `compiled_graph.astream_events()`:

```python
async def generate_stream_via_graph(request, state):
    async for event in compiled_graph.astream_events(lg_state, config=...):
        if event["event"] == "on_chain_start":
            yield turn_start_event(...)
        elif event["event"] == "on_chain_end":
            yield turn_end_event(...)
        # ... map LangGraph events to our SSE event schema
    yield done_event()
```

This would:
- Eliminate the duplicated REPL loop
- Give streaming the full feature set of graph nodes (session log, compaction, etc.)
- Make `iter_task()` the single code path for both streaming and non-streaming

**This is a separate follow-up handoff**, not part of the core migration. The migration succeeds without it.

### Token-Level Streaming Note

Current "streaming" is post-hoc: `primitives.llm_call()` returns the full response, then it's split by newlines and yielded as `token_event`s. True sub-token streaming would require wiring `primitives.llm_call_stream()` (if it existed) into the SSE generator. This is orthogonal to the graph framework migration.

## Research Context

| Intake ID | Title | Relevance |
|-----------|-------|-----------|
| intake-146 | LangGraph | Core migration target |
| intake-145 | Agent Protocol | API standard that LangGraph implements |
| intake-144 | Deep Agents | Batteries-included pattern built on LangGraph |
| intake-143 | LangChain | Parent ecosystem (not needed for LangGraph alone) |
