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
- [ ] **R3 — declare both subsystems instances of the ratified fabric contract (M1).** The
  CPU-region lock and this bus are the same five-part structure: resource set · exclusive claim ·
  co-residency policy as data · admission gate · typed defer reasons. Give the bus's co-residency
  policy the contention-matrix shape (pair-keyed, `verdict` + floor) **including a
  `topology_hash` staleness guard** — a stale hand-declared `contention_class` currently fails
  silently. Promote declared classes toward measured ones reusing
  `epyc-orchestrator/scripts/server/contention_matrix.py`, never a second generator.
  **Correction to §Convergence:** read-only sensing is *not* sufficient for exclusion (TOCTOU) —
  anything occupying CPU regions must **acquire** the locks, per fabric axiom 1.
- [ ] **R4 — lease authority and revocation-by-drain (M4).** Grant/revoke belongs to
  coordinator-agent. `cpu_region_lock` **cannot be revoked by a third party** (`cancel_check`
  only aborts an in-progress acquire; a held flock releases on fd-close), so authority lives in
  an advisory layer *above* the flock, with the flock remaining liveness truth. Revocation =
  quiesce + drain at the holder's next boundary, reusing the ratified swap protocol — never
  mid-decode (axiom 4). A revoked main continues on `lane: none` work immediately.
  **Prerequisite:** every queue row declares its gating (`cpu`/`gpu`/`both`/`none`); a missing
  classification is a hard validation failure, because without it revocation has no defined
  fallback set.
- [ ] **R5 — priority classes and pausability (M4).** Classes
  `production-live` > `operator-directed` > `background-churn`; yield = quiesce + drain, never
  kill. Long work drains via **progressive persistence** (every persisted unit is a drain point —
  no segmentation ceremony), enforced by `lease.max_hold_s`. **Pausability splits by run type:**
  `exclusive-contiguous` for decision-gating timing runs (never paused — a run split across a
  pause spans different thermal/cache/NUMA-warmth states and the halves may not compose into one
  valid observation) versus `resumable` for quality evals, sweeps, replays, and evidence
  collection. Class axis is designed now, populated when real production traffic exists.
- [ ] **R6 — coordinator-agent as integration owner (M5).** Wrap-up (via
  `epyc-root/scripts/coordination/flip_checkbox.py`), worktree merging, pushing, merge-to-main.
  Structurally removes the shared-clone hazard: `/workspace/repos/<n>` and `/mnt/raid0/llm/<n>`
  are the same tree, so parallel mains' staged files ride into each other's commits — mains in
  worktrees with a single integrator fixes it by construction. **Merge-to-main gates on content,
  not category:** autonomous unless the diff touches a human-only path (`MEASUREMENT.md`,
  `instrument_eras.yaml`, eval tower/scoring, safety gates, era rows,
  `production-consolidated-*` kernel state), where it becomes a boundary token; the kernel case
  additionally carries the four-step promotion workflow. Git hygiene as enforced rules:
  path-scoped adds only, `fetch` + `log @{u}..main` before commit, no branch switching in a
  shared clone. **Exclusion:** may flip checkboxes and append progress, may **not** create
  handoff stubs, intake entries, or index rows.
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
  `outbox/<a>` whose `from` is not `<a>`). Defects go to `advisory.jsonl`, preserving M3's verified
  zero-foreign-writes property.
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
- [ ] **R8 — consolidated unblock artifact (M2).** Coordinator-agent maintains ONE continuously
  current artifact listing every pending gate — bench tokens, trust-boundary applies, and R6
  merge gates alike — each line individually strikeable, every command pre-validated end-to-end
  (a failed operator-presented command is an agent defect). Operator runs **one command on
  return**. Follows the `ratify_*.sh` idiom: pinned HEAD + file `sha256`s, refuse on drift,
  idempotent; a failed validation repairs and re-presents the **same** token, never a new chain.
  Per-line independent validation so striking one line cannot invalidate the rest; a struck line
  returns to `HELD_OP_GATE` — held, not dropped, not silently requeued. **Not** a dwell-time
  metric: waiting on a token must never idle anything, so the only counter kept is
  idle-lane-time-while-eligible-work-existed, as an invariant alarm that should read zero.
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
  Emits advisory `saturation` / `would-assign` / `would-idle` / `would-skip` records to
  `advisory.jsonl` only.
  Verified: **survives kill -9 via supervisor** (recovered in 1s, epoch 1→2, and advisory rows
  carry the epoch so a pre-restart generation is identifiable); **zero writes to foreign files**
  (only `advisory.jsonl` + its own heartbeat, both daemon-owned); eligibility honours priority
  order, lane-busy, ungranted `operator_gates`, and non-terminal `depends_on`;
  `authority: assign` is **refused** because M4 is not built — an unbuilt assign path must never
  be silently approximated by the advisory one.
  Two bugs found by its own tests and fixed: `classify_load()` returns `state`, not `class`
  (reading the wrong key fail-safes to permanently-busy, so the daemon would never have advised
  anything), and the same task was being advised to every idle agent (harmless while advisory,
  a double-assignment once M4 has authority).
  **Remaining for M3 sign-off: would-assign matches actual human/agent choices over a working
  day, divergences explainable.** That needs elapsed time and cannot be compressed. The daemon is
  running in advisory mode to accumulate it; the supervisor loop is NOT started (operator's call
  — `bus_supervisor.sh loop`, or the cron `once` entry in its header).
  Rollback: stop the daemon; the bus returns to fully-functional M1 manual mode.
- [ ] **M4 — assignment authority.** Real task-assign + lease/stall ladder + requeue + token
  relay; mains consume assignments at boundaries. Accept: 48h with zero idle-lane time while
  eligible work existed (hub saturation history is the evidence); one induced stall exercises
  nudge→requeue; induced coordinator-daemon restart mid-assignment shows epoch fencing (no double
  assignment); operator touched ONLY token-queue checkboxes. Rollback: `authority: advisory`.
- [ ] **M5 — flag-gated extensions** (each independent): Claude Stop/SessionStart drain hook
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
