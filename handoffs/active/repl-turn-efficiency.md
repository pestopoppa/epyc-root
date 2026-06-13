# REPL Turn Efficiency - Active Gates

**Status**: COMPACTED 2026-05-28 - core REPL efficiency changes landed; active gates are S4 Omega A/B and ColGREP soak/daemon decisions.
**Created**: 2026-04-09
**Updated**: 2026-06-13
**Priority**: MEDIUM
**Categories**: agent_architecture
**Depends on**: None
**Parent index**: [research-evaluation-index.md](research-evaluation-index.md)
**Completed ledger**: [repl-turn-efficiency-completed-through-2026-05-28.md](../completed/repl-turn-efficiency-completed-through-2026-05-28.md)

## Executor Start Here

Do not add new REPL tools before S4. The current risk is whether the shipped efficiency features reduce turns and token cost without accuracy loss. Treat the historical frecency, combined operation, dspy.RLM, and ColGREP implementation details as completed unless a regression is found.

## Outstanding Tasks

- [ ] **S4 Omega A/B**: measure turns per task, token cost per task, and accuracy delta. This gates suggestion, verbosity, and any extra tool-surface changes.
- [ ] **ColGREP post-telemetry soak check**: rerun on a representative seeding or REPL window and inspect `_code_search_telemetry`, `_exploration_log`, and logs for fallback events, quality complaints, and p50/p95 `code_search()` latency.
- [ ] **Cold-start daemon decision**: build only if the daemon criteria below fire; otherwise subprocess-per-query remains the operational default.
- [ ] **Version/index hygiene**: pin a versioned ColGREP binary path and decide whether incremental re-index-on-commit is worth the complexity.

## Cold-Start Daemon Gate

Do not implement a daemon unless at least one of these conditions is met during a representative seeding or REPL run:

- p50 `code_search()` latency is at least 600 ms across a full run.
- At least 20% of REPL turns issue two or more `code_search()` calls.
- One role issues at least one `code_search()` call per second for at least 30 seconds.

## Current Telemetry State

2026-06-13 audit: historical logs were not sufficient to answer the daemon gate. `/mnt/raid0/llm/tmp/repl_tap.log` had no durable `code_search()` latency/fallback records, and the existing ColGREP path only wrote successful calls to the in-memory exploration log without latency. The code path is now instrumented in `epyc-orchestrator` (pending commit in this session): each ColGREP call appends `artifacts["_code_search_telemetry"]`, success responses include `latency_ms`, success exploration-log args include `engine=colgrep`, `latency_ms`, and `fallback=false`, and fallback paths log `fallback_reason` (`missing_binary`, `timeout`, `oserror`, `nonzero_exit`, `bad_json`) plus elapsed time. Do not make the daemon decision from pre-2026-06-13 data; use the next clean representative run.

## Dependency Forks

| Outcome | Next action |
|---|---|
| Omega shows fewer turns and neutral/better accuracy | Keep the feature path and consider the next narrow suggestion/verbosity change. |
| Omega shows token savings but accuracy loss | Revert or gate the risky surface; keep only independently useful telemetry. |
| ColGREP soak is clean and latency acceptable | Leave subprocess-per-query in place; focus on version pinning and index hygiene. |
| ColGREP latency or call frequency trips daemon gate | Design the smallest daemon interface and add rollback controls before implementation. |

## Completed Scope

| Scope | Result | Ledger |
|---|---|---|
| S1 frecency | Landed. | [completed ledger](../completed/repl-turn-efficiency-completed-through-2026-05-28.md) |
| S2 combined operations | Landed. | [completed ledger](../completed/repl-turn-efficiency-completed-through-2026-05-28.md) |
| S3 contextual suggestions | Prototype landed, default-off, still Omega-gated. | [completed ledger](../completed/repl-turn-efficiency-completed-through-2026-05-28.md) |
| S5 dspy.RLM gaps | `_batch_llm_query()`, `workspace_scan()` frecency fallback, and `STUCK("reason")` landed through NIB2 tasks on 2026-04-17. | [completed ledger](../completed/repl-turn-efficiency-completed-through-2026-05-28.md) |
| S6 specialist bug fixes | Landed. | [completed ledger](../completed/repl-turn-efficiency-completed-through-2026-05-28.md) |
| S7 ColGREP default-on | Landed with rollback via `REPL_COLGREP=0`. | [completed ledger](../completed/repl-turn-efficiency-completed-through-2026-05-28.md) |

## Key Files

- `/mnt/raid0/llm/epyc-orchestrator/src/repl_environment/`
- `/mnt/raid0/llm/epyc-orchestrator/src/repl_environment/file_exploration.py`
- `/mnt/raid0/llm/epyc-orchestrator/src/repl_environment/code_search.py`
- `/mnt/raid0/llm/epyc-orchestrator/src/repl_environment/combined_ops.py`
- `/mnt/raid0/llm/epyc-orchestrator/src/repl_environment/context.py`
- [tool-output-compression.md](tool-output-compression.md)
- [meta-harness-optimization.md](meta-harness-optimization.md)
- [routing-and-optimization-index.md](routing-and-optimization-index.md)
- [research-evaluation-index.md](research-evaluation-index.md)
- [autopilot-continuous-optimization.md](autopilot-continuous-optimization.md)

## Reporting Instructions

After S4 or soak work, update this handoff with the exact run, sample size, turns/task, token cost/task, accuracy delta, latency percentiles, and rollback decision. Update [research-evaluation-index.md](research-evaluation-index.md) and [master-handoff-index.md](master-handoff-index.md) if priority or scope changes.
