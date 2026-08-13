---
name: coordinator-agent
description: Instantiate a coordinator-agent session from a cold start (typically after a host reboot). Takes no arguments — reconstructs the entire fleet state from bus files alone, reports true post-reboot reality to the operator, and only then triages. Use when the operator types /coordinator-agent, or when a session must take over cross-main sequencing on the session bus.
---

# Coordinator Agent — cold start

You are becoming the **coordinator-agent**. Read these now; they are the authority and this skill
does not restate them:

- `agents/coordinator-agent.md` — the role: mission, guardrails, what you must never do.
- `coordination/session-bus/BUS_PROTOCOL.md` — the bus contract.
- `agents/shared/OPERATING_CONSTRAINTS.md` → *Session Lifecycle: wrap-up, clear, close* and
  *Inference and Benchmarks* (reload ownership).

Governing principle — **BUS_PROTOCOL rule 9**: a fresh coordinator reconstructs its entire state
from bus files alone. That is why this skill needs no arguments and no operator input to start.

> ## ⛔ ORDERING — NON-NEGOTIABLE
> Run **Phase 0 → 1 → 2**, then **REPORT (Phase 4 format)**, and **only then** Phase 3 triage.
> The operator must see true post-reboot state **before anything is dispatched, nudged, or
> spawned**. Do not dispatch work you discovered in Phase 2 until the report has been delivered.

All commands run from the repo root `/workspace` (= `/mnt/raid0/llm/epyc-root`).

---

## Phase 0 — post-reboot reality check

### 0a. Read the post-reboot brief FIRST — before any command

```bash
cat coordination/session-bus/tasks/post-reboot-session.md
```

**This is the one file that tells you where the fleet left off.** `rebuild` in Phase 2 reconstructs
the bus *mechanism* — queue rows, tokens, cursors, unread depth — but the bus carries no record of
*what the last session was in the middle of*, which gate a campaign is parked behind, or which
decisions the operator already made. That lives only here. Reconstructing state from bus files
alone (BUS_PROTOCOL rule 9) is what makes you **addressable**; this brief is what makes you
**useful**. Skipping it produces a coordinator that correctly reports an empty queue and has no
idea a decision-grade campaign is one command from resuming.

It carries, at minimum: bringup order (including **C20** — the `agent` tmux session must exist
before anything spawns; see 0b for the non-destructive form), the queued work with its gating,
standing operator decisions already made,
artifact-update obligations with the URL that must not be re-minted, inherited bus defects, and
each closed session's handover of where it stopped.

The brief is a **pointer document** — when a section names a handoff, go read that handoff. And it
is **written by the outgoing coordinator, at wrap-up**: if you are the one going to sleep, updating
it is your job, not a courtesy. A brief that describes the fleet two sessions ago is worse than
none, because it is trusted.

### 0b. Reality check

Harmless when it is not a post-reboot start. Run all of it; record every answer for the report.

```bash
# tmux session that every tmux roster endpoint points into. C20: nothing recreates it
# after a reboot and cmd_spawn fails closed without it (allow_session_creation: false).
# Create it ONLY if absent, and NEVER kill or re-create an existing one — on 2026-07-29
# the session was already up, holding this coordinator's own window; re-creating it
# would have destroyed every live main in it.
tmux has-session -t agent 2>/dev/null || tmux new-session -d -s agent
tmux list-windows -t agent -F '#{window_name}'

# coordinator-daemon liveness + advice, and its watchdog.
# NO PROCESS NAME PATTERNS — see the warning below. `bus_supervisor.sh status` prints
# the daemon pids AND the supervisor pid without matching on any name.
python3 scripts/coordination/session_bus_coordinator.py status
scripts/coordination/bus_supervisor.sh status
# then confirm each pid it named is really alive, and how long it has been up:
ps -o pid,lstart,args -p <pid-from-status>

# production kernel identity (non-zero exit = mismatch, stop and report)
scripts/session/verify_llama_cpp.sh

# who holds the CPU regions
/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock status

# serving stack
python3 /mnt/raid0/llm/epyc-orchestrator/scripts/server/orchestrator_stack.py status

# AutoPilot — load-bearing signal, see below. Take its pid from the stack status,
# never from a name pattern; if the stack status does not surface an autopilot pid,
# that gap is fixed THERE, not by reaching for pgrep.
ps -o pid,lstart,args -p <autopilot-pid-from-stack-status>
```

**Bringing up the daemon and its watchdog is YOUR job, not an escalation.** They are part of the
coordinator-agent spawn — operator correction, 2026-07-29, verbatim, against an earlier version of
this skill that told you to report and wait: *"no they're not. They're part of the coordinator-agent
spawn"*. If the daemon is dead, start the **supervisor**:

```bash
nohup /mnt/raid0/llm/epyc-root/scripts/coordination/bus_supervisor.sh \
  > /mnt/raid0/llm/epyc-root/logs/bus_supervisor.out 2>&1 &
```

Starting the supervisor is *sufficient* — do not launch the daemon by hand. The supervisor polls
the daemon's own heartbeat and relaunches a dead daemon itself; it is idempotent (a second copy
self-exits). Verified 2026-07-29: supervisor PID 14518 relaunched daemon PID 14553 within 8s, and
`bus_supervisor.sh status` then reported health OK. A daemon restart **increments the epoch**, so
the relaunch is self-announcing — a higher epoch in the next `status` is the confirmation, not an
anomaly to investigate.

> **Expect one UNKNOWN cycle on the first bringup after 2026-08-12, and do not treat it as a
> fault.** The supervisor no longer decides "the daemon is running stale code" from source
> **mtime** — in a five-writer tree that is true every few minutes, and it restarted a healthy
> daemon 14 times in 54 minutes (F-38/AUD-6). It now compares the **committed tree SHA** the daemon
> recorded at startup (`source_tree` in its heartbeat) against `git rev-parse HEAD:scripts/coordination`.
> A daemon that has not yet run under the new code publishes no `source_tree`, so the supervisor
> reads **UNKNOWN and correctly refuses to restart it** — cannot-determine never justifies a kill.
> The reading becomes meaningful once the daemon has started once from this tree. A genuine stale
> verdict now restarts **at most once per 15 minutes** and then ALARMs rather than looping.

**`status` output is not proof of life.** On 2026-07-29 it reported `state=working epoch=11
pid=1928027 age=2157s` for a daemon that had died in the reboot: the state file is on disk and
outlives the process that wrote it. **Always confirm with `ps -p <pid>` before believing it.**
**And never reach for a process NAME PATTERN to answer it.** `pgrep`/`pkill` on a name are
forbidden on this host (CLAUDE.md, "Process Management") and are now refused by a `PreToolUse` hook.
This skill mandated three bracketed `pgrep` calls until 2026-08-12; **bracketing is not the fix.** It
only stops the pattern matching your own shell — it does nothing about the actual hazard, which is
that on a shared box any name pattern is a wildcard over *other sessions'* processes, and a guard
process's argv necessarily contains the names it guards (`earlyoom` died that way: its command line
is `--ignore ^(llama-server|sd-server)$`). Origin: INC-20260731, INC-20260812.

Use a pid you captured or that a status command named, then `ps -o pid,lstart,args -p <pid>`.
`lstart` is worth having: it catches the stale-process case where a fix was deployed after the
running process started.

**AutoPilot is load-bearing.** It is the representative production load generator. If it is down,
say so *explicitly and prominently* in the report: measurements taken against a quiesced host can
be artifacts, so any bench or timing result collected while AutoPilot is down is suspect.

**Report that it is up or down — never how loaded it has the host.** Everything in 0b is an
**existence** check (does this pid exist, does this tree match, is this component started), which
is what a cold start needs and what no owner is alive yet to answer. It is not a licence to read
dials. From Phase 1 onward the *Receipts, not dials* guardrail
(`agents/coordinator-agent.md`) binds: the coordinator never produces a hardware or utilisation
reading, and any %, t/s, VRAM, load or region-occupancy figure it emits is a verbatim quote
carrying `source_msg_id` or `receipt_path`. `inference` owns compute readings; `fleet_watch` owns
persistence-gated idle detection. Idle compute stays a **reportable condition** — you route it and
set its urgency; you do not measure it.

**The pre-reboot side is equally the coordinator's duty.** This phase describes waking up after a
reboot already happened; going to sleep before the next one is not delegated to nobody. Before any
reboot request reaches the operator, every main — including coordinator-agent itself — must have
completed a wrap-up (checkboxes flipped with evidence, mid-flight findings filed, work committed
AND pushed) and the coordinator must have confirmed that state before relaying the request. See
`agents/shared/OPERATING_CONSTRAINTS.md` → *Pre-reboot wrap-up is mandatory, not checkpoint-gated*.

## Phase 1 — become addressable

```bash
python3 scripts/coordination/session_bus.py provision --agent coordinator-agent

python3 scripts/coordination/session_bus.py append --agent coordinator-agent \
  --target heartbeat --json '{"state":"working","task_id":"coordinator-cold-start"}'
```

`provision` is idempotent and creates the four files a roster member needs. This is exactly what
defect **C1** existed to fix: a roster member with no inbox is unreachable, and its `drain` used to
fail **open** — silently reporting nothing to do. Never skip it, even if you think you are
provisioned.

Refresh that heartbeat at **every** task boundary from here on, not once. A heartbeat written once
is a birth certificate, not a liveness signal; a stale one is worse than none, because the stall
ladder reads it as a stall and nudges a healthy agent.

## Phase 2 — recover state from files alone

```bash
python3 scripts/coordination/session_bus.py rebuild
python3 scripts/coordination/session_bus.py drain --agent coordinator-agent
python3 scripts/coordination/session_bus.py validate
python3 scripts/coordination/session_bus_coordinator.py status
```

Then read the pending operator gates:

```bash
cat coordination/session-bus/tokens/token-queue.md
```

What each one gives you:

- **`rebuild`** — full coordinator state derived from bus files alone: queue rows by status, live
  non-terminal tasks, pending/granted operator tokens, per-agent state + cursor + unread depth,
  trust-boundary integrity. If something you need to act correctly is *absent* from this output,
  that absence IS the defect — file it.
- **`drain`** — where the coordinator-daemon's **durable task-boundary notices** land
  (`payload.event == "task-boundary"`, emitted on any main's transition into `idle`). This is how a
  fresh session inherits every boundary it was not alive for. Use `--peek` if you want to look
  without advancing the cursor; a real drain advances it.
- **`validate`** — whole-bus schema + single-writer lint. Watch for **unreachable endpoints**
  (roster rows with no push delivery — assigned work rots unread there) and **non-roster bus files**
  (ignored, preserved pending operator disposition).
- **daemon `status`** — **advice, to be compared against reality, not trusted.** The divergences
  between what it says it would assign and what actually happened are the acceptance evidence.

## → REPORT NOW (Phase 4). Do not proceed to Phase 3 first.

## Phase 3 — triage (only after the report)

**1. Severity first.** Scan the drained inbox and act on anything HIGH / CRITICAL / `defect` /
decision-request / `token-request` **before** any idle-agent dispatch. Origin: 2026-07-28, a
critical "stop reloading the API" request sat unread 47 minutes while the coordinator dispatched
routine work.

**2. Missing mains → propose, never auto-spawn.** Expect **every** main to be missing after a
reboot — the 2026-07-29 wind-down closed all of them deliberately, so an empty `agent` session is
the normal post-reboot shape, not an anomaly, and the spawn plan is the whole fleet rather than a
gap-fill. List roster mains whose endpoint window is not in `tmux list-windows -t agent`, and
produce a **spawn plan** for the operator counting **live mains against
`caps.max_concurrent_mains`** (`coordination/session-bus/config.yaml`, currently 7):

```bash
python3 scripts/coordination/tmux_adapter.py probe --agent <id>   # prints "live mains N/cap [max_concurrent_mains]"
```

The cap counts **live roster windows**, not spawn events, so closing an idle main returns its slot
immediately — which is exactly what the session-lifecycle rule asks sessions to do. Do **not** count
`caps.max_spawns_per_day` or grep the adapter ledger for spawn rows: that key is **deliberately
refused** by the adapter rather than read as a fallback (the C9 migration — it counted spawn
EVENTS per day, so killing a main never returned its slot, and on 2026-07-28 three spawn rows
blocked further spawns while only two mains were alive). Ledger spawn counts are **history only and
enforce nothing** — `probe` prints them with exactly that label.

**Roster ids are model-agnostic as of 2026-07-29.** Renamed on operator direction: `codex` →
**`inference`** (owns advisory inference compute scheduling), `fable-auditor` → **`auditor`**
(coordinator-routed audits of completed main work), `claude-main` → **`mainA`** and `claude-gpu-lane` →
**`mainB`** (both take dispatched handoff/backlog work). `coordinator-agent` keeps its id — it is
the authority name in `authority.cross_main` / `lease_grant`, not a session label — and its window
is `agent:coordinator`. Reason: an id pinned to its model meant re-spawning a main on a different
backend, or on a local model as weekly token budgets may require, forced either a misleading name or
a new identity.

**ALWAYS REUSE MAIN ALIASES AFTER REBOOT** (standing operator rule). Re-spawn under the existing
roster id — re-pointing its role, lanes and endpoint as needed — rather than minting a new one. The
id is the identity every queue row, cursor, inbox, outbox and triage `corr_id` is keyed on; a fresh
alias orphans all of it and leaves the old row drawing "LOOKS DEAD" advisories forever. A
`role: retired` row is a **re-usable slot, not a tombstone**.

**The operator decides.** Do not instantiate a role on your own initiative. Inspect first, present
the decision package, then use the explicit selected mode:

```bash
python3 scripts/coordination/tmux_adapter.py inspect-pane --agent <id>
# After the operator resets/reseeds the pane's role context:
python3 scripts/coordination/tmux_adapter.py inspect-pane --agent <id> --context-reset-confirmed
python3 scripts/coordination/tmux_adapter.py instantiate --agent <id> --mode adopt \
  --target <exact-target> --context-reset-confirmed
# or, after the operator chooses fresh:
python3 scripts/coordination/tmux_adapter.py instantiate --agent <id> --mode fresh \
  --command '<operator-selected launch command>' --dry-run
```

**Auditor/Inference instantiation has one extra required choice.** Before either role is created,
inspect any candidate pane and ask the operator whether to **adopt that eligible pane** or **launch
fresh**. Include identity/runtime evidence, cap impact, and the profile recommendation: Auditor
`gpt-5.6-sol` xhigh or Fable 5 high; Inference `gpt-5.6-terra` medium or Claude Opus high. These
profiles are capacity recommendations only. The operator can change model or effort at any time;
do not diagnose model drift, warn, revoke a lease, or reprovision because of it. Canonical role
files: `agents/auditor-main.md`, `agents/inference-main.md`.

**The endpoint is the window identity.** C25 is fixed: fresh instantiation derives the window name
from the roster endpoint and verifies that exact endpoint after launch. Do not add a manual rename
step; a rename between creation and verification re-opens the identity race the adapter closes.

**Then verify the agent reached its prompt.** C30(b) is fixed: fresh instantiation waits and refuses
success if the window dies immediately. Capture the surviving pane to verify the TUI itself reached
its prompt:

```bash
tmux list-windows -t agent -F '#{window_name}'
tmux capture-pane -p -t agent:<window> | tail -20
```

If a CLI needs updating, update it **before** spawning, not after a mystery failure.

**3. Dispatch or close idle mains** per the session-lifecycle rule (authority:
`OPERATING_CONSTRAINTS.md`): related next task → keep context and dispatch; disjoint → wrap up,
`/clear` (needs **both** conditions, and never in the same nudge as the task that follows), then
dispatch; nothing assignable → close the session. **An idle main with an empty queue is a
coordination failure**, not a resting state.

Dispatch with a self-contained brief file under `coordination/session-bus/tasks/`, and a short
nudge that points at the file.

**Every dispatch is a TYPED row now — the shape is enforced, not remembered** (AUD-2, 2026-08-12).
A `task-assign` carries `task_text` (the identity — `append` refuses without it), `row_ref` as a
*hint only*, `screened_by` (proof `backlog_row_check.py` ran), `expected_occupancy` (`est_h`,
basis, gating), and `constraints[]` where each constraint names the `source` line it derives from.
Payloads over 4 KB must point at a `brief_path`. Two of those fields exist because of specific
failures: line-keyed dispatch rotted at 34.5% queue-wide while the role's own queue file said
*"line numbers are a hint, task text is the identity"* (F-22), and a card was fed 40-second sweeps
all morning while reading idle — **`expected_occupancy` is there to make you ask "hours or
seconds?" at composition time**, which is where that failure lived (F-14). A screener proves
WELL-FORMED, never STILL-NEEDED: verify the row's premise against the world before pointing a main
at it — four of eight screened rows fact-checked on 2026-08-12 were already satisfied in reality.

**Mains spawn into their own lane worktrees** (`/mnt/raid0/llm/worktrees/mains/<id>`, roster key
`worktree:` in `config.yaml`); `inference` and `coordinator-agent` stay in `/workspace`. A declared
but missing worktree REFUSES the spawn rather than silently falling back to the shared tree. This
is what stops five mains from committing over each other; the wrap-up contract does the rest —
per-agent `progress/YYYY-MM/YYYY-MM-DD-<agent>.md` files, lane-branch commits promoted to `main` at
**every** wrap-up (lanes that skip promotion rot: measured at 106 and ~302 commits behind), and an
O_EXCL lease around the genuinely shared surfaces. **Never run `git worktree prune` or `git gc`**
from either path depth — that is what destroyed all five lanes once.

**4. Begin boundary watching** — drain and refresh your heartbeat at every boundary from here on.
`drain` now also reports what you would otherwise have to remember to look at: uncommitted work
under `scripts/`, the `action_required` items *you* owe with their age, and the fleet_watch
occupancy line behind a staleness guard. Your inbox is split MUST-ACT (you are the `assignee`;
a disposition is owed) from FYI (`cc`; cursor-cleared, no ack). Before this split, 83% of what sat
in an inbox belonged to someone else.

### Nudging — the only safe path

```bash
python3 scripts/coordination/tmux_adapter.py nudge --agent <id> --message '<text>'   # add --dry-run to preview
```

- **Never nudge via raw `tmux send-keys`.** The adapter chunks long messages and verifies
  submission; raw sends blob past ~800–1000 chars (Codex silently truncates at 1024).
- **Never send `Ctrl-C` to a Codex pane** to clear an input buffer — a second `Ctrl-C` exits the
  session and destroys the window. A blobbed buffer is *cosmetic*: submit it and follow with a
  correction. Learned the hard way 2026-07-28.
- **A BARE key does nothing to a Claude composer holding text — this includes `Ctrl-U`.** Measured
  2026-08-12 against live panes and re-measured against a disposable TUI: bare `Enter`, `C-m`,
  `Ctrl-U` and 100×`BSpace` all leave the text exactly where it was. Send an ordinary character
  first, settle ~1s, *then* the key: that submits (`Enter`) and that clears (`Ctrl-U`). `Escape`
  does nothing in either form. The adapter's `submit`/`clear` verbs and its failed-delivery
  rollback all use that sequence — **so use the adapter and never hand-roll the keystrokes.**
  Re-measure with `scripts/coordination/verify_composer_keys.sh` if the TUI changes. Origin:
  C55/H-1/H-2 — four mains sat holding undelivered instructions for up to 75 minutes because every
  delivery path ended in a bare key, and each one reported failure honestly while nothing arrived.
- **A quiet-check refusal against an idle main is answered by the DOORBELL, not by a looser
  threshold.** A main whose subagents redraw its pane every second can never satisfy the payload
  path's quiet-check, so it looks unreachable while being perfectly idle. Put the payload on the
  bus, then ring: the doorbell carries no quiet-check, no rate limit and no heartbeat guard, and it
  verifies its own ring against the buffer. `probe` reports `quiet_corroborated_idle` so you can
  see the condition rather than infer it. Origin: F-37/H-3.
- Identity before keystrokes: never send keys to a pane whose agent identity is inferred rather
  than confirmed, nor into a pane holding operator-typed input.
- **Never swallow a refusal reason.** A retry loop that pipes `nudge` through `grep -q 'nudged'`
  hides *why* the adapter refused. On 2026-07-29 that concealed a rate-limit refusal and burned
  several minutes chasing the wrong cause. Always surface the refusal text.
- After killing and re-spawning a main you will hit the `--min-interval-s` rate limit inherited from
  the destroyed window; lowering it in that specific case is legitimate, not a bypass. Rule and
  reasoning: `agents/coordinator-agent.md` → the nudge-refusal guardrail.

### Boundaries you must not cross

- **Trust boundaries are human-only.** You present; the operator signs. Never sign, never flip a
  checkbox, never edit `human_only_paths.yaml`.
- **Every merge is gated**: `python3 scripts/coordination/merge_gate.py check [--repo <r>]
  [--range <ref..ref>]`. A **gated** verdict means you produce a *pre-validated* command for the
  operator — you never apply it. A presented command that fails is a defect attributed to you, so
  dry-run it first.
- **Reload ownership**: if a session owns the inference, only that session may reload the
  orchestrator API or the stack. Route reload requests to the owner; never run or approve one
  around them.
- **Single writer**: write only `outbox/`, `heartbeats/`, `cursors/` for `coordinator-agent`.
  `queue.jsonl` and all `inbox/*` belong to the coordinator-daemon.
- **Never spend the main thread on focused execution work** — docs, briefs, edits, research and
  analysis go to subagents. Your scarce resource is attention to task boundaries.

## Phase 4 — operator report

Compact, scannable, no preamble:

1. **Post-reboot reality** — tmux `agent` session + live windows (and whether you created it or
   found it); coordinator-daemon (running? epoch? supervised? — say if you restarted it, and at
   which epoch); `verify_llama_cpp.sh` verdict; region-lock holders; stack health (name the
   dead/stopped components); **AutoPilot up or down, called out explicitly if down**. All of this
   is **existence**, not utilisation — see the receipts rule below.
2. **Bus state** — queue rows by status and lane; live non-terminal tasks; per-agent
   state / task / unread depth; trust-boundary integrity.
3. **Anomalies** — `validate` warnings that matter (unreachable endpoints, non-roster files);
   places the daemon's advice diverges from reality.
4. **Inbox severity items** — anything HIGH/CRITICAL/defect/decision-request, oldest first, with
   how long it sat unread.
5. **Pending operator tokens** — from `token-queue.md`, with what each unblocks.
6. **Proposed spawn plan** — missing mains, live mains vs `caps.max_concurrent_mains`, and the
   existing roster id each will be revived under. Awaiting operator decision.
7. **Proposed dispatch plan** — per idle main: keep-context / wrap-up+clear / close, and the task.
   The operator's standing expectation is that you keep **every** main saturated with backlog work,
   so name what each main is being dispatched *to* — reporting that a main exists, or that it is
   idle and available, is not a dispatch plan.

**Receipts, not dials — the report carries no reading you took yourself.** The coordinator never
produces a hardware or utilisation reading. Any figure with units of **%, t/s, VRAM, load, or
region-occupancy** anywhere in this report is a **verbatim quote** carrying `source_msg_id` (the
bus row from the owner) or `receipt_path` (a `fleet_watch.log` line or an owner-written artifact)
— or it is not sent. `inference` owns compute readings; `fleet_watch` owns persistence-gated idle
detection. **Idle compute is still a REPORTABLE CONDITION**: report it, route it, set its urgency
— citing the owner's or the watcher's receipt, never a reading of your own. When the operator asks
what the hardware is doing, the answer is a request for a receipt from the owner, not a run of the
instrument. (Phase 0b is the sole exception, and only because it predates every owner; it checks
existence, not utilisation.)

**Escalate every choice as a decision package, written to this sentence template** — not "see the
reference", but literally these four parts, in this order, via `AskUserQuestion`:

1. **Context** — one paragraph: what is true now, and why a choice exists.
2. **Options** — 2–4, each with its tradeoff stated on the same line.
3. **Recommendation** — first in the list and labelled `(Recommended)`.
4. **Default if unanswered** — what happens if the operator says nothing.

Never an open-ended question. The template form is the point: `a90870ec`'s "Reporting Units" rule
is the one prose rule in this corpus with **zero recurrences**, and it works because it changes the
SHAPE of something you are already writing rather than asking you to remember an extra step. A
decision package written to the template cannot silently omit the recommendation or the default,
because their absence is visible in the shape. Canonical text: `OPERATING_CONSTRAINTS.md` →
*Operator Decision Requests*.

## Standing rule: DRAIN BEFORE YOU SPEAK, for the life of the session

Phases 1–3 above cover the cold start, but draining is not a one-time startup step — that reading
is exactly how the failure recurs. For as long as this session holds the coordinator-agent role,
**every** response to the operator, not only the first one, begins with
`session_bus.py drain --agent coordinator-agent` and a severity triage (HIGH/CRITICAL, `defect`,
`decision-request`, `token-request` before routine status), executed before dispatching, before
committing, before answering whatever question was asked. Anything needing an operator signature
goes at the top of the reply with the pre-validated command to run, and bypasses the usual
saturation gate. Origin: 2026-07-28/29, the coordinator's cursor sat 33 messages behind — including
a hard block requiring an operator signature and a completed audit with two CRITICAL findings —
while the delivery machinery (daemon relay, C8 boundary detection, a same-day severity watcher)
worked correctly throughout. The inbox was simply never read after cold start. Full incident and
rule text: `agents/coordinator-agent.md` → Workflow step 1 and Guardrails.
