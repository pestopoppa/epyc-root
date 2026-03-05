# REPL Session Log

**Status:** PRODUCTION — enabled via `ORCHESTRATOR_SESSION_LOG=1` in `orchestrator_stack.py` (2026-03-05)
**Created:** 2026-03-03
**Owner:** Agent

## Problem Statement

Each REPL turn builds a fresh prompt with only `last_output`/`last_error` from the single previous turn. All earlier turns — code, outputs, errors, tool results — are invisible. Models restart from scratch, repeat failed approaches, and lose context across escalation boundaries. Each turn IS part of the inference process, not an independent request.

## Architecture

**Two-file design per task:**
- **Session log** (`session_{task_id}.md`) — append-only processing journal. Read-only reference for the model.
- **Solution file** (`{task_id}_solution.py`) — the evolving code artifact. Already exists.

**Worker-generated summaries:** Uses `worker_fast` (1.5B, 4 slots, ~100+ t/s) for intelligent session summaries. Deterministic fallback if worker unavailable. Regenerated every 2-3 turns or on escalation.

## Dependency Map

```
session_log.py (new) → helpers.py → state.py → builder.py
                                                constants.py
```

## Key Files

| File | Changes |
|------|---------|
| `src/graph/session_log.py` | **NEW** — TurnRecord, append/build/summarize functions |
| `src/graph/state.py` | Add 4 fields to TaskState |
| `src/graph/helpers.py` | 4 integration points in `_execute_turn()` |
| `src/prompt_builders/constants.py` | Update COMPLEX CODE rules |
| `src/features.py` | Add `session_log` feature flag |

## Integration Points in `_execute_turn()`

1. **Initialize** (after `state.turns += 1`): Set `state.session_log_path` on first turn
2. **Capture exploration baseline** (before REPL exec): Save exploration event count for tool-call diffing
3. **Record turn** (at each return point — 7 total): Build TurnRecord, append to memory + disk
4. **Inject summary** (after workspace block): Regenerate if stale, append to prompt. Also inject into escalation prompts.

### Return Points (7 total)
1. `return "", "No LLM primitives...", False, {}` — deps missing
2. `return "", f"LLM call failed: {e}", False, {}` — inference error
3. `return "", f"LLM call failed (unexpected): {e}", False, {}` — unexpected error
4. `return "", None, False, {"_nudge": nudge}` — comment-only nudge
5. `return "", None, False, {"_nudge": nudge}` — comment-ratio nudge
6. `return "", None, False, {"_nudge": nudge}` — silent execution nudge
7. `return output, result.error, result.is_final, artifacts` — normal return

## Existing Patterns Followed

- **repl_tap.py**: Thread-safe append-only log, fail-silent, `_IN_PYTEST` guard
- **Session compaction**: Worker-generated index (`worker_explore`), deterministic fallback
- **`_persist_solution_file()`**: Per-task file, sanitized task_id, fail-silent
- **Workspace state**: Blackboard pattern in state.py for cross-turn context

## Token Budget

| Component | Tokens |
|-----------|--------|
| Worker-generated summary | ~150-300 |
| Deterministic fallback | ~300-400 |
| Worker call latency | ~100-200ms |
| Regen frequency | Every 2-3 turns |

## Risk Mitigation

- **Worker contention**: Fast worker has 4 slots, low risk. Deterministic fallback.
- **Summary quality**: Structured input (TurnRecords) makes summarization straightforward.
- **Prompt size growth**: Summaries capped at ~300 tokens. Feature-flagged for rollback.
