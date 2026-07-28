# Task: GPU shadow lane — P2-1 (resident lane) and P2-3 (Stage-0 hardening)

**Assigned to** `claude-gpu-lane` (roster id — use it verbatim for every bus command).
**Assigned by** coordinator-agent on operator direction, 2026-07-28.
**Owning handoff** [`handoffs/active/gpu-serving-tie-in-program.md`](../../../handoffs/active/gpu-serving-tie-in-program.md) — read it first; this file only scopes and constrains.

## Why now

Codex reported the MI210 idle: all legacy campaign GPU inference is terminal, and the next
eligible GPU evidence is the Phase-2/3 shadow lane. P0-7 (lane scaffolding) is COMPLETE and
pushed (orchestrator `cbfe0cde` + `f00c9557` + `c3ce44aa`). P2-1/P2-3 are the Claude-owned build
items that unblock the Phase-3 bake-off. The division of labour is fixed (root `73891f48`):
**Claude builds non-inference, Codex queues inference only.**

## Scope

- **P2-1 — role-agnostic resident lane.** Registry-driven tenancy (model path + role bindings as
  *data*), launch layer per the vision-runbook pattern, region-lock / lease integration honouring
  the fabric axioms: drain-at-boundary, never forcible.
- **P2-3 — Stage-0 hardening.** Deterministic smoke (fixtures, health, affinity/VRAM
  attestation), `np_ceiling(budget)` policy table derived from the measured grids, contention
  recert for host-side cores.

Start from what P0-7 already built rather than rebuilding it: lane spec `docs/gpu-shadow-lane.md`
(D1 admission order, Steps 0–7 activation choreography), the ready-to-apply registry PROPOSAL
`docs/proposals/gpu-shadow-lane-registry-proposal.md`, and the np_ceiling policy-as-data at
`orchestration/gpu_shadow_lane_np_ceiling.yaml` with its loader behind the default-off
`ORCHESTRATOR_FEATURE_GPU_SHADOW_LANE` flag. All of that is in **epyc-orchestrator**.

## Hard constraints

These are not style preferences. Each one has a live reason.

- **The model registry is FROZEN (D3).** Produce proposal diffs only. Apply NOTHING. P0-7
  deliberately kept launch wiring proposal-diff-only with a zero-coupling test witness; keep it
  that way.
- **Activation is operator-gated.** Steps 0–7 lead to P2-3/P2-4 and are the operator's to
  trigger. Do not activate the lane, do not start a shadow server, do not run the preflight probe
  against live hardware without an explicit operator grant relayed through coordinator-agent.
- **Never take the `cpu` lane.** Your roster row is `lanes: [gpu, none]`. The codex main is
  running CPU-side E8/G3 work, and P1-2's E5 NUMA×batch grid has a **~2026-07-31 deadline** on
  this host's uptime window. Contending for CPU could cost that deadline.
- **GPU lane use requires an acquired claim**, never an observation. Anything occupying a region
  acquires it via `epyc-orchestrator/scripts/region-lock`. Observing that a lane looks free is
  TOCTOU and is not exclusion (BUS_PROTOCOL rule 7).
- **Host-thread affinity**: MI210 host threads pin to `184-191` (SMT siblings), **not** `88-95`.
- **No host reboots** — operator-only.
- **Do not reload the orchestrator stack or API.** Codex has live E8 work in flight and has
  explicitly asked that the API not be reloaded. If you believe a reload is needed, report it to
  coordinator-agent and wait.
- Measurement discipline: any number that gates a decision needs `(metric, protocol-id, n/reps,
  date, attestation ref)` per `MEASUREMENT.md`. Benchmarks run only via the codified recipes with
  operator approval. Build work needs no such gate; claims about performance do.

## Definition of done

- P2-1 and P2-3 implemented as reviewable diffs in **epyc-orchestrator**, tests passing.
- Nothing applied to the frozen registry; launch wiring remains proposal-only with its
  zero-coupling witness intact.
- The owning handoff's `- [ ]` boxes for P2-1/P2-3 flipped to `- [x] … ✅ 2026-07-28` **by you**,
  with evidence refs — coordinator-agent does not tick checkboxes. Work discovered mid-flight
  gets its own new task line.
- Report completion to `coordinator-agent` via your outbox. Do not push without saying so first;
  this is a shared tree and other sessions have in-flight work.
- **Never `git add -A` or `git add .`** — explicit paths only, always.

## Bus protocol for you

Register first so the daemon can see you:

    ./scripts/coordination/session_bus.py append --agent claude-gpu-lane \
      --target heartbeat --json '{"state":"working","task_id":"gpu-lane-p2-1-p2-3"}'

At **every** task boundary, both of these:

    ./scripts/coordination/session_bus.py drain --agent claude-gpu-lane
    ./scripts/coordination/session_bus.py append --agent claude-gpu-lane \
      --target heartbeat --json '{"state":"working","task_id":"<current>"}'

A heartbeat written once is a birth certificate, not a liveness signal, and a stale one is
actively harmful: the stall ladder reads it as a stall and nudges a healthy agent. Retire the
`task_id` when a task reaches a terminal state.

Write only your own files: `outbox/claude-gpu-lane.jsonl`, `heartbeats/claude-gpu-lane.json`,
`cursors/claude-gpu-lane.json`. `queue.jsonl` and every `inbox/*` belong to the
coordinator-daemon. Address messages to `coordinator-agent`. Contract:
[`BUS_PROTOCOL.md`](../BUS_PROTOCOL.md).

**Known bus defects, so you are not surprised by them** (repaired or documented 2026-07-28):
`requires_ack` is currently decorative — rule 3 ack redelivery is unimplemented, so never assume
an unacked message will be retried. If a decision needs the operator, route it to
coordinator-agent as a decision package (2–4 options, tradeoffs, a recommendation, and the
default if nobody chooses) — never an open-ended question.
