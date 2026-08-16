# Session Lifecycle — wrap-up, clear, close

Canonical contract for any agent directing another long-running session (coordinator-agent
above all), and for your own session when a task ends. Extracted 2026-07-30 from
`agents/shared/OPERATING_CONSTRAINTS.md` § "Session Lifecycle: wrap-up, clear, close" (AFC-P6
restructure); coordinator-specific duties stay in `agents/coordinator-agent.md`.

**How to read this file (P1-4, 2026-08-16).** Every section is a CONTRACT; a rule keeps at most a
short `(origin: …)` pointer and the story lives in the *Appendix — incident origins* at the bottom.

## Two axioms (canonical statements — cite, don't restate)

- **An idle main with an empty queue is a coordination failure**, not a neutral resting state.
- **The handoff dashboard counts CHECKBOX STATE ONLY.** Prose status is invisible to it. Any
  edit recording completed work flips the matching `- [ ]` → `- [x]` (append `✅ YYYY-MM-DD`);
  work discovered mid-flight gets its own task line. Un-wrapped work is, from the operator's
  view, work that did not happen.

Four things the axiom does not say, and each one is load-bearing:

- **The date is appended for a machine, not for style.** The timeline generator prefers the
  in-file `✅ YYYY-MM-DD` over the commit date, so an unflipped or undated box also loses its
  position in time. Pre-reboot flips additionally carry an evidence ref (below).
- **You never tick ANOTHER agent's checkbox** (`agents/shared/INVARIANTS.md` invariant 9). Stating
  that someone else's box is stale is not ticking it and is always allowed — say it, do not flip
  it. "Never flip a checkbox" is a mis-scoping of this rule: you flip your OWN.
- **A handoff may forbid new task boxes.** Frozen and compatibility-pointer handoffs exist and
  explicitly refuse new checkboxes; check that status before filing a discovery into one, and file
  it in the owning live handoff instead.
- **Two states are not enough for a checkpoint.** A task boundary that is neither done nor
  abandoned is recorded by `scripts/coordination/worker_checkpoint.py` (`/log`): `completed` flips
  the exact box, `blocked` records a non-movable blocker, `partial` is allowed ONLY at a pre-reboot
  boundary. **Nonterminal outcomes leave the source task open and add a checkpoint-keyed child
  task** — they never flip the parent. Do not hand-reproduce that tool's mutation, commit, push,
  receipt, or bus-publication phases.

## Reading another session's liveness — three states, not two

A session is **working**, **compacting**, or **idle**, and the pane cannot tell you which. A
session COMPACTING its context renders **identically** to a finished one: the goal line, the
"Pursuing goal" timer and the background-terminal count all disappear together, leaving a bare
status line above an empty composer. Read that as "done" and you re-dispatch, wrap up, or
`/clear` a session that is mid-turn. **Never conclude idle from pane text alone — not from a
window list, not from a quiet-check, not from a `capture-pane`.**

- **The authoritative instrument is `scripts/coordination/tmux_adapter.py`'s runtime check**
  (`probe` is read-only and cheap). It reads the session's own rollout JSONL and reports ACTIVE
  when the last record is mid-turn (`token_count`, `reasoning`) rather than the turn-terminal
  `task_complete`/`turn_aborted` — precisely the signal a compacting pane hides. Its polarity is
  one-way by construction: it never manufactures an `idle`, and an unreadable runtime falls back
  to the weaker signals rather than clearing the session.
- **An adapter refusal citing runtime state is a finding about the world, not an obstacle to
  retry past.** It is the instrument reporting that the session is alive. Re-probe and let the
  timers clear it (ladder: `docs/guides/agent-workflows/coordinator-escalation.md`); routing
  around it discards the only reading that distinguishes compacting from idle.
- **Heartbeats lie, and it is the READER who pays.** Measured 2026-08-12 10:53Z: `mainB`'s
  heartbeat read `state: working, task_id: A3-gpu-baseline…` while **446 seconds stale**, with
  the pane idle across three consecutive watcher cycles and the GPU at 0%. Written once, a
  heartbeat is a birth certificate, not a liveness signal — which is why every main refreshes it
  at EVERY task boundary (`CLAUDE.md` § Agents & Automation). **A stale heartbeat is worse than no
  heartbeat**: the stall ladder reads it as a stall and nudges a perfectly healthy agent.
  (origin: INC-20260727-stale-heartbeat)
- **When heartbeat, pane and hardware disagree, the hardware reading wins** — provided the
  hardware reading itself persists across samples, because one sample landing between two
  short benches shows an idle card in a healthy sweep (`agents/shared/OPERATING_CONSTRAINTS.md` →
  *Observation Windows*, which owns the sampling discipline and its two-vs-named-count rule).

(origin: INC-20260812-compacting-read-as-idle; Appendix)

## At every task boundary, exactly one of

| Situation | Action |
|---|---|
| Next task is **related** to what just finished | Leverage the existing context — dispatch straight into it. Do NOT wrap up, do NOT clear. |
| Next task is **disjoint** | **Wrap up first, then `/clear`**, then dispatch. |
| **No further task** can be assigned | **Close the session.** Do not leave it idling. |

**`/clear` requires BOTH a completed wrap-up AND a disjoint follow-on task.** Context on a
related task is an asset — clearing it forces a rediscovery pass; clearing without a wrap-up
also loses the durable record. Judge disjointness against what the session just wrapped up, not
its whole history.

**Sequencing trap**: `/clear` wipes the pending instruction too. Never send "run /clear then do
X" as one nudge — send `/clear`, confirm it landed, then dispatch via a self-contained brief
file (origin: INC-20260728-cleared-context). **Recovery**: Codex prints `codex resume
<session-id>` on clear — resume rather than rediscover if context was cleared by mistake.

## Wrap-up cadence

**Binding: one task done = one wrap-up, AS YOU GO.** The operator's rule of 2026-08-11 governs and
was reaffirmed by ruling (a) of 2026-08-16 (`agents/shared/OPERATING_CONSTRAINTS.md` → *Doctrine
rulings — 2026-08-16*). This replaces the former "major checkpoints, not every task" cadence, which
is retired: a checkpoint that is never wrapped up did not happen from the operator's view, and the
dashboard sees checkbox state only (axiom above).

- **Runs at EVERY completed task**, autonomous and nightshift sessions included: progress report,
  checkbox sync, handoff updates, `Next action` cell refresh, agent log, pathspec commit, lane
  promotion.
- **Two BROAD, DESTRUCTIVE steps stay at the operator cadence** and run ONLY inside an
  operator-invoked `/wrap-up`: index **PRUNING** (deleting or archiving rows, handoff compaction)
  and the **wiki compilation sweep**. They are *deferred, not skipped* — report what you saw that
  they would have handled.
- **Nothing may auto-trigger the full routine.** There is no `Stop`, `SessionEnd` or `PreCompact`
  hook, no cron and no nightshift task that calls it, and there must not be one. A per-task wrap-up
  is invoked by the session doing the work.
- **A wrap-up may run via a subagent on a session's behalf** — preferred when the session is
  already dispatched into new work. That subagent may **PREPARE** index edits: draft row text, run
  `scripts/handoffs/index_state.py --check`, and report the exact diff. **The owning session
  APPLIES them and owns the commit.** Adding, deleting or re-pointing an index row is never a
  subagent's own write; the same holds for intake entries and handoff stubs. Widening this — a
  subagent writing an index directly — needs explicit operator approval. (ruling (b), 2026-08-16)
- Step-level split of what runs when: `agents/commands/wrap-up.md` → CADENCE.

Related standing direction (2026-07-28): actively source and track non-inference work that can
proceed regardless of a pending reboot or blocked inference lane.

### Auditor audit-pass checkpoint

Every completed audit pass is a wrap-up boundary in its own right, even when the auditor remains
available for the next packet. Persist the verdict, evidence, and handoff follow-ups before
accepting a disjoint audit. This does not authorize the auditor to contact the source main:
follow-ups return to the ordinary handoff/coordinator backlog path.

### Auditor audit-pass checkpoint

Every completed Auditor audit pass is a checkpoint even when the Auditor remains available for the
next packet. Persist the verdict, evidence, and handoff follow-ups via the standard wrap-up routine
before accepting a disjoint audit. This does not authorize the Auditor to contact the source main:
follow-ups return to the ordinary handoff/coordinator backlog path. The precise narrow exception to
the manual-trigger rule is maintained in `agents/commands/wrap-up.md`.

## Pre-reboot wrap-up is mandatory, not checkpoint-gated

Operator, 2026-07-29: ALL progress MUST be persisted and logged BEFORE a host reboot. Every
main — the coordinator included — completes a wrap-up first; whatever is not on disk and in the
handoffs/progress record did not happen. Sequencing: wrap up when the CURRENT task completes,
report ready-for-reboot, go idle-ready; the critical-path main wraps LAST and requests the
reboot; the coordinator confirms every other main wrapped before relaying — a reboot request
with an unwrapped main is a coordinator defect.

**A pre-reboot wrap-up includes**: (1) flip every completed checkbox with an evidence ref;
(2) file mid-flight discoveries as their own task lines; (3) commit AND PUSH — unpushed commits
are invisible to the post-reboot session; (4) state plainly what is INCOMPLETE — a handover,
not a summary; (5) anything you were going to tell the operator later, say now.

**Post-reboot spawning** (operator, 2026-07-29): the operator has coordinator-agent spawn the
mains, so every post-reboot main is coordinator-covered by construction (re-spawn under
EXISTING roster ids). A manually adopted pre-existing session is the documented exception, not
the pattern.

## Coordinator main thread stays free for coordination

A session whose job is coordinating other sessions must NOT spend its main thread on focused
execution work — that is dispatched to subagents so the main thread keeps its attention on task
boundaries. Full coordinator-side rule and duties: `agents/coordinator-agent.md` → Guardrails.

This is the strict case of a fleet-wide default and never an exemption from it: EVERY main fans
execution out to 3–5 concurrent subagents and keeps its own thread for review, integration and
boundaries. Canonical rule, including *When NOT to fan out*:
`agents/shared/OPERATING_CONSTRAINTS.md` → *Parallel Subagent Fan-Out*.
(origin: INC-20260728-idle-mains)

## Appendix — incident origins

Narrative only. Every rule above is complete without this section; nothing here is a directive.
Full ledger: `docs/reference/agent-config/INCIDENT_LOG.md`.

**INC-20260812-compacting-read-as-idle — three states, not two.** The same main was called
finished twice on pane text alone, and the operator corrected it both times. A compacting session
had shed its goal line, its "Pursuing goal" timer and its background-terminal count at once,
leaving a pane indistinguishable from a finished one.

**INC-20260727-stale-heartbeat — heartbeats are birth certificates.** A heartbeat written once at
session start was read as proof of liveness for the rest of the session. The 2026-08-12 measurement
in the rule above is the recurrence that fixed the refresh cadence at every task boundary.

**INC-20260728-cleared-context — the `/clear` sequencing trap.** A nudge of the form "run /clear
then do X" lost X: the clear wiped the pending instruction along with the context.

**INC-20260728-idle-mains — coordinator thread on execution work.** The coordinator worked focused
execution on its own thread while the mains it was meant to keep saturated sat idle with empty
queues.
