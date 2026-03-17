# Deep Dive: LangGraph Ecosystem vs EPYC Orchestrator

**Source**: intake-144 (Deep Agents), intake-145 (Agent Protocol), intake-146 (LangGraph)
**Date**: 2026-03-15
**Scope**: Architectural comparison of LangGraph ecosystem against our pydantic_graph-based orchestrator. Identify gaps worth adopting and strengths to preserve.

## Architecture Comparison

| Dimension | EPYC Orchestrator | LangGraph | Assessment |
|-----------|-------------------|-----------|------------|
| Graph structure | pydantic_graph, 7 typed nodes, Union return types for compile-time safe transitions | Fluent builder API, arbitrary topology, cycles, subgraphs, conditional edges | LangGraph: more flexible topology, subgraph nesting |
| State management | Mutable `TaskState` (180+ fields), domain-specific, single shared state | User-defined `TypedDict` + reducer functions, immutable, composable | Tie: ours is deeper domain-wise, theirs is more general and debuggable |
| Durable execution | `resume_tokens` <500B (portable, URL-passable), ~10 fields captured | Checkpoint at every node transition, pluggable backends (Postgres, Redis, memory) | LangGraph: much finer granularity, time-travel replay |
| Human-in-the-loop | `ApprovalCallback` at escalation boundaries + destructive ops (`approval_gate.py`) | `interrupt()` at any node, state editable during pause, `Command(resume=...)` | LangGraph: more flexible interruption points |
| Memory | Episodic + Strategy + Skill stores (FAISS+SQLite), MemRL learned retrieval | Working memory (checkpoint) + long-term (Store API with namespaces), user-managed | EPYC: richer built-in memory with learned retrieval |
| Error recovery | 3-tier escalation ladder, error taxonomy, think-harder ROI, budget caps, graceful degradation | Custom routing via conditional edges, no built-in error patterns | EPYC: significantly richer error handling |
| Context management | 5 layers: hard preview, stale clearing, session log, compaction/virtual memory, solution file persistence + output spill | Basic message trimming, user responsibility for summarization | EPYC: 5 production-hardened layers vs basic |
| Production controls | 43+ feature flags, env vars, live toggle via `/config`, dependency validation | None — all features always on | EPYC: mature experimentation infrastructure |
| Routing intelligence | MemRL (Q-value learned routing), MLP+GAT classifiers, specialist routing, factual risk scoring | Manual lambda routing, no learned component | EPYC: fundamentally more sophisticated |

## Gap Analysis: What LangGraph Does Better

### Gap 1: Checkpoint Granularity (Time-Travel Debugging)

**LangGraph**: Checkpoints state at every node transition. Pluggable backends (Postgres, Redis, in-memory). Can replay from any point, fork execution, inspect full state history.

**EPYC**: `resume_tokens` captures ~10 fields in <500B — portable but lossy. `session_store.py` persists state every 5 turns (for crash recovery). No ability to replay from an arbitrary node transition.

**Impact**: We can't time-travel debug a failed escalation path. If a worker produces bad output at turn 3 that cascades to a coder failure at turn 7, we can't replay from turn 3 with a different approach.

**Recommendation**: Log `TaskState` snapshots at each node transition (not just every 5 turns). Enables post-hoc debugging without the full LangGraph checkpoint machinery. ~50 lines in `persistence.py`. Does NOT require LangGraph migration.

### Gap 2: Subgraph Composition

**LangGraph**: Subgraphs are first-class — nest graphs with isolated state, inherited checkpointers, and clean input/output schema boundaries. A "research agent" subgraph can have its own internal nodes while appearing as a single node to the parent graph.

**EPYC**: Flat graph with 7 nodes. Escalation is a linear ladder (Worker→Coder→Architect), not nested composition. The `_delegate_to_worker()` pattern spawns isolated subprocess agents but without graph-level composition.

**Impact**: Adding a new agent type (e.g., a research agent, a code review agent) requires modifying the monolithic graph rather than composing a new subgraph. Our escalation model works well for the current 3-tier system but doesn't scale to heterogeneous agent topologies.

**Recommendation**: This is the strongest argument for LangGraph migration. Our orchestrator already does heterogeneous agent composition — 7 node types across 4 model tiers with learned routing between them. LangGraph would formalize this with proper subgraph boundaries, making it easier to add new agent types and compose multi-step workflows. **Separate handoff created**: `handoffs/active/langgraph-migration.md`.

### Gap 3: interrupt() Flexibility

**LangGraph**: `interrupt()` can pause execution at ANY node. The interrupted state is checkpointed. Humans can inspect state, modify it, and resume with `Command(resume=value)`. Works naturally with the checkpoint system.

**EPYC**: `ApprovalCallback` protocol in `approval_gate.py` only triggers at escalation boundaries and destructive operations. Can't pause mid-task for clarification on non-escalation paths (e.g., "this code looks risky, should I proceed?").

**Impact**: If a worker is about to execute code that deletes files, we can't interrupt unless it hits an explicit approval gate. The model must self-detect the risk and escalate.

**Recommendation**: Extend `approval_gate.py` to support arbitrary interrupt points via an `interrupt_before` parameter on node execution. The existing `ApprovalCallback` protocol is clean — adding interrupt support means allowing any node to register interrupt conditions. ~100 lines. Compatible with current architecture; would become native if we migrate to LangGraph.

### Gap 4: State Immutability + Reducers

**LangGraph**: State is immutable `TypedDict` with reducer functions that define how concurrent updates merge. Enables safe parallel node execution and provides a complete state history.

**EPYC**: Mutable `TaskState` with 180+ fields modified in-place throughout execution. No state history, no merge semantics for concurrent updates.

**Impact**: Harder to debug state mutations — if `last_output` is wrong at turn 5, we can't trace which node set it. No possibility of parallel node execution (e.g., running coder and researcher simultaneously).

**Recommendation**: Not worth retrofitting onto pydantic_graph. Would come naturally with LangGraph migration.

### Gap 5: Agent Protocol API Surface

**LangGraph Platform** implements the Agent Protocol standard (intake-145): Runs (stateless execution), Threads (persistent multi-turn), Store (namespace-scoped long-term memory).

**EPYC**: Ad-hoc API (`/chat`, `/v1/chat/completions`). No standard interop surface.

**Mapping**:
| Agent Protocol | EPYC Equivalent |
|----------------|-----------------|
| Runs | Task execution (single `/chat` request) |
| Threads | Session persistence (`session_store.py`) |
| Store | Episodic memory (`episodic_store.py`) |

**Recommendation**: When we next touch the API surface, align naming with Agent Protocol's Runs/Threads/Store. No code change needed now — just architectural alignment for future API work. If we migrate to LangGraph, we'd get Agent Protocol compliance for free.

## What NOT to Adopt (Where We're Already Better)

| Capability | EPYC Advantage | LangGraph Status |
|-----------|----------------|------------------|
| Error taxonomy + escalation | 3-tier ladder with error classification, think-harder ROI, budget caps | Nothing comparable — user builds from scratch |
| MemRL learned routing | Q-value trained routing with specialist selection, factual risk, difficulty signal | Manual lambda routing only |
| 5-layer context management | Hard preview + stale clearing + session log + compaction + solution file + output spill | Basic message trimming, user responsibility |
| Feature flags | 43+ flags, live toggle, env vars, dependency validation | All features always on, no experimentation |
| Think-harder ROI regulation | Expected ROI calculation, token budget enforcement, graceful degradation | No concept of compute budgeting |
| Budget enforcement | Per-turn caps, band-adaptive budgets, max escalation limits | No built-in budget controls |
| Skill + strategy memory | FAISS+SQLite stores with Q-value weighted retrieval | User-managed Store API with no retrieval intelligence |

## Deep Agents (intake-144) — Architectural Parallel

LangChain's Deep Agents (`create_deep_agent`) is a batteries-included agent with:
- Planning tools (`write_todos`, structured task tracking)
- Sub-agent delegation (`create_deep_agent` returns compiled LangGraph)
- Context summarization for long conversations
- File-based output storage

**Comparison**: Our architecture is more sophisticated (multi-tier routing, MemRL, SkillBank, 5-layer context management) but less turnkey. Deep Agents shows the "opinionated defaults" pattern — pre-tuned prompts and automatic context handling.

**Takeaway**: No adoption needed. Deep Agents validates our architectural choices (planning tools, sub-agent delegation, context management) but at a simpler level than what we've already built.

## Actionable Recommendations

| # | Recommendation | Effort | Dependencies | Status |
|---|---------------|--------|-------------|--------|
| 1 | Agent Protocol naming alignment | None (documentation) | Next API surface change | Documented in hermes-agent-integration.md |
| 2 | State history snapshots at node transitions | ~50 lines | None | Handoff: langgraph-migration.md |
| 3 | interrupt() generalization in approval_gate.py | ~100 lines | None | Handoff: langgraph-migration.md |
| 4 | LangGraph migration (subgraph composition, checkpoints, state immutability) | Large | Careful migration plan | Handoff: langgraph-migration.md |

Items 2 and 3 are implementable independently of LangGraph migration but would become native features post-migration. Item 4 subsumes items 2-4 if pursued.

## Migration Assessment

**Should we migrate to LangGraph?**

Arguments for:
- Our orchestrator IS heterogeneous agent composition — LangGraph formalizes what we're already doing
- Subgraph composition would make adding new agent types (research, code review, etc.) much cleaner
- Checkpoint + time-travel debugging would significantly improve development velocity
- Agent Protocol compliance for free
- Active open-source community (LangGraph is Apache-2.0)

Arguments against:
- Our domain-specific features (MemRL, escalation ladder, feature flags, think-harder, 5-layer context) are NOT in LangGraph — we'd need to port them
- pydantic_graph's compile-time type safety (Union return types) is stronger than LangGraph's runtime edge validation
- Migration risk: 7 nodes, 180+ state fields, 120+ tests to port
- LangGraph's state model (immutable TypedDict + reducers) doesn't naturally fit our mutable TaskState pattern

**Verdict**: Worth investigating as a dedicated handoff. The migration would be incremental — start with a new subgraph for a new capability (e.g., research agent) running alongside the existing pydantic_graph, then gradually migrate nodes.
