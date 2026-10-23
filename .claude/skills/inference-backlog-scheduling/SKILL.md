---
name: inference-backlog-scheduling
description: Pack an accumulated inference backlog onto the shared EPYC + MI210 host as a knapsack — bins (CPU quarters, whole host, the MI210 with its host threads, RAM, time windows), items (queue rows with a region shape, min-window, estimate, RAM need and a DERIVED booking class), the compatibility rules, the packing heuristics, the grant-writer invariants learned from the 10-21..10-23 incidents, the cross-session grant protocol and the operator status/ETA report. Use this whenever you own or share the compute calendar, write or review grant writers, triage FILLERS.md, place a run on a quarter or the GPU, see idle compute while rows are queued, or are asked "what is running / when will the backlog finish" — even if nobody says "knapsack" or "calendar".
---

# Inference Backlog Scheduling

The host is one 96-core EPYC (4 quarters q0-q3, SMT siblings c+96), one MI210, ~1.1 TB RAM, and a
clock. The backlog is a queue of measurement and build items that each need a *shape* of those
resources for a *minimum* time. The job is a knapsack: keep every bin full of admissible items until
the backlog is empty, without ever perturbing a decision-grade measurement. Idle hardware with queued
work is a reportable failure, not a resting state.

Canonical protocol (read it once per session): `docs/guides/agent-workflows/compute-fillers.md`.
Live state lives outside the repo: queue `/mnt/raid0/llm/tmp/compute-flags/FILLERS.md`, grants
`compute-flags/grants/`, calendar `/mnt/raid0/llm/tmp/compute-calendar-<date>.md` (append-only
REVISION lines). The backlog these items come from is the inference domain index
`handoffs/active/inference-research-index.md` (one `INF-NN` row per handoff; the master index
`handoffs/active/master-handoff-index.md` routes to it); non-compute work is
`handoffs/active/non-inference-backlog.md`. Posture: `handoffs/active/CURRENT-CAMPAIGN.md`.

## 1. The model: bins, items, classes

**Bins.** `q0`=0-23, `q1`=24-47, `q2`=48-71, `q3`=72-95 (claim physical cores; siblings follow);
explicit lists such as `72-95`; whole host `0-95`; the MI210 (`mi210_0`) **with its host threads
184-191, which are q3's SMT siblings**; host RAM (bookable ≈ 1069 GiB: 1133 total minus the 64 GiB
`ram_admit` margin above earlyoom's 40 GiB trigger); and time windows with a hard end.

**Items** are FILLERS.md rows (18 columns; `validate_fillers.py` is the schema). What the packer reads:

| Field | Meaning for packing |
|---|---|
| resources / substrate | the region shape: `qN`, a CPU list, `0-95`, `mi210_0,184-191`; `either` = place on whatever frees first |
| min window + duration | the smallest useful slice and the estimate; a run >1.5x estimate is a failure to explain |
| peak host RAM GiB | private/anon peak **plus** file-mapped weights (mmap counts); DS41-1017 = 739 |
| resumable vs atomic | resumable rows take any slice ≥ min-window and skip done work; atomic rows (e.g. KPF-64 arms, 4.1-6.6 h, fixed order) need the whole slice in one bin |
| class (DERIVED, CTC-Q-C) | `quiet` only when `decision` names a champion/candidate baseline or an AK keep gate with a cited floor file; `timing-pairable` when indicative; `correctness` otherwise. `--print-class ROW` prints it; a declared class stricter than derived is refused |
| QUEUED vs BACKLOG | QUEUED = status ARMED, `ready=y`, a live launcher pid polling this id. Anything else is BACKLOG with `blocker=<missing launcher|harness fix|build|operator decision>` and an owner |

## 2. Compatibility rules (what may share a bin)

- **Quiet host** (gpu-quiet exclusive + all of 0-95, nothing else running) is earned only by
  decision-grade baselines and AK keep gates. Indicative timing shares with a labelled GPU job (and
  the GPU-on/off difference is itself a wanted measurement). Correctness shares with anything but
  CPU timing. Builds are correctness.
- **The q3 fold.** `region-lock --cpu-list 184-191` folds into a claim on all of q3. A folded GPU
  job conflicts with any q3 or 0-95 CPU claim, and a q3 build makes the MI210 idle behind it. A
  GPU-only job claims gpu-quiet with **no CPU region** and tasksets 184-191 itself (`filler_run7+
  --class gpu --no-fold-siblings`); region-lock's own `--no-fold-siblings` on an SMT-only list is
  refused ("maps to no regions"). Decide per GPU row: *no-fold* (co-runs with whole-CPU
  correctness) or *folded* (needs q3 empty; keep q3 free while it runs).
- **Co-residency cost, measured 2026-10-22 (gpu-cpu-noise):** with every GPU thread pinned to
  184-191, CPU decode -0.7..-1.05 %, prefill -4.3..-4.8 %, variance not inflated; on the SMT
  channel (88-95 vs 184-191) prefill -9.6 %. Whole-host CPU models eat it; partial-host models go
  off q3 when a GPU job is live. One ROCr thread escapes `taskset`; pin with
  `HSA_OVERRIDE_CPU_AFFINITY_DEBUG=0` (P1 PASS 10-23) or `taskset -a -p` after health.
- **RAM is a bin.** `ram_admit.sh <peak_gib> [ds41]` before every grant and every model load.
  At most ONE DS41-class (≥200 GiB; 1017 = 739 GiB) server host-wide: `ram_admit 739 ds41`
  refuses while any process maps a 1017 shard. Keep ≥20 min between DS41 handovers.
- **Launcher class must match the grant shape it will receive.** `--class cpu+gpu` refuses a
  `regions=0-95` grant (no `mi210_0` token, `.ended rc=2`, slot lost). A CPU timing job that needs
  the GPU quiet is `--class cpu --gpu-quiet exclusive --claim-cpus 0-95` (filler_run8). Dry-check
  the launcher's region parser against the exact grant line before arming.

## 3. Packing procedure

Run this loop at every task boundary and on every watcher event (`event-watch-ws58.sh` fires on
`*FAILED*`, `*.ended`, `*_ENDED`, `*_FREED` under `/mnt/raid0/llm/tmp`).

1. **Read the bins.** `region-lock status` (claims), `rocm-smi --showuse --showmemuse` (a held
   gpu-quiet at 0 % use is idle, not busy), `MemAvailable`, open `grants/*.grant`, live writer pids.
   Real utilisation, never the lock table alone.
2. **Read the items.** `scripts/queue_status.py` (this skill) prints COMPLETE / RUNNING / BOOKED /
   ARMED-UNBOOKED / BACKLOG per owner from FILLERS.md, the grants dir and the live writers. Only
   ARMED-UNBOOKED rows are placeable. Every BACKLOG row blocked on code gets a subagent **this
   turn**; unwritten code is never a recorded blocker, and a cleared blocker is armed and requested
   in the same turn as it clears.
3. **Place, largest-and-stiffest first.** Order: quiet items into the windows they alone can use
   (night, early morning), then atomic long items wholly inside one bin (a 6.6 h arm on q0 for the
   night), then builds *before* the tests that `--precond-cmd` on them, then resumable fillers to
   soak every remaining gap. Prefer parallel lanes: q0, q1, q2 each run their own chain while a
   folded GPU chain owns q3 + MI210, or a no-fold GPU chain co-runs with a 0-95 correctness block.
4. **Size every window** as `end ≥ start + min_window + poll(45 s) + 60 s`, in practice
   `min + 300 s`. A window equal to the min is refused (`rc=3`) because the launcher sees the grant
   up to one poll late. Cap at the bin's hard end and skip if the cap leaves less than that.
5. **Write the writer**, one per region set, as a versioned script
   (`references/grant-writer-pattern.md`): `grant_ok.sh` before each grant, claim-wait on *only the
   regions this grant needs*, skip ids that are `.complete` or whose launcher pid is dead, wait for
   `.ended` newer than the grant's start, then the next step. Book the chain to the END of the
   night with backlog depth; the owner session can disappear (rate limit 22:3x-05:5xZ on 10-22 left
   4-5 h idle after the last queued job).
6. **Record** one calendar `REVISION <HH:MM>Z <date>:` line per placement, failure and fix; it is
   the audit record. Then refresh the heartbeat and wrap up the task boundary.

## 4. Invariants, each bought by an incident (`references/incident-ledger.md` has dates and ids)

- Window ≥ min-window + 300 s. Exactly-equal windows were refused three times in two days
  (kpf60 10-22, rtepfx2 10-23, ch28 v1 near-miss) despite the lesson being written after the first.
- Grant only when the previous holder's claims and flocks are *released*, not when its `.ended`
  appears; poll `region-lock status` for the needed regions until none is HELD/EXCL/SHARED.
- A claim-wait checks only the regions the next grant needs; a whole-status wait stalled a CPU
  block behind a co-running GPU-only claim (block v2 → v3).
- One live writer per region set. Before arming vN+1, kill vN by its captured pid and list every
  other live writer (including conditional early-trigger branches) that can grant the same regions;
  an old writer's early branch double-granted q0-q3 under a quiet noise run and aborted it.
- Fallback branches (`or <clock>`) fire only if the predecessor no longer holds the regions.
- A writer with an `EXIT` trap that writes a done-flag is stopped with SIGKILL, so the flag is not
  written early. Never edit a running `.sh` (writer, launcher or job): write vN+1 and swap it in.
- Never grant an id that is `.complete`, or whose work is known done while its poller still polls
  (dhm-mining-full, df2-ubatch-census on 10-23). A stale poller takes a re-written grant.
- `grant_ok.sh <id> <gib> [ds41]` before every grant: validator `--for-grant` plus `ram_admit`.
- A GPU window is never booked on top of a q3 CPU claim you (or a peer) will hold, and q3 is never
  granted while a folded GPU job runs. Check the GPU lane before granting q3.
- On any FAILED / `.ended rc≠0` / hard-end: read the log, name the cause, fix, re-queue, relay to
  the owner. Distinguish harness false-FAILs (`strings|grep -q` or `ctest -N|grep -q` SIGPIPE under
  pipefail; a linkage gate comparing symlink parents to realpaths) from real failures, and do not
  re-grant a third failure blindly; ask for a dry-run outside a grant.
- Watchers are `#!/bin/bash` files keyed on mtime (`find -newer stamp`), never zsh globs; a
  no-match glob killed the FREED watcher and cost a 70 min gap.

## 5. Coordination protocol

- A grant request from a peer carries: `id`, regions shape, `min_window` s, `minutes` estimate,
  `RAM` GiB (+`ds41` if applicable), launcher `pid`, and the class evidence (`decision`, `prior`).
  The calendar owner validates (`grant_ok`), places it in the next fitting slot, writes the grant
  (or the writer step), and answers with the window. Peers never write grant files; an owner
  re-issuing its *own identical unexpired* window is the one tolerated exception.
- Cross-session relay is `SendMessage` plus a flag file touched on success and failure.
- Every launcher is paired with a zero-token watcher by its owner at arm time; before idling for
  the night, list every armed job with its end flag and the watcher that covers it.
- A choice only the operator can make (which reference, lift a hold, accept a redesign cost) is
  written out where the plan is: **Context → 2-4 Options, each with its tradeoff on the same line
  → Recommendation (labelled) → Default if unanswered**, with the compute cost estimate first.
  "Recommendation stated in the package" is not a package; the operator reads the plan, not a
  promise of one. Everything not depending on the answer keeps running.

## 6. Status / ETA report (the format the operator asked for)

```
STATUS <HH:MM>Z — per session (ws58 | f8 | 3c4ca599 | 7b | …)
  COMPLETED      id (rc, time) …
  RUNNING        id  regions  start→end  (grant)            — one line each
  BOOKED         id  regions  planned window  writer vN pid — in a live writer, not yet granted
  ARMED-UNBOOKED id  shape  min-window  RAM                — placeable now
  BACKLOG        id  blocker=<kind>: <one line>  owner      — not placeable
IDLE NOW: <bins with no claim and no grant>  (must be empty or explained)
CRITICAL PATH: <the chain whose last end is latest> → ETA <HH:MM>Z <date>; slack on other lanes
RAM ledger next 24 h: peak concurrent GiB per block (never two DS41-class items in one row)
```

`scripts/queue_status.py [--owner X] [--json]` produces the first five sections read-only; the
critical path and the RAM ledger come from the writers' chains and the row RAM figures.

## When not to apply this skill

A single run on an otherwise empty host still needs a FILLERS row, a grant and `ram_admit`, but
not the packing loop. Operator-booked windows (noise experiments, ratification baselines) are
fixed points the packer works around, never re-opens.
