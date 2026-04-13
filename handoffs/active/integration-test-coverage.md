# Integration Test Coverage — Remaining Gaps

**Status**: ACTIVE — ready for execution when inference stack is available
**Created**: 2026-04-13
**Priority**: MEDIUM
**Primary repo**: `/mnt/raid0/llm/epyc-orchestrator`

## Context

The orchestrator refactoring audit (Phases 0-8, now completed) decomposed `graph/helpers.py` into 10 modules and hardened diagnostic surfaces across the codebase. Unit test coverage on the extracted modules averages **88%**. The remaining gaps require integration-level fixtures — a wired `GraphRunContext` with real REPL, config, and backend connections — that can't be meaningfully mocked.

## Current Unit Coverage (post-refactoring)

| Module | Coverage | Uncovered Lines | Why Integration |
|--------|----------|-----------------|-----------------|
| `graph/task_ir_helpers.py` | 95% | 48, 51, 97, 101 | Non-dict step edge cases in TaskIR plan parsing |
| `graph/budgets.py` | 96% | 64-65, 68 | `difficulty_signal` import error fallback in band lookup |
| `graph/decision_gates.py` | 93% | 46, 116-119, 155 | `_make_end_result` needs full GraphRunContext + REPL artifacts |
| `graph/answer_resolution.py` | 93% | 35, 37, 39, 45 | Regex edge cases on real LLM output |
| `graph/workspace.py` | 89% | 27,29,33,35,57,90,98,113,121,149-150,162 | Workspace broadcast needs real graph state mutation |
| `graph/think_harder.py` | 88% | 61, 105, 108-125 | `_should_think_harder` cooldown/ROI/marginal-utility gates need full config |
| `graph/session_summary.py` | 84% | 30,67-68,92-93,122-124,147,153,166-174,204-212,233,287-291 | Two-level summary + session log prompt assembly need real REPL history |
| `graph/compaction.py` | 83% | 87-91,125-126,140-150,163,169-171,184,218-219 | Session token budget trigger + recompaction interval logic |
| `graph/observability.py` | 80% | 27-29,45,51-52,67-68,89-90 | `_record_failure`/`_add_evidence` need FailureGraph/HypothesisGraph |
| `graph/file_artifacts.py` | 76% | 24,28-34,61-63 | Solution file persistence + output spill need real REPL artifacts dict |

## Other Integration-Level Gaps

| Module | Coverage | Gap Description |
|--------|----------|-----------------|
| `graph/helpers.py` | 57% | `_execute_turn` (~600 lines) — the main orchestration loop; needs full LLM call + REPL execution cycle |
| `graph/nodes.py` | 48% | Node execution paths — needs `GraphRunContext` with typed state transitions |
| `graph/graph.py` | 47% | Graph entry point (`run_task`) — needs all node types wired |
| `runtime/inference_lock.py` | 43% | fcntl-based file locking, `/proc/locks` parsing, watchdog thread — platform-specific |
| `backends/concurrency_aware.py` | 59% | KV save/restore/migrate paths — needs real llama-server slots |
| `api/routes/chat.py` | 53% | HTTP endpoint — needs ASGI test client (httpx.AsyncClient + app) |
| `api/routes/documents.py` | 50% | Document preprocessing endpoints — needs PDF/OCR service mocks |

## Integration Test Plan

### Fixture: `GraphRunContext` Factory

Create a reusable fixture that assembles a minimal but real `GraphRunContext`:

```python
@pytest.fixture
def graph_ctx(tmp_path):
    """Minimal GraphRunContext for integration tests."""
    from src.graph.state import TaskState, TaskDeps
    from src.repl_environment.environment import REPLEnvironment
    from src.features import Features

    state = TaskState(task_id="test", context="test context")
    repl = REPLEnvironment(context="test", work_dir=str(tmp_path))
    deps = TaskDeps(
        config=GraphConfig.from_defaults(),
        primitives=MockLLMPrimitives(),  # Returns canned responses
        repl=repl,
        features=Features(),
    )
    return GraphRunContext(state=state, deps=deps)
```

### Test Phases

**Phase 1: Graph execution loop** (highest value)
- Wire `_execute_turn` with a mock LLM that returns `FINAL("answer")`
- Verify: answer extraction, session turn recording, token tracking
- Target: `helpers.py` 57% → 75%+

**Phase 2: Node-level paths**
- Test each node type (Frontdoor, Coder, Architect, Worker) through a single turn
- Verify: escalation decisions, think-harder gating, retry logic
- Target: `nodes.py` 48% → 70%+

**Phase 3: Failure/observability**
- Test `_record_failure`, `_add_evidence`, `_log_escalation` with real FailureGraph/HypothesisGraph
- Verify: failure patterns recorded, mitigations suggested
- Target: `observability.py` 80% → 95%+

**Phase 4: API endpoints**
- Use `httpx.AsyncClient` with the FastAPI app for chat, documents, health
- Verify: streaming, delegation, vision pipeline paths
- Target: `chat.py` 53% → 75%+

### Prerequisites

- Running inference stack (at least one llama-server for smoke tests)
- OR a `MockLLMPrimitives` that returns realistic `InferenceResult` objects with correct fields

### Execution Constraints

- Integration tests should be in `tests/integration/` (separate from unit)
- Mark with `@pytest.mark.integration` so they can be excluded from fast CI
- Each test should be self-contained (no shared state across tests)
- Timeout: 30s per test (real LLM calls are slow)

## Key Files

| File | Purpose |
|------|---------|
| `/mnt/raid0/llm/epyc-orchestrator/src/graph/helpers.py` | Main execution loop (966 lines) |
| `/mnt/raid0/llm/epyc-orchestrator/src/graph/nodes.py` | Node implementations |
| `/mnt/raid0/llm/epyc-orchestrator/src/graph/state.py` | TaskState, TaskDeps, GraphRunContext |
| `/mnt/raid0/llm/epyc-orchestrator/src/graph/graph.py` | Graph entry point |
| `/mnt/raid0/llm/epyc-orchestrator/tests/integration/` | Target directory for new tests |

## Reporting

After each integration test pass, update this handoff with:
- Coverage deltas per module
- Any production bugs discovered
- New test count
