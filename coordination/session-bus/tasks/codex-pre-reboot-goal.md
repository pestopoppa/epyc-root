# Codex-inference: revised goal — pre-reboot set, ending in a reboot request

**For** `codex` (window `agent:codex-inference`).
**From** coordinator-agent, relaying an **operator decision**, 2026-07-28.
**Supersedes** the open-ended campaign framing. This is a scoped, terminating goal.

## The decision

The operator is scheduling a host reboot. Work is now split into a **pre-reboot set (yours,
this session)** and a **post-reboot set (a new session, after the reboot)**. Your goal is:
**complete the pre-reboot set, drive the E8 chain to an apply-ready ratification bundle, present
it, and finish by requesting the reboot.** Then stop — do not start post-reboot work.

### What this changes about E5 urgency

`gpu-serving-tie-in-program.md` Phase 1 currently reads **"REBOOT NOT NEEDED"** with the note
that *"urgency INVERTS: E5 must run before ~2026-07-31"* — that text assumed no reboot. With a
reboot scheduled, **that deadline dissolves**: uptime resets to zero and the P-BENCH ≤1-week
decision-grade window reopens. So **E5 W1–W4 is POST-reboot** and is explicitly **not** yours.
Do not rush it into the remaining window. That Phase 1 text is now stale; flag it to its owner
rather than silently acting against it. (Note `batched-decode-measurement.md:519` says the
opposite — `BLOCKED_ON_OPERATOR_SCHEDULED_REBOOT`. Under this decision **that line is the
correct one** and Phase 1 is the stale one. The contradiction is real; say so in your wrap-up.)

---

## PRE-REBOOT set — yours

### 1. E8 chain → apply-ready ratification bundle (the spine)
- Drive the live cadence-fixed 298-generation successor (launched 16:09:17Z under q3 from
  detached worktree `d6b5d552`) to terminal.
- Reconcile the race-only successor-of-successor on `codex/e8-race-lost-successor-20260728`
  (`ccbdda1b`) per the parent's exact reconciliation/pin requirements.
- **P0-1 FIX-FIRST work — you own the branch.** The independent wrapper review verdict is
  *do NOT sign as pushed*. Required, all mechanical:
  - merge the branch's **3 newest commits** (the receipt-after-CAS redesign — the KEEP side)
    onto **main's composite validator**;
  - resolve the **4 add/add conflicts**, keeping **branch wrapper semantics + main validator**;
  - re-run the wrapper test suite;
  - **pin the MERGED-tree hashes** in the presentation — the branch tip `575ca543` is not
    self-consistent (it pins three runner files that exist only on main, and its own
    prepare/validator disagree on CLI args), so it cannot run from its own checkout.
- Reach **T2 terminal**. Once merged + T2 terminal → SAFE-TO-SIGN.
- **Present ONE consolidated apply-time bundle.** Per `MEASUREMENT_POLICY.md` → *Consolidated
  apply-time ratification*: evidence collection never waits on a signature; the human signs once,
  at apply time, over a consolidated bundle. A failed validation **repairs and re-presents the
  same token — never a new chain**.
- **Pre-validate every operator-facing command end-to-end.** A failed operator-presented command
  is an agent defect, not an operator problem.

### 2. P0-2 — FG-4b canonical A4 CPU re-anchor
q2 is FREE (verified via `region-lock status`; the on-disk lock files are harmless vestiges —
**do not delete them**). Run `bench_canonical.sh` per protocol and refresh the stale 24.3 t/s
registry row **via the canonical path only**.

### 3. P0-3 remaining blocker — commit the uncommitted E5 research-tree files
Modified `server_numa_np_sweep.py` + tests, untracked `e5_w0_offline_score.py` + tests, the W0
run-dir score artifacts, and `stage_b_prune_plan.json`. The **Gemma capture gate is a hard W2
blocker** (gemma W0: 43/43 parse failures in all 10 cells without it), so the post-reboot session
cannot start W2 until this is committed. Explicit paths only — never `git add -A`.

### 4. Finish: request the reboot
When 1–3 are done, send a `decision-request` to `coordinator-agent` stating: pre-reboot set
complete, E8 bundle presented (or its exact remaining gate), and **the host reboot is requested**.
Include anything that must be quiesced first — live runs drained, region claims released, stack
state. **Host reboots are operator-only**; you request, you never perform.

---

## POST-REBOOT set — NOT yours, do not start

- **E5 W1–W4** (NUMA×batch 2D grid), with **W2's focused post-fix capture smoke first** — the
  historic Gemma `430/430` parse failures have no raw SSE ledger and are unrecoverable, so the
  smoke must prove the offline scorer sees scoreable answer text before the decision-grade sweep.
- **R1–R4** — withheld until clean decision-grade Stage-B cells exist.
- **P1-3** AutoPilot resume — gated on the P0-1 E8 signature.

## Not yours either (already routed)

- **P2-1 / P2-3** GPU shadow lane → `claude-gpu-lane` (spawned on your 15:43 request). Division of
  labour holds: **Claude builds non-inference, Codex queues inference only.**
- **`stage_b_prune_plan.json` provenance repair** (the stale limitation text you flagged at 15:28)
  → Claude-owned, being routed separately. Do not change frozen manifests or run selection.

## Constraints

- Quiesce-and-drain only, never forcible: releases happen at boundaries (fabric axiom 4).
- Region claims are **acquired** via `region-lock`, never observed (BUS_PROTOCOL rule 7).
- Trust boundaries stay human-only: you present, the operator signs. Neither coordinator-agent
  nor the daemon signs anything.
- Drain and refresh your heartbeat at **every** task boundary; retire `task_id` at terminal state.
- **`requires_ack` is currently decorative** — rule 3 redelivery is unimplemented, so never
  assume an unacked message will be retried.
- Report to `coordinator-agent` via your own outbox.
