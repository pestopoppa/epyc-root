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

- [x] **C-OWN — the C-series needs a new owner.** ✅ 2026-07-29 — **adopted by roster id `auditor`**
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
- [ ] **C23 (NEW) — triage disposition should not require an identical payload per `corr_id`.**
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
- [x] **C18a — `codex-bus-tests` carries `role: retired` with a stale heartbeat.** ✅ 2026-07-29 —
  **bookkeeping, confirmed, no delivery risk.** Heartbeat `idle`, age ~21 h. `role == "retired"`
  already makes the relay treat it as an unreachable routing recipient
  (`session_bus_coordinator.py:1937`), so the staleness is cosmetic. Note this is distinct from the
  still-open C18(a) *decision* about what that roster row should ultimately be — that is a
  coordinator call and is unchanged.

> ### POST-REBOOT HANDOVER — `claude-gpu-lane`, closed 2026-07-29 (read this first)
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
  - [ ] **C11 — C9 landed without the independent review its own filing required.** The C9 entry
    says the change "wants an independent review before it lands, not a same-session self-merge",
    and it was implemented and committed (`8cbe50c0`) by the same session that had just reviewed
    C6 — on direct operator instruction, which supersedes the handoff's own procedure, but the
    review debt is real and unpaid. A second pair of eyes on `live_mains` / `resolve_spawn_cap` /
    `cmd_spawn` is cheap now and expensive after something spawns wrongly. Not urgent: the change
    is fail-closed on every branch it cannot evaluate, and both suites are green.
  - [ ] **C12 — the nudge fragment can collide with the transcript.** Post-Enter success is "the
    60-char tail is on the pane but not at the cursor". If an identical fragment is already in the
    scrollback (the same nudge sent earlier, or an agent echoing the text), an Enter that never
    submitted could still find it and read as success. The 600s rate limit makes a same-text
    repeat unlikely and the failure needs a *second* fault to matter, which is why it is filed
    rather than fixed. Closing it properly means anchoring the echo to a position *below* the
    pre-Enter cursor rather than anywhere on the pane.
  - [ ] **C13 — nudge refuses `@` anywhere in the message, which is broader than the hazard.**
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
    - [ ] **ACTIVATION for the second half: the daemon at epoch 9 predates it.** Third activation
      gap on this file in one day. The notice is inert until the daemon's owner restarts it —
      or, most likely, until the post-reboot restart picks it up for free. Not this lane's to do.
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
  - [ ] **OPEN — make the two sides agree, and unstick the 217 rows.** Two coupled contract calls,
    escalated with options: (i) which interpreter is authoritative for authoring (pin the venv in the
    documented command, install jsonschema for the system python, or ship a wrapper); (ii) whether
    `_renamed_from` should be permitted by the schema (it is provenance the rename deliberately
    added to preserve history) or stripped from the 217 rows. **Until one is chosen those 217 rows,
    including both C27 gates, remain un-relayable to any inbox.** Note the C27a/C27c fixes DO still
    present the two gates to `token-queue.md` — `relay_tokens` reads outboxes directly and does not
    validate — so the operator path is unblocked even while the inbox path is not. Verified.
- [ ] **C28 — relay is tracked by destination FILE, not by message identity, so moving an inbox
  re-floods it.** *Observed 2026-07-29 during the roster rename.* Renaming the roster ids meant
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
