Stage 1 is finished: all 9 findings are done and committed on `wt/o1`, nothing was skipped, and the combined regression run passed (875 tests). On the relayed question: yes, this ran in the ephemeral cloud container (4 CPUs, no `/mnt/raid0`), not on the operator's host.

## Per finding

All are status **done**. LOC figures are src net / tests net.

| Finding | Commit | What changed | Tests added | Net LOC |
|---|---|---|---|---|
| A1-02, A2-01, A1-M2 | `8f22bbb0` | Committed by the earlier implementer. Per-request counters, call log, `cache_prompt` and budget diagnostics live on a `RequestScope` bound by `begin_request()`; recursion depth and the early-stop predicate are ContextVars. I re-ran its tests in the combined run. | `test_primitives_request_scope.py` | +65 / +157 |
| A1-M1 | `e6169e90` | Committed by the earlier implementer. Every `/v1` mode now carries `cancel_check` and `task_id=chat_id`. Re-checked. | `test_v1_request_context.py` | +21 / +82 |
| A1-01 | `4dfc0b89` + `e0983c60` | See details below. | `test_api_event_loop_responsiveness.py` (4 tests, all 4 fail on base); one new behavioural test in `test_control_token_assemblers.py` | +45 / +138, then +3 / +13 |
| A4-M1 | `b423b243` | New `tool_policy.tool_context_for()` feeds all 9 `REPLEnvironment` construction sites. `/v1` and `/chat/stream` take the task type from the role via `task_type_for_role` (the same mapping as `derive_task_type_from_route`). | `test_no_web_tool_context.py` (4 behavioural cases fail on base) | +23 / +136 |
| A2-04, with a minimal A2-12 | `1a86a306` | See details below. | `test_backend_pool.py` (3 tests; 10 warm builds create 0 clients) | +67 / +74 |
| A2-13 | `ba61913d` | See details below. | `test_dispatch_region_lock_release.py` (2 of 3 fail on base) | +11 / +84 |
| A1-17 | `7e4b9a6b` | `route_with_skills` and `select_initial_route` now return `skill_ids` alongside `skill_context`; `extract_skill_ids` is deleted. | New test in `test_skill_integration.py` (fails on base: `[]` instead of 2 ids); ids are now asserted in the 3 existing `route_with_skills` tests | -12 / +36 |

**A1-01 details:**
- `/chat` routing now runs in a thread through a new helper, `chat_utils.to_thread_keeping_context`, so the stage-timing ContextVar it sets survives.
- Cheap-first, two-stage summarization and every non-streamed `/v1` model call go through `to_thread`.
- `/v1` REPL turns use the graph's `_execute_repl_with_timeout`. The REPL's own SIGALRM timeout only works on the main thread, so a plain `to_thread` would have silently dropped the timeout.
- The `AdmissionController` docstring is corrected.
- `e0983c60` is a follow-up: the CT-12.3c security sweep only saw direct sink calls, so moving `llm_call` into `to_thread` hid it. The sweep now matches any loaded sink attribute.

**A2-04 details:**
- `AppState.backend_pool` holds one backend build per worker for each distinct set of config-sourced inputs (URLs, slots, chat-completions roles, the `FLEET_LAYER` and `NATIVE_BATCH_SHARED_ROLES` env vars, and the identity of registry/admission/health_tracker).
- Request-supplied URLs never use the pool.
- The pool is wired into `/chat`'s `_init_primitives`, `/v1`, voice and `/chat/stream`.
- Per the verifier's ordering rule, pooled `ConcurrencyAwareBackend` session maps are capped at 4096; above that the least recently seen half is dropped. The current full holder and sessions with a migration in flight are kept.

**A2-13 details:**
- The code that ran after lock acquisition moved unchanged into `_record_placement`, which is now called inside the try. Release (`_release` plus lock exit) happens in the same finally.
- The native-batch lease uses a `with` statement.
- I used try/finally plus this extraction rather than an `ExitStack`: release is just as deterministic and the diff is much smaller.

## Tests run
Command for every run: `cd /workspace/wt/o1 && CI=true ORCHESTRATOR_MOCK_MODE=1 /workspace/repos/epyc-orchestrator/.venv/bin/python -m pytest -q -p no:cacheprovider -o addopts="" -n 2 <files>`

| Run | Result |
|---|---|
| A1-01, 31 files (goldens, chat routes, `/v1`, integration) | 940 passed, 5 skipped |
| Control-token, kpf21_25_trunk, parallel_step_executor and related | 111 passed |
| A4-M1, 22 files | 631 passed. The 2 `test_control_token_assemblers` failures came from my own `4dfc0b89`; fixed in `e0983c60` (29 passed on rerun) |
| A2-04, 29 files | 545 passed |
| A2-13, 24 dispatch/migration files | 458 passed |
| A1-17, 14 files | 468 passed, 5 skipped |
| Final combined run, 32 files across all commits | 875 passed |

Each new test was confirmed failing with the src changes stashed, then passing with them. I found no pre-existing failures, so the baseline list was not needed. `ruff check` passes on every changed `.py` file.

## For the integrator
- **Files outside the package area:**
  - `src/parallel_step_executor.py`: the wider CT-12.3c sweep found a real security gap there. Earlier step outputs were fed into the next prompt without control-token neutralisation; they are now neutralised. The prompt bytes only change when control tokens are present.
  - `tests/unit/test_control_token_assemblers.py`: the sweep change plus 3 new `ACCOUNTED_ELSEWHERE` entries.
  - `orchestration/repl_memory/retriever.py`: `route_with_skills` now returns a 4-tuple. Its only production caller is `select_initial_route`, and I found no callers in the research repo.
- No `SOURCE_PINS` files, frozen trees or evaluator-fingerprinted files were touched.
- **A1-01 parts not done:**
  - `_init_primitives` stays on the event loop on purpose. `begin_request()` binds the request scope in the caller's context, and the shared instance is cached; the pool now makes the request-URL path cheap too.
  - `_plan_review_gate` and the legacy `/chat/stream` `generate()`/`stream_adapter` calls are still inline. The verifier says `/chat/stream` has no live client.
  - The AST-scanner gate and ruff `ASYNC` in `make gates` are not added; that needs the remaining ~60 blocking sites fixed first.
- **A2-04 follow-ups:**
  - There is no `close_all()` shutdown hook (the pool lives for the worker's lifetime).
  - `LlamaTokenizer` is still created per request.
  - `CachingBackend.cache_stats` is not locked, as was already the case on the shared `/chat` instance.
- A2-12 has only the minimal session-map cap; no package owns the rest of it.
- At the start, the worktree held uncommitted partial work: A1-01 staged, A4-M1/A2-04/A2-12 unstaged, plus two untracked tests. I reviewed it, changed it as above and committed it. The original diff is saved at `/tmp/claude-0/-home-user/2773a866-6e4b-53fa-9304-d5960d8e1337/scratchpad/O1/unstaged.patch`. The tree is clean, with no scratch tests or stashes left.