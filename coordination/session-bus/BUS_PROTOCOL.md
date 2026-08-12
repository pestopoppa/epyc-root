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

## Routing intent is structural, not prose (2026-07-29)

Two routed messages were missed on 2026-07-29 because routing intent lived as prose inside
`payload` ("FOR FABLE-AUDITOR …" in a defect string; "action: DOC FIX requested … relay") and a
context-economy payload truncation cut exactly the sentences carrying it. No tool could have known
better. Therefore:

- **`needs_routing_to`** (top-level msg field, array of roster ids): who this message must REACH,
  beyond the transport `to`. `append` refuses non-roster ids.
- **`action_required`** (top-level, boolean): the routed-to agents (`needs_routing_to`, else a
  concrete `to`) must ACT. `append` refuses `action_required` on `to: '*'` with no
  `needs_routing_to` — intent with no addressee is the failure shape itself.
- **`triage --agent <id>`** (also `drain --triage`) prints the standing queue of messages routed
  to you: **in full, never truncated, cursor-independent** — the agent's whole inbox plus a scan of
  every outbox, so a message the relay never delivered is still visible to its target. Draining
  cannot consume this queue.
- **Disposition** is the only thing that clears an item, written to YOUR OWN outbox with
  `corr_id` = the message id (a daemon relay copy and its original are one logical message —
  either id works): any substantive kind, or `kind: ack` with `payload.disposition` in
  `done | declined | handed-off | superseded`. A **bare ack is receipt, not action**: it clears a
  reach-only message but an `action_required` one stays listed as acked-awaiting-action.
- **`validate` warns** when a payload carries prose routing markers (a roster id in a routing
  phrase, or an action request) while the structural field is unset — authoring-side (outbox rows)
  only. Anyone summarizing or truncating bus traffic must preserve these two fields and must not
  truncate messages carrying them.

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

## Stuck-agent rescue and the last hop to the operator (C19 / C20, 2026-07-29)

**Stuck-agent rescue (C19).** The coordinator-daemon detects, every tick, any roster member with
`unread > 0` past its cursor whose heartbeat says `idle`, is absent, or is stale beyond one hour,
and nudges it to drain **through `tmux_adapter.py`** — never with raw `send-keys`. An adapter
refusal (rate limit, quiet-check, unresolvable window, gate off) is a legitimate outcome: it is
recorded in `advisory.jsonl` and retried later, never routed around. A non-tmux endpoint
(`monitor:file`) cannot be nudged at all and is surfaced as `stuck-unreachable`. An agent that was
nudged and whose unread count *and* cursor are unchanged is not asleep — it is refusing to drain;
that escalates (`stuck-refusing-drain`) instead of being nudged forever. State lives in the
daemon-owned `stuck_state.json`, so a daemon restart does not re-nudge everybody. Unread that
cannot be computed (missing inbox, unreadable cursor, malformed JSONL) is **never** read as zero.

**The last hop (C20).** Delivery is mechanical; bus → *operator* was not. Unread `token-request` /
`defect` / CRITICAL items in `coordinator-agent`'s inbox age into a nudge at 30 minutes and, if
still unread at 90 minutes, into a **daemon escalation block appended to `tokens/token-queue.md`** —
a file the operator already reads. The coordinator is in the loop for JUDGEMENT; it must not be a
single point of failure for TRANSPORT of "a human signature is needed". The block is idempotent on
message id and carries **no checkbox**: the daemon relays, only the operator signs (rule 1).
**Since C27 it also scans OUTBOXES** for operator items with no evidence anyone consumed them
(not relayed, not answered by `corr_id`, gate not in the token queue), and tags the escalation by
which hop failed — "never reached the inbox" and "sat unread" have different repairs. A last-hop
net that depends on the hop before it having worked is not a net.

## Gate presentation is transport, and transport runs at every authority (C27, 2026-07-29)

Two operator SIGNATURE REQUESTS filed on 2026-07-29 were never presented to anyone:
`RATIFY-P-BENCH-4-FG4B-AFFINITY-20260729` (10:18Z) and
`RATIFY-E8-FINAL-C1-RETRY-CAPACITYFIX-20260729` (11:16Z). Both well-formed, both
`needs_routing_to: [coordinator-agent]`, both `action_required`. `token-queue.md` read
*"Pending token requests: (none)"* throughout, so **a coordinator following the documented cold
start exactly would conclude no gates were waiting.** Not a lost message — a lost request for a
human signature.

Cause: `relay_tokens`, the only writer of gate blocks, ran only inside `apply_assignment`
(`authority: assign`) while the live config is `manual`; and `token-request` was excluded from the
always-on relay *because `relay_tokens` was named as its handler*. An exclusion was justified by a
handler the configured authority never reached.

The standing rules that follow:

- **Presenting a gate is TRANSPORT.** It writes an unchecked `- [ ]` into a file the operator
  reads. It grants nothing, expands no authority, touches no trust boundary — the operator still
  signs. So it runs at EVERY authority, beside C2 relay, C19 rescue and C20. **Holding the
  requesting task on that gate is a scheduling decision** and stays `assign`-only. The daemon's
  bright line is unmoved: at `manual` it still writes no queue rows.
- **An exclusion from the general path is a claim you must be able to defend**: name the function
  that consumes the kind AND the authorities at which that function actually runs. When the handler
  is unreachable the message is **relayed normally and a defect is emitted** — never a silent
  `continue`. Duplicating a message into an inbox costs a read; dropping one costs a gate.
- Consequence worth remembering: the `needs_routing_to` fan-out sits *after* that exclusion, so
  the field this protocol says DELIVERS was inert for exactly the kinds that most needed it.

## A repeated payload across N corr_ids is bus noise by construction (C23, 2026-07-29)

Clearing triage requires one disposition per `corr_id`. When the same payload answers N routed
items, that produces N byte-identical messages — 19 identical `triage-disposition-post-standdown`
rows once made up 40% of a 48-item queue. This is **protocol shape, not a send bug**: 19 distinct
corr_ids, 19 distinct ids, relayed 1:1. Do not "fix" it in `tmux_adapter.py`.

**The 2026-07-29 rule was NOT PERFORMABLE, and is replaced (C23, 2026-08-11).** It said *"before
writing the same payload against a second `corr_id`, write it once and reference it"* — while no
mechanism to reference it existed. Clearing triage took one `corr_id` per item, full stop, so a
session holding one answer for N items had no compliant way to send it once. It failed within
hours: measured from one careful main, 3 byte-identical payloads at 17:41Z and 6 more at 17:44Z
differing only in `corr_id` — **nine in ten minutes, by someone following the rule correctly.**
Fan-out multiplies it, since N dispositions × M routing targets is N×M triage entries fleet-wide.
Two failures in ten minutes is the rule being the defect, not the sender.

Standing rule, now performable: **one answer, one row.** A message may carry `corr_ids: [<id>,
<id>, …]` alongside or instead of the scalar `corr_id`, and it clears every id it names. The scalar
is unchanged and is still correct for a genuinely per-item answer.

What has NOT changed, and is the reason the bulk form is scoped rather than general: a disposition
that is genuinely per-item carries per-item content, so **N distinct answers still want N rows**.
Use `corr_ids` only when one answer really does cover every id listed. A reader who cannot tell N
answers from one answer repeated N times has lost the signal the queue exists to carry — and a bulk
row that flattens N different answers into one loses it just as thoroughly, in the other direction.
A bare bulk ack is still receipt, not action: `action_required` items keep appearing until
dispositioned. Bulk changes the arity, never the semantics.

**Operator-script receipt convention (proposed; the scanner is inert until adopted).** A script in
`artifacts/operator/` may declare its gate with a header line `# BUS-GATE: <gate-id>`. On a
successful apply it writes `<script-name>.receipt.json` beside itself; when a successor is
generated, the superseded script gets `<script-name>.superseded`. The daemon then flags any
declaring script whose gate appears in neither the token queue nor any outbox `token-request` and
which has neither marker — i.e. a ratification that was printed at a human but never *filed*. No
script declares `BUS-GATE` today, so the check emits nothing; adopting the convention is an
operator decision, and without it the join has no ground truth (an earlier attempt mis-flagged 11
of 25 scripts, because superseded and repaired scripts never receive receipts).
