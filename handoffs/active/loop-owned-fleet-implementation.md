# Loop-Owned Fleet — implementation

> **Fold destination** (BRF-T1-F19, BRF-T1-1, route 1a, 2026-11-02): absorbs 2 handoff(s) as `## Track:` sections at the end of this file (`fleet-fanout-measurement.md`, `wrap-up-division-of-labor-policy.md`). The body above the first track is the former `loop-owned-fleet-implementation.md`.

**Status**: ACTIVE — implementation not yet started; plan ratified, all decisions signed.
**Created**: 2026-08-15
**Priority**: P1 — restructures the coordinator-agent + mains architecture whose failure record is
`coordinator-role-failure-modes-and-refactor.md` (RTG-48) and `session-bus-thin-dispatcher.md` (RTG-34).
**Parent index**: [routing-and-optimization-index.md](routing-and-optimization-index.md)
**Owner**: unassigned (dispatch at Phase 0 start). **Reviewer**: `auditor`.
**Plan of record**: the "Loop-Owned Fleet" artifact, v5 (decisions ratified 2026-08-15; D4 amended same day).
Source file: `/workspace/tmp/fleet-restructure/loop-owned-fleet.html` — copy into
`docs/design/loop-owned-fleet.html` as task P0-0 below so the plan of record is in-repo and versioned.

## What this is

The ratified restructure of the coordination layer, produced from a six-reader audit + two
adversarial reviews + operator decision rounds (2026-08-15, in-session via decision packages). Thesis:

> **Code owns the loop. Models judge at choke points, with examples in the prompt. Workers run in
> visible panes the operator can steer — but the machine's only channel to them is spawn-args in,
> report file and exit status out.**

This handoff is the implementation tracker. The design rationale, adversarial findings (R1–R20, the
delete-lens, the OP row) and diagrams live in the plan of record; do not restate them here — cite them.

## Ratified decisions (operator, 2026-08-15) — binding on every task below

| ID | Decision |
|----|----------|
| D0 | Two-level worker pool: 2 interactive sessions (console + inference) + ≤4 pool workers, each fanning out 3–5 subagents. Coordinator keeps dispatch + compute negotiation. |
| D1 | Standing spawn authority for the runner, bounded: concurrency ≤4, pinned paid provider, ~250k tokens/batch ceiling (doubles as the Phase-2 cost gate). Revocable on any violation. |
| D2 | Worker harness = `worker_harness:` config knob, per-lane overridable. Claude Code for the ≤10-row pilot; codex exec default for scale-out; easy to change later. Console harness unconstrained. |
| D3 | NO cron. Manual relaunch packaged as the hardened `/coordinator-agent` cold-start skill (reboots are operator-only, so the operator is present at the relaunch moment). |
| D4 (amended) | Compute owned at the COORDINATION level, not by a session. Console (in conversation with the operator) authors the compute policy file and approves choreography recipes; the daemon executes grants deterministically (region-free ∧ policy-allows); AutoKernel, AutoPilot, inference, pool workers are all symmetric consumers. Amends bus rule 11: ownership = policy authorship, not a session. |
| D4b | Exotic lease arrangements = named choreography recipes: typed, receipt-gated step sequences (e.g. drain@boundary → GPU load → run ∥ resume), approved once, executed deterministically by the daemon forever after. New arrangement = new recipe file, never code (policy-data-never-code). |
| D5 | Bus runtime relocated off the git tree; tracked symlink at the old path (survives `git clean -ffdx`). |
| D6 (amended) | Kill-with-salvage: kill at lease expiry is allowed, loss is FORBIDDEN. SIGTERM → grace → SIGKILL, then mandatory salvage: uncommitted worktree state committed to `salvage/<task_id>`, harness transcript + pane scrollback attached to the row, row marked FAILED with a `salvage_ref`. Nothing is ever discarded. **Requires a BUS_PROTOCOL rule-8 amendment** (lease-expiry salvage exception for POOL WORKERS ONLY; interactive-session reclaim stays quiesce-and-drain) — lands with P2-4 under operator ack, BEFORE the first kill path ships. |
| D7 | One-time signed ghost sweep (11 dead-owner rows/claims, owner-death verified, list enumerated for operator review first) + `.orphan` worktree disposal (archive tarball, verify tips contained in lane branches, delete by explicit path list — NEVER `git worktree prune`). |
| D8 | Worker panes are VISIBLE and human-authoritative: the operator may watch, steer, and answer permission prompts by hand. The machine never types into a pane and never makes a decision from pane text; it may capture scrollback as evidence for human triage. Completion signal = schema-valid report file, never pane text. |
| D9 | Operator-gated loop-plane merges: the fleet may file typed defect rows and proposed patches, but merging any change under `scripts/coordination/**` requires operator ack. Self-repair share is computed by commit-path classification, never self-reported. **Handoff-local discipline for this implementation** (a scoping of ratified D9, not an extension of it): changes under `scripts/coordination/**` and any BUS_PROTOCOL amendment land as proposed commits with operator ack; Phase-1 doc/agent-file edits outside that path ship-and-fix-forward per the Phase-1 gate. |

Standing constraint (from the plan): **prose-rule moratorium** — from Phase 0 onward, a new incident
appends a labeled example to the eval fixtures, never a new rule/conjunct to BUS_PROTOCOL or agent files.

## Invariants that must survive every task — P1-1 copies THIS list into INVARIANTS.md

1. Single writer: each agent writes only its own outbox/heartbeat/cursor; path-derived authorship.
2. Never block on the bus.
3. The daemon is mechanical-only: it files defects on mechanically checkable violations, never grades work.
4. Trust boundaries are human-only: hash-pinned `human_only_paths.yaml`, refuse on pin mismatch; never sign.
5. Claims are ACQUIRED, never observed (flock; observing is TOCTOU).
6. Reclaim of interactive sessions is quiesce-and-drain at a boundary — pool workers get the D6
   salvage-kill exception ONLY (rule-8 amendment, P2-4).
7. Full coordinator state reconstructs from bus files alone.
8. Compute windows are requested via the bus and granted per policy (rule 11 as amended by D4).
9. Never tick another agent's checkbox.
10. Never edit `human_only_paths.yaml`.
11. Never commit another session's in-flight work (salvage of a DEAD pool worker's tree is the D6 exception).
12. No name-pattern kills — owned, self-captured pids only; verify death after killing.
13. Two-sample persistence before any destructive or escalatory action on an absence/idleness claim.
14. Gating declaration mandatory on queue rows.
15. The measurement trust boundary is human-amendment-only.

---

## Phase 0 — Stop the bleeding (Day 1)

Gate: **live-fire drill** — fleet killed ⇒ assignment halts and the operator's push channel receives
exactly ONE alarm; the cold-start skill brings the supervision tier back and re-verifies.

- [x] P0-0 Copy the plan of record into `docs/design/loop-owned-fleet.html`; future amendments edit
      the in-repo copy first, republish to the artifact second.
- [x] P0-1 Alarm channel: one operator-reachable push mechanism. Present ntfy vs email as a decision
      package (options + recommendation) at dispatch — not an open question mid-task. Day-1 sources:
      daemon fleet/runner-dead + supervisor death (the only producers that exist on Day 1);
      queue-aging arrives with P3-3 and aged compute-requests with P3-5, wired to this same channel.
      Emit once on state change, never per tick. Deliverable includes the kill-the-fleet drill script.
- [x] P0-2 Fleet-existence gate in the daemon: zero live roster mains ⇒ halt assignment + ONE
      critical alarm (not per-task INFRA_BLOCKED). Predicate is explicitly transitional — see P3-4.
- [x] P0-3 Ghost-state sweep (D7, operator-signed): enumerate the 14 INFRA_BLOCKED rows + 11
      dead-owner CLAIMED/RUNNING/STALE_REQUEUED rows and claims; verify owner death via process
      table; present the list; on signature, release + reset to READY (or CANCELLED where the
      premise died). Add the standing rule: claims owned by retired ids are daemon-releasable with a
      receipt.
- [x] P0-4 Fix `backfill_supervisor.sh` undefined `health_ok` (loop mode always takes the failure
      branch); add a test that exercises `loop` — THE consumer, not A consumer.
- [x] P0-5 Verify the H-4 SHA deploy-marker predicate is what the RUNNING bus_supervisor executes
      (`ps -o lstart` vs commit time of `bc6dc77f`); restart if stale.
- [x] P0-6 Harden `/coordinator-agent` into the D3 cold-start one-shot: relaunch supervisors, verify
      daemon health (pid identity + SHA marker, never the status file), run the alarm drill, report.
- [x] P0-7 Bus runtime off-tree (D5). Scope: RUNTIME DATA ONLY — `queue.jsonl`, `advisory.jsonl`,
      `claims/`, `tokens/`, `inbox/`, `outbox/`, `cursors/`, `heartbeats/`, and the `*_state.json`
      files move to `/mnt/raid0/llm/bus-runtime/`; tracked policy files (`config.yaml`,
      `BUS_PROTOCOL.md`, `session_bus.schema.json`, `human_only_paths.yaml`) STAY tracked in place.
      Procedure: quiesce the daemon + watchers → `mv` → tracked symlinks at the old paths → restart →
      verify every consumer resolves (Python `get_bus_root()` AND the shell daemons, which hardcode
      paths separately — enumerate them at implementation). Written rollback: reverse-`mv` + symlink
      removal, daemons quiesced again. **Sequencing: run P0-3 strictly before P0-7, same session** —
      never rewrite the queue while it is being moved. Document the real path for backup tooling.
- [x] P0-8 `.orphan` worktree disposal (D7): archive tarball → verify each orphan tip is contained
      in a lane branch (push unique commits first if not) → delete by explicit path list. Add runner
      refusal for lane paths matching `*.orphan*` (lands with P2-1).
- [x] P0-9 Declare the prose-rule moratorium in force: create `coordination/evals/fixtures/` with
      the fixture format (`label_provenance` field mandatory) and a README stating the rule.

## Phase 1 — Doctrine collapse (Days 2–3)

Gate: ship and fix forward (pure deletion needs no drill); moratorium verified in force.

- [x] P1-1 `agents/shared/INVARIANTS.md`: the ~15 real invariants, verbatim, no origin narratives.
      Mechanical protocol cited from `session_bus.schema.json`, not restated.
- [x] P1-2 Deduplicate headline rules (fan-out, liveness, checkbox, dispatch-identity, reload
      ownership, observation windows…): one canonical copy each; CLAUDE.md and every other surface
      cite, never restate. (The fan-out rule's 08-13 exceptions currently exist in 1 of 5 copies.)
- [x] P1-3 Resolve the three live self-contradictions with one explicit ruling each, recorded here:
      (a) wrap-up cadence (manual-trigger banner vs lifecycle checkpoint contract vs binding 08-11
      per-task rule); (b) subagent index edits (SESSION_LIFECYCLE "coordinator subagent preferred"
      vs CLAUDE.md prohibition); (c) role-based delegation (role files/delegation matrix vs the
      measured role-decomposition anti-pattern).
- [x] P1-4 Move incident narratives out of the instruction path: BUS_PROTOCOL/coordinator-agent.md
      shrink to contracts; narratives live in the ledgers; judgment heuristics become per-decision
      example packs under `coordination/evals/examples/` (future few-shot content).
- [x] P1-5 Archive the eight dormant role files (benchmark-analyst … sysadmin) and the amber unwired
      task-flow sections; regenerate the flow doc from wired reality only.
- [x] P1-6 Rewrite `agents/coordinator-agent.md` to ~50 lines: identity, invariants pointer,
      choke-point contracts, console role (primary operator channel; no clock ownership; no
      instrument reading; compute-policy editor per amended D4).

### P1-3 rulings (recorded 2026-08-16) — binding

Canonical home: `agents/shared/OPERATING_CONSTRAINTS.md` → *Doctrine rulings — 2026-08-16*.
Recorded here as well because P1-3 says "recorded here".

- **(a) Wrap-up cadence.** The binding 2026-08-11 operator rule wins: **one task done = one wrap-up,
  AS YOU GO** — not manual-trigger-only, not session-end. What survives of the "MANUAL TRIGGER ONLY"
  banner is narrower and real: the two BROAD, DESTRUCTIVE steps (index PRUNING, the wiki compilation
  sweep) run only inside an operator-invoked `/wrap-up`. Everything else — progress report, checkbox
  sync, handoff updates, `Next action` refresh, agent log, pathspec commit, lane promotion — runs at
  every completed task, autonomous and nightshift sessions included. **Nothing may auto-trigger the
  full routine**: no `Stop`/`SessionEnd`/`PreCompact` hook, no cron, no nightshift task, and there
  must not be one. `agents/commands/wrap-up.md` and `agents/shared/SESSION_LIFECYCLE.md` were both
  changed to say this; the ruling itself is unchanged by either.
- **(b) Subagent index edits.** **A subagent may PREPARE index edits; the owning session APPLIES
  them and owns the commit.** Drafting row text, running `index_state.py --check` and reporting the
  exact diff is preparation. Adding, deleting or re-pointing an index row is never a subagent's own
  write. This reconciles SESSION_LIFECYCLE's "wrap-up may run via a coordinator subagent —
  preferred" with the standing CLAUDE.md prohibition: both hold, because preparation is not
  modification. Explicit operator approval is required only to widen it — a subagent writing an
  index directly. Same rule for intake entries and handoff stubs.
- **(c) Role-based delegation.** **Decomposition by ROLE is a measured anti-pattern and no live
  surface may instruct it.** Decompose by CONTEXT BOUNDARY. Confirmed by sweep on 2026-08-16: the
  eight persona files are archived, the roster (`coordination/session-bus/config.yaml`, closed set
  `main`/`coordinator-agent`/`reviewer`/`retired`/`service`) is the sole authority on who holds
  which role, and no live surface routes by persona. Two corrections were needed and made:
  `docs/guides/agent-workflows/research-writer.md` instructed dispatching "to a session acting in
  the research-writer role", and `docs/guides/agent-workflows/INDEX.md` carried persona framing in
  its header. `agents/README.md` → Model Routing (Task-Based) is model-tier-vs-task-difficulty
  routing, **not** the anti-pattern, and stays. Residual, filed not fixed:
  `agents/archived/lead-developer.md` still holds a Delegation Matrix whose six backtick paths are
  now dangling — invisible only because both validators glob `agents/*.md` non-recursively.

### P1 blocker — the doctrine corpus is behind the trust boundary

`agents/shared/*.md`, `CLAUDE.md` and `agents/AGENT_INSTRUCTIONS.md` match the human-only write list
(`coordination/session-bus/human_only_paths.yaml`), so `scripts/hooks/check_trust_boundary_edit.sh`
refuses agent Write/Edit on them — by construction, as containment. P1-1's `INVARIANTS.md` and the
P1-2/P1-3 canonical merges therefore land through the operator/ratify path, not an agent edit:

- Package: `tmp/p1-doctrine/apply_p1_doctrine_collapse.sh` (dry run by default, `--apply` to write,
  `--only <NAME>` to narrow). Every target sha256-pinned to its current content; drift or a
  pre-existing `INVARIANTS.md` aborts that item without touching the rest; already-applied items
  report "already applied". Companion: `tmp/p1-doctrine/PACKAGE.md`.
- `agents/coordinator-agent.md` (P1-6) is in the same package **only** because it cites
  `agents/shared/INVARIANTS.md`; the reference guard and `validate_agents_references.py` both refuse
  a dangling reference, so the two files must land together.

## Phase 2 — worker_runner MVP + pilot (Days 3–5)

Gate (absolute, measurable): ≥10 rows end-to-end with schema-valid reports · zero machine
delivery-plane interventions · zero silent permission denials · 100% independently audited ·
operator spot-reviews 3 of 10 · tokens/row within the D1 ceiling. Kill: quality drop or ceiling
breach ⇒ stop, reassess.

- [x] P2-0 Pre-create the POOL worktrees: `worktrees/pool/lane0..lane3` (operator-visible step).
      **Pilot workers NEVER spawn into mainA–D's lane worktrees while their interactive mains are
      live** — a worker's commit-per-unit or salvage commit in an occupied worktree is the documented
      commit-sweep hazard. mainA–D lanes become available to the pool only after P3-1 retirement.
- [x] P2-1 `scripts/coordination/worker_runner.py` (~200 lines target): claim (O_EXCL) → typed brief
      (AUD-2 schema: task_text primary, ≤4KB, screened_by, expected_occupancy, constraints[].source)
      → premise preflight (P2-2) → permission profile injection (P2-3) → pool-lane lockfile (1 worker
      per worktree; refuse non-pool and `*.orphan*` paths until P3-1) → spawn in a VISIBLE tmux pane
      (D8) → watch report-file + process exit → collect (schema validation, denial audit,
      `subagents_spawned`) → bus writes under the `workerpool` identity → audit packet (pointers
      only) → promotion row. Exec'd fresh per assignment by the daemon tick; the only persistent
      piece is the collector wait. Includes the `session_bus.schema.json` update: target status set
      is **READY · RUNNING · DONE_PASS · FAILED · HELD_OP_GATE** (5 states); `parked` = READY + a
      `parked_reason` field, salvaged = FAILED + a `salvage_ref` field — annotations, NOT new states.
- [x] P2-2 `premise_screener`: point LLM call, forced-choice still-needed | stale | UNKNOWN with a
      mandatory evidence quote; UNKNOWN/stale ⇒ park row + routed fix task (refusals emit once, on
      state change, and count as queue-aging). Few-shot examples from `coordination/evals/examples/`;
      eval fixtures with `label_provenance` before any authority promotion.
- [x] P2-3 D2b permission profile: per-worker settings allowlist; any denied tool call recorded in
      the report ⇒ row outcome FAILED/blocked, never silent parity. Interactive-pane prompts remain
      answerable by the operator (D8); unanswered ⇒ lease expiry ⇒ salvage.
- [x] P2-4 Kill-with-salvage (D6): lease expiry ⇒ SIGTERM → grace → SIGKILL (owned pid only), then
      WIP commit of the pool worktree to `salvage/<task_id>`, attach harness transcript + captured
      pane scrollback to the row, mark FAILED + `salvage_ref`. Mutation-test: a salvage that loses
      any file must fail the runner's own test. **Includes the BUS_PROTOCOL rule-8 amendment**
      (pool-worker salvage-kill exception; interactive reclaim stays drain-only) — proposed commit,
      operator ack, merged BEFORE the kill path first runs.
- [x] P2-5 Roster + daemon wiring: add `{id: workerpool, role: main, endpoint: "exec:worker_runner"}`
      and the daemon endpoint-scheme branch — the ONE schema/code extension the plan permits.
      `worker_harness:` config knob (global + per-lane override), pinned paid provider, concurrency
      cap ≤4, ~250k tokens/batch ceiling (D1). Rollback note: revert = delete the roster row +
      revert the endpoint-scheme commit (both under D9 ack); the daemon must refuse `exec:` endpoints
      it has no branch for, so a half-rollback fails closed.
- [x] P2-6 Static batching: rows from the same source handoff share one invocation, cap 3, per-row
      completion records; on timeout only the in-progress row fails, untouched rows return to READY.
- [x] P2-7 Headless audit per completion: auditor invocation consumes the pointer packet, derives
      the diff from git independently, runs one mutation probe, writes a typed verdict to the bus.
- [x] P2-8 Merge cadence: promotion rows serialized through `merge_gate.py` / `serialized_push`, one
      at a time; part of the 10-row acceptance.
- [x] P2-9 Run the pilot: 10 screened churn rows in the POOL worktrees (P2-0), alongside the
      existing fleet (additive; nothing retired). Record tokens/row — mandatory input to the Phase-3
      go decision and the D2 scale-out harness choice.
- [x] P2-10 Belief-kernel wiring (CLAUDE.md standing rule — file IMMEDIATELY, not when ready): the
      completion reports (`subagents_spawned`, tokens/row), audit verdicts, and the duty-cycle /
      self-repair metrics are new measurement producers. Add the source row to
      `scripts/vidya/adapters/README.md` and the wiring task to
      `handoffs/active/vidya-belief-substrate-program.md`.

## Phase 3 — Retire the machine delivery plane (Days 6–7)

Gate: one full day of backlog churn with zero machine pane-IO for workers.

- [x] P3-1 Retire mainA–D per identity: drain-verify → final wrap receipt → tombstone marker in the
      roster row → `assignee:` linter refuses new messages to retired ids → cursors archived. NOT
      "re-usable slots" (C24/C28 class).
- [x] P3-2 Shrink `tmux_adapter.py` to the two interactive endpoints (machine side); worker panes
      remain human-only. Delete worker-side nudge/doorbell/heartbeat/glyph machinery.
- [x] P3-3 `fleet_watch`: drop pane heuristics; keep hardware compute-idle (rocm-smi + region
      claims); add queue-aging alarm — rows refused by any gate count as AGING; every refusal class
      has an owner and emits once on state change with a routed fix task.
- [x] P3-4 Swap the fleet-gate predicate for the ephemeral pool: runner-liveness + "READY>0 ∧
      capacity free ∧ no spawn attempt in N ticks" as the anomaly condition (zero live workers is
      the NORMAL idle state after this phase).
- [x] P3-5 D4/D4b compute mechanization: compute policy file (priorities, windows, reservations;
      console-edited, edits logged as typed rows) + daemon grant check (region-free ∧ policy-allows)
      + aged-request alarm. All consumers (AutoKernel, AutoPilot, inference, workers) request via the
      same bus path. Amend BUS_PROTOCOL rule 11 accordingly (this is a protocol edit — lands with
      operator ack under D9).
- [x] P3-6 First choreography recipe: the operator's CPU-pause → GPU-load → run ∥ resume example as
      a typed, receipt-gated recipe (drain@boundary receipt → load receipt → start + resume);
      approved at the coordination level, stepped through by the daemon.
- [x] P3-7 Disposition the `auditor` roster identity: once P2-7 headless audits prove out through
      the pilot, retire the interactive auditor row by the same P3-1 procedure (its worktree follows
      the lane-retirement path; its `.orphan` backup was handled in P0-8). The reviewer function
      lives on as per-packet headless invocations.

## Open defect — the pool cannot reach its own concurrency bound

- [x] **PD-1 — `max_concurrent_workers: 4` is unreachable through the daemon.**
      Surfaced by the P3-4 rework 2026-08-16 and confirmed independently.
      `compute_advice` skips any agent already in `busy_owners`, and `busy_owners`
      is keyed on the queue row's `owner`. The entire pool is ONE roster identity
      (`workerpool`), so the first row assigned to it makes the whole pool "busy"
      and no second row is picked until that row clears. The pool therefore
      serializes at ONE row at a time, whatever `max_concurrent_workers` says.
      The pilot reached three concurrent workers only because they were dispatched
      BY HAND with `--pilot-override`, bypassing the picker — so the measured
      throughput does not demonstrate the automatic path.
      Deliberately NOT alarmed on: the condition is continuously true, so an alarm
      would be permanently on, which is the exact failure P3-4 exists to end. It is
      visible in every tick's `fleet-health` advisory via `capacity_free` /
      `in_flight` / `dispatchable`.
      Fix shapes, none chosen yet: per-lane roster identities (`workerpool-lane0..3`);
      or make `busy_owners` count in-flight rows per owner against a declared cap
      rather than treating owner-present as owner-busy; or let the runner itself pull
      the next eligible row rather than waiting to be assigned one.
      D1's bound is honest as a CEILING — nothing exceeds 4 — but it is not yet
      achievable, and the >40% duty-cycle target assumes it is.

## Pulled by need (NOT scheduled — do not start without a measured consumer)

- [ ] PN-1 Liveness / escalation classifiers — only if interactive-session volume returns.
      Shadow-first beside the existing predicate; fixtures re-labeled from primary artifacts
      (`label_provenance`); promotion metric = precision WITH a recall floor (silence must not score).
- [ ] PN-2 Wrap-up generation from bus records — after the completion-report format stabilizes
      (RTG-51 holds the policy).
- [ ] PN-3 Eval CI runner — when the first classifier promotion needs it (fixtures exist from P0-9).

## Phase 4 — Role shrink (week 2; falls out of Phases 1–3, no new build)

- [ ] P4-1 Gate check over 7 days: zero operator delivery interventions (steering by choice is
      fine); duty-cycle target sustained; no MUST-ACT bus item aging past SLA while the console is
      closed ≥12h/day; critical alarms still reaching the operator with it closed.

## Trust-boundary follow-ups (research-intake 2026-09-07)

- [ ] **P5-1 Trust-boundary analysis of the coordination-plane hook surface**, with a specific
      newly-found item: PostToolUse `hookSpecificOutput.classifierContext` — the classifier may weigh
      a user statement relayed here as user intent (it can satisfy a consent bar a user turn would
      satisfy, never a hard boundary). **Declare it out of bounds for any coordination-plane hook and
      say so in the design.** This is a concrete write path into a main's CONSENT state available to
      any hook script. `intake-1325#05`. Zero compute.
      **Scope note**: this row covers the handoff/design half only. The corresponding
      `agents/shared/INVARIANTS.md` text (invariants 1 and 4) is a **human-amendment-only** path
      (`coordination/session-bus/human_only_paths.yaml`, enforced by
      `scripts/hooks/check_trust_boundary_edit.sh` + the `.sha256` pin) and is filed here as an
      **operator token-request**, never an agent edit.
- [ ] **P5-2 The NL-only rule lands in `coordination/evals/examples/` beside C23, NOT in
      `BUS_PROTOCOL`.** This file's standing constraint is verbatim in force: *"prose-rule moratorium
      — from Phase 0 onward, a new incident appends a labeled example to the eval fixtures, never a
      new rule/conjunct to BUS_PROTOCOL or agent files"*, and P0-9 (which declared it) is ticked
      above. A new BUS_PROTOCOL rule would violate the moratorium this file declared, so the rule
      ships as a labeled fixture example instead. `intake-1325#03`. Zero compute.
- [ ] **P5-3 Per-turn PURPOSE LABEL at write time** — add a purpose label to bus rows, delegated-task
      envelopes and orchestrator turn telemetry, so the Eq.-2 split (system / replayed history / tool
      schemas / retrieval / coordination) becomes computable. **Do not attempt post-hoc
      classification of transcripts**: a 32-author team with full trace-shim control published no
      share number because their meter recorded totals, not purposes. Lands beside OBS-11's channel
      work in [`session-bus-thin-dispatcher.md`](coordination-and-churn-pipeline.md) — it is the same
      write-side surface — and is cross-referenced from
      [`delegation-context-preassembly.md`](context-and-token-economy.md#track-delegation-context-preassembly) (DCP-9b depends on it;
      blocks the coordination-share half). `intake-1333#01`. Zero compute.

## Metrics (targets) and kill criteria

- Compute duty cycle on unattended nights: 8–9% baseline → **>40%** within two weeks of Phase 3.
- Operator delivery interventions: ~daily → **0**.
- Coordination self-repair share: ~50% → **<10%**, computed by commit-path classification over
  `scripts/coordination/**` (D9) — never self-reported.
- Alarm fidelity: every drill alarm arrives; **zero** alarms on well-run nights.
- **Kill criteria**: pilot breaches the D1 ceiling, OR audit quality drops — defined as the operator
  spot-review overturning ≥2 of the 3 reviewed pilot rows (pilot) or the operator-vs-auditor verdict
  disagreement rate exceeding 20% over any 7-day window (post-pilot) ⇒ halt, reassess. Any
  single-writer or trust-boundary violation by the runner ⇒ immediate revocation of its authority.
  **Meta-kill**: any phase exceeding 2× its estimate stops the plan — this restructure must never
  become the next 50%-self-repair sinkhole.

## Explicitly not built

No general workflow engine; no new message kinds beyond the `workerpool` endpoint; no classifier for
any surface Phase 3 deletes; no policy-DSL for exotic leases (recipes are data); no autonomous merges
to the loop plane; no re-litigation of ratified invariants; the four AUD-16 items stay un-mechanized.

## Relationship to existing handoffs

- **RTG-48** `coordinator-role-failure-modes-and-refactor.md`: the failure evidence and R-/AUD-
  series this plan answers. Stays open as the ledger; its open R-items are superseded where this
  plan's phases cover them — reconcile at Phase 1 (P1-4) and note supersessions there, in that file.
- **RTG-34** `session-bus-thin-dispatcher.md`: the C-series delivery-plane ledger. Phase 3 deletes
  most of its remaining open surface for workers; reconcile its open C/DP/OBS/FW rows at P3-2/P3-3.
- **RTG-49** `fleet-fanout-measurement.md`: satisfied for the pool tier by `subagents_spawned` in
  the completion report (P2-1); interactive-session measurement stays with RTG-49.


---

## Implementation record — 2026-08-16

**Landed:** Phase 0 complete (10/10). Phase 2 complete and piloted. Phase 3 complete except
P3-4, which is a reviewed proposal awaiting D9 ack. Phase 1's unprotected surfaces landed;
its human-only half is staged. 20 commits.

**The pilot ran for real.** Four workers, `claude -p` harness, visible panes, three
concurrent. **4 of 4 rows passed** with schema-valid reports:

| row | outcome | tokens | subagents | denials |
|---|---|---|---|---|
| pilot-01 delegation-matrix dangling refs | pass | 41,000 | 0 | 1 |
| pilot-02 FETCH_HEAD regression test | pass | 62,000 | 0 | 0 |
| pilot-03 document the pool in agents/README | pass | 118,000 | 2 | 0 |
| pilot-04 worker-pool operator runbook | pass | 205,000 | 3 | 0 |

Every batch inside the D1 ceiling (250k; max observed 205k). **Five subagents fanned out and
counted** — the multiplier had no detector but the operator's word until today (RTG-49/F-15).
Three of four promoted to main through `promote_lane`; pilot-02 is D9-gated because its test
lands under `scripts/coordination/**`.

Two rows the pool REFUSED to run matter as much as the four it ran: both parked on
`premise-unknown` rather than guessing.

**Deviations from the plan text, and why:**
- P2-1's queue-state collapse to 5 states was NOT done. The runner writes only its own outbox,
  never `queue.jsonl`, and `parked_reason`/`salvage_ref` ride in message payloads that already
  validate — so the collapse bought nothing and would have broken the daemon's
  ASSIGNED/CLAIMED/INFRA_BLOCKED handling.
- P1-6 landed at 134 lines, not ~50. Going further meant deleting contracts rather than citing
  them, which is the failure the phase exists to prevent.
- P3-7 retired the auditor SESSION but deliberately did NOT tombstone the IDENTITY: the
  headless auditor still writes under it, and `role: retired` would make the routing linter
  refuse the P2-7 audit path.

**Still open by design:** PN-1/2/3 (pulled by need — no measured consumer exists yet) and
P4-1 (a 7-day observation; `fleet_metrics.py` is built and running).

**Operator gates:** `artifacts/operator/loop-owned-fleet-operator-package-20260816.md`.

---

## Wrap-up findings, 2026-08-16 (operator cadence)

Discovered while running the operator-invoked `/wrap-up`. Each item is done or filed;
none is an "open item" restated as a question.

- [x] **Four handoffs existed in BOTH `active/` and `completed/`, and `--check` was blind to
  all four.** ✅ 2026-08-16 — `index_state.py --check` now carries a **SPLIT IDENTITY** pass
  that exempts only a deliberate compatibility pointer (a body containing
  `../completed/<name>`). Mutation-verified: reintroducing a duplicate produces exactly one
  error. One duplicate mattered — `fable5-window2-findings-05` had been archived on 2026-08-13
  while it still held a live go/no-go, so the *active* copy is the newer one and the completed
  copy was renamed `-completed-through-2026-08-13.md` rather than the active one deleted.

- [x] **A routine handoff prune rotted 151 wiki links, with every lint pass green.** ✅
  2026-08-16 — `check_missing_crossrefs` runs handoff→wiki and accepts a basename found in
  *either* `active/` or `completed/`, so moving a handoff between them is invisible to it, and
  nothing resolved wiki→repo at all. Added lint pass 7 `wiki_link_targets`
  (`.claude/skills/project-wiki/scripts/lint_wiki.py`), enabled in `wiki.yaml`. Dangling target
  = ERROR, dangling anchor = WARNING. **Five mutations, all correct**: pass runs and is counted
  by the reporter; broken target fires; broken anchor fires; a valid anchor does not; a path
  inside backticks does not. The anchor check failed its own first mutation — the dedup key
  ignored the anchor, so a plain link earlier in the page masked a broken anchor later — and
  the key now includes it.

- [x] **`/workspace/repos/` was empty — the documented symlinks were gone.** ✅ 2026-08-16 —
  18 wiki links resolved only through it. Repaired with the idempotent
  `scripts/clone-repos.sh` (previewed with `DRY_RUN=1` first: pure symlink creation, no
  divergent clone to back up). Inode identity re-verified against `/mnt/raid0/llm/` per
  CLAUDE.md. All 3183 relative wiki links now resolve; before this wrap-up, 151 did not.

- [x] **The two recurrence guards are BUILT, not just filed.** ✅ 2026-08-18 — commit `96ccad1a`
  under operator D9-ack: `REPO-SEQUENCER-STALE` (per-repo abandoned cherry-pick/merge/rebase head,
  2h threshold — the 3-day research-repo wedge shape) and `RETIRED-LANE-UNMERGED` (`git cherry`
  patch-id count per retired identity — the mainD 9-stranded-patches shape). Suite 137→159, 30/30
  pre-existing + 3/3 new mutations caught, real-probe tests against throwaway repos. First live run
  found and led to porting 19 stranded patches (`10ff9bdf`); lane/mainC + lane/mainD worktrees and
  branches then removed by explicit path (D7 pattern), so the guard comes up quiet.
- [ ] **Find out what removed `repos/`.** The likeliest cause is the live `git clean` that
  destroyed `retirements/` earlier today (see P0-7/P3-7 above), which would mean the same
  event cost two things and only one was noticed. Cheap to check against the shell history and
  the reflog; worth knowing, because the repair is idempotent but the *cause* is not fixed.

### OP-11 — `main` cannot push, and the graph is the only thing left unreconciled

> **CLOSED 2026-09-01 — resolved by an ordinary three-way merge (`21cefca5`, on `origin/main`).**
> The blocking premise below had gone STALE and nobody re-measured it: the row and this section
> describe *89-90 ahead / 111 behind with 103 files changed on both sides*, which is what made
> option (a)'s `-s ours` tempting and option (b)'s ~78 conflicts forbidding. At resolution time the
> real divergence was **42 ahead / 30 behind with FOUR both-sides files** — the 2026-08-30
> reconciliation had already collapsed it. Option (b), the one rejected as too costly, took two
> conflicts and no hand-picking: both were disjoint appends resolved by keeping both sides. No
> `-s ours`, no force-push, nothing discarded.
>
> The one real hazard was not in the options table at all: the operator queue had a **duplicate-ID
> collision** — the autokernel lane and this session each minted OP-30 and OP-31 while `main` was
> diverged. Origin's kept their numbers; ours became OP-32/OP-33 with references updated. Two
> *deliberate* deletions also had to be preserved against the merge's instinct to resurrect them
> (OP-8, GLM-5.2 KILL; OP-28, resolved by the autokernel lane).
>
> **Standing lesson: a blocker row is a measurement with a timestamp, not a standing fact.** This
> one was carried for 16 days and re-reported in four consecutive wrap-ups after it had ceased to
> be true. Re-measure a blocker before re-reporting it.


`main` is 89 ahead / 111 behind `origin/main`, so `git push` will be rejected. **Never
force-push it.** The content, however, is reconciled: measured 2026-08-16, **no file on
`origin/main` is absent locally** (`git diff --name-status HEAD origin/main` yields zero `A`
entries), the research plane is a strict superset (1150 local intake ids vs 1130 on origin,
**zero** missing), and the residual per-file deltas were forward-ported individually.

What is left is a *graph* problem, not a content problem, and recording it as a merge touches
`scripts/coordination/**` — so **D9 gates it**. Options:

| | Option | Cost | Risk |
|---|---|---|---|
| **a** | `git merge -s ours origin/main`, then push | one commit | Records origin as a parent while keeping our tree. Correct **only because** the per-file port already did the semantic merge with evidence. Nothing becomes unreachable: `refs/heads/lane/auditor` names the same tip on origin. |
| b | Full `git merge origin/main` with manual resolution | ~78 conflicted files | Redoes by hand the work already done per-file, and invites a wrong pick on a loop-plane file that was deliberately rewritten. |
| c | Leave diverged; push to a review branch | zero | `main` stays unpushable indefinitely, and every later session inherits the divergence. |

**~~Recommendation: (a)~~ — WITHDRAWN 2026-08-16, same day, and the reason is the useful part.**

The evidence I gave for (a) was `git diff --name-status HEAD origin/main` yielding zero `A`
entries, which I reported as "the content is reconciled". **That measures file PRESENCE, not
content equality, and I stated the second having tested only the first.** The parallel session
(`stage-3-action-plan`) measured the thing I should have:

| against the merge base | files |
|---|---|
| `origin/main` changed | 104 |
| local `main` changed | 269 |
| **changed on BOTH sides** | **103** |
| origin-only | 1 |

`-s ours` keeps local content for all 103 and discards origin's half of each **with no conflict
raised and nothing in the resulting diff to review**. That is not a graph-only operation; it is a
silent 103-file revert of the other session's work. Option (a) is wrong and is withdrawn.

**Resolution: option (b), and it is IN FLIGHT and owned by the other session** — a real per-file
three-way merge in an isolated detached worktree (`/mnt/raid0/llm/tmp/merge-20260816`, our live
tree untouched), 36 conflicts, fanned out over 4 subagents on disjoint sets. Policy: union by
default; never drop a rule, guard, test or task; **retractions win over what they retract**;
genuine contradictions preserved and reported, never silently picked.

**RESOLVED 2026-08-23 — the reconciliation landed and this wrap-up completes it.** The D9-acked
landing commit is `4ae0c049` (on both `origin/main` and local `main`), with the per-file
three-way merge commits (`80cd4e66`, `9cff0ff7`) as ancestors. This session's wrap-up
promotion carries the remaining lane work onto `main`; the stale master-index OP-11 row was
removed at the operator's directive. No force-push was used at any point.

Nothing is at risk while it runs. Every local commit is on origin — verified with
`git rev-list <branch> --not --remotes=origin` across all local branches; the only
origin-unreachable commit was `4ad13cb2`, now parked at
`origin/backup/coordinator-agent-20260816T1952Z/main`. All of today's earlier work was already
inside `origin/backup/20260816T1900Z/main-research-intake`.

**The instructive case, for whoever reviews the merged tree.** Local now carries the decode-vs-depth
retraction (added by the forward-port at `gpu-candidates-surface-qwen38-update.md:58-61`), but it
sits as a note *beneath* table rows that still read `✅ **37.15 t/s** … 13.61 @32k` and
`**MTP HURTS at depth**`. Origin rewrote those rows instead. **Origin is right**, and a naive union
is the worst of the three outcomes — it would preserve both the retracted cells and their
retraction, and a `✅ measured` cell gets quoted downstream without the paragraph that withdraws it.

## Bus-triage findings, 2026-08-16 — the 51-message backlog, read not swept

All 51 routed messages (2026-07-29 → 2026-08-16) were dispositioned individually against the
repo by four parallel readers, each disposition backed by a commit / file:line / handoff row.
Zero were bulk-acked. What survived as live work:

- [x] **BUS_ROOT derived from `__file__` in 3 modules — writes silently lost in every lane
  worktree.** ✅ 2026-08-16 — flagged by `auditor` on 2026-08-12; one of three named files was
  fixed then, and `tmux_adapter.py`'s instance SURVIVED THE P3-2 REWRITE of that file because
  only per-file assertions guarded the invariant. Fixed `tmux_adapter.py`, `seed_queue.py`, and
  — found by the new guard, not by any audit — `alarm_channel.py`, written 2026-08-16 *after*
  the audit, proof that per-file assertions can never cover the next file. All three now use
  `session_bus.get_bus_root()`. New AST sweep in `tests/test_bus_root_resolution.py` fails on
  ANY `scripts/coordination/*.py` module deriving a bus root from `__file__`; mutation-verified
  three ways (each fix reverted individually → sweep fires; restored → 9/9 green).
- [x] **Four pilot audit packets were never audited — the invoke wiring landed 12 minutes too
  late.** ✅ 2026-08-16 — packets emitted 10:17–10:46Z, `_invoke_headless_audit` (P2-7's other
  half) landed 10:58Z. All four run retroactively; verdicts on the bus under `auditor`. Two
  rationales report mutation-probe FAILs that are benign over-matches: the probe expects the
  diff to touch every file the task TEXT mentions, and both pilots' prose named files outside
  their deliverable (pilot-03 → RTG-52 itself, pilot-04 → `worker_runner.py`).
- [x] **D9 hook: fire on the COMMIT PATHSPEC, not the command string.** ✅ 2026-08-18 (`a1294552`,
  under D9-ack). Root cause was narrower and worse than "parses the command string": it took every
  token after the FIRST `--` to **end-of-string**, so the pathspec ran through the `;` and swallowed
  the next command's argv — and the `--` it keyed on need not have belonged to the commit at all.
  Fixed by not deciding: the hook now asks **git** what the commit records — `git diff --cached`
  for a plain commit, `git diff HEAD -- <pathspec>` for a pathspec commit, with the pathspec scoped
  to the commit's own shell segment and handed to git verbatim. Coverage is sharpened, not traded:
  it now expresses that a pathspec commit does **not** record the index, so a staged guarded file is
  correctly irrelevant to a commit naming only a doc. 11 regression tests against a real temp git
  repo (`scripts/hooks/tests/test_d9_loop_plane.py`); the original had none. Every false-positive
  case is paired with one proving the real refusal still fires.
- [x] **The same defect existed in three more guards; swept and fixed.** ✅ 2026-08-18. All 13
  registered PreToolUse hooks plus the precommit and context hooks were audited for
  match-on-text-not-effect. `check_commit_hygiene.py` (`cdbbd761`): `_SEP` split on newlines, so
  every LINE of a heredoc body became a command — a Python heredoc whose *source* contained a commit
  was blocked for a stale fetch. `check_live_holder_interference.sh` (`5202e98e`): matched its write
  regex against the raw command, so a doc heredoc and a `grep` both matched a drop_caches write —
  **latent**, reachable only under a held region, i.e. only mid-bench. Both fixed with paired
  enforcement tests. Already-correct: `pytest_worker_scan` (C21 fixed this first, 2026-07-29) and the
  two scanners importing from it; the `file_path`-only guards; the precommit and context hooks.
- [x] **`positional_and_flags()` misreads shell redirection tokens as pathspecs — strip `>` / `>>` / `2>&1` /
  `|` before computing positionals**, so `git commit --file=<msg> 2>&1 | tail` stops being blocked as a
  "pathspec commit" (`positionals[0] == "2>&1"`); `git commit -F -` / `-F <file>` is refused for the same
  reason while `--file=<path>` passes, it is the same family as the quoted-`-m` false positive its own
  docstring documents, it cost four agents a retry, and a guard that fires spuriously is how a real block
  eventually gets bypassed (`epyc-orchestrator` `scripts/hooks/check_commit_hygiene.py:282-310`; raised
  independently by 7 agents) (found 2026-09-14, noninf sweep).
  - MAIN 2026-10-07 source reconciliation: the current shared parser already strips redirections before segmentation and consumes `-F` values. Existing paired controls retained; no new execution or native pass claimed. [Review](../../artifacts/ni08/rtg52-hygiene-source-20261007/README.md).
  - *+1 2026-09-23 (intake-jev-exl3):* `git commit -q -F - <<'EOF'` refused as a pathspec commit; `--file=<path>` passed.
- [x] **The hygiene hook's documented override is unreachable from an agent — make the refusal say how the operator applies it.**
  `check_commit_hygiene.py:504` reads `EPYC_ALLOW_COMMIT_HYGIENE_BYPASS` from the hook's own environment, so the inline form
  the refusal text suggests (`EPYC_ALLOW_COMMIT_HYGIENE_BYPASS=1 git restore …`) never reaches it — the hook refused it twice on
  2026-09-23 even after the operator typed that exact command, because the operator's message arrived as chat text rather
  than a `!` shell line. Either name the operator path in the refusal ("the operator runs it with a `!` prompt line, or sets it
  in the session env") or accept a one-shot operator token. The present text invites an agent to try, fail, and then be
  tempted to route around the guard with an equivalent write (found 2026-09-23, research-lane cleanup).
  - MAIN 2026-10-07 accepts the two-file refusal-text source change and meaningful existing-script assertions. Enforcement and environment lookup unchanged. [Review](../../artifacts/ni08/rtg52-hygiene-source-20261007/README.md).
- [x] **One shared implementation instead of four.** ✅ 2026-08-18 (`2f5a0c63`). `shell_scan.py` now
  owns `SEPARATORS`/`strip_quoted`/`strip_heredocs`/`strip_comments`/`segments()`; four scanners
  import it. −73/+17, `strip_comments` de-triplicated (one copy substituted `""` where the others
  used `" "`, which could fuse tokens). Verified a **pure refactor**: a 22-command corpus through
  three verdict functions before and after, byte-identical. The module's docstring carries the
  incident record — the same defect, four times, dated — so a fifth author reads why before writing
  a fifth copy.
- [x] **`test_hook_worktree_resolution.py` has 2 failing tests** ✅ 2026-08-18 (`25726a78`) — both were the TEST, not the cascade, and neither was about resolution: the tier-1 stub fixture hard-coded two hook names while `pre-commit.extras` had chained a third through the same variable, and the sparse fixture rmtree-d the whole `scripts/hooks` tree, which trips the later-added observer census on registry rows pointing into it. Fixed by DISCOVERING the chain rather than naming it, and by simulating sparseness the way tier 2 actually detects it (remove the one probe file). Its sibling was passing for the WRONG REASON — asserting `rc != 0` and getting non-zero from the census, not from resolution. Also removed a `git worktree prune` from the fixture teardown: the command that destroyed all five lanes on 2026-08-12 had no business in a test. 8 passed, was 2 failed / 6 passed. ORIGINAL NOTE: (`test_env_override_wins_over_everything`,
  `test_sparse_worktree_fallback_allows_a_clean_commit_too`). Confirmed **pre-existing** on 2026-08-18
  by stashing the guard-sweep work and re-running: identical 2 failed / 6 passed. Untouched by that
  sweep and filed here rather than left in prose. Not blocked on anything.
- [x] **The probe over-match above is itself a defect worth one line of code** ✅ 2026-10-31 — ROOT `752a7a6ec2a121b5f5492ee2e218b71bfe57e756`; [43 tests plus 12 subtests and 3 runner tests](../../artifacts/compute/codex3-loop-probe-20261031/README.md). [no-belief: software fix and regression tests only]: the mutation
  probe should resolve expected-touched files from the row's stated deliverable, not from every
  path-shaped token in the task text — two of four pilot audits FAIL-noised on it.
- [x] **`monitor:file` service identities are structurally invisible to the fleet-health plane.**
  ✅ 2026-08-23 (RTG-52 D3, `5412e86b`, D9-ack) — daemon re-invoke sweep implemented:
  `resolve_stuck_agents`'s monitor:file branch runs `_monitor_file_reinvoke_sweep`;
  unanswered `action_required` packets older than `_MONITOR_FILE_REINVOKE_INTERVAL_S` (600s)
  are re-invoked — a `stuck-reinvoke` advisory carries packet id + role_policy/invocation
  path with an explicit `re-invoke` marker, and `auditor` packets route through the SAME
  headless-audit invocation the runner uses (`headless_audit.py audit --packet --emit`), so a
  missed audit packet is re-audited, not merely re-flagged. Guards: once per interval per
  packet (`stuck_state.json` per-agent dedupe), never a packet answered by corr_id
  disposition OR by an existing verdict naming the same task_ids/commit_range (the
  pilot-verdict shape carries no corr_id), missing-cursor identities read from zero (never
  fail open), every re-invoke logged. 7 tests
  (`tests/coordination/test_monitor_file_reinvoke.py`); M4 + routing-intent suites green.
  The sweep ships in code; the live daemon must be restarted to run it (daemon boundary —
  operator follow-up).
- [x] ✅ 2026-10-31 **Screener paraphrase defect: a pool dispatch screened a worker against hand-written `--row-text` instead of the row's verbatim text.** Evidence: ROOT `3e86fa5eccb6abcb0822f65cd45b29c9d22968fb`; `scripts/coordination/tests/test_worker_row_text_identity.py`, `test_headless_audit_deliverables.py` and `test_worker_runner.py` in that directory (81 pass). [no-belief: dispatch source and regression controls; no daemon reload or retrospective re-screening]
  Full queued text is passed without truncation; both CLI and assignment-file dispatches refuse resolved-ID paraphrases. A file-only reader without a queue namespace preserves its offline contract. Original incident: CJ-1c parked `unknown` on a 241-char
  paraphrase while the real 452-char row text matches its checkbox verbatim. "The task TEXT is
  the identity" — the dispatch path must pass the row text through byte-for-byte; forbid
  free-hand `--row-text` when the row resolves. (5/5 pilot rows screened `unknown`; at least
  this one is a screening artifact, not a premise problem.)
- [x] **Relay ledger: 296 flagged rows, never reconciled.** ✅ 2026-08-23 (RTG-52 D2,
  `37b6a7e0`, D9-ack) — `relay_state.json` carries 296
  flagged entries (oldest 2026-07-27, `handler:intake_proposals`). The 2026-08-12 "reconcile
  before restart" window is long past and this triage answered the re-presented backlog, but
  the flagged list itself has never been adjudicated: nothing distinguishes "handled by a
  handler" from "dropped". One pass over the 296 with the handler ledgers, then either clear
  the list or file what it proves lost. (chunk-2 S1; two of 13 sampled messages in this very
  triage carried `NOT-IN-INBOX` markers — the drop mechanism is corroborated, not hypothetical.)
  **Adjudicated 2026-08-23**: `scripts/coordination/relay_ledger_adjudicate.py` classified the
  live 298-entry ledger against the bus files — 244 handled (follow-up disposition), 15
  delivered-not-drained, 3 schema-invalid (source rows now validate — flag premise resolved),
  36 unknown, 0 dropped (nothing proven lost; no defect row needed). `--apply-clear` on the
  live ledger: **247 cleared, 51 stay**; original backed up to
  `coordination/session-bus/relay_state.json.bak-2026-08-23`, `delivered` map preserved.
  Machine report: `data/relay_ledger_adjudication_2026-08-23.json`; 10 tests incl. the
  inbox-removal mutation (classification flips to dropped).
- [x] **The E8 wipe now has its incident entry.** ✅ 2026-08-16 —
  `INC-20260816-git-clean-shared-clone` in `docs/reference/agent-config/INCIDENT_LOG.md`,
  folding both dated events (08-12 worktree wipe, 08-16 retirements/watermark/repos/ loss) into
  one signature: `git clean` removes exactly the untracked-but-load-bearing state no commit
  protects, and the cost surfaces days later as unrelated-looking breakage.
- [x] **"Backfill landed but off" — REFUTED during triage.** ✅ 2026-08-16 — chunk-4 read
  `coordination/backfill/` (docs only) and concluded the runner never landed; in fact
  `5af987ef` shipped `hardware_backfill.py` (777 lines) + supervisor + 418-line test, the
  `hardware-backfill` roster row exists (`config.yaml:132`), and the supervisor process is
  running. Recorded so the claim does not resurface.

**E8 reseed gate (chunk-4 #4) — folded into OP-19** rather than filed twice: the gate text in
`CURRENT-CAMPAIGN.md:103,106` blocks every stack change on an E8-form reseed that can no longer
be satisfied (era advanced to E9, source evidence destroyed), and the file contains zero
occurrences of "E9". OP-19's ruling should answer BOTH the B9/B10 disposition and the gate's
restatement against E9 — answering the narrow question alone leaves the unsatisfiable gate
binding. Master-index OP-19 row amended to say so.
*Note 2026-09-16: OP-19 was ruled in [`ruling_op19_e8_chain_20260827.json`](../../artifacts/operator/ruling_op19_e8_chain_20260827.json) (root `1ee8bd7c`). The ruling retires the E8 chain and re-anchors the reseed gate to the current eras; the gate binds only at promotion.*

## Newly executable bounded source proposal

- [ ] **RTG52-D9-SOURCE — integrate reviewed target-selection and exact assignment-stdin source controls after the exact D9 acknowledgement.** Private tip `33df263031234d78272baafd096ef1dee5c946fb`, full six-file footprint: `headless_audit.py`, `session_bus_coordinator.py`, `worker_runner.py`, and coordination tests `test_fleet_gate.py`, `test_headless_audit.py`, `test_worker_runner.py`. Strict supported grammar abstains on ambiguity/negation; task text is sent as bounded exact UTF-8 JSON stdin without clipping. Fake captured-child cleanup is bounded and refuses unconfirmed exit. Native proof is VB-RTG52-D9-CONFORMANCE, not semantic/assignment correctness authority. Protected merge remains operator-gated by D9; no host activation or dispatch. Previously accepted hygiene ancestor is not new RTG52 work.

## Track: fleet-fanout-measurement
<!-- gate: RTG-34, RTG-48 -->

> Folded from `handoffs/active/fleet-fanout-measurement.md` @ `b1bf3f3f7ade` on 2026-11-02 (BRF-T1-F19, route 1a, operator D1/D5; retired row RTG-49 → RTG-52). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Fleet Fan-Out Measurement — per-subagent timing collector + failure grading

**Status**: active — FM-1 (2026-08-23), FM-5 and FM-6 (2026-09-07) landed; FM-2/FM-3/FM-4 open. ✅ 2026-09-15
**Created**: 2026-08-13 (via `/research-intake` Stage 3, operator-approved plan; source round intake-1105…intake-1127, PARL/Kimi-agent-swarm sweep)
**Parent index**: [routing-and-optimization-index.md](routing-and-optimization-index.md)
**Categories**: swarm_techniques, agent_architecture, benchmark_methodology, autonomous_research

#### Objective

Our fan-out doctrine (`agents/shared/OPERATING_CONSTRAINTS.md` → *Parallel Subagent Fan-Out*) mandates
3–5 concurrent subagents unconditionally, with no completion feedback and no way to distinguish a main
that actually fanned out from one that worked serially and reported otherwise. The open item at
`session-bus-thin-dispatcher.md:2685` names this gap directly: *"nothing on this plane distinguishes a
main that dispatched five concurrent subagents from one that did the same work on its own thread — so
the only detector is the operator saying so, which is how it ran unchallenged to 1,070 open backlog
items."* `coordinator-role-failure-modes-and-refactor.md` F-15's `Recur: 0` currently rests on that same
self-report evidence.

This stub owns the measurement side: turn the assertion into a number, using data already on disk.

#### Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-1106 | Kimi K2.5: Visual Agentic Intelligence (arxiv:2602.02276) | high | worth_investigating — names "serial collapse", supplies no instrumentation |
| intake-1111#record | OrchBench (arxiv:2607.25656) | high | dive-overturned — requires per-node durations as INPUT, but Appendix D-I's real-side metric definitions (declared/started/completed agents, parallel utilization, workflow depth) are a ready spec |
| intake-1109 | Single-Agent vs MAS at Equal Token Budgets (arxiv:2604.02460) | high | dive-verified — Appendix B four-bucket breadth-vs-synthesis diagnostic |
| intake-1127 | AdaMAST (arxiv:2607.16387) | high | dive-verified, adopt_component — Apache-2.0 trace grader, no success/failure oracle required |
| intake-1110#00 | MAST (arxiv:2503.13657) | medium | dive-overturned — 14-mode taxonomy, FC1/FC3 transfer to our topology, FC2 largely does not |

Related existing work (do NOT duplicate):
- [`session-bus-thin-dispatcher.md`](coordination-and-churn-pipeline.md) — owns the C36 substrate this collector builds on: per-backend transcript mechanics (Codex `thread_source`, Claude subagents in-process via `claude agents --json`), and the standing rule that **CPU delta is an invalid proxy** for subagent activity.
- [`coordinator-role-failure-modes-and-refactor.md`](coordinator-role-failure-modes-and-refactor.md) — F-15 (fan-out doctrine), R-17/R-23 (thread-attribution premise), the F-series failure ledger this stub's grading output would cross-walk against.
- [`repl-turn-efficiency.md`](harness-program.md#track-repl-turn-efficiency) — S4 Omega A/B, the metric this collector's data would feed.

#### Corpus, verified on disk 2026-08-13

- **Claude Code**: ~1,843 JSONL under `~/.claude/projects/-workspace/<session>/` (1,611 in `subagents/`, 232 session files). Fields: `agentId`, `parentUuid`, `isSidechain`, `uuid`, `timestamp`, `sessionId`, `promptId`, `message`, `toolUseResult`.
- **Codex**: ~4,422 rollout files under `~/.codex/sessions/YYYY/MM/DD/`. First record `session_meta` carries `payload.source.subagent.thread_spawn.{parent_thread_id, depth, agent_role}`; every record timestamped.
- `scripts/coordination/tmux_adapter.py:1376-1441` already opens both formats and parses the subagent structure — currently only for a boolean liveness check, discarding the timing.

#### Tasks

- [x] **FM-1 — Per-subagent timing collector.** ✅ 2026-08-23 — `scripts/coordination/fanout_timing.py`
  (collect-claude / collect-codex / merge, schema `fanout_timing.v1`), tests in
  `tests/coordination/test_fanout_timing.py` (14 passed), corpus run in
  `data/fanout_timing/` (2428 workflows, 4727 subagents; 52 workflows with >=2 overlapping
  subagents holding 3847 subagents; mean depth 1.38, max 4; 54 workflows joined to queue.jsonl).
  Extract per-subagent start/finish timestamps from Claude Code and Codex transcripts into a durable record. Spec: OrchBench Appendix D-I real-side metric
  definitions — Declared/Started/Completed Agents, Parallel Utilization (`Σ subagent active time ÷ (max
  overlapping subagents × total workflow span)`), Workflow Depth. Do NOT infer edges by keyword-matching
  between subagent outputs (OrchBench's own weak proxy for this) — our Task/SendMessage records carry
  real parent→child edges; use those. Output should be joinable against `queue.jsonl` task IDs for a
  fleet-level view.
- [x] **FM-5 — Per-subagent OUTCOME accounting (intake-1304; 2026-09-07).** ✅ 2026-09-07 — see the RESULT block below the FM-6 row; read the bounds before quoting any number. Extend the FM-1
  collector with an outcome bucket per subagent — `produced-and-used` / `produced-and-discarded` /
  `no-output` / `blocked` / `aborted` — and a token total per bucket, over the existing
  `data/fanout_timing/` corpus (2428 workflows, 4727 subagents). **Target metric: the share of
  fan-out tokens spent on subagents whose work was never used.** Comparator, from the only published
  per-outcome accounting of a large agent swarm: 80.2% of tokens went to non-merged runs and 51.6%
  to Aborted alone, and that paper's own remediation list projects a 3–10× cost reduction from
  fixing orchestration without better models. **This is a strictly WEAKER oracle than FM-4 and does
  NOT block on it** — "was the output used" is derivable from the parent's subsequent tool calls and
  git diff, and needs no task-success verdict. That is the whole reason to do it first.
- [x] **FM-6 — Reconnection requirement (intake-1299#05; 2026-09-07).** ✅ 2026-09-07 — orphan rate 35.0%; declared width 1,187 -> measured 928 (-21.8%). A fan-out record counts only if
  each subagent's output is linked to a backlog row or an artifact path; unlinked output is reported
  as `orphan` and excluded from the measured fan-out width. Adapted from Prove2Me's rule that work
  which does not reconnect to the mission decomposition earns no credit at all. Note the direct
  bearing on this handoff's own premise: an orphan-blind width count cannot distinguish a main that
  dispatched five subagents usefully from one that dispatched five and used none.

##### FM-5 / FM-6 RESULT — 2026-09-07, and the bounds are part of the result

`scripts/coordination/fanout_timing.py` at schema `fanout_timing.v2` (a strict superset of v1;
v1 rows are counted as `schema_v1_no_outcome` and never folded into a bucket). Tests:
`tests/coordination/test_fanout_timing.py`, 14 -> 58, every positive paired with a mutation that
removes exactly the signal under test. Corpus: `data/fanout_timing/*.v2.jsonl` +
`outcome-report.v2.json`, **4,278 subagents over 14,004 workflows**.

| bucket | n | share of known | share of tokens |
|---|---|---|---|
| produced-and-used | 2,265 | 60.0% | 13.5% |
| produced-and-discarded | 1,281 | 33.9% | 79.7% |
| no-output | 122 | 3.2% | ~0% |
| aborted | 109 | 2.9% | 6.8% |
| blocked | 0 | 0.0% | 0.0% |
| *unknown* | *501* | *excluded* | *excluded* |

**HEADLINE — BANDS, NOT POINTS. Revised 2026-09-07 by SC62.** A point estimate here is a
different and stronger claim than the one that was made, so the projection into the belief kernel
(`scripts/vidya/adapters/fanout_outcome.py`) refuses to yield a scalar at all: `.point`, `float()`
and `int()` on the value raise. Over the **3,777 subagents whose outcome is known**:

| quantity | band |
|---|---|
| head-count waste | **40.0% – 95.5%** |
| token waste (`total` basis) | **86.5% – 99.7%** |
| token waste (`new` basis) | **83.8% – 99.6%** |
| blocked share | **>= 0.0%, NO upper bound** |
| unclassifiable | **exactly 501** (census, held out of every denominator) |

**The two ends rest on different EVIDENCE, not different confidence** — this is not a confidence
interval and must never be rendered as one. Low end: 2,265 `produced-and-used`, an upper bound on
usefulness because 2,094 of those verdicts are `parent-reference` substring hits (evidence the
parent *saw* the output, not that it *used* it). High end: 171 `git-landed`, the only proven floor.

**The familiar 86.5% is the LOW END of one band, never the finding.** On the proven-floor reading
the token ceiling is **99.7%**, because those 171 subagents account for just 2.85B of 1,110.7B
tokens. Anything citing a single number off this measurement is citing something we did not measure.

**Why the two units disagree by 46 points, which is itself the finding:** discarded subagents are
the token-heavy ones. Cost does not track head count here, so a width-based cost argument measures
the wrong thing — which is exactly what the ratified discarded-work clause says.

**Bounds you must carry when citing this:**
- **`produced-and-used` is an UPPER bound.** 2,094 of its 2,265 verdicts rest on `parent-reference`
  (a substring hit in a later parent record), which over-fires for a subagent citing a hot path.
  The **strict floor of PROVEN reuse is `git-landed` = 171 = 4.5% of known subagents.** So
  head-count waste is the band **40.0% – 95.5%**, and the token bands are above.
- **`blocked` = 0 is a floor, not a finding.** Neither transcript format carries a blocked marker;
  only a narrow API-error tail is detectable. A subagent that reported a blocker in prose is
  sitting in `produced-and-discarded`.
- **Token totals are provider-cumulative and skewed** (Codex p50 1.27 M, p90 1.68 B): the token
  share is a statement about a handful of very long threads. The head-count figure is not.
- **501 `unknown`** (all Codex, parent rollout exceeded the 512 MB reuse-index cap) are reported
  separately and folded into nothing. They hold 0.1% of tokens.
- **Codex `written_paths` is a lower bound** (only `apply_patch` headers parsed), so the 38.0%
  Codex orphan rate is an upper bound.
- **The corpus is NOT reproducible.** Claude transcripts have been pruned since the v1 snapshot
  (1,546 -> 1,078 subagents) and the Codex corpus grew (2,344 -> 13,942 workflows). The v2 artifacts
  are committed *because* of this: a measurement whose corpus no longer exists is unfalsifiable.

**Comparator, for context only:** the external swarm reported 80.2% of tokens to non-merged runs
and 51.6% to aborted alone. **Our aborted share is 6.8% — an order of magnitude lower — and our
loss is concentrated in DISCARDED, not aborted.** Different failure, different remedy: their fix is
crash-loop repair, ours would be reconnection.

**Do NOT read this wave as an argument to narrow the 3–5 fan-out width.** The evidence points the
other way: in the one study that varied workers-per-task (1/3/5, intake-1305), the 3- and 5-worker
arms beat 1 worker on **both** wall-clock and token cost at matched completion, and the central
coordination tier was only ~11% of compute. The cost driver these sources identify is discarded
work, not width — which is what FM-5 measures.

- [ ] **FM-2 — AdaMAST fixed-catalog grading pilot.** Stage 1 (now): `adamast judge --taxonomy
  adamast/core/mast.json` over a stratified sample of Codex rollouts and Claude transcripts, one LLM
  call per trace, no oracle required — the pipeline is deliberately outcome-blind
  (`outcome_blind_trace()` strips `outcome`/`final_gate_status` before the judge ever sees a trace).
  Two small enablers first: (a) a `base_url` passthrough in `providers.py` (`SUPPORTED_PROVIDERS =
  ("openai","anthropic","google","bedrock")`, client constructed with no kwargs) to point the judge at
  a local endpoint, ~5 lines; (b) a normalizer emitting the 4-field canonical schema
  (`problem_id, task, raw_trajectory, metadata`) from Claude JSONL, carrying `agentId`/`isSidechain`/
  `parentUuid` in `metadata`; Codex is detected natively but `thread_spawn` metadata is silently
  dropped upstream and should be preserved the same way. Stage 2 (after FM-4/oracle work, separately
  scoped): `adamast generate` to induce a fleet-specific taxonomy — the paper's own evidence (induced
  vocabulary κ=0.682 vs a hand-crafted comparator at κ=0.516 on TRAIL, and mean pairwise Jaccard 0.14
  across six domains for independently induced taxonomies) argues an imported 7-framework taxonomy
  should not be expected to fit our traces as well as one induced on them. Do not trust the repo's
  built-in agreement gate (four personas of one model, Fleiss κ, no human) as validation; build a small
  human-graded set if a faithfulness number is ever needed.
- [ ] **FM-3 — Breadth-vs-synthesis diagnostic.** Apply the four-bucket split from intake-1109 Appendix
  B (fan-out-right/single-right, single-right/fan-out-wrong, both-right, both-wrong) to FM-1's output
  once paired serial/fan-out task pairs exist, to answer: does fan-out win by surfacing more candidates,
  or lose at the integration/synthesis step?
- [ ] **FM-4 — Success/failure oracle.** Blocking prerequisite for FM-2 Stage 2 and for any accuracy-side
  A/B. Derive a machine-readable per-session verdict (task exit status, gate result, git outcome) —
  neither corpus carries one today.

- [x] **FM-7 — Delegation accounting over Claude Code journals (zero inference; intake-2535, intake-2541).** Extend `scripts/coordination/fanout_timing.py` with a `delegation_accounting` report: per main session and per subagent, usage by field (input, cache_creation, cache_read, output), subagent model and effort, first-request input tokens (fixed overhead), final-report output tokens, and every Read `toolUseResult.file` (numLines, startLine, totalLines, chars). Frozen sha256 manifest of `~/.claude/projects/-workspace/**/*.jsonl` at a stated cutoff; all sessions in the denominator, unparsable files counted. Decision rule fixed now: A = Σ(chars/4 of main-thread full reads of files >350 lines × requests remaining in that session) ÷ Σ(main-thread input + cache_creation + cache_read tokens); A ≥ 10% in both the pre- and post-2026-10-15 windows fires M1 in Notes, A < 3% in both closes it, otherwise re-measure in 30 days. Acceptance: tests with paired mutations, the report artifact path, the A value per window, the decision line, and a belief tick (extend `scripts/vidya/adapters/fanout_outcome.py` or `[no-belief: <reason>]`). ✅ 2026-10-31 — commit `8a1ca9227`; test `tests/coordination/test_delegation_accounting.py` (34 paired-mutation tests; FM-5/FM-6 `report` byte-identical vs origin/main); artifact `data/fanout_timing/delegation_accounting_report.v1.json` + rows `delegation_accounting.v1.jsonl` over manifest `delegation_manifest.v1.json` (5,829 files, 13.43 GB, cutoff 2026-10-31T13:03:52Z, all sha256-verified, 0 unparsable lines). **A pre-2026-10-15 = 1.57%, post = 0.007% → decision: M1 declined** (both < 3%; compaction-bounded 0.10% / 0.007%; Bash-inclusive proxy 2.28% / 0.80%, also both < 3%). M2 trigger: higher-tier re-dispatch 0.37% of cheap dispatches over the last 30 days (5/1,343; Codex 1/788) → does not fire. Codex covered: A not computable (no structured read event); proxy, overhead, tier spend in the report. [belief: cc]
- [ ] **FM-8 — Declarative project subagent types and a main-thread dispatch audit hook (intake-2540, intake-2537, intake-2538).** Add `.claude/agents/explorer.md` (haiku, effort low, tools Read/Grep/Glob, omitClaudeMd true, maxTurns 8, returns only `path:start-end — reason` lines, max 20), `.claude/agents/runner.md` (sonnet, effort medium, Bash/Read/Grep, keeps CLAUDE.md, returns one block per command: command, exit status, pass/fail counts, key error excerpt) and `.claude/agents/clerk.md` (haiku, effort low, docs/logs/handoff text); add `scripts/hooks/check_agent_dispatch.py` on PreToolUse `Agent|Task`, main thread only (no `agent_id`), WARN mode (exit 0, stderr note, JSONL line to `logs/agent_dispatch_audit.jsonl` with hook sha) for a dispatch with no `model` that is not a project type, and for a `fork` given a cheaper `model`. Acceptance: fixture tests with paired mutations (incl. malformed input allows and logs), `/agents` lists the three types, one live dispatch of each type with its model confirmed in `/tasks`, settings diff reviewed.
- [ ] **FM-9 — Apply the delegation-contract amendment (intake-2535 Stage-3 plan).** **Scope extended by operator 2026-10-31:** once FM-7 verdicts are in, the policy change must also cover Codex worker sessions (agent:2-4), including their sub-delegation and model/effort routing, the Codex delegation contract in `OPERATING_CONSTRAINTS.md` → *Codex Delegation & Long-Horizon Throughput*, and token accounting. FM-7 must therefore also measure Codex session logs where they exist on disk. Apply the approved `agents/README.md` Model Routing diff (subagent types, Haiku-points rule, effort-before-tier escalation, when a cheaper tier pays, four-field brief, per-command and evidence-only return contracts, path:start-end edit input, main+subagent+total accounting); hand the approved `agents/shared/OPERATING_CONSTRAINTS.md` hunk to the operator as one ratify-script command (human-only path). Acceptance: README diff landed, agents_reference_guard and agents_schema_guard pass, `scripts/vidya/cli.py cite-check` exits 0 on the edited files, ratify command delivered and its receipt recorded once the operator runs it.
#### Notes

Corpus counts above supersede any earlier figure of "4,087 Claude transcripts" circulating from the
research-intake round that produced this stub (`intake-1110#record` dive_corrections) — that figure was
overstated ~2.2×.

##### Delegation triggers from the Portal/shunt intake (2026-10-31)

- **M1 — main-thread large-Read redirect.** Fires when FM-7's A ≥ 10% in both windows. Then add a `PreToolUse` `Read` hook gated on missing `agent_id` that blocks full reads (no offset/limit) of files over 350 lines and points the main thread at the `explorer` subagent. Then run a four-arm A/B on a frozen task set from our own repos: raw read, explorer pointers, Spotify-style summary, and goal-conditioned line filter (SWE-Pruner shape). Score task outcome, main/subagent/total tokens and re-read rate. Build cost: about one day for the hook and fixtures, plus the A/B in metered Claude tokens. Closed as declined if A < 3% in both windows. **Declined 2026-10-31 by FM-7** (A = 1.57% / 0.007%).
- **M2 — Opus advisor for cheap-tier subagents** (`advisorModel: opus`; subagents inherit it). Fires when FM-7 shows cheap-tier subagents re-dispatched at a higher tier in ≥ 15% of dispatches over 30 days. First measure the consult rate on 20 dispatches; build only if consults are > 0. Our Opus 5.5 main accepts only Opus 5+ or Fable advisors. **FM-7 2026-10-31: not fired** (0.37% over 30 days).
- **M3 — local-stack read worker.** Fires when M1 fires and the explorer A/B shows pointers at least as accurate as raw reads. Then price serving delegated reads from the local worker via the orchestrator MCP (`harness-selection-and-integration.md` HS-4 P6 exports read_range/grep/code_search there). Real constraints: inference windows on the shared host, and CPU decode latency per call. Build cost: a script wrapper plus an MCP timeout setting (HS-17).
- **FM-8 enforce mode.** Switch the dispatch hook from warn to deny once 14 days of `logs/agent_dispatch_audit.jsonl` show zero false positives on reviewed lines.

## Track: wrap-up-division-of-labor-policy
<!-- gate: RTG-34, RTG-48 -->

> Folded from `handoffs/active/wrap-up-division-of-labor-policy.md` @ `b1bf3f3f7ade` on 2026-11-02 (BRF-T1-F19, route 1a, operator D1/D5; retired row RTG-51 → RTG-52). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Wrap-up division of labor — actionable implementation plan

**Status**: ACTIVE — Phases 0–2 and the Phase-3 planner core are pushed on `lane/auditor`; rollout remains off pending compute/wrap integration, protected policy review, and canaries
**Created**: 2026-08-13
**Last refined**: 2026-08-13
**Priority**: P1 — task-boundary durability, fleet documentation consistency, and compute-blocker
visibility currently depend on contradictory procedures.
**Owner**: `coordinator-agent` (lifecycle and integration owner)
**Reviewer**: `auditor`
**Owning index**: [`routing-and-optimization-index.md`](routing-and-optimization-index.md), `RTG-51`
**Related work**: `RTG-48` coordinator failure modes; `RTG-34` session-bus dispatcher
**Rollout state**: `off`; no current worker behavior changes merely because this plan exists.

#### Decision and outcome

The operator's role split is decided and is not reopened here:

- Worker mains perform a lightweight, durable **log checkpoint** at every completed or genuinely
  blocked task boundary. They do not run the fleet's heavy wrap-up.
- Coordinator validates checkpoint receipts, integrates accepted lane commits, controls context
  transitions, and relays fleet-wide wrap triggers. It wraps only its own coordination surfaces.
- The **auditor IDENTITY** owns review and the heavy wrap. Since P3-7 there is no interactive
  auditor SESSION: the reviewer function runs as **per-packet headless invocations**, one per
  completion (P2-7). Per-packet audit and the fleet-wide heavy wrap are therefore two different
  transactions — see *Heavy wrap* below — and only the latter takes the single-writer lease.
- Inference alone judges live resource compatibility (graded `compute-window` events) and owns
  the physical-claim lease vocabulary; the daemon executes compute-window grants deterministically
  against `compute_policy.yaml` (D4 as amended 2026-08-15/16; BUS_PROTOCOL rule 11 as amended
  2026-08-16). Coordinator prioritizes eligible work; neither Coordinator nor Auditor manufactures
  hardware state.

This plan replaces the original planning stub. The audit found that its direction was sound but its
mechanics were not executable: a worker commit was not visible across lanes, blocked work had no
typed receipt, the proposed batch index is a single-writer execution campaign, per-agent progress
logs were rejected by the live currency checker, hooks wrote derived index state after worker
commits, and the long-lived wrap lease could be reclaimed by a second same-role process. Current
structural checks pass despite those defects, so each contract below has a negative control.

#### Vocabulary

- **Task boundary**: the worker completed its task, or progress now requires a named other owner,
  operator decision, resource grant, or external event.
- **Promptly movable blocker**: the worker has authority and resources to clear it now, within the
  current work unit, without waiting for another owner, grant, decision, or event. This is not a
  task boundary; the worker keeps working.
- **Non-movable blocker**: the worker has exhausted in-scope preparation and can name the owner or
  event that must occur, the evidence, and the exact resume action.
- **Log checkpoint**: the worker-owned transaction that records, validates, commits, pushes, and
  emits a typed receipt for one task boundary.
- **Heavy wrap**: the transaction that reconciles an immutable receipt cut, files follow-ups,
  compacts handoffs, regenerates indices, compiles documentation, and publishes once. It is owned
  by the auditor IDENTITY and executed by a **single headless invocation holding the wrap lease** —
  NOT by an interactive session, and NOT once per completion. Regenerating indices or compiling the
  wiki per packet would be wrong and expensive; batching is the point of the immutable cut.
- **Per-packet audit**: the P2-7 headless invocation that consumes one completion's pointer packet
  and emits a verdict. It is read-only with respect to indices, the wiki, and `main`. Many of these
  occur between heavy wraps.
- **Major checkpoint**: a completed phase or campaign whose integrated state should be reflected in
  fleet indices and the wiki. It does not mean every task boundary.
- **Related work**: the same artifacts, premises, or investigation remain load-bearing.
- **Disjoint work**: productive work needs a fresh context and would not reuse the checkpointed
  task's reasoning.

#### Authority and write ownership

| Surface or decision | Sole authority | Other roles |
|---|---|---|
| Task artifacts, source task checkbox, newly discovered source tasks | Originating worker | Coordinator/Auditor verify read-only |
| `progress/YYYY-MM/YYYY-MM-DD-<agent>.md` | Named agent | Receipt validator verifies committed copy |
| Lane commit and lane push | Originating worker | Coordinator verifies remote reachability |
| Receipt acceptance, lane-integration order, `/clear`, follow-on dispatch | Coordinator | Worker reports facts; Auditor may audit |
| Audit verdict and audit follow-up rows | Auditor | Worker retains ownership of source completion state |
| Handoff compaction, domain-index mutation, generated index state, wiki compile | One heavy-wrap writer | Auditor subagents may inspect/propose read-only |
| Compute window grade, compatibility, physical claim, safe drain | Inference | Coordinator ranks only Inference-eligible candidates; the daemon grants windows per `compute_policy.yaml` (D4) |
| Cross-lane promotion to `main` | Coordinator integration path | Auditor supplies the reviewed/published packet |

Workers must not mutate domain indices, master generated blocks, wiki manifests, or `main` during a
log checkpoint. Auditor must not flip a worker-owned checkbox or absorb uncommitted state from
another lane. Coordinator must not reconstruct an absent worker checkpoint. Derived files have one
writer and are regenerated only inside the heavy-wrap lease.

The current top-level trust rule forbids handoff and index mutations by subagents without explicit
operator approval. The proposed narrow exception authorizes exactly one designated wrap executor per
Coordinator request and lease; it does not authorize parallel mutation.

> **REVISED 2026-08-16 — the interim rule became unsatisfiable and had to be replaced, not merely
> reworded.** This paragraph previously read: *"Until the protected amendment in Phase 5 is
> ratified, Auditor main is the heavy-wrap writer and subagents are read-only."* **P3-7 retired the
> interactive auditor session**, so that sentence has no subject — taken literally the document was
> left with NO designated heavy-wrap writer, which is worse than an outdated one because it fails
> silently. Corrected interim rule: **the heavy-wrap writer is the single headless invocation that
> holds the wrap lease, writing under the auditor identity.** The read-only constraint survives
> unchanged and now binds every invocation that does NOT hold the lease, which includes every
> per-packet P2-7 audit.
>
> **Identity is not session, and the distinction is load-bearing.** Supplied verbatim by the RTG-52
> Loop-Owned Fleet session, which owns this mechanism:
>
> > Since P3-7 (2026-08-16) the `auditor` roster row is `role: service` with no tmux
> > endpoint and no `worktree:` key: no pane can be spawned, probed or nudged under
> > that id. The reviewer function runs as per-packet headless invocations of
> > `scripts/coordination/headless_audit.py`. The IDENTITY is deliberately NOT
> > retired — `worker_runner.py` addresses every audit packet to `auditor` and
> > `headless_audit.py` writes its own outbox under that id, and
> > `session_bus.py::_check_routing_intent` raises `BusError` on an assignee or
> > routing target whose roster role is `retired`. Tombstoning it would break the
> > P2-7 audit path.
>
> Any future edit that "cleans up" the retired session by retiring the identity will break audit
> routing at that raise.
>
> **The test this tier must keep passing: does it still work with no interactive auditor?** Every
> remaining `Auditor` in this document should be read as the identity, executing headlessly. Where
> a row below says Auditor *subagents* may inspect or propose, that now describes invocations under
> the identity rather than children of a session.

#### Lifecycle state machine

| Current state | Event | Required action | Next state |
|---|---|---|---|
| `WORKING` | Promptly movable blocker | Clear it or finish remaining preparation; emit no boundary receipt. | `WORKING` |
| `WORKING` | Task completed | Run a log checkpoint with `outcome=completed`. | `CHECKPOINTING` |
| `WORKING` | Non-movable blocker | Name owner/event and resume action; checkpoint with `outcome=blocked`. | `CHECKPOINTING` |
| `CHECKPOINTING` | Validation, commit, push, or receipt fails | Preserve the completed prefix and retry idempotently; refuse clear/close. | `CHECKPOINT_FAILED` |
| `CHECKPOINT_FAILED` | Missing suffix succeeds | Coordinator validates the pushed receipt. | `CHECKPOINT_RECEIVED` |
| `CHECKPOINT_RECEIVED` | Schema, remote, ownership, or evidence fails | Quarantine receipt with typed reasons; do not audit or integrate. | `REJECTED` |
| `CHECKPOINT_RECEIVED` | Validation succeeds | Emit one immutable `audit-request` for exact SHA/evidence packet. | `AUDIT_PENDING` |
| `AUDIT_PENDING` | `accept` or `accept-with-followups` | Coordinator integrates exact reviewed commit; Auditor owns any follow-up rows. | `DURABLE_BOUNDARY` |
| `AUDIT_PENDING` | `needs-rework` | Coordinator converts findings to ordinary owned backlog work; do not integrate. | `REWORK` |
| `AUDIT_PENDING` | `blocked-evidence` | Request only the named missing evidence; do not integrate. | `EVIDENCE_BLOCKED` |
| `DURABLE_BOUNDARY` | Related work ready | Keep context and continue; heavy wrap is asynchronous. | `WORKING` |
| `DURABLE_BOUNDARY` | Disjoint work ready | Coordinator sends `/clear` alone, confirms it landed, then sends a self-contained brief. | `CLEARING` then `WORKING` |
| `DURABLE_BOUNDARY` | Alternate work exists behind a blocker | Route blocker to its owner and dispatch alternate work by related/disjoint rule. | `WORKING` |
| `DURABLE_BOUNDARY` | Worker reports genuinely dry | Coordinator rechecks the queue, then dispatches or sends close. | `WORKING` or `CLOSED` |
| `DURABLE_BOUNDARY` | `major_checkpoint=true` | Coordinator creates one deduplicated heavy-wrap request with a fixed cut. | Worker stays `WORKING`; wrap becomes `REQUESTED` |
| Any active state | Clear/close requested before a valid receipt | Refuse it and safely finish the checkpoint. | Unchanged |

A worker may continue related safe work after its pushed checkpoint while audit/integration is
pending, but no disjoint `/clear`, close, promotion, or completed-state claim is authorized until the
receipt reaches `DURABLE_BOUNDARY`. A worker never decides fleet-wide dryness and never idles on a compute grant. It reports a durable
blocker, then drains the bus and takes the next compatible task. A normal `/clear` requires a valid
checkpoint receipt plus a disjoint next task; it does **not** wait for heavy wrap. Pre-reboot is the
only standing synchronous heavy-wrap barrier.

#### Worker log-checkpoint contract

The implementation is one command/skill backed by one testable program, not a prose checklist:

- `.claude/skills/log/SKILL.md`
- `scripts/coordination/worker_checkpoint.py`
- `tests/coordination/test_worker_checkpoint.py`

For a stable `boundary_id`, it performs this exact order:

1. Verify private-lane identity and resolve the source task by task text, not a stale line number.
2. Update only worker-owned task state: completed tasks flip the exact box and append
   `✅ YYYY-MM-DD`; blockers remain open and gain a distinct task with an exact resume action.
3. Append the boundary result to `progress/YYYY-MM/YYYY-MM-DD-<agent>.md`.
4. Run ownership, checkbox-sync, scoped diff, and task-specific validation gates.
5. Commit only explicit owned pathspecs. `git add -A`, peer shards, and unrelated dirty files are
   forbidden.
6. Push `lane/<agent>` without promoting it.
7. Emit the typed receipt containing the pushed SHA. No receipt exists before a successful push.

Retries return the existing receipt or execute only the missing suffix. They must not duplicate a
progress entry, task row, commit, or bus message. A no-op is valid only when the same `boundary_id`,
commit, and receipt already validate. Failure leaves a machine-readable checkpoint state and never
claims durability.

##### Boundary receipt

Add a typed `task-checkpoint` bus kind. It does not replace the existing `task-complete` audit event:
the checkpoint references that event, or the Coordinator synthesizes it exactly once after accepting
a completed receipt.

Required common fields:

```yaml
boundary_id: <agent>:<task_id>:<stable-boundary-sequence>
outcome: completed | blocked | partial
boundary_reason: task-boundary | pre-reboot
task_id: <durable id>
task_text: <resolved checkbox text>
spec_ref: <handoff path plus stable task anchor>
agent: mainA | mainB | mainC | mainD | auditor | coordinator-agent | inference
branch: lane/<agent>
commit_sha: <40-hex pushed commit>
pushed_ref: refs/remotes/origin/lane/<agent>
progress_path: progress/YYYY-MM/YYYY-MM-DD-<agent>.md
handoff_paths: [<owned paths>]
checkbox_flips: [<before/after task identity>]
new_tasks: [<task identity and owner>]
validation: [{command: <argv>, exit_code: 0, evidence_ref: <ref>}]
next_context: related | disjoint | dry | pre-reboot
major_checkpoint: true | false
completed_at: <UTC RFC3339>
```

`outcome=blocked` additionally requires:

```yaml
blocker_class: dependency | operator-decision | external-event | compute
blocked_on: <specific condition>
blocking_owner_or_event: <named owner or event>
evidence_refs: [<durable refs>]
alternatives_exhausted: [<attempted in-scope alternatives>]
resume_action: <first executable action after unblock>
compute_request: <typed request or null>
```

`outcome=partial` is legal only for `boundary_reason=pre-reboot`. It never flips the completion box
and requires the same evidence and exact resume action as a blocker.

Coordinator accepts a receipt only if its author matches the roster/lane, the SHA is reachable from
the stated remote ref, the commit contains the named per-agent progress shard and handoff changes,
and all paths are owned by that worker. A local-only SHA, unsuffixed progress file, peer progress
shard, forged author, or post-commit log edit fails closed.

An accepted receipt produces one `audit-request`. Auditor responds with a typed `audit-verdict`
containing `checkpoint_id`, exact audited SHA, verdict (`accept`, `accept-with-followups`,
`needs-rework`, or `blocked-evidence`), evidence references, findings, and follow-up task IDs.
Coordinator integrates only the first two verdicts. Auditor never directs a worker; rework and
follow-ups return through Coordinator as ordinary owned tasks.

#### Heavy-wrap contract

A heavy wrap begins only from a typed `wrapup-request` issued by Coordinator. Valid reasons are:

- explicit operator request;
- an accepted major-checkpoint receipt;
- a pre-reboot barrier;
- an Auditor `wrapup-due` proposal that Coordinator accepts.

The request carries `request_id`, reason, synchronization mode, and the exact accepted receipt IDs
or cutoff timestamp. Receipts arriving after the cut belong to the next wrap. “Auditor cadence” means
Auditor may propose that a wrap is due; it does not authorize an untracked autonomous mutation.

After Coordinator has integrated every eligible lane checkpoint in the cut, the designated writer
acquires one operation-token lease and performs the ordered transaction:

1. Sync from the integrated `origin/main` commit named in the request.
2. Reconcile every included receipt and record every explicit exclusion.
3. File Auditor-owned follow-ups; never rewrite worker-owned completion state.
4. Compact/prune handoffs and update each owning domain index.
5. Regenerate timeline/index state and run structural and ownership checks.
6. Run remaining documentation and freshness work.
7. Compile the wiki as the **last documentation-content mutation**.
8. Commit exact paths, push the Auditor lane, and hand the reviewed packet to Coordinator promotion.
9. Verify promoted `main`, then emit `wrapup-complete` and release the lease in a trap.

The wiki is not literally the final shell command: commit, push, promotion, verification, receipt,
and lease release follow it. A failed asynchronous wrap remains queued and does not stop workers. A
failed synchronized pre-reboot wrap keeps the barrier closed.

`wrapup-complete` names the request and included receipts, exclusions, source and promoted SHAs,
generated-artifact hashes, validation results, wiki manifest/watermark, and lease operation ID.

#### Compute-blocker intake and graded window contract

`handoffs/active/eval-tower-program.md` is **not** the generic intake surface. It is a v7-era,
single-writer execution campaign whose manifest and ledger are owned by `/loop`; its boxes must not
be mutated by Auditor. This plan leaves that authority intact.

The source of truth for compute-ready work is the accepted `task-checkpoint` receipt, its typed
compute request, and Inference's append-only intake dispositions. Coordinator forwards a
`compute-blocker`; Inference alone moves it through
`submitted -> admitted|duplicate|needs-info|rejected -> ready -> planned -> granted|denied -> running -> terminal`.
A daemon builds a reconstructible, read-only projection of admitted/ready records at
`coordination/session-bus/compute_ready.json`; no human or worker edits the generated candidate
block. The existing `coordination/backfill/ready_hint.txt` becomes a pointer derived from that
projection, not a second truth source. Proposed implementation:

- `scripts/coordination/compute_ready.py`
- `coordination/session-bus/compute_ready.json`
- `tests/coordination/test_compute_ready.py`
- schema and relay changes in the existing session-bus files

Each candidate carries task/spec identity, source receipt, minimum window grade, CPU bandwidth
class, GPU/device/VRAM requirements, model and weight identity, estimated load/occupancy/duration,
contention and pausability class, operator gates, expiry, and graph-derived live downstream tasks.

Each disposition carries a stable `blocker_id`, source checkpoint, reason code, and prior-event ID;
status changes are new events, never in-place edits. Auditor verifies coverage during heavy wrap but
does not admit or status the intake. Only Inference emits a typed `compute-window` event:

```yaml
grade: small-model-only | load-then-keep-hot | full-idle
eligible_devices: [<device/region>]
cpu_bandwidth_class: <class>
gpu_vram_available: <bytes plus observation refs>
resident_model: <identity or null>
load_allowed: true | false
starts_at: <UTC RFC3339>
expires_at: <UTC RFC3339>
time_budget_seconds: <integer>
safe_drain_at: <condition/time>
observation_refs: [<multi-sample evidence>]
```

A window grade is a compatibility label, not a total ordering; explicit budgets decide fit. A window
announcement is advisory and never substitutes for the existing typed resource lease.
Inference filters candidates for live compatibility and owns execute/lease choice. Coordinator then
ranks the eligible set deterministically by:

1. explicit operator `must-run` override, if any;
2. number of currently live downstream tasks made fire-ready, derived from a pinned
   `.index-graph.json` hash;
3. direct handoffs unlocked, then transitive open dependants;
4. production priority class;
5. exact window fit, grouping same-weight work for `load-then-keep-hot`;
6. oldest accepted checkpoint;
7. stable blocker ID.

The dispatch contains only the selected finite batch, its rank evidence, window ID, and lease path.
Unknown grades, expired windows, missing evidence, incompatible weights, or unleased execution fail
closed. Inference may skip a higher-ranked candidate only with a typed incompatibility reason for the
current window; Coordinator may not override fit, and Inference may not rewrite leverage or priority.

#### Implementation sequence

Each phase has an independent commit and must leave the current workflow usable. Safety repairs land
before role cutover.

##### Phase 0 — publish the contract

- [x] Audit current lifecycle, bus, progress, hook, batch, role, and lease contracts. ✅ 2026-08-13
- [x] Replace the stub with this authority table, state machine, typed protocols, migration matrix,
      rollout gates, and acceptance suite. ✅ 2026-08-13
- [x] Correct ownership to `RTG-51`; remove the stale `d7b83ddf` dependency (already in
      `origin/main`). ✅ 2026-08-13
- [x] Publish a standalone implementation-audit flowchart covering Coordinator, mainA–D,
      Auditor, Inference, failure loops, authority boundaries, and deployment gaps. ✅ 2026-08-13

##### Phase 1 — repair foundations before changing behavior

- [x] Change `progress_log_currency()` to validate receipt-bound per-agent progress evidence. ✅ 2026-08-13 (`20640d55`)
  Keep unsuffixed logs for historical reads only. Add negative controls for local-only SHA, peer
  shard, post-receipt edit, and no-boundary state.
- [x] **Autonomous writers:** remove `index_state.py` writes from post-commit/merge/checkout hook ✅ 2026-08-13 (`60187101`)
- [x] **Step-3 prune selection no longer keys on `open == 0`** ✅ 2026-08-18 (`428c7bb6`). That read
  the ABSENCE OF OPEN CHECKBOXES as the PRESENCE OF COMPLETION — the same category error as using
  mtime for `last_advanced`. Measured across the 15 handoffs then reporting `open == 0`: **13 were
  false positives** (compatibility pointers, work stated in prose and never checkboxed, prompts and
  notes-only references that never carried tasks, and handoffs whose remaining boxes are
  guarded/blocked). `scan_handoff` now also reads the status region and the structural open-work
  markers, emitting `prune: {candidate, blocker, evidence}` — conservative by construction, every
  rejection naming its blocker and quoting the evidence line. `agents/commands/wrap-up.md` Step 3
  documents the replacement selection command and states it is a **screen, not a verdict**.
  17 tests; the screen is proven non-vacuous by a real-world positive control.
      bodies; make `install_timeline_hook.sh` upgrade its marked block; prove a worker handoff commit
      leaves `.index-state.json`, `.index-graph.json`, and master generated content unchanged.
- [x] **Wiki hook:** ensure ordinary post-commit retrieval refresh cannot mutate ✅ 2026-08-13 (`60187101`)
      `wiki/source_manifest.json` or the wrap watermark; give retrieval its own cursor if needed.
- [x] **Lease:** replace roster/PID reclaim with an opaque per-operation token in a mode-0600 token ✅ 2026-08-13 (`8ff5162c`)
      file, store its hash in the lock, require the token for normal release, and audit explicit
      force-release. A second same-roster process without the token must be refused.

Phase gate: focused progress, hook, lease, and concurrent-wrap suites pass, including a negative
control that would have admitted the previous same-role lease collision.

##### Phase 2 — implement checkpoint and receipt in shadow mode

- [x] Add the log skill, checkpoint program, typed schema, relay/fold validation, and idempotence
      journal. ✅ 2026-08-13 (`82c1c5b4`)
- [x] Preserve the existing completed-task audit flow without duplicate `audit-request` synthesis. ✅ 2026-08-13 (`82c1c5b4`)
- [x] Add Coordinator validation for remote reachability, path ownership, exact task identity, and
      committed progress evidence. ✅ 2026-08-13 (`82c1c5b4`)
- [x] Shadow-record complete, blocked, and pre-reboot boundaries without rejecting legacy behavior.
      ✅ 2026-08-23 — `scripts/coordination/rtg51_rollout.py` + `coordination/session-bus/rtg51_rollout.yaml`
      (`worker_checkpoint_receipts: off|shadow|enforce`). Shadow validates every receipt class
      (complete, blocked, partial/pre-reboot), writes each result as a finding-shaped observation on
      the bus, and never rejects; enforce refuses defects; `RTG51_SHADOW_MODE=1` forces the canary
      grade. `tests/coordination/test_rtg51_rollout.py` pins shadow-records/never-rejects and
      enforce-refuses.

Phase gate: two workers can checkpoint concurrently without sweeping peer hunks; failed validation,
commit, or push cannot produce an accepted receipt; a repeated `boundary_id` produces no duplicate.

##### Phase 3 — implement compute-ready projection and admission

- [x] Implement and test the pure, deterministic compute-ready projection/ranking core without
      creating a live intake or dispatch path. ✅ 2026-08-13 (`7623e37c`)
- [x] Add compute request/window schemas, the reconstructible projection, graph-derived leverage,
      stable ranking, and focused bus dispatch. ✅ 2026-08-23 — `compute-window` and
      `compute-blocker` kinds in `session_bus.schema.json` (blocker lifecycle as append-only
      disposition events, never in-place edits; only `inference` authors windows/dispositions),
      `scripts/coordination/compute_ready_daemon.py` rebuilding `coordination/session-bus/compute_ready.json`
      via the landed planner core (cross-validates each forward against its accepted receipt;
      self-hash + deterministic-replay `check`). Daemon integration tests appended to
      `tests/coordination/test_compute_ready.py`.
- [ ] Encode the authority split in Coordinator and Inference role files.
- [ ] Leave `inference-batch-loop.md`, its manifest, and its `/loop` single-writer protocol
      unchanged except for an explanatory cross-reference if useful.

Phase gate: small-model, keep-hot, full-idle, expired, wrong-weight, insufficient-VRAM, and missing
lease cases are deterministic; only Inference can declare compatibility or grant a claim.

##### Phase 4 — make heavy wrap atomic and receipt-driven

- [x] Update `agents/commands/wrap-up.md` for request ID, immutable receipt cut, one designated
      writer, operation-token lease, ordered mutations, Coordinator promotion handoff, and completion
      receipt. ✅ 2026-10-07 — MAIN source-only review; conditional typed transaction contract now explicit. Protected Phase-5 ratification and actual Auditor canary remain open; no runtime activation.
- [x] Fix the deterministic `test_full_wrap_transaction_end_to_end` failure (filed 2026-09-08
      wrap-up). The heavy-wrap e2e fails at its progress-shard assertion (`progress/2026-08/
      2026-08-23-auditor.md` missing after the run) on a PRISTINE HEAD checkout — proven twice
      independently (a scratch `git archive` run and a stash-run of the same test), so it is not
      environment or this session's manifest fix. The defect is upstream of `step_7_compile_wiki`:
      the run completes all earlier steps yet never writes the auditor's daily shard that step 6
      asserts.
      ✅ Fixed by `40034bf1` (2026-09-16, KB-WM-4), never ticked: a TEST defect, not a code one — the
      assertion hard-coded the fixture day `2026-08-23` while `step_6_freshness` stamps the shard with
      the wall clock; the test now globs `progress/*/*-{AGENT}.md`. Re-verified 2026-09-24:
      `test_heavy_wrap.py` 14/14, the e2e case 20/20 repeated runs, fixture fully under `tmp_path`.
- [x] Update concurrent-wrap tests: two same-roster executors contend, only one mutates, crash ✅ 2026-08-13 (`8ff5162c`)
      residue remains held, wrong tokens cannot release, and all worktrees share the common-git-dir
      lease.
- [x] Add receipt inclusion/exclusion and post-cut deferral tests. ✅ 2026-08-23 —
      `tests/coordination/test_heavy_wrap.py` pins pure `reconcile_receipts` (exact-id set,
      cutoff mode, `post-cut-deferral` for receipts after the cut, duplicates, wrong-kind,
      absent named ids) plus the executor-level lease tests (two same-roster executors with
      distinct operation tokens contend and only one mutates; wrong token cannot release;
      crash residue stays held until a named displacement; dry-run mutates nothing).

Phase gate: one real Auditor canary consumes two concurrent worker receipts and promotes one complete,
reproducible wrap packet with no lost generated contribution.

##### Phase 5 — migrate standing policy as a protected package

- [ ] Reconcile every superseded instruction in the migration matrix below. Keep protected policy in
      a separate reviewable commit; do not change `human_only_paths.yaml` or its pin.
- [ ] Present the `CLAUDE.md`/`AGENTS.md` and `agents/shared/*` amendment for operator signoff. The
      subagent exception, if retained, must be narrow: one designated writer, one request, one lease.
- [ ] After merge, Coordinator sends each live session a correlated instruction-refresh nudge naming
      the merged SHA and exact files. Each agent rereads its common and role files and acknowledges
      from its own outbox before enforcement.
- [ ] Restart the session-bus daemon at its owner's boundary and prove process start time is newer
      than every changed runtime file.

##### Phase 6 — canary, enforce, and retire the old path

- [x] Add rollout modes: `worker_checkpoint_receipts: off|shadow|enforce`,
      `auditor_full_wrap: off|shadow|enforce`, and `compute_window_plan: off|observe|enforce`.
      ✅ 2026-08-23 — `coordination/session-bus/rtg51_rollout.yaml` is policy-as-data;
      `scripts/coordination/rtg51_rollout.py` loads it (env override `RTG51_SHADOW_MODE=1` for
      canary runs) and gates the checkpoint receipts, the heavy wrap (`off` refuses a real run,
      `shadow` forces dry-run + finding observations, `enforce` runs the ordered transaction),
      and the compute plan. Default is `off`: no live behavior changes merely because the plan
      exists.
- [ ] Canary one completed boundary, one non-compute blocker, one compute blocker, two concurrent
      workers, one Auditor wrap, and one simulated pre-reboot barrier.
- [ ] Move to enforcement only after complete, blocked, and pre-reboot cases each pass three
      consecutive real/simulated boundaries with no manual repair and every live role acknowledges
      the new instructions.

#### Policy migration matrix

| Surface | Superseded behavior | Required replacement | Gate |
|---|---|---|---|
| `coordination/session-bus/tasks/MAIN-GOALS.md` | Worker behavior does not name the checkpoint transaction | Require checkpoint receipt at every terminal boundary | Phase 5 |
| `coordination/session-bus/tasks/STANDING-MAIN-RULES.md` | Workers full-wrap at major checkpoints; progress path is unsuffixed | Workers checkpoint; per-agent shard; Coordinator triggers heavy wrap | Phase 5 |
| `coordination/session-bus/tasks/post-reboot-session.md` §6 | Each main writes its own wrap-up | Per-worker pushed receipt plus one synchronized fleet wrap | Phase 5 |
| Current mainA–D briefs | Explicit worker `/wrap-up` instructions | Regenerate briefs after common policy lands | Instruction ack |
| `agents/shared/SESSION_LIFECYCLE.md` | Disjoint task and major checkpoint require worker full wrap | Every terminal boundary checkpoints; disjoint then clears; heavy wrap async except reboot | Operator signoff |
| `agents/shared/OPERATING_CONSTRAINTS.md` | Phase-boundary/full-wrap and generic fan-out language conflict with one writer | Separate read-only fan-out from designated mutation | Operator signoff |
| `agents/commands/wrap-up.md` | Manual-only/narrow audit trigger; wiki not literally last; PID-style lease usage | Coordinator request, immutable cut, one writer, wiki last content mutation, token lease | Phase 4 |
| `agents/auditor-main.md` | Full wrap after every audit pass | Audit checkpoint per pass; heavy wrap only from typed request | Phase 5 |
| `agents/coordinator-agent.md` | May tell a main/subagent to wrap without receipt cut | Validate/integrate receipts and issue deduplicated request | Phase 5 |
| `agents/inference-main.md` | Resource selection exists but graded-window division is implicit | Inference owns grade/compatibility/claim; Coordinator owns ranking | Phase 3/5 |
| `CLAUDE.md` / generated `AGENTS.md` | Subagent handoff/index writes forbidden | Preserve prohibition or ratify narrow designated-writer exception | Operator signoff |
| `session_bus_coordinator.py` | Checks only unsuffixed progress file | Verify committed per-agent shard from accepted receipt | Phase 1 |
| Timeline hooks | Regenerate index state after any handoff commit | Timeline-only hook; derived index regeneration inside heavy wrap | Phase 1 |

#### End-to-end acceptance matrix

| Scenario | Required result |
|---|---|
| Completed task, related follow-on | Pushed checkpoint accepted; context retained; no heavy-wrap wait |
| Completed task, disjoint follow-on | Pushed checkpoint accepted; `/clear` delivered alone; brief follows confirmation |
| Movable blocker | Worker continues; no terminal blocker receipt |
| Non-movable blocker | Typed evidence/resume action accepted; blocker routed; worker receives other work |
| Compute blocker | Candidate appears in generated compute-ready projection, never directly in `/loop` ledger |
| Failed validation/commit/push | No accepted receipt, clear, close, or success claim |
| Duplicate boundary | Same receipt returned; no duplicate docs, commit, or message |
| Peer or unrelated dirty hunk | Excluded from pathspec; checkpoint either succeeds safely or refuses |
| Major checkpoint | Exactly one asynchronous wrap request for an immutable cut |
| Concurrent Auditor executors | One enters; all others are refused without the operation token |
| Receipt after wrap cutoff | Deferred explicitly to next wrap |
| Graded compute window | Only compatible, leased tasks dispatched in deterministic order |
| Pre-reboot | Every roster receipt and Inference drain validates; one synchronous heavy wrap; then ready |

Required validation includes the worker/checkpoint tests, full session-bus schema/relay/fold suite,
progress-currency tests, hook installer/non-writer tests, serialized-push and concurrent-wrap tests,
compute-grade/ranking tests, agent-file validators, `index_state.py --check`, claim grammar, README
freshness, and wiki manifest/lint checks. Passing the current legacy suite alone is not acceptance.

#### Rollout and rollback

Start `off`, then `shadow`, then `enforce`. Shadow mode records and validates the new receipts while
legacy behavior remains available. Enforcement is fleet-wide only after the protected policy package,
live daemon reload proof, and instruction acknowledgments land.

Immediately return the affected flag to `shadow` or `off` if a compliant worker gets a false progress
defect, two heavy-wrap writers enter, a worker changes a generated/index/wiki surface, a pushed
receipt cannot be reconstructed, a source receipt is omitted, a wrong compute grade admits a task,
promotion loses prior state, or any live role has not acknowledged the instruction SHA.

Rollback never deletes receipts or force-pushes. Pause new heavy wraps, let workers keep checkpointing
their lanes, inspect the lease, force-release only proven residue with an audit reason, and regenerate
derived state from authoritative handoffs under one valid lease. Keep independent safety fixes
(per-agent progress support, autonomous-writer removal, and lease hardening) unless their own tests
fail.

#### Pre-reboot barrier

1. Coordinator announces a cut and stops dispatching work that cannot reach a safe drain point.
2. Every worker finishes or safely stops its unit, pushes a checkpoint with
   `next_context=pre-reboot`, and names the resume action for incomplete work.
3. Inference drains active work and records/releases physical claims under its own contract.
4. Coordinator validates the roster receipts, integrates the cut, and checkpoints its coordination
   surfaces.
5. Coordinator issues one synchronized `wrapup-request` with the complete cut.
6. Auditor performs and publishes the heavy wrap.
7. Coordinator validates `wrapup-complete` and roster coverage. Only then is reboot readiness true.

A missing/unpushed worker receipt, unreleased claim, failed promotion, missing wiki watermark, or
failed heavy wrap keeps the barrier closed.

#### Immediate next action

Finish the open integration seams in this order:

1. connect typed compute blocker/intake/window events and the pushed planner core to the bus under
   Inference-owned compatibility and lease authority;
2. implement the receipt-cut heavy-wrap executor and completion receipt on the hardened lease;
3. shadow the complete, blocked, pre-reboot, compute, and immutable-cut paths;
4. present the protected Phase-5 instruction package for operator approval, then canary before
   enforcement.

The current implementation and its remaining gaps are rendered in
[`docs/coordination/session-bus-task-flow.html`](../../docs/coordination/session-bus-task-flow.html).
The only operator-only action is approval/merge of the protected Phase 5 policy package and any
narrow subagent-writer exception.
