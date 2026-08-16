# Session Lifecycle — wrap-up, clear, close

Canonical contract for any agent directing another long-running session (coordinator-agent
above all), and for your own session when a task ends. Extracted 2026-07-30 from
`agents/shared/OPERATING_CONSTRAINTS.md` § "Session Lifecycle: wrap-up, clear, close" (AFC-P6
restructure); coordinator-specific duties stay in `agents/coordinator-agent.md`.

## Two axioms (canonical statements — cite, don't restate)

- **An idle main with an empty queue is a coordination failure**, not a neutral resting state.
- **The handoff dashboard counts CHECKBOX STATE ONLY.** Prose status is invisible to it. Any
  edit recording completed work flips the matching `- [ ]` → `- [x]` (append `✅ YYYY-MM-DD`);
  work discovered mid-flight gets its own task line. Un-wrapped work is, from the operator's
  view, work that did not happen.

## Reading another session's liveness — three states, not two

A session is **working**, **compacting**, or **idle**, and the pane cannot tell you which. A
session COMPACTING its context renders **identically** to a finished one: the goal line, the
"Pursuing goal" timer and the background-terminal count all disappear together, leaving a bare
status line above an empty composer. Read that as "done" and you re-dispatch, wrap up, or
`/clear` a session that is mid-turn. Never conclude idle from pane text alone.

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
  heartbeat is a birth certificate, not a liveness signal (INC-20260727-stale-heartbeat) — which
  is why every main refreshes it at EVERY task boundary (`CLAUDE.md` § Agents & Automation).
- **When heartbeat, pane and hardware disagree, the hardware reading wins** — provided the
  hardware reading itself persists across samples, because one sample landing between two
  short benches shows an idle card in a healthy sweep (`agents/shared/MEASUREMENT_POLICY.md` →
  *Observation windows*).

Origin: INC-20260812-compacting-read-as-idle (`docs/reference/agent-config/INCIDENT_LOG.md`) —
the same main was called finished twice on pane text alone, and the operator corrected it both
times.

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

## Wrap-up at major checkpoints, not only at session end

A major checkpoint is a phase boundary or a completed campaign — not every task. The operator
monitors progress via the dashboard (checkbox axiom above), so a checkpoint that is never
wrapped up did not happen from their view. Wrap-up may run on the main session or via a
coordinator subagent **on its behalf** — preferred when the main is already dispatched into new
work. Related standing direction (2026-07-28): actively source and track non-inference work
that can proceed regardless of a pending reboot or blocked inference lane.

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
boundaries (origin: INC-20260728-idle-mains). Full coordinator-side rule and duties:
`agents/coordinator-agent.md` → Guardrails.

This is the strict case of a fleet-wide default, not a coordinator privilege: EVERY main fans
execution out to 3–5 concurrent subagents and keeps its own thread for review, integration and
boundaries. Canonical rule: `agents/shared/OPERATING_CONSTRAINTS.md` → *Parallel Subagent Fan-Out*.

Incident narratives: `docs/reference/agent-config/INCIDENT_LOG.md`.
