# Session Bus + Thin Coordinator — N-main-thread control structure

**Status**: DESIGN-RATIFIED (operator, 2026-07-27, plan-mode Q&A ×2) — build-ready; M1 skeleton is verbatim below. **Nomenclature revised 2026-07-27** (operator) — see §Nomenclature.
**Created**: 2026-07-27
**Priority**: HIGH — removes the operator-paste-buffer relay bottleneck measured all week
**Effort**: M1–M2 ~half day · M3–M4 ~1–2 days (incl. the 48h M4 soak) · M5 optional, flag-gated
**Categories**: coordination, governance, automation
**Parent index**: [master-handoff-index.md](master-handoff-index.md) (★ post-closure pivot block)
**Related**: [`../../coordination/inference-batch/LOOP_PROTOCOL.md`](../../coordination/inference-batch/LOOP_PROTOCOL.md) (contracts this extends) · [`../../coordination/inference-batch/op-bundle.md`](../../coordination/inference-batch/op-bundle.md) (token-queue pattern) · [heterogeneous-slot-fabric-residency.md](heterogeneous-slot-fabric-residency.md) + the ratified fabric contract (convergence target) · CLAUDE.md §Long-horizon throughput contract + `agents/shared/MEASUREMENT_POLICY.md` §Consolidated apply-time ratification (the policies this mechanizes)

---

## Nomenclature (operator, 2026-07-27) — one role, two tiers

The original "dispatcher" / "meta-main" pair read as **one** thing from the operator seat and
**two** things in this document, and the two readings collided in design discussion. Resolved as
one logical role with two runtime tiers:

| Term | What it is | Authority |
|---|---|---|
| **coordinator** | the role the operator interacts with | — |
| **coordinator-daemon** | `session_bus_coordinator.py`; host-side, `nohup`+flock singleton, tick loop, epoch fencing, heartbeat; **not** an agent session | transcribes, validates, assigns by deterministic rule; **never** sets priorities, never reviews work products |
| **coordinator-agent** | an agent session with a roster row, inbox/outbox/heartbeat/cursor | decision packages, operator-intent relay, cross-main reprioritization, lease grants, integration |

The split is forced by runtime requirements, not preference: an always-on watchdog cannot be an
LLM (it compacts, dies, costs tokens per tick), and deterministic code cannot draft decisions or
merge. The split is also what makes coordinator integrity solvable — the daemon outlives the agent
and is the only component positioned to audit it deterministically.

**Old → new**: `dispatcher` → `coordinator-daemon` · `meta-main` → `coordinator-agent` ·
`session_bus_dispatcher.py` → `session_bus_coordinator.py`.

**The filename `session-bus-thin-dispatcher.md` is deliberately unchanged** — it is referenced by
`master-handoff-index.md` and by a `progress/` entry, and progress files are historical records
that are appended to, never rewritten.

## Executor start here

Zero inference throughout. Build **M1 verbatim from §Skeleton** (files + schema + CLI), run the
M1 manual round-trip acceptance, then M2→M4 in order. Every M5 item is independently
flag/grant-gated — do not build any of them until its gate is granted. The coordinator-daemon NEVER
analyzes, reviews, or edits work products — queue/routing/watchdog only ("the moment it
reviews, it's a second main" — operator).

## Why

- The operator ran multiple agent main-threads (Codex long-horizon, Claude oversight, others)
  coordinated **through their own paste buffer** — relay latency, false serialization (bench
  work gated behind unrelated token chains), and idle hardware during governance turns.
- Now-binding policies this structure mechanizes: zero-idle compute + saturation scheduling +
  boundary-tokens-only-while-saturated (CLAUDE.md `401f4a36`), consolidated apply-time
  ratification + pre-validated operator commands (`MEASUREMENT_POLICY.md`), run-first bias.
- Operator decisions (2026-07-27): build now at N=2 mains but **roster-driven N-main from day
  one**; **hybrid runtime** (deterministic core + capped one-shot triage); Codex consumption
  via boundary drain (send-keys OFF behind grant); operator interface = a **coordinator-agent**
  thread; authority matrix below.

## Components

| Component | Runs where | Cloned from |
|---|---|---|
| **Session bus** (files) | `coordination/session-bus/` | `coordination/inference-batch/` (ledger + op-bundle) |
| **Coordinator-daemon** `session_bus_coordinator.py` | host, nohup+flock (or tmux window in session `agent`) — NOT inside any agent session | `hub_supervisor.sh` loop discipline + `batch_ledger.py` fold |
| **Bus library/CLI** `scripts/coordination/session_bus.py` | called by coordinator-daemon AND agents | `batch_ledger.py` / `batch_status_report.py` |
| **Watchdog-of-coordinator-daemon** `scripts/coordination/bus_supervisor.sh` | host, nohup+flock | verbatim `hub_supervisor.sh` clone (health = coordinator-daemon heartbeat mtime) |
| **Coordinator-agent** (operator-facing coordination agent) | an agent session (today: the Claude oversight session, formalized) | the role this week's session performed ad hoc |
| **Hub visibility** `/api/bus`, `/api/queue`, `/bus` page | `dashboard/server.py` (:8100) | `/api/kernel` external-contract pattern |
| **Triage hook** (M5, flag-gated) | coordinator-daemon subprocess, one-shot `claude -p --model haiku` via `claude_via_devc.sh` | nightshift budget caps |
| **Codex nudge adapter** (M5, grant-gated OFF) | coordinator-daemon → `tmux send-keys -t agent` | new, deliberately tiny |

**Coordinator-agent** (operator decision Q3): a first-class bus participant (roster role `coordinator-agent`,
own inbox/outbox/heartbeat/cursor) responsible for parallel-thread coordination — presents
token requests + decision packages to the operator, relays operator intent onto the bus,
monitors/audits mains, handles all unstructured coordination the deterministic coordinator-daemon
cannot. `tokens/token-queue.md` stays the durable substrate; coordinator-agent is its presenter.
FUTURE seam (explicitly out of scope now): expose the coordinator-agent thread as a dedicated
phone-accessible chat.

**Deployment note**: the coordinator-daemon needs host visibility (`inference_load_check.py`,
`rocm-smi`, pgrep, optionally the host tmux server) — run it host-side like
`hub_supervisor.sh`. Repo paths are the shared mount, so container agents read/write the same
bus files.

## File layout

```
coordination/session-bus/
  BUS_PROTOCOL.md              # single-writer + claim + ack contract (LOOP_PROTOCOL analog)
  config.yaml                  # roster (N mains + coordinator-agent), lanes, authority matrix,
                               # thresholds, flags (codex_sendkeys: off, triage: off), caps
  config/routing-table.yaml    # task-class → (main, model-tier, effort) data artifact
  session_bus.schema.json      # Draft-07 schema: msg + queue rows
  queue.jsonl                  # WORK QUEUE — single writer: COORDINATOR-DAEMON
  inbox/<agent>.jsonl          # single writer: coordinator-daemon
  outbox/<agent>.jsonl         # single writer: that agent
  tokens/token-queue.md        # op-bundle clone; agents author blocks, coordinator-daemon relays,
                               # coordinator-agent presents, operator flips [x] GRANTED <date>
  heartbeats/<agent>.json      # atomic overwrite (tmp+rename), one file per writer
  cursors/<agent>.json         # per-consumer read offsets (byte offset per inbox file)
  archive/                     # rotation, coordinator-daemon-owned files only, only past all cursors
```

Single-writer is **structural**: one writer may own many files; no file has two writers.
**Adding a main = 1 roster row + 4 files** (inbox/outbox/heartbeat/cursor). Codex and
claude-main are merely the first two roster entries (operator: N-main is routine, not future).

## Schemas

### `session_bus.msg.v1` (all bus jsonl)
`schema_version, id ("msg-<ts>-<seq>-<writer>", sortable), ts, from, to` (roster ids or `*`),
`kind ∈ {task-assign, task-complete, status, finding, decision-request, token-request, ack,
nudge, defect, requeue, reprioritize, saturation}`, `corr_id, task_id, requires_ack,
ack_deadline_s, priority, payload` (kind-specific, schema-validated).
Key payloads:
- `task-assign`: `{spec_ref|inline_spec, lane, lease_expires_ts, epoch}`
- `token-request`: `{gate_id, block_ref, validated: {cmd, dry_run_exit, dry_run_evidence}}` —
  **pre-validation mandatory**; an operator command that fails ⇒ `defect` row attributed to
  the requesting agent (policy).
- `decision-request`: full pre-formed Gate/Evidence/Options A–C/Recommendation block authored
  by the **agent**; coordinator-daemon relays verbatim.
- `reprioritize`: `{task_id, new_priority, scope}` — validated against the authority matrix;
  unauthorized ⇒ rejected + `defect` row.

### `session_bus.queue.v1` (`queue.jsonl`; latest-row-per-task_id-wins fold, = `batch_ledger.reconcile`)
`batch_ledger.v2` fields plus: `lane ∈ {cpu, gpu, none}` (none = code/doc work, always
schedulable), `contention_class` (reuses quiet-window semantics), `origin, status ∈ {READY,
ASSIGNED, CLAIMED, RUNNING, DONE_PASS, DONE_MARGINAL_OBS, FAILED, INFRA_BLOCKED, HELD_OP_GATE,
STALE_REQUEUED, CANCELLED}`, `depends_on[], operator_gates[], priority, est_wall_clock_h,
owner, assign_msg_id, epoch` (coordinator-daemon generation counter, fencing), `claim_ts,
lease_expires_ts, heartbeat_grace_s, attempt, max_attempts, spec_ref` (spec stays OUT of the
row), `findings[], artifacts[], era_stamp, failure_reason, routing_annotation` (from triage,
advisory only).
**Agents never write `queue.jsonl`**: they propose (outbox `finding`/task-propose) and report
(`ack`/`status`/`task-complete`); the coordinator-daemon transcribes — pure bookkeeping, no judgment.

### Heartbeat file
`{agent, ts, state: idle|working|draining, task_id|null, note}` — atomic overwrite.

## Protocols

### Task assignment (zero-idle path)
1. Coordinator-daemon tick (30–60s): fold queue + outboxes; lane snapshot (`classify_load()` +
   `mi210_state()` + heartbeats — a lane is idle only when ALL agree; fail-safe unknown=busy).
2. For each agent with no live CLAIMED/RUNNING task and <1 pending ASSIGNED (one-task
   lookahead): eligible = `READY ∧ depends_on terminal ∧ operator_gates GRANTED ∧ lane matches
   roster ∧ contention_class compatible with load class`; pick by priority (then
   stack-affinity, per pick-next-entry), consuming `routing_annotation` if present.
3. Append queue row `{ASSIGNED, owner, epoch, lease_expires_ts}` + inbox `task-assign`
   (requires_ack).
4. Agent drains inbox at its boundary (Codex: session-init/task boundary per the standing
   CLAUDE.md instruction added in M1; Claude mains: Monitor push or M5 Stop-hook) → outbox
   `ack` then `status RUNNING`.
5. Coordinator-daemon folds ack → CLAIMED → RUNNING rows. On `task-complete` → terminal row → next
   assignment. Lookahead means the agent's next boundary-poll already finds work — no idle gap.

### Decision-request → operator token (via coordinator-agent)
1. Agent hits a trust boundary → authors the FULL pre-formed block with the operator command
   **pre-validated** (dry-run evidence attached) → outbox `token-request` → agent CONTINUES
   with other eligible work (never blocks).
2. Coordinator-daemon relays the block verbatim into `tokens/token-queue.md`; gated tasks →
   `HELD_OP_GATE`.
3. **Presentation rule (saturation-gated)**: coordinator-agent presents pending tokens to the operator
   only while the saturation snapshot shows lanes busy — EXCEPT when a gate is the sole cause
   of imminent lane idleness, which forces immediate presentation.
4. Operator flips `[ ] → [x] GRANTED <date>`; next tick re-admits gated tasks.

### Stall ladder
- **soft-stall** (no outbox activity + stale heartbeat past lane-tuned grace; cpu/gpu grace
  derives from `est_wall_clock_h` — silence ≠ stall on bench lanes): inbox `nudge`
  (+ send-keys IF granted, rate-limited, idle-pane-checked).
- **hard-stall** (lease expired): `STALE_REQUEUED` (owner cleared, attempt+1) + `defect` row;
  task returns to READY for any capable main.
- **give-up** (attempts exhausted / heartbeat dead through ladder): alert block in
  token-queue + hub health red — operator/coordinator-agent decision, never the coordinator-daemon's.
- **coordinator-daemon-stall**: `bus_supervisor.sh` restarts with backoff; hub classifies coordinator-daemon
  heartbeat staleness.

## Authority matrix (config.yaml; deterministically enforced)

| Actor | Within own lane | Cross-main |
|---|---|---|
| main | reprioritize own-lane rows ✔ | ✘ (rejected + defect row) |
| coordinator-agent | ✔ | ✔ (reprioritize any; direct a main to reprioritize) |
| operator | ✔ | ✔ (via token-queue or coordinator-agent) |
| coordinator-daemon | never sets priorities — only transcribes/validates | — |

## Failure modes designed out

Coordinator-daemon dies → supervisor restart, agents degrade to no-new-assignments, files can't
corrupt. Split-brain → flock singleton + **epoch fencing** (restart increments epoch; stale
assigns ignored/flagged) + coordinator-daemon-only queue writes. Stale rows → leases +
STALE_REQUEUED + status-report flags. Message loss → append-only + requires_ack + redelivery
(same corr_id, consumer dedupe by id) + rotation only past all cursors. Codex ignoring inbox →
nudge ladder → (granted) send-keys → token-queue surfacing; hard-stalled tasks requeue to
other mains. Runaway spawn → config caps (`max_headless_workers`, `max_spawns_per_day`,
per-task wall budget) checked before any exec.

## Hybrid triage (operator decision Q1 — M5, flag-gated, budget-capped)

One-shot smallest-model subprocess (`claude -p --model haiku` via `claude_via_devc.sh`),
never resident, two duties ONLY:
1. **Dead-agent block drafting**: when an agent dies without authoring its decision block,
   draft one from log tails — output always marked `DRAFT-UNREVIEWED`.
2. **Task→tier routing annotation**: classify inbound task proposals against
   `config/routing-table.yaml` (task-class → main, model-tier, effort) and write an advisory
   `routing_annotation`. The table is **policy-as-data**: seeded manually from
   `feedback_subagent_model_effort_matching`; future: rebuilt from benchmarked episodic
   routing memory (the operator's original claude-tier task-benchmark concept, revived as a
   data artifact). Triage never assigns; the deterministic rule consumes annotations.
Bright line: the triage hook never reads or evaluates work products.

## Convergence with the orchestration stack (operator-requested)

| Orchestration stack | Session bus | Note |
|---|---|---|
| frontdoor + learned router | coordinator-daemon assignment + routing-table.yaml | both: routing = compiled policy-data; intelligence in endpoints |
| placement queue + contention matrix | lane sensing + saturation scheduler | bus reuses `classify_load` semantics read-only **for scheduling hints only — see R3: exclusion requires acquiring the region locks, not observing them (TOCTOU / axiom 1)** |
| slot leases (WP-12 fabric) | task claims + leases + epoch fencing | |
| op-bundle operator gates | tokens/token-queue.md | same grant lifecycle |
| model backends (fungible within role) | agent mains (**stateful — NOT fungible**) | requeue is lossy; leases tuned accordingly |

Fabric-contract consistency: the bus is pure policy-as-data (files/YAML/JSONL) — satisfies
*policy-data-never-code* by construction. Roster rows are **slot-shaped**
(`{id, role, lanes, capabilities, endpoint}`) so a future local-model main (hermes/opencode
agent served by the orchestrator) is just another row. **Defer triggers for unification**:
(a) a local-model long-horizon main exists, or (b) the slot fabric lands "everything is a
slot". Until then the stack contact is read-only sensing via `inference_load_check.py` — **plus** the
one exclusion primitive required by R1/R3: acquiring `cpu_region_lock` (via
`epyc-orchestrator/scripts/region-lock`) for any work that occupies CPU regions. Sensing informs
scheduling; only the claim provides exclusion.

## Skeleton (M1 — write these verbatim, then adapt)

**Directories**: `coordination/session-bus/{inbox,outbox,tokens,heartbeats,cursors,archive,config}/`

**`BUS_PROTOCOL.md`** (draft body):
```
# Session Bus Protocol v1
1. SINGLE WRITER: queue.jsonl + inbox/* = coordinator-daemon; outbox/<a> = agent <a>;
   heartbeats/<w> = writer <w>; tokens/token-queue.md blocks = coordinator-daemon relay,
   checkboxes = operator. No file ever has two writers.
2. NEVER BLOCK: no agent waits on the bus; work continues; grants/acks are picked
   up at the next boundary (op-bundle contract).
3. ACKS: requires_ack messages are redelivered as nudge (same corr_id) after
   ack_deadline_s; consumers dedupe by msg id.
4. CURSORS: each consumer owns cursors/<self>.json (byte offsets); never rewind
   another's cursor. Rotation (coordinator-daemon, own files only) only past ALL cursors,
   into archive/.
5. AUTHORITY: reprioritize scope per config.yaml matrix; violations are rejected
   with a defect row.
6. Trust boundaries unchanged: era rows, MEASUREMENT.md, baseline applies,
   production freezes, host reboots are HUMAN-ONLY. The coordinator-daemon sequences and
   the coordinator-agent presents; neither signs.
```

**`config.yaml`** (seed):
```yaml
schema_version: session_bus.config.v1
roster:
  - {id: codex,       role: main,      lanes: [cpu, gpu, none], endpoint: tmux:agent,   drain: boundary}
  - {id: claude-main, role: main,      lanes: [cpu, gpu, none], endpoint: monitor:file, drain: push}
  - {id: coordinator-agent,   role: coordinator-agent, lanes: [none],           endpoint: monitor:file, drain: push}
authority:
  within_lane: [self]
  cross_main: [operator, coordinator-agent]
coordinator-daemon:
  tick_s: 45
  lookahead: 1
  authority: manual        # manual (M1) | advisory (M3) | assign (M4)
  epoch: 0
flags:
  codex_sendkeys: off       # gate: OP-SENDKEYS-CODEX in tokens/token-queue.md
  triage: off               # M5
caps:
  max_headless_workers: 0
  max_spawns_per_day: 0
  triage_calls_per_day: 0
leases:
  none_lane_grace_s: 900
  bench_grace_margin: 1.5   # × est_wall_clock_h
```

**`session_bus.py` CLI surface** (clone fold semantics from `batch_ledger.py`):
`append` (schema-validated row → owned file) · `fold` (queue/outbox reconcile,
latest-per-task_id) · `validate` (whole-bus schema + single-writer lint) · `cursor`
(get/advance own cursor) · `status` (human summary: queue by status/lane, inbox depths,
heartbeat ages) · `drain` (print own inbox past cursor + advance; the one-liner agents run
at boundaries).

**M1 also includes**: the CLAUDE.md standing instruction (one line, near the throughput
contract): *"Bus drain: at every task boundary, run `session_bus.py drain --agent <id>` and
act on assignments/nudges; write acks/status to your outbox."* (Codex inherits via AGENTS.md
symlink — this IS the Q2 resolution; M1's acceptance validates it empirically.)

## Rider — resource admission & coordinator authority (operator-approved 2026-07-27)

Additive to M1–M5; each item names the milestone it attaches to. Origin: desk-time-reduction
plan, operator plan-mode Q&A ×4 on 2026-07-27.

**Framing correction adopted:** deciding what may co-run is *scheduling*, expressed as data and
enforced by the coordinator — **never** grounds for a human approval gate. Trust boundaries stay
human and are a short enumerated list (era rows, `MEASUREMENT.md`, baseline applies, production
freezes/cutovers, host reboots).

- [x] **R1 — CPU-region claim for benches (A0).** ✅ 2026-07-27 — Three disjoint exclusion domains
  existed over the same cores: orchestrator dispatch took per-region flocks, `run_benchmark.py`
  took its own flock in a different namespace, and `bench_canonical.sh` (the *sanctioned* path)
  took **none**. Closed via `epyc-orchestrator/src/runtime/region_lock_cli.py` +
  `scripts/region-lock` — a wrapper over the *same* `cpu_region_lock()`, holding regions for the
  child's lifetime; `bench_canonical.sh` derives its cpu list from the emitted canonical command
  and fails closed. Verified: contention serializes, SIGKILL releases (kernel fd-close), signals
  forwarded for drain, stale payloads never reported as holders.
  - [ ] **R1a — end-to-end bench claim never fired (open gap, inference-gated).** The wiring is
    verified structurally via `bench_canonical.sh --dry-run`, and contention was verified against
    *synthetic* holders. A real `llama-bench` has never acquired the claim, held it through a run,
    and released it. Closing this needs one short smoke run (e.g. `-n 128 -r 1` on a small model),
    which under the amended clause needs a held claim rather than an operator signature. Deferred
    by the operator 2026-07-27; until it runs, treat A0 as structurally-verified, not
    end-to-end-verified.
- [x] **R2 — retire per-run operator approval (A1).** ✅ 2026-07-27 — ratified and applied by the
  operator via `artifacts/operator/ratify_inference_gate_amendment_20260727.sh`
  (`OPERATING_CONSTRAINTS.md` → `bc290da2…`). M4's zero-idle acceptance is no longer gated on a
  human signature per lane refill. Draft/rationale retained at
  [`../../artifacts/operator/proposed_inference_gate_amendment_20260727.md`](../../artifacts/operator/proposed_inference_gate_amendment_20260727.md);
  **operator applies**. Blocks M4 — its 48h zero-idle acceptance is unachievable while every lane
  refill needs a signature. Must land *after* R1, never before.
- [x] **R3 — declare both subsystems instances of the ratified fabric contract.** ✅ 2026-07-27
  Both declared as instances in
  [heterogeneous-slot-fabric-residency.md](heterogeneous-slot-fabric-residency.md) with the
  five-part table and the axiom-1/axiom-4 consequences. `config.yaml`'s `co_residency` block
  carries the matrix's shape and an `expected_topology_hash` with `on_topology_mismatch: refuse`;
  `/api/bus` surfaces `co-residency-topology-drift` as an alarm.
  **Correction applied to §Convergence:** read-only sensing is not exclusion (TOCTOU) — anything
  occupying CPU regions acquires the locks (R1).

  **DRAFTING ERROR IN THIS ITEM, now fixed.** R3 originally said "promote declared classes toward
  measured ones", conflating two orthogonal axes: `contention_class`
  (`exclusive-contiguous | resumable`) is a **pausability** axis introduced by R5, whereas the
  contention matrix measures **per-role-pair co-residency** (15 measured pairs, allow/borderline/
  block against a 0.85 floor). They are not the same thing and one cannot be promoted into the
  other. The real gap the wording hid: the bus *referenced* the matrix in config but never
  *consulted* it — eligibility asked only the binary question "is the lane busy", which is
  strictly weaker than what the orchestrator already knows.

  **Now implemented.** Queue rows carry an optional `role_affinity` (the stack role whose resource
  profile the task resembles); the daemon maps `priority_class` → `TrafficClass` and consults
  `src.scheduling.contention.pair_policy()` against every live role holder from
  `active_region_holders()`. Reused, never reimplemented — R3's "never a second generator" applied
  to the consumer side.
  Verified live against `frontdoor` holding q0/q2/q3: `architect_general` is **queued** at
  `background-churn` (measured ratio 0.9) but **admitted** at `production-live`. That is R5's
  priority semantics falling out of the measured policy for free, rather than being reimplemented.

  **One deliberate divergence from the orchestrator, documented in code.** `pair_policy()` returns
  `allow` for an *unmeasured* pair at foreground traffic — correct there, where a real request is
  waiting and starving it on missing data would be worse. The bus carries no SLO, so fabric
  axiom 3 governs instead: unverifiable is **excluded**, not permitted. An unmeasured pair is
  rejected at every traffic class, with a message naming the generator that would measure it.
  Admitting one would have been the same silently-wrong-policy failure the topology-hash guard
  exists to prevent, one level down.
- [x] **R4 — lease authority and revocation-by-drain.** ✅ 2026-07-27 — new `lease-revoke`
  message kind and a `revoking` queue-row field. `coordinator-agent` (or the operator through it)
  requests revocation from its own outbox; authority is checked against `authority.lease_grant` and
  an unauthorised sender is **rejected with a defect, never obeyed** — a deterministic check, so
  the daemon making it does not stray into judgment.
  Revocation is cooperative by necessity as well as by policy: a held `flock` cannot be revoked by
  a third party, and axiom 4 forbids mid-decode preemption. The daemon marks the row `revoking`
  with **status unchanged** — the task genuinely is still running — and nudges the holder to
  quiesce, with an instruction that explicitly says to continue on `lane: none` work rather than
  idle. On `state: draining` the lease is released: owner cleared, status `READY`.
  A revocation the holder ignores still surfaces via the ordinary stall ladder when its lease
  expires, so it becomes a defect rather than a silent inconsistency.
  **Bug found and fixed by its own test.** Returning the task to `READY` made it immediately
  eligible again *in the same tick*, so the assignment pass handed it straight back to the same
  holder — the revocation became a no-op and the drain pure churn. Released tasks are now excluded
  from that tick's assignment. Verified both directions: a higher-priority `production-live` task
  claims the freed lane, and with nothing outranking it the yielded task resumes on the next tick,
  so the exclusion carries no lasting penalty. Ordinary priority ordering IS the deterministic
  re-grant trigger; no separate mechanism was needed.
  Prerequisite already satisfied: `gating` is a REQUIRED queue-row field, so the fallback set is
  always defined.
  Tests: 45/45 in `scripts/coordination/tests/test_session_bus_m4.py`.
- [x] **R5 — priority classes, yield, and pausability.** ✅ 2026-07-27 — classes
  `production-live > operator-directed > background-churn` live in `config.yaml` as a
  `priority_classes` artifact with explicit `yields_to`, so precedence is data, not code.
  *Pausability* is enforced in eligibility and tested: `exclusive-contiguous` refuses to start on a
  non-quiet host, `resumable` drains at any persisted unit, and `lease.max_hold_s` bounds the hold.
  *Yield* reuses R4's drain mechanism exactly — quiesce, release at a boundary, never a kill.
  **Automatic yield implemented** (`auto_yield()`): a higher-priority *class* waiting on a lane a
  lower class holds triggers a drain. This is the deterministic trigger R4 permits the daemon to
  pull — precedence comes straight from the artifact, so no discretion is exercised; discretionary
  revocation stays coordinator-agent's.
  Two guards keep it from thrashing, both tested: the waiting task must be eligible **but for the
  lane** (draining a lane for a task that is also gate-blocked would leave the lane idle AND the
  task still unable to run — pure churn), and at most one revocation per lane per tick so a burst
  of high-class work cannot drain every holder at once. Verified that `production-live` is **not**
  preempted by `background-churn` even when the latter carries a higher P-rank: class precedence
  dominates P-rank, which is the point of having two axes.
  Also added a **per-tick probe cache**: host sensing costs ~2s a call and a tick needed it in
  three places. Beyond the wasted 6s of a 45s tick, the real hazard was two halves of one decision
  observing different host states. Now probed once per tick, verified 1 call.
  Tests: 50/50.
- [x] **R6 — coordinator-agent as integration owner.** ✅ 2026-07-27 — the mechanizable half is
  built; the rest is procedure, and is labelled as such rather than pretended into code.

  **Built: the merge gate** (`scripts/coordination/merge_gate.py`). Classifies a diff as
  `autonomous` or `gated` from CONTENT, never category — autonomous unless the change touches a
  human-only path, because merges are revertible and the human-only list is not. Production kernels
  are one entry on that list, not a special case; they differ only in what satisfies the gate
  (operator approval **plus** the four-step promotion workflow, carried through as an
  `extra_requirement`). Rules are repo-scoped, so `MEASUREMENT.md` gates in `epyc-root` and not
  elsewhere. A gated verdict emits a ready-to-relay token-request block with an ungranted checkbox.
  **Fail-closed, opposite to the PreToolUse guard, deliberately:** an unverifiable or drifted gate
  list returns rc 3 and refuses, because a list that cannot be verified cannot authorise anything.
  The edit-time guard errs permissive (blocking on uncertainty would stall the repo); this one errs
  strict (refusing costs one operator glance). Same list, two biases, each matched to its cost.
  It never merges, pushes, or commits — deciding and acting are separate so the check can run in a
  pre-merge hook, in coordinator-agent, or by hand without any of them inheriting write authority.
  Tests: `scripts/coordination/tests/test_merge_gate.py`, 25/25, including the drifted-pin refusal
  end-to-end and its restoration.
- [x] **R6b — coordinator-agent instantiated and made re-instantiable.** ✅ 2026-07-29 — R6 built
  the authority; this ran it for a full campaign and turned what was learned into a cold start.
  Deliverables: `agents/coordinator-agent.md` (the role — mission, guardrails, the never-sign /
  never-tick / never-edit-`human_only_paths.yaml` boundary) and `.claude/skills/coordinator-agent/`
  (the cold start: Phase 0 reality check → 1 addressable → 2 recover-from-files → **report** → 3
  triage, with the ordering marked non-negotiable because the failure mode is dispatching before
  the operator has seen true state).
  **The rule the campaign actually paid for is Workflow step 1, DRAIN BEFORE YOU SPEAK**: the
  coordinator's cursor sat 33 messages behind — including a hard block needing an operator
  signature and a completed audit carrying two CRITICAL findings — while the delivery machinery
  (daemon relay, C8 boundary detection, the severity watcher) worked correctly the whole time. The
  inbox was simply never read. Every fix that session shipped was in the delivery plane; the defect
  was in the last hop, bus → operator, which is judgment and cannot be mechanised — so it is a
  standing rule on every reply, not a startup step.
- [x] **R6c — post-reboot brief promoted to a first-class coordinator artifact.** ✅ 2026-07-29 —
  `coordination/session-bus/tasks/post-reboot-session.md` is now read in **Phase 0a, before any
  command**, and maintaining it at wrap-up is the outgoing coordinator's stated duty. Rationale:
  `rebuild` reconstructs the bus *mechanism* (queue, tokens, cursors, unread depth) but the bus
  carries no record of what a session was in the middle of or which gate a campaign is parked
  behind. Without the brief a fresh coordinator correctly reports an empty queue while a
  decision-grade campaign sits one command from resuming.

  **Built elsewhere: git hygiene as enforced rules** — path-scoped adds and fetch-before-commit are
  R7a's `check_commit_hygiene.py`, not prose.

  **Procedure, not code (stated so it is not mistaken for automated):** wrap-up itself
  (`flip_checkbox.py` is the primitive; sequencing it is coordinator-agent's job), worktree
  merging, and pushing. The structural benefit — mains in worktrees with a single integrator, so
  parallel sessions' staged files cannot ride into each other's commits — comes from the working
  arrangement, not from a script.

  **The no-index-creation exclusion stays policy, not a hook, and here is why:** blocking creation
  of handoff stubs or index rows mechanically cannot distinguish an agent inventing work from the
  operator asking for a handoff to be written. A guard that cannot tell those apart would block
  legitimate requested work, which is the over-blocking failure this session already hit twice.
  `CLAUDE.md` states the rule; the daemon's audit reports index changes as observations.
- [x] **R7 — coordinator integrity.** ✅ 2026-07-27 — three layers, each catching what the
  previous one cannot:
  *Containment.* The trust boundary moved out of agent-editable `config.yaml` into
  `coordination/session-bus/human_only_paths.yaml`, pinned by `human_only_paths.sha256`.
  `scripts/hooks/check_trust_boundary_edit.sh` (registered `PreToolUse → Write|Edit`) refuses edits
  to the gate list and its pin **unconditionally** (layer 1, needs no parsing, never degrades) and
  to the paths the list names (layer 2, best-effort — it ALLOWS with a warning if the list cannot be
  parsed, because failing closed on an unreadable config would block every edit in the repo).
  The operator path is untouched: ratify scripts amend via bash/python, not Write/Edit.
  *Detection.* `session_bus.py validate` compares the list against its pin, so a direct shell write
  that bypasses hooks entirely is still caught after the fact. Verified against injected drift, a
  missing list, and a missing pin.
  *Attribution.* `session_bus_coordinator.py audit` emits `defect` records for the two
  mechanically decidable violations — trust-boundary pin drift and single-writer breach (a row in
  `outbox/<a>` whose `from` is not `<a>`). Defects go to `advisory.jsonl`, preserving the M3
  separation between non-binding observability and autonomous routing decisions.
  **Honest scoping — two of R7's candidate checks are NOT defects and are emitted as
  `observation` instead.** "Commit without a preceding fetch" and "wholesale `git add`" are not
  reliably decidable after the fact, and a commit touching a human-only path cannot be attributed
  to agent-versus-operator at all, because every session commits under one git identity (the same
  limitation that broke M1's git-blame audit criterion). Preventing those belongs in a pre-commit
  hook, where the actor is still known. A clean audit must not be read as full coverage.
  *Reconstructibility.* `session_bus.py rebuild` derives full coordinator state from bus files
  alone, turning `BUS_PROTOCOL.md` rule 9 from an assertion into something runnable.
  Tests: `scripts/hooks/tests/test_trust_boundary_edit.py`, 16/16 — including that layer 2 degrades
  open while layer 1 holds.
  - [x] **R7a — the two checks the audit cannot make, moved to where the actor is known.**
    ✅ 2026-07-27 — `scripts/hooks/check_commit_hygiene.py` (`PreToolUse → Bash`). Rule A blocks
    wholesale staging on a shared repo (`git add -A|--all|-u|.`, `git commit -a|-am`), citing the
    real 2026-07-27 incident where one session's progress entry rode into commit `94a39cc0`
    authored by another and reached `origin/main` under an unrelated message. Rule B blocks
    committing with a stale `FETCH_HEAD` (default 600s, `EPYC_FETCH_MAX_AGE_S`), because parallel
    sessions push between your read and your write.
    Sandbox/temp repos are skipped by design so throwaway git fixtures stay frictionless.
    **Implemented in Python, not bash, for a specific reason:** the first draft matched with regex
    and had a false-positive class it could not escape — `git commit -m "add -A to the docs"`
    matched, because a regex cannot see that `-A` sits inside a quoted message. `shlex` tokenises
    properly and the argument of `-m` is never scanned for flags. Same lesson as the drop_caches
    matcher: an over-broad guard is worse than a missing one.
    Tests: `scripts/hooks/tests/test_commit_hygiene.py`, 29/29, including all five
    message-mentions-a-flag cases the regex draft failed, plus malformed quoting degrading open.
  **Deferred to M4 (not outstanding here):** coordinator-agent stall *detection* is the M4 stall
  ladder's job; the heartbeat it needs already exists and `/api/bus` already surfaces its age.
- [x] **R8 — consolidated unblock artifact.** ✅ 2026-07-27 —
  `scripts/coordination/unblock_artifact.py` (`generate` / `show` / `apply [--plan]`) plus
  `artifacts/operator/unblock.sh` as THE one command.
  **Granting is flipping a checkbox in `tokens/token-queue.md`** — the mechanism BUS_PROTOCOL
  rule 1 already establishes, where a checkbox in an operator-owned file *is* the grant. No new
  grammar invented. Per-gate command pins (never a bundle-wide hash, which would hard-fail the
  moment a line is struck), struck gates stay `HELD_OP_GATE` and are re-presented unchanged, and
  the applier never commits, never `git add`s and writes no bus file but its receipt — the daemon
  transcribes next tick. An already-applied gate is skipped by receipt lookup keyed on the command
  hash, so a second `apply` cannot double-run a non-idempotent command, while a *changed* command
  correctly counts as not-yet-applied.
  Tests: 24/24 — drift-after-grant refuses (rc 3), a struck line does not invalidate granted ones,
  a failing command returns rc 2 and is attributed to the AGENT, undated adjudication is malformed,
  `--plan` writes nothing, all three dash forms parse identically.
  A test also caught a real flaw in the module: it used one constant for both where its code lives
  and where its data lives, which made it unimportable under a redirected root. Now separated.

  **DESIGN NOTE — a multi-agent spec was produced for this and largely rejected.** A 9-agent
  workflow (4 surveys → synthesis → 3 adversarial lenses → consolidation; 919k tokens, 43 min)
  returned a ~113k-character spec proposing a hashed token preimage typed by the operator, versioned
  sidecars, revision-pinned appliers, `0444` forensic archives, per-item transaction directories with
  rollback, a token-attempt rate-limit ledger, and a six-verb mark grammar.
  Rejected as disproportionate, and **its own §7 supplies the decisive evidence**: under
  "deliberately not doing" it records that defending against a compromised generator is out of scope
  because *"the operator's secret is typed into a machine-generated script."* The centrepiece
  ceremony therefore defends against nothing an agent could do, while taxing every return. The
  checkbox has identical real security properties and already existed.
  **Process lesson:** three adversarial lenses each asked "what could go wrong" and each answered
  "add mechanism"; none asked "is this proportionate". Adversarial critique escalates by
  construction — a panel of this shape needs a fourth lens whose job is to *delete*.
  **Findings from it that WERE adopted** (the survey work was genuinely useful): no repo-HEAD pin
  (parallel sessions commit continuously); no dwell-time metric (it measures the operator); never a
  whole-bundle integrity assertion; only the operator escalates a glyph, machines may only
  de-escalate on payload drift; never delete or move a row, because a missing gate reads as *absent*
  rather than *declined*; an adjudication verb without an ISO date is malformed; parse the gate id
  independently of the dash character; keep generator annotations off the operator's line.
- [ ] **R9 — replay-eligibility screen at queue admission (M1/M3).** *Enforcement DONE
  ✅ 2026-07-27* — `replay_eligible` is a schema field, and the coordinator-daemon's eligibility
  rule now admits such a task **regardless of lane occupancy**: a tail-replayable result comes
  from deterministically rescoring banked outputs, so it occupies no lane and needs no claim, and
  gating it on lane-busy would queue work that cannot possibly contend. Verified with the CPU lane
  busy — a `replay_eligible` rescore is admitted while an otherwise-identical regeneration is
  rejected.
  **Remaining: the classification half.** Deciding *which* tasks are tail-replayable is per-task
  judgment; today it must be annotated by hand when the row is authored. Automating it is the M5
  triage hook's routing-annotation duty (flag-gated, `triage: off`). Until then the enforcement is
  live but only fires on rows someone remembered to mark.
- [x] **R10 — interference hooks.** ✅ 2026-07-27 —
  `scripts/hooks/check_live_holder_interference.sh`, registered in `.claude/settings.json` under
  both `PreToolUse → Bash` and `PreToolUse → Write|Edit`. Two mechanically checkable rules: refuse
  a **write** to `drop_caches` while any CPU region is claimed (the re-read pins pages onto one
  NUMA node, so the live run does not error — its numbers just become wrong), and refuse editing a
  `.sh` that a shell is currently executing (bash reads incrementally from its file offset, so an
  in-place edit splices old and new text). Fail-open: any probe that cannot answer confidently
  allows the call, because a hook that blocks on uncertainty stalls parallel sessions for reasons
  they cannot see. Override `EPYC_ALLOW_LIVE_INTERFERENCE=1`.
  Tests: `scripts/hooks/tests/test_live_holder_interference.py --all`, 16/16. Cases live in a JSON
  fixture because a PreToolUse hook matches command *text* and so cannot distinguish performing an
  action from mentioning it — a test with the patterns as literals is blocked by the hook it tests.
  Three bring-up lessons, all encoded: it fired for real (frontdoor held q0/q2/q3 while the
  orchestrator served, blocking a cache drop that would have corrupted live inference — the test
  expectation was wrong, not the hook); the first matcher was over-broad and blocked this hook's
  own commit message; and a PreToolUse block kills the **entire** Bash call, so a blocked block
  executes *nothing* — do not assume partial execution.

## Milestones

- [x] **M1 — skeleton + manual round-trip.** ✅ 2026-07-27 — layout, `BUS_PROTOCOL.md`,
  `config.yaml`, `session_bus.schema.json`, `scripts/coordination/session_bus.py` (append/fold/
  validate/cursor/status/drain), `tokens/token-queue.md`, and the CLAUDE.md drain instruction
  (inherited by Codex via the `AGENTS.md` symlink). Manual round-trip
  READY→ASSIGNED→CLAIMED→RUNNING→DONE_PASS green via file appends only; `validate` schema- and
  single-writer-clean over 16 records; negatives correctly refused (a main writing `queue.jsonl`,
  a row missing `gating`, a `token-request` without pre-validation evidence).
  **Codex drained unprompted at a real boundary** — cursor advanced to the full inbox at 18:34Z,
  ack/status/task-complete written to its own outbox at 18:35Z, boundary reported as *"after
  main-thread review, acceptance, commit, and push of the FG-1 replay provenance/taxonomy
  repair"*, instruction *"verified independently at AGENTS.md lines 198-202"*.
  **Caveat, self-reported by Codex** (`operator_message_also_notified: true`): it was also
  notified by the operator, so "would have drained with zero prompting" is not falsifiable from
  this instance. What IS evidenced: the standing instruction is discoverable, was independently
  verified, and the mechanism works end-to-end at a genuine task boundary.
  Rollback: delete the directory.
  **Audit-criterion correction (2026-07-27):** "single-writer audit clean (git blame per file =
  one authoring session)" does **not** discriminate here — every agent commits under the same git
  identity (`pestopoppa`), so `git log --format=%an` returns one name for every bus file
  regardless of who wrote it. The enforcing check is the content-level lint in
  `session_bus.py validate` (every row in `outbox/<a>` must carry `from == <a>`; every write is
  refused unless the caller owns the target path), corroborated by commit separation — Codex
  committed only its own three files as `45501f0a`; the coordinator fold has since terminalized
  the acceptance row as `DONE_PASS`. Later milestones should cite the lint, not the author field.
- [x] **M2 — hub visibility.** ✅ 2026-07-27 — `/api/bus` (roster, per-agent liveness, inbox
  depth, operator-token counts, co-residency topology check), `/api/queue` (folded queue +
  invariant alarms), and the `/bus` page on :8100. Clones the `/api/kernel` payload-builder
  pattern and classifies freshness from semantic heartbeat/row timestamps, not file mtime.
  PyYAML is imported behind a guard so the hub stays runnable under a stdlib-only interpreter.
  Accept: renders live state ✅; correct staleness classes on stale fixtures ✅ (fresh → aging at
  30m → stale at 3h, with `stale-heartbeat:*` alarms firing); fails soft ✅ (missing config →
  `config_error` + empty roster, no crash). Surfaces the rider invariants directly:
  `none-lane-depth`, `missing-gating`, `roster-orphan`, `co-residency-topology-drift`.
  Verified on a throwaway port; the live hub was never restarted. Rollback: revert the additive
  routes.
- [ ] **M3 — coordinator-daemon, read-only advisory.** *BUILT ✅ 2026-07-27* —
  `scripts/coordination/session_bus_coordinator.py` (flock singleton, tick loop, heartbeat,
  epoch fencing) and `scripts/coordination/bus_supervisor.sh` (userspace watchdog, health =
  heartbeat mtime, SIGTERM-then-SIGKILL, exponential backoff, `loop|once|status`; no systemd).
  Emits non-binding advisory `saturation` / `would-assign` / `would-idle` / `would-skip` records
  to `advisory.jsonl`. C2 relay, ACK redelivery, and C8 durable boundary surfacing may also append
  prescribed transport/notification rows to daemon-owned `inbox/*`; C8 persists its comparison
  snapshot in `boundary_state.json`.
  Verified: **survives kill -9 via supervisor** (recovered in 1s, epoch 1→2, and advisory rows
  carry the epoch so a pre-restart generation is identifiable); eligibility honours priority order,
  lane-busy, ungranted `operator_gates`, and non-terminal `depends_on`;
  `authority: assign` is **refused** because M4 is not built — an unbuilt assign path must never
  be silently approximated by the advisory one.
  **M3 acceptance restatement — no autonomous decision at `authority: manual|advisory`.** The
  retired “exactly two files” count was only a proxy for this property and is no longer evidence:
  legitimate C2/C8 transport now writes inboxes. In either pre-M4 authority, every daemon mutation
  must be one of: (a) its heartbeat, advisory, or C8 comparison state; (b) a schema-valid,
  explicitly addressed outbox relay that preserves the sender-selected recipient, `kind`,
  `task_id`/`corr_id`, and payload verbatim (the daemon adds only its delivery envelope and
  `relayed_src`); (c) the fixed ACK-redelivery transform of a previously delivered, overdue
  `requires_ack` message; or (d) the fixed C8 transform of a recorded non-idle → `idle` heartbeat
  transition into the defined `task-boundary` status notice for `coordinator-agent`. These are
  mechanical derivations, not choices. The daemon must not select work or a work recipient, nor
  set or alter priority, lane, owner, lease, queue status, gating, or a token outcome; it must not
  write `queue.jsonl` or `tokens/token-queue.md`. Advisory records remain observations only.
  **Required evidence for M3 sign-off:** run manual and advisory ticks over fixtures containing an
  explicit relay, an overdue ACK, and an idle transition; account for every mutation; prove
  byte-equivalence of relay-controlled fields, provenance of every generated notice, and no
  queue/token or assignment-state mutation. **This criterion is falsified by** any manual/advisory
  tick that changes `queue.jsonl` or `tokens/token-queue.md`; creates `task-assign` or another
  assignment/lifecycle/priority/lease/gating decision; alters a relayed recipient, kind,
  task/correlation identity, or payload; emits a boundary notice without its prior non-idle → idle
  heartbeat transition (or fields not derived from that heartbeat); or redelivers without a prior,
  overdue `requires_ack` source. File count alone is deliberately non-evidence.
  Two bugs found by its own tests and fixed: `classify_load()` returns `state`, not `class`
  (reading the wrong key fail-safes to permanently-busy, so the daemon would never have advised
  anything), and the same task was being advised to every idle agent (harmless while advisory,
  a double-assignment once M4 has authority).
  **Remaining for M3 sign-off: would-assign matches actual human/agent choices over a working
  day, divergences explainable.** That needs elapsed time and cannot be compressed.
  - [x] **M3a — supervisor running.** ✅ 2026-07-27 — started by the operator's instruction;
    supervisor 2009016 holds the lock, daemon does not. Fixing a self-lockout was required first
    (see M3b).
  - [x] **M3b — supervisor could never start (fd-9 self-lockout).** ✅ 2026-07-27 —
    `exec 9>"$LOCK_FILE"` creates an inheritable descriptor, so the daemon inherited the
    supervisor's own flock and held it for life. Every `loop` logged "another supervisor holds the
    lock" while `status` showed none running. Fixed with `9>&-`; pinned by
    `scripts/coordination/tests/test_bus_supervisor.py` (5/5), which asserts the daemon holds ZERO
    fds on the lock.
  - [x] **M3c — the supervisor test killed the live daemon.** ✅ 2026-07-27 — it scoped
    `LOCK_FILE`/`EPYC_ROOT`/`BUS_ROOT` but the supervisor's `pgrep -f` pattern is global, so a
    stub with the same filename matched production. `DAEMON`/`DAEMON_PATTERN` are now overridable.
    *Isolation is only as strong as its weakest axis.*
  - [ ] **M3d — the queue must hold real work for the evidence to mean anything.** Seeded
    2026-07-27 (19 tasks); before that the advisory stream held 978 records and ZERO
    `would-assign`. Widen per-handoff with `seed_queue.py --list` as the soak proceeds.
  Rollback: stop the daemon; the bus returns to fully-functional M1 manual mode.
- [ ] **M4 — assignment authority.** *CODE BUILT ✅ 2026-07-27, acceptance pending.*
  `apply_assignment()` in `session_bus_coordinator.py`, gated entirely on
  `coordinator_daemon.authority == "assign"`. M3's decision-property criterion—not a file
  count—proves that manual/advisory transport cannot become an assignment path, so flipping
  authority is the single switch and setting it back to `advisory` is the whole rollback.
  Implemented: real task-assign (queue row + inbox `task-assign` + lease from `leases.max_hold_s`);
  deterministic transcription of agent reports (ack→CLAIMED, status→RUNNING,
  task-complete→DONE_PASS/DONE_MARGINAL_OBS/FAILED, carrying `failure_reason`); token relay into
  `tokens/token-queue.md` with the pre-validated command verbatim, marking the task
  `HELD_OP_GATE`; and all three stall rungs (soft→`nudge`, hard/lease-expired→`STALE_REQUEUED`
  with owner cleared and attempt+1 plus a defect, give-up→`INFRA_BLOCKED` plus a token-queue alert
  that explicitly leaves the decision to the operator).
  **Ordering is deliberate:** transcribe → relay → stall ladder → assign. Transcribing first means
  decisions are made against current truth, not a stale queue; relaying before assigning means a
  newly-gated task is not assigned in the same tick; the ladder before assignment means a requeued
  task is immediately available.
  **Idempotent by construction, not by bookkeeping.** Transcription compares the latest report per
  task against the queue instead of tracking consumed messages — which would have needed
  daemon-owned cursors on files the daemon does not own. Repeated ticks provably append nothing.
  Also: a `token-request` lacking dry-run evidence is refused and raises a defect rather than being
  relayed, because presenting a command that fails is an agent defect by policy.
  Tests: `scripts/coordination/tests/test_session_bus_m4.py`, **31/31**.
  A documented test seam (`SESSION_BUS_LANE_SNAPSHOT_JSON`) makes lane state deterministic — real
  probing made the suite 66s and host-dependent, and a test whose result depends on whether a role
  happens to be serving is a test that will eventually lie (it already did once today, on the
  drop_caches guard). With the seam: 7s, plus five cases that could not be expressed before
  (lane-busy gating, `exclusive-contiguous` needing a quiet host, `replay_eligible` bypassing a
  busy lane).
  **Remaining for M4 sign-off:** the 48h zero-idle soak, one induced stall, an induced restart
  mid-assignment showing epoch fencing, and operator touching only token-queue checkboxes — plus
  M3's advisory-accuracy evidence, on which M4's go/no-go rests. The switch stays at `manual`
  until then. Rollback: `authority: advisory`.
### C-series ownership + residuals after the 2026-07-29 gpu-lane re-task (filed at wrap-up)

The `claude-gpu-lane` identity was stood down, then **re-spawned and re-tasked by the operator to
P2-2 tenant landing** (`gpu-serving-tie-in-program.md`). It is **not carrying the session-bus
C-series forward**, and said so explicitly on the bus rather than letting the work rot as
implicitly-owned. These three are filed here so they exist as tasks, not as prose in a bus message
nobody re-reads:

- [x] **C-OWN — the C-series needs a new owner.** **CURRENT OWNER: `mainD`, by operator decision
  2026-08-11** — a dedicated main rather than the auditor, brief
  `coordination/session-bus/tasks/mainD-c-own-delivery-plane.md`. History below.
  ✅ 2026-07-29 — **adopted by roster id `auditor`**
  (coordinator assignment, brief `coordination/session-bus/tasks/auditor-c-own-20260729.md`).
  C6/C9/C10/C14/C16/C18/C21 and the `tmux_adapter.py` hardening arc now have an owner. Round 2
  landed C24-review + C25 + C26 + C27(a/b/c) + C32 and the C24 ledger row, each committed with its
  tests. The two decisions the lane deliberately left open (C15 spawn cap, C18(a) `codex-bus-tests`
  role) are in the handover block below and **remain open — they are operator/coordinator calls,
  not this owner's to close.**
- [x] **C22 (NEW) — `roster_window_names()` is dead code still carrying the last-writer-wins idiom.**
  ✅ 2026-07-29 — **CLOSED, already fixed; deliberately NOT re-fixed.** Verified by `auditor`: the
  function is gone, and the only remaining occurrence of the name is a docstring line at
  `tmux_adapter.py:437` recording that it was deleted as dead code on 2026-07-29 and that its
  invariant (the undercount polarity) moved to `live_mains`. Confirmed by grep — zero definitions,
  zero callers. The row is closed rather than worked, per coordinator direction.
- [x] **C23 — triage disposition should not require an identical payload per `corr_id`.** ✅ 2026-08-11 — `mainD` implemented the bulk form; original protocol-shape disposition 2026-07-29 verified against `BUS_PROTOCOL.md` C23 rule and commit `01142ba5`; deliberately no adapter workaround.
  Found by doing it wrong on 2026-07-29: clearing 19 routed items needs one message per `corr_id`,
  so a session with a single disposition for all of them emits the **same ~1.5 KB payload 19 times**.
  Audited and worth stating precisely, because the obvious diagnosis is wrong: there is **no
  duplicate-send bug and no relay fan-out** — 19 messages, 19 distinct `corr_id`s, 19 distinct ids,
  relayed 1:1. The defect is that the protocol's clearing granularity makes bus spam the *natural*
  way to do a bulk disposition. Options: allow a `corr_ids: [...]` list on one message, or have
  `drain --triage` accept a bulk-disposition verb. Until then the workaround is discipline — a
  repeated payload across N `corr_id`s is bus noise by construction, so bodies must be per-item or
  terse. Belongs to whoever owns `BUS_PROTOCOL.md`; not edited here because the contract is not
  this lane's to change.
  **✅ 2026-07-29 — dispositioned by `auditor` as PROTOCOL SHAPE, not an adapter bug, and codified
  rather than coded around.** The diagnosis stands and was NOT re-fixed in `tmux_adapter.py`. The
  standing rule is now written into `coordination/session-bus/BUS_PROTOCOL.md` → *A repeated payload
  across N corr_ids is bus noise by construction*: before writing the same payload against a second
  `corr_id`, write it once and reference it; a disposition that is genuinely per-item carries
  per-item content, and if it does not, the items wanted one answer. A reader who cannot tell N
  answers from one answer repeated N times has lost the signal the queue exists to carry.
  **One honest caveat on the evidence:** the "19 identical payloads" count is taken from the prior
  report, not independently re-derived — scanning `outbox/claude-gpu-lane.jsonl` for the
  `triage-disposition-post-standdown` marker returned 0 at audit time (the roster rename moved the
  file). The DIAGNOSIS is confirmed from the protocol shape itself and does not depend on the count.
  The two structural options (a `corr_ids: [...]` list on one message, or a bulk-disposition verb in
  `drain --triage`) remain **open and unimplemented** — they change the contract, which is not this
  lane's to change unilaterally.
  - [x] **REOPENED 2026-07-29 — "the workaround is discipline" HAS NOW FAILED IN PRACTICE, twice in
    ten minutes, hours after the rule was codified.** Measured from one careful main (`mainA`): 3
    byte-identical payloads at 17:41Z (payload sha `ad177aa188e8`), then 6 more at 17:44Z whose
    payloads are identical and differ ONLY in `corr_id`. **Nine identical payloads in ten minutes.**
    **Why discipline cannot fix it, and this is my error not the sender's:** the protocol requires
    ONE `corr_id` per item to clear triage, so a main holding a single disposition for N routed items
    has **no compliant way to send it once**. The rule I wrote into `BUS_PROTOCOL.md` — *"write it
    once and reference it"* — is **not performable**, because no mechanism to reference it exists.
    **And the fan-out multiplies it:** each of those 6 acks carried `needs_routing_to` including
    `auditor` though 5 answered `inference`, so N dispositions × M routing targets = N×M triage
    entries fleet-wide.
    **✅ 2026-08-11 — `mainD`. IMPLEMENTED, exactly as the escalation designed it.** `corr_ids: [...]`
    alongside the scalar `corr_id`; the triage clearer treats a row as clearing every id it names.
    Purely additive — the scalar is unchanged and every row already on the bus keeps working.
    `BUS_PROTOCOL.md` is rewritten: the unperformable "write it once and reference it" is replaced by
    *one answer, one row*, and `print_triage` now advertises the bulk form in its trailer whenever
    more than one item is queued — the old trailer implied one row per item was the only way, which
    is how someone following it correctly sent nine identical payloads in ten minutes.
    Dogfooded on the live bus before documenting it (`msg-20260811T105403Z-190-mainD`). 6 tests, 418
    green.
    **On "not mine to change unilaterally":** that was the prior owner's read and it was right for
    them. Two things changed. The blocker sat unchanged for 13 days across owners, which is the
    recurrence check in `CLAUDE.md` — an item whose blocker never moves was never blocked. And the
    thing being protected was a rule that could not be obeyed, so "leave the contract alone" meant
    "keep requiring bus spam". The schema is not in `human_only_paths.yaml`; this is additive and
    reverts in one commit. Flagged to `coordinator-agent` as a contract change made, not asked.
    - [x] **`auditor`'s review note answered: there is NO vendored-schema consumer, and the
      architecture is why.** ✅ 2026-08-11. The note was the right question — "additive is
      automatically safe only where validation is centralized", and C40 had just established that
      `additionalProperties: false` rejects any stray key, so a consumer holding an old schema COPY
      would refuse a `corr_ids` row. Checked three ways rather than asserted:
      (a) **`_load_schema(bus_root)` reads the schema from the BUS ROOT, not from the code tree**
      (`session_bus.py:152-156`). The schema is data that travels with the bus, so every consumer
      pointed at a bus reads THAT bus's schema, whatever the age of the code doing the reading.
      (b) **Proven, not reasoned:** the 2026-07-28 worktree copy at
      `/mnt/raid0/llm/worktrees/wrapup-e8-m2-g3-20260728/` — whose own `session_bus.schema.json`
      has no `corr_ids` — was imported and pointed at the live bus root, and it ACCEPTED a
      `corr_ids` row. Old code, live schema, no failure.
      (c) **No hardcoded property allowlist exists anywhere.** Every non-schema `corr_id` occurrence
      is a test fixture constructing a row or the coordinator authoring one; none enumerates the
      permitted properties. `codex-bus-tests` is a roster id, not a fixture directory.
      The many on-disk schema copies are git worktrees (each with its own bus root, which a live-bus
      row never reaches) and ephemeral `tmp_path` test buses. **Closure is airtight.**
      Worth keeping as a general property: on this bus a schema addition reaches every consumer of
      that bus the moment the file changes, regardless of code age — which is exactly why "additive"
      is safe HERE and would not be in a system that bundles its schema with its clients.
    - [x] **Scoped, not general.** ✅ N distinct answers still want N rows; a bulk row that flattens
      N different answers into one loses the signal just as thoroughly as repeating one answer N
      times, in the other direction. A bare bulk ack is still receipt, not action. Both pinned by
      tests, along with "bulk must not mean all" — a `corr_ids` row clears only what it lists.
- [x] **C11 — the independent review C9's own filing called for was never paid.** ✅ 2026-07-29 —
  paid by `auditor` as part of the C24 review (they touch the same invariant, exactly as the brief
  directed). The review attacked C9's central claim — can `live_mains()` return a set missing a
  genuinely live id? — and found that **it can**, which corrects a safety argument that had been
  stated wrongly twice in this module. See the C24 review sub-row for the finding, the replacement
  invariant, and the test that pins it. Commit `3d509613`.
- [x] **C17 — a live window no roster row claims.** ✅ 2026-07-29 — **no action, correctly
  categorised.** `htop` and `btop` are live operator-owned windows in the `agent` session. Per
  `live_mains`' matching rules they are never counted and never cause a refusal, so they are a
  different CATEGORY, not an undercount. Surface them as informational; never refuse on them.
- [x] **C18a — `codex-bus-tests` carries `role: retired` with a stale heartbeat.** *Re-verified
  2026-08-11 by `mainD`: roster row is `role: retired`, `lanes: []`; heartbeat `idle`, now 14.2 days
  old. Still cosmetic.* **Recommendation on the still-open C18(a) DECISION — keep the row, retired.**
  Removing it would convert `codex-bus-tests`'s four files (inbox holds 23 delivered rows of real
  history) into **non-roster residue**, i.e. manufacture exactly the problem filed as brief item 10.
  `role == "retired"` already makes the relay treat it as unreachable and nothing nudges it, so the
  row costs nothing where it is and removing it costs history. ✅ 2026-07-29 —
  **bookkeeping, confirmed, no delivery risk.** Heartbeat `idle`, age ~21 h. `role == "retired"`
  already makes the relay treat it as an unreachable routing recipient
  (`session_bus_coordinator.py:1937`), so the staleness is cosmetic. Note this is distinct from the
  still-open C18(a) *decision* about what that roster row should ultimately be — that is a
  coordinator call and is unchanged.

> ### POST-REBOOT HANDOVER — `claude-gpu-lane`, closed 2026-07-29 — **HISTORICAL, do not act on**
>
> *Marked 2026-08-11 by `mainD` (flagged by `mainC`). It says "read this first" and describes a
> reboot 13 days past, by a session that no longer exists. The host rebooted 2026-07-29 13:41 and
> again nothing since; the branch it points at should be checked against `main` before any use.
> Kept for the record, demoted from instruction to history.*
>
> <details><summary>original text</summary>
>
> **Tier-C rank 10(d) crash-window fixes are on a PUSHED BRANCH, not in /tmp.**
> `epyc-orchestrator` branch **`tierc-10d-crash-window-durability`** (`8cdf14f9`, off
> `origin/main` `182ccef6`). Reviewed and tested, **deliberately not merged**: the diff touches
> `final_c1_retry.py` and `race_retry.py`, which codex is live in. Apply when its run is terminal.
> This is the STORAGE-DURABILITY half of 10(d); codex owns the control-flow half (universal
> abort-seal). They meet at exactly one place — `race_retry.execute`, lines ~1285-1307 — where my
> hunk is mechanical (build `marker_extra`, drop the load-update-rewrite) and touches no race
> logic. Tests: 380 passed + 5 skipped across the e8/v5/seal/c1 selection.
>
> This lane owned the `tmux_adapter.py` / session-bus hardening arc (C6, C9, C10, C14, C16, C18)
> and does not survive the reboot. Everything below is committed and pushed; nothing is in flight.
>
> **Do this before anything else, or spawning is dead:**
> 1. `tmux new-session -d -s agent` — nothing creates it, and `cmd_spawn` fails closed without it
>    (**C20**). This is not optional and not a defect when you see the refusal.
> 2. Restart the coordinator-daemon — it is a process, not state. It was at epoch 9 pre-reboot.
> 3. Every heartbeat will be stale and no window will be live, so **routed messages to
>    not-yet-restarted mains will emit "LOOKS DEAD" advisories**. That is the C18 warning working,
>    not a fault; it is deduped per (msg, recipient) so it cannot flood. It goes quiet as mains come
>    back up.
>
> **Two live decisions this lane deliberately did NOT make for you:**
> - **C15** — `caps.max_concurrent_mains` is **4** and reads 4/4. It was NOT raised to 6: that 6
>   belonged to the superseded daily-action key, and re-reading it as concurrency is exactly what
>   `resolve_spawn_cap()` refuses to do in code. Name a number; it is a one-line change. Post-reboot
>   the live count starts at 0, so this does not block bring-up — it bites once four mains are up.
> - **C18(a)** — `codex-bus-tests` is still `role: main` with no session. Non-urgent now: the
>   liveness check detects it regardless of whether anyone maintains the field.
>
> **What is verified vs what is asserted.** Verified by running it: the whole-repo suite (2 failed,
> 616 passed **from the canonical root**; the two are codex-owned stale expectations), both adapter
> suites and both bus suites (96 passed), the reboot spawn blocker, and the daemon epoch. Asserted
> but not re-run since: nothing.
>
> **Testing rules this arc produced — they are why the above numbers mean anything:**
> a fixture must not delete the signal under test; a suite whose entry points cannot fail is worse
> than an uncollected one; quote the invocation path with any tally (`/workspace` and the canonical
> root give different answers, deliberately — C19); and derive state from what is observable, never
> from a field somebody must maintain (C14/C18 polarity).
>
> </details>

- [ ] **M5 — flag-gated extensions** (each independent). *Send-keys/spawn BUILT ✅ 2026-07-27*
  after the operator granted `OP-SENDKEYS-CODEX` with `max_spawns_per_day: 3`:
  `scripts/coordination/tmux_adapter.py` (probe/nudge/spawn). Fail-closed; refuses to
  guess a pane; spawns only as a **window in `tmux.live_session`**, never its own session; creates
  all four bus files before the pane starts.
  Three defects its test suite found: an unverified target could send keys to the **wrong pane**
  (tmux resolves a miss to the current window with exit 0); the quiet-check was **fail-open**
  (`window_activity` only tracks output while attached); and `--dry-run` created files.
  - [x] **C6 — nudge submission verification.** ✅ 2026-07-28 — commit `8033f039`. Attempt 1
    (fail-open) let an unverified target send keys to the wrong pane; attempt 2 (quiet-check via
    `window_activity`) produced a false-negative on TUI overlays; attempt 3 (`codex-bus-tests`)
    replaced the row-window predicate with a **cursor-anchored** one — the composer is everything
    up to the terminal cursor, a pending message is one the composer *ends with*, matching is
    whitespace-insensitive (both TUIs soft-wrap inside the fragment), and the 240-char cap became
    a 4000-char policy ceiling on measured calibration (Claude blobs at ~805, Codex at 1001 and
    truncates blobs at 1024; 400-char chunks with a load-bearing 0.15s gap are verified to 12,000).
    Independently reviewed by `claude-gpu-lane`, which found attempt 3 had **reopened the
    fail-open through two narrower doors** and fixed both; 21 → 29 tests.
    - `text_absent` post-Enter was read as "submitted". An Enter consumed by a completion overlay
      rewrites or *extends* the typed text instead of submitting, leaving a pane that is
      byte-for-byte a success. Fixed twice over: success now requires the transcript **echo**
      positively (`text_echoed`), and messages containing `@` or starting with `/ ! #` are refused
      up front, because the extend case is undetectable from the pane afterwards. A leading `!` is
      Claude Code's bash mode — such a nudge would have *executed* in the target session.
    - A whitespace-only 60-char tail normalised to `""`, and `endswith("")` matched every pane, so
      the pre-Enter gate passed unconditionally and fired a bare Enter into the pane.
    - Also: post-Enter acceptance now needs 2 consecutive samples (a half-drawn repaint frame was
      believable on one); `send-keys` gained `--` (a chunk starting with `-` parsed as a flag); a
      mid-message chunk failure now reports how many chars it left pending in someone's composer.
    - **Testing rule this produced — a fixture must not hide the predicate under test.** The
      end-to-end fixture cleared the screen on submit (`\033[2J\033[H` after `read`). No real TUI
      does that — both echo the submitted message into the transcript — and it is precisely the
      echo that the post-Enter check must observe. A screen-clearing fixture therefore passes an
      implementation that cannot tell submission from a swallowed Enter: the test models away the
      one signal it exists to verify. When a fixture stands in for a real system, check what it
      *removes*, not just what it reproduces; anything the predicate reads is not optional detail.
  - [x] **C7 — roster-bound writer containment** ✅ 2026-07-28 — heartbeat/outbox appends require
    a roster id; rebuild and daemon audit ignore non-roster artifacts; validation warns without
    deleting them. `tests/test_session_bus.py` proves no task-shaped writer becomes an agent.
  - [x] **Bus protocol test suite** ✅ 2026-07-28 — first-ever automated coverage for the session
    bus (`tests/test_session_bus.py`); grew from 14 passed + 2 xfail to 27 passed, 0 xfail across
    the campaign below. Commit `69c65068`.
  - [x] **C1 — no inbound route for coordinator-agent.** ✅ 2026-07-28 — added
    `session_bus.py provision`. (Fixed by coordinator-agent, same campaign.)
  - [x] **C2 — daemon never relayed agent-authored outbox messages.** ✅ 2026-07-28 — added
    `relay_outbox_messages`, idempotent via `relayed_src`. (Fixed by coordinator-agent, same
    campaign.)
  - [x] **C3 — drain failed open on a missing inbox.** ✅ 2026-07-28 — drain now exits 2 on a
    missing inbox instead of silently succeeding. (Fixed by coordinator-agent, same campaign.)
  - [x] **C4 — ack redelivery and cursor-rewind enforcement.** ✅ 2026-07-28 — one durable tagged
    ack-deadline nudge per unacked `corr_id`, recipient-outbox ACK only; Rule 4 cursor rewind now
    refused (lower `--set` offsets rejected, equal/higher allowed). Commit `d6599a2b`; both prior
    xfails promoted to passing (16 passed).
  - [x] **C8 — durable task-boundary surfacing + endpoint-lint coverage.** ✅ 2026-07-28 —
    `detect_task_boundaries` in the coordinator-daemon delivers a task-boundary status message to
    coordinator-agent's inbox on any main's transition to idle, persisted in daemon-owned
    `boundary_state.json` so a daemon restart does not replay; plus a `validate` WARN for any
    roster row whose endpoint has no working delivery path, and a WARN for a missing
    `config.yaml`. Commits `496363c8`, `fa7ad915`, `7806b6a8` (durable surfacing, fixed by
    coordinator-agent). 27 passed, 0 xfail.
  - [x] **Guard self-idiom regression** ✅ 2026-07-28 — `agents_reference_guard.sh` now resolves
    bare nested session-bus references, and the compliant coordinator-agent role file is
    explicitly tested (a guard must not forbid its own idiom). Commit `667ed96f`, 3 passed.
  - [ ] **M5a — `--min-interval-s` default of 600s is the implementer's guess, not an operator
    decision.** Same class as the `max_spawns_per_day: 4` that the operator corrected to 3.
  - [x] **M5b — operator disposition for preserved roster orphans.** ✅ 2026-08-11 — `mainD`,
    commit `060efa27`, on `coordinator-agent`'s approval of a disposition package. **This row's own
    recommended action, carried out in its own order.** The two task-keyed outboxes were dealt with
    FIRST: their four messages — the E8-launch audit finding and three E8-R2 statuses including the
    sealed-vector scorer fix `c7f6c7fa` — were relayed to `coordinator-agent`
    (`msg-20260811T111438Z-193-mainD`) before anything moved, because they were never relayed and
    the archive would otherwise have been the only copy. Then all 24 files (2 outboxes + 22
    heartbeat snapshots) moved to `archive/non-roster-20260811/` with a provenance README.
    `validate`'s non-roster warning set: 24 → 0.
    **One deviation from the letter of the recommendation, stated rather than glossed:** it says a
    roster writer should "adopt the messages with original ids". That is not achievable — the msg
    `id` pattern encodes its writer, and one agent cannot author another's id without forging
    provenance. So the content was relayed with the original id CITED, and the originals kept
    readable in the archive. Same guarantee (nothing lost, content delivered), honest about
    authorship.
    *Original filing:* C7 prevents recurrence and
    keeps existing task-named heartbeat/outbox files out of roster-derived state, but does not
    delete or move evidence. **Audit 2026-07-29:** archive (never delete) the 22 task-keyed
    heartbeat snapshots after disposition; each is only `{agent,state,task_id,ts}` and carries no
    unique finding or attestation. Retain/re-home first the two task-keyed outboxes: their four
    messages are unique and unrelayed — one E8-launch audit finding and three E8-R2 statuses,
    including the sealed-vector scorer fix `c7f6c7fa`. Recommended action: a roster writer adopts
    the messages with original ids/payloads, then archives both outboxes with the heartbeats. Only
    the operator can authorize this disposition.
  - [ ] **M5c — standing instructions do not reach running sessions.** A CLAUDE.md rule added at
    21:43Z left an active agent on its 19:45Z heartbeat. Recorded in `BUS_PROTOCOL.md`; the open
    task is for coordinator-agent to nudge running mains to *re-read* on every such change.
  - [x] **C9 — `cmd_spawn` caps a daily action count, not live concurrency.** ✅ 2026-07-28 —
    `cmd_spawn` now counts LIVE roster-member windows in `tmux.live_session`; closing an idle main
    returns its slot immediately. `live_mains()` maps each roster row to the window that can carry
    it — its id, or the window component of a tmux endpoint where they differ (`codex` lives in
    `codex-inference`) — and intersects that with `tmux list-windows`; a window-INDEX endpoint
    (`tmux:agent:3`) contributes no name — an undercount, which **relaxes** the cap (see C14; this
    line originally said the opposite). **Fail-closed on an unreadable count:**
    tmux unreachable, the live session absent, or a roster with no ids all return `None`, never an
    empty set — "I could not count" is not "nothing is running", which is the exact shape of C3,
    C6 and C8. Spawning a main that is already live is also refused (one identity, one window).
    **Key decision, stated:** `caps.max_spawns_per_day` is **refused, not read as a fallback** —
    its `6` authorised six spawn ACTIONS in a day, and re-reading that as six SIMULTANEOUS mains
    would grant concurrency nobody approved, i.e. a fail-open. The old key alone now exits
    `EX_MISCONFIG` with the one-line config edit spelled out. `caps.max_concurrent_mains: 4` set
    by operator decision 2026-07-28 (one slot above the then-steady state of 3 live mains).
    The daily ledger count survives in `probe` as `spawns_today_history_only` and gates nothing.
    Tests: 10 new cases in `tests/test_tmux_adapter.py` (40 passed) including an end-to-end
    disposable-session proof that closing a window returns the slot, plus 4 new cases in the
    standalone suite, since renamed to `scripts/coordination/tests/test_tmux_adapter_live.py`
    (37/37 — but see C10: that run was flaky-green on one C9 check).
    *Found while doing it:* that standalone suite had been **red at HEAD** since the C6 change —
    it is not pytest-collected, so nobody re-ran it — and for the same reason the C6 review
    flagged: its nudge fixture cleared the screen on submit, deleting the transcript echo the
    post-Enter check must observe. Same fixture bug, second file. Fixed; see the C6 entry's
    testing rule. **Anyone touching this module: run BOTH suites.**
    <details><summary>Original filing (2026-07-28)</summary> `caps.max_spawns_per_day` is enforced by counting `kind == "spawn"` rows in
    `coordination/session-bus/adapter-ledger.jsonl` whose `ts` starts with today's date — a rate
    limit on the spawn action, not a bound on simultaneously-live mains. Killing or closing a main
    never returns its slot. Observed with three spawn rows for the day (`codex-bus-tests`
    15:34:25, `claude-gpu-lane` 16:04:42, `fable-auditor` 19:47:34) while only two mains were
    actually alive — `codex-bus-tests` had already been destroyed — yet further spawns were
    refused at 3/3 despite spare real capacity.
    A concurrency cap should bound the thing that actually costs something: simultaneous mains
    competing for compute, context, and coordinator attention. A daily action cap instead
    penalises churn, turns one operational mistake into a cost for the rest of the day, and —
    worst — makes closing an idle session cost a spawn slot for no reason, directly against the
    session-lifecycle rule in `agents/shared/OPERATING_CONSTRAINTS.md` ("nothing assignable →
    close the session"): a coordinator that correctly closes a finished main is punished for it.
    The operator's expectation was concurrency semantics; the config key name matches the
    implementation, so the key name is not the bug — the design is.
    Fix: count **live roster-member windows** (e.g. `tmux list-windows` against
    `tmux.live_session`, intersected with roster ids from `config.yaml`) instead of ledger rows.
    Rename the cap to reflect concurrency (e.g. `caps.max_concurrent_mains`) — decide and state
    explicitly whether the old key stays readable for one release or the module fails closed when
    only the old key is present; do not leave that ambiguous. Stay fail-closed: if the live-window
    count can't be determined (tmux unreachable, session absent), refuse rather than assume zero —
    this module's whole history (C3, C6, C8) is fail-open defects; do not add another. Needs tests
    in `tests/test_tmux_adapter.py`. `tmux_adapter.py` is grant-gated (`OP-SENDKEYS-CODEX`) and had
    three fix attempts on the unrelated C6 defect on 2026-07-28 alone, so this change wants an
    independent review before it lands, not a same-session self-merge.
    *Context, not part of the fix:* the operator raised the cap 3 → 6 in
    `coordination/session-bus/config.yaml` on 2026-07-28 as interim headroom. That bump is not the
    fix and does not close this item.
    </details>
  - [x] **C10 — the standalone adapter suite is not collected, so it rots unrun.** ✅ 2026-07-28.
    Renamed `scripts/coordination/tests/test_tmux_adapter.py` →
    **`test_tmux_adapter_live.py`** (`git mv`, history preserved) and made its entry points
    assert. It is now collected and green: `pytest tests/test_tmux_adapter.py
    scripts/coordination/tests/test_tmux_adapter_live.py` → **42 passed**.
    Two distinct defects, both worse than "not collected":
    - **The basename collided.** It shared `test_tmux_adapter.py` with `tests/`, and neither
      directory is a package, so pytest derived the module name `test_tmux_adapter` for both and
      raised `import file mismatch` — a collection ERROR that **interrupts the entire run**, not a
      skip. Any attempt to run both suites together aborted, so in practice only the `tests/` one
      was ever run, and this file sat RED at HEAD for a day after the C6 change.
    - **Collected would have been WORSE than uncollected.** `check()` only appended to a
      module-global list that `main()` inspected; `test_unit`/`test_live` returned `None`. Under
      pytest they would have reported **PASS with every check failing** — manufactured green
      evidence. Each entry point now asserts over the checks it recorded (sliced by start index,
      so `test_live` cannot inherit `test_unit`'s failures), and `_skip()` yields a real pytest
      skip when tmux is unreachable instead of a silent pass. Verified by injecting a failing
      check: the assertion fires.
    - **A third defect fell out: the spawn fixture was racy.** Real spawns used `command="true"`,
      which exits at once — measured, tmux reaps the window within ~0.3 s — so every check needing
      the spawned main to *be live* raced the reaper. The C9 duplicate-refusal check failed on the
      very next run after landing; **the "37/37" first quoted for C9 was flaky-green.** Fixture
      now spawns `sleep 300`. This is a fixture defect, not an adapter defect: a window whose
      command exited is genuinely not a live main, and the adapter counting it as dead is correct.
      3 consecutive clean runs after the fix.
    Anyone touching `tmux_adapter.py` still runs **both** suites — the header of each says so.
  - [x] **C16 — a bare repo-wide `pytest` cannot run, which is why C10 could hide.** ✅ 2026-07-28
    — `pytest.ini` + two package markers. Before: `pytest` from `/workspace` collected 2200 tests
    and **aborted with 46 collection errors**, so there was no whole-repo run for anything to be
    red in. After: **576 collected, 0 collection errors, 0.8 s**, and the run completes.
    - 45 of the 46 were `repos/` — the child repos reached by symlink, plus `*.bak-*` backups.
      They own their suites and their dependencies. `norecursedirs` excludes them from
      *recursion* only, so `pytest repos/epyc-orchestrator/tests` still works on purpose.
    - The 46th was `tests/compliance`, and the cause was not the obvious one. Its modules import
      themselves absolutely (`from tests.compliance.agent_file...`), which is required by the
      documented `python -m tests.compliance.agent_file.runner` CLI, so rewriting them to relative
      imports would have broken that CLI. But `tests/` had no `__init__.py`, and **a namespace
      package loses to a regular package anywhere on sys.path regardless of order** — so `tests`
      resolved to `/mnt/raid0/llm/epyc-orchestrator/tests/__init__.py`, reached through this venv.
      `pythonpath = .` alone does not fix that; `tests/__init__.py` +
      `tests/compliance/__init__.py` do. The documented CLI was broken by the same cause and now
      imports.
    - **Nothing is hidden.** No test is suppressed, deselected or xfailed. The 53 collected cases
      in the codex-owned E8 files (`test_e8_quality_baseline_v4_wrapper`,
      `test_e8_quality_source_protocol_amendment`, `test_ratify_pbench4_fg4b_*`) are collected and
      still fail — that is the intended outcome. **The goal was a run that is honestly red, not a
      green one.**
    - **First whole-repo run:** `5 failed, 571 passed, 2 warnings in 189.05s`. The five are exactly
      the pre-existing E8 reds; no new failure introduced, none hidden. Codex owns those; do not
      "fix" them from this lane.
  - [x] **C11 — C9 landed without the independent review its own filing required.** ✅ Paid
    2026-07-29 by `auditor` as part of the C24 review, commit `3d509613` — the two touch the same
    invariant, exactly as the row directed. Re-verified by `mainD` 2026-08-11 against current HEAD
    rather than taken from the earlier claim: the commit exists, carries 145 lines of test, and its
    review attacked C9's central claim — *can `live_mains()` return a set missing a genuinely live
    id?* — and found that **it can**, correcting a safety argument this module had stated wrongly
    twice. The debt is paid; this box was simply never flipped.
    *Original filing:* The C9 entry
    says the change "wants an independent review before it lands, not a same-session self-merge",
    and it was implemented and committed (`8cbe50c0`) by the same session that had just reviewed
    C6 — on direct operator instruction, which supersedes the handoff's own procedure, but the
    review debt is real and unpaid. A second pair of eyes on `live_mains` / `resolve_spawn_cap` /
    `cmd_spawn` is cheap now and expensive after something spawns wrongly. Not urgent: the change
    is fail-closed on every branch it cannot evaluate, and both suites are green.
  - [x] **C12 — the nudge fragment can collide with the transcript.** ✅ 2026-08-11 — `mainD`.
    Closed with an OCCURRENCE COUNT rather than the cursor offset the filing proposed: the capture
    is re-normalised and the pane can scroll between samples, so a byte offset does not survive a
    poll and a count does. The caller records how many times the fragment is on the pane before
    Enter; a genuine submission MOVES our copy from the composer into the transcript so the count
    holds, while an Enter eaten by a completion overlay DELETES it so the count drops and whatever
    remains is provably stale. An unreadable pane yields `None` = no anchor and keeps the pre-C12
    behaviour — the capture-failure path already refuses a moment later, and refusing twice for one
    cause turns a transient tmux hiccup into a nudge failure. 3 tests.
    *Original filing:* Post-Enter success is "the
    60-char tail is on the pane but not at the cursor". If an identical fragment is already in the
    scrollback (the same nudge sent earlier, or an agent echoing the text), an Enter that never
    submitted could still find it and read as success. The 600s rate limit makes a same-text
    repeat unlikely and the failure needs a *second* fault to matter, which is why it is filed
    rather than fixed. Closing it properly means anchoring the echo to a position *below* the
    pre-Enter cursor rather than anywhere on the pane.
  - [x] **C13 — nudge refuses `@` anywhere in the message, which is broader than the hazard.**
    ✅ 2026-08-11 — `mainD`. Narrowed to a token-initial `@` (start of message or after
    whitespace), which is the shape the picker actually binds to. `ops@example.com` and `a@b` now
    pass; `@file.py` and a bare `@` still refuse. **Narrowed, not relaxed** — the filing's own
    condition was "if it proves annoying in practice", and it did, on a message containing an email
    address. 6-case parametrised test covering both directions.
    *Original filing:*
    The trigger is a picker opening on an `@`-prefixed *token*; the guard refuses the character
    anywhere, so an email address or an `@`-mention in otherwise-fine prose is rejected. Chosen
    deliberately — a false refusal costs a rephrase, a false accept fires Enter into a picker —
    but if it proves annoying in practice, narrow it to `@` at a token start and keep the rest.
  - [x] **C14 — a roster row whose window is unmatchable is invisible to the concurrency count,
    and that INVENTS capacity.** ✅ 2026-07-28 — *Polarity corrected 2026-07-28 — this item, the
    `roster_window_names` docstring, and the `8033f039`/`8cbe50c0` commit messages all originally
    claimed the opposite ("an undercount in the direction that refuses spawns, never one that
    invents capacity"). It is backwards.* `cmd_spawn` refuses when `len(ids) >= cap`, so missing a
    live main makes `len(ids)` **smaller**, the comparison passes when it should not, and a slot
    that is actually occupied is handed out. It also weakens the `args.agent in ids` duplicate
    check, so the invisible main can be spawned twice. **Undercount = fail-open**, in the module
    whose entire defect history (C3, C6, C8, C9) is fail-opens — which is exactly how the next one
    gets built when the invariant is documented backwards.
    Three drift triggers, none live in `config.yaml` today (checked), which is why this is a
    documented residual rather than an open hole:
    (a) **an operator renames a window without updating the endpoint** — the real
    `codex` → `codex-inference` rename of 2026-07-28 stayed counted *only* because the endpoint was
    updated with it; (b) **window-INDEX endpoints** (`tmux:agent:3`) — an index is not a name;
    (c) **pane-suffixed components** (`tmux:agent:win.0`) — `.0` is a pane, so the string never
    equals a `#{window_name}`.
    **FIXED ✅ 2026-07-28.** `live_mains` now lists with
    `-F '#{window_index}\t#{window_name}'` and `parse_endpoint_window()` resolves all three shapes:
    an index against `#{window_index}`, a pane suffix by stripping `.<pane>` and resolving the
    remainder, and an endpoint with more `:` parts than `tmux:<session>[:<window>]` as an outright
    **refusal**. Four refusing branches, each tested:
    (i) an endpoint that cannot be READ refuses the whole count — *uninterpretable is not absent*,
    since skipping the row shrinks the count and frees an occupied slot;
    (ii) two roster rows claiming one window refuses (which main is live would be a guess);
    (iii) a `list-windows` row without the tab refuses rather than being read as an empty session;
    (iv) the pre-existing unreadable/absent-session branch is unchanged.
    **Kept usable:** a row that is interpretable but matches no live window is simply NOT LIVE —
    the normal state of a retired or closed main — and costs nothing. Only unreadable endpoints
    refuse.
    **Where there was a choice, it overcounts:** an id is counted live if a window carries its id
    OR its endpoint resolves, and the endpoint match applies even across sessions. Overcounting
    refuses a spawn that might have been allowed; undercounting grants one that must not be. Only
    the first is recoverable by asking again.
    **`pane_dead` is deliberately NOT consulted** (fable-auditor's caution): a dead pane still holds
    a window, and excluding those would shrink the count — flipping the error polarity back toward
    inventing capacity if the `pane_dead` read ever misreported. There is a test asserting
    `live_mains` contains no `pane_dead` filter, so a future "optimisation" trips it.
    Latent, not live: no roster row triggered any of these shapes, and the real config resolves to
    the same 4 mains before and after. 40 → 46 tests in `tests/test_tmux_adapter.py`; 48 across
    both suites.
  - [x] **C19 — the whole-repo test result depends on WHICH PATH you invoke it from.** ✅ CLOSED
    2026-07-29 by owner decision: **codex retains the literal canonical-root guard deliberately**,
    as a trust-boundary property — a production ratifier must not accept a second name for the
    production root. So this is intended strictness, not drift, and the resolution is procedural:
    quote the invocation path with any tally and prefer the canonical root (`pytest.ini` says so at
    the top). *Original measurement below for the record.* *Measured
    2026-07-29, and it is why two sessions reported different truths about the same commit.* Same
    tree, same commit, same interpreter:
    `cd /mnt/raid0/llm/epyc-root && pytest tests/test_ratify_pbench4_fg4b_*` → **28 passed**;
    `cd /workspace && …` → **3 failed, 25 passed**. `/workspace/.git` and
    `/mnt/raid0/llm/epyc-root/.git` are the same inode (96604699), so this is one tree reached two
    ways. The E8 ratifier scripts under `artifacts/operator/` compare the invocation path against
    the literal canonical root as a **trust-boundary guard** ("production ratifier must run from
    the canonical root"). *The guard is correct and must not be relaxed to make a test pass* — it
    is exactly the kind of check that should not accept a second name for the production root.
    Consequence for C16: a pass/fail tally from this repo is only comparable when the invocation
    path is quoted with it. `pytest.ini` now documents the canonical path at the top. Open question
    for the owner of those scripts (codex / measurement, NOT this lane): should the guard compare
    `realpath` so one physical tree gives one answer, or is binding to the literal path the
    intended strictness? Either answer is fine; the current silent divergence is not.
  - [x] **C17 — a live window that NO roster row claims is silently excluded from the count.**
    ✅ CLOSED 2026-07-29 by operator answer on the bus: the `claude` window is **operator-owned and
    out of scope**, and coordinator-covered mains are **always coordinator-spawned**, so an
    unattributed window can never be one. The exclusion is therefore correct, not a fail-open: the
    count is of coordinator-managed mains, and a window outside that set is not a slot the cap
    governs. No `tmux.non_main_windows` key is needed. *Original filing below for the record.*
    ~~Filed as a live fail-open:~~ *Found 2026-07-29 while auditing routed bus messages.* C14 closed the
    **row → window** direction (a roster row whose endpoint could not be read). This is the
    **window → row** direction, and it is live rather than latent: session `agent` holds a window
    named `claude` that no roster row claims (`claude-main` is RETIRED with a `monitor:file`
    endpoint and its historical window was `claude_A`). `live_mains` reports 4 —
    `claude-gpu-lane`, `codex`, `coordinator-agent`, `fable-auditor` — and `claude` is attributed
    to nobody. ~~**If that window is a main, the cap is really 5/4 and a slot has been
    invented**~~ — **RETRACTED 2026-07-29**: that framing is wrong. `max_concurrent_mains`
    governs COORDINATOR-SPAWNED mains, and an operator-owned session outside the roster is a
    different CATEGORY, not a shortfall — the count measures exactly what it should. The one
    genuine signal that survives is narrower and is C14's: a *roster* main whose window was
    renamed away from both its id and its endpoint, which WAS coordinator-spawned and does
    belong under the cap;
    the count resolves the ambiguity in the capacity-inventing direction, which is the one this
    module keeps getting wrong.
    Why it was not simply fixed with C14: an unattributed window is indistinguishable from a tool
    window, and `htop`/`btop`/`fish` are legitimately not mains — refusing on every unattributed
    window would make spawn refuse permanently. The principled fix needs config data that does not
    exist yet: an explicit `tmux.non_main_windows` allowlist, after which any window that is
    neither a roster main nor allowlisted refuses (or at minimum surfaces in `probe`). That is a
    new config key changing spawn behaviour, so it is an operator decision, not an implementer's.
    **Immediate question, independent of the fix:** is `claude` a main needing a roster row, or an
    operator shell? If it is a main, `config.yaml` is stale and the concurrency count is
    understating the fleet today.
  - [x] **C18 — a routed message to a dead session is dropped silently.** ✅ 2026-07-29 —
    detection landed (`528435fc` fan-out + defect advisories; liveness check in `e428bceb`,
    record `92348b68`), activated at daemon **epoch 9** (pid 1795713, 11:19:51Z). The data
    cleanup (a) remains as its own line below. *Original filing:*
    `msg-20260729T092520Z-15-claude-gpu-lane` routed to `[fable-auditor, codex-bus-tests]`;
    `fable-auditor` received it, `codex-bus-tests` no longer exists (no tmux window, heartbeat 16.4h
    stale) and its share vanished with no defect, no bounce, nothing. `append` validates that a
    `needs_routing_to` entry is a roster ID — but a roster row outlives the session, so ID validity
    is not reachability. Audit done here: of 16 outbox rows only 2 carry `needs_routing_to`, and
    `codex-bus-tests` was the only unreachable recipient among them — re-sent to
    `coordinator-agent` as `msg-20260729T100100Z-18-claude-gpu-lane`.
    **Half-closed by `528435fc`, and the remaining half is the case that actually bit.** The relay
    now fans out on `needs_routing_to` and raises a `defect` advisory for an unreachable recipient —
    but only when the id is *not a roster id* or its *role is `retired`*
    (`session_bus_coordinator.py:1288-1291`). `codex-bus-tests` is neither: it is still
    `role: main` in `config.yaml:25`, while its window is gone and its heartbeat is **16.7 h
    stale**. So the exact message that was dropped today would still be dropped silently.
    Two ways to finish it, and they are not exclusive:
    (a) **data** — set `codex-bus-tests` to `role: retired` (coordinator/operator call; the row must
    be kept, not deleted, since its cursors and history are keyed on the identity);
    (b) **code — DONE ✅ 2026-07-29.** `_looks_dead()` + `_live_window_names()` in
    `session_bus_coordinator.py`: reachability is now **observed**, not declared. A live window in
    `tmux.live_session` means alive and SUPPRESSES the warning (a healthy main's heartbeat goes
    stale mid-generation — observed 2026-07-27, so staleness alone would fire on healthy agents and
    train people to ignore it); otherwise a heartbeat silent past 4 h is the evidence. Polarity per
    fable-auditor's caution: **deliver-plus-warn, never refuse** — an inbox row is durable and a
    merely-offline agent drains it on return, so bouncing would convert transient offline into
    message loss. If tmux is unreadable the warning still fires (deduped per (msg, recipient)):
    a false warning costs one visible line, false silence costs the defect. A caller with no
    config never probes the real session, so unit tests cannot read whichever windows happen to be
    up. Four regression tests including the exact 2026-07-29 miss (rostered, non-retired, 17 h
    stale, no window → warned AND delivered). Suites: 48 passed.
    - [x] **ACTIVATION for (b)** ✅ 2026-07-29 — operator restarted the daemon to **epoch 9**
      (pid 1795713, started 11:19:51Z, after `e428bceb`), so the liveness warning is live, not
      inert. Two activation gaps in one day on the same file: **a merged fix and a running fix are
      different states**, and only the process owner can close the second.
    (a) data — still open: `codex-bus-tests` remains `role: main`. Now non-urgent, since (b)
    detects it regardless of whether anyone remembers to set the field.
    - [x] **SECOND HALF: the warning needed a reader too** ✅ 2026-07-29. After (b), a routed
      message to a dead agent was delivered-and-warned — but the warning was an `advisory.jsonl`
      row, and **advisory rows are delivered to no one**; `status` prints the last five on demand.
      So the defect had two layers: a message in an inbox nobody drains, and a notice about it in a
      ledger nobody reads. The notice now also goes to **coordinator-agent's inbox**, a channel
      drained at every task boundary, because coordinator-agent is the party that can retire the
      roster row or re-route the work. Delivery to the dead recipient is UNCHANGED — this adds a
      reader, it does not refuse, bounce or withhold (fable-auditor's polarity note, honoured).
      Idempotency is keyed on **the notice's own durable trace** (a matching row already in
      coordinator-agent's inbox), not on the advisory ledger: the ledger is written by the tick
      loop, so any direct caller — every unit test, and any future one — would have re-notified on
      every pass. Same rule the module applies to liveness: derive it from what the thing itself
      leaves behind. Two regression tests; 96 passed across the affected suites.
    - [x] **ACTIVATION for the second half: the daemon at epoch 9 predates it.** ✅ 2026-08-11 —
      closed by restart. The daemon is at **epoch 16** (pid 942753); the row was written against
      epoch 9, so every restart since carried it. Verified from the live heartbeat, not assumed.
      Its own words — *"third activation gap on this file in one day"* — are the reason **C42**
      exists: a merged fix and a running fix are different states, and this row had to wait for a
      human to notice. The supervisor now detects a daemon predating its own source, so this class
      of gap should not need a row again.
    *Precision + polarity note (fable-auditor, wrap-up 2026-07-29):* post-`528435fc` the rostered
    non-retired case is no longer *dropped* — it is durably DELIVERED to an inbox nothing drains
    (recoverable if the session revives; invisible to the sender either way). For (b), prefer
    deliver-plus-WARN-advisory (`delivered but heartbeat is Nh stale`) over refuse-on-staleness:
    refusal would bounce messages to a merely-offline agent that today drains them on return —
    converting transient offline into message loss, the opposite-polarity error.
    - [x] Relay fan-out + unreachable-recipient defect advisories landed (fable-auditor,
      `528435fc`): delivery to every `needs_routing_to` id IN ADDITION to `to`, per-recipient
      idempotent via `relayed_src`; unreachable = roster row gone OR role `retired`, defect
      advisory deduped once per (msg, recipient) against `advisory.jsonl`; `append` refuses
      retired targets at authoring; regression reproduces the exact 09:50Z miss. NOTE: the commit
      message and two in-code comments originally said "C16"; comments corrected to C18 at
      wrap-up — the pushed commit message is immutable, this line is the record. ✅ 2026-07-29
    - [x] ACTIVATION GAP CLOSED ✅ 2026-07-29 — the operator restarted the daemon (**epoch 8**,
      pid 1659843, started 10:06:18Z, i.e. after `528435fc` at 10:02Z) and verified fan-out live: a
      message addressed to `coordinator-agent` with `needs_routing_to` for `claude-gpu-lane` and
      `fable-auditor` reached both. Routed delivery no longer depends on the triage outbox-scan.
      *The lesson generalises and it applies to this very entry:* a merged fix is inert until the
      long-running process carrying it is restarted, so "landed" and "active" are two states, and
      the second one needs an owner. See the activation note on the code half below.
    - [x] Delete dead `roster_window_names()` in `tmux_adapter.py` ✅ 2026-07-29 — zero callers
      confirmed before deleting. **Its docstring carried the corrected polarity statement and the
      drift-trigger list**, so that text was re-homed onto `live_mains` (the function whose
      arithmetic the invariant is about) BEFORE the deletion — otherwise the cleanup would have
      deleted the correction that `8d865ea2` exists to preserve. 48 passed.
  - [x] **C21 — `check_pytest_safety.sh` matched `-n <num>` anywhere in a compound command.**
    ✅ 2026-07-29 — scoped to the invocation. The match is now segment- and quote-aware
    (`scripts/hooks/pytest_worker_scan.py`, called by the hook): quoted runs are blanked because
    their contents are data, the command is split on shell separators because a later pipeline
    stage is a different program, and **heredoc bodies are blanked too** — found when the guard
    blocked its own test fixture, which listed `-n auto` as example data. That is the third face
    of one bug: it was matching TEXT, not INVOCATIONS. Detection of `pytest` stays deliberately
    generous about position, so `xargs pytest -n 64` and `timeout 900 python -m pytest -n 32`
    are still caught; only the scope narrowed. Fails CLOSED — if python3 is missing or the
    scanner errors, it falls back to the original broad match and refuses rather than guessing.
    14 scanner cases + 18 tests in `tests/hooks/test_pytest_worker_scan.py`; end-to-end the real
    false positive now exits 0 and `pytest -n 40` still exits 2.
    *Original filing:*
    *Observed 2026-07-29.* A command combining pytest with `sed -n 340,360p` was blocked as
    "pytest -n 340 is too many workers" — the guard scans the whole command string rather than the
    pytest segment, so an unrelated `-n` in a later stage trips it. Harmless today (split the
    commands and it passes) and the guard errs toward refusing, which is the right direction for a
    memory-safety check on a 192-thread box — but it will keep surprising people. Scope the match
    to the pytest invocation.
  - [ ] **C20 — after a reboot, `tmux_adapter.py spawn` cannot spawn ANYTHING until someone
    creates the `agent` tmux session by hand. THIS IS ON THE REBOOT CRITICAL PATH.** *Verified
    2026-07-29 by running `live_mains` against an absent session.* With no tmux server or no
    `agent` session, `live_mains` returns `None` ("cannot list windows of the live session"), so
    `cmd_spawn` refuses with `EX_BLOCKED` — correct fail-closed behaviour, and
    `tmux.allow_session_creation: false` means the adapter will **never** create the session
    itself (an operator requirement from 2026-07-27: every main is a WINDOW in the one live
    session, and this module never calls `new-session`).
    So the post-reboot sequence has a mandatory first step that nothing in the code will do for
    you: **`tmux new-session -d -s agent`** (plus restarting the coordinator-daemon, which is a
    process and does not survive either). Until then every spawn attempt refuses with a message
    about being unable to count live mains — which reads like a defect and is not one.
    Decide deliberately, do not paper over it: either the operator/coordinator creates the session
    as a documented reboot step (recommended — it keeps `allow_session_creation: false`, which is
    what stops a stray spawn from inventing its own session), or that flag is flipped with an
    explicit decision recorded. Do NOT "fix" this by making an unreadable tmux count as zero mains:
    that is the C14 polarity error and it hands out occupied slots.
  - [ ] **C15 — `caps.max_concurrent_mains: 4` is saturated at 4/4. STILL 4, not 6** — checked
    2026-07-29, and the "already raised to 6" recollection is a **key conflation**, which is worth
    recording because it is the exact hazard C9 was about. The 3 → 6 bump (`9b6c4f13`) raised
    `max_spawns_per_day`, the DAILY-ACTION key, and C9 (`8cbe50c0`) **superseded** that key with
    `max_concurrent_mains: 4` — the value chosen by operator decision at the time, against a
    then-steady state of 3 live mains. `git log -L` on the line shows no later change; the working
    tree is clean; `probe` reads **4/4** (`claude-gpu-lane`, `codex`, `coordinator-agent`,
    `fable-auditor`). So the saturation is current, not stale.
    I did not set it to 6, deliberately: re-reading the old 6 as a concurrency figure is precisely
    what `resolve_spawn_cap()` refuses to do in code — six spawn ACTIONS per day is not six
    SIMULTANEOUS mains, and doing it by hand would grant capacity no decision covers. **Operator:
    say a number and it changes in one line.**
  Original list: Claude Stop/SessionStart drain hook
  (clone `*_context.sh`) · send-keys adapter behind `OP-SENDKEYS-CODEX` (OFF; rate-limited;
  idle-pane check) · hybrid triage (dead-agent drafts + routing annotations; budget-capped;
  `DRAFT-UNREVIEWED`) · headless workers via `claude_via_devc.sh` under caps. Accept: per
  feature as specced. Rollback: per-flag disable.

### C24–C31 — defects surfaced by the FIRST cold-start coordinator instantiation (2026-07-29)

2026-07-29 was the first time the `coordinator-agent` role was instantiated **from scratch after a
host reboot**, via the `/coordinator-agent` skill, rather than continuing in a session that had
watched the fleet grow. That is a different code path in practice even though it is the same code:
nothing was live, every heartbeat was a survivor of a dead process, every window had to be
re-created, and the roster ids had to be re-spawned onto identities that already had history. Eight
defects fell out of it. They belong to **C-OWN** (adopted by roster id `auditor`) and they are filed
here rather than in the cold-start brief because the brief is read once and this file is the ledger.
The through-line is the one this module keeps re-learning: **a reboot does not produce a clean
slate, it produces a fleet of stale artifacts that every liveness predicate reads as live.**

- [x] **C24 — `cmd_spawn` seeded the heartbeat only-if-absent, so every RE-spawned roster id was
  unreachable from birth.** ✅ 2026-07-29 — commit `42f27e69`. The seeding loop wrote all four bus
  files under `if not p.exists()`, which is correct for an inbox/outbox/cursor and catastrophic for
  a heartbeat: a heartbeat is a **liveness claim**, and a re-spawned identity inherited its dead
  predecessor's. The trap closes on itself — `cmd_nudge` refuses on `state == working` and refuses
  on age (`tmux_adapter.py:604-609`), and the fresh session cannot clear either, because it has not
  been told to drain and it **cannot be told: the telling is what the guard refuses**. Measured
  post-reboot: **all three pre-existing roster ids were undeliverable**, `codex` (now `inference`)
  on BOTH state and age, its heartbeat still reading `working` on
  `e8-deterministic-completion-repair` from a session that no longer existed.
  Fix: the heartbeat is now written **unconditionally** (`tmux_adapter.py:855-890`); the cursor is
  deliberately still only-if-absent, because a cursor is a read POSITION, not a liveness claim —
  resetting it would re-deliver everything the identity already drained.
  **Polarity, stated because the whole fix rests on it:** overwriting a heartbeat is safe only
  because `cmd_spawn` refuses when `args.agent in ids` (`tmux_adapter.py:790`) and therefore
  *proves* the id is not live before it reaches the write. That proof is exactly as strong as
  `live_mains()` never undercounting. **If `live_mains()` can undercount — the C14
  capacity-inventing direction — this fix can reset a LIVE main's heartbeat and re-open it to a
  mid-generation nudge.** C24 and C14 are now coupled: a future change that relaxes `live_mains`
  toward undercounting does not just invent a slot, it silences a working agent's own guard.
  5 assertions added to `scripts/coordination/tests/test_tmux_adapter_live.py` (state reset to
  idle, `task_id` cleared, `ts` refreshed, the re-spawned main is not heartbeat-blocked, and the
  cursor offset is PRESERVED); suite 43/43 green at fix time.
  **Why the pre-existing re-spawn test missed it, which is the reusable part:** the C9 slot-return
  case at `test_tmux_adapter_live.py:332-338` deletes all four bus files before re-spawning. With
  the files gone, only-if-absent and unconditional are indistinguishable. That deletion is exactly
  the shape **a reboot does NOT produce** — the real post-reboot shape is the four files surviving
  with a `working` state on a dead pid. Same family as the C6/C9 fixture rule: a fixture that
  removes the precondition under test passes an implementation that cannot handle it.
  - [x] **C24 review — needs an independent reviewer, not the author.** ✅ 2026-07-29 — `auditor`,
    commits `3d509613` (comment + invariant test) and `2eb51796` (ledger). **Answer to the one
    question: YES, `live_mains()` CAN return a set missing a genuinely live id, without refusing.**
    Demonstrated against the real session — rename a window without updating `config.yaml` (its own
    drift trigger #1) and a live main drops out of `ids` while the function returns a SMALLER SET,
    not `None`. So `args.agent in ids` passes and the reset lands on a live main. **The safety
    argument above names a guarantee that does not exist and is hereby corrected.** The reset is
    safe for a different reason: *an identity `live_mains` cannot see is an identity
    `resolve_target` cannot reach* — their matching rules coincide, so undercount implies no nudge
    target, and `not target` is itself a `probe()` blocker. resolve_target, not the heartbeat, is
    the last line of defence. The hazard is otherwise real: the write clears BOTH heartbeat blockers
    at once, and on a DETACHED session (the normal overnight state) `quiet_check` is skipped by
    design. **Verdict: ship C24 — it replaces a certain, 3/3-reproducible failure with one that is
    separately blocked.** The invariant was emergent, undocumented and untested; now pinned by
    `test_c24_undercount_implies_resolve_target_refuses` over 5 drift shapes, with a positive
    control (a resolve_target that refused everything would otherwise satisfy it) and an assertion
    that the fake reproduces tmux's rc=0 fallback rather than failing on a miss. Mutation-checked.
    One live counterexample was found and fixed — see **C32**. This also pays **C11**.
  - [x] **C24 ledger — the reset must leave a durable trace.** ✅ 2026-07-29 — commit `2eb51796`.
    The reset announced itself only on stdout, so the most consequential thing `cmd_spawn` does —
    destroying the evidence of what a previous session was doing — was the one action the ledger did
    not record. `record()` gained `**fields`; the row keeps the VALUE overwritten (state, task_id,
    ts), not merely the fact, and is written BEFORE `new-window` so a later failure cannot swallow
    it.
- [x] **C25 — `cmd_spawn` names the window after the roster ID, `resolve_target` verifies the
  window named by the ENDPOINT, and nothing reconciles them.** ✅ 2026-07-29 — `auditor`, commit
  `a59a8ac5`. The window name is now derived from the endpoint via `parse_endpoint_window`; an INDEX
  endpoint is REFUSED rather than guessed at (tmux assigns indexes, so a spawn cannot promise the
  window lands on the one the endpoint names, and a mismatch is exactly this defect). The dead
  `target, why = resolve_target(...)` assignment at `cmd_spawn:802` is deleted and the call
  reinstated where it earns its keep — AFTER the window exists, verifying the spawned main actually
  resolves, warning rather than aborting since the window and bus files are real by then. 6 checks;
  the load-bearing one asserts DELIVERABILITY, not the window name, because asserting the name would
  pass an adapter that names it correctly and still cannot be reached. Side benefit: this removes
  drift trigger #1 for name endpoints, which the C24 containment argument depends on. *Observed live 2026-07-29 during
  post-reboot bring-up.* Spawn creates the window with `-n args.agent`
  (`tmux_adapter.py:899`), while `resolve_target` takes the window component of the endpoint and
  **verifies it** (`tmux_adapter.py:311-335`, the C6 anti-guess check). For roster id `codex` with
  endpoint `tmux:agent:codex-inference`, spawn therefore created a window named `codex` and every
  subsequent nudge refused with "does not resolve" — correctly, since the adapter must never guess
  a pane. Worked around by hand with `tmux rename-window`; that workaround is not a fix, it is a
  step nobody will remember next reboot. Real fix: **derive the spawned window name from the
  endpoint**, not from the id, so the two agree by construction rather than by an operator
  remembering they differ. (Today's roster resolves the mismatch away — `inference` has endpoint
  `tmux:agent:inference` — which makes this latent again and is exactly why it should be fixed
  while the failure is still remembered.)
  **Polarity: this is delivery-only, not a capacity bug.** `live_mains()` counts an id live if a
  window carries its **id OR its resolved endpoint** (C14's deliberate overcount), so the mismatched
  window was still counted and the concurrency cap held. Only the send path broke. Do not "fix" this
  by relaxing the endpoint verification in `resolve_target` — that check is C6, and its failure mode
  is typing into someone else's pane.
- [x] **C26 — the coordinator-daemon's `status` reports a live daemon from a stale state file, with
  no PID check.** ✅ 2026-07-29 — `auditor`, commits `9ffd094f` (pid) and `a75c7e90` (boot time).
  BOTH checks the row asked for landed. `daemon_liveness()` is tristate: `PermissionError` means the
  process exists under another uid (alive, not absent), and an unusable pid returns None and prints
  "(unverified)" — "I cannot tell" is never rendered as either alive or dead. `heartbeat_predates_boot()`
  closes what the pid check cannot: `os.kill(pid, 0)` answers "does a process with that number
  exist", not "is it MY process", and pid numbering restarts at boot, so a recycled pid would have
  made the fix a fresh fail-open in the very scenario that raised this. That verdict OVERRIDES the
  pid check rather than supplementing it. The heartbeat's own claim is annotated, never overwritten —
  what the last daemon believed is evidence worth keeping. 8 tests. *Verified 2026-07-29 with `ps -p`.* Post-reboot the daemon was dead, and
  `session_bus_coordinator.py status` printed
  `state=working epoch=11 pid=1928027 age=2157s` — for a PID that **did not exist**. `cmd_status`
  (`session_bus_coordinator.py:2233-2240`) reads `heartbeats/coordinator-daemon.json` and prints
  `state`/`epoch`/`pid` verbatim, deriving `age` from the file mtime; it never asks whether the pid
  is alive. This is a fail-open on the one command a cold start uses to answer "is the control
  plane up?" — **a coordinator that trusted `status` would have concluded the daemon was healthy
  and moved on, leaving relay, ACK redelivery and C8 boundary surfacing all dead while the dashboard
  said working.** Two cheap checks close it, and both should be present: verify the pid is alive
  (`os.kill(pid, 0)` / `/proc/<pid>`), and refuse to report a live state when `age` exceeds **system
  uptime**, since a heartbeat older than the boot cannot describe a running process. Report
  `state=STALE (pid N not running)` rather than the recorded state. Same family as C3/C18: a
  recorded claim is not an observation.
- [x] **C27 — two operator SIGNATURE REQUESTS were never relayed, and the documented cold start
  would have reported no gates pending. Cross-ref: PRIORITY 1 in
  `coordination/session-bus/tasks/auditor-c-own-20260729.md`.** *Verified 2026-07-29 by direct file
  inspection.* Two well-formed `token-request` messages from `codex`, both `to: coordinator-agent`,
  both with `needs_routing_to: ["coordinator-agent"]` and `action_required: true`:
  `msg-20260729T101827Z-64-codex` (`RATIFY-P-BENCH-4-FG4B-AFFINITY-20260729`, 10:18:27Z) and
  `msg-20260729T111638Z-68-codex` (`RATIFY-E8-FINAL-C1-RETRY-CAPACITYFIX-20260729`, 11:16:38Z).
  Neither reached `inbox/coordinator-agent.jsonl` (grep count for both token names: **0**) and
  neither reached `tokens/token-queue.md`, whose *Pending token requests* section reads
  `_(none …)_` at line 40-42. `rebuild` reports "2 pending", which sounds reassuring and refers to
  the unrelated M5 flags. The triage report found both **only by outbox scan**, annotating each
  *"NOT in your inbox — found by outbox scan; the relay may never have delivered it"*.
  **Why this is the worst one in the batch:** it is the C3/C6/C8 fail-open family one layer up. Not
  a lost message — a lost *request for a human signature*. A coordinator following the cold-start
  procedure exactly, reading `token-queue.md` as the authority it is documented to be, concludes
  **no gates are waiting** while two ratifications sit unsigned in a sender's outbox. The
  outbox-scan triage is what saved it, and triage is a backstop, not the channel.
  Investigation must land on where in the relay path a `token-request` is supposed to become a
  `token-queue.md` block (M4 specifies the transform, `authority` is still `manual`), and whether
  the answer is "the code is inert at this authority level" — in which case the DOCUMENTED cold
  start is wrong to treat `token-queue.md` as complete, and must scan outboxes until M4 is live.
  **✅ 2026-07-29 — `auditor`. ROOT CAUSE, and it is worse than "not relayed": at `authority:
  manual`, `kind: token-request` had NO DELIVERY PATH AT ALL and was dropped silently, by
  construction. The daemon being down is not the explanation** — reproduced with the daemon healthy
  (`artifacts/bus-audit-20260729/repro_token_drop.py`). Three mechanisms composed: (1)
  `_NO_RELAY_KINDS` excluded the kind from the only always-on path, acted on with a bare `continue`
  — no advisory, no defect, no trace; (2) the "other path" that justified the exclusion,
  `relay_tokens`, was reachable only from `apply_assignment`, gated on `authority == "assign"`,
  while `config.yaml` is `manual`; (3) the C20 safety net — built for exactly "a human signature
  request went unseen" — scanned the coordinator's INBOX, which step (1) guarantees can never
  contain a `token-request`. **The last-hop net was searching a set that structurally cannot contain
  what it looks for.** Corroboration: `tokens-relayed` and `operator-bypass-escalated` each appear
  **0 times in all 31,405 advisory records**. Answers to the four questions in the brief: the
  transform is `relay_tokens` → `apply_assignment:2074-2078`; **the RELAY dropped them**, not the
  transcription (it renders a correct block when invoked) and not the queue render (nothing was ever
  written to render); **not a durability defect** — both functions are stateless full-outbox rescans
  deduped on `gate_id`/`relayed_src`, so nothing was lost; **`task-complete` and `task-propose` can
  be lost identically** and were verified so by the same harness (`transcribe` is also assign-only;
  `intake_proposals` is reachable ONLY from the manual `intake` CLI — `tick` has never called it at
  any authority). Fixed in three commits, each with its tests: `91dafa1e` presentation moves to the
  always-on tier (transport, not judgment — the HELD_OP_GATE rows stay assign-only, and
  `relay_tokens`' block and row are now INDEPENDENTLY idempotent, without which the always-on write
  would have silently swallowed the hold row); `31129b7b` `_RELAY_HANDLERS` maps kind →
  (handler, authority-it-runs-at) and relays + emits a defect when the handler is unreachable;
  `ef5598f5` gives C20 an outbox input. Measured before wiring: 24 operator-kind outbox rows live, 3
  unevidenced — two of them these gates. Standing rules codified in `BUS_PROTOCOL.md`.
  - [x] **The old test asserted the defect.** ✅ 2026-07-29 —
    `test_c2_no_relay_kinds_are_not_fanned_out` parametrized over the CONSTANT set, so it pinned the
    silent drop of `task-complete` and `task-propose` at manual authority as correct behaviour.
    Rewritten against the authority-derived set.
- [x] **C32 (NEW) — `resolve_target` exempted INDEX endpoints from its own verification and reported
  the result as "(verified)".** ✅ 2026-07-29 — `auditor`, commit `9c714eed`. Found while paying the
  C24 review. The check read `if got.strip() != want and not want.isdigit()` — it compared every
  endpoint against the window NAME and waived the comparison for numeric components, because an
  index never equals a name. So for index endpoints it **trusted the string**, which is the precise
  thing the function exists to prevent (its own comment records the 2026-07-27 measurement and says
  trusting it "would have let send-keys hit the wrong pane"), and then returned a **false
  attestation**. Measured, worse than first reported: `display-message -p -t sess:7 '#{window_name}'`
  exits **0 with EMPTY output** when the session does not exist at all, so `tmux:no-such-session:7`
  was attested as verified; for an out-of-range index in a live session tmux falls back to window 0
  — the operator's own window — and a nudge would have typed into it.
  **This was the one live counterexample to C24's containment invariant**: uncounted by
  `live_mains` AND resolvable, which is exactly the pair that must never both hold. Latent, not
  live — no roster row uses an index endpoint today, but C14 lists `tmux:agent:3` as a supported
  resolved form and no test used one, which is how the exemption survived.
  Fix: request `#{window_index}\t#{window_name}` in one call and verify against the component that
  was actually named; an unreadable reply refuses rather than attests. **The unit-group fixture
  pinned the bug** — `check(t == "sess:7", "explicit window in endpoint resolves")` asserted a
  verified resolution for an absent session; corrected, and the live group gained real index
  coverage. A refusal is recoverable by asking again; a false "verified" is not.
- [x] **C33 (NEW) — a `token-request` refused for lack of dry-run evidence tells nobody.**
  ✅ 2026-07-29 — `auditor`, commit `e428d70f`. Found while verifying C27a against a throwaway copy
  of the live bus. `relay_tokens` correctly refuses to present an unvalidated command (agent defect
  by policy) but reported the refusal ONLY as an advisory row — and `advisory.jsonl` is delivered to
  nobody. So a gate can be filed, be schema-valid, be silently never presented, **and the notice
  about that be a second durable-but-unread sink one level up.** C18's second half exactly.
  **LIVE INSTANCE, not hypothetical:** `mainA` filed `E5-THROTTLE-SCOPE-ERA-ROW-20260729` at
  2026-07-29 **15:18:28Z** with `action_required: true` and `needs_routing_to: [coordinator-agent]`,
  carrying `apply_command` + a top-level `dry_run_evidence` rather than the
  `validated: {cmd, dry_run_exit}` object the relay reads. A THIRD lost signature request beyond
  C27's two, by a different mechanism.
  **CORRECTION 2026-07-29 (same session):** this row and commit `e428d70f` originally stated
  *"the SCHEMA ACCEPTS that shape; the relay does not."* **That was wrong.** It was measured under
  `/usr/bin/python3`, where `validate_row` silently degrades to a six-required-key check — the exact
  fail-open now filed as **C34**. Under the venv interpreter the daemon actually uses, the schema
  **REJECTS** it too (`payload: 'validated' is a required property`). The C33 fix and its tests are
  unchanged and still needed; only the stated cause was wrong, and it understated the problem — the
  real question is not "why does the relay disagree with the schema" but "how did a schema-invalid
  row get written at all", which is C34. Fix: the notice goes to
  `coordinator-agent`'s inbox (drained every task boundary), deduped once per `gate_id` against its
  own durable evidence, naming the concrete repair; `relay_tokens` now carries `gate_id`/`msg_id` as
  FIELDS so the notice never parses prose out of `detail`.
  - [ ] **OPEN — align the schema with the relay contract so `append` refuses at AUTHORING time.**
    Failing at the author is the right place; today a schema-valid gate can be structurally
    unpresentable. **This is a CONTRACT change and is deliberately NOT made here** — it is a
    coordinator/operator call, and tightening it invalidates `mainA`'s existing row, which would
    have to be re-filed. Escalated on the bus with options. **Superseded in part by C34:** the
    schema already requires `validated`; what failed is that authoring never applied the schema.
- [x] **C34 (NEW) — the two sides of the bus run different validators, and only one says so.**
  ✅ 2026-07-29 — `auditor`, commit `25eb2b0a`. Found while measuring `advisory.jsonl` growth.
  `validate_row` degrades to a six-required-key check when `jsonschema` is unavailable — documented
  and deliberate — but **on the SUCCESS path it returned silently**, so "validated" and "checked six
  keys exist" were indistinguishable to the caller. That distinction is the whole ballgame, because
  the two sides run different interpreters: **agents author with `python3
  scripts/coordination/session_bus.py append ...`**, the command `CLAUDE.md`, `BUS_PROTOCOL.md` and
  every task brief specify, and `/usr/bin/python3` has **no jsonschema**; the coordinator-daemon runs
  under the orchestrator venv, which has 4.26.0, so relay applies the FULL schema. A message passes
  authoring, is refused at relay, and is never delivered — the write succeeded, the send did not,
  and nobody is told.
  **MEASURED: 217 of 341 live outbox rows (64%) are in exactly that state**, because the roster
  rename added `_renamed_from` to migrated rows and the schema forbids additional properties. 12 are
  operator items — including BOTH C27 gates and three of `mainA`'s. The warning is now unconditional
  on stderr; it does NOT refuse, because refusing would break every agent on the documented command
  with no interpreter to switch to mid-task, trading a silent gap for a total outage.
  Second half, same commit: **the schema-invalid defect had no dedupe** — the one defect path in
  `relay_outbox_messages` that appended unconditionally (C18's branch has keyed on `already_flagged`
  since it was written). An outbox row is never repaired by the daemon (single writer), so an invalid
  row is invalid forever. Measured: 249 distinct shapes re-emitted per tick, **~20,000 advisory
  rows/hour**, 33,074 `defect` rows in a **38.5 MiB** `advisory.jsonl` that `already_flagged` then
  re-reads IN FULL every tick, on the daemon's hot path. 4 tests.
  - [x] **DISPOSITION of the 151 residual rows — recommendation, 2026-08-11 `mainD`.**
    Re-measured after the fix: **151 of 1251 outbox rows (12%)**, down from 368/32%. The operator's
    368 is the pre-fix number. Three facts decide it:
    (1) **The leak is already stopped. ZERO invalid rows were authored after the authoring gate
    landed** (`035dfecf`, ~09:15Z); the newest is 08:59Z and the oldest 2026-07-29. So
    *gate-new-writes-only* is **already done and needs no operator decision**.
    (2) **All 151 were never delivered** — they are lost communications, not cosmetic lint.
    (3) Repairability splits 114 mechanical (extra top-level keys that belong in `payload`) / 20
    with genuinely missing content / 17 whose `kind` is outside the enum and needs a human choice.
    **RECOMMENDED: triage-by-value, not repair-all, and NOT quarantine.** An outbox is append-only,
    so "repair" can only mean re-authoring a corrected copy as a NEW row citing the original id —
    and re-filing 151 rows aged 13 days would recreate **C40** exactly: a burst of stale mail that
    reads as fresh instructions, which is what cost `mainA` and `mainB` their first hour today.
    So: each owner re-files only what is *still live*, citing the original id; the rest stays as the
    historical record it is. Per-owner counts: `mainB` 81, `mainD` 49, `coordinator-agent` 19,
    `mainA` 1, `mainC` 1. **Mine are all 2026-07-29, from a previous `mainD` session, on unrelated
    tasks (RC-9, HG-3, DAR-5.5, …) — none is still live, so my 49 need no re-filing and I am not
    manufacturing 49 stale messages to prove a point.** Quarantine is rejected for the same reason
    deletion was rejected in the non-roster residue: I only knew those messages mattered because
    they were still readable.
  - [x] **OPEN — make the two sides agree, and unstick the 217 rows.** ✅ Both done 2026-08-11;
    see the C34 body above. Two coupled contract calls,
    escalated with options: (i) which interpreter is authoritative for authoring (pin the venv in the
    documented command, install jsonschema for the system python, or ship a wrapper); (ii) whether
    `_renamed_from` should be permitted by the schema (it is provenance the rename deliberately
    added to preserve history) or stripped from the 217 rows. **Until one is chosen those 217 rows,
    including both C27 gates, remain un-relayable to any inbox.** Note the C27a/C27c fixes DO still
    present the two gates to `token-queue.md` — `relay_tokens` reads outboxes directly and does not
    validate — so the operator path is unblocked even while the inbox path is not. Verified.
- [x] **C28 — relay is tracked by destination FILE, not by message identity, so moving an inbox
  re-floods it.** ✅ 2026-08-11 — `mainD`, commit `2e01d5dd`. Fixed together with **C38**, because
  they are the same defect asked twice: both ask *"what has this daemon already done"* and both
  answered by re-reading the thing it had acted on. Delivery is now keyed on message identity in a
  daemon-owned `relay_state.json` — the C18 rule each of them half-applied. Measured: **104 KiB,
  0 ms steady-state read**, exact round-trip. Bootstrap (no ledger on disk) rebuilds from the
  inboxes plus a STREAMED advisory pass in **0.54s**, paid once per ledger lifetime rather than
  every 45s. **Fail-safe direction is deliberate:** a missing or corrupt ledger degrades to
  bootstrap — today's semantics, reading what is actually there — never to an empty set that would
  re-deliver everything; pinned by a test over empty / torn / unknown-schema files. The save
  happens AFTER the relay pass, so a crash loses at most one tick of ledger updates, never a
  delivery. Test reproduces the exact trigger: an inbox emptied after delivery is NOT re-flooded,
  and a second tick over the same outbox is a no-op while the first still delivers.
  **⚠ COMMITTED, NOT LIVE — added 2026-08-11 after `auditor`'s same-day commit audit caught this box
  closed with before/after numbers while the running daemon executes the pre-fix code.** `pid 496387`
  started 08:48:00, before `2e01d5dd`; `coordination/session-bus/relay_state.json` **does not exist on
  the live bus**, which is the proof. The measurements above are real and were taken by direct
  invocation; the RUNNING PROCESS has none of it. The fair part of the hit: I disclosed exactly this
  condition for C39 the same morning and then did not for C28/C38 — the defect class I spent the day
  closing, inside my own closure. Restart is `coordinator-agent`'s. *Observed 2026-07-29 during the roster rename.* Renaming the roster ids meant
  `git mv inbox/<old>.jsonl inbox/<new>.jsonl`; the running daemon then re-delivered its **entire
  relay history** into freshly recreated old-id inboxes. Measured in the preserved copies under
  `coordination/session-bus/archive/pre-rename-20260729/`: 16 / 13 / 22 / 17 rows across the four
  ids (`claude-gpu-lane`, `claude-main`, `codex`, `fable-auditor`). *(The in-session recollection of
  "22-39 rows each" is not what the archived files measure; the counts above are what is on disk
  today, and the archive is the record.)* The idempotency key is `relayed_src` **checked against the
  destination file**, so an absent or truncated destination reads as "never relayed". Consequence,
  stated generally because the rename is not the only trigger: **any operation that moves,
  truncates, rotates or restores an inbox re-floods it**, including a well-intentioned cleanup or a
  log rotation. Fix direction: track relay completion in daemon-owned state keyed on the message
  identity (`relayed_src` in a daemon-owned ledger), not by re-reading the file it was delivered
  into — the same "derive it from what the thing itself leaves behind, in a place the operation
  cannot erase" rule C18's second half already applied to notice idempotency.
- [x] **C29 — `drain --agent <non-roster-id>` fails OPEN.** ✅ 2026-07-29 — `auditor`, commit
  `e510a091`. **The gap was WIDER than filed: three verbs take an identity and never validated it.**
  `drain` (exit 0, printed another agent's mail, advanced a cursor); **`triage`, which is the worse
  half** — `routed_view` filters on membership, so an unknown id matched nothing and got
  `(triage: no routed messages awaiting <id>)` at exit 0, indistinguishable from "you are clear",
  turning the LOUDEST signal on this bus into a silent all-clear for a stale or typo'd id; and
  `cursor`, where `required_writer` accepts any stem under `cursors/` and so answers "may this agent
  write this path", never "is this agent real" (`cursor --agent another-ghost --set 5` exited 0 and
  created the file). All three now use `_require_roster_id`.
  **REFUSE, not warn — the deliberate choice this row asked to be recorded.** A warning leaves the
  cursor advance in place, which silently CONSUMES another agent's mail: the read is the damage, not
  the exit code. The mid-rename hazard is real but measured-bounded — no automated caller uses a
  stale id (the daemon interpolates roster-derived ids) and the only stale reference is one line in
  an archived task file. The identity check runs BEFORE the C3 file check and does not replace it:
  telling someone to `provision` a non-roster id sends them to a command that also refuses, so both
  messages survive and are pinned. 9 tests. *Verified 2026-07-29 with
  `drain --agent codex` after `codex` had been renamed out of the roster.* `cmd_drain`
  (`session_bus.py:692-729`) checks only that the inbox FILE exists (the C3 fix) — it never calls
  `_require_roster_id`. So an unknown id with a leftover inbox exits **0**, prints messages, advances
  a cursor, and never says the identity has no roster row. By contrast `append --agent codex` fails
  **CLOSED** with the valid id list (`session_bus.py:450` → `_require_roster_id`, 141-145). The two
  halves of the same CLI disagree about whether an identity must exist.
  This is not academic and C28 is why: relay **recreates** old-id inboxes, so the file-exists check
  passes for exactly the ids that no longer exist. A session that keeps using its pre-rename id
  drains a ghost inbox cleanly, sees "no new messages", and concludes it is up to date — the precise
  C3 failure, one identity-check short of being fixed. A drain on an unknown id must warn loudly
  (and the deliberate choice between warn and refuse should be recorded, since refusing changes
  behaviour for anyone mid-rename).
- [ ] **C30 — the backend a main runs on is invisible to the bus, and spawn reports success for a
  window that died a second later.** Two halves of one gap — **(b) is DONE, (a) is still open:**
  (a) **The launch command is not roster data.** `cmd_spawn --command` defaults to
  `cd /workspace && claude` (`tmux_adapter.py:931`) and no roster row carries a launch command, so
  which backend an identity runs on lives only in the head of whoever types the spawn. That was
  tolerable while ids were named after their backend; it is **not** tolerable now, because the
  2026-07-29 rename made roster ids deliberately **model-agnostic** (`inference`, `mainA`, `mainB`,
  `auditor`) precisely so a main can move between backends — including onto a local model. The thing
  the rename made variable is the thing the bus does not record. It belongs in the roster row as
  data, next to `endpoint` and `lanes`.
  (b) **Spawn confirms `new-window` exit 0, not a surviving window.** A spawned `codex` pane died
  instantly and silently because the codex CLI presented an update prompt on start; the window
  vanished, `cmd_spawn` still reported success, and only a manual `tmux list-windows` revealed it.
  `cmd_spawn` returns on the `new-window` return code (`tmux_adapter.py:899-901`) — which reports
  that tmux accepted the request, not that anything is running in it. Verify the window still exists
  a few seconds after creation before reporting success. Note the polarity: a false success here is
  worse than a false failure, because the four bus files are already written and the identity now
  looks provisioned-and-live to everything downstream, including the C24 heartbeat reset.
  **✅ 2026-07-29 (b) only — `auditor`, commit `dfb775f7`.** `cmd_spawn` re-checks the window list
  after `SPAWN_SETTLE_S` (2s, module-level so tests drive it to 0), records `spawn-died`, returns
  EX_BLOCKED and writes NO `spawn` row, so the ledger never claims a live window that is not there.
  The message states that the four bus files are LEFT IN PLACE and a retry reuses them. One
  deliberate asymmetry, tested: an UNREADABLE window list does NOT manufacture a failure — elsewhere
  in this module an unreadable signal fails closed, but here the window and bus files already exist
  and a transient tmux hiccup must not send an operator to tear down a healthy session, so the check
  fires only on positive evidence of absence. Proven against REAL tmux (`true` is reaped in ~0.3s,
  well inside the settle window) — the only place it can be. 3 unit tests + 3 live checks.
  **Reusable finding: the shared C9 test harness was pinning a false pass.** Its fake tmux answered
  `list-windows` from a fixed string and never showed a window it had just created, so every spawn
  test would have read as "the window died instantly". It now reflects its own `new-window` calls.
  - [ ] **(a) STILL OPEN — the launch command belongs in the roster row as data.** `cmd_spawn
    --command` defaults to `claude` and no roster row carries a launch command, so
    which backend an identity runs on lives only in the head of whoever types the spawn. The
    2026-07-29 rename made roster ids deliberately model-agnostic precisely so a main can move
    between backends — **the thing the rename made variable is the thing the bus does not record.**
    This is a ROSTER SCHEMA change (a contract), so it is escalated rather than taken.
- [x] **C31 — the nudge rate limit is keyed to the roster ID, not the window instance, so a
  re-spawned main is silenced by nudges sent to a window that no longer exists.** ✅ 2026-07-29 —
  `auditor`, commit `66f60536`. The limit now only counts nudges sent AFTER the newest `spawn`
  ledger row for that agent, so it is keyed on (agent, window instance). The spawn epoch comes from
  the ledger the adapter already writes — no new state file, and nothing that can disagree with one.
  Timestamps are PARSED rather than string-compared, so a future `_now()` format change cannot
  silently break the ordering. Two deliberate fail-safe choices: a window created outside
  `cmd_spawn` leaves no spawn row and keeps the whole-history limit (the windows this adapter knows
  least about keep their guard), and an unparseable nudge ts is skipped exactly as before rather
  than being widened into a permanent block — a corrupt ledger row that wedged nudging fleet-wide
  would be strictly worse than one missed rate limit. `probe` now reports
  `nudges_this_window_instance` and `spawned_at`. 6 tests; the load-bearing one is the positive
  control, because "ignore old nudges" is otherwise satisfied by ignoring ALL of them, which deletes
  the rate limit rather than re-keying it. **The C24 coupling noted in this row is now closed on
  both sides** — C24 stops a re-spawned main being heartbeat-blocked, C31 stops it being
  rate-limit-blocked instead. *Observed
  2026-07-29 during bring-up.* `probe` computes `seconds_since_last_nudge` as the newest
  `kind == "nudge"` ledger row for that **agent id** (`tmux_adapter.py:559-560`), and `cmd_nudge`
  refuses below `--min-interval-s` (default 600, `tmux_adapter.py:685-687, 923`). After a window was
  killed and re-spawned, nudges to the **fresh** window were refused for the remainder of the 600s
  window because a nudge had gone to the **destroyed** one minutes earlier. The rate limit exists to
  avoid pestering a working session; a session that did not exist when the earlier nudge was sent
  cannot have been pestered by it. Fix: killing or re-spawning a main resets its nudge ledger entry
  (or the limit keys on (id, window-instance) — a spawn epoch per identity, mirroring the daemon's
  epoch fencing). Same root cause as C24 one field over: **state keyed to an identity outlives the
  session that identity named**, and every predicate that reads it inherits the lie.
  Note the interaction, since both landed in the same hour: C24 makes a re-spawned main *not*
  heartbeat-blocked, and C31 then rate-limit-blocks it anyway. Fixing one without the other leaves
  the fresh session unreachable, which is the symptom C24 exists to remove. *(M5a already flags the
  600s default as an implementer's guess rather than an operator decision — C31 is about the KEY,
  not the value, and the two are independent.)*

- [x] **C35 — a `working` heartbeat wedges a session forever, because the code that would clear it
  is the code that has stopped running.** ✅ 2026-07-29 — `claude`, commit `7a159781`. `cmd_nudge`
  refused whenever the target's heartbeat said `state: working`. That guard is right in principle —
  typing into a pane mid-generation corrupts whatever is running there — but a main that FINISHES a
  unit and settles at its prompt very often still says `working`, and it cannot clear the flag
  because clearing it requires being told to, which is exactly what the guard refuses.
  `--heartbeat-max-age` does **not** rescue it: the refusal keys on STATE, not age, so a
  five-second-old heartbeat wedges the session just as hard as an ancient one. *Measured 2026-07-29:
  the operator hand-relayed into panes at least four times in one day, including into `mainA` while
  it held the ENTIRE machine for an exclusive E5 decision-grade window — the most expensive possible
  idle state, since nothing else can use the host either. One stretch saw ten consecutive nudge
  attempts refused against a session provably sitting at an empty prompt.*
  **Fix:** pane quiescence now outvotes a `working` heartbeat past a long threshold, behind a new
  `--heartbeat-override-quiet-s` (default 120). Both TUIs redraw a spinner with an elapsed-seconds
  counter while generating, so a window quiet for minutes is strong evidence the session is settled
  at its prompt regardless of what it claims. This is the same reasoning the existing `--quiet-s`
  check already encodes, at a 6x longer and therefore much safer horizon.
  **Calibrated before implementing, in disposable `tuiok-*` sessions created and killed by the
  measurement — the live `agent` session was never written to.** A window emitting 5x/second never
  exceeded **1s** of apparent quiet across the full matrix of {detached, attached} x {background,
  active}, while an idle window aged monotonically (35→51s, 54→70s, 73→90s, 84→139s). 120s is thus
  ~120x the largest gap ever seen on a window that was genuinely producing output. Corroborated
  read-only against the live session: working mains and the redrawing htop/btop windows sat at 0-2s
  while two settled mains showed 209s and 211s.
  **Two earlier attempts at this same measurement were wrong**, both worth knowing before anyone
  re-measures: (a) the default shell here is fish, so a bash-syntax loop handed to `tmux new-window`
  dies instantly while `new-window` still exits 0 — C30(b) met again in the measurement rather than
  in production; (b) `automatic-rename` renames a window to its running command, after which a
  NAME-based target stops resolving and `display-message` silently falls back to the session's
  CURRENT window, so several windows report one window's numbers. Both artefacts produce the same
  false reading — "a busy window looks quiet" — which would have argued *against* this override.
  **Scope is deliberately narrow.** The override suppresses the `state == working` blocker and
  nothing else: pane existence, `pane_dead`, the normal quiet check, the rate limit, the
  authorisation flag and target resolution all still refuse independently, and every unreadable
  input fails closed (an unparseable `window_activity`, a `display-message` failure, a dead pane, a
  missing heartbeat). A non-positive threshold disables the override entirely rather than meaning
  "override always", so a mis-set 0 is inert. **Staleness stays a separate blocker on purpose** — it
  is already tunable with `--heartbeat-max-age`, whereas state was not tunable at all, and that
  asymmetry is the whole defect. `probe` reports the override in BOTH directions, so a refusal is
  explained and a human is never surprised by a nudge the guard "should" have refused; an overriding
  nudge also writes `heartbeat_override` + `window_quiet_for_s` into the ledger, while an ordinary
  nudge row is unchanged on disk. 17 stubbed tests + 11 live-pane checks. The load-bearing ones are
  the mid-generation case (a real, still-emitting pane keeps its `working` heartbeat believed) and
  the live PREMISE check, which asserts the empirical claim the design rests on rather than assuming
  it — if a future tmux or TUI stops moving `window_activity`, that check fails loudly instead of
  the operator discovering it as a corrupted pane. Verified by mutation: inverting the threshold
  comparison, removing the recency check, and turning the 0-disable into "always override" each turn
  a test red.
  *Follow-up, NOT done here (needs its own row + owner):* the `attached is False` branch of the
  existing quiet-check claims `window_activity` "does not track output" while detached, citing a
  2026-07-27 measurement. **That claim is falsified** by the calibration above — detached tracking
  works, and is now pinned by a live check in a detached throwaway session. The comment has been
  corrected in place, but the *behaviour* it guards (skipping the normal `--quiet-s` blocker when
  detached) was left exactly as it was, since C35's brief was the heartbeat blocker alone. Removing
  that skip would make the quiet-check STRICTER and close a real fail-open; it should be measured
  and filed on its own rather than smuggled in here.

- [x] **C36 — liveness is decided by the RUNTIME, not by the agent's self-report.** ✅ 2026-07-29 — `auditor`, commits `33eb7306` (signal + backend identification) and `dd9e61d2` (probe wiring). **Codex mains are decided by the runtime; Claude mains fall back and `probe` says so.** Both directions act and both report: runtime ACTIVE blocks whatever the heartbeat says — a protection the pre-C36 guard did not have at all, since a main whose heartbeat wrongly read `idle` mid-generation was nudged without hesitation; runtime IDLE clears both the `working` heartbeat AND its staleness, because once the runtime has spoken a self-report is not evidence about anything. UNAVAILABLE changes nothing and never becomes `idle`. Every other guard stands (pinned by its own test). The PREMISE is asserted as a live test against the real corpus (120/120 tails parse, 118/120 terminal), so a CLI format change fails loudly instead of silently reporting every settled agent as ACTIVE. 18 tests, mutation-verified on five separate mutants incl. the fail-open. Live end-to-end: 4 Codex decided by runtime, 3 Claude falling back explicitly.
  - [ ] **OPEN — the Claude source is an operator/coordinator call.** Escalated: my subagent obtained part of its evidence by decompiling the shipped bundle, which the design doc §7 rules out as a basis. Recommended option is the vendor's documented `claude agents --json` (filtered to `kind == interactive` — it is currently emitting a stale 2026-07-23 background record) with per-pass caching for its ~2s cost. Until answered, Claude mains stay on the heartbeat chain and `probe` reports them as UNAVAILABLE rather than pretending coverage.
- [ ] **C36 residual (superseded framing kept for history)** *Operator-approved
  Option B, 2026-07-29; assigned to `auditor`. Evidence base:
  [`docs/design/agent-session-control-surface.md`](../../docs/design/agent-session-control-surface.md),
  which ranks 14 candidate signals with measurements and disproves several plausible ones.*
  **The root defect:** the heartbeat is written BY the agent, so an agent that has stopped cannot say
  so — and `probe` refuses every nudge on `state == "working"`. That is the deadlock; C35
  (pane-quiescence override) mitigates the symptom, not the cause. A runtime-reported status has no
  such dependency: it is true even when the agent is wedged, because it is STATE, not a timestamp.
  Scope: `probe`/`cmd_nudge` decide from runtime; the heartbeat is demoted to a CORROBORATOR; when
  the two disagree **the runtime wins and `probe` says so in BOTH directions**, the way C35 reports
  its override even when it did not fire. Signals, in priority order: (1) Codex `thread.status` via
  `codex app-server` JSON-RPC (exact, runtime-reported); (2) the Codex rollout terminal record
  (`task_complete` / `turn_aborted`) — no server needed; (3) `claude agents --json` for Claude mains.
  **Note the direction of the NEW protection:** today a main whose heartbeat wrongly reads `idle`
  while it is mid-generation *will* be nudged. Runtime `active` blocks that — a hazard the current
  guard cannot see at all.
  Constraints carried from the dispatch: every other guard stands (pane exists, `pane_dead` false,
  quiet check, rate limit, auth flag, target resolution); fail closed on anything unreadable; an
  UNAVAILABLE runtime falls back to current behaviour, **never** to `idle`. **CPU delta is INVALID
  for Claude mains** — a main burned 17% CPU sitting at its prompt because its subagents run
  in-process. Option A (running Codex mains as `--remote` clients and injecting turns over JSON-RPC)
  is **not** approved; read-only status queries only.
  - [x] **Signal #2 (rollout terminal record) VERIFIED, with four corrections that change the
    implementation.** ✅ 2026-07-29 — `auditor`. The claim's substance holds and is *stronger* than
    the design doc states, but taking it verbatim would have produced a wrong implementation:
    1. **"64/64 correct on today's rollouts" conflates two claims.** 60 of 64 end terminal; the
       other 4 are live TUIs mid-turn — the signal correctly reporting *busy*. Defensible as
       classification accuracy, false as "64 ended terminal". **The corpus number is much better and
       the doc undersells itself: 400 random files from the full 4,233 → 385 `task_complete` +
       15 `turn_aborted` = 400/400.**
    2. **n is 7, not 64.** 57 of today's rollouts are *subagent* files; the population the signal
       serves — user sessions one might nudge — had n=7 today.
    3. **`thread_source == 'user'` is UNSAFE.** 8 corpus files (older `cli_version`) carry no such
       field at all and an equality test misclassifies them. Use `!= 'subagent'` or fail closed on
       absence.
    4. **THE LOAD-BEARING ONE — the parent holds FINISHED subagent fds open.** Measured 16:38Z on
       live pid 257808 (`mainD`): fd 39 → a subagent rollout reading `task_complete`, fd 45 → its
       own user rollout reading `custom_tool_call`. **Picking the wrong fd reports "idle" for an
       agent that is mid-tool-call, and that unsafe reading is available on a live pid right now.**
       The `thread_source` filter is not hygiene; it is the guard.
    Minor: a session's subagent files can sit in a date directory containing **no** parent user
    file (a 31-file group today), so resolve the parent through the fd, never by scanning a date
    dir; and only the musl `codex` binary holds rollout fds (`node` wrappers and
    `codex-code-mode-host` hold none).
    *Robustness, measured:* `tail -n 1` is size-independent (~10 ms; sub-ms in-process) and 1,800
    reads under live append gave **0** parse failures — but the longest record today is 192 KB, past
    any single-write atomicity guarantee, so a torn tail cannot be *proven* impossible. Retry once,
    then report unknown and fail closed. The property the signal rests on does hold:
    `task_complete` is a **stable resting tail**, only ever followed by `task_started` or
    `thread_settings_applied`, never by the frequent mid-turn `token_count`.
  - [ ] **BLOCKED-ON / dependency: C30(a).** C36 must branch on which backend a roster id runs, and
    C30(a) — still open — is exactly *"the backend a main runs on is invisible to the bus"*. The
    2026-07-29 model-agnostic rename made backend a runtime property that nothing records. Escalated
    with options; the default if unanswered is single-backend scope with an explicit fallback and
    `probe` stating which mains are uncovered, because a wrong backend guess makes C36 return a
    confident WRONG answer — strictly worse than the heartbeat it replaces.

- [x] **C37 (NEW) — a dead daemon reported itself healthy for 243 hours, and the pid check that
  was supposed to prevent that had already landed.** ✅ 2026-08-11 — `mainD`, commit `001c06da`'s
  successor on `main` (see `git log -- scripts/coordination/session_bus_coordinator.py`).
  **Dead window measured, not estimated: 2026-08-01T05:42:54Z → 2026-08-11T08:48:02Z = 243.1h**, the
  single >1h gap in `advisory.jsonl`. P1b added the pid check on **2026-07-29**, *before* the death,
  so "there was no pid check" is the wrong story and chasing it would have fixed nothing. Two
  independent holes, both **reproduced against the real module before either was touched**:
  1. **Identity.** `os.kill(pid, 0)` proves a process with that number exists, not that it is this
     daemon. `heartbeat_predates_boot` closes that only ACROSS a reboot — and its own docstring says
     so — but the host booted 2026-07-29 13:41 and never rebooted, so the recycling guard was
     inapplicable for the entire window. Reproduced: a 10-day-old heartbeat naming `pid 1` printed
     `state=working epoch=13 pid=1 age=876736s` with **no staleness note at all**. `pid 1` is
     `/sbin/init`. Now verified against `/proc/<pid>/cmdline`. Unverifiable identity reports *alive
     with the doubt stated*, never dead: a missing `/proc` is a portability fact, and a false DEAD
     sends someone to restart a running singleton.
  2. **Freshness was printed and never judged.** `age=876736s` and `age=19s` produced the same
     verdict: none. A wedged daemon holds its pid and stops ticking, so pid-alive must not imply
     healthy. Bound is 10 missed ticks (floor 120s) — deliberately generous, a false alarm costs one
     glance at `ps`.
  `daemon_verdict` now folds all three checks into **one word, worst wins**: DEAD / STALE / UNKNOWN
  / HEALTHY, and `status` LEADS with it and lists every reason underneath. That rendering change is
  the other half of the defect: healthy and ten-days-dead differed only by a parenthetical several
  fields into a dense line, and for ten days nobody read the difference. The heartbeat's own claim is
  still printed verbatim — evidence, annotated, never overwritten. Verified **both directions on the
  live bus**: HEALTHY/exit 0 for running pid 496387, DEAD/exit 1 for the reconstructed heartbeat.
  22 tests.
  - [x] **The pull-only gap is closed IN-BAND, with no host change.** ✅ 2026-08-11 — `mainD`,
    commit `2e01d5dd`. `session_bus.py drain` now checks daemon liveness itself — dead pid, recycled
    pid, or wedged-and-not-ticking — and warns on stderr. **Every agent drains at every task
    boundary**, so the outage becomes visible within ONE boundary instead of ten days, with no cron,
    no host change and no new daemon to supervise. It fires on the EMPTY drain especially, because
    `(no new messages)` is exactly what a dead relay looks like from inside an agent: an all-clear
    that is really a silence. The check is duplicated rather than imported from the coordinator
    module on purpose — a check that imports the thing it is checking on fails exactly when it is
    needed. Silent when healthy. 5 tests.
  - [ ] **OPERATOR (still open, now a belt-and-braces item rather than the only line of defence) —
    nothing AUTOMATICALLY RESTARTS the daemon.**
    The report was correct-once-asked and pull-only, and **the supervisor was dead too**, so "the
    supervisor will catch it" is not an answer — nothing watched the watcher. `status` now takes
    `--exit-nonzero-if-unhealthy` (default exit stays 0, so no existing reader changes) precisely so
    a scheduler can act on it. **Recommendation:** the cron form already documented for the same
    problem one level up in
    [`handoff-index-and-backlog-graph.md`](handoff-index-and-backlog-graph.md) — `*/5 * * * *
    session_bus_coordinator.py status --exit-nonzero-if-unhealthy || bus_supervisor.sh once` —
    idempotent, self-exiting when a daemon is already running, no new daemon to supervise.
    Host-level change → operator's call. **Note this is the same unwatched-supervisor defect as the
    open `hub_supervisor.sh` item in that handoff; one decision should cover both.**
- [ ] **C38 (NEW) — `advisory.jsonl` is 1,028 MiB / 2,986,358 rows and the daemon re-parses it in
  full every tick.** Filed 2026-08-11 by `mainD`, half fixed. C34's dedupe stopped the *growth*
  (~20k rows/hour) but nothing addressed the ledger already on disk, and `already_flagged` in
  `relay_outbox_messages` reads it **entirely, every 45s, on the delivery hot path**. Measured:
  ~8.9s and ~6.6 GiB of transient dicts per tick, against a 45s tick — the live daemon sits at
  **29.5% of a core doing nothing else**. ✅ The `cmd_status` half is fixed: it called `_read_jsonl`
  on the whole file to print five lines and a count, and now does a bounded byte-count plus a
  backwards tail walk — identical output, **~9s → 0.4s**.
  - [x] **The tick-path read.** ✅ 2026-08-11 — `mainD`, commit `2e01d5dd`. Done together with
    **C28** exactly as this row predicted: they wanted the same ledger, so they got one.
    `already_flagged` now comes from `relay_state.json`. **Measured before: 3,001,866 rows parsed
    every 45s to rebuild a set of 637 pairs.** After: one 104 KiB read, 0 ms. The advisory is never
    fully read again except on a one-time bootstrap, and even that is streamed rather than parsed
    whole — at 1 GiB the parse-everything form is itself the defect. Nothing was trimmed: the
    ledger is still the record. **⚠ COMMITTED, NOT LIVE** — same restart dependency as C28 above;
    the ~29.5%-of-a-core cost is still being paid by `pid 496387` until it restarts.
  - [x] **Rotation.** ✅ 2026-08-11 — `mainD`, and **only possible because C28 landed first**, as
    this row required. Shards at 128 MiB to `advisory_<n>.jsonl`; rename, never truncate.
    **Re-measured after the restart: the daemon is at 1.3% CPU, down from 29.5%** — C38 already
    removed the hot-path cost, so rotation is the SIZE and the one remaining full read (the ledger
    bootstrap), not the performance defect it was twelve hours ago. Stated that way rather than
    claiming a win C38 had already banked.
    - [x] **`load_relay_state` now bootstraps across EVERY `advisory*.jsonl` shard.** ✅ The one way
      this change could do harm: a bootstrap reading only the live file would lose every flag raised
      before the last rotation and re-flag all of them, turning housekeeping into the C34 flood it
      was meant to prevent. Own test.

- [x] **C39 — the token relay is RECEIPT-BLIND: it presents gates the operator already
  signed.** ✅ 2026-08-11 — `mainD`. Filed by `auditor`, confirmed independently the same hour.
  `token-queue.md` currently presents **both** C27 gates as unchecked pending requests —
  `RATIFY-P-BENCH-4-FG4B-AFFINITY-20260729` (line 134) and
  `RATIFY-E8-FINAL-C1-RETRY-CAPACITYFIX-20260729` (line 144) — while **both carry ratified receipts
  on disk since 2026-07-29**: `artifacts/operator/ratify_pbench4_fg4b_affinity_witness_20260729T105911Z.json`
  and `artifacts/operator/ratify_e8_final_c1_retry_capacityfix_20260729.json`, each `status:
  ratified`. `relay_tokens` dedupes only on `gate in existing` — presence of the gate string in
  `token-queue.md` — and has no notion of a gate being SPENT, so deleting the stale rows will not
  stick: the next tick re-presents them. **This is not cosmetic. It asks a human to sign something
  they already signed**, and the E8 gate is the one whose ratified work then aborted, so a re-signature
  would look like authorisation for a cross-era re-run.
  Note this became reachable only *because* C27 works: the presentation path is live at
  `authority: manual` now, so a defect in what it presents is newly visible.
  **FIXED, and NOT YET LIVE — see the deploy box below.** Three parts:
  (i) `spent_receipt_for(gate_id)` — a SINGLE keyed read of
  `artifacts/operator/receipts/<GATE_ID>.json`, treating `ratified|spent|applied|attested|granted`
  as signed. (ii) A new gate carrying a receipt is still PRESENTED, with the receipt named beside
  it — annotate, never suppress. (iii) A gate presented BEFORE its receipt existed can never get
  that annotation, because the daemon does not edit `token-queue.md`; both live C27 gates are in
  exactly that state, so it says so on the bus instead, as a `token-gate-looks-spent` notice
  delivered to `coordinator-agent`'s INBOX — advisory-only would rebuild C33.
  **Verified read-only against the live bus: both gates flag, and 0 new blocks would be appended**
  (no duplication). 256 tests.
  - [x] **The 55 MB scan is a one-shot, never the tick path.** ✅ The legacy receipts carry the
    gate id at inconsistent keys, so finding them means reading `artifacts/operator/*.json` — 55
    files, 55.7 MB. Doing that every 45s would be a fresh instance of **C38**, the defect this same
    module already carries. So `session_bus_coordinator.py backfill-receipts [--dry-run]` pays it
    once (0.15s) and writes the keyed index; the daemon only ever stats one path. Run today: 2
    receipts indexed, 0 false positives across the 9 known gate_ids. The index is a **POINTER, not
    a copy** — duplicating an operator signature would give it a second source of truth.
  - [x] **The notice loop no longer mislabels.** ✅ It consumed EVERY advisory row carrying a
    `gate_id` and called it `token-request-not-presented` — true while `token-prevalidation` was the
    only such row. A "looks already signed" row rendered as "was never presented" would send the
    coordinator chasing a gate that is sitting in the queue. Selection and dedupe are both keyed on
    the check name now, so a third check cannot inherit the second one's wording. Pinned by a test.
  - [ ] **DEPLOY — the running daemon is executing the old code.** `pid 496387` started
    2026-08-11 08:48:00, before this landed, and Python loaded the module then. The fix is verified
    by direct invocation but **is not live until the daemon restarts**, which is the coordinator's
    call, not mine — process lifecycle is outside C-OWN's lane. Until then `token-queue.md` keeps
    presenting both gates with no notice. Flagged rather than assumed, because "committed but not
    live" is exactly what **C27** was.
  - [x] **The link exists but is not a contract.** Both receipts DO contain the literal gate id —
    but at different keys (`human_attestation` in one, elsewhere in the other), so today the only
    general way to find them is a content grep. `artifacts/operator/receipts/` **exists and is
    empty**: the keyed-receipt contract was intended and never wired. Fix direction: the `--attest`
    scripts write `artifacts/operator/receipts/<GATE_ID>.json`, and `relay_tokens` reads that.
    **Write side now exists, and is a CONVENTION — measured, not assumed.** `auditor` closed this
    for their two in-flight gates in `7c682621` (both ratifiers write `receipts/<GATE_ID>.json` at
    `--attest` and refuse if the index already exists). Verified, and verified further: **2 of 24
    `ratify_*.sh` scripts do this.** The other 22 are each one forgotten copy-paste away from
    re-creating C39 for their gate, and nothing would have said so — the relay would just present a
    signed gate as pending again. "Closed for two gates" is not closed for the class, which is the
    same shape as pinning an interpreter in C34.
    - [x] **So the gap is now DETECTABLE rather than remembered.** ✅ 2026-08-11 — `mainD`.
      `backfill-receipts --check` exits 1 when any SIGNED gate lacks a keyed receipt, whichever
      script signed it, and writes nothing while checking. Verified both directions on the live
      tree: clean → exit 0, one index removed → exit 1 naming the gate, index restored → exit 0.
    - [x] **Class closed by `auditor` in `ebce92a2`, and the class was WIDER than my count.**
      ✅ 2026-08-11. Verified: `scripts/operator/check_ratifier_receipt_contract.sh` exists, is
      static and read-only, and exits 1 on the one honest residual
      (`ratify_and_apply_e8_quality_baseline_v4_20260727.sh`, signable and receiptless, routed to
      `inference` as retire-or-repin). Three states, not two: **three gates were signed on disk and
      INVISIBLE to my `--check`** — `E8-FINAL-C1-RETRY-20260728`, `-SUPERSEDING-20260729`,
      `P-BENCH-4-FG4B-20260728` — now indexed as pointers with the gate id extracted from each
      receipt rather than hand-typed. The dry-run/apply vehicles take no token argv and never enter
      `token-queue.md`: out of scope by design, now documented instead of silently skipped.
      **My shared-snippet suggestion was WRONG and is withdrawn.** A signed artifact whose
      behaviour depends on an unpinned external file is no longer the thing the operator validated;
      self-containment is the trust property these scripts exist to provide. Documented authoring
      template (`artifacts/operator/receipts/README.md`) + two mechanical checks avoids the C34
      shape without weakening the signature. `auditor`'s call, and it is the better one.
    - [x] **My `--check` success line was an overclaim, and now states its scope.** ✅ 2026-08-11 —
      `mainD`. It derives its gate set from token-requests in the bus outboxes, so it can only speak
      about gates the BUS has seen — correct for C39, whose subject is what `relay_tokens` presents,
      and a fail-open if reported as an all-clear. It printed a clean verdict while those three
      gates sat unindexed. It now says what it did not check and names the check that covers the
      other half. The two compose; neither subsumes the other.
  - [x] **Fix by ANNOTATING, never by suppressing.** A relay that silently withholds a gate because
    a heuristic thinks it is spent is the C3/C6/C8 fail-open family aimed at the operator path —
    strictly worse than the defect. Present the block as now, and add a line naming the receipt, its
    path and its status, so the operator sees "this looks already signed" and decides. Suppression
    only becomes safe once the keyed-receipt contract above is real.
  - [ ] **Same shape, same fix:** the C33 pre-validation notice re-fires every tick against
    `mainA`'s 12-day-old `E5-THROTTLE-SCOPE-ERA-ROW-20260729`. Deduped per `gate_id` against durable
    evidence, but "the gate is stale/spent" is not among the states it can represent.
- [ ] **C40 (NEW) — a relayed backlog carries no age, so a fresh session cannot tell 12-day-old mail
  from this minute's.** Observed 2026-08-11 by `coordinator-agent`, filed by `mainD`. When the daemon
  came back after the 243h outage it relayed **703 messages** in one burst. `mainA` and `mainB`,
  spawned minutes earlier, drained that backlog and **both self-assigned `p2-5l-stack-numa-doc-debt`
  — work `auditor` had COMPLETED on 2026-07-29 as `ae40ee8b`.** They burned tokens on it until the
  coordinator could redirect them. Distinct from C28: nothing was re-delivered wrongly here, the
  delivery was CORRECT and the age was invisible. `drain` and `triage` print `ts` inside each JSON
  body and nowhere else, so "this is stale" is a judgement every reader must make per message, and a
  fresh session with no history makes it wrong. Fix direction: age is structural, like
  `needs_routing_to` — `drain`/`triage` annotate each item with its age and flag anything older than
  a threshold as historical. **FIXED**: `drain` prints a staleness banner naming every message older
  than `--stale-after-h` (default 24), worst first, with kind/sender/task/id; `triage` marks a stale
  item on its `via:` line. Reproduced today's incident on a fixture — the 12.1d `p2-5l` assignment
  is flagged, the fresh one is not. 5 tests, 412 green.
  - [x] **The signal goes to STDERR and to the `via:` line — never into the payload.** ✅ Two
    constraints decided this, and both are defects this handoff already carries. `drain`'s stdout is
    JSONL that consumers parse, and the msg schema sets `additionalProperties: false`, so decorating
    a drained row would make anything that re-validates it start failing — the C34 class. And
    `triage`'s fence carries a byte count and sha256 **over `body`** precisely so a downstream
    truncation is provable; putting the age inside would force the digest to cover text the sender
    never wrote. Tests assert the drained rows still pass `validate_row` untouched, and that the
    integrity-covered body is the sender's bytes.
  - [x] **An unreadable `ts` is neither fresh nor stale.** ✅ `message_age_h` returns None and the
    message is simply not listed — inventing an age would be a claim the record does not support.
  - [x] **Silent when everything is current.** ✅ A banner on every drain trains the reader to skip
    it, which is how the real one gets missed.
  - [ ] **Not done, and deliberately not guessed: the spawn mark.** The filing also proposed
    labelling mail that predates the current session, which is sharper than any age threshold — a
    2h-old assignment to a session spawned 10 minutes ago is also suspect. The spawn timestamp lives
    in `adapter-ledger.jsonl`, which `session_bus.py` does not read today; wiring it couples the two
    modules and wants its own think. The 24h threshold already covers the measured incident (12
    days), so this is a refinement, not a gap.

- [x] **C41 — `backlog_row_check.section_is_guarded` answers a SECTION question about a BOX,
  and is wrong in both directions.** ✅ 2026-08-11 — `mainD`. Filed by `auditor`, corroborated
  independently by `mainC`. The predicate takes the nearest preceding `#` heading and returns one blanket bool for
  everything under it, so a banner that guards *enumerated* boxes silently guards the whole section:
  - **False REFUSAL** — every row in such a section is reported undispatchable, withholding genuinely
    ready work. `mainC` measured this inflating corruption counts; 6 false positives adjudicated
    (`msg-20260811T092254Z-131-mainC`).
  - **False PERMIT, and it is the worse one** — a standing-constraint box NOT covered by the
    enumeration is treated as guarded, so every repair pass *skips* it. Live instance: the **seventh**
    box under `model-stack-single-source-update-pipeline.md:320`, whose banner reads *"THESE SIX
    BOXES ARE STANDING CONSTRAINTS"*. It survived two repair sweeps including `e43c8c27` for exactly
    this reason. **A guard that trusts an enumeration is passed by not being enumerated.**
  **FIXED**: `section_is_guarded` → `box_is_guarded(path, lineno)`. A guard now has a scope,
  resolved per box: **inline** (the phrase on the box's own line) covers that box only;
  **banner** (a blockquote — the corpus's only form that speaks for other boxes) covers the first
  N *open* boxes when it enumerates (`THESE SIX BOXES`, digits or words, count read across the whole
  wrapped blockquote) and otherwise the rest of the section, unchanged; **anything else is prose and
  guards nothing**. Counting OPEN boxes is deliberate — `classify` returns on `- [x]` before it ever
  asks, so closed boxes are not what a banner rations.
  **Measured over the live corpus, 1,277 open boxes: 43 guarded → 39, and every one of the 4
  changes is `GUARDED → free` on a genuine task.** No box became newly guarded, so the fix cannot
  have introduced a false permit. The 4: `standardized-stack-…:244` ("Finish W4 swap-CI", refused by
  the inline marker at `:232` bleeding forward), `stale-open-audit-…:269` ("read-certify the
  remaining ~918", refused by a table cell 140 lines up that merely NAMES the category), and this
  handoff's own two C41 sub-boxes, refused by C41's prose quoting the banner it describes.
  The remaining 39 break down exactly as intended: 2 inline markers + 37 under banners. 45 tests.
  - [x] **The `THESE SIX BOXES` banner turned out to be RIGHT.** ✅ Counted before trusting the
    filing: the section holds exactly **six open** boxes and three closed. The "un-enumerated
    seventh" is one of the CLOSED ones, so the scope bug is real but that particular box is a
    *checkbox-state* question for its owner, not a guard-scope one. Recorded because the predicted
    doc defect did not materialise and the prediction should not be left standing as if it had.
  - [x] **Scanning the box's continuation lines was tried and REVERTED.** ✅ It looks like
    robustness and re-imports the same prose-vs-guard confusion one level down: it newly guarded
    two real tasks whose *bodies* discuss standing constraints — C41's own filing and
    `stale-open-audit-…:110`. The inline check reads the box's own line only. Known limit, stated in
    the code rather than hidden: a row whose own first line contains the phrase still reads as
    guarded. Zero such rows exist today; the fix if one appears is to write the row's subject on its
    first line, not to loosen the predicate.
  - [x] **Compliant path tested.** ✅ The enumerated boxes stay guarded, the inline markers stay
    guarded, and unenumerated banners keep whole-section scope — otherwise "scope it to the
    enumeration" is satisfied by guarding nothing, which deletes the guard rather than scoping it.
  - [x] **The blind spot the fix could not reach, closed separately: `--audit-guards`.**
    ✅ 2026-08-11 — `mainD`. `box_is_guarded` can only ever speak about OPEN boxes, because
    `classify` returns on `- [x]` before it asks. Correct for a dispatch check, and it leaves a
    standing constraint that has ALREADY been flipped **invisible to every pass** — which is what
    `auditor` was actually pointing at with L339, once the banner-count half turned out to be
    sound. In a section whose banner forbids flipping, any `- [x]` is suspicious by construction,
    so the rule needs no cleverness. **Measured before writing it: 3 hits corpus-wide**, of which
    1 is the real defect and 2 are ordinary finished tasks in the same section — so it prints as a
    REVIEW PROMPT and says so, never a verdict. Three rows for a human to glance at is worth one
    invisible standing constraint; three hundred would not have been. Adjudicating the 3 is
    `mainC`'s, per the auditor's synthesis proposal — the detector is mine, the disposition is not.
    *Correction 2026-08-11 (`auditor`'s same-day audit): commit `a17ba974` says "54 tests". That
    was `test_backlog_row_check.py` and `test_backlog_queue_gen.py` SUMMED and presented as one
    file's count; the file alone was 47 at that commit (50 now, 14 in the companion). My other five
    test counts today reconciled exactly. Stated here rather than quietly amended.*

- [x] **R1 (NEW, P0) — the nudge guard HARDENED as the condition worsened, and the whole fleet
  became unreachable.** ✅ 2026-08-11 — `mainD`, commit `b41af9d7` *(this handoff and the progress log first cited `b41af9d7`, which is DANGLING — reflog-only and unreachable from any clone, so it dies at gc. The R1 code landed inside `b41af9d7`, whose message is a verbatim copy of an unrelated A16+A18 commit: an `--amend` artifact in the shared index, the third sweep-class incident today. Corrected here rather than rewritten — history is pushed. Found by `auditor`.)*. Raised by `coordinator-agent`
  from the cold-start config-repair report; **this, not a missing coordinator tick, is the cause of
  today's 10-hour stall.**
  **The deadlock:** the daemon calls a heartbeat older than **3600s** STUCK and tries to nudge;
  `tmux_adapter` refused every nudge past **900s**. Between the two nobody has decided you are
  stuck; past 3600s somebody has and can no longer reach you. Measured: every main crossed 900s at
  ~10:14-10:22Z and the entire fleet — **the coordinator included** — went permanently unreachable,
  **1,903 `stuck-nudge-refused` rows**, recovered only by a human passing `--heartbeat-max-age
  86400` by hand. Neither escape hatch reaches it: **C35 lifts only the `working` blocker, never
  staleness**, and **C36 is codex-rollout-only — 0% availability on an all-Claude fleet.**
  **Fixed with evidence, not a bigger timer.** Raising the default would trade a deadlock for
  typing into a mid-generation pane. Staleness is a timer and a timer cannot tell *wedged* from
  *quietly waiting*; the pane can. `hb_stale_override_ok` reuses exactly the evidence C35 already
  trusts — `pane_dead` false plus quiescence past the spinner interval — and **fails closed on every
  unknown** (override disabled, pane dead/unreadable, activity unreadable). 7-case parametrised
  test.
  - [x] **Compliant path pinned, and it is the one that matters.** ✅ A stale heartbeat on a pane
    that looks mid-generation STILL refuses. A fix that made everything nudgeable would be worse
    than the bug.
  - [x] **The fail-open that hid it.** ✅ `last_nudge_ts`/`last_nudge_sig` were written ONLY on
    `rc == 0`, and the `stuck-refusing-drain` escalation is gated on `last_nudge_sig` — so **a nudge
    that is always refused could never escalate**, and the only path that reported it was an
    advisory row in a file with no reader. Refusal now carries its own clock and emits
    `stuck-unreachable` **into `coordinator-agent`'s inbox** (C33: an escalation delivered only to
    `advisory.jsonl` is a second unread sink one level up).
  - [x] **A test asserted the deadlock as correct.** ✅ `test_c35_the_override_touches_only_the
    _working_blocker` justified never overriding staleness because it "is already tunable with
    `--heartbeat-max-age`" — the very tunable a human had to set to 86400 to rescue the fleet.
    Rewritten to the corrected contract; its real intent (every other guard survives independently)
    kept, authorisation half untouched.
  - [x] **R2 — daemon-side progress-log currency check.** ✅ 2026-08-11 — `mainD`. Built
    fail-closed as the report demanded, because it named this the proposal most at risk of
    fail-open. All three silent-pass paths emit a `defect` instead of returning clean: unreadable
    git (which is NOT "no commits"), a missing `progress/` directory (a louder defect than a stale
    file, not a quieter one), and a missing file for today when commits exist (the absent file IS
    the defect). **Exactly ONE clean exit** — no commits landed today — and it is keyed on positive
    evidence, a commit timestamp older than today, never on something being unreadable; a test pins
    that distinction because it is the difference between "nothing was owed" and "I could not tell".
    Kind is `defect` deliberately: it is already in `_OPERATOR_ITEM_KINDS`, so an unpresented one
    reaches `token-queue.md` on the C20 timer with **no new escalation code**. It never writes the
    log it checks — a checker that repairs what it checks for cannot be trusted to report. 8 tests;
    450 green. Verified against the live repo: clean, because the log is current.
    - [x] **CORRECTION, same day, caught by the operator: it escalated into `advisory.jsonl`, not
      an inbox.** ✅ 2026-08-11. I shipped it emitting the advisory row only, reasoning that
      `defect` is in `_OPERATOR_ITEM_KINDS` and would reach `token-queue.md` on the C20 timer for
      free. **Wrong**: `_is_operator_item` is applied to OUTBOX and INBOX rows, never advisory rows,
      so the notice stopped in a file nobody drains — the C33 shape, and a sentence I had quoted
      twice the same day while building this. Now delivered into `coordinator-agent`'s inbox,
      deduped once per day against that inbox's own contents; delivery failure is swallowed because
      a reporting path must not be able to take the tick down. 3 tests.
    *(Original filing below, kept for the record.)*
  - [x] **R2, filed:** a daemon-side progress-log-stale defect routed to the
    operator through the existing C20 bypass. The report flags it as the proposal MOST at risk of
    fail-open (three silent-pass paths) and names the in-repo fail-closed pattern to copy. **Build
    it fail-closed or not at all.** Source: `/workspace/tmp/coord-coldstart/coordinator-config-repair.md`.

- [x] **C42 (NEW) — the supervisor could not tell a daemon running OLD CODE from a healthy one, and
  that is the pattern behind five committed-not-live gaps in one evening.** ✅ 2026-08-11 —
  `mainD`. Raised by the operator from the recurrence itself: a restart at 22:18:12Z was followed by
  an R2 commit at 22:21:25Z, so that fix needed a **second** human-initiated restart. `health_ok`
  asks *is a process there* and *is its heartbeat fresh*; a daemon running twelve-hour-old code
  answers yes to both, so C39, C28, C38's tick path, R1 and R2 all sat inert until a human noticed.
  **A delivery gap in the same family as R1** — the mechanism worked and nothing carried its result
  to where it takes effect.
  *(Numbered C42, not R7. It was first filed as R7 by analogy with the coordinator's config-repair
  report, but R1-R6 are that report's items; this one was found from the recurrence itself and is a
  C-OWN delivery-plane defect, so it belongs in the series that owns the plane. Renumbered
  2026-08-11 on the operator's point that a proposal on the bus with no C-number is not filed.)*
  `check_stale_source` compares the newest source mtime against the running process's start time and
  restarts **once per source version**; identity comes from the heartbeat's own pid, never a name
  pattern (INC-20260731). Fail-closed on every unknown per the R2 discipline: no heartbeat, no pid,
  a dead pid, or unreadable sources are all *reported*, never passed as clean.
  - [x] **Three bugs found building it, two by the EXISTING suite going 5/5 → 4/5.** ✅
    `ps -o etimes` truncates to whole seconds, so a source written in the same second as a
    legitimate restart read as newer — a false positive that recurs every cycle, i.e. a restart
    loop. And **twice** `set -euo pipefail` bit: a failing command substitution aborts the script
    (dead pid, empty source dir), and a *function* returning non-zero as a simple command aborts it
    too — so `f; rc=$?` killed the supervisor on the NORMAL path. A watchdog that silently stops
    watching.
  - [x] **My own test had missed both `set -e` bugs because it ran without `set -e`.** ✅ The test
    method differed from production; matching it is what turned an empty output into a real signal.
    Recorded because "rule out the test method first" is a rule I have quoted and still had to
    relearn here.
  - [x] **Predicate-only scope, deliberately.** ✅ The test never sources the supervisor and never
    reaches `stop_wedged`/`start_daemon`: a stub named `session_bus_coordinator.py` matches the
    production `pgrep` pattern and killed the live daemon that way on 2026-07-27.
  - [x] **C42 BUGFIX — the loop's healthy path never reached the check.** ✅ 2026-08-12 — `mainD`.
    The supervisor restart at 00:26:25Z made it source-current, and the check **still did not
    fire**: zero detections logged while the daemon was demonstrably stale and the predicate
    returned STALE when run by hand. Cause: `check_stale_source` was hooked into `check_once`, but
    the loop's healthy branch does `sleep; continue` and **never calls `check_once`** — so the check
    only ever ran on the UNHEALTHY path, where the daemon is about to be restarted anyway and the
    question is moot. The whole point is a daemon that is UP and answering on old code. Now called
    on the healthy branch, and still from `check_once` for the cron `once` path.
    **My tests could not have caught it and that is the lesson:** they exercised the predicate and
    `check_once` directly — *A* consumer, not *THE* consumer. Added a static wiring assertion that
    the loop's healthy branch reaches the check, **mutation-verified**: removing the call takes the
    suite 8/8 → 7/8 with the failure naming the defect.
  - [x] **C43 SECOND HALF — the relaunch RACES the dying supervisor's lock release.** ✅ 2026-08-12
    — `mainD`. `coordinator-agent` measured it while doing the C42 bootstrap restart I asked for:
    killed 489217, verified dead with `ps`, relaunched immediately, and the new process (1316099)
    **lost the race against the dying holder's flock release** — logged the contention, exited 0,
    and died. **For ~90 seconds nothing would have relaunched the daemon if it had died** — the
    exact condition that went unnoticed for ten days from 2026-07-29.
    **My first C43 fix would not have helped, and saying so matters:** the holder was still alive
    while releasing, so it would have printed `(ALIVE)` and exited 0 — accurate, unhelpful, gap
    still open. **Evidence about a race is not a fix for the race.**
    Fixed with a bounded `flock -w` (15s, `LOCK_WAIT_S`): a dying holder releases in milliseconds so
    the relaunch wins; a genuinely running one holds for its life so we still report and exit 0,
    which keeps the cron idiom intact. Chose the retry over exit-non-zero because a skip is the
    NORMAL case for `once` and paging every tick is how a real alarm gets ignored.
    5 tests including the **contrast** — the old `flock -n` form is asserted to LOSE the same race,
    so the test is measuring the fix rather than the environment — plus wiring assertions that
    neither entrypoint can regress to the non-blocking form.
  - [x] **C43 FIRST HALF — lock contention exits 0 with no evidence.**
    ✅ 2026-08-12 — `mainD`. A relaunch at 00:25:09Z logged *"another supervisor holds the lock;
    exiting"* and exited **0**. True at the time, but the exit code says SUCCESS, so nothing
    downstream can tell *"correctly skipped, one is already running"* from *"failed to start,
    nothing is supervising"*. **The exit code is deliberately unchanged** — for the documented cron
    idiom a skip is the normal case, and non-zero there would page on every ordinary tick. The fix
    is the EVIDENCE: it now names the holder pid and whether it is ALIVE or DEAD, and reports a dead
    or unreadable holder loudly, because that is the shape where nothing is supervising and
    everything still looks fine. Verified live: `once` against the running supervisor prints
    `lock holder: pid 1336629 (ALIVE)`.
  - [x] **THE BOOTSTRAP CHAIN CLOSED, AND C42 FIRED FOR THE FIRST TIME IN PRODUCTION.**
    ✅ 2026-08-12 00:45Z, verified from the supervisor's own log and the filesystem, not claimed:
    1. Supervisor restarted **00:45:19Z** → source-current, and the loop's healthy branch reached
       the check (the 48648df2 bugfix).
    2. **It DETECTED the stale daemon** — `daemon is running code OLDER than its source (source
       00:03:07Z is newer than the running process) — restarting so committed fixes take effect`.
       First live detection this mechanism has ever made.
    3. Restarted it: `stopping wedged daemon pid(s): 942753` → new daemon **1510614 at 00:45:20Z**,
       one second later, source-current.
    4. That daemon ran the rotation it had been unable to run: **`advisory.jsonl` 1,044 MiB → 0 MiB,
       `advisory_1.jsonl` 1,045 MiB.**
    5. **The hazard did not fire:** flags survived the shard — 660 pairs in `relay_state.json`, and
       a fresh bootstrap across `advisory*.jsonl` finds all 660. The all-shard read is what stopped
       rotation turning into the C34 flood.
    Daemon now at **1.8% CPU** (29.5% pre-C38, 1.3% post-C38-live). Five defects — C28, C38, C39,
    R1, R2 — went from committed to live on one restart, and **C42 now keeps the chain closed
    without one**: the next fix to land is picked up by the supervisor within a poll.
    *The mechanism finally outlived the need for the restarts it was built to remove.* Measured 2026-08-12: the
    supervisor is source-current, but the daemon (pid 942753, started 22:25:55Z) still runs
    pre-rotation code and `advisory.jsonl` is still **1,044 MiB with no shards**. With the loop
    bugfix above the supervisor should now detect and restart it on its own within a poll — but the
    supervisor must first be restarted ONCE MORE to pick up this fix, which is the same bootstrap
    step, one level down. **OP-9 again, and not mine: restarting is process lifecycle.**
    The watchdog that detects staleness must ITSELF be restarted to gain the ability to detect it.
    Verified, not theorised: `bus_supervisor` pid 489217 started **08:48:01Z**; C42 landed in
    `bus_supervisor.sh` at **22:40:02Z**. So the running supervisor predates its own check, has
    logged **zero** stale-source detections, and therefore never noticed that the coordinator-daemon
    (pid 942753, started 22:25:55Z) is itself running pre-rotation code — which is why
    `advisory.jsonl` is **still 1,044 MiB with no shards** and rotation has never fired.
    **The chain is: stale supervisor → undetected stale daemon → un-run rotation.** One supervisor
    restart collapses all three, and after it C42 keeps the chain closed on its own. This is
    **OP-9** in concrete form — *nothing restarts the supervisor itself* — and the strongest
    argument yet for that cron decision, because C42 cannot bootstrap itself past a supervisor that
    predates it. **Not mine to do: restarting is process lifecycle, outside C-OWN's lane.**

- [x] **C34 residual disposition — CLOSED as a decision, routed as work.** ✅ 2026-08-11.
  `coordinator-agent` approved **per-owner triage-by-value** (not repair-all, not quarantine) and
  approved **all 17 kind mappings as proposed**. Final numbers: **151 of 1283 outbox rows (12%)**,
  down from the 368/32% quoted pre-fix; **gate-new-writes-only was already done** — the authoring
  gate closed 09:15Z and the newest invalid row on the bus is 08:59Z, so nothing new joins the set.
  - [x] **`mainD`'s 49 triaged.** ✅ First answer — "none is still live" — **was wrong**, and the
    second look is what caught it: 11 of 40 task_ids are still referenced in `handoffs/active`, but
    judging by CONTENT exactly **one** row is genuinely live. The HG-3 finding (`action_required`,
    never delivered) is re-authored as `msg-20260811T225126Z-202-mainD` citing the original; the
    other 48 close as historical. That row had died TWO ways — a top-level `body` key the schema
    forbids *and* `to: "coordinator"`, which is not a roster id, so the relay had no target even had
    it validated.
  - [x] **Each other owner routed their own list.** ✅ `mainB` 81 (78 additionalProperties, 7
    out-of-enum, dominant shape: 51 rows with top-level evidence/next/status/summary), `mainA` 1
    (a **token-request** — the C27 class, a signature request that vanished), `mainC` 1
    (`risk_escalation`), `coordinator-agent` 19 (13 `task-assign` missing lane/lease/epoch). Routed
    with the approved mapping and the worked example, **not touched** — single-writer, and the
    liveness judgement is the owner's.
  - [x] **The RECEIPT PRESENT marker — BUILT 2026-08-12, and deliberately narrower than proposed.**
    ✅ `mainD`. The C39 notice reached `coordinator-agent`'s inbox, which is right, but left the
    operator-facing file misleading on its own terms: **six of seven unchecked gates in
    `token-queue.md` carry `status: ratified` receipts** and nothing in the file said so. A reader
    of that file alone sees six pending signature requests that are not pending.
    **APPEND-ONLY, not in-place.** The proposal was to annotate each block where it sits; that means
    the daemon editing operator-facing content it wrote earlier, immediately beside checkboxes only
    the operator may touch — a small blast radius right up until the day an edit lands wrong.
    Appending a clearly-marked block gives a reader the same thing and cannot corrupt an existing
    one, and appending is already what this daemon does here (`relay_tokens`, C20's escalation).
    It never writes or alters a checkbox, and it never says a gate is closed — only that a receipt
    exists and where. **Stating the evidence is transport; deciding is not.**
    Deduped on the gate SET rather than on "a notice exists", so a steady state appends once and a
    later-signed gate gets a fresh corrected note instead of silently going unmentioned — quiet is
    not the same as correct. Dry-run against a COPY of the live queue: names the 6, existing content
    byte-identical, zero ticked boxes written. 4 tests.
  - [x] **The earlier deferral was the right call at the time.** ✅ Accepted by the
    operator as a considered non-choice. It means the daemon editing an operator-facing file it has
    already written, which wants more care than a late-night text fix, and the six live instances
    are already surfaced by the C39 notice.

### C44–C50 + the 2026-08-12 delivery-plane landings (filed at wrap-up by `coordinator-agent`)

Filed because most of these emerged mid-flight and had no task line: work that landed with a commit
gets a closed box carrying its hash, work this session only *recommended* gets an open one. Nothing
here is back-dated — `✅ 2026-08-12` is the day it landed and the day it was filed.

Two of these (`guard-universe-and-worktree-isolation` items 1–5, and the pattern-kill hooks) belong
to a task with **no handoff of its own**. They are filed here rather than left as prose in a bus
message, because item 1 is a bus-root fix and the whole task's premise is this plane's
one-live-instance assumption. If that task gets its own handoff, move these five rows wholesale.

> **⚠ C-NUMBER COLLISION — for the C-series owner (`mainD`), NOT renumbered here.** `C45` is anchored
> twice on 2026-08-12 and neither anchor can be dropped silently: the **doorbell** owns it in the code
> (a `C45` comment block in `scripts/coordination/tmux_adapter.py`, plus `DOORBELL_MIGRATION.md` and
> two test files), and the **`agent_audit.log` untrack** owns it in `a70dbe1a`'s `.gitignore`
> rationale (*"C45 precedent — the same untrack-and-gitignore ruling already applied to
> logs/agent_audit.log"*). Renumbering inside another agent's namespace is that agent's call. Until
> it is made, the audit-log item is referred to by description and hash, never by a number.

- [x] **C44 — the token relay is WITHDRAWAL-BLIND: a gate whose own requester has moved on is still
  presented as a live ask.** ✅ 2026-08-12 — `mainD`, commit `bd2e830d`. C39 taught the relay to
  notice a *signed* gate; it could not notice a *withdrawn* one. Verified closed end-to-end rather
  than re-done: `tokens/token-queue.md:365` carries the `REQUESTER-MOVED-ON` marker, so the operator
  no longer reads that gate as pending.
- [x] **C45 — every nudge guard exists because nudges carry PAYLOAD, and the payload never needed the
  pane.** ✅ 2026-08-12 — commit `777f826e`. The bus is already durable, schema-validated and
  cursor-tracked; the pane only ever needed a **doorbell** — a fixed, content-free, idempotent "go
  check the bus" string with no `--message`, since a caller-controlled string is a payload nudge by
  another name. Quiet-for, the rate limit, the heartbeat-state refusal and C35's override machinery
  are all **not** applied to it, each removal reasoned through in the code. Two guards stay,
  fail-closed, against the one hazard content-free does not remove: an Enter landing where it
  corrupts. Cost of the old shape, measured: an idle-but-`working`-labelled agent was unreachable for
  **33 minutes** on 2026-08-12 — the heartbeat-state blocker refused every nudge, and clearing the
  flag is exactly what the refused nudge would have done. 28 new tests; all 124 pre-existing
  `tmux_adapter` tests still pass unchanged. `DOORBELL_MIGRATION.md` names the daemon call sites for
  the daemon's owner and is deliberately not applied here.
- [x] **`logs/agent_audit.log` untracked — a concurrently-appended tracked file is permanent merge
  tax.** ✅ 2026-08-12 — commit `73998d70` (labelled C45 in its subject; see the collision note).
  Every writer touches the same last line, so a textual merge cannot interleave two sets of appends;
  it conflicted on this merge and would conflict on every future one. The trail lives on disk and is
  read via `agent_log_analyze.sh` — nothing reads it out of git history. Option 1 of three, per the
  A19 precedent. **Option 3 (a `merge=union` driver) was rejected on its own merits**: it makes the
  conflict disappear while silently reordering chronology, passing every check and producing a log
  nobody can trust to be ordered.
- [x] **C46 — the pattern-kill hook forbade an idiom a project skill instructs.** ✅ 2026-08-12 —
  commit `e08fe836`, operator decision, `mainD` CC'd (they own the hook and had argued the opposite).
  The guard was scoped to `pkill` **and** `pgrep`; `pgrep` selects but does not kill, and blocking it
  collided with legitimate read-only sensing, forcing a skill rewrite around an unapproved scope. The
  scanner still classifies grep-patterns; the hook now allows them. The narrowing is pinned by its own
  test so it cannot be silently re-widened. 9/9 green. *A guard must be tested against the compliant
  path, not only the hazardous one.*
- [x] **C47 — the hook blocked the message REPORTING the incident it guards.** ✅ 2026-08-12 —
  commit `ee628304` (guard itself `68979233`). Scoped to invocations, not text.
- [x] **C48 — supervisor liveness was derived from a pid file, not from the lock.** ✅ 2026-08-12 —
  commit `a96191af`. Measured incident: `status` reported *"supervisor: not running"* and health
  UNHEALTHY while pid 1510370 was alive, holding the lock, and had been supervising for 7h40m,
  because `$SUP_PIDFILE` had vanished. The coordinator read UNHEALTHY, concluded the bus was
  unwatched, and launched a second supervisor; C43's bounded flock correctly refused it, but the
  refusal **could not name the holder**, because naming also read the missing pid file. *The
  diagnostic and the thing it diagnoses shared a single point of failure.* Liveness now comes from
  the flock; the pid file is demoted to a hint.
- [x] **The destructive-revert guard (hook 2) reverted.** ✅ 2026-08-12 — commit `3d8800e6`, reverting
  `03e17111`, by operator decision. Recorded as landed work rather than dropped: a shipped-then-pulled
  guard is a decision, and `54889ea3` separately pinned the shell-framing gap found in it so the
  finding outlives the revert.
- [x] **`start_orchestrator_test` name-pattern kills removed — twice, at two levels.** ✅ 2026-08-12
  — commits `81412a6e` (the kills the script *executes*, lines 76–77) and `c46caf24` (the one it
  *recommends*, line 232, printed as the operator's stop procedure). Landed on coordinator
  instruction at severity CRITICAL; **authorship is not the committer's** — the fix was written by an
  unidentified agent, had been destroyed twice, and survived only in fragile copies. The second
  commit is the same bug one level over: the first fix's universe was *"commands this script runs"*,
  the hazard's universe is *"name-pattern kills this script causes"*, and the missing line is
  arguably worse because it launders the wildcard through the operator.
- [x] **Bus-root resolution canonicalised — one strategy.** ✅ 2026-08-12 — commit `8b308468`
  (`guard-universe-and-worktree-isolation` P1/1). `session_bus.py` resolved `DEFAULT_BUS_ROOT` via
  `Path(__file__).resolve().parents[2]` while `merge_gate.py` hardcoded the literal `/workspace` —
  two strategies for one fact. Under worktree-per-main the first derives **five independently
  mutating bus directories** instead of the single shared runtime plane the protocol assumes (one
  queue, one cursor set, one single-writer rule per file). New `--print-root` flag makes the
  resolution assertable from inside a worktree.
- [x] **Worktree machinery + migration doc.** ✅ 2026-08-12 — commit `724b5f85` (P1/4).
  `scripts/coordination/setup_main_worktrees.sh`: idempotent per-agent
  `git worktree add /mnt/raid0/llm/worktrees/mains/<agent> -b lane/<agent>`, syncs `repos/*` via the
  **worktree's own** `clone-repos.sh`, then verifies inside the worktree that the shared pre-commit
  hooks actually fire (stages a secret-shaped blob, confirms the block; stages a clean file, confirms
  the commit) and that `session_bus.py --print-root` resolves to the ONE canonical bus root.
  Throwaway worktree cleaned up completely after each verification pass, confirmed absent from
  `git worktree list`, `git branch -a` and the filesystem.
- [x] **Test coverage for the three worktree items.** ✅ 2026-08-12 — commit `fbff4c22` (P1/5). Four
  pytest-collectible files, 57 collected / 50 passed / 7 honest skips, each carrying a
  **both-directions** pair: the new behaviour fires, and the adjacent behaviour it must not disturb
  stays intact. The core pin relocates a *copy* of `session_bus.py` to an arbitrary path — which is
  exactly what a worktree checkout is — and asserts the root does not follow it.
- [x] **`worktrees/` gitignored — and the premise it was routed on corrected in the same commit.**
  ✅ 2026-08-12 — commit `5df3c9eb`. Routed as a one-line live-hazard fix; **both halves of the
  premise were wrong**, and measurement rather than assumption is what caught them. `git clean -ndx`
  prints `Would skip repository` for all **29** (not 20) — git skips nested repositories, so `-fdx`
  removes none of them. Only `-ffdx` removes them, as a single `Would remove worktrees/`. The commit
  states plainly that ignoring does **not** close the hazard. *Falsified within the hour: the wipe
  below is that second `f` being typed.*
- [x] **Hardware-idle backfill runner + queue-empty detector.** ✅ 2026-08-12 — commit `5af987ef`.
  Against a measured gap: 19 READY compute-gated tasks existed, nothing translated them into queued
  jobs, hardware sat idle **3h47m**, and the daemon wrote 590 consecutive all-idle advisory records
  nothing reads. Region-lock-wrapped, timeout-bounded, concurrency-capped, crash-safe re-queue of
  orphaned in-flight entries; the detector watches the QUEUE, not the hardware, and emits at most one
  bus finding per unbroken idle stretch.
- [x] **The daemon's own pick now reaches a reader.** ✅ 2026-08-12 — commit `e9a11f08`.
  *(Labelled "M1" in the falsifiability investigation's numbering — **not** this handoff's M1
  milestone, which is the 2026-07-27 skeleton. Recorded without a number to stop the collision
  spreading.)* `compute_advice()` has always computed a concrete pick per agent per tick, into
  `advisory.jsonl` — a file whose own producer says in-source that it has no reader.
  `deliver_scheduling_recommendation()` routes a *stable* pick-set into `coordinator-agent`'s inbox,
  reusing R1's `_append_inbox` shape and R2's dedupe verbatim. **There is deliberately no authority
  branch in the code**: under `assign` the row leaves READY, the pick stops being emitted, and the
  arming counter resets, so the mechanism silences itself *structurally*. A mechanism that behaves
  differently when a config flag is raised has smuggled the flag's decision into itself.
- [x] **Residency is not work — the idle model that locked the queue.** ✅ 2026-08-12 — commit
  `e9a11f08`. *(Labelled "M4" in the same ad-hoc numbering; not this handoff's M4 milestone.)*
  `mi210_state()` OR-ed `util_pct` with `vram_used_mb` into one `occupied` boolean, so a
  loaded-but-idle model read BUSY and `_eligible` rejected every queued lane row behind it — **572
  `lane cpu busy` rejections**. The sensor now publishes `busy | resident | free | unknown`;
  `occupied` is retained unchanged for pre-split callers. **RESIDENT ADMITS, WITH A WARNING**, stated
  rather than buried: admission is not acquisition — `_eligible` only makes a row pickable, and
  `device_claim.py` / `cpu_region_lock` remain the only things that grant a device, untouched.
  `test_busy_mi210_vram` was **deleted, not adjusted**: it pinned the defect. Six mutations verified
  against a sandbox copy, never the shared tree.
- [x] **The device-claim expiry check was disarmed for exactly the claim that monopolised the
  MI210.** ✅ 2026-08-12 — `epyc-inference-research` commit `4755e727`. The device claim was acquired
  with no `max_hold_s` while the CPU claim three lines above passed one, so `expires_at` was never
  written and `check_claim_expiry()` returned `COULD_NOT_CHECK` forever instead of `FAIL`. Fixed by
  quoting `spec.max_hold_s` rather than a fresh constant — both claims are taken in one transaction
  for one campaign and released together, so two declared deadlines would be a defect by construction.
- [x] **Three operator decisions applied to `config.yaml`.** ✅ 2026-08-12 — commit `6d8b5999`.
  `authority: manual` → `assign`; cpu lanes for `mainC` and `mainD` (only `mainA` had it, so CPU work
  queued behind one agent and `lane cpu not in <agent> roster lanes` was the dominant rejection); and
  a `hardware-backfill` roster row, without which `_require_roster_id` refuses the new runner's
  findings and they cannot reach the bus at all. Verified before editing that `config.yaml` is not in
  `human_only_paths.yaml` and that `authority.lease_grant` includes `coordinator-agent`, so no
  signature was required. **Effect, measured within a tick:** `ready_depth: 19` with nothing moving
  → queue fold `ASSIGNED 6 / CLAIMED 1 / READY 12`, with seven `assigned` and one
  `scheduling-recommendation-delivered` advisory record.
- [x] **The coordinator's status-from-memory replaced by an artifact-per-row ledger.** ✅ 2026-08-12
  — commit `1764471d` (`artifacts/operator/RESOLUTION-LEDGER-20260812.md`), with the morning package
  `9cbcca0c` (`artifacts/operator/MORNING-PACKAGE-20260812.md`) as its decisions-first companion.
  Every row carries a commit, a receipt path, a `file:line`, or the literal token `NO ARTIFACT`, and
  the **unowned section is first and is not empty** (ten items). Both documents exist to correct the
  coordinator's own reported figures, and they did: duty cycle ~20% → **~8–9%**; checkbox counts
  re-derived with an anchored pattern (1273→1242 open, 2306→2368 done); the **5,292** lane-rejection
  figure withdrawn as **not reproducible**; and one coordinator self-criticism withdrawn because it
  could not be verified at all. *A metric can flag candidates; only the artifact settles them.*

- [x] **C49 — the operator escalation misclassifies `action_required`, and reported 11 items when
  there were zero.** FILED 2026-08-12 by `coordinator-agent`, **unfixed**. The daemon escalated 11
  operator items; a full parse of the same 17-item standing queue found **zero** needing the human.
  The 11 is reproducible exactly as *every item with `action_required: true` (12) minus `kind: status`
  (1)*. That formula reads `action_required` as "the operator must act", when on this bus it means
  "some named agent must act next" — every one of the 11 is addressed to `auditor`, a main, or the
  coordinator in its own text, and only one carries `kind: decision-request`, which its author
  disclaims. Measured across the live inboxes: **111 rows carry `action_required`, 8 satisfy
  `_is_operator_item` (`session_bus_coordinator.py:2643`, keyed on `kind ∈ {token-request, defect}`
  or `severity == CRITICAL`), 7 overlap** — the two predicates are nearly disjoint. An escalation
  that fires on a well-run night trains everyone to ignore it, which is the same failure as not
  checking, one level up.
    ✅ 2026-08-12 — `mainD`. **An operator item is now DECLARED, not inferred.**
    `payload.operator_signature_needed: true`, plus `kind == "token-request"`, which stays because a
    token IS the operator's signature — dropping it would fix the false positives by making the
    channel silent, the failure that matters most. Dropped: `kind: defect` and
    `severity/priority == CRITICAL`, both of which inferred operator-ness from fields meaning
    something adjacent. Measured before and after on the live bus: 267 rows, 116 `action_required`,
    **8 → 0** classified as operator items, and every one of those 8 was `kind: defect` — *not one
    was a `token-request`*. An agent can no longer escalate to the operator by owing itself a next step.
    **MIGRATION COST, stated because it is the risk you named:** nothing written before today carries
    the marker, so a genuine non-token operator need will now go unescalated until its author declares
    it. In this corpus that is exactly one row; `token-request` still qualifies structurally, which is
    why the compliant path is unaffected.
    **What the consumer check caught that the unit tests did not:** narrowing the predicate broke
    `test_c20_bypass…`, whose fixture relied on `kind: defect` qualifying. Fixed at the FIXTURE (it
    now declares) rather than by widening the predicate back. My first attempt defaulted the
    declaration inside the shared `_op_msg` helper and broke `test_c27c_…_stay_quiet` — a fixture
    change that deleted the distinction another test existed to check. Declaration is now per-caller.
    Mutation-verified both directions: restore the old inference → 2 fail; silence `token-request` →
    the compliant-path test fails. 315 pass.
  - [ ] **The fix is a POSITIVE marker, not a tightened negative.** Neither predicate can be repaired
    by exclusion: `action_required` over-fires and the kind-set under-fires, so a sender who needs the
    operator has no way to say so. Add an explicit sender-set field (the `needs_routing_to` /
    structural-intent idiom already in use), make the escalation key on **that alone**, and make an
    item claiming operator attention without it a schema warning — so the marker's absence is
    detectable rather than silent.
- [ ] **C50 — the picker serves a STALE READY set, and this is DISTINCT from the authority gag.**
  FILED 2026-08-12 by `coordinator-agent` from `mainB`'s screening, **unfixed**. Six dispatched picks
  screened with `backlog_row_check.py --ref`: **1 of 6 dispatchable**; four (`:463`, `:511`, `:513`,
  `:628`) had been `- [x]` since **2026-07-29**, closed fourteen days before the daemon named them,
  and one (`:626`) was anchor rot — the file untouched in between, so the picker never re-read what
  closed them. It re-selected them on 20 consecutive ticks. In the surviving advisory shard: **811
  `would-assign` records, 100% carrying a `task_id`, resolving to 15 distinct `(agent, task, lane)`
  picks over NINE distinct task rows, all nine from one file**
  (`handoffs/active/opendataloader-pipeline-integration.md`), the top six repeating 104–105 times
  each. **Fixing delivery does not fix selection** — a working courier now delivers wrong rows faster.
  - [x] **Establish whether the READY set is cached or re-derived per tick** ✅ 2026-08-12 — `mainD`.
    **CACHED, and nothing ever re-derived it.** Root cause is one line:
    `session_bus_coordinator.py:1633` writes `"status": "READY"` as a literal in `intake_proposals`
    and copies `spec_ref` beside it; `_eligible` then checked status, deps, gates, lane and load —
    **all from the queue row** — and never opened `spec_ref`. The reference was carried into messages
    at three call sites and dereferenced at none, so rot was *undetectable by construction*. Fixed at
    `1fae78dc`: a positively CLOSED box refuses; rot and unreadable refs stay dispatchable and are
    reported, because refusing real work on a bad pointer is the costlier error.
    **The PROBE is the deliverable, and it caught a defect in its own fix.** Two consumer-level tests
    assert the *dispatch decision* (`_eligible`), not the lookup helper — the first C50 tests
    exercised `spec_ref_state` in isolation, which proves the helper and not the thing that decides
    dispatch. The probe immediately dispatched a stale row while every helper test stayed green:
    `spec_ref_state(..., repo_root=REPO_ROOT)` bound the root **at import**, so the consumer always
    resolved against the real repo and the fix was inert anywhere else. Now late-bound.
    Mutation-verified both ways — remove the dereference: 2 failed; revert the late binding: 2
    failed; restored byte-identical. 310 pass.
  - [ ] **Re-anchor picks on row identity rather than `file:line`** — NOT done, split out honestly.
    The dereference now *detects* rot; it does not remove the dependency on line numbers. Six of
    seven anchors checked pointed at a tree-diagram branch, a `###` heading or a prose bullet, and
    the task_id's two halves disagree (`--013-` vs `L534`: box #13 is at line 59). Both were computed
    at seed time from a file since rewritten and neither is re-derived.
- [x] **Reporting-unit rule for any scheduler/backlog figure — write it into the shared
  constraints.** ✅ 2026-08-12 — landed as `## Reporting Units` in `agents/shared/OPERATING_CONSTRAINTS.md`, with the C50 origin and the N/M/K decomposition stated as binding form.** Derived from the C50 retraction: the "4,602 pending picks" headline counted
  **records, not work**. Standing form: *"N records resolving to M distinct rows, of which K were
  dispatchable at emission."* K is the only one of the three that was ever a claim about the fleet,
  and it is the one nobody computed. Applies to queue depth, backlog size and advisory volume alike;
  a figure quoted without its distinct-row and dispatchable-at-emission denominators is the same
  error. Belongs in `agents/shared/OPERATING_CONSTRAINTS.md` beside the existing claim-grammar rules.
- [x] **`advisory*.jsonl` rotation keeps no durable history** ✅ 2026-08-12 (`mainB`) — sealed
  shards now archive OUTSIDE the repo and carry their own denominators.
  `advisory_archive_root()` (env `EPYC_BUS_ARCHIVE_ROOT`, default
  `/mnt/raid0/llm/bus-archive/advisory`) puts the record where `git clean -x` cannot reach it;
  `_archive_advisory_shard` copies-then-**verifies by sha256** rather than trusting that a copy
  which exists is a copy which arrived, and writes a ~1 KB `*.digest.json` beside it **even when
  the copy fails** — the digest survives disk pressure a 128 MiB shard will not.
  `summarize_advisory_shard` records the standing form: **N** pick records, **M** distinct rows,
  and per-row `first_ts`/`last_ts`. **K is deliberately left `None`.** Whether a pick was
  dispatchable *at emission* depends on the handoff file's state at that timestamp — which is
  recoverable from git precisely because the per-pick timestamps are preserved, so the digest
  carries K's inputs and names the method rather than inventing a number that would silently be
  computed against today's file. Verified against the live shard: the code re-derives **811
  records → 9 distinct rows** independently, matching the hand adjudication. Mutation-tested three
  ways — a corrupted copy reports `archived: False`, an empty shard yields 0/0 rather than an
  inherited count, and N and M are proven able to differ (8 records over 2 rows). *A history that
  only exists in `clean -x` fodder is not a history.** C38's rotation is correct and closed,
  but the shards land **inside the repo and gitignored** (`.gitignore`: `coordination/session-bus/
  advisory*.jsonl`), which makes the entire scheduler record `git clean -x` fodder. It was destroyed
  on 2026-08-12: the earliest surviving record is **08:20:31Z**, which is precisely why the 4,602
  figure above cannot be re-derived and 811 is what remains. Rotate to a path outside the repo, or
  archive each sealed shard to one. *A history that only exists in `clean -x` fodder is not a
  history.*
- [x] **Nothing on this host explains the deletion of `logs/bus_supervisor.pid`, and nobody owns it.**
  ✅ 2026-08-12 — **NAMED CAUSE, not written off.** The deleter is the supervisor's OWN trap
  (`bus_supervisor.sh:373`) running in a second instance that should never have held the lock:
  something removes `$LOCK_FILE` while A holds it → B's `exec 9>"$LOCK_FILE"` creates a NEW INODE
  and its flock succeeds (C43 cannot refuse what the kernel sees as an unrelated file) → B clobbers
  the pid, is TERM'd, and its trap `rm -f`s it → A is still alive holding the unlinked lock with no
  pid file. That is the C48 symptom exactly, with no external deleter to find, which is why
  "probably the clean run" never fit: it hunts a deleter one layer BELOW the defect.
  **Mechanism reproduced, not argued** — `scripts/coordination/tests/test_supervisor_lock_inode_identity.sh`:
  same-inode contender refused, post-replacement contender ACQUIRES. Ruled out first: path never
  tracked (no git op), `clean -ffdx` runs in `/workspace` and cannot reach `/tmp`, all three
  supervisor tests isolated, tmpfiles ages `/tmp` at 10d.
  **Residual, and it is now the real question:** what removed the lock file. Nothing in the repo
  does. **The fix is upstream of the pid** — flock identity is per-INODE, not per-path, so the
  acquire must verify the fd's inode still matches the path after locking, or the lock must live
  somewhere `/tmp` policy cannot reach. NOT applied here: `bus_supervisor.sh` is a RUNNING script.
  Routed explicitly by `mainD` rather than left implicit: the `auditor` exonerated `a70dbe1a` with
  mechanism — the path was never tracked in any commit, so `git rm --cached` could not have deleted
  it even in principle. C48 makes it moot for *liveness*, but something deleted a live process's
  record and the cause is unestablished. Closes as either a named cause or an explicit written-off.
- [x] **Per-agent shards for the concurrently-appended log files.** ✅ 2026-08-12 Implemented for
  `agent_audit.log` (the only file in scope this pass — `llama.log`/`main.log` from `334d04b3` are a
  different producer, llama-server itself, not this bash/python plane, and stay out of scope).
  `scripts/utils/agent_log.sh` now writes `logs/agent_audit-<AGENT_ID>.log` (falls back to
  `agent_audit-unattributed.log` when `AGENT_ID` is unset) instead of the single shared file;
  `scripts/hooks/earlyoom_audit.sh` gets its own `agent_audit-earlyoom.log` shard too, since it was a
  SEVENTH, previously-undocumented writer bypassing `agent_log.sh` entirely. New shared helper
  `scripts/utils/agent_log_read.sh` (`agent_log_files`/`agent_log_merged`, glob `agent_audit*.log`,
  plain lexical `sort`) is wired into every reader in the same commit: `agent_log.sh`'s own
  `agent_log_tail`/`agent_log_session`,
  `agent_log_analyze.sh` (materializes the merged stream once, rest of the script unchanged),
  `repo_readiness_scorer.py` (glob-broadened `exists_any` patterns), `session_init.sh` (updated
  echo), `scripts/backup/MANIFEST.yaml` (glob so new shards aren't silently dropped from backup
  coverage). `.gitignore` restores tracking for the shard glob (`!logs/agent_audit*.log`) — the whole
  point, vs. the untrack-and-`clean -x`-expose precedent. Legacy `agent_audit.log` stays tracked,
  frozen (no longer written), still read via the same glob — verified backward-compatible.
  **Mutation-tested both directions** (scratch `LOG_DIR`, real interpreters: bash 5.2, python3.13 — no
  venv pinned for this script, `#!/usr/bin/env python3` shebang, checked): a naive single-shard read
  (`wc -l < agent_audit-mainA.log` or legacy-only) undercounts (1 of 4 fleet-wide entries); the merged
  reader (`agent_log_tail`, `agent_log_analyze.sh --summary`) correctly shows all 4 across mainA,
  mainB, earlyoom and the legacy file, from a peer (mainC) that wrote nothing itself. Also fixed a
  latent pre-existing bug surfaced by the same test: `grep -c ... || echo 0` in `agent_log_analyze.sh`
  double-printed on a genuine zero-match category (grep -c already emits "0" AND exits 1) — now
  `|| true`. NOT fixed (flagged, out of scope): several other `grep | while read` pipelines in that
  same script are still `pipefail`-fragile on an all-zero-match category; harmless today because the
  merged stream always includes the large pre-existing legacy file, but noted for a future pass.
  Could not run the repo's pytest suite (no `pytest` module / venv reachable in this sandbox); verified
  `tests/validate/test_repo_readiness_scorer.py`'s exact fixture and assertions by manual replay
  instead (both pass unchanged).
  **Correction, 2026-08-12 coordinator review of 1c6839c5:** the original claim — "all entries share
  ts-first JSON key order, so lexical sort is a correct chronological merge" — was FALSE on the real
  corpus; it only held on the synthetic all-JSON fixture used to verify it. Measured against the real
  `logs/agent_audit.log` (4,402 lines): 1,167 lines are a pre-2026 bracketed format
  (`[2025-12-15T17:12:49+01:00] TASK_END: ...`), not JSON at all, plus a handful of
  `{"timestamp":...}`-keyed (not `"ts"`-keyed) lines from a still-older format. What `agent_log_merged`
  actually does: **two blocks**, not one interleaved chronology — every legacy-bracket line before
  every JSON line, because `[` (0x5B) sorts before `{` (0x7B), which matches real chronology only
  because the bracketed format stopped being written before the JSON format started (Dec 2025
  changeover). Within each block, ordering is correct (bracket lines keep their original append order;
  JSON lines sort by real `ts`). **Decision: two-block ordering is ACCEPTED and documented, not fixed
  with a timestamp-extracting parser** — nothing has written the legacy formats since Dec 2025 (a
  frozen corpus), so a multi-format parser on the hot read path would guard against writes that will
  never happen. Comment corrected in `scripts/utils/agent_log_read.sh`. New fixture-based regression
  test `scripts/utils/tests/test_agent_log_merge_format.sh` mixes both formats (the ad hoc verification
  in 1c6839c5 used only JSON, which cannot distinguish "sorts by real timestamp" from "sorts by leading
  byte, which happens to agree here") and pins the two-block behavior explicitly: 5/5 checks pass
  against the real `agent_log_merged`; run against a mutation that makes `agent_log_merged` return only
  the legacy file (simulating exactly the narrowing regression this design exists to prevent), 3 of 5
  checks correctly fail (total-line count, cross-file JSON `ts` ordering, and a fixture sanity check) —
  but 2 of 5 ("legacy-bracket block is first, in original order" and "no bracket line appears after a
  JSON line") still pass even under that mutation, because both properties are trivially true when
  there are no shards to interleave. Named per the coordinator's direct question: those two are real
  but weak checks on their own; the suite's aggregate result (and specifically checks 1/4/5) is what
  catches the regression, and the suite as a whole correctly reports `fail=3` and exits 1 under the
  mutation.
- [ ] **Worktree isolation phase 2 — the cutover.**

  - [ ] **Re-register the 3 worktrees still holding RELATIVE gitdir pointers.** Measured
        2026-08-12 (`mainA`): `/workspace/.git` and `/mnt/raid0/llm/epyc-root/.git` are ONE repo
        (inode `96604699`) at two depths — a **bind mount**, so `realpath` does not collapse them.
        With `worktree.useRelativePaths=true` git writes pointers that resolve only at the depth
        they were written for, so from the deeper path live worktrees read **prunable** and any
        `git worktree prune` — or the `git gc` that runs one — DELETES their admin data. That is
        what destroyed all five lane worktrees this morning. Config is now `false` and the five
        lanes were re-registered absolute, but **the fix is not retroactive**: three pre-existing
        worktrees remain exposed. `pytest.ini` tells agents to invoke from the deep path, so this
        will recur. Re-register them or rewrite their `gitdir` files to absolute.
  - [ ] **Decide whether to install the pre-push serialization guard.** Built and tested
        2026-08-12 (`mainA`, root `75c7dd59`): `scripts/coordination/serialized_push.py` (62 tests)
        + `scripts/hooks/pre_push_serialization_guard.sh` (56 tests), 50 mutations all killed.
        **Deliberately NOT installed** — nothing registered in `.git/hooks` or settings. This is an
        operator decision, not an engineering one: the guard is advisory (a plain `git push`
        bypasses it, `--no-verify` defeats it), and **only a server-side `pre-receive` on origin
        makes serialization structural**. Decide: install as-is, pursue server-side, or neither.
  - [ ] **Compile 4 pending wiki sources.** `compile_sources.py` reports `total_new: 4` —
        `architect-model-selection-bench.md`, `rocm-verify-profile-backend.md`,
        `session-bus-thin-dispatcher.md`, `progress/2026-08/2026-08-12.md`. NOT compiled in the
        2026-08-12 `mainA` wrap-up, deliberately and with a reason rather than skipped: three of the
        four are that session's own output, and their reusable content — the verification-failure
        faces 12/13/14 — is already durable in
        `docs/guides/agent-workflows/verification-failure-catalogue.md`, so compiling now would
        largely restate it. The two non-mainA sources still deserve a pass.
  - [ ] **Close the `repos/` gap, or record that it stays open.** Worktree phase 2 isolates
        `epyc-root` per agent, but `repos/<name>` is a **symlink out** of every lane worktree, so
        `epyc-orchestrator` and `epyc-inference-research` remain one shared clone regardless of
        which worktree an agent sits in. Measured cost 2026-08-12: three subagents editing one
        shared orchestrator clone held apart only by file-disjoint ownership and a no-commit rule,
        and a `git add` into a mid-cherry-pick index putting 42 files into another agent's commit.
        Phase 2 does **not** cover the sub-repos and should not be read as if it does. Phase 1 items 1–5 are landed above; nothing is

- [ ] **Per-agent shards for the concurrently-appended log files.** Option 2 from the
  `agent_audit.log` adjudication, which untracking deliberately did not implement. Untracking removed
  the merge tax at the cost of the git copy; per-agent files remove it while keeping tracking, and the
  same shape applies to any other all-writers-one-file artifact on this plane. Decide it as a policy
  once rather than per-file — and note that the untrack has already converted two paths from *merge
  contention* into *`clean -x` exposure*, which is the cost this option avoids.
- [x] **Worktree isolation phase 2 — the cutover.** ✅ 2026-08-12 — all five lane worktrees created and
  verified by `setup_main_worktrees.sh mainA mainB mainC mainD auditor`: `/mnt/raid0/llm/worktrees/mains/<agent>` on `lane/<agent>`, `repos/*` synced via each worktree's own
  `clone-repos.sh`, shared pre-commit hooks confirmed firing inside each worktree (secret-shaped blob
  blocked, clean commit allowed, scratch removed), and `session_bus.py --print-root` resolving to the
  canonical `/workspace/coordination/session-bus` from all five — the two-plane split holds.
  **Index isolation proven, not assumed:** staging a scratch file inside `mains/mainA` leaves
  `/workspace`'s staged count at 0. The pathspec-sweep and staged-files-riding-along hazards are now
  structurally impossible rather than a discipline every session has to remember.
  The shared clone was never switched: `/workspace` stayed on `main` throughout, and the tip it moved
  to mid-run (`a90870ec`->`4622c0d7`) was another session committing, not this script.
  *Residual, stated rather than buried:* creating a worktree does not MOVE a live session into it —
  each main must `cd` to its own lane worktree, and until they do, the isolation exists but is unused. Phase 1 items 1–5 are landed above; nothing is
  migrated. `scripts/coordination/WORKTREE_MIGRATION.md` is written and `setup_main_worktrees.sh` is
  verified against a throwaway, but the five mains still share `/workspace` — which is what forced a
  15-minute fleet-wide commit freeze to land one merge, and what put 29 worktrees inside the tree that
  `git clean -ffdx` then swept (`progress/2026-08/2026-08-12.md`). **Not blocked on the
  reboot** — OP-16 was declined by the operator, so this is queued, not gated. Its own task id
  (`guard-universe-and-worktree-isolation`) still has no handoff of its own; give it one at cutover
  or fold it here permanently.
- [ ] **"This main is working serially" must become an observable condition, not something the
  operator has to notice.** The fan-out default is now durable
  (`agents/shared/OPERATING_CONSTRAINTS.md` → *Parallel Subagent Fan-Out*, operator 2026-08-12), but
  nothing on this plane distinguishes a main that dispatched five concurrent subagents from one that
  did the same work on its own thread — so the only detector is the operator saying so, which is how
  it ran unchallenged to 1,070 open backlog items. Build it on the C36 substrate, per backend: for
  Codex mains the rollout files already separate parent from child (`thread_source != 'subagent'`,
  fail closed on absence) and the parent holds FINISHED subagent fds open, so concurrent-child count
  is readable from the parent's fds; for Claude mains use signal #3 (`claude agents --json`) because
  their subagents run IN-PROCESS — which is also why **CPU delta is INVALID here** (C36 constraint:
  a main burned 17% CPU sitting at its prompt). Deliverable: per-main concurrent-subagent count over
  a window, exposed where `probe`/`rebuild` already report liveness. The defect signal is sustained
  zero children while the main's queue is non-empty. Same shape as C35/C36 — the RUNTIME decides,
  not the agent's self-report — so it inherits their fail-closed and UNAVAILABLE-fallback rules.

## Delivery-plane repair — C51–C54 landed, four residuals (filed 2026-08-12 at wrap-up)

`b6ea8679` fixed the root cause of the fleet's idle compute on 2026-08-12: three mains sat with
instructions queued and unsubmitted in their composers, which is indistinguishable from a main that
received the message and declined it. Four defects, each reproduced against real tmux panes before
being fixed; 567 tests pass, mutation-tested at source level (reverting the glyph table, the buffer
check, the C12 ordering, the rollback, the pre-typing guard, the cursor-prefix read, the faint rule,
or any C52 contradiction source each turns the suite red).

- [x] **C51 — the submit step is verified against the BUFFER, not the keystrokes.** ✅ 2026-08-12 —
  `b6ea8679`. `nudge` had no rollback and `record()` ran only on the success path, so a strand that
  failed after the first character was typed appeared in no ledger, no bus row and no log; `doorbell`
  had no post-Enter verification at all; C12's anti-staleness anchor was sampled AFTER the Enter and
  was therefore vacuous. The composer must now return to its pre-typing baseline (a delta, so it needs
  no prompt pattern and cannot rot), and any failure rolls the text back with Ctrl-U and writes a
  `*-undelivered` row. New read-only `pending` detector; unevaluable exits non-zero, so "I could not
  look" never reads as "nothing is pending".
- [x] **C52 — a `state: working` heartbeat must be CORROBORATED before it refuses.** ✅ 2026-08-12 —
  `b6ea8679`. `mainB` settled at an empty composer with its heartbeat still reading `working` on a task
  whose pid was already dead: six nudges refused, MI210 at 0% for thirteen minutes, and single-writer
  meant nobody else could clear the flag. Three verdicts now — corroborated / contradicted /
  undetermined — and undetermined refuses and SAYS so instead of reporting a stale claim as believed.
- [x] **C53 — the cursor is NOT at the end of pending input.** ✅ 2026-08-12 — `b6ea8679`. Measured on
  live panes the cursor parks at column 2 with the text to its RIGHT, and each such string appeared
  exactly once in 3,000 rows of scrollback — never submitted. Every cursor-prefix read called those
  composers EMPTY, including the C51 detector. Emptiness is now judged on the whole row. Faint (SGR 2)
  means placeholder on Codex and pending input on Claude — opposite senses — so the read is
  backend-aware and fails closed when the backend cannot be identified.
- [x] **C54 — `clear` and `submit`, the detector's missing remedy half.** ✅ 2026-08-12 — `b6ea8679`.
  Two verbs, because discarding pending text and accepting it as an instruction are opposite decisions
  only the caller can make. `--expect` refuses if the pane changed under you (TOCTOU), `--force` is the
  blunt alternative, neither given is a refusal. Ctrl-U only, never Ctrl-C, asserted over every branch;
  every discard logged verbatim so a wrongly-discarded instruction is recoverable.

Residuals the repair did NOT close. All four were observed in the same window; none is fixed.

- [ ] **DP-1** (HIGH): **the composer needs a `<char>`-then-`Enter` sequence and the adapter does not
  send one.** Observed 2026-08-12 driving live panes: `Enter` alone against a composer holding pending
  text does not submit it — a character must land first to take the composer out of the state it is
  parked in, and only then does `Enter` commit. `cmd_submit` sends `Enter` directly, so `submit`
  inherits exactly the failure C51 was built to detect: it verifies honestly and reports failure, but
  has no working remedy behind it. Fix belongs in `scripts/coordination/tmux_adapter.py` (owned by a
  parallel session — deliberately NOT edited from this seat). Pin the sequence with a case in
  `scripts/coordination/tests/composer_tui_fixture.py`, which already has selectable Enter behaviour,
  so the calibration announces itself when it rots rather than failing silently.
- [ ] **DP-2** (HIGH): **`clear` and `submit` do not work on Claude panes.** The C54 verbs were
  calibrated against a disposable Codex session; against the five Claude mains neither verb takes
  effect. Same backend asymmetry C53 names — faint SGR 2 carries opposite senses on the two TUIs — and
  it means the remedy half of the detector is live for exactly one of the six roster members. Until
  this lands, a Claude pane holding pending input still needs a human at the keyboard, which is the
  condition C51–C54 were opened to remove. Calibrate on an expendable Claude pane and pin it with a
  fixture case; this seat must not send keys to a live main.
- [ ] **DP-3** (MED): **`bus_supervisor.sh`'s stale-source check is mitigated by a config constant, not
  fixed.** `STALE_SRC_SKEW_S=5` (`scripts/coordination/bus_supervisor.sh:362`) exists because
  `ps -p <pid> -o etimes=` reports WHOLE seconds, so a computed `started` can land up to a second
  before the real start and a source written in the same second as a legitimate restart reads as newer
  than the process it produced — a false positive that recurs every cycle, i.e. a restart loop. The
  tolerance suppresses that, but buys it with a matching false NEGATIVE: a source edited within 5 s of
  a restart reads as current forever, so the daemon runs stale code and the watchdog never says so.
  The real fix removes the tolerance rather than tuning it — take the start time at sub-second
  resolution (`/proc/<pid>/stat` field 22 against `/proc/uptime`, monotonic and already trusted
  elsewhere on this plane) and compare exactly. File owned by a parallel session; not edited here.
- [ ] **DP-4** (HIGH): **shared child clones are reachable from inside every lane worktree, so worktree
  isolation does not prevent cross-agent index contamination.** `repos/<name>` is a symlink OUT of any
  lane worktree to the single shared clone at `/mnt/raid0/llm/<name>`, so a main sitting in its own
  isolated worktree still shares one index and one `CHERRY_PICK_HEAD` with every other agent for the
  orchestrator and research repos. Measured twice on 2026-08-12: (a) `mainA` ran `git add` in the
  research clone without first checking its state and put 42 files into another agent's in-flight
  cherry-pick index (staged 8 → 50); had anyone run `git cherry-pick --continue` in that window,
  mainA's entire A7 staging would have ridden into their commit under their subject line — it was
  caught ONLY because `git commit -- <paths>` refuses with `fatal: cannot do a partial commit during a
  cherry-pick`, and had the commit been allowed nobody would have known; (b) this wrap-up merged and
  pushed that same clone while the cherry-pick was live — verified non-destructive afterwards, but
  nothing structurally forced that check first. Phase-2 isolation as written covers `/workspace` only
  and does not address this. Deliverable: either give each lane its own child-repo worktrees instead of
  a shared symlink, or make every write path assert a clean sequencer state (`CHERRY_PICK_HEAD`,
  `MERGE_HEAD`, `REBASE_HEAD` absent and no unmerged paths) before `git add`/`commit`/`checkout` in a
  shared clone. Fold into **Worktree isolation phase 2** above at cutover, or give it its own handoff.
- [ ] **DP-5** (HIGH): **`cmd_clear`/`cmd_submit` send a BARE keystroke, and a Claude composer ignores
  it — pin the wake character in a committed test.** The call site is one line in
  `scripts/coordination/tmux_adapter.py` (~`:2597`): `key = "C-u" if verb == "clear" else "Enter"`.
  Measured 2026-08-12 against live panes: `Enter`, `C-m`, `C-u` and `BSpace` each left queued text
  exactly where it was, re-read and confirmed; sending any ORDINARY CHARACTER first and only then the
  key submits. So the wake character is not cosmetic — without it `submit` and `clear` cannot succeed
  at all. They failed **honestly** (the post-action re-read caught it every time and never claimed
  success), which is why nothing was lost, but an operator spent an hour pressing keys by hand while
  the tool could only report its own failure. **State at filing (12:52Z): a fix exists in the live
  working tree and is UNCOMMITTED** — it introduces a `C55` block using a SPACE as the wake character
  (inert for `submit`, irrelevant for `clear` since `C-u` kills the line regardless), but `C55` appears
  in neither `main` nor `origin/main` and no commit references it, so a `git clean`/`checkout` on that
  path destroys it with no reflog. This row is therefore filed for the *durable* obligation regardless
  of whether that edit lands: (a) get the wake character committed, (b) pin it with a case in
  `scripts/coordination/tests/composer_tui_fixture.py`, whose selectable Enter behaviour already models
  swallow/picker/cancel and needs only a "bare key ignored, char-then-key accepted" mode, and (c)
  mutation-test it so reverting the wake character turns the suite red. Closing this row closes the
  actionable half of **DP-1** and **DP-2**, which were filed earlier in this same wrap-up against
  committed state and remain accurate against it. NEVER `C-c` — see the C54 block.

## Observation contract — adoption backlog

Filed 2026-08-12 by the class-sweep that followed the `pgrep -f "session_bus_coordinator\.py run"`
watchdog blindness (the live daemon's argv carried `--bus-root <path>` between `.py` and `run`, so a
healthy heartbeating daemon read as dead forever and the watchdog relaunch-looped for hours). The
instance repair is owned elsewhere; this row is about the **class**, and it is enforced, not
remembered — `tests/test_observer_contract.py` reads
[`scripts/coordination/observer_registry.json`](../../scripts/coordination/observer_registry.json)
and goes RED if this line is checked off or deleted without the migration landing.

- [ ] **OBS-1** (MED): **`scripts/coordination/bus_supervisor.sh` adopts the observation contract.**
  Source [`scripts/coordination/observer_guard.sh`](../../scripts/coordination/observer_guard.sh),
  fold identity three-valued (`present`/`absent`/`unobservable`) over ≥2 independent channels, and
  expose the uniform `observe` subcommand (`state=…`, exit 0/1/3). That entrypoint is what enrolls
  the file in the shared behavioural battery — which drives a real stand-in process through
  channel-disagreement and partial-blindness cases, and asserts corrective action is SUPPRESSED
  while blind and still TAKEN when the target is genuinely absent. Reference adoption:
  `scripts/coordination/backfill_supervisor.sh`. On landing, flip the registry row to
  `contract: "v1"` and delete this line. Note the residual the sweep found even after the C49
  repair: an unverifiable identity resolves to **`dead`** rather than `unknown`, which is the one
  place the collapse survives — `session_bus_coordinator.py::_identity_verdict` answers the same
  question with the opposite polarity, so the two halves of one check disagree.

## Decision gates

- `OP-SENDKEYS-CODEX` (send-keys nudging) — operator grant, evidence-driven, default OFF.
- `triage: on` + `triage_calls_per_day` — operator flag after M4 soak.
- Headless-worker caps >0 — operator, only after M4 acceptance.
- M4 go/no-go rests on M3's advisory-accuracy evidence.

## Key files (reuse)

`scripts/coordination/batch_ledger.py` (fold core) · `scripts/coordination/inference_batch.schema.json`
(validation style) · `scripts/coordination/inference_load_check.py` (lane sensing) ·
`coordination/inference-batch/{LOOP_PROTOCOL.md,op-bundle.md}` (contracts) ·
`scripts/dashboard/hub_supervisor.sh` (daemon + watchdog skeleton) ·
`dashboard/{server.py,freshness.py,handoff_parser.py}` (hub) · `scripts/hooks/*_context.sh`
(hook precedent) · `scripts/nightshift/claude_via_devc.sh` (one-shot/headless launcher) ·
`scripts/utils/agent_log.sh` (audit API — coordinator-daemon + agents log through it).

## fleet_watch.sh — productionisation residuals (filed 2026-08-12)

`scripts/coordination/fleet_watch.sh` (the coordinator's continuous fleet-stall detector) was
hand-written on the coordinator's own thread under time pressure and has been rebuilt as a tested
detector: authoritative sources first (`tmux_adapter.py probe` → tmux `window_activity` → pane
glyphs), three-valued everywhere, cursor-anchored composer reads, and a `DETECTOR-BLIND` guard so
UI drift announces itself instead of manufacturing six idle mains. Evidence:
`scripts/coordination/tests/test_fleet_watch.sh` (76 assertions, both directions on every rule) and
`scripts/coordination/tests/test_fleet_watch_mutation.sh` (21 deliberate breakages, 21 caught, each
mutation proven APPLIED before it counts). These are the things that rebuild FOUND and could not fix
from that seat.

- [ ] **OBS-11** (MED): **`scripts/coordination/fleet_watch.sh` adopts the observation contract.**
  It decides whether six mains are alive, so it belongs to the class this contract governs — but
  `observer_registry.json`'s discovery cannot find it (Rule A looks for `pgrep`/`pidof`/`ps -e`, and
  this file identifies nothing by argv; Rule B looks for `observer_guard.sh`, which it does not
  source). It is therefore enrolled by hand as `unadopted`, which is exactly the case the registry's
  "reviewed, not forgotten" row exists for. Adoption means sourcing
  [`observer_guard.sh`](../../scripts/coordination/observer_guard.sh), folding main-liveness
  three-valued over ≥2 independent channels, and exposing the uniform `observe` entrypoint so the
  shared behavioural battery runs against it. The three-valued fold is already the file's internal
  discipline (`fw_classify_liveness` / `fw_classify_compute` return `unknown` and never collapse it
  to idle); what is missing is the `observe` surface and the battery.
- [ ] **FW-1** (MED): **the Codex EMPTY composer is excluded BY NAME, and that calibration can rot.**
  An empty Codex composer *renders text* — a greyed placeholder (`› Write tests for @filename`).
  Measured 2026-08-12, neither available discriminator separates it from real queued input: the
  placeholder carries the same dim SGR (`ESC[2m`) that Claude uses for genuinely queued text, and
  `cursor_x` is parked at column 2 on every live pane in BOTH the empty and the text-present case,
  so the cursor slice `tmux_adapter.py` relies on cannot separate them either. So `fleet_watch.sh`
  excludes the placeholder with a `PLACEHOLDER_RE` list. If a Codex release ships an unlisted
  placeholder, it reads as pending input and parks a PERMANENT false `STUCK-INPUT` on `inference` —
  the cry-wolf failure the persistence rule exists to prevent. Enumerating the set needs keystrokes
  into a live pane, which this seat must not do. Fix: get an authoritative empty-composer signal for
  Codex (the rollout/TUI state, not the rendered row), or enumerate the placeholder set from an
  expendable pane and pin it with a fixture.
- [ ] **FW-2** (MED): **five of the six mains have NO runtime liveness signal, so `IDLE-CANDIDATE`
  is a heuristic for them.** `runtime_liveness()` implements the rollout check for Codex only;
  measured across the live roster 2026-08-12, `inference` returns `active`, while `auditor`, `mainA`,
  `mainB`, `mainC` and `mainD` all return `None` with *"backend 'claude': no runtime signal
  implemented yet"*. For those five, `fleet_watch.sh` falls back to tmux's `window_activity` clock
  plus a busy-marker veto — which is why every idle report is a CANDIDATE and says
  *"may be compacting"*. This is the same gap as M5/C36's unwired signal #3
  (`claude agents --json`); landing it upgrades this detector from heuristic to authoritative for
  the whole fleet, and is the single highest-value change available to it.
- [ ] **FW-3** (LOW): **nothing supervises the watcher.** If `fleet_watch.sh` dies, nothing restarts
  it and — worse — nothing notices: the coordinator's Monitor on the log simply goes quiet, and a
  quiet log is what a healthy fleet also looks like. The `flock` single-instance guard is in place,
  so a supervisor can safely relaunch it unconditionally. `bus_supervisor.sh` is the pattern; it was
  not extended from this seat because it has a live owner in a parallel session.

## Reporting instructions

Flip milestone boxes with `✅ YYYY-MM-DD` + evidence refs (M4 cites the hub saturation-history
artifact). Progress-file entry per milestone. Note the single-writer audit outcome per bus
file at M1 and M4. Any deviation from §Skeleton is recorded inline here with rationale.
