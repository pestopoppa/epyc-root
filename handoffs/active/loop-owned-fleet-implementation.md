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
| D6 (amended) | Kill-with-salvage: kill at lease expiry is allowed, loss is FORBIDDEN. SIGTERM → grace → SIGKILL, then mandatory salvage: uncommitted worktree state committed to `salvage/<task_id>`, harness transcript + pane scrollback attached to the row, row marked `FAILED-salvaged`. Nothing is ever discarded. |
| D7 | One-time signed ghost sweep (11 dead-owner rows/claims, owner-death verified, list enumerated for operator review first) + `.orphan` worktree disposal (archive tarball, verify tips contained in lane branches, delete by explicit path list — NEVER `git worktree prune`). |
| D8 | Worker panes are VISIBLE and human-authoritative: the operator may watch, steer, and answer permission prompts by hand. The machine never types into a pane and never makes a decision from pane text; it may capture scrollback as evidence for human triage. Completion signal = schema-valid report file, never pane text. |
| D9 | Operator-gated loop-plane merges: the fleet may file typed defect rows and proposed patches, but merging any change under `scripts/coordination/**` requires operator ack. Self-repair share is computed by commit-path classification, never self-reported. **This gate applies to this implementation itself** — each phase lands as proposed commits the operator acks. |

Standing constraint (from the plan): **prose-rule moratorium** — from Phase 0 onward, a new incident
appends a labeled example to the eval fixtures, never a new rule/conjunct to BUS_PROTOCOL or agent files.

## Invariants that must survive every task (verbatim set lives in P1-1's INVARIANTS.md)

Single-writer; hash-pinned human-only trust boundaries; region claims acquired-not-observed (flock);
no name-pattern kills (owned pids only); two-sample persistence before destructive action; checkbox
ownership; never sign; measurement trust boundary human-amendment-only.

---

## Phase 0 — Stop the bleeding (Day 1)

Gate: **live-fire drill** — fleet killed ⇒ assignment halts and the operator's push channel receives
exactly ONE alarm; the cold-start skill brings the supervision tier back and re-verifies.

- [ ] P0-0 Copy the plan of record into `docs/design/loop-owned-fleet.html`; future amendments edit
      the in-repo copy first, republish to the artifact second.
- [ ] P0-1 Alarm channel: one operator-reachable push mechanism (ntfy/email — operator picks the
      endpoint at implementation). Wire: daemon fleet/runner-dead, fleet_watch queue-aging +
      compute-idle, supervisor death, aged compute-requests. Emit once on state change, never per tick.
      Deliverable includes the kill-the-fleet drill script.
- [ ] P0-2 Fleet-existence gate in the daemon: zero live roster mains ⇒ halt assignment + ONE
      critical alarm (not per-task INFRA_BLOCKED). Predicate is explicitly transitional — see P3-4.
- [ ] P0-3 Ghost-state sweep (D7, operator-signed): enumerate the 14 INFRA_BLOCKED rows + 11
      dead-owner CLAIMED/RUNNING/STALE_REQUEUED rows and claims; verify owner death via process
      table; present the list; on signature, release + reset to READY (or CANCELLED where the
      premise died). Add the standing rule: claims owned by retired ids are daemon-releasable with a
      receipt.
- [ ] P0-4 Fix `backfill_supervisor.sh` undefined `health_ok` (loop mode always takes the failure
      branch); add a test that exercises `loop` — THE consumer, not A consumer.
- [ ] P0-5 Verify the H-4 SHA deploy-marker predicate is what the RUNNING bus_supervisor executes
      (`ps -o lstart` vs commit time of `bc6dc77f`); restart if stale.
- [ ] P0-6 Harden `/coordinator-agent` into the D3 cold-start one-shot: relaunch supervisors, verify
      daemon health (pid identity + SHA marker, never the status file), run the alarm drill, report.
- [ ] P0-7 Bus runtime off-tree (D5): `mv` runtime data to `/mnt/raid0/llm/bus-runtime` at a quiet
      boundary + commit a tracked symlink at `coordination/session-bus`'s runtime paths; verify all
      consumers (Python `get_bus_root()` + the shell daemons) still resolve; document the real path
      for backup tooling.
- [ ] P0-8 `.orphan` worktree disposal (D7): archive tarball → verify each orphan tip is contained
      in a lane branch (push unique commits first if not) → delete by explicit path list. Add runner
      refusal for lane paths matching `*.orphan*` (lands with P2-1).
- [ ] P0-9 Declare the prose-rule moratorium in force: create `coordination/evals/fixtures/` with
      the fixture format (`label_provenance` field mandatory) and a README stating the rule.

## Phase 1 — Doctrine collapse (Days 2–3)

Gate: ship and fix forward (pure deletion needs no drill); moratorium verified in force.

- [ ] P1-1 `agents/shared/INVARIANTS.md`: the ~15 real invariants, verbatim, no origin narratives.
      Mechanical protocol cited from `session_bus.schema.json`, not restated.
- [ ] P1-2 Deduplicate headline rules (fan-out, liveness, checkbox, dispatch-identity, reload
      ownership, observation windows…): one canonical copy each; CLAUDE.md and every other surface
      cite, never restate. (The fan-out rule's 08-13 exceptions currently exist in 1 of 5 copies.)
- [ ] P1-3 Resolve the three live self-contradictions with one explicit ruling each, recorded here:
      (a) wrap-up cadence (manual-trigger banner vs lifecycle checkpoint contract vs binding 08-11
      per-task rule); (b) subagent index edits (SESSION_LIFECYCLE "coordinator subagent preferred"
      vs CLAUDE.md prohibition); (c) role-based delegation (role files/delegation matrix vs the
      measured role-decomposition anti-pattern).
- [ ] P1-4 Move incident narratives out of the instruction path: BUS_PROTOCOL/coordinator-agent.md
      shrink to contracts; narratives live in the ledgers; judgment heuristics become per-decision
      example packs under `coordination/evals/examples/` (future few-shot content).
- [ ] P1-5 Archive the eight dormant role files (benchmark-analyst … sysadmin) and the amber unwired
      task-flow sections; regenerate the flow doc from wired reality only.
- [ ] P1-6 Rewrite `agents/coordinator-agent.md` to ~50 lines: identity, invariants pointer,
      choke-point contracts, console role (primary operator channel; no clock ownership; no
      instrument reading; compute-policy editor per amended D4).

## Phase 2 — worker_runner MVP + pilot (Days 3–5)

Gate (absolute, measurable): ≥10 rows end-to-end with schema-valid reports · zero machine
delivery-plane interventions · zero silent permission denials · 100% independently audited ·
operator spot-reviews 3 of 10 · tokens/row within the D1 ceiling. Kill: quality drop or ceiling
breach ⇒ stop, reassess.

- [ ] P2-1 `scripts/coordination/worker_runner.py` (~200 lines target): claim (O_EXCL) → typed brief
      (AUD-2 schema: task_text primary, ≤4KB, screened_by, expected_occupancy, constraints[].source)
      → premise preflight (P2-2) → permission profile injection (P2-3) → lane lockfile (1 worker per
      worktree; refuse non-lane and `*.orphan*` paths) → spawn in a VISIBLE tmux pane (D8) → watch
      report-file + process exit → collect (schema validation, denial audit, `subagents_spawned`) →
      bus writes under the `workerpool` identity → audit packet (pointers only) → promotion row.
      Exec'd fresh per assignment by the daemon tick; the only persistent piece is the collector wait.
- [ ] P2-2 `premise_screener`: point LLM call, forced-choice still-needed | stale | UNKNOWN with a
      mandatory evidence quote; UNKNOWN/stale ⇒ park row + routed fix task (refusals emit once, on
      state change, and count as queue-aging). Few-shot examples from `coordination/evals/examples/`;
      eval fixtures with `label_provenance` before any authority promotion.
- [ ] P2-3 D2b permission profile: per-worker settings allowlist; any denied tool call recorded in
      the report ⇒ row outcome FAILED/blocked, never silent parity. Interactive-pane prompts remain
      answerable by the operator (D8); unanswered ⇒ lease expiry ⇒ salvage.
- [ ] P2-4 Kill-with-salvage (D6): lease expiry ⇒ SIGTERM → grace → SIGKILL (owned pid only), then
      WIP commit of the lane worktree to `salvage/<task_id>`, attach harness transcript + captured
      pane scrollback to the row, mark `FAILED-salvaged`. Mutation-test: a salvage that loses any
      file must fail the runner's own test.
- [ ] P2-5 Roster + daemon wiring: add `{id: workerpool, role: main, endpoint: "exec:worker_runner"}`
      and the daemon endpoint-scheme branch — the ONE schema/code extension the plan permits.
      `worker_harness:` config knob (global + per-lane override), pinned paid provider, concurrency
      cap ≤4, ~250k tokens/batch ceiling (D1).
- [ ] P2-6 Static batching: rows from the same source handoff share one invocation, cap 3, per-row
      completion records; on timeout only the in-progress row fails, untouched rows return to READY.
- [ ] P2-7 Headless audit per completion: auditor invocation consumes the pointer packet, derives
      the diff from git independently, runs one mutation probe, writes a typed verdict to the bus.
- [ ] P2-8 Merge cadence: promotion rows serialized through `merge_gate.py` / `serialized_push`, one
      at a time; part of the 10-row acceptance.
- [ ] P2-9 Run the pilot: 10 screened churn rows alongside the existing fleet (additive; nothing
      retired). Record tokens/row — mandatory input to the Phase-3 go decision and the D2 scale-out
      harness choice.

## Phase 3 — Retire the machine delivery plane (Days 6–7)

Gate: one full day of backlog churn with zero machine pane-IO for workers.

- [ ] P3-1 Retire mainA–D per identity: drain-verify → final wrap receipt → tombstone marker in the
      roster row → `assignee:` linter refuses new messages to retired ids → cursors archived. NOT
      "re-usable slots" (C24/C28 class).
- [ ] P3-2 Shrink `tmux_adapter.py` to the two interactive endpoints (machine side); worker panes
      remain human-only. Delete worker-side nudge/doorbell/heartbeat/glyph machinery.
- [ ] P3-3 `fleet_watch`: drop pane heuristics; keep hardware compute-idle (rocm-smi + region
      claims); add queue-aging alarm — rows refused by any gate count as AGING; every refusal class
      has an owner and emits once on state change with a routed fix task.
- [ ] P3-4 Swap the fleet-gate predicate for the ephemeral pool: runner-liveness + "READY>0 ∧
      capacity free ∧ no spawn attempt in N ticks" as the anomaly condition (zero live workers is
      the NORMAL idle state after this phase).
- [ ] P3-5 D4/D4b compute mechanization: compute policy file (priorities, windows, reservations;
      console-edited, edits logged as typed rows) + daemon grant check (region-free ∧ policy-allows)
      + aged-request alarm. All consumers (AutoKernel, AutoPilot, inference, workers) request via the
      same bus path. Amend BUS_PROTOCOL rule 11 accordingly (this is a protocol edit — lands with
      operator ack under D9).
- [ ] P3-6 First choreography recipe: the operator's CPU-pause → GPU-load → run ∥ resume example as
      a typed, receipt-gated recipe (drain@boundary receipt → load receipt → start + resume);
      approved at the coordination level, stepped through by the daemon.

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
- **Kill criteria**: pilot breaches the D1 ceiling or audit quality drops ⇒ halt, reassess. Any
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
