# Task: fix C6 (nudge reports success without submitting) and C7 (non-roster bus files)

**Assigned to** `codex-bus-tests`. Continuation of [`bus-test-coverage.md`](bus-test-coverage.md)
and [`bus-test-coverage-followup.md`](bus-test-coverage-followup.md). All prior constraints still
bind — they are restated at the bottom.

Both defects were found in live operation on 2026-07-28. Neither is theoretical.

---

## C6 — `tmux_adapter.py nudge` reports success when the message was never submitted

**Severity: high.** `OP-SENDKEYS-CODEX` was granted specifically so the daemon could nudge a
main. If nudges silently do not land, the entire stall ladder is decorative and its evidence is
worthless.

`scripts/coordination/tmux_adapter.py:285` sends the message and `Enter` in ONE call:

    rc, out = _tmux("send-keys", "-t", p["target"], args.message, "Enter")

Against the codex TUI the `Enter` is absorbed — the text lands in the input buffer and sits
there. The adapter prints `nudged <agent> at <target>` and exits 0 regardless, so a nudge that
did nothing is indistinguishable from one that worked. This is the same fail-open shape as C3.

**Observed twice today.** A short message needed a separate `tmux send-keys -t <target> Enter` to
submit. A ~1000-char message was worse: the TUI turned it into a `[Pasted Content 1018 chars]`
blob with overflow text and the content was mangled — so **length matters**, and a fix that only
handles short messages is not a fix.

### Required
- Send the message, then `Enter` as a **separate** `send-keys` call, with a settle delay between.
- **Verify submission** rather than assuming it: re-capture the pane and confirm the prompt no
  longer holds the pending text. Report failure and exit non-zero if it still does.
- Handle the long-message case. If a length threshold exists past which the TUI pastes rather
  than types, either chunk below it or detect the paste-blob state and fail loudly. Decide,
  implement, and **state the rule you chose and how you determined the threshold** — do not guess
  a number silently.
- Keep `probe` honest: if submission verification can fail, `probe` should say so is possible.

### Testing C6 safely
- Test against a **throwaway tmux session you create and kill yourself**, never `agent`. The live
  session hosts four working agents; a stray keystroke into the wrong pane is the exact failure
  this module exists to prevent. Config `tmux.allow_session_creation: false` governs the
  *adapter*; your test may create its own session — that is what "throwaway sessions are a
  testing device only" means.
- Never send keys to any window in the `agent` session.
- A shell prompt (`cat` or `sh -c 'read x; echo GOT:$x'`) is a fine stand-in for a TUI for the
  submit-verification path; be explicit in the test about what it does and does not model.

---

## C7 — heartbeats and outboxes named after TASKS, not writers

**Severity: medium, but it contaminates M4 acceptance evidence.**

`coordination/session-bus/heartbeats/` currently holds 22 files whose names are task ids, not
roster ids (`e8_partial_r2_recovery`, `episodic_reseed_terminal`, `g3_context_defect_fix`, …),
and it has now spread to outboxes: `outbox/e8_launch_sequence_review.jsonl`,
`outbox/e8_r2_execute_test_and_fix.jsonl`.

BUS_PROTOCOL rule 1 defines `heartbeats/<w>` as owned by **writer** `<w>`. A per-task heartbeat
has no writer, so single-writer ownership is undefined for these files and the ownership lint
cannot evaluate them. Worse, they inflate the agent roster the daemon and `rebuild` derive:
`session_bus.py rebuild` already lists `refresh_gpu_queue_integration` and
`validate_reseed_integration` as though they were agents. Stall-ladder and idle accounting
therefore run over **phantom agents that can never respond to a nudge** — which directly
contaminates M4's zero-idle acceptance evidence.

Task identity belongs in the `task_id` **field**, which the schema already carries.

### Required
- **Fail closed at write time.** `session_bus.py append --target heartbeat|outbox` must refuse an
  `--agent` that is not a roster id in `config.yaml`, with a clear message pointing at the
  roster. This is the fix that stops recurrence.
- **Ignore, don't adopt.** The daemon and `rebuild` must derive agents from the **roster**, not
  from whatever files happen to exist in `heartbeats/`. A non-roster file must never be treated
  as an agent for stall-ladder, idle accounting, or advice.
- **Surface, don't delete.** Report existing non-roster files (a `validate` warning naming them
  is ideal). **Do NOT delete or move them** — they are other sessions' files, and whether they
  are garbage or evidence is not yours or mine to decide. Disposition is an operator call; say in
  your report that it is pending.
- Tests for all three behaviours.

---

## Constraints (unchanged, still binding)

- Temporary bus roots (`tmp_path`) only. **Never** touch the live `coordination/session-bus/`
  files.
- **Never** start, stop, signal or `pkill` the coordinator-daemon.
- **The daemon is LIVE**, running your `session_bus_coordinator.py` on a 45s tick. Keep every
  file import-safe and syntactically valid at all times — a broken save takes it down next tick.
- No cpu or gpu lane, no inference, no benchmarks. Two other mains are working: codex on CPU
  E8/G3, claude-gpu-lane on the GPU shadow lane.
- Interpreter: `/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python`.
- **Commit by explicit path only** — never `git add -A` or `git add .`. Stage and commit in ONE
  step: staging then pausing lets a parallel session's commit sweep your files in. That happened
  today.
- Pre-existing failures you must not "fix": `tests/compliance/` collection error,
  `test_e8_quality_*`, `tests/validate/test_repo_readiness_scorer.py`, `tests/hermes/*`
  (the last is a real bug — `scripts/hermes/reference_openai_client.py:77` reads a missing
  `args.max_tokens` — but it is not yours).

## Reporting

Report to `coordinator-agent` after each defect lands, with the SHA. Do not push. Refresh your
heartbeat and drain at every boundary. If either fix turns out larger than it looks — C6's
long-message handling plausibly is — say so rather than half-landing it. A partial fix to the
live daemon's nudge path is worse than a documented defect.
