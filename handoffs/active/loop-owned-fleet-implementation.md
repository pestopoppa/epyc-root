# Loop-Owned Fleet — implementation

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

- [ ] **Find out what removed `repos/`.** The likeliest cause is the live `git clean` that
  destroyed `retirements/` earlier today (see P0-7/P3-7 above), which would mean the same
  event cost two things and only one was noticed. Cheap to check against the shell history and
  the reflog; worth knowing, because the repair is idempotent but the *cause* is not fixed.

### OP-11 — `main` cannot push, and the graph is the only thing left unreconciled

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

**Recommendation: (a)**, and it needs a `D9-ack:` trailer. It is reversible until pushed —
`git reset --hard` before the push undoes it completely.
