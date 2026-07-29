# TASK BRIEF — auditor — adopt C-OWN (the session-bus delivery plane)

**Roster id:** `auditor` · **Lane:** none (never takes an inference lane) ·
**Assigned by:** coordinator-agent, 2026-07-29

## 0. Why you, and why now

`mainB` was re-tasked off the session-bus C-series and then closed, and it explicitly
refused to inherit the series under a different mandate. So **C6 / C9 / C10 / C11 / C14 / C16 /
C18 / C21 / C22 / C23 and all of `scripts/coordination/tmux_adapter.py` currently have no owner.**
Filed as **C-OWN** in `handoffs/active/session-bus-thin-dispatcher.md` (~line 678).

That is the plane every other main depends on to receive work at all. Two independent failures
this morning show it is not theoretical — see §2. **You own it now.** Your first task is the
defect that was actively hiding operator gates.

Read `handoffs/active/session-bus-thin-dispatcher.md` (the C-series ledger) and
`coordination/session-bus/BUS_PROTOCOL.md` first.

## 1. PRIORITY 1 — the undelivered token-request defect (HIGH)

**Two `token-request` messages from `inference` never reached the coordinator's inbox and never
reached `tokens/token-queue.md`.** The triage report found them only by outbox scan, annotating
each: *"NOT in your inbox — found by outbox scan; the relay may never have delivered it."*

| Gate | Filed | Undelivered for |
|---|---|---|
| `RATIFY-P-BENCH-4-FG4B-AFFINITY-20260729` (P0-2) | 2026-07-29 10:18Z | ~4 h until the reboot |
| `RATIFY-E8-FINAL-C1-RETRY-CAPACITYFIX-20260729` (P0-1) | 2026-07-29 11:16Z | ~3 h until the reboot |

Both are `kind: token-request`, both carry `needs_routing_to: ["coordinator-agent"]` and
`action_required: true`, both were well-formed. Neither was ever presented to the operator, so
neither is expired-by-decision — **they are undelivered**.

Why this is the worst class of bug on this plane: `token-queue.md` reads *"Pending token requests:
(none)"* and `session_bus.py rebuild` reports *"2 pending"* meaning the unrelated M5 flags. **A
coordinator following the documented cold-start procedure exactly would conclude no gates were
waiting.** That is a fail-open in the same family as C3 / C6 / C8, one layer up: not a lost
message, a lost *signature request*.

Answer, with evidence, at minimum:
1. Where in the daemon's relay path a `token-request` is supposed to become a `token-queue.md`
   block, and what actually happened to these two.
2. Whether the relay dropped them, or the transcription step did, or whether they were relayed and
   the queue render silently omitted them.
3. Whether the daemon being **down at the time** explains it — and if so, why nothing detected a
   gap on restart. A queue that only reflects messages relayed while the daemon happened to be
   running is a durability defect, not a scheduling one. (Note the daemon was found dead at
   14:12Z post-reboot with a stale `epoch=11 pid=1928027 age=2157s` state file naming a PID that
   did not exist — `status` reporting a dead daemon as `state=working` is itself worth a finding.)
4. Whether any **other** message class can be lost the same way.

Do not repair the two gates themselves — codex is re-validating and re-filing them. Fix the path.

## 2. PRIORITY 2 — C24 and C25, found during this cold start

**C24 — `cmd_spawn` left a stale heartbeat, making every re-spawned main unreachable from birth.**
`cmd_spawn` seeded `heartbeats/<agent>.json` only `if not p.exists()`, so a roster id that had ever
run kept its dead predecessor's heartbeat. `cmd_nudge` then refuses on `state == working` and on
age, and the fresh session cannot clear either — it has not been told to drain, and it cannot be
told, because the telling is what the guard refuses. Measured at 14:20Z: **all three pre-existing
roster ids were undeliverable**; `inference` on both state *and* age, its heartbeat still reading
`working` on `e8-deterministic-completion-repair` from a session that no longer existed.

**Already fixed by coordinator-agent** — heartbeat now written unconditionally, cursor deliberately
still only-if-absent (a cursor is a read position, not a liveness claim; resetting it would
re-deliver everything the identity already drained). 5 new assertions;
`test_tmux_adapter_live.py` **43/43 green**; verified end-to-end by re-spawning codex through the
fixed path.

**Your job is the independent review that C9's own filing called for and never got** (that is C11,
still unpaid). Review C24 specifically for this: its safety argument rests entirely on
`live_mains()` being correct, because `cmd_spawn` refuses when `args.agent in ids` and therefore
"proves" the id is not live before overwriting its heartbeat. **If `live_mains()` can ever
undercount — the C14 capacity-inventing direction — that fix can reset a genuinely live main's
heartbeat and re-open it to a mid-generation nudge.** Say plainly whether that hazard is real.

**C25 — `cmd_spawn` and `resolve_target` disagree on the window name for one identity.** Spawn
names the window `args.agent` (`inference`); `resolve_target` verifies the roster endpoint's window
(`codex-inference`). So a spawned main is undeliverable until renamed. Worked around at 14:18Z with
`tmux rename-window -t agent:codex codex-inference` (probe-verified), but that is a manual step
whose omission silently breaks delivery. Real fix: derive the window name from the endpoint.
**Not yet fixed — it is yours.**

Both are filed on the bus: `coordination/session-bus/outbox/coordinator-agent.jsonl`,
`msg-20260729T142122Z-38-coordinator-agent`, task `bus-c24-spawn-leaves-stale-heartbeat`.

## 3. PRIORITY 3 — the standing residuals

- **C11** — C9 (the `live_mains` / `resolve_spawn_cap` / `cmd_spawn` change, committed `8cbe50c0`)
  landed on direct operator instruction, but **the independent review C9's own filing called for
  was never paid.** Not urgent — the change is fail-closed on every branch it cannot evaluate and
  both suites are green — but cheap now, expensive later. Fold it into your C24 review; they touch
  the same invariant.
- **C22** — `roster_window_names()` dead code carrying the last-writer-wins `names[value]=rid`
  idiom. **Verify before working it**: the docstring at `tmux_adapter.py` ~line 437 states it was
  *"deleted as dead code 2026-07-29"*, so this may already be closed. If it is, say so and close
  the row rather than re-fixing it.
- **C23** — triage disposition has no bulk-clear granularity, so N routed items produce N identical
  payloads. **This is protocol shape, not a send bug — do not "fix" it in the adapter.** It is not
  hypothetical: **19 byte-identical `triage-disposition-post-standdown` payloads are sitting in the
  coordinator's triage queue right now — 40% of a 48-item queue is one message.** `mainB`
  self-diagnosed it correctly before closing: 19 distinct corr_ids, 19 distinct message ids,
  relayed 1:1, no duplicate-send bug; the defect is that clearing triage requires one corr_id per
  item while the payload was identical across all of them. Standing rule it adopted, worth
  codifying: *a repeated payload across N corr_ids is bus noise by construction.*
- **C18a** — `codex-bus-tests` still carries `role: retired` with a stale heartbeat. Bookkeeping.
- **C17** — a live window that no roster row claims (`htop`, `btop` are live in the `agent` session
  right now and are operator-owned). Per the corrected model these are a different **category**,
  not an undercount: surface them as informational, never refuse on them.

## 4. Constraints

- **Lane `none`, always.** Never take an inference lane; `inference` (E8) and `mainA` (E5) are
  both on the CPU and you must not contend with them.
- **Single writer.** Write only `outbox/`, `heartbeats/`, `cursors/` for `auditor`.
  `queue.jsonl` and every `inbox/*` belong to the coordinator-daemon.
- **Never suppress error output on bus writes.** A silenced schema rejection is indistinguishable
  from success — the same fail-open class as C3/C6/C8.
- **Test guards against the COMPLIANT path too**, not just the violating one, and verify resolved
  targets rather than trusting them. Audit what a fixture *deletes*: the existing spawn test
  deleted all four bus files before re-spawning, which is exactly why it never caught C24 — a
  fixture that removes the signal under test passes a broken implementation.
- Trust boundaries are human-only. Never sign, never flip a checkbox you do not own, never edit
  `human_only_paths.yaml`.

## 5. Bus discipline

At every task boundary:

```bash
python3 scripts/coordination/session_bus.py drain --agent auditor --triage
python3 scripts/coordination/session_bus.py append --agent auditor \
  --target heartbeat --json '{"state":"working","task_id":"<current>"}'
```

Report to coordinator-agent on task_id `c-own-adoption`. File each disposition as a finding on the
bus, with `needs_routing_to` / `action_required` set structurally.

---

## ROSTER RENAME — 2026-07-29 14:45Z (operator direction)

Roster ids are now **model-agnostic**, so a main can be re-spawned on a different backend (or a
local model) without its identity changing:

| was | now | owns |
|---|---|---|
| `codex` | **`inference`** | inference tasks; currently the stack owner + E8 P0-1 |
| `fable-auditor` | **`auditor`** | miscellaneous tasks; the DEFAULT main for auditing other mains' work |
| `claude-main` | **`mainA`** | whatever handoff/backlog work is dispatched to it |
| `claude-gpu-lane` | **`mainB`** | whatever handoff/backlog work is dispatched to it |

`coordinator-agent` keeps its id (it is the authority name in `authority.cross_main` /
`lease_grant`, not a session label); its window is `agent:coordinator`.

Your four bus files were moved with `git mv` and their internal `agent` fields rewritten, so your
history followed you — nothing was orphaned. **Use your NEW id verbatim in every bus command.**
Older briefs and `post-reboot-session.md` still name the old ids; that is history, read it as such.
