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

### Incremental Must-Test Tranche (2026-04-14)

Executed next must-test items from the matrix with test-only changes:
- Added flat embedding shape coverage for `_precompute_embedding()` in `tests/unit/test_seeding_injection_additional.py`.
- Added non-standard eval-line fallback coverage for `parse_timing()` in `tests/unit/test_script_lib_output_parser.py`.

Verification:
- `python3 -m pytest -q tests/unit/test_seeding_injection_additional.py tests/unit/test_script_lib_output_parser.py` → `16 passed`
- `make coverage-orchestrator-slice` → `108 passed`

Coverage deltas in gated files:
- `scripts/benchmark/seeding_injection.py`: `98.94%` → `100.00%`
- `scripts/lib/output_parser.py`: `93.58%` → `99.08%` (only line 107 remains)

GitNexus status:
- Re-index succeeded after environment stabilization using:
  - `npx -y gitnexus@1.6.1 analyze --skip-agents-md --no-stats -v`
- Repo now reports `Status: ✅ up-to-date`.

### Incremental Must-Test Tranche 2 (2026-04-14)

Executed next control-plane tranche:
- Runtime micro-fix in `scripts/lib/output_parser.py` `parse_response()`:
  - moved `common_perf_print` end-of-response check before generic skip filtering so the branch is semantically live.
  - impact warning was HIGH for `parse_response`; edit kept minimal and parser-intent preserving.
- Added targeted tests for benchmark control-plane and executor branch surfaces:
  - `tests/unit/test_seeding_orchestrator.py`
  - `tests/unit/test_benchmark_executor_branching.py`
  - `tests/unit/test_benchmark_executor_additional.py`
- Raised enforced floors in `scripts/analysis/check_orchestrator_slice_coverage.py`:
  - `seeding_injection`: `95 -> 100`
  - `output_parser`: `90 -> 99`

Verification:
- `python3 -m pytest -q tests/unit/test_script_lib_output_parser.py tests/unit/test_seeding_injection_additional.py tests/unit/test_seeding_orchestrator.py tests/unit/test_benchmark_executor_branching.py tests/unit/test_benchmark_executor_additional.py` → `55 passed`
- `make coverage-orchestrator-slice` → `120 passed`

Coverage deltas in gated files:
- `scripts/lib/output_parser.py`: `99.08%` → `100.00%`
- `scripts/lib/executor.py`: `88.04%` → `95.43%`
- `scripts/benchmark/seeding_orchestrator.py`: `80.49%` → `92.68%`
- `scripts/benchmark/seeding_injection.py`: held at `100.00%`

Residual notable gaps (focused slice):
- `scripts/lib/onboard.py`: `83.08%` (branch-heavy family/role mapping and import-fallback paths)
- `scripts/lib/registry.py`: `86.88%` (family mapping variants and defensive returns)

### Incremental Must-Test Tranche 3 (2026-04-14)

Executed focused `onboard` + `registry` closure tranche with mostly test-only changes:
- Added extensive branch coverage in:
  - `tests/unit/test_script_lib_registry.py`
  - `tests/unit/test_script_lib_onboard.py`
- Kept runtime behavior unchanged for `onboard`/`registry`.
- Tightened per-file gate floors in `scripts/analysis/check_orchestrator_slice_coverage.py`:
  - `executor` `85 -> 90`
  - `registry` `85 -> 95`
  - `onboard` `80 -> 95`
  - `seeding_orchestrator` `80 -> 90`

Verification:
- `python3 -m pytest -q tests/unit/test_script_lib_registry.py tests/unit/test_script_lib_onboard.py` → `27 passed`
- `make coverage-orchestrator-slice` → `130 passed`

Coverage deltas in gated files:
- `scripts/lib/registry.py`: `86.88%` → `100.00%`
- `scripts/lib/onboard.py`: `83.08%` → `98.19%`
- `scripts/lib/executor.py`: held `95.43%`
- `scripts/benchmark/seeding_orchestrator.py`: held `92.68%`
- `scripts/lib/output_parser.py`: held `100.00%`
- `scripts/benchmark/seeding_injection.py`: held `100.00%`
- `scripts/benchmark/seeding_infra.py`: held `100.00%`

Residual misses in focused slice are now narrow:
- `scripts/lib/onboard.py`: `34-37` (import fallback path), `169`, `178` (specific family variants)
- `scripts/lib/executor.py`: mostly portability/diagnostic branches and fallback loader paths.

Tranche-3 follow-up (same day):
- Added two additional `detect_family()` branch assertions (DeepSeek-R1-Distill-Qwen, Llama-3.2).
- `scripts/lib/onboard.py` improved further from `98.19%` to `98.79%`.
- Remaining onboard misses are now only import fallback lines `34-37`.

### Incremental Must-Test Tranche 4 (2026-04-14)

Executed final focused closure tranche for remaining `executor`, `seeding_orchestrator`, and onboard import-fallback lines.

Risk workflow:
- Re-indexed GitNexus and confirmed current index.
- Re-ran impact before edits:
  - `_erase_slots`: `CRITICAL`
  - `_force_erase_and_verify`: `CRITICAL`
  - `_call_orchestrator_with_slot_poll`: `HIGH`
- Because of blast radius, kept this tranche test-only on those symbols.

Test additions:
- `tests/unit/test_seeding_orchestrator.py`
  - covered remaining slot erase strategy fallback/exception branches, force-erase short-circuit and probe exception, non-200/exception probes, progress-none continue path, progress logging + heartbeat path, and direct `_run` call path.
- `tests/unit/test_benchmark_executor_additional.py`
  - covered import fallback load path, `_read_registry_timeout` runtime-default map branch, `validate_binaries` missing-binary raise path, HTTP session creation, explicit/default context selection in `start()`, `wait_ready()` timeout/default/diagnostic branches, `is_running()`, and dense model size fallback branch.
- `tests/unit/test_script_lib_onboard.py`
  - covered standalone import fallback path for lines `34-37`.

Verification:
- `python3 -m pytest -q tests/unit/test_seeding_orchestrator.py tests/unit/test_benchmark_executor_additional.py` → `44 passed`
- `python3 -m pytest -q tests/unit/test_script_lib_onboard.py` → `15 passed`
- `make coverage-orchestrator-slice` → `148 passed`

Focused gate final state:
- `scripts/benchmark/seeding_infra.py`: `100.00%`
- `scripts/benchmark/seeding_injection.py`: `100.00%`
- `scripts/lib/output_parser.py`: `100.00%`
- `scripts/lib/registry.py`: `100.00%`
- `scripts/lib/executor.py`: `100.00%`
- `scripts/benchmark/seeding_orchestrator.py`: `100.00%`
- `scripts/lib/onboard.py`: `100.00%`

Result:
- All seven orchestrator-slice gate files are now fully covered (`100%`) with no additional runtime behavior edits in this tranche.

### Broader Benchmark Tranche A (2026-04-14)

Post-slice expansion to high-signal benchmark support modules not currently enforced by the 7-file orchestrator-slice gate.

Risk workflow:
- Re-indexed GitNexus first.
- Impact checks before runtime consideration:
  - `checkpoint_result`: `HIGH`
  - `load_checkpoint`: `HIGH`
  - `_adaptive_timeout_s`: `CRITICAL`
- Kept this tranche strictly test-only (no runtime symbol changes).

Test additions:
- `tests/unit/test_seeding_scoring.py`
- `tests/unit/test_seeding_checkpoint.py`
- `tests/unit/test_seeding_types_state.py`

Verification:
- `python3 -m pytest -q tests/unit/test_seeding_scoring.py tests/unit/test_seeding_checkpoint.py tests/unit/test_seeding_types_state.py` → `17 passed`
- Targeted coverage run:
  - `python3 -m pytest -q ... --cov=scripts/benchmark --cov-report=term-missing --cov-fail-under=0`
  - `scripts/benchmark/seeding_scoring.py`: `0% -> 100%`
  - `scripts/benchmark/seeding_checkpoint.py`: `0% -> 100%`
  - `scripts/benchmark/seeding_types.py`: `92% -> 100%`
- Existing enforced gate remains stable:
  - `make coverage-orchestrator-slice` → `148 passed`, all 7 gated files still at `100%`.

Note:
- These new module gains are validated but not yet included in `coverage-orchestrator-slice` threshold enforcement.

### Broader Benchmark Tranche B (2026-04-14)

Extended coverage characterization to benchmark eval/reward logic.

Risk workflow:
- GitNexus index confirmed up-to-date before work.
- Impact checks (high fanout):
  - `_eval_single_config`: `CRITICAL`
  - `evaluate_question_3way`: `CRITICAL`
  - `_compute_3way_metadata`: `CRITICAL`
  - `detect_escalation_chains`: `CRITICAL`
  - `extract_web_research_telemetry`: `HIGH`
  - `compute_web_research_rewards`: `HIGH`
  - `compute_scratchpad_rewards`: `HIGH`
- Kept tranche test-only due blast radius.

Test additions:
- `tests/unit/test_seeding_rewards.py`
- `tests/unit/test_seeding_eval.py`

Verification:
- `python3 -m pytest -q tests/unit/test_seeding_rewards.py tests/unit/test_seeding_eval.py` → `18 passed`
- Combined broader benchmark tranche suites:
  - `python3 -m pytest -q tests/unit/test_seeding_scoring.py tests/unit/test_seeding_checkpoint.py tests/unit/test_seeding_types_state.py tests/unit/test_seeding_rewards.py tests/unit/test_seeding_eval.py` → `35 passed`
- Targeted coverage run:
  - `python3 -m pytest -q tests/unit/test_seeding_rewards.py tests/unit/test_seeding_eval.py --cov=scripts/benchmark --cov-report=term-missing --cov-fail-under=0`
  - `scripts/benchmark/seeding_eval.py`: `0% -> 80%`
  - `scripts/benchmark/seeding_rewards.py`: `0% -> 93%`
- Existing enforced 7-file gate remains stable:
  - `make coverage-orchestrator-slice` → `148 passed` (all enforced files remain `100%`).

Note:
- `seeding_eval` and `seeding_rewards` gains are currently targeted/validated but not yet part of the enforced `coverage-orchestrator-slice` threshold list.

### Broader Benchmark Tranche C (2026-04-14)

Extended characterization to legacy comparative-path control logic.

Risk workflow:
- GitNexus status confirmed up-to-date before changes.
- Impact checks:
  - `evaluate_question`: `HIGH`
  - `_build_role_mode_combos`: `HIGH`
  - `run_batch`: `LOW`
- Strategy remained test-only due fanout on legacy entrypoints.

Test additions:
- `tests/unit/test_seeding_legacy.py`

Verification:
- `python3 -m pytest -q tests/unit/test_seeding_legacy.py` → `12 passed`
- Targeted coverage run:
  - `python3 -m pytest -q tests/unit/test_seeding_legacy.py --cov=scripts/benchmark --cov-report=term-missing --cov-fail-under=0`
  - `scripts/benchmark/seeding_legacy.py`: `0% -> 92%`
- Regression safety:
  - `make coverage-orchestrator-slice` unchanged at `148 passed` with all 7 enforced files still `100%`.

Result:
- Legacy seeding fallback behavior is now substantially regression-characterized without runtime edits.

### Broader Benchmark Tranche D (2026-04-14)

Extended characterization to the seeding TUI diagnostics surface.

Risk workflow:
- GitNexus status confirmed up-to-date.
- Impact checks:
  - `SeedingTUI`: `HIGH`
  - `TapTailer`: `MEDIUM`
  - `_style_stream_lines`: `LOW`
  - `_latex_to_unicode`: `LOW`
- Because this path is shared by benchmark/autopilot frontends, kept tranche strictly test-only.

Test additions:
- `tests/unit/test_seeding_tui.py` (13 tests)

Verification:
- `python3 -m pytest -q tests/unit/test_seeding_tui.py` → `13 passed`
- Targeted coverage run:
  - `python3 -m pytest -q tests/unit/test_seeding_tui.py --cov=scripts/benchmark --cov-report=term-missing --cov-fail-under=0`
  - `scripts/benchmark/seeding_tui.py`: `0% -> 85%`
- Combined seeding characterization suite:
  - `python3 -m pytest -q tests/unit/test_seeding_*.py tests/unit/test_seeding_tui.py --cov=scripts/benchmark --cov-report=term-missing --cov-fail-under=0` → `131 passed`
- Regression safety:
  - `make coverage-orchestrator-slice` remained `148 passed` (all enforced files `100%`).

Result:
- TUI observability path is no longer uncovered; key display/sanitization/tailer lifecycle branches are now tested.

### Broader Benchmark Tranche E (2026-04-14)

Closed the remaining uncovered branches in `seeding_eval.py`.

Risk workflow:
- GitNexus index confirmed current before edits.
- Impact checks:
  - `_eval_single_config`: `CRITICAL`
  - `evaluate_question_3way`: `CRITICAL`
- Strategy remained test-only due fanout into benchmark `main` + autopilot dispatch paths.

Test additions:
- Expanded `tests/unit/test_seeding_eval.py` (5 additional branch-focused tests)

Verification:
- `python3 -m pytest -q tests/unit/test_seeding_eval.py` → `12 passed`
- Targeted coverage run:
  - `python3 -m pytest -q tests/unit/test_seeding_eval.py --cov=scripts/benchmark --cov-report=term-missing --cov-fail-under=0`
  - `scripts/benchmark/seeding_eval.py`: `80% -> 100%`
- Combined seeding characterization suite:
  - `python3 -m pytest -q tests/unit/test_seeding_*.py tests/unit/test_seeding_tui.py --cov=scripts/benchmark --cov-report=term-missing --cov-fail-under=0` → `137 passed`
- Regression safety:
  - `make coverage-orchestrator-slice` remained `148 passed` (all enforced files `100%`).

Result:
- `seeding_eval.py` is now fully covered with test-only changes; residual notable benchmark gaps in this seeding-focused slice are now primarily `seeding_tui` (`85%`), `seeding_legacy` (`92%`), and `seeding_rewards` (`93%`).

### Broader Benchmark Tranche F (2026-04-14)

Closed the remaining `seeding_rewards.py` coverage gaps.

Risk workflow:
- GitNexus status confirmed up-to-date.
- Impact checks were HIGH on:
  - `extract_web_research_telemetry`
  - `compute_web_research_rewards`
  - `compute_scratchpad_rewards`
- Kept tranche test-only to avoid touching high-fanout reward logic.

Test additions:
- Expanded `tests/unit/test_seeding_rewards.py` with 6 additional branch-focused cases.

Verification:
- `python3 -m pytest -q tests/unit/test_seeding_rewards.py` → `16 passed`
- Targeted coverage run:
  - `python3 -m pytest -q tests/unit/test_seeding_rewards.py --cov=scripts/benchmark --cov-report=term-missing --cov-fail-under=0`
  - `scripts/benchmark/seeding_rewards.py`: `93% -> 100%`
- Combined seeding characterization suite:
  - `python3 -m pytest -q tests/unit/test_seeding_*.py tests/unit/test_seeding_tui.py --cov=scripts/benchmark --cov-report=term-missing --cov-fail-under=0` → `141 passed`
- Regression safety:
  - `make coverage-orchestrator-slice` remained `148 passed` (all enforced files still `100%`).

Result:
- Seeding control-plane coverage is now `100%` for `seeding_checkpoint`, `seeding_eval`, `seeding_infra`, `seeding_injection`, `seeding_orchestrator`, `seeding_rewards`, `seeding_scoring`, and `seeding_types`.
- Remaining notable gaps in this focused tranche set are now `seeding_legacy` (`92%`) and `seeding_tui` (`85%`).
