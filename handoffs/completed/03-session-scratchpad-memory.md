# Session Scratchpad Memory

**Status**: COMPLETED
**Created**: 2026-03-03
**Completed**: 2026-03-03
**Priority**: P1 — enhances existing session log, unblocks quality improvements
**Effort**: Medium
**Source**: [Custom LLM Memory Layer Architecture (Towards Data Science)](https://towardsdatascience.com/how-to-build-your-own-custom-llm-memory-layer-from-scratch/) | [ICLR 2026 MemAgents Workshop](https://openreview.net/pdf?id=U51WxL382H)

## Research Review

### Custom LLM Memory Layer Architecture
**Author:** Avishek Biswas
**Related:** ICLR 2026 MemAgents Workshop paper

Architecture for per-user persistent vector-backed memory combining three memory types: episodic memory (long-term conversation index for retrieval), working memory (recent turns), and scratchpad (model reasons over dialogue, records salient facts). Incremental summarization of conversations. Mem0-inspired architecture.

**Orchestrator Relevance: HIGH.** Directly maps to our session log and episodic memory systems:
- **Three-memory architecture** maps cleanly to our existing infrastructure:
  - Episodic → our `session_{task_id}.md` (turn history)
  - Working → our state dict (current REPL context)
  - Scratchpad → **now implemented** — model-generated salient fact extraction
- **Scratchpad concept**: After each summary refresh, model reasons about what's important and records it.
- **Incremental summarization**: Our session log already does periodic summaries via `worker_fast`, now extended with structured insight extraction.

## Design Decisions

- **Combined extraction**: Extended existing `summarize_session_with_worker` prompt to also return `INSIGHT|category|text` lines. Zero additional inference calls.
- **Separate state field**: `scratchpad_entries: list[Any]` on `TaskState` (not embedded in TurnRecord) — different lifecycle, pruned by category.
- **Category-based pruning**: Newer entry in same category supersedes older. Max 8 entries.
- **Prompt injection**: Prepend `[Key Insights]` block before existing `[Session History]` in `_session_log_prompt_block`.
- **Escalation passthrough**: `scratchpad_entries` on `EscalationContext` + injected into escalation prompt as `## Previous Insights`.

## Implementation Steps

### 1. Define scratchpad data model — DONE
- **Where**: `/mnt/raid0/llm/epyc-orchestrator/src/graph/session_log.py`
- `ScratchpadEntry` dataclass with `turn`, `category`, `insight`, `confidence`
- `SCRATCHPAD_CATEGORIES` frozenset: `bug_location`, `approach_eliminated`, `constraint_discovered`, `user_intent`, `dependency_found`
- `build_scratchpad_extraction_prompt()` — combined SECTION 1 (summary) + SECTION 2 (INSIGHT lines)
- `parse_scratchpad_from_response()` — splits worker output into summary + parsed entries, validates categories, caps insight at 200 chars
- `prune_scratchpad()` — category supersession + max 8 entries cap
- Modified `summarize_session_with_worker()` — `extract_scratchpad` and `current_turn` params, 400 tokens when extracting

### 2. Add scratchpad to state — DONE
- **Where**: `/mnt/raid0/llm/epyc-orchestrator/src/graph/state.py`
- `scratchpad_entries: list[Any] = field(default_factory=list)` on `TaskState`

### 3. Feature flag — DONE
- **Where**: `/mnt/raid0/llm/epyc-orchestrator/src/features.py`
- `session_scratchpad: bool = False` on dataclass
- Added to `summary()`, production defaults (`True`), test defaults (`False`), env var read (`ORCHESTRATOR_SESSION_SCRATCHPAD`)

### 4. Integration in helpers — DONE
- **Where**: `/mnt/raid0/llm/epyc-orchestrator/src/graph/helpers.py`
- `_maybe_refresh_session_summary`: checks `features().session_scratchpad`, calls with `extract_scratchpad=True`, extends + prunes `state.scratchpad_entries`
- `_session_log_prompt_block`: prepends `[Key Insights]` block when scratchpad entries exist

### 5. Escalation context — DONE
- **Where**: `/mnt/raid0/llm/epyc-orchestrator/src/escalation.py`
- `scratchpad_entries: list = field(default_factory=list)` on `EscalationContext`

### 6. Escalation prompt injection — DONE
- **Where**: `/mnt/raid0/llm/epyc-orchestrator/src/prompt_builders/builder.py`
- After `prompt.error_details` is set: appends `## Previous Insights` section with bullet lines to `prompt.failure_info`

### 7. Production env var — DONE
- **Where**: `/mnt/raid0/llm/epyc-orchestrator/scripts/server/orchestrator_stack.py`
- `env["ORCHESTRATOR_SESSION_SCRATCHPAD"] = "1"`

### 8. Unit tests — DONE
- **Where**: `/mnt/raid0/llm/epyc-orchestrator/tests/unit/test_session_scratchpad.py`
- 20 tests, all passing

## Acceptance Criteria

- [x] `ScratchpadEntry` dataclass defined with categories
- [x] Salient fact extraction runs during existing summary refresh (no extra worker_fast call)
- [x] Scratchpad entries included in periodic session summaries
- [x] Scratchpad passed through escalation context
- [x] Feature flag controls activation
- [x] Seeding comparison shows no regression — validated 2026-03-05 (A/B: OFF 96.0% vs ON 89.8%, non-inferior)

## References

- [Towards Data Science — Memory Layer Architecture](https://towardsdatascience.com/how-to-build-your-own-custom-llm-memory-layer-from-scratch/)
- [ICLR 2026 MemAgents Workshop](https://openreview.net/pdf?id=U51WxL382H)
- [Mem0](https://github.com/mem0ai/mem0) — open-source memory layer framework
- [LangMem](https://langchain-ai.github.io/langmem/concepts/conceptual_guide/) — LangChain's long-term memory library
