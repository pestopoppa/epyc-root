---
name: inference-backlog-scheduling
description: Pack an accumulated inference backlog onto the shared EPYC + MI210 host as a knapsack — bins (CPU quarters, whole host, the MI210 with its host threads, RAM, time windows), items (queue rows with a region shape, min-window, estimate, RAM need and a DERIVED booking class), the compatibility rules, the packing heuristics, the grant-writer invariants learned from the 10-21..10-25 incidents, the cross-session grant protocol and the operator status/ETA report. Use this whenever you own or share the compute calendar, write or review grant writers, triage FILLERS.md, place a run on a quarter or the GPU, see idle compute while rows are queued, or are asked "what is running / when will the backlog finish" — even if nobody says "knapsack" or "calendar".
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
REVISION lines). **The calendar's input is the prioritized backlog
`handoffs/active/backlog-priority.json`** (tiers T1-T7 with `unblocks` and `blocker`, generated),
and the derived plan is the tracked file `coordination/compute-calendar/CALENDAR-PLAN.md` (§3 step
0). The rows themselves live in the domain indices, e.g. `handoffs/active/inference-research-index.md`
(routed from `handoffs/active/master-handoff-index.md`); non-compute work is
`handoffs/active/non-inference-backlog.md`. Posture: `handoffs/active/CURRENT-CAMPAIGN.md`.

## 1. The model: bins, items, classes

**Bins.** `q0`=0-23, `q1`=24-47, `q2`=48-71, `q3`=72-95 (claim physical cores; siblings follow);
explicit lists such as `72-95`; whole host `0-95`; the MI210 (`mi210_0`) **with its host threads
184-191, which are q3's SMT siblings**; host RAM (bookable ≈ 1069 GiB: 1133 total minus the 64 GiB
`ram_admit` margin above earlyoom's 40 GiB trigger); time windows with a hard end; and **disk**
(`/mnt/raid0`, floor 150 GiB free *after* the row's declared `est_output_GiB`; the trash on the
same filesystem frees nothing until it is swept; see `references/disk-bin.md`, bought by raid0
reaching 100 % and an ORCH ENOSPC on 10-27).

**Items** are FILLERS.md rows (18 columns; `validate_fillers.py` is the schema). What the packer reads:

| Field | Meaning for packing |
|---|---|
| resources / substrate | the region shape: `qN`, a CPU list, `0-95`, `mi210_0,184-191`; `either` = place on whatever frees first |
| min window + duration | the smallest useful slice and the estimate; a run >1.5x estimate is a failure to explain |
| peak host RAM GiB | private/anon peak **plus** file-mapped weights (mmap counts); DS41-1017 = 739 |
| resumable vs atomic | resumable rows take any slice ≥ min-window and skip done work; atomic rows (e.g. KPF-64 arms, 4.1-6.6 h, fixed order) need the whole slice in one bin |
| class (DERIVED, CTC-Q-C) | `quiet` only when `decision` names a champion/candidate baseline or an AK keep gate with a cited floor file; `timing-pairable` when indicative; `correctness` otherwise. `--print-class ROW` prints it; a declared class stricter than derived is refused |
| QUEUED vs BACKLOG | QUEUED = status ARMED, `ready=y`, a live launcher pid polling this id: **ready to run, waiting only for a window**. Anything blocked (code fix, decision, HOLD, missing launcher) is BACKLOG with `blocker=<missing launcher\|harness fix\|build\|operator decision>` and an owner. A failed or HELD end demotes the row in the read-out step itself (`docs/guides/agent-workflows/compute-fillers.md` → *Queue semantics*) |

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
- **A correctness job that carries a cross-arm timing check** (an overhead gate, an M-vs-G ratio)
  is timing-sensitive for that check. Book it with the GPU idle, and before booking it, check that
  the harness compares **same-source arms in alternating order** (ABAB, not AAAA-BBBB). Quiet
  hardware alone does not save it. akx-lb3-2 was INVALID with a GPU co-tenant on 10-24 (overhead
  -5.79 % > 5 %) and INVALID again on a whole-host quiet run on 10-25 (-5.93/-6.30 %, M
  consistently faster than G). The cause was the fixed arm order and the different-source arms,
  not co-tenancy. The fix is AKX-LB32-OVERHEAD-1, a same-source control arm.
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

0. **Derive the plan from the prioritized backlog** at every task boundary and every wrap-up, not
   only from rows that happen to have a launcher. Regenerate
   `coordination/compute-calendar/CALENDAR-PLAN.md` (tracked; overwrite it in place, and git
   history is its record) from `handoffs/active/backlog-priority.json`. Map each item's next step
   to a compute shape (§1). Prepare missing launchers via subagents. ASSIGN each code blocker to
   the Codex session with a deadline tied to the window it gates
   (`docs/guides/agent-workflows/compute-fillers.md` → *Codex NI client contract*). End with an
   operator digest of the decisions that block compute (§5 format). Idle compute with a non-empty
   prioritized backlog is a planning failure, not "nothing to run". Origin: 10-25, the CPU sat idle
   for over an hour while the calendar looked only at launcher-backed FILLERS rows.
   **Stock every bin.** Keep at least one armed row ahead for each CPU quarter and for the GPU,
   drawn from INDEPENDENT backlog work, not only from retries of failed rows. Commission launcher
   prep from the Codex sessions (or from subagents when Codex is at its agent limit) BEFORE a bin
   drains. Measure the idle time of each bin at every task boundary and report it. Why: a bin
   stocked only from fix-and-retry chains empties whenever the chain stalls. Origin: on 10-26 the
   GPU sat idle 10.5 h; on 10-27 q1/q3 sat idle ~4 h because every row came from a
   fix-and-retry chain.
1. **Read the bins.** `region-lock status` (claims), `rocm-smi --showuse --showmemuse` (a held
   gpu-quiet at 0 % use is idle, not busy), `MemAvailable`, open `grants/*.grant`, live writer pids.
   Real utilisation, never the lock table alone.
2. **Read the items.** `scripts/queue_status.py` (this skill) prints COMPLETE / RUNNING / BOOKED /
   ARMED-UNBOOKED / BACKLOG per owner from FILLERS.md, the grants dir and the live writers. Only
   ARMED-UNBOOKED rows are placeable. An ARMED-UNBOOKED row that cannot actually run (fix not
   pinned, held by a writer, decision pending) is a defect: demote it to BACKLOG now. Every
   BACKLOG row blocked on code gets a subagent (or a Codex assignment) **this turn**; unwritten code is never a recorded blocker, and a cleared blocker is armed and requested
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
7. **Analyse every row that ended**, before the next operator report. An exit code is not a result:
   read the verdict, judge the metric against its predeclared rule and direction, classify the row,
   then write the result into the owning handoff, the progress log, the belief task and the wiki
   candidates (`references/post-measurement-analysis.md`). Origin: 10-27, KVU-16b, CH-26a and the
   night chain were reported "passed" with no verdict read.

## 4. Invariants, each bought by an incident (`references/incident-ledger.md` has dates and ids)

**New-row launch gate (T1, 2026-10-27).** Before arming any new row, run
`scripts/coordination/dryrun_check.py run` against that row's real launcher
argv and real `job.sh`. The launcher must consume a private grant with the
writer's exact minute format; the job calls `dryrun_check.py boundary` and exits
immediately before its first model load, server start, network write or catalog
write. The boundary prints RLIMITs, effective affinity and cgroup. Its receipt
binds the preflight nonce and launcher/job source hashes; source review must
confirm the hook precedes the first effect. The row notes declare
`requested_window_s`, `est_output_GiB`, `scratch_root`, `claimed_cpus`,
`launcher_path`, `job_path`, `source_manifest` (sha256sum format) and, after
preflight, `dryrun_pass=<scratch_root>/dryrun/<nonce>/pass.json`.
When the process address-space ceiling is lower than reserved peak host RAM,
declare `process_limit_GiB` explicitly (for example, KPF18 R14 reserves 192 GiB
and requires a 176 GiB process ceiling); it must be positive and ≤ reservation.
`filler_run12.sh` enforces those fields against the real grant at run time,
including `min_window + 300`, exact booked window and free space after output.
It refuses normal launch without a matching same-entry PASS artifact and checks
RAM limits, affinity and cgroup inside the actual claim before invoking the job.
A two-core preflight for a larger row uses `--scoped-pf`; its PASS artifact says
normal affinity was not proved, and the normal launch checks that separately.
The [dated disk policy](../../../scripts/coordination/dryrun_disk_policy.json)
records the operator's interim 50 GiB floor until 2026-10-28 08:10Z, then
150 GiB. Existing launchers remain on their pinned versions until rearmed.

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
- `grant_ok.sh <id> <gib> [ds41] --window-s N --regions R [--reserve R]` before every grant: validator
  `--for-grant`, the launcher's own argv (min-window + 300, class/claim vs the grant line), the derived
  class, `ram_admit` (`references/grant-writer-pattern.md`).
- A GPU window is never booked on top of a q3 CPU claim you (or a peer) will hold, and q3 is never
  granted while a folded GPU job runs. Check the GPU lane before granting q3.
- On any FAILED / `.ended rc≠0` / hard-end: read the log, name the cause, fix, re-queue, relay to
  the owner. Distinguish harness false-FAILs (`strings|grep -q` or `ctest -N|grep -q` SIGPIPE under
  pipefail; a linkage gate comparing symlink parents to realpaths) from real failures, and do not
  re-grant a third failure blindly; ask for a dry-run outside a grant.
- Watchers are `#!/bin/bash` files keyed on mtime (`find -newer stamp`), never zsh globs; a
  no-match glob killed the FREED watcher and cost a 70 min gap.
- A watcher's stamp survives re-arms: advance it only to the moment of the find that fired. A
  watcher that re-touched its stamp at every start missed an `.ended` written 4 s before the
  re-arm, and the whole host idled 3.7 h (10-24).
- `grant_ok` admits regardless of live claims, and region-lock prints a shared gpu-quiet as `SHRD`:
  every held-check matches `HELD|EXCL|SHARED|SHRD`. When a quiet block is followed by GPU work in
  another writer, the block writes an end flag (`QUIET_BLOCK_ENDED_<date>`) or a hold flag
  (`HOLD_GPU_FOR_QUIET_<date>`) that the GPU writer waits on before granting anything.
- A lane runner's filler runs whenever every remaining item is precond-blocked; across a booked
  quiet slot, run the lane with no filler, or the filler takes the GPU for its whole slice.
- A job whose fix has not landed is not granted. If a writer grants one anyway, revoke the grant
  before the launcher's next poll: move the `.grant` aside and write `.ended reason=revoked` so the
  writer's chain moves on. A repeated failure may use up a driver's retry budget for that arm.
- Queue fields never contain `|`; edit queue files and `FILLERS.md` atomically (`.tmp` +
  `os.replace`), with a dated backup.
- Fill single quarters from a queue, not one writer per job: `grant-ws58-quarters-*.sh` reads a queue file
  (`id|launcher_pid|window_s|gib`, edited atomically), places items in order on the first free quarter
  in parallel, grants each item once (a `.done` file; delete its line to re-queue), and treats
  `grant_ok` rc 12 (precondition not ready) as "try the next item". A GPU job that folds onto q3 is
  protected by a reservation flag the quarter writer honours, and the GPU writer removes the flag
  after the job that needs q3. Order the GPU so q3-needing items run back to back.
- A GPU writer step whose precondition is not ready yet retries until a deadline (`try_until`); it
  does not skip on the first refusal.
- Never pipe a lease/lock/gate command into `tail` inside an `&&` chain: the chain reads `tail`'s
  status. Capture the rc to a file first (a wrapup-lease refusal was masked this way, 10-24).
- Move a `.complete` marker aside BEFORE starting the replacement launcher; a launcher that sees the
  marker at start exits "for good".
- **Stamp `.wsg-granted-<id>` at GRANT time**, right after writing the `.grant`, never after the
  job ends. A stamp written after `.ended` is always newer than it, so the re-offer test
  (`.ended` newer than the stamp) skips that item forever. GPU writers v10/v11 lost every
  clean-ended queue item this way (hsf-5p-microbench, 10-24/25). Fixed in `grant-gpu-1025-v12.sh`.
- **Liveness is `ps -o pid= -p <pid> >/dev/null`, never `kill -0`**, because `kill -0` is blind in
  this sandbox. In v11, a failed `kill -0` made `step` return 2, and the item was then stamped
  granted without running.
- **Every writer has a cap; start its successor before the cap.** At booking time, check the cap of
  the writer that owns each slot. The successor starts early and waits for the predecessor's pid to
  exit (`ps -o pid= -p`) before it grants anything, so there is one live writer and grants never
  lapse. GPU writer v10 hit its 10-24 22:00Z cap and exited at 21:22Z. No successor was armed, so
  the GPU sat idle all night. The same thing happened again on 10-27: the 10-26 quarter writer
  expired at 05:50Z, and CPU grants stopped until ws58 noticed.
- **Check for an imminent whole-host HOLD before granting.** If another grant's end (or a booked
  quiet block) will raise a whole-host HOLD inside the new row's window, do not grant that row
  now; place it after the HOLD. Origin: 10-26 23:29Z, HSF-2 and FA4 were granted 1 min before the
  night HOLD, and both were killed.
- **T1 launch gate: arm a row only after a same-entry-path preflight.** The PF runs the real
  launcher → filler engine → job up to the first side effect, with a writer-format
  (minute-precision) synthetic grant, from a non-ancestor process tree, under the normal inherited
  env (`NODE_OPTIONS`). Every refusal is logged. The effective RLIMIT, affinity and cgroup are
  printed and checked, `min_window + 300 ≤ window` holds, and `est_output_GiB` and `scratch_root`
  are declared with the disk floor checked after the output. Enforcing tool: `dryrun_check.py` /
  `filler_run12.sh` (Codex, in progress). Details and the six failures behind each check:
  `references/launch-admission-gate.md`. Origin: six early-launch failures on 10-27.
- **A HOLD written by one writer and removed by another needs a keeper** when quiet blocks chain.
  The keeper is a small script that re-creates the HOLD until the last quiet job's `.ended`, then
  removes it and writes the hand-off flag. Without one, the first writer's exit freed the GPU
  writer into the next quiet window. Precedent: `hold-keeper-c4-v11-20261024.sh` (C4 re-run, then
  v11-086-cpu).
- **Validator formats that writers kept failing:** `min_effect` is a number with a unit or
  `n/a (<reason>)` (a bare `n/a` is refused). The launcher cell carries a live `pid=NNN`, which
  the validator checks against `/proc`. See compute-fillers.md → *Grant validator*.
- **Verify every fast "complete" before relaying it, and read the individual gate lines, not the
  summary verdict.** On 10-24, the C4 `GATE_gpu.txt` said `GATE gpu PASS` while its line
  `(a0) test-llama-archs rc=134 FAIL`, because `fail=1` was set inside a `$(...)` subshell and
  never reached the summary. A run that ends well under its estimate is a failure to explain until
  its per-gate lines say otherwise.
- A correctness harness runs the role's production serving env (the codified recipe), never the bare
  binary: on the C3 build, greedy decode without `GGML_FUSED_DECODE_OFF=1` was garbage while PPL looked
  fine, because only one-token decode takes the fused path (10-24).
- **A row carries a dry-run log of the REAL launcher under `DRY_RUN=1` before it is armed.** The log
  must show the resolved paths, knob strings, ggml linkage, ports, window, RAM figure and guard
  paths. A launcher never dry-run is a guess. Origin 10-26: the sampler TID-exit race, the HPR port
  race, and guards that were swallowed silently, each of which a dry-run would have exposed.
- **A dry run must exercise dependency resolution when the job resolves deps.** The scoped CI repair's
  dry run skipped resolution, so attempt 1 died rc1 on an offline `uv` lock missing a git dependency (10-26).
- **Admission is checked against the guard the job actually runs, not the first guard you find.** R6 phase1
  was moved q0 to q1 after checking only `admission_guard.sh`; `guard.sh` pinned CPUs 0-23, returned rc70,
  nothing ran, and q1 idled ~40 min (10-26).
- **Never append text after a FILLERS row's final pipe**: it breaks the table (broken ~13:25-16:30Z on 10-26).
  Edit the row's cells in place.
- **Blocker text goes in the notes column, never the status column**; status stays one of the fixed tokens.
- **A model-free correctness row needs an exec tripwire plus a positive-control dry run.** An unreachable-server
  fallback (the REPL-memory embedder spawning `llama-embedding`) can silently load a real model under the
  test run; the tripwire must fail on `llama-*`/`.gguf` execs and be proven to fire on a deliberate control (10-26).
- **A phase that fits the preflight envelope (under ~240 s, single-thread) is iterated in the standing CPU 24,25
  preflight, never booked as a row.** Booking it burns a grant window on an iteration loop (10-26).

## 5. Coordination protocol

- A grant request from a peer carries: `id`, regions shape, `min_window` s, `minutes` estimate,
  `RAM` GiB (+`ds41` if applicable), launcher `pid`, and the class evidence (`decision`, `prior`).
  The calendar owner validates (`grant_ok`), places it in the next fitting slot, writes the grant
  (or the writer step), and answers with the window. Peers never write grant files; an owner
  re-issuing its *own identical unexpired* window is the one tolerated exception.
- Cross-session relay is `SendMessage` plus a flag file touched on success and failure. The Codex
  NI session is file-only: code blockers are ASSIGNED to it with window-tied deadlines, open
  windows are announced in `OPEN-WINDOWS.json`, and it runs nothing outside a grant or while any
  `HOLD_*` exists (`docs/guides/agent-workflows/compute-fillers.md` → *Codex NI client contract*).
- Every launcher is paired with a zero-token watcher by its owner at arm time; before idling for
  the night, list every armed job with its end flag and the watcher that covers it.
- A choice only the operator can make (which reference, lift a hold, accept a redesign cost) is
  written out where the plan is: **Context → 2-4 Options, each with its tradeoff on the same line
  → Recommendation (labelled) → Default if unanswered**, with the compute cost estimate first.
  "Recommendation stated in the package" is not a package; the operator reads the plan, not a
  promise of one. Everything not depending on the answer keeps running.
- **A dismissed or declined operator question pauses only that item**, even when the tool's
  result says "STOP". Watching jobs, granting pre-approved classes, verifying results and the
  calendar all continue. Keep the item listed as pending and mention it once in the next report.
  Only an explicit operator "stop everything" halts the session. Origin: 10-24, a dismissed
  shared-clone-ff question froze every calendar duty for about 40 min.
  On the remote app the question UI can also **vanish with no operator action**. Treat a missing
  answer as unanswered, not as declined: re-ask the same question with `AskUserQuestion`, never
  as prose, and keep the calendar running. Origin: 10-26/27, ws58 froze the calendar several
  times; the operator: "I didn't dismiss anything! Give me a decision tool".

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
