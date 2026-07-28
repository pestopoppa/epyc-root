# Session Bus Protocol v1

Owning handoff: [`handoffs/active/session-bus-thin-dispatcher.md`](../../handoffs/active/session-bus-thin-dispatcher.md)
(M1). Sibling contract: [`../inference-batch/LOOP_PROTOCOL.md`](../inference-batch/LOOP_PROTOCOL.md).

## Roles (one role, two tiers)

| Term | What it is |
|---|---|
| **coordinator** | the role the operator interacts with |
| **coordinator-daemon** | `session_bus_coordinator.py` — host-side, `nohup`+flock singleton, tick loop, epoch fencing, heartbeat. **Not** an agent session. Transcribes, validates, assigns by deterministic rule; **never** sets priorities, never reviews work products |
| **coordinator-agent** | an agent session with a roster row. Decision packages, operator-intent relay, cross-main reprioritization, lease grants, integration |
| **main** | a long-horizon agent thread doing the work |

## Rules

1. **SINGLE WRITER.** `queue.jsonl` + `inbox/*` = coordinator-daemon; `outbox/<a>` = agent `<a>`;
   `heartbeats/<w>` = writer `<w>`; `tokens/token-queue.md` blocks = coordinator-daemon relay,
   checkboxes = operator. **No file ever has two writers.** One writer may own many files.

   *Enforcement boundary, stated plainly:* `session_bus.py` derives the required writer from the
   target path and refuses a mismatch, so a cross-write is structurally inexpressible — you can
   only address the files of whoever you claim to be. But `--agent` is **self-asserted**: the CLI
   cannot detect impersonation. M1 acceptance therefore relies on the content-level ownership
   lint (`from == owner` plus target-path refusal) and commit separation, not `git blame` author
   names: all current agents share one git identity, so author-name output cannot discriminate
   writer sessions. A stronger identity boundary remains future work.
2. **NEVER BLOCK.** No agent waits on the bus. Work continues; grants and acks are picked up at
   the next boundary (op-bundle contract). A pending operator token never gates unrelated work.
3. **ACKS.** `requires_ack` messages are redelivered as a `nudge` (same `corr_id`) after
   `ack_deadline_s`; consumers dedupe by msg `id`.
4. **CURSORS.** Each consumer owns `cursors/<self>.json` (byte offsets); never rewind another's
   cursor. Rotation (coordinator-daemon, own files only) happens only past ALL cursors, into
   `archive/`.
5. **AUTHORITY.** Reprioritize scope per `config.yaml`'s matrix; violations are rejected with a
   `defect` row. The coordinator-daemon files defect rows against coordinator-agent on
   **mechanically checkable** violations only — never on judgment.
6. **TRUST BOUNDARIES ARE HUMAN-ONLY** and unchanged: era registry rows, `MEASUREMENT.md`,
   AutoPilot baseline applies, production freezes/cutovers, host reboots. The coordinator-daemon
   sequences and the coordinator-agent presents; **neither signs**. The human-only path list is
   itself human-amendment-only and hash-pinned — coordinator-agent reads it, never writes it.
7. **RESOURCE CLAIMS ARE ACQUIRED, NOT OBSERVED.** Lane sensing informs scheduling; only holding
   the lock provides exclusion (observing holders is TOCTOU). Anything occupying CPU regions
   acquires them via `epyc-orchestrator/scripts/region-lock`. One fact per physical resource —
   the `flock` — with any advisory lease layer sitting *above* it, never claiming to be it
   (fabric axiom 1).
8. **RECLAIM IS ALWAYS QUIESCE-AND-DRAIN.** Lease revocation and priority yield mark the holder
   `revoking`/`draining`; it stops accepting new work and releases at its next boundary. Never
   mid-decode, never a kill (fabric axiom 4). A revoked main immediately continues on `lane: none`
   work — it does not stall. A revocation the holder ignores surfaces as a `defect`, never as a
   silent inconsistency.

   *Mechanism (R4).* `coordinator-agent` (or the operator through it) writes a `lease-revoke`
   message to its own outbox; authority is checked against `authority.lease_grant` in
   `config.yaml` and an unauthorised sender is rejected with a `defect`, never obeyed. The
   coordinator-daemon marks the queue row `revoking` — status is UNCHANGED, because the task
   genuinely is still running — and nudges the holder to drain. When the holder reports
   `state: draining`, the lease is released: owner cleared, status `READY`.
   A task released this way is **excluded from that same tick's assignment**, otherwise it would
   be handed straight back to the same holder and the revocation would be a no-op with a pointless
   drain. It resumes on a later tick by ordinary priority ordering, so there is no lasting
   penalty — that ordering IS the deterministic re-grant trigger, and the daemon exercises no
   discretion in choosing when.
9. **RECONSTRUCTIBILITY.** Coordinator-agent state must be rebuildable from bus files alone
   (`queue.jsonl`, `tokens/token-queue.md`, heartbeats, cursors). Authority that exists only in a
   session's context is a design defect. **Verify it, do not assert it:**
   `session_bus.py rebuild` derives the full coordinator state from bus files alone. If a
   fresh session can act correctly from that output the invariant holds; anything it needs
   that is absent there IS the defect. Degraded mode with coordinator-agent down: the daemon
   keeps assigning, deterministic lease re-grants keep flowing, tokens accumulate durably, and
   **merges and discretionary reprioritization pause** — nothing blocks.
10. **EVERY QUEUE ROW DECLARES ITS GATING** (`cpu` / `gpu` / `both` / `none`). A missing
    classification is a hard validation failure: without it, revocation has no defined fallback
    set and rule 8 cannot be honoured.

## Standing instructions change under running sessions

An agent's instruction set is loaded at session start. Editing `CLAUDE.md` /
`AGENTS.md` therefore does **not** reach a session already running — observed
2026-07-27, when a heartbeat-refresh rule was added at 21:43Z and a demonstrably
active agent was still on its 19:45Z heartbeat afterwards.

So a standing-instruction change is a **coordination event**, not just a commit:

- The coordinator-agent nudges every running main to **re-read `AGENTS.md`**, not to
  act on a summary of the change. A summary is lossy; the file is authoritative.
- Agents treat such a nudge as "refresh your instruction set", not as a one-off
  task, because the next change will arrive the same way.
- Until a main confirms the re-read, assume it is operating on its startup copy.
  Do not read a stale behaviour as disobedience.

## Drain

Every agent, at every task boundary:

```
python3 scripts/coordination/session_bus.py drain --agent <id>
```

Act on assignments and nudges; write acks and status to your own outbox.

## Session lifecycle at a task boundary (coordinator duty)

Full contract: `agents/shared/OPERATING_CONSTRAINTS.md` → *Session Lifecycle: wrap-up, clear,
close*. The bus-relevant summary, because this is where the coordinator sees the boundary:

- **An idle main with an empty queue is a coordination failure**, not a resting state. Rule 2
  says no agent blocks on the bus; it does not say an agent may sit with nothing to do.
- At a boundary, exactly one of: **related next task → keep the context and dispatch**;
  **disjoint next task → wrap up, then `/clear`, then dispatch**; **nothing assignable → close
  the session**.
- `/clear` needs **both** a completed wrap-up **and** a disjoint follow-on. Related-domain
  context is an asset — clearing it buys a rediscovery pass and nothing else.
- `/clear` destroys the pending instruction, so it can never share a nudge with the task that
  follows it. Clear, confirm, then dispatch a separate nudge pointing at a self-contained brief.

Boundaries reach the coordinator durably: the coordinator-daemon's `detect_task_boundaries()`
delivers a `status` message with `payload.event == "task-boundary"` to `coordinator-agent`'s
inbox on any main's transition into `idle`. That is daemon-side, so it survives a coordinator
session restart — but it makes boundaries *durable*, not *instant*: a running session still only

### Unreachable idle session (stale heartbeat, guard refuses nudge)

`tmux_adapter.py nudge` refuses to nudge a target whose heartbeat still reads `working`, even if
the target actually finished and is now idle and blocked waiting for input — it cannot refresh
its own heartbeat while blocked, so the guard's refusal and the target's silence reinforce each
other into a deadlock. `--heartbeat-max-age` does not help: the refusal keys on heartbeat state,
not age. Do not bypass the guard with raw `tmux send-keys`.

A refusal is a snapshot, not a verdict: check the pane first (a mid-generation session is not
blocked, and the guard is correct), then keep re-probing with `tmux_adapter.py probe --agent <id>`
rather than escalating immediately — most refusals self-clear (quiet-check ~20s, nudge rate limit
600s, `working` heartbeat clears at the session's own next boundary). Escalate to the operator
only once the block outlives the longest plausible self-clearing timer (10-15 minutes of
continuous refusal with no pane activity) AND something is actually waiting on that session. Never
busy-wait or bypass while probing; do other coordination work between probes (rule 2 covers
blocking on a human too). Full procedure, threshold reasoning, and origin incident:
`agents/coordinator-agent.md` → Guardrails.
sees them at its next drain (defect C8, 2026-07-28).
