# Follow-up: commit the suite, then fix the two defects it documents

Continuation of [`bus-test-coverage.md`](bus-test-coverage.md). Same constraints, restated at the
bottom because they still bind.

## Step 1 — commit your test suite (do this first, before any fix)

Commit `tests/test_session_bus.py` **alone**, by explicit path:

    scripts/coordination/merge_gate.py check
    git add tests/test_session_bus.py
    git commit

- **Never** `git add -A`, `git add .`, or any wholesale add. Other sessions have in-flight edits
  in this shared tree; a wholesale add commits their work under your message.
- **Do not push.** Report the SHA to `coordinator-agent` via your outbox.
- The suite is verified as-is: 14 passed, 2 xfailed, and the full suite shows no new failures
  (9 failed / 266 passed / 2 xfailed, against a 9 failed / 252 passed baseline — the delta is
  exactly your 14 passes and 2 xfails). Commit it in that state.

## Step 2 — fix the two defects your xfails document

Fix each, then flip its `xfail` to a passing test. Do not weaken a test to make it pass.

### (a) C4 — BUS_PROTOCOL rule 3 ack redelivery is entirely unimplemented

`requires_ack` appears exactly once in `scripts/coordination/session_bus_coordinator.py`
(~line 1260), and only as a field being **set** on an outgoing message. Nothing anywhere scans
delivered inbox messages whose `ack_deadline_s` has lapsed without a matching `ack` and
redelivers them.

Rule 3: *"`requires_ack` messages are redelivered as a `nudge` (same `corr_id`) after
`ack_deadline_s`; consumers dedupe by msg `id`."*

- The redelivered message is a `nudge` carrying the **same `corr_id`** as the original.
- Consumers dedupe by msg `id`, so each redelivery needs its own `id` while the `corr_id` ties
  them together.
- Redelivery must be safe to repeat every tick without unbounded growth — decide and test the
  bound (e.g. one outstanding nudge per unacked `corr_id`), and state the rule you chose.
- An `ack` is matched from the recipient's **outbox**; that is the only place an agent may write.

### (b) Rule 4 — `cursor --set` permits rewind

`cmd_cursor` in `scripts/coordination/session_bus.py` writes any offset with no monotonicity
check. Rule 4: *"Each consumer owns `cursors/<self>.json` (byte offsets); never rewind another's
cursor."* A cursor only advances.

- `--set` to a **lower** offset must refuse with a clear message and a non-zero exit.
- `--set` to an equal or higher offset stays allowed.
- Note this gap was used in anger earlier today (`cursor --set 0` to re-read an inbox), so if you
  believe a deliberate rewind has a legitimate operator use, do not silently keep it — implement
  the refusal and say in your report what an explicit override would need to look like. Do not
  add the override yourself.

## Constraints (unchanged, still binding)

- Temporary bus roots (`tmp_path`) only. **Never** touch the live `coordination/session-bus/`
  files — a daemon and two working mains read them concurrently.
- **Never** start, stop, signal or `pkill` the coordinator-daemon.
- **The daemon is LIVE right now**, running your modified `session_bus_coordinator.py` on a 45s
  tick. Keep the file import-safe and syntactically valid at every moment — a broken save takes
  the running daemon down on its next tick.
- No cpu or gpu lane, no inference, no benchmarks. Another codex main is running G3/E8 on this
  host.
- Interpreter: `/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python`.
- Pre-existing failures you must not "fix": `tests/compliance/` collection error,
  `test_e8_quality_*`, `tests/validate/test_repo_readiness_scorer.py`.

## Reporting

Report to `coordinator-agent` via your outbox after step 1 (with the SHA) and again after each
defect is fixed and its xfail flipped. Refresh your heartbeat and drain at every boundary. If a
fix turns out to be larger than it looks, say so rather than half-landing it — a partial fix to
the live daemon's code path is worse than a documented xfail.
