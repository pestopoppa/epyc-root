# 2026-08-16 — coordinator-agent

Second half of the day. The implementation itself is recorded in the earlier
unsuffixed entry `progress/2026-08/2026-08-16.md` (written before the per-agent
convention was picked up in this session); this file covers everything after it:
the operator ratification run, the reconciliation with the parallel session and
with `origin`, the two defects found in my own work, and the wrap-up.

Owning handoff: `handoffs/active/loop-owned-fleet-implementation.md` (RTG-52).

## Ratification — all five gates signed

The operator ran `artifacts/operator/ratify-loop-owned-fleet-20260816.sh`. Steps
1–5 are done: the alarm channel is live and drill-verified, pilot-02 promoted
under a D9 ack, `INVARIANTS.md` installed, the dead marker retired, and the
worker pool enabled.

**Then enabled-and-paused, at the operator's instruction, because I was wrong
about the intent.** The ratification script's step 4 flipped `worker_pool.enabled`
to true, and the operator's response was unambiguous: *"so the loop is live
already? I explicitly said that I wanted to be able to launch it manually
myself!"* I stopped, measured the damage before claiming there was none — one row
dispatched, parked by the screener, no worker spawned, no commit written — and
paused the pool (`d18290ff`). The lesson is not "ask more"; it is that a
ratification script that flips a runtime flag is *deploying*, not *approving*,
and those must not travel in one command.

`scripts/coordination/fleet_control.sh` is the consequence: the single
deploy/stop handle the `/coordinator-agent` skill was always meant to expose
(`ade9a3b0`), wired into skill section 0b-bis.

## Two defects in my own work

**D9 had an unguarded path.** The gate I built lived at *promotion* time only —
`promote_lane.py`. A session committing directly to `scripts/coordination/**` in
the shared clone walked straight past it. A control with a bypass is not a
control, so `scripts/hooks/check_d9_loop_plane.py` now enforces it at commit time
(`12c4a67f`); it demands a `D9-ack:` trailer or `EPYC_D9_ACK`, and exempts tests.

**PD-1: the pool could not reach its own bound.** `compute_advice` skipped any
agent already present in a set of busy owners. Correct for a tmux main — one
session, one task. Wrong for the pool, which is a *single* roster identity
(`workerpool`) fronting four runners, so the first assigned row made the whole
pool read busy and throughput capped at one row. `max_concurrent_workers: 4` was
unreachable through the daemon.

The pilot's three concurrent workers were dispatched by hand with
`--pilot-override`, straight past the picker — so the measured throughput never
exercised this path, and reporting it as evidence of pool concurrency would have
been exactly the "dispatch reported as utilisation" error this whole program
exists to end.

Fixed by replacing the `busy_owners` set with an `inflight_by_owner` count
compared against `_owner_capacity()`, which is 1 for a session and, for an exec
pool, the configured concurrency **floored by the lanes that exist on disk**
(`6958867c`). Two workers in one worktree is the shared-clone commit-sweep
hazard, so scaling past the lanes present has to be a deliberate step.

**My fix had two defects of its own, and the second one is the useful one.** The
first test suite I wrote *passed with the bug reinserted* — isolated
`_owner_capacity` unit tests plus source greps, neither of which drives the loop
that actually decides. A guard that survives its own mutation is not a guard. I
added `PickLoopBehaviourTests`, which drives `compute_advice` end to end and
asserts the pool is picked for a *second* row while already holding one — and
that test immediately caught that I had passed the agent *state* dict where the
roster *entry* was wanted, collapsing capacity back to 1.

## P3-4 landed

The fleet-gate predicate swap (`860fac3d`), with its tests, in one commit under a
D9 ack. It **deletes** the halt rather than softening it and carries an explicit
`halt_assignment: False`, so reintroducing one means changing a stated value
rather than omitting a line. Zero live workers — the normal idle state of an
ephemeral pool — no longer reads as an emergency. 9 tests → 49; six mutations all
caught; the quiet-night walkthrough is 480 ticks with zero alarms.

## Reconciliation

**With the parallel session** (`stage-3-action-plan`): coordinated directly over
the bus. `agents/` duplicates removed, the RTG-51 policy tier rewritten for the
headless auditor, and their disclosed clobber verified harmless — the lost edits
were a half-built copy of a feature the lane had already finished, and the test
that proves it passes 11/11 and is now tracked.

**With `origin`**: `origin/main` and `lane/auditor` are the same tip; a merge
produced 21 conflicts across a 92/12 newer split, so per-file forward-port was
the only correct mechanism — 39 lane-only files taken wholesale (`7370e1dc`),
then the 12 lane-newer files finished individually with three-way merges
(`45d49f23`). Nothing was ever at risk: `refs/heads/lane/auditor` exists on
origin at the same tip, so those commits are durably named there regardless.

One forward-port overreached and resurrected 8 archived persona files; caught and
dropped (`99c4f49c`), P1-5's archival stands.

## Wrap-up (operator cadence)

Split-identity fix, index pruning, and the wiki compile sweep — recorded in the
wrap-up output and in RTG-52. New this session: `index_state.py --check` now
carries a **SPLIT IDENTITY** check, because four handoffs existed simultaneously
in `active/` and `completed/` and `--check` was blind to all four. One of them
mattered: `fable5-window2-findings-05` had been archived on 2026-08-13 while it
still held a live go/no-go, and the active copy restored today is the newer one.

## Deferred, with reasons

- **PN-1/2/3 remain deliberately unbuilt.** They are pulled by need and no
  measured consumer exists yet. Building them now would be speculation dressed as
  progress.
- **P4-1 is time-gated**, not blocked: a 7-day observation window whose harness
  (`fleet_metrics.py`) is built and already running.
- **The pool stays paused.** Resuming is the operator's, and PD-1's fix means
  resuming now buys genuine four-way concurrency rather than the serialized
  throughput it would have bought this morning.
