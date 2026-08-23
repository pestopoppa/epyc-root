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

   *Amendment, 2026-08-16 — POOL WORKERS ONLY (D6, Loop-Owned Fleet).* A pool worker reached
   through an `exec:` endpoint may be killed at lease expiry: `SIGTERM` → grace →
   `SIGKILL`, of a pid the runner captured itself. **KILL IS PERMITTED; LOSS IS NOT.** Every
   kill is followed by a MANDATORY salvage before the row may close — the lane worktree's
   uncommitted state is committed to a `salvage/<task_id>` ref, the harness transcript and the
   captured pane scrollback are attached, and the row is marked `FAILED` with a `salvage_ref`.
   A kill whose salvage did not complete is itself a `defect`.

   The exception is narrow and does not generalise. **Interactive sessions keep drain-only
   reclaim, unchanged** — the reason axiom 4 exists is that a human's session holds
   unreproducible context, and a pool worker holds none: it is exec'd per assignment from a
   typed brief, commits per unit, and is reconstructible from that brief plus its salvage ref.
   Quiesce-and-drain also cannot terminate a *wedged* worker — a hung API call never reaches a
   boundary — so without this the lease would be unenforceable and a single wedge would hold a
   lane forever, which is the unbounded-block failure the lease exists to prevent.

   *Enforcement.* `worker_runner.py` REFUSES TO SPAWN unless
   `worker_pool.rule8_amendment_ack` in `config.yaml` names this ratification. A runner that
   enforces a lease can kill, so it declines to exist until the amendment permitting that is on
   the record. Ratified with D6 by the operator, 2026-08-15.

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
11. **COMPUTE IS OWNED AT THE COORDINATION LEVEL AS POLICY DATA; EVERYONE REQUESTS WINDOWS
    THROUGH THE BUS.** No session owns compute. The console (in conversation with the
    operator) authors the compute policy file, `compute_policy.yaml` — priorities,
    reservations and windows are judgement and live there. The coordinator-daemon EXECUTES
    grants deterministically: a request is granted iff the region is free (the flock claim,
    never an observation) ∧ policy allows it (consumer listed, device permitted, no
    reservation excludes it). The per-request approval that a session used to give was never
    judgement — it was bookkeeping over "is the region free" plus "does policy allow it" — so
    it is mechanized, and a policy file cannot be asleep. AutoKernel, AutoPilot, the inference
    session and pool workers are all symmetric consumers; none of them is the owner. (D4 as
    amended by the operator, 2026-08-15/16.)

    *Mechanism.* A consumer writes a `compute-request` message to its own outbox
    (`kind: compute-request`, `needs_routing_to: [coordinator-daemon]`, payload names task +
    window + device/region + est_h + release-condition). The coordinator-daemon grants or
    denies it deterministically against `compute_policy.yaml` — `compute-grant` (window
    accepted, boundaries stated) or `compute-deny` (refused, reason + what to do next) —
    relayed to the requester's inbox. A request the daemon cannot decide is denied with
    `needs-operator` and ages into an alarm; it is never left pending in silence. A request
    is never blocked on the bus; work on non-compute rows continues meanwhile. An
    unauthorised `compute-request` (from an agent without a roster row, or one that bypasses
    the relay) is still rejected with a `defect`. This rule subsumes the older
    *"one main owns compute; everyone requests from `inference`"* language AND the earlier
    *"release at your next boundary if inference asks"* language: windows are granted by the
    policy, not assumed from any session. The `inference-batch/LOOP_PROTOCOL.md` quiet-window
    gate and the `hardware_backfill.py` "only wedge into a gap the policy releases" contract
    are the execution-side instruments of this same ownership.

    > **Amended 2026-08-16 per D4 (operator):** compute owned at the coordination level as
    > policy data — see `compute_policy.yaml`. The daemon executes grants deterministically
    > (region free ∧ policy allows); no session owns compute.

12. **SPECIAL ROLE ROUTING IS EXPLICIT.** The audit role is excluded from generic backlog
    scheduling and accepts only a coordinator-routed audit packet for completed `mainA`–`mainD`
    work. Its verdict never directly assigns or messages the source main; handoff follow-ups
    return through coordinator dispatch. Inference Main owns advisory resource scheduling for
    inference-gated work. A typed resource lease is distinct from a task assignment and from the
    physical claim; model and effort are never part of either role's identity or lease validity.
    (Since P3-7 the audit role is a headless per-packet invocation under the `auditor` identity
    rather than an interactive session — `agents/auditor-main.md`. The routing rule is unchanged.)

13. **PERSISTENT IDLE IS ROUTING INPUT.** `fleet_watch` supplies the persistence-gated CPU/GPU
    receipt; coordinator-agent supplies priority and routing; Inference Main supplies the execute
    or lease decision. None may replace the others or infer a physical claim from observation.

### Audit and compute-resource wire contracts

- A successful `task-complete` from `mainA`–`mainD` deterministically creates one linked
  `audit-request`, keyed by source task plus completion-message id. `role_rollout.audit_completion`
  selects the default and is `shadow`: the source keeps its existing terminal semantics while audit
  coverage is measured. Each audit row captures that choice in immutable `audit_policy` plus an
  `audit_question`, so later config changes cannot alter work already sent for review. `required`
  changes the source to `DONE_PENDING_AUDIT` until an `audit-verdict` of
  `accept`, `accept-with-followups`, `needs-rework`, or `blocked-evidence` is transcribed. Verdicts
  address coordinator-agent only; the original main is provenance, never an assignee or CC.
- Compute-resource messages are `resource-lease-request`, `-grant`, `-decline`, `-activate`,
  `-renew`, `-revoke-request`, `-draining`, `-release`, `-cancel`, and `-expire`. The reconstructible
  lifecycle is `REQUESTED → RESERVED → ACTIVE → DRAINING → RELEASED`, with terminal alternatives
  `DECLINED`, `CANCELLED`, and `EXPIRED`. Only `inference` grants, renews, declines, or expires a
  resource lease. Coordinator-agent may request cooperative revocation; it cannot grant one.
  (Amended 2026-08-16 per D4: the daemon's deterministic grant against `compute_policy.yaml`
  is the coordination-level grant path; this `resource-lease-*` lifecycle is the typed wire
  vocabulary for the active lease once granted — the two remain compatible because the policy
  file is what authorizes any `-grant` the daemon or its delegated executor writes.)
- Every compute-resource event is addressed/actionable (`assignee == to`). Requests and grants name
  exact CPU regions and/or GPU devices and the finite task batch. A CPU+GPU request is atomic.
  Activation requires provider-qualified physical claim-open receipts (`region-lock` for CPU and
  the configured device claim for GPU); release requires matching claim-close receipts. An
  unactivated reservation may expire. An active lease must use revoke, drain, and release, so an
  expiry never steals a live physical claim. The current config disables delegated GPU grants until
  a general GPU claim provider is selected and enabled.
- `role_rollout.resource_leases: observe` records and routes this protocol without changing task
  admission. `enforce` requires a non-Inference executor to hold a matching live Inference-issued
  reservation before an inference-gated task can be assigned. The physical claim remains a second,
  separate prerequisite before execution.
- `compute-idle` carries the watcher receipt path and exact receipt line, separately for `cpu` and
  `gpu`. One message is emitted per persistence episode. `persistent_idle_routing: observe` reports
  to coordinator-agent; `route` additionally assigns the episode to Inference Main for an execute,
  lease, or queue-empty disposition.

## Standing instructions change under running sessions

An agent's instruction set is loaded at session start. Editing `CLAUDE.md` / `AGENTS.md` therefore
does **not** reach a session already running (origin: 2026-07-27 — appendix).

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

Routing intent that lives as prose inside `payload` does not survive a context-economy truncation,
and no tool can know better (origin: two missed messages, 2026-07-29 — appendix). Therefore:

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

## ONE assignee per action; everyone else is `cc` (2026-08-12)

`action_required` applied to **every** member of `needs_routing_to`, the schema had no way to say
*"read this, you owe nothing"*, and the relay re-addressed every fan-out copy — so a CC was
structurally indistinguishable from an assignment, and a triage queue that is mostly other people's
work stops being read (measured 2026-08-12 — appendix).

**The fields.**

- **`assignee`** (top-level, ONE roster id): the single party that must ACT. `append` refuses a
  non-roster or retired id, and refuses an agent that is also on `cc`.
- **`cc`** (top-level, array of roster ids): **reach-only**. Never implies an action, never owes an
  ack or a disposition, cleared by advancing your cursor.
- **`cc_delivery`** (tool-written): the relay stamps it on a CC copy. **A CC copy PRESERVES the
  original `to`**; only the assignee's copy is re-addressed. If `to` is not you, the message is not
  yours.
- `needs_routing_to` keeps working for history. A **single-entry** list still resolves as the
  assignee; a multi-entry one is FYI for everyone, because a request N agents share is a request
  none of them owns.

**The refusal** (`append`, fail-closed, beside the existing `to: '*'` refusal):

> `action_required` with more than one routing target — **one assignee per action; N agents each
> owing a distinct action = N messages; reach-only readers go in `cc`.**

The compliant rewrite is in the error text: set `assignee: "<one roster id>"` and move the rest to
`cc`. Do not "fix" this by dropping `action_required` from something that really is a job.

**`drain --triage` splits the output.**

| Section | What it is | What you owe |
|---|---|---|
| **MUST-ACT** | you are the `assignee` (or the sole legacy target) | full body, fenced, truncation-evident; **a disposition from your own outbox** (rule above) |
| **FYI** | `cc`, or a broadcast several agents received | **one line each. No disposition. No ack.** A `cc` clears when you advance your cursor |

A row addressed to you *alone* still gets full detail even without an `assignee` — the collapse to
one line is for mail you received because it went to everyone.

**Linter symmetry.** The prose lint no longer fires on a row carrying `corr_id`/`corr_ids` or of
`kind: ack`: a disposition **quoting** the request it answers is not a new request, and telling its
author to set `action_required` would re-arm the item it was clearing. The missing opposite
polarity now exists: a `finding` / `status` / `task-complete` with `action_required` and more than
one target warns **"this looks like FYI; use `cc`"** (the old one-way lint — appendix).

**Migration is authoring-side only.** All existing history stays valid, `validate` warns and never
fails on a legacy row, and the relay keeps delivering pre-migration rows unchanged.

## A dispatch is TYPED (AUD-2, 2026-08-12)

With no vocabulary, no content rule about a dispatch was mechanizable — prose addressed to the
author is not a channel tools act on (AUD-2 — appendix). The `task-assign` payload now has one:

| Field | Status | Why |
|---|---|---|
| `task_text` | **REQUIRED** (enforced in `cmd_append`) | the dispatch IDENTITY — the row's TEXT: `file.md:LINE` names a different row every few weeks (anchor rot — appendix) |
| `row_ref` | optional **hint** | demoted from identity. When it disagrees with `task_text`, the text wins; re-resolve with `backlog_row_check.py --row "<text>"` |
| `screened_by` | receipt | evidence `backlog_row_check` RAN. It proves WELL-FORMED, not STILL-NEEDED — verify the premise too (screening — appendix) |
| `expected_occupancy` | `{est_h, basis, gating}` | nothing in an untyped dispatch made an occupancy mismatch expressible. Declaring it forces the question at composition time (F-14 — appendix) |
| `constraints[]` | each entry needs a **`source`** | a restated constraint cites the line it derives from, or it is the author's recollection wearing the roster's authority (F-20 — appendix) |
| `brief_path` | required past the size cap | draft-7 has no size keyword, so the cap lives in `cmd_append`: a payload over `TASK_ASSIGN_PAYLOAD_MAX_BYTES` with no `brief_path` is **refused**. A dispatch too big to read in a triage report belongs in a file |

Missing `task_text` and oversize-without-`brief_path` are **refusals**; keys outside the vocabulary,
a prose `constraints` string, and absent `screened_by`/`expected_occupancy` are **warnings** —
refusing those mid-flight would move the failure rather than fix it. Gated on `kind == task-assign`;
no other kind acquires these duties. **The daemon obeys the same vocabulary**: it emits
`task-assign` under authority `assign` and populates every field from the queue row
(`_task_assign_payload`), because a typed dispatch only humans have to fill in is a rule with a
hole in it exactly where the volume is. `queue.jsonl` therefore carries `task_text`, `screened_by`
and `expected_occupancy`, transcribed at intake from the `task-propose` payload (`summary` is the
fallback row text).

## The AUTOMATIC dispatch gate (R-16 option B, Phase 6, 2026-08-12)

The daemon's between-turns tick MAY dispatch from its `assign` authority, but **only
deterministically and only for a queue row that carries the AUD-2 evidence above**. It never
dispatches on discretion. `dispatch_gate()` in `session_bus_coordinator.py` refuses with one of
exactly two codes, kept apart because each is fixed by editing a **different** field:

| Code | Condition | The measured failure |
|---|---|---|
| `unscreened` | no `screened_by` on the queue row | nothing in the pick path had ever re-derived whether the rows it picked were still real (the overnight pick storm — appendix) |
| `no-occupancy-estimate` | no usable `expected_occupancy.est_h` (absent, unparseable, or ≤ 0) | a card was fed seconds-long work while every occupancy instrument read idle (F-14 — appendix) |

A refused row is **reported, never skipped**: one `dispatch-refused` advisory row per row per tick
(not per agent — per-agent emission is how 9 rows became 4,602 records), naming the `task_id`, the
code and the reason. It is also excluded from the automatic candidate set, so the dispatchable row
behind it is not starved; and the write path re-checks the gate, so routing around the pick cannot
land an assignment. Occupancy resolves through `session_bus.row_occupancy_h` — the single
definition shared by the gate, the pick ordering and the drain depth line, so the three readings
cannot disagree.

**Human/coordinator-authored dispatch through `append` is unchanged** (warn-only). A human who
reads the warning and proceeds is making a judgment; an autonomous tick is not allowed to.
fleet_watch stays detect-only per its own contract.

**Pick ordering** (`_pick`, deterministic, readable off one sort tuple): `priority` rank first,
then **larger `expected_occupancy.est_h` first** — between otherwise-equal candidates the daemon
prefers the deeper work, because a tick that hands an idle main six minutes of work leaves it idle
again inside the same tick interval while the fleet reads busy — then `task_id` as the tiebreak.

**At the boundary**, `drain` prints READY depth per lane plus the summed `est_h` of everything
in flight (`ASSIGNED`/`CLAIMED`/`RUNNING`). An in-flight row with no estimate is counted and named
as **unknown depth, never folded in as zero** — summing it as 0 would make a loaded fleet read
empty, which is the reading the line exists to replace.

## Corrections are typed, so an omitted one is visible (AUD-4, 2026-08-12)

A correction that looks like any other `finding` cannot be enumerated, so an omission is invisible
on both sides (origin: 2026-08-12 wrap-up — appendix). A `finding` payload may now carry:

- **`corrects: <msg-id>`** — the message this finding corrects.
- **`provenance`** — `operator-verbatim` | `paraphrase` | `inferred`. A correction whose standing
  is unstated gets read as the operator's own words.

`python3 scripts/coordination/session_bus.py corrections --agent <id> [--since <ts>]` generates the
wrap-up corrections section from your own outbox. A correction that is not in the section is now a
diff, not a memory lapse.

## `drain` carries the boundary checks (AUD-3, 2026-08-12)

`drain` is the role's **one proven checkpoint** — Guardrail 1 makes it mandatory at every task
boundary, which makes it the only place a check is certain to run. Every drain, empty or not, now
prints three readings to **stderr** (stdout stays JSONL):

1. **`scripts/` hygiene** — untracked/modified counts from one `git status --porcelain -- scripts/`.
   Agent infrastructure rotting uncommitted in a shared tree is invisible until someone else's
   pathspec commit sweeps it up or a checkout reverts it with no reflog.
2. **`action_required` rows YOU owe, WITH AGE.** The machinery already knew them; it never said how
   old they were, so a two-week-old unanswered request read exactly like this minute's.
3. **The last `COMPUTE-IDLE` / `IDLE-CANDIDATE` line** from `logs/fleet_watch.log`, verbatim, with
   its path **and a log-mtime staleness guard**. The guard is mandatory: fleet_watch runs
   unsupervised, so its log going quiet is indistinguishable from a busy fleet, and relaying a
   stale line as current is the exact failure class this refactor exists to close.

Each is best-effort and never fails the drain — but *best-effort* is not *silent*: a check that
cannot read its input says `UNREADABLE` / `UNKNOWN` / `STALE`, because a missing reading rendered as
a clean one is the same failure wearing a different hat. `--no-boundary-checks` exists for tests and
non-interactive callers; an agent at a task boundary wants them.

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
sees them at its next drain (defect C8, 2026-07-28).

### Unreachable idle session (stale heartbeat, guard refuses nudge)

`tmux_adapter.py nudge` refuses to nudge a target whose heartbeat still reads `working`, even if
the target actually finished and is now idle and blocked waiting for input — it cannot refresh
its own heartbeat while blocked, so the guard's refusal and the target's silence reinforce each
other into a deadlock. `--heartbeat-max-age` does not help: the refusal keys on heartbeat state,
not age. Do not bypass the guard with raw `tmux send-keys`.

A refusal is a snapshot, not a verdict: run the authoritative instrument first —
`tmux_adapter.py probe --agent <id>`, the runtime check — and **never conclude idle from pane text
alone**, because a session is working, compacting or idle and a compacting pane renders
identically to a finished one (a mid-generation session is not blocked, and the guard is correct).
Then keep re-probing rather than escalating immediately — most refusals self-clear (quiet-check
~20s, nudge rate limit 600s, `working` heartbeat clears at the session's own next boundary).
Escalate to the operator only once the block outlives the longest plausible self-clearing timer
(10-15 minutes of continuous refusal with no pane activity) AND something is actually waiting on
that session. Never busy-wait or bypass while probing; do other coordination work between probes
(rule 2 covers blocking on a human too). Full rule: `agents/shared/SESSION_LIFECYCLE.md` →
*Reading another session's liveness*. Full procedure, threshold reasoning, and origin incident:
`agents/coordinator-agent.md` → Guardrails.

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

## Operator items are DECLARED, not inferred (C49, 2026-08-12)

"Unread `token-request` / `defect` / CRITICAL" (the C20 predicate above) is **superseded.** It and
`action_required` are near-disjoint sets that misclassify in both directions, and what it caught was
`kind: defect` — fleet-internal engineering work — never a `token-request`, the only kind that
genuinely means a human must sign something (measured 2026-08-12 — appendix).

An item reaches the operator if, and only if, one of two things is true:

- **`kind: token-request`** — a token IS the operator's signature, so this kind is an operator gate
  by definition and needs no additional marker.
- **`payload.operator_signature_needed: true`** — set deliberately by the author. This is the only
  way any other kind reaches the operator.

Three things this deliberately is NOT:

- **`action_required: true` does NOT reach the operator.** It means the routed-to agent(s)
  (`needs_routing_to`, else a concrete `to`) must act — see "Routing intent is structural, not
  prose" above. Most `action_required` traffic is one main asking another to do something; the
  operator is not in that loop by default.
- **Urgency is not operator-ness.** `severity`/`priority: CRITICAL` means act soon, not "a human
  must decide." An urgent engineering item still routes to an agent unless the marker is set.
- **`kind: defect` is not, on its own, an operator item.** It is fleet-internal engineering work,
  even at CRITICAL severity. If a defect genuinely needs a human's call, set
  `payload.operator_signature_needed: true` on it explicitly — the kind alone no longer implies it.

Enforced by `_is_operator_item()` in `scripts/coordination/session_bus_coordinator.py`, which the
C19/C20/C27 escalation paths above all call: a message without the marker and without
`kind: token-request` will not reach the last-hop escalation, no matter how urgent it looks. An
agent can no longer escalate to the operator by owing itself a next step.

## Gate presentation is transport, and transport runs at every authority (C27, 2026-07-29)

Two well-formed operator SIGNATURE REQUESTS were never presented to anyone while `token-queue.md`
read *"Pending token requests: (none)"*, so **a coordinator following the documented cold start
exactly would conclude no gates were waiting.** Not a lost message — a lost request for a human
signature. Cause: an exclusion justified by a handler the configured authority never reached
(C27, 2026-07-29 — appendix).

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
items, that produces N byte-identical messages (origin: C23, 2026-07-29 — appendix). This is
**protocol shape, not a send bug**: N distinct corr_ids, N distinct ids, relayed 1:1. Do not
"fix" it in `tmux_adapter.py`.

**The 2026-07-29 rule was NOT PERFORMABLE, and is replaced (C23, 2026-08-11).** It said *"before
writing the same payload against a second `corr_id`, write it once and reference it"* — while no
mechanism to reference it existed. Clearing triage took one `corr_id` per item, full stop, so a
session holding one answer for N items had no compliant way to send it once, and it failed within
hours (full record: `handoffs/active/session-bus-thin-dispatcher.md` → C23).

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
operator decision, and without it the join has no ground truth (an earlier receipt-less attempt
mis-flagged most of the scripts it scanned — appendix).

## Typed checkpoint, audit, integration, and wrap lifecycle (RTG-51)

The JSON schema is the executable wire contract for these kinds; their payloads are closed objects
(`additionalProperties: false`). A worker main sends one `task-checkpoint` to
`coordinator-agent` at a task boundary. Its `boundary_id` is the worker's idempotence key and the
message names the exact queue task text/spec reference, lane branch and remote-tracking ref, pushed
commit, committed per-agent progress shard, handoff/artifact paths, actual changed paths, checkbox
transition, validation receipts, and next-context classification. `blocked` and `partial` add typed
blocker evidence; `partial` is restricted to `pre-reboot`.

At `assign` authority the daemon admits the receipt fail-closed. It checks the roster author and
queue owner, exact task identity, `lane/<agent>` and `origin/lane/<agent>` identity, SHA reachability,
exact commit path equality, worker-owned surfaces, and the committed progress/handoff evidence.
Invalid receipts are quarantined as defects and never create audit or integration state. A valid
receipt moves the source to `DONE_PENDING_AUDIT` and creates exactly one deterministic audit row.
When a linked legacy `task-complete` exists, its message id is the shared correlation key, so the
old completion path cannot create a second audit.

The daemon sends the Auditor a typed `audit-request`; only `auditor` may return the linked
`audit-verdict`, and the verdict must repeat the source task, correlation, and audited SHA. Only
`accept` and `accept-with-followups` produce `integration_state: ready` and a typed
`checkpoint-integration-ready` notice. `needs-rework` returns the source to ordinary
`STALE_REQUEUED` Coordinator routing. `blocked-evidence` leaves the source pending and sends the
worker an `evidence-only` audit request: it asks for missing proof, never implementation rework.
All notices are deduped by correlation/checkpoint identity, so replay and daemon restart are safe.

`wrapup-request` is Coordinator-to-Auditor and names a cutoff, synchronization mode, included
checkpoint ids, and integrated main SHA. `wrapup-complete` is Auditor-to-Coordinator and records the
included/excluded boundaries, source/promoted SHAs, generated artifacts, validations, wiki result,
and serialized lease operation. Those message kinds establish authority and durable linkage here;
the wrap implementation remains separately staged. (Since P3-7 the `auditor` end of these kinds is a
headless per-packet invocation, not an interactive session; the wire contract is unchanged.)

### Compute-blocker intake and graded compute windows (RTG-51, 2026-08-23)

Two kinds close the compute-ready loop described in
`handoffs/active/wrap-up-division-of-labor-policy.md` ("Compute-blocker intake and graded window
contract"):

- `compute-blocker` is ONE kind with two event classes, never an in-place edit. The initial
  forward (`state: submitted`) is authored by `coordinator-agent` and types the worker's own
  free-form `compute_request` from an accepted compute-class `task-checkpoint` receipt into
  `requirements`; it names the receipt (`checkpoint_ref`, `checkpoint_sha256`). Every later event on
  the same `blocker_id` is an Inference-authored disposition through
  `submitted -> admitted|duplicate|needs-info|rejected -> ready -> planned -> granted|denied ->
  running -> terminal`, each carrying `reason_code`, `prior_event_id` (the previous `compute-blocker`
  message id) and `checkpoint_event_id` (the submission's message id). Status changes are NEW
  messages; no field of an earlier message is ever rewritten.
- `compute-window` is authored by `inference` only and announces a graded window
  (`small-model-only | load-then-keep-hot | full-idle`) with `eligible_devices`,
  `cpu_bandwidth_class`, `gpu_vram_available` (bytes plus observation refs), `resident_model`
  (identity or null), `load_allowed`, window `starts_at`/`expires_at`, `time_budget_seconds`,
  `safe_drain_at`, `observation_refs`, and the planner-core inputs `eligible_model_ids` and
  `max_model_bytes`. A window grade is a compatibility label, never a total ordering, and the
  announcement never substitutes for the typed resource lease.

`scripts/coordination/compute_ready_daemon.py` rebuilds
`coordination/session-bus/compute_ready.json` (derived runtime state; never hand-edited) from the
accepted receipts in the coordinator inbox, the `compute-blocker` forwards/dispositions in the
coordinator and inference outboxes, and the `compute-window` events in the inference outbox, by
invoking the landed pure planner core (`scripts/coordination/compute_ready.py`) unchanged. A
forward whose receipt is absent, whose envelope hash disagrees, or whose receipt is not a
compute-class blocker fails closed; the projection is reconstructible from bus records alone.
Rollout for the checkpoint receipts, the wrap, and the compute plan is gated by
`coordination/session-bus/rtg51_rollout.yaml` (off | shadow | enforce), read by
`scripts/coordination/rtg51_rollout.py`; shadow records findings and never rejects legacy behavior.

## Appendix — incident record (not instructions)

Nothing below is a directive; it is the evidence the rules above were derived from, kept here so
the instruction path stays short. The full ledgers are
[`handoffs/active/coordinator-role-failure-modes-and-refactor.md`](../../handoffs/active/coordinator-role-failure-modes-and-refactor.md)
(R-/AUD-/F- series) and
[`handoffs/active/session-bus-thin-dispatcher.md`](../../handoffs/active/session-bus-thin-dispatcher.md)
(C-/H- series).

### 2026-07-27 — standing instructions do not reach running sessions

Observed 2026-07-27, when a heartbeat-refresh rule was added at 21:43Z and a demonstrably active
agent was still on its 19:45Z heartbeat afterwards. (Ledger: `session-bus-thin-dispatcher.md` M5c.)

### 2026-07-29 — routing intent as prose

Two routed messages were missed on 2026-07-29 because routing intent lived as prose inside
`payload` ("FOR FABLE-AUDITOR …" in a defect string; "action: DOC FIX requested … relay") and a
context-economy payload truncation cut exactly the sentences carrying it. No tool could have known
better.

### 2026-08-12 — CC indistinguishable from assignment

Measured across the fleet's inboxes on 2026-08-12: **499 `action_required` rows, only 86
sole-target — 83% of what an agent had to triage was not its own** (73–89% per agent). Compounding
it, the relay set `msg["to"] = target` on every fan-out copy, so **100% of delivered rows looked
directly addressed**. A triage queue that is 83% other people's work stops being read, and then the
17% that *was* yours is lost too.

### 2026-08-12 — the one-way lint

The old lint only ever pushed the bit ON, which is half of how 499 rows accumulated with 86 sole
targets.

### AUD-2, 2026-08-12 — an untyped dispatch payload

Measured: **171 distinct payload keys across 55 `task-assign` messages.**

### Anchor rot, 2026-08-11 — `file.md:LINE` is not an identity

Anchor rot measured **34.5% queue-wide** on 2026-08-11 (27% twelve days earlier).

### Screening, 2026-08-12 — well-formed is not still-needed

Four of eight rows screened on 2026-08-12 were already satisfied.

### F-14 — dispatched shallow

Seconds-long work was queued at a card that needed hours, and nothing in the dispatch made the
mismatch expressible; a card was fed 40-second sweeps while every occupancy instrument read idle.
(Ledger: `coordinator-role-failure-modes-and-refactor.md` F-14.)

### F-20 — an invented roster constraint

A brief asserted `lanes: [none]` the roster never imposed. (Ledger:
`coordinator-role-failure-modes-and-refactor.md` F-20.)

### 2026-08-11/12 — the overnight pick storm

Overnight 2026-08-11/12 the tick emitted **4,602 would-assign picks resolving to 9 distinct rows
from ONE file** — nothing in the pick path had ever re-derived whether those rows were still real.

### AUD-4, 2026-08-12 — five omitted corrections

Five corrections were silently missing from the 2026-08-12 wrap-up — not because anyone decided to
omit them, but because a correction looked like any other `finding`, so nothing could enumerate
them and the omission was invisible on both sides.

### C49 / C20, 2026-08-12 — operator items were inferred, and wrongly

Measured 2026-08-12 over 267 live inbox rows: 116 carried `action_required` (which means a NAMED
AGENT must act next, never the operator), only 8 satisfied the old C20 predicate, and just 7
overlapped — near-disjoint sets, misclassifying in both directions. Every one of those 8 was
`kind: defect`, and **not one was a `token-request`**. The daemon had escalated "11
operator-decision items unread past deadline"; a parse of all 17 found **zero** genuine operator
items.

### C27, 2026-07-29 — two gates never presented

`RATIFY-P-BENCH-4-FG4B-AFFINITY-20260729` (10:18Z) and
`RATIFY-E8-FINAL-C1-RETRY-CAPACITYFIX-20260729` (11:16Z), both `needs_routing_to:
[coordinator-agent]`, both `action_required`. Cause: `relay_tokens`, the only writer of gate
blocks, ran only inside `apply_assignment` (`authority: assign`) while the live config is `manual`;
and `token-request` was excluded from the always-on relay *because `relay_tokens` was named as its
handler*.

### C23, 2026-07-29 — a repeated payload is bus noise by construction

19 identical `triage-disposition-post-standdown` rows once made up 40% of a 48-item queue: 19
distinct corr_ids, 19 distinct ids, relayed 1:1. (The 2026-08-11 replacement measurement — nine
identical payloads in ten minutes from a main following the old rule correctly — is held in full
at `session-bus-thin-dispatcher.md` → C23.)

### BUS-GATE receipts — an unadopted join has no ground truth

An earlier attempt mis-flagged 11 of 25 scripts, because superseded and repaired scripts never
receive receipts.
