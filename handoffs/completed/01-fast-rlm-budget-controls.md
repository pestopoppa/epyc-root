# Fast-RLM Budget Controls

**Status**: COMPLETED
**Created**: 2026-03-03
**Priority**: P0 — prevents infinite loops, no model changes required
**Effort**: Low
**Source**: [Fast-RLM (github.com/avbiswas/fast-rlm)](https://github.com/avbiswas/fast-rlm)

## Research Review

### Fast-RLM: Recursive Language Models
**Author:** Avishek Biswas

Minimal implementation of Recursive Language Models — processes arbitrarily long prompts by hierarchical agent decomposition. Primary agent coordinates sub-agents; sub-agent responses appear as variables (not full context). Budget controls for API spend, tokens, recursion depth. Truncated REPL output (default 2000 chars). Deno + Pyodide runtime.

**Orchestrator Relevance: HIGH.** Architecturally very similar to our orchestrator's escalation pattern:
- **Sub-agent results as variables, not context**: Our solution file persistence does exactly this — pass file path, not full code. Validates our approach.
- **Budget controls**: We have token caps (`_repl_turn_token_cap`) but lack recursion depth/call count limits. Their budget model is more comprehensive.
- **Truncated REPL output (2000 chars)**: We use 5000 tokens. Their lower default suggests more aggressive truncation may work.
- **Hierarchical decomposition**: Maps to our root LM → specialist worker → escalation flow.

### Patterns to Adopt
- Formal recursion depth limits (prevent infinite escalation loops)
- Call count budgets per worker invocation
- Variable-passing instead of context-stuffing for inter-agent communication

## References

- [Fast-RLM repo](https://github.com/avbiswas/fast-rlm)
- Existing token caps: `src/graph/helpers.py` — `_repl_turn_token_cap()`, `_frontdoor_repl_non_tool_token_cap()`
- Escalation flow: `src/graph/` — escalation context passing
- Solution file persistence: `_solution_file_path()`, `_persist_solution_file()` in `src/graph/helpers.py`

## Implementation Steps

### 1. Escalation depth limits — DONE (already implemented)
Existing protections cover this comprehensively:
- `max_escalations=2` in `GraphConfig` — caps total escalation count
- `detect_role_cycle()` in `escalation_helpers.py` — detects A→B→A loops
- `max_turns=15` in `TaskState` — hard cap on total turns across all roles
- `consecutive_failures` with `max_retries=2` — caps retries before escalation
No additional work needed.

### 2. Worker call budget (REPL execution cap) — DONE
- **Where**: `src/graph/helpers.py`, `src/graph/nodes.py`, `src/graph/state.py`
- `state.repl_executions` counter incremented after each REPL execute() call
- `_worker_call_budget_cap()` reads `ORCHESTRATOR_WORKER_CALL_BUDGET_CAP` (default: 30)
- `_check_budget_exceeded()` checks counter against cap when `worker_call_budget` feature enabled
- Budget check runs in all 7 node `run()` methods before `_execute_turn()`
- Pressure warning injected into prompt when ≤3 REPL calls remaining
- Feature flag: `worker_call_budget` (env: `ORCHESTRATOR_WORKER_CALL_BUDGET`)

### 3. Per-task aggregate token budget — DONE
- **Where**: `src/graph/helpers.py`, `src/graph/nodes.py`, `src/graph/state.py`
- `state.aggregate_tokens` counter updated from `_last_inference_meta["tokens"]` after each LLM call
- `_task_token_budget_cap()` reads `ORCHESTRATOR_TASK_TOKEN_BUDGET_CAP` (default: 200000)
- `_check_budget_exceeded()` checks counter against cap when `task_token_budget` feature enabled
- Pressure warning injected into prompt when <15% token budget remaining
- Feature flag: `task_token_budget` (env: `ORCHESTRATOR_TASK_TOKEN_BUDGET`)

### 4. Evaluate REPL truncation at 2000 chars — DEFERRED
Requires seeding benchmark runs, not code changes. Will evaluate after budget controls are validated in production.

## Acceptance Criteria

- [x] Escalation depth tracked in state; configurable max enforced (pre-existing)
- [x] Worker call count budget enforced with graceful termination
- [x] Per-task aggregate token budget tracked and enforced
- [x] All budgets configurable via env vars and feature flags
- [x] No infinite escalation loops possible (pre-existing)
- [ ] REPL truncation benchmark completed with recommendation (DEFERRED)

## Files Modified

- `src/graph/state.py` — `repl_executions`, `aggregate_tokens` fields
- `src/features.py` — `worker_call_budget`, `task_token_budget` flags
- `src/graph/helpers.py` — `_worker_call_budget_cap()`, `_task_token_budget_cap()`, `_check_budget_exceeded()`, `_budget_pressure_warnings()`, counter increments in `_execute_turn()`
- `src/graph/nodes.py` — budget check in all 7 node `run()` methods
- `scripts/server/orchestrator_stack.py` — production env vars
