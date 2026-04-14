# Integration Test Coverage — Remaining Gaps

**Status**: ACTIVE — Phases 1-4 integration tests written (61 new tests, all passing)
**Created**: 2026-04-13
**Updated**: 2026-04-13 (Phase 1-4 integration tests implemented with mock LLM + real REPL)
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

**Phase 1: Graph execution loop** (highest value) ✅ 2026-04-13
- 17 tests: FINAL extraction, non-final turns, errors, nudges, prose rescue, session log, workspace
- Uses real REPLEnvironment with mock LLM primitives

**Phase 2: Node-level paths** ✅ 2026-04-13
- 15 tests: FrontdoorNode, WorkerNode, CoderNode happy/error/escalation paths + `run_task` E2E
- Covers retry logic, escalation chain, max turns, mitigation recording

**Phase 3: Failure/observability** ✅ 2026-04-13
- 19 tests: `_record_failure`, `_add_evidence`, `_record_mitigation`, `_log_escalation`, `_make_end_result`
- Uses real StubFailureGraph/StubHypothesisGraph implementations

**Phase 4: API endpoints** ✅ 2026-04-13
- 10 tests: health, stats, chat, OpenAI-compat, models endpoints
- Uses FastAPI TestClient with dependency overrides

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

## Progress — 2026-04-13

### New Tests Added: 61 total (all passing)

| File | Tests | Target Module | What's Covered |
|------|-------|---------------|----------------|
| `tests/integration/conftest.py` | — | Fixtures | `StubFailureGraph`, `StubHypothesisGraph`, `make_mock_primitives`, `graph_ctx` factory |
| `tests/integration/test_execute_turn.py` | 17 | `graph/helpers.py` | FINAL extraction (string/numeric/computed), non-final turns, runtime errors, no-primitives/no-REPL guards, comment-only nudge, silent execution nudge, status-message rejection, prose rescue, session log recording, REPL execution count, markdown code extraction, workspace state updates, LLM call exceptions |
| `tests/integration/test_node_execution.py` | 15 | `graph/nodes.py`, `graph/graph.py` | FrontdoorNode (happy path, max turns, rescue, retry, escalation), WorkerNode (happy, loop, escalation), CoderNode (happy, architect escalation, mitigation recording), `run_task` E2E (success, escalation flow, max turns), role history tracking |
| `tests/integration/test_observability.py` | 19 | `graph/observability.py`, `graph/decision_gates.py` | `_record_failure` (with/without graph, severity scaling, truncation, last_failure_id), `_add_evidence` (success/failure, noop, confidence), `_record_mitigation` (with id, fallback, noop cases), `_log_escalation` (with/without logger), `_make_end_result` (evidence recording, workspace decisions, metadata) |
| `tests/integration/test_api_endpoints.py` | 10 | `api/routes/health.py`, `api/routes/chat.py`, etc. | Health endpoint (status, version, knowledge tools), stats endpoint, chat validation (missing prompt, valid request, task_id), OpenAI-compat (messages, model validation), models endpoint |

### Regression Check
- **Unit tests**: 4919 passed, 7 skipped, 0 failures
- **Integration tests**: 371 passed (310 pre-existing + 61 new), 12 skipped, 1 pre-existing failure (`test_cache_integration.py` MagicMock type error — not related)

### Key Design Decisions
- Mock LLM responses must be wrapped in markdown code blocks (` ```python ... ``` `) when testing non-final flows, otherwise `auto_wrap_final` or prose rescue converts them to FINAL answers
- Session log recording requires `Features(session_log=True)` feature flag
- `StubFailureGraph`/`StubHypothesisGraph` are real in-memory implementations (not MagicMock) to exercise the full protocol surface
- REPL is real (executes actual Python) — only LLM calls are mocked

### Remaining Gaps (need inference stack)
- Real LLM output parsing with production model responses
- Think-harder config with actual CoT prefix injection
- Budget controls with realistic token counts
- Backend health probing in health endpoint (currently mocked)
- Streaming chat response testing

## Reporting

After each integration test pass, update this handoff with:
- Coverage deltas per module
- Any production bugs discovered
- New test count

## Focused Slice 100%-Coverage Feasibility Audit (2026-04-14)

Scope audited from `make coverage-orchestrator-slice`:
- `scripts/benchmark/seeding_infra.py` `100.00%`
- `scripts/lib/executor.py` `88.04%`
- `scripts/lib/registry.py` `86.88%`
- `scripts/lib/output_parser.py` `93.58%`
- `scripts/lib/onboard.py` `83.08%`
- `scripts/benchmark/seeding_injection.py` `98.94%`
- `scripts/benchmark/seeding_orchestrator.py` `80.49%`

### Verdict

Blanket `100%` across all seven files is not the right short-term target.

Reason:
- some misses are high-value and should be tested;
- some are portability/defensive branches with low defect yield;
- at least one uncovered line is effectively dead under current control flow (`output_parser.parse_response()` line with `common_perf_print` break is shadowed by earlier skip pattern).

### Must-Test vs Acceptable-Gap Matrix

`scripts/benchmark/seeding_infra.py` (`100%`)
- Must-test: N/A for this pass (already fully covered in focused slice).
- Acceptable gap: none.

`scripts/benchmark/seeding_injection.py` (`98.94%`)
- Must-test:
  - `_precompute_embedding()` flat `"embedding": [..]` shape return branch.
- Acceptable gap:
  - none; this file is realistically a `100%` candidate.

`scripts/lib/output_parser.py` (`93.58%`)
- Must-test:
  - `parse_timing()` final fallback loop for non-standard `"eval time"` lines with `"tokens per second"`.
- Acceptable gap / cleanup candidate:
  - `parse_response()` `common_perf_print` break branch currently shadowed by prior `skip_patterns` match (`"common_"`), so this is dead-ish unless logic order changes.

`scripts/lib/registry.py` (`86.88%`)
- Must-test:
  - `get_max_context()` family fallback branches (`llama2`, `qwen2`, `deepseek-r1`, `gemma3`) because they influence runtime context sizing.
  - direct wrappers `get_moe_override_key()` and `get_baseline_experts()` for non-empty acceleration config.
- Acceptable gap (lower risk mapping/defensive returns):
  - missing-role/null-path returns (`get_model_path`, `get_mmproj_path`, etc.).
  - expanded `_get_quirk_keys_for_model()` variant mapping branches beyond currently active fleet.

`scripts/lib/onboard.py` (`83.08%`)
- Must-test:
  - `detect_family()` and `generate_role_name()` branch families that alter role assignment behavior.
  - `generate_compatible_targets_patterns()` branches for draft families used by current onboarding flow.
- Acceptable gap:
  - import fallback (`except ImportError` local-run path).
  - registry-timeout fallback and default `load_registry()` path wiring.

`scripts/lib/executor.py` (`88.04%`)
- Must-test:
  - `build_command()` config-type branches (`completion` + `--no-conversation`, `moe`, `moe_spec`) because they directly affect invoked binaries/flags.
  - `get_configs_for_architecture()` branches that add compound configs from compatible drafts.
- Acceptable gap:
  - portability/import fallback (`numactl`/ImportError fallback import path).
  - diagnostic printing branches in `wait_ready()` and temp-file cleanup line.

`scripts/benchmark/seeding_orchestrator.py` (`80.49%`)
- Must-test:
  - `_erase_slots()` and `_recover_heavy_ports_if_stuck()` failure branches (control-plane recovery behavior).
  - `_read_slot_progress()` coercion-failure fallbacks for malformed slot payloads.
- Acceptable gap for now:
  - heartbeat/debug logging cadence branches in `_call_orchestrator_with_slot_poll()`.
  - optional payload field branches in `call_orchestrator_forced()` (low defect risk compared to recovery/timeout flow).

### Recommended Floor Strategy (Do Not Force 100%)

Use staged floor raises with explicit branch-classification review:
- Phase A (now): keep current gate floors as stability contract.
- Phase B (next): raise floors after must-test branches land:
  - `seeding_injection` `95 -> 99/100`
  - `output_parser` `90 -> 98` (or `100` only after dead-branch cleanup)
  - `registry` `85 -> 88+`
  - `onboard` `80 -> 85+`
  - `executor` `85 -> 88+`
  - `seeding_orchestrator` `80 -> 83+`
- Phase C: only chase `100%` per-file where residual misses are deterministic and behaviorally meaningful.

### Tooling Note

GitNexus was checked before considering symbol edits, but local re-index failed in this environment:
- `npx gitnexus status` worked and reported stale index.
- `npx gitnexus analyze` failed with npm packaging error (`Cannot destructure property 'package' of 'node.target' as it is null`).

Given that blocker, this pass was kept read-only on runtime code and focused on classification + planning.
