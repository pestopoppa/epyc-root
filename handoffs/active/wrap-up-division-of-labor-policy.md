# Wrap-up division of labor — durable policy (plan)

**Status**: ACTIVE — planning stub; the decided policy below is to be encoded into the standing
agent files. Opened 2026-08-13 by operator directive.
**Created**: 2026-08-13
**Priority**: P1 — wrap-up is the write-path into the batch-inference index, and it is currently
performed inconsistently (or not at all), which is how compute-gated blockers go invisible.
**Owner**: `coordinator-agent` (process owner; relays wrap-up triggers). **Reviewer**: `auditor`.
**Parent index**: `master-handoff-index.md` (session-lifecycle / coordination domain).

## The decided policy (operator, 2026-08-13 — encode, do not re-open)

Three owners, three distinct scopes. The key split is **log skill (lightweight, frequent)** vs
**wrap-up (heavy, operator-cadenced)**:

1. **Worker mains** (`mainA`–`mainD`) — do the work; at the **absolute end of a task boundary**
   (task completed, **or** a blocker that cannot be promptly moved), they run the **log skill**:
   `git commit` (pathspec, own files only) + append the progress log + flip their own handoff's
   checkboxes. **They stop there — no full wrap-up.**
2. **Auditor** — runs the **full wrap-up** (index pruning, handoff compaction, indices **including
   the batch-inference index** `handoffs/active/inference-batch-loop.md`, and the **wiki** as the
   last step) at its own cadence, dispatched to subagents. The worker mains' log skill is what makes
   newly-exposed blockers *visible* in the handoffs; the auditor's wrap-up is what *files* them.
3. **Coordinator-agent** — a separate entity; wraps up *itself* (its own coordination surfaces).
   Also the operator's point of contact, so **fleet-wide wrap-up triggers flow through it**.

**Why wrap-up is load-bearing here:** the batch-inference index is the standing, decision-ready set
of compute-gated tasks. It is updated **at every wrap-up**. A worker main that wraps up mid-task
captures its blocker into the index for the next compute window; a main that idles (or skips
wrap-up) leaves the blocker invisible until rediscovered. The index is what makes a future graded
compute window (small-model-only / load-then-keep-hot / full-idle — **graded, not binary**) a
one-plan un-block moment rather than a scramble — and that plan lands as a **focused, prioritized
dispatch on the bus** for the workers to take on, not as a planning document.

## The compute window — how the index is consumed

Compute is owned by `inference` and currently consumed by two operator-stoppable loops (autokernel +
autopilot). When a window opens, `inference` signals it **graded, not binary**:

- **small-model only** — GPU available but RAM-bandwidth-conserving (must not compete with CPU-side load);
- **load-then-keep-hot** — a load window, then extended weight residence (a long series of same-weight tasks);
- **full idle** — rare.

The coordinator matches **task grade to window grade** (a keep-hot window wants a long same-weight
series; a small-model window wants exactly that and nothing big), ranks the fire-ready set by
**unblock-leverage** (how many downstream handoffs each entry frees), and lands a **focused,
prioritized dispatch on the bus**.

**Inference-gated worker rule:** a main blocked on a compute grant either (a) negotiates the window
with `inference`, or (b) — when there is no non-compute alternative — **wraps up where it stands** and
moves to other tasks from the bus. Never idle on a grant that will not come. The churn phase exists to
surface and characterize as many blockers as possible so the next window is a plan, not a scramble.

## Plan to make it durable

- [ ] **Create the log skill** (`.claude/skills/` or `agents/commands/`) — one command: `git commit`
      (pathspec, own files only) + append the progress log + flip the handoff's own checkboxes. Reuse
      the wrap-up checklist-sync gate + commit hygiene; idempotent and safe mid-task.
- [ ] Adjust worker-main policy (`coordination/session-bus/tasks/MAIN-GOALS.md` +
      `STANDING-MAIN-RULES.md`) — run the log skill at every task boundary, replacing "wrap up".
- [ ] Encode the auditor's wrap-up duty in `agents/auditor-main.md` — the full wrap-up (indices
      incl. batch-inference index + wiki) at its own cadence, dispatched to subagents (file on
      `lane/auditor`, unmerged).
- [ ] Encode the boundary rule in `agents/shared/SESSION_LIFECYCLE.md` — the log skill fires at task
      end or a prompt-movable blocker (**trust-boundary file: needs operator merge sign-off**).
- [ ] Reconcile the superseded rule — `coordination/session-bus/tasks/post-reboot-session.md` §6
      still says *"each main writes its OWN wrap-up"*; mark it superseded (worker mains now log, not wrap up).
- [ ] Confirm the batch-inference index update is an explicit auditor wrap-up step (not implied) — a
      wrap-up that does not land new blockers into `inference-batch-loop.md` is incomplete.
- [ ] Wire the coordinator dispatch flow: wrap-up triggers relay through the coordinator.

## Dependencies / blockers

- `agents/auditor-main.md`, `agents/shared/SESSION_LIFECYCLE.md` changes interact with the unmerged
  `d7b83ddf` role-definition work on `lane/auditor` and the human-only trust-boundary list — the
  shared-policy files (`agents/shared/*.md`) cannot be merged without operator sign-off.

## Next action

1. **Create the log skill** — the one new artifact (commit + progress + box-check), reusing the
   wrap-up checklist-sync gate + pathspec commit hygiene.
2. Point the worker-main policy at it; then the auditor wrap-up, boundary rule, and superseded-rule
   reconciliations follow (the `SESSION_LIFECYCLE.md` item is queued behind operator merge sign-off).
