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

Harmless when it is not a post-reboot start. Run all of it; record every answer for the report.

```bash
# tmux session that every tmux roster endpoint points into
tmux has-session -t agent && tmux list-windows -t agent

# coordinator-daemon liveness + advice, and its watchdog
python3 scripts/coordination/session_bus_coordinator.py status
pgrep -af 'bus_supervisor\.sh'

# production kernel identity (non-zero exit = mismatch, stop and report)
scripts/session/verify_llama_cpp.sh

# who holds the CPU regions
/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock status

# serving stack
python3 /mnt/raid0/llm/epyc-orchestrator/scripts/server/orchestrator_stack.py status

# AutoPilot — load-bearing signal, see below
pgrep -af '[a]utopilot\.py'
```

If the daemon is not running or `bus_supervisor.sh` is absent, **report it — do not start either
one yourself.** Daemon/watchdog lifecycle after a reboot is an operator action.

**AutoPilot is load-bearing.** It is the representative production load generator. If it is down,
say so *explicitly and prominently* in the report: measurements taken against a quiesced host can
be artifacts, so any bench or timing result collected while AutoPilot is down is suspect.

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

**2. Missing mains → propose, never auto-spawn.** List roster mains whose endpoint window is not in
`tmux list-windows -t agent`, and produce a **spawn plan** for the operator including spawns used
today against `caps.max_spawns_per_day` (`coordination/session-bus/config.yaml`):

```bash
grep '"kind": "spawn"' coordination/session-bus/adapter-ledger.jsonl | grep -c "$(date -u +%Y-%m-%d)"
```

**The operator decides.** Do not run `tmux_adapter.py spawn` on your own initiative. When
authorised, `tmux_adapter.py spawn --agent <id> --dry-run` first.

**3. Dispatch or close idle mains** per the session-lifecycle rule (authority:
`OPERATING_CONSTRAINTS.md`): related next task → keep context and dispatch; disjoint → wrap up,
`/clear` (needs **both** conditions, and never in the same nudge as the task that follows), then
dispatch; nothing assignable → close the session. **An idle main with an empty queue is a
coordination failure**, not a resting state.

Dispatch with a self-contained brief file under `coordination/session-bus/tasks/`, and a short
nudge that points at the file.

**4. Begin boundary watching** — drain and refresh your heartbeat at every boundary from here on.

### Nudging — the only safe path

```bash
python3 scripts/coordination/tmux_adapter.py nudge --agent <id> --message '<text>'   # add --dry-run to preview
```

- **Never nudge via raw `tmux send-keys`.** The adapter chunks long messages and verifies
  submission; raw sends blob past ~800–1000 chars (Codex silently truncates at 1024).
- **Never send `Ctrl-C` to a Codex pane** to clear an input buffer — a second `Ctrl-C` exits the
  session and destroys the window. `Ctrl-U` alone clears the composer. A blobbed buffer is
  *cosmetic*: submit it and follow with a correction. Both lessons learned the hard way 2026-07-28.
- Identity before keystrokes: never send keys to a pane whose agent identity is inferred rather
  than confirmed, nor into a pane holding operator-typed input.

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

1. **Post-reboot reality** — tmux `agent` session + live windows; coordinator-daemon (running?
   epoch? supervised?); `verify_llama_cpp.sh` verdict; region-lock holders; stack health (name the
   dead/stopped components); **AutoPilot up or down, called out explicitly if down**.
2. **Bus state** — queue rows by status and lane; live non-terminal tasks; per-agent
   state / task / unread depth; trust-boundary integrity.
3. **Anomalies** — `validate` warnings that matter (unreachable endpoints, non-roster files);
   places the daemon's advice diverges from reality.
4. **Inbox severity items** — anything HIGH/CRITICAL/defect/decision-request, oldest first, with
   how long it sat unread.
5. **Pending operator tokens** — from `token-queue.md`, with what each unblocks.
6. **Proposed spawn plan** — missing mains, spawns used today vs `max_spawns_per_day`. Awaiting
   operator decision.
7. **Proposed dispatch plan** — per idle main: keep-context / wrap-up+clear / close, and the task.

Escalate any choice as a decision package (`OPERATING_CONSTRAINTS.md` → *Operator Decision
Requests*): 2–4 options with tradeoffs, a recommendation first and labelled "(Recommended)", and
the default if no choice is made. Via `AskUserQuestion`. Never an open-ended question.

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
