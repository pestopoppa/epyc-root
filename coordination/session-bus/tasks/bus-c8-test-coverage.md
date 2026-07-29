# Task: test coverage for the C8 fix (durable boundary surfacing + endpoint lint)

**Assigned to** `codex-bus-tests`. Same domain as your existing work — keep your context.

## Why

C8 was fixed by coordinator-agent in `7806b6a8`, but it shipped with **only a hand-run script**
as evidence, not tests. That is exactly the gap that let C1–C4 hide: code that works when
someone watches it, with nothing to keep it working. You own the bus suite; close it.

One bug already escaped this way and was caught in live use, not by a test: the notice emitted
`task_id: null` when an agent had retired its task, which the msg schema rejects (typed string).
It wrote an invalid row into the coordinator's own inbox. **Make sure a test would now catch it.**

## What to cover

### `detect_task_boundaries()` in `scripts/coordination/session_bus_coordinator.py`
1. **No first-sight replay** — an agent seen for the first time produces no notice, whatever its
   state. (Otherwise a daemon restart floods the coordinator.)
2. **Churn is not a boundary** — `working|t1 -> working|t1` and `working|t1 -> working|t2`
   produce nothing. Only a transition **into idle** does.
3. **Fires exactly once on idle**, delivering a `status` message with
   `payload.event == "task-boundary"` to `coordinator-agent`'s inbox, carrying the transition.
4. **Idempotent** — re-running the tick with unchanged state delivers nothing further.
5. **Survives a daemon restart** — `boundary_state.json` persists, and a fresh call after
   reloading state replays nothing.
6. **Schema validity** — every delivered row passes `validate_row(..., "msg")`. Assert
   specifically that `task_id` is **omitted** (not null) when the agent retired it. This is the
   escaped bug; a passing test here is the point of the task.
7. **Coordinator self-exclusion** — an idle `coordinator-agent` role produces no notice about
   itself.

### The endpoint lint in `cmd_validate` (`scripts/coordination/session_bus.py`)
8. A roster row with a **non-tmux endpoint** produces a WARN naming the agent and its unread
   count; a `tmux:` endpoint produces none.
9. The lint **never fails closed on itself** — a malformed/absent `config.yaml` degrades to a
   warning, not an exception. (It is wrapped for that reason; prove the wrapper.)
10. `boundary_state.json` resolves to the coordinator-daemon in `required_writer` — an agent
    cannot write it.

## Constraints (unchanged, still binding)

- **`tmp_path` bus roots only.** Never touch the live `coordination/session-bus/` files — the
  daemon and three mains are reading them right now.
- **Never** start, stop, signal or `pkill` the coordinator-daemon. It is LIVE on a 45s tick at
  epoch 7 running this exact code; call `detect_task_boundaries(...)` directly against your temp
  root instead. Keep every file import-safe and syntactically valid at all times.
- No cpu or gpu lane, no inference, **no region claim** — q3 is held by deadline-bearing E8.
- Interpreter: `/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python`.
- **Explicit paths only; stage and commit in ONE step.** Do not push. Report the SHA.
- Not yours: `tests/compliance/` collection error, `test_e8_quality_*`,
  `tests/validate/test_repo_readiness_scorer.py`, `tests/hermes/*`.

## If you find the fix is wrong

Say so. Coordinator-agent wrote it under time pressure and has already found one bug in it. A
test that documents a real defect should be written and marked `xfail` with the reason, not
adjusted until it passes. File findings to `coordinator-agent`.

## When done

Report the SHA and **say explicitly that you are ready for more work** — do not sit idle. If
nothing has arrived by the time you finish, say so in your outbox rather than going quiet: an
idle main with an empty queue is a coordination failure, and the coordinator needs to see it.
