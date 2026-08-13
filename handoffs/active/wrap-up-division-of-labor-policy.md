# Wrap-up division of labor — durable policy (plan)

**Status**: ACTIVE — planning stub; the decided policy below is to be encoded into the standing
agent files. Opened 2026-08-13 by operator directive.
**Created**: 2026-08-13
**Priority**: P1 — wrap-up is the write-path into the batch-inference index, and it is currently
performed inconsistently (or not at all), which is how compute-gated blockers go invisible.
**Owner**: `coordinator-agent` (process owner; relays wrap-up triggers). **Reviewer**: `auditor`.
**Parent index**: `master-handoff-index.md` (session-lifecycle / coordination domain).

## The decided policy (operator, 2026-08-13 — encode, do not re-open)

Three wrap-up owners, three distinct scopes:

1. **Worker mains** (`mainA`–`mainD`) — do the work; at the **absolute end of a task boundary**
   (task completed, **or** a blocker that cannot be promptly moved), they: commit changes, write
   the progress log, and flip their own handoff checkboxes, then **hand the completed work to the
   auditor and stop**. No full wrap-up.
2. **Auditor** — reviews/audits the completed work, then performs the wrap-up: updates handoffs and
   indices (**including the batch-inference index** `handoffs/active/inference-batch-loop.md`) and
   the **wiki** (last step). The wrap-up mechanics are dispatched to subagents, leaving the
   auditor's main thread free to manage subagents and reasoning.
3. **Coordinator-agent** — a separate entity; wraps up *itself* (its own coordination surfaces).
   Also the operator's point of contact, so **fleet-wide wrap-up triggers flow through it**.

**Why wrap-up is load-bearing here:** the batch-inference index is the standing, decision-ready set
of compute-gated tasks. It is updated **at every wrap-up**. A worker main that wraps up mid-task
captures its blocker into the index for the next compute window; a main that idles (or skips
wrap-up) leaves the blocker invisible until rediscovered. The index is what makes a future graded
compute window (small-model-only / load-then-keep-hot / full-idle — **graded, not binary**) a
one-plan un-block moment rather than a scramble.

## Plan to make it durable

- [ ] Encode the three-tier division in `agents/commands/wrap-up.md` (the routine's owner/scope
      section — currently the "narrow standing exception" for the auditor; expand to the full model).
- [ ] Encode the auditor's wrap-up duty in `agents/auditor-main.md` — review + wrap-up via
      subagents, updating handoffs + indices + wiki (note: this file is on `lane/auditor`, unmerged).
- [ ] Encode the worker-main half in `coordination/session-bus/tasks/MAIN-GOALS.md` +
      `STANDING-MAIN-RULES.md` — commit + progress + checkbox, then hand to auditor, stop.
- [ ] Encode the boundary rule in `agents/shared/SESSION_LIFECYCLE.md` — wrap-up fires at task end
      or a prompt-movable blocker (**trust-boundary file: needs operator merge sign-off**).
- [ ] Reconcile the superseded rule — `coordination/session-bus/tasks/post-reboot-session.md` §6
      still says *"each main writes its OWN wrap-up"*; mark it superseded by this policy.
- [ ] Confirm the batch-inference index update is an explicit wrap-up step (not implied) — a
      wrap-up that does not land new blockers into `inference-batch-loop.md` is incomplete.
- [ ] Wire the coordinator dispatch flow: completed-work packets route to the auditor for
      review+wrap-up; wrap-up triggers relay through the coordinator.

## Dependencies / blockers

- `agents/auditor-main.md`, `agents/shared/SESSION_LIFECYCLE.md` changes interact with the unmerged
  `d7b83ddf` role-definition work on `lane/auditor` and the human-only trust-boundary list — the
  shared-policy files (`agents/shared/*.md`) cannot be merged without operator sign-off.

## Next action

Encode item 1 (`wrap-up.md`) and item 2 (`auditor-main.md`) first — they carry the division of
labor; the trust-boundary item (4) is queued behind operator merge approval.
