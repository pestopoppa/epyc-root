# Task: repair the `stage_b_prune_plan.json` provenance contradiction

**Assigned to** `codex-bus-tests` (reassigned 2026-07-28T16:2xZ).

> **Reassignment note.** This was first routed to `claude-main` at 16:21Z. It was *delivered*
> but never *dispatched*: `claude-main` is rostered `endpoint: monitor:file, drain: push`, nothing
> pushes to that endpoint, it was idle so it never hit a draining boundary, and `tmux_adapter`
> refuses to nudge a non-tmux endpoint. The row sat `unread=1` (defect **C8**). Its pane also held
> operator-typed text and a live background agent, so typing into it directly would have corrupted
> the operator's own in-flight input. Reassigned on operator direction.
>
> **Substitution the operator should know about:** the original instruction was to dispatch this to
> a **subagent on Opus at medium effort**. `codex-bus-tests` is a Codex session and cannot spawn an
> Opus subagent — its delegation targets are `gpt-5.6-terra` / `gpt-5.6-luna`. So either do it
> directly (the task is small and crisply bounded) or delegate to the smallest capable `gpt-5.6`
> agent. **Do not silently pretend the Opus requirement was met.**


**From** coordinator-agent, on operator direction, 2026-07-28.
**Origin**: codex finding `e5-stage-b-plan-integrity`, 2026-07-28T15:28Z, severity medium.
Codex explicitly handed this to Claude ownership: *"Claude owns non-inference infrastructure;
please repair/terminalize without changing the frozen manifests or run selection."*

## How to execute it: main thread, directly

**Operator instruction (revised 2026-07-28): do this on the main thread — do NOT delegate it.**
The earlier "dispatch to an Opus subagent at medium effort" instruction was written for a
Claude-owned session and no longer applies: your wrap-up is complete and you have nothing else
queued, so the delegation rationale (keep the main thread free) is gone.

Do not widen scope while you are in here. If the work appears to require changing run selection
or the frozen manifests, that is a **refusal** — stop and report to `coordinator-agent` rather
than deciding it yourself.

## The defect

`stage_b_prune_plan.json`, committed in **research `efd0980c`**, carries a stale limitation
claiming the `offline_scores` producer is **absent** and that there is **no correctness gate** —
while **the same commit** adds 2,967 offline score rows and regenerated rules.

The execution selection itself is **explicit and sound**. What is wrong is the durable
provenance text: it contradicts the artifact it ships with. Left alone, anyone reading the plan
later — including the post-reboot session that will run E5 W1–W4 off it — is told the scoring
basis does not exist when it does.

Plan file: `data/batched_decode/e5_pre_reboot_20260728/stage_b_prune_plan.json`,
SHA-256 `06b0abb2ca7abaf004ce56658a8c3753ea719ebdc4f1b50bec65a015954d4f8b` (per
`handoffs/active/batched-decode-measurement.md:517`). Confirm the hash before and after; if
your repair changes it, say so explicitly and update the handoff line that pins it — a silently
stale pinned hash is a worse defect than the one being fixed.

## Hard constraints

- **Do NOT change the frozen manifests.** They are unchanged by design.
- **Do NOT change run selection.** The prune decisions stand: W1 prunes only throughput-only
  `qwen36_q8_0-C1b-{np4,np8,np16}`; W2 retains its full C1/C3 family; W3 retains its full grid;
  W4 retains its full grid with high-K `raw_fallback` rows demoted from decision-grade use.
- **Append, never rewrite history.** Per `MEASUREMENT.md`, historical records are never edited to
  "fix" them — they are appended to. If the limitation text is part of a durable provenance
  record, correct it by superseding with a dated note that says what was believed, what is
  actually true, and why — not by deleting the wrong sentence.
- W2 remains **invalid for quality/garbage interpretation** regardless of this repair: the
  original Gemma capture stored reasoning text with no answer channel, and the historic `430/430`
  parse failures have **no raw SSE ledger and are unrecoverable**. Do not let a provenance fix
  imply otherwise.
- Explicit paths only on commit; **never `git add -A` or `git add .`**, and stage + commit in ONE
  step — a parallel session swept a staged set into an unrelated commit today (`7020d1f5`).

## Why it matters now

The operator has scheduled a host reboot. E5 W1–W4 moves to a **post-reboot session** that will
read this plan as its authority. Getting the provenance honest before that handover is the point
of doing it now rather than later.

## Definition of done

- The contradiction resolved in the durable text, with the correct state of the `offline_scores`
  producer and correctness gate recorded.
- Frozen manifests and run selection demonstrably untouched.
- The pinned SHA-256 in `batched-decode-measurement.md:517` either still matches or is updated in
  the same commit.
- Report to `coordinator-agent` via your outbox with the SHA. Do not tick another owner's
  checkboxes; flip only what you own, with `✅ 2026-07-28` inline.

## Note on your heartbeat

Your heartbeat currently reads `state: idle, task_id: null` (16:00:14Z) while your pane is
actively working with a background agent running. That is the stale-heartbeat failure mode — the
stall ladder reads it as idle and will not nudge you, and idle accounting counts you as free.
Refresh it at every task boundary and retire `task_id` only at terminal state.
