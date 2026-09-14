# Process-global mutable state read as if it were per-request

**Category**: `agent_architecture`
**Confidence**: verified (local code + unit tests, zero inference)
**Date**: 2026-09-14
**Source**: RTG-02, `epyc-orchestrator` `d65a4e93` and `b69bda61`; handoff
`handoffs/active/autopilot-continuous-optimization.md` (boxes at `:1787` and `:1793`)
**Folds into**: [Agent Architecture](../agent-architecture.md) — tool-telemetry capture; and
[Tool Implementation](../tool-implementation.md) for the registry contract

## The mechanism

One `ToolRegistry` is constructed per API process (`src/api/__init__.py` sets a single
`state.tool_registry`). It carries an `_invocation_log` that `invoke()` appends to. Four
request-scoped readers built *per-request* telemetry out of that log — the ReAct durable record
(`chat_pipeline/stages.py`), the specialist delegation phase (`chat_delegation.py`), and two
streaming tool-event emitters (`chat.py`, `stream_adapter.py`).

Nothing about the log is per-request. Under uvicorn concurrency it interleaves every in-flight
request's calls, so request A's durable episodic row recorded request B's tools, and A's SSE stream
emitted B's tool events. The log was also a plain `list` that nothing ever cleared, so it grew for
the lifetime of the process; `clear_invocation_log()` had zero callers in `src/`.

**The defect is not "the log was never cleared". It is that shared state was read as scoped state.**
Clearing it per request does not fix anything — it is the *same* defect with a narrower race window:

    request A finishes → A clears the log → B's tool call lands → A reads → A records B's call

A correct fix has to make the scope structural, not temporal.

## The shape of the fix, and why "clear it" is the wrong instinct

Per-request telemetry now comes from `REPLEnvironment._invoked_tools`, captured at the single
`_invoke_tool` chokepoint (`src/repl_environment/context.py`). One list per REPL, and one REPL per
request, which buys four properties no amount of clearing can:

- **Exactness** — the buffer *cannot* contain another request's call, so there is no window.
- **Lock-free** — no contended structure, no contextvar, no request-id stamp to filter on.
- **Cleanup on every path including exceptions** — the buffer is owned by the request's object graph,
  so it is released when the request is, whether it returned or raised. There is no `finally` to
  forget.
- **Boundedness for free** — a per-request buffer is bounded by the request, not by uptime.

The shared log survives as an explicitly labelled *diagnostic ring* (`deque(maxlen=1000)`, override
`ORCHESTRATOR_TOOL_INVOCATION_LOG_MAX`, `<= 0` disables). `clear_invocation_log()` is kept for tests
and interactive use, with a docstring that says it is not a per-request mechanism. Dead API is worse
than no API, but so is API whose only documented use is the wrong one.

A cursor into shared state is the same bug wearing a hat. Both streaming emitters kept
`prev_tool_count` and sliced `log[prev_tool_count:]` — correct only if nothing else appends, which is
exactly what does not hold. Bounding the ring would have broken it a second way: eviction shifts
indices, so the cursor silently reads the wrong entries.

**Guard**: an `ast` test asserts that no request-scoped module *calls* `get_invocation_log()`. Parsed
rather than grepped, so the comments explaining why it must not be called do not trip it. It flags
all four pre-fix sites.

## The paired half: a write path that computes a field and drops it

The same handoff box named a second defect with the same signature — available data discarded at the
boundary. `EpisodicStore.store()` was the only site that ever wrote `assigned_role` (TR-3.2) and the
`work` payload (M-11a2b). Every UPDATE branch in `QScorer` called `update_q_value()` and returned
*before* reaching it. Because the find-or-update branch fires ~11x more often than create
(`SUM(update_count)` 668,070 vs 59,337 rows), both columns were effectively never populated: the
values were read off entries already in hand, then dropped on the floor.

Two rules worth carrying:

1. **A find-or-update path must carry everything the create path writes**, or the field only exists
   on first observation. A test that exercises only create passes for the bug's entire lifetime — and
   here it did, because `Q_TD_WRITE` is read at import time and is `0` under pytest while production
   sets it to `1`. **A flag read at import time makes the production branch untestable by default.**
2. **Backfill MERGES, never overwrites.** `assigned_role` fills only when NULL; `work` sub-keys fill
   only where absent; all other `context` keys are preserved. A later observation may close a gap a
   first observation left, but must never blank out captured work.

## Non-idempotent sanitization makes a record lie about itself

The `work` box named a third hole, and it is the subtlest. The size/redaction policy is applied
**twice** on the live create path — once by `chat_pipeline.telemetry.work_completion_meta` heading
into the progress JSONL, then again by `build_memory_record` heading into `memories.context`. Its
docstring claimed idempotence; the code did not have it:

- An already-truncated string is `max_chars` **plus** its truncation marker long, so pass two
  re-truncated and appended a second marker. A 32,500-char answer was stored reporting
  `total was 32049`.
- An already-bounded list is `max_items` **plus** the `_elided_entries` sentinel, so pass two saw
  `max_items + 1`, dropped one entry — which, being at the front, was *the sentinel itself* — and
  inserted a fresh `_elided_entries: 1`. A row that elided 50 entries claimed 1, and lost the real
  first retained entry too.

**A bounding function that annotates its own output must be idempotent, or the annotation becomes the
first thing it destroys.** Both now recognise their own marker at their own cap and no-op; the
sentinel is lifted before counting and its count carried into the total. The general form: a function
whose output is in its own input domain is composed with itself sooner or later, usually by a caller
who cannot see the other one — so idempotence is a correctness property, not a nicety, and it needs a
test rather than a docstring.

## Checklist for a per-request field

- Is the state it reads owned by the request, or by the process?
- If per-request scoping is achieved by *clearing* something shared, name the window. There is one.
- Does the cleanup run when the request raises?
- Is it bounded by the request, or by process uptime?
- Does the UPDATE path write every field the CREATE path writes?
- Is the sanitizer idempotent, and is there a test that composes it with itself?
