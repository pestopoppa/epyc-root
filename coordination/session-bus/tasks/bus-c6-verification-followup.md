# Task: fix the C6 submission-verification false negative

> **RESOLVED 2026-07-28 — commit `8033f039`.** The cursor-anchored predicate (this task's
> deliverable, by `codex-bus-tests`) plus two fail-opens it introduced, found and fixed by
> `claude-gpu-lane` on independent review: post-Enter *absence* of the message was read as
> submission (an Enter eaten by a completion overlay rewrites or extends the text and looks
> identical to a success — success now requires the transcript echo, and `@ / ! #` triggers are
> refused up front), and a whitespace-only fragment normalised to `""` so `endswith("")` matched
> every pane. 21 → 29 tests. Full record: `handoffs/active/session-bus-thin-dispatcher.md` → M5 → C6.
> **Kept, not archived**, because the two-attempt failure history above is why the third attempt
> got a mandatory independent review — and C9 in the same module is queued for the same treatment.

**Assigned to** `codex-bus-tests`. You fixed C6 in `e6c8abcf`; this is the follow-up its live use
exposed. Written to be self-contained, because you are picking this up on a cleared context.

## Background you need

`scripts/coordination/tmux_adapter.py nudge` originally sent the message and `Enter` in one
`send-keys` call. The `Enter` was absorbed, the text sat unsubmitted in the pane, and the adapter
printed success and exited 0 — a fail-open. That was **C6**, and your fix made it fail closed:
separate text and Enter sends, 0.25s settle/capture, no success ledger unless prompt-tail
verification clears, plus a conservative 240-char refusal (a ~1018-char message was observed
mangling into a paste blob).

**That fix is correct in the direction that matters and must not be regressed.** Failing closed
is right. The problem is the predicate.

## The defect

Verification now produces **false negatives**: it reports

    nudge submission not confirmed before Enter: prompt tail lacks pending text or shows paste blob

and aborts *before* sending Enter — while the text has in fact landed correctly in the pane. The
nudge then requires a manual `tmux send-keys -t <target> Enter` to complete, so the adapter
cannot currently finish a nudge unassisted.

**Observed twice, and the cause is characterised — do not treat it as flaky.** Both failures
happened when a TUI overlay occupied the input area rather than a bare prompt:

1. a Codex **`Create a plan?  shift + tab use Plan mode   esc dismiss`** prompt;
2. a Claude **background-agent selector list** (`● main` / `◯ general-purpose …`).

The predicate appears to recognise only a bare prompt tail, so any overlay that shifts or
decorates the input line defeats it, and the adapter concludes "not submitted" when it was.

## Required

- Make submission verification **overlay-tolerant**: it must confirm the message text is present
  in the pane's input region even when an overlay (plan prompt, agent picker, paste blob banner)
  is also rendered.
- **Keep failing closed.** If the text genuinely is not there, still refuse and exit non-zero.
  Never re-introduce an unconditional success ledger. A false *negative* is an annoyance; a false
  *positive* is the original defect.
- Distinguish the states in the message so the next reader is not guessing: *text absent* vs
  *text present but unsubmitted* vs *paste-blob mangled* are three different situations and only
  the first should read as "did not land".
- Revisit the 240-char cap **only if** your calibration justifies it. It is deliberately ~4×
  below the observed ~1018-char failure. If you raise it, state the calibration; if you cannot
  calibrate safely, leave it and say so. Do not raise it on intuition.
- Tests covering both overlay shapes above, plus the genuine-failure path.

## Testing constraints — read before touching tmux

- Test against a **throwaway tmux session you create and kill yourself**. **Never** send keys to
  any window in the live `agent` session: it currently hosts `codex-inference` (deadline-bearing
  E8 under a q3 region claim), `claude_A`, `coordinator-agent`, `claude-gpu-lane`, and your own
  window. A stray keystroke into the wrong pane is precisely the failure this module exists to
  prevent, and one of those panes is holding operator-typed input.
- You can reproduce both overlay shapes cheaply without a real TUI — a script that prints a
  decorated input line and waits is enough to exercise the predicate. Be explicit in the test
  about what it models and what it does not.

## General constraints (still binding)

- Temporary bus roots (`tmp_path`) only; never touch live `coordination/session-bus/` files.
- **Never** start, stop, signal or `pkill` the coordinator-daemon. It is LIVE on a 45s tick
  running code you own — keep every file import-safe and syntactically valid at all times.
- No cpu or gpu lane, no inference, no benchmarks. **Do not take a region claim**: q3 is held by
  `bench-e8-quality` (`e8-v5-r2-cadencefix-20260728T160917Z`) and that work is deadline-bearing.
- Interpreter: `/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python`.
- **Explicit paths only; stage and commit in ONE step.** A parallel session swept a staged set
  into an unrelated commit earlier today.
- Do not push. Report the SHA to `coordinator-agent`.
- Not yours, do not "fix": `tests/compliance/` collection error, `test_e8_quality_*`,
  `tests/validate/test_repo_readiness_scorer.py`, `tests/hermes/*` (that last one is a real bug —
  `scripts/hermes/reference_openai_client.py:77` reads a missing `args.max_tokens` — but it
  belongs to someone else).

## Bus protocol

    ./scripts/coordination/session_bus.py append --agent codex-bus-tests \
      --target heartbeat --json '{"state":"working","task_id":"bus-c6-verification-followup"}'

Drain and refresh your heartbeat at every task boundary; retire `task_id` at terminal state.
Write only your own outbox. Report findings to `coordinator-agent`. If you discover further
defects, file them as `kind: finding` rather than expanding scope.
