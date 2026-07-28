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
  - [ ] **M5b — operator disposition for preserved roster orphans.** C7 prevents recurrence and
    keeps existing task-named heartbeat/outbox files out of roster-derived state, but does not
    delete or move evidence. Decide whether each preserved artifact is retained evidence, gets a
    roster row, or is superseded by a task signal; only the operator can authorize disposition.
  - [ ] **M5c — standing instructions do not reach running sessions.** A CLAUDE.md rule added at
    21:43Z left an active agent on its 19:45Z heartbeat. Recorded in `BUS_PROTOCOL.md`; the open
    task is for coordinator-agent to nudge running mains to *re-read* on every such change.
  - [ ] **C9 — `cmd_spawn` caps a daily action count, not live concurrency.** *Observed
    2026-07-28.* `caps.max_spawns_per_day` is enforced by counting `kind == "spawn"` rows in
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
  Original list: Claude Stop/SessionStart drain hook
  (clone `*_context.sh`) · send-keys adapter behind `OP-SENDKEYS-CODEX` (OFF; rate-limited;
  idle-pane check) · hybrid triage (dead-agent drafts + routing annotations; budget-capped;
  `DRAFT-UNREVIEWED`) · headless workers via `claude_via_devc.sh` under caps. Accept: per
  feature as specced. Rollback: per-flag disable.

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

## Reporting instructions

Flip milestone boxes with `✅ YYYY-MM-DD` + evidence refs (M4 cites the hub saturation-history
artifact). Progress-file entry per milestone. Note the single-writer audit outcome per bus
file at M1 and M4. Any deviation from §Skeleton is recorded inline here with rationale.
