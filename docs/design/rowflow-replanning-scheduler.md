# Rowflow re-planning scheduler (dynamic knapsack): design and offline evaluation (2026-11-24)

**Status:** PROPOSAL. It was evaluated offline only. No live file, keeper, `rowflow.py` or grant was touched.
**Owner:** pipeline-mgmt.
**Simulator:** `/mnt/raid0/llm/tmp/pm-knapsack-sim-20261124/`. `trace.py` reconstructs the trace and `sim.py` runs the strategies. Results are in `results.json`, `sens.out`, `starvation.json`, `bound_noquiet.json` and `bench.json`. `report.py` renders the tables below from those files, so the numbers in this doc are generated, not transcribed.

## 1. The ask and the short answer

The operator, on 2026-11-24:

> "the sense that I'm getting is that the scheduler never reconsiders its scheduling. As new jobs get added to the
> queue, the scheduler should be allowed to reshuffle order of claims around like a dynamic knapsack problem to
> maximize churn throughput"

**The sense is correct.** `rowflow.py allocate()` is greedy per tick. It places what fits in `plan_order` and never revisits a placement. Today the reconsidering was done by hand. Owners issued 8 STOPs to undo keeper placements (10:45, 11:16, 11:26, 11:38, 11:42, 12:45, 15:04 and 15:52Z; see section 2). Four further STOPs were supersessions: c21-fold-cpu r1/r2/r3 and c21-gpu27b-identity-r2. Five of those placements were made at the moments examined in section 9.

**The answer has three parts.**

1. **On the replay with exact estimates, a reservation captures the urgent-row gain.** Today's trace was replayed without human STOPs.
   - The reservation fix being landed now (B: EASY backfill, depth 1, uncapped) cuts the c21-fold-cpu-r2 wait from 269 to 3.5 min.
   - It moves the C21 CPU gate from 16:39Z to 11:39Z. The real run reached 14:44Z, and only through owner STOPs.
   - **But under ±30 % estimate noise B is the worst strategy.** Its urgent mean wait is 53 ± 32 min, against 44 for greedy. Its weighted work to 24:00Z is 132 against 151. A depth-1 reservation computed from wrong estimates over-holds lanes.
2. **The re-planner (C) is better and robust.** These are ±30 % noise numbers, 8 seeds, mean ± sd:
   - Weighted work to 16:00Z is 116.1 ± 3.1, against 106.8 ± 9.3 for A and 98.9 ± 12.0 for B.
   - Urgent mean wait is 21 ± 8 min, against 44 ± 10 (A) and 53 ± 32 (B).
   - CPU idle-while-queued is 44.5 ± 0.8 quarter-hours, against 48.8 (A) and 70.1 (B).
   - To 24:00Z, C equals greedy within noise: 152.2 ± 2.6 against 150.6 ± 2.2.
   - On the replay, the C21 GPU step-C row finishes at 14:58Z under C and 16:40Z under A and B (actual: 15:29Z).
   - The solver costs 55 ms mean per state change against a 120 s tick.
   - Its one regression is 1.0 ± 1.3 BUILD-LANE quiet collisions per day, against 0.1.
3. **Most CPU idle is not a packing problem.**
   - QUIET-SERIAL is host-wide (`QUIET_NUMA_SIDES` = one side), and quiet-host rows refuse any loud grant anywhere on the host. Together they serialize almost every AK CPU row.
   - With those two rules switched off, greedy A's CPU occupancy to 16:00Z rises from 90 to 136 quarter-hours, and idle-while-queued falls from 49 to 3.
   - No ordering recovers those ~46 quarter-hours. Only a change to the quiet model does (section 10).

**Recommendation:** section 11.

## 2. What the keeper does today (from the 2026-11-24 log)

- `plan()` is a pure per-tick fixpoint. Candidates come in `plan_order` order (rank < 10 first, then starved lane, then rank). The first fitting option is taken.
- The only look-ahead is the reservation family: `rank_reservation`, DRAIN, RANK-HOLD, QUIET-RESERVE, QUIET-URGENT-PENDING and BACKFILL-IF-FITS. Each is a hand-coded special case of "hold regions for a better row".
  - `rank_reservation` is capped at `DRAIN_MAX_WAIT_S = 3600`. Its horizon T is the latest end of ANY running grant, not of the regions the waiting row needs.
  - At 11:35 and 11:39Z, c21-fold-cpu-r3 (rank 9) was RANK-SKIPped "needs busy regions until 13:56Z (> 3600s)". 13:56Z was the GPU grant's end, which c21-r3 did not need.
- A row the quiet gate removes reserves nothing. At 11:20Z, c21-r3 was refused for "foreign busy 31 % on q3" (light claims and pytest on 84-87; its grant includes c72-87). ak-specpit1-t1p100-r4 (rank 40, 6.4 h) then took q0.
- The humans were the re-planner. The owner STOPs undid keeper placements:

| STOP (Z) | row stopped | why |
|---|---|---|
| 10:45 | aa-calibration-q-a3b (rank 60, 4.6 h) | make room for c21-fold-cpu-r2 |
| 11:16 | rka-a3b-d-remeasure-r5 (rank 60) | paused for the C21 gate |
| 11:26 | specpit1-t1p100-r4 (rank 40, 6.4 h) | taken at 11:20 ahead of c21-r3 |
| 11:38 | aa-calibration-c18-r3 (rank 60, 6.9 h) | taken at 11:35 ahead of c21-r3 |
| 11:42 | specpit1-t1p095 (rank 40, 19.8 h) | taken at 11:39 ahead of c21-r3 |
| 12:45 | cdr-a3b-q4kv-32k (rank 45) | paused for the C21 gate |
| 15:04 / 15:52 | specpit1-t1p095-r2 / -r3 | superseded by r3 / re-fill q1+q2 around a build claim |

## 3. Formulation

**Bins (tokens):**
- `q0`, `q1`, `q2` (cores 0-71). These are the CPU pool: multi-quarter rows are q0-q2 only, and today every CPU grant landed there.
- `q3` = 72-87.
- `H` = the GPU host lane, 88-95 plus 184-191.
- `G` = the MI210.
- RAM: 1069 GiB bookable with a 64 GiB margin.

GPU rows take {G, H}. A whole-host `0-95` row takes {q0, q1, q2, q3, H}, so it also blocks the GPU, exactly as live: akx-all-13a "needs q0,q3 until 13:56Z".

**Items** are rows not yet started (`epyc.row.v3`). Each carries:
- `options`: the token sets from regions, any-of or multi-quarter(n);
- `est` (`estimate_s`; `book_s` is used only by A, as live) and `resumable` (pro-rata credit, as opposed to atomic credit);
- `rank`, from which `w(rank)` is derived;
- its quiet class, derived as the keeper does:
  - `host` when the row declares `requires_quiet_host` or `quiet_guard_regions`;
  - `serial` for an AK CPU row without an opt-out;
- `loud`: a non-light build claim, a host-shape row, or `busy_fraction >= 0.6`;
- `exclusive_cpu` (rank <= 10);
- its release time and its announce time.

Two other item kinds:
- **GPU smokes** are GPU items placed first (SMOKE-SLOT). A GPU row is released by its smoke.
- **Build claims** are exogenous. They take the first free quarter immediately. After 900 s refused (BUILD-LANE) they ignore the quiet rules.

**Constraints.** All strategies use the same `conflict()`:
- token disjointness;
- QUIET-SERIAL: at most one quiet row on the host;
- quiet-host rows versus loud items, both ways, host-wide;
- EXCLUSIVE-CPU-HOLD: no new CPU row while an `exclusive_cpu` row runs;
- the GPU is exclusive;
- RAM;
- **no pre-emption of started rows** (C' relaxes this at unit boundaries, at a stated cost).

**Objective (C).** C maximizes, over the next 6 h:

  `sum_i  w(rank_i) * age_i * size_i * done_i(s_i) * (1 - 0.5*(s_i - now)/6h)  -  lateness_i  -  lock_i`

The terms are:
- **`w(rank)`**: 4 for rank < 10, 2 for 10-29, 1 for 30-59 and 0.5 for 60 and above.
- **`size`**: the number of quarters for CPU rows, and **3 for a GPU row** (one GPU-hour is valued as three quarter-hours, because the MI210 is a whole bin). The reported "rank-weighted work" uses the same convention, and lane-split numbers are in `results.json`.
- **`done`**: the work inside the horizon. Resumable rows earn it pro-rata; atomic rows earn it only if they fit whole.
- **`age = 1 + waited/8h`**: smooth aging.
- **`lateness`**: urgent rows (rank < 10) have a soft deadline of release + 30 min, and pay `2*w*size` per hour beyond it.
- **`lock`**: the expected urgent lateness that a placement imposes on its lane. It is `24 * rho_lane * max(0, d - 0.5h)^2 / 2`, where `d` is the row's remaining length inside the horizon and `rho_lane` is the urgent releases in the trailing 2 h plus announced urgent rows, divided by 2 h.
- A placement whose net value is negative is left unplaced (deferred), unless it is a smoke, urgent or pinned.

## 4. Algorithm and complexity

**Serial schedule generation (SGS) over an order, plus bounded local search.**

- **Placement.** Given an order, each item is placed at its earliest feasible start among the event points {max(now, release, gate), the est-ends of running and already-placed intervals}. Placement is exact and uses no time grid.
- **Scoring.** The schedule is scored with the objective above.
- **Seeds:**
  - the incumbent order, with new rows inserted by rank;
  - rank order;
  - WSPT (`w*size/remaining`);
  - urgent first, then WSPT;
  - urgent first, then largest first.
  
  Smokes, urgent rows and pinned rows are always first, in that order.
- **Local search.** Random swap or insertion moves, keeping improvements, until 400 evaluations or 150 ms.
- **Commit.** Only items whose planned start is now are committed. Each is re-checked with the live `conflict()` before it starts.

**Complexity.** One SGS evaluation is O(n * k * m): n items, k candidate start points (at most n + the running rows), m placed intervals. That is O(n^3) in the worst case, and the search multiplies it by the evaluation budget.

Measured costs:
- **Replay:** at most 28 rows were planned at once. A solve took 46 ms mean, 149 ms p95 (the 150 ms budget cap) and 180 ms max, over 247 solves in 24 h.
- **Synthetic 20 / 40 / 60 rows:** one evaluation takes 0.3 / 0.7 / 1.5 ms, and a full 400-evaluation solve 156 / 367 / 669 ms. At 60 rows the full budget does not fit 150 ms. The search then stops at the budget with the best order found so far, which is never worse than the seeds, so the cost stays bounded.

## 5. Re-plan triggers

C re-solves on any **state change**, where state is a signature of (pending set, running set and their est-ends):
- a row released (smoke PASS / publish);
- a successor announced (a `supersedes` row is visible while its predecessor runs);
- a row or claim ends (`.ended`);
- a build claim starts;
- a row is withdrawn or superseded;
- a running row passes its est-end (the est is extended and the plan re-solved);
- a quiet-gate block clears.

The 120 s keeper tick reuses the cached plan when the signature is unchanged and only commits rows due now. In the replay that was 247 solves over 24 h.

## 6. Hysteresis and anti-starvation

- **Commit only "start now".** Everything else is freely revisable; nothing not yet started is ever promised.
- **Incumbent stickiness.** A new order replaces the incumbent only if it improves the objective by more than 1 %. Re-solves after small changes therefore keep the same plan.
- **Bump counter.** A row's planned start slipping by more than 15 min between consecutive plans counts as one bump.
- **Anti-starvation bound.** A row is **pinned** after 6 bumps or after 12 h waiting. A pinned row is placed straight after smokes and urgent rows, in release order, and is exempt from the negative-value deferral. The 8 h aging term means most rows never reach the pin.
  - Replay: the maximum non-urgent wait was 905 min under C, against 1009 under A and 1037 under B (p90: 687 / 660 / 755 min).
  - 17 rows were pinned (all 12-hour waits on this serial-quiet day), and the maximum was 18 bumps. That count is why the bump pin exists.
- **An earlier version pinned after 4 h, and that was too aggressive.** Under this quiet model the median row waits about 4-6 h in every strategy. A 4 h pin pinned 30 rows and turned C into FIFO, falling below A on weighted work. The pin has to sit above the typical wait.

## 7. How C composes with the reservation fix (B) and the claim queue

- **B is C's fallback, and the place where C plugs in.** B is the degenerate case of C: today's order with a depth-1 head reservation. C replaces the reservation *family* (rank_reservation, DRAIN, RANK-HOLD, QUIET-RESERVE, QUIET-URGENT-PENDING) with one plan.
- **Integration.** C emits a plan. B's single admission queue commits C's "start now" set and also enforces the reservation for C's first planned-but-blocked row. If the solver times out, throws or returns a plan that fails `conflict()`, the keeper runs B unchanged.
- **Build claims stay out of the plan.** They are short, immediate and operator-blocking. The plan sees running claims at their declared minutes.
  - The other agent's claim-cost rule should feed C's expected-build-arrival rate.
  - Variant **C+b** prices expected build arrivals into quiet-host placements (cost 6 per expected collision). It cut collisions to 1 but cost urgent wait (37.7 vs 22.7 min), so it is not in the base recommendation.
  - Collisions here mean BUILD-LANE overrides beside a quiet-host row.
- **The idle-autopilot rules are unaffected.** They act on running grants, not on placement.

## 8. Simulator and results

**How the trace was built:**
- **Sources:** today's keeper log from 00:00Z to 16:00:52Z, plus `ready/` (and `.withdrawn/` for superseded manifests), `dryrun/<id>/PASS.json`, `grants/*.ended` (with the `.autorequeue/` and `.resume/` segments) and `grants/build-*.build.json`.
- **Scope:** 64 rows, 34 GPU smokes (including 6 failed smokes seen holding the device) and 8 loud build claims (light 84-87 claims touch no q0-q2 quarter). 3 rows were already running at 00:00Z.
- **Durations:** actual run time where a row completed. A row that ran and was then superseded is real but wasted work: actual time, no credit. Otherwise the estimate is used.
- **Supersession chains:** a successor is released at the predecessor's *simulated* end plus the human lag observed today.
- **Release times:** CPU rows release at smoke PASS (smokes run on SMT siblings). GPU rows release when their simulated smoke ends.
- **Dropped rows:** rows superseded before they ever ran, and rows that never passed a smoke.
- **No human STOPs are simulated.** This is deliberate: it is what the scheduler alone would do.

**Calibration (A against the real day, to 16:00Z):**
- CPU busy: 90.3 against 86.0 quarter-hours.
- CPU idle-while-queued: 49.2 against 52.9 quarter-hours.
- Rows completed: 27 against 27.
- GPU idle-while-queued is under-modelled: 0.02 h against 2.0 h real. Live GPU smokes held the device for their budget (up to ~1 h), whereas the sim books their measured `elapsed_s`. Every strategy shares this bias.

**One trajectory is chaotic.** A single different decision cascades through the chains, so the ±30 % noise sweep is the evidence. The baseline replay is the anecdote.

### Baseline replay (estimates as published, actual durations)

| metric | actual (log) | A | B | C | C' | C-nolock | C+b |
|---|---|---|---|---|---|---|---|
| rows completed by 16:00Z | 27 | 27 | 28 | 27 | 28 | 27 | 27 |
| rows completed by 24:00Z | - | 46 | 45 | 46 | 44 | 46 | 45 |
| rank-weighted work to 16:00Z (wQh) | - | 104.7 | 110.2 | 117.0 | 117.1 | 117.0 | 116.4 |
| rank-weighted work to 24:00Z (wQh) | - | 148.2 | 145.9 | 151.4 | 152.2 | 151.4 | 150.9 |
| CPU q0-q2 busy to 16:00Z (Qh) | 86.0 | 90.3 | 83.0 | 96.1 | 95.5 | 96.1 | 94.1 |
| CPU idle while CPU work queued to 16:00Z (Qh) | 52.9 | 49.2 | 56.5 | 43.3 | 43.4 | 43.3 | 45.3 |
| CPU idle while queued to 24:00Z (Qh) | - | 133.9 | 152.3 | 107.2 | 106.6 | 107.2 | 109.0 |
| GPU idle while GPU work queued to 16:00Z (h) | 2.0 | 0.02 | 0.02 | 0.02 | 0.02 | 0.02 | 0.02 |
| urgent (rank<10) mean wait to 16:00Z (min) | - | 47.5 | 25.2 | 22.7 | 22.7 | 22.7 | 37.7 |
| wait c21-fold-cpu-r2 (min) | 35.7 | 268.7 | 3.5 | 1.2 | 1.2 | 1.2 | 0.5 |
| wait c21-fold-cpu-r3 (min) | 26.1 | 47.1 | 12.3 | 12.3 | 12.3 | 12.3 | 0.5 |
| wait c21-fold-cpu-r4 (min) | 15.2 | 0.5 | 0.5 | 0.5 | 0.5 | 0.5 | 0.5 |
| C21 CPU gate (fold-cpu-r4) done | 14:44 | 16:39 | 11:39 | 11:37 | 11:37 | 11:37 | 15:27 |
| C21 GPU step-C (stepc-r3) done | 15:29 | 16:40 | 16:40 | 14:58 | 15:03 | 14:58 | 14:58 |
| quiet collisions to 24:00Z | 7 CONTAMINATION lines | 0 | 0 | 0 | 3 | 0 | 1 |
| solver ms/solve mean / p95 / max | - | - | - | 46.2 / 148.4 / 164.3 | 48.1 / 149.2 / 201.4 | 48.8 / 150.1 / 150.7 | 47.0 / 138.7 / 150.3 |
| solves (state changes) / max rows planned | - | - | - | 247 / 28 | 244 / 27 | 247 / 28 | 249 / 27 |
| non-urgent wait max / p90 to 24:00Z (min) | - | 1009 / 660 | 1037 / 755 | 905 / 687 | 905 / 687 | 905 / 687 | 905 / 687 |

wQh = rank-weighted quarter-hours (`w(rank)` x quarters; a GPU-hour counts 3). "Done" times are simulated. A wait is measured from the row's own simulated release, and the chains shift, so compare the gate completion times, not only the per-row waits. "7 CONTAMINATION lines" are foreign processes (a research-intake python, claude, firefox), not keeper placements.

### Sensitivity (±30 % noise on every planner estimate and on every unknown duration, 8 seeds)

| +-30 % noise, mean (sd) | A | B | C | C' | C-nolock | C+b |
|---|---|---|---|---|---|---|
| rows completed by 24:00Z | 46.12 (1.17) | 43.38 (1.32) | 44.62 (1.93) | 44.5 (1.41) | 43.5 (3.28) | 43.88 (1.69) |
| rank-weighted work to 16:00Z | 106.84 (9.28) | 98.92 (11.95) | 116.14 (3.12) | 115.98 (2.92) | 110.92 (8.96) | 107.81 (10.7) |
| rank-weighted work to 24:00Z | 150.61 (2.15) | 132.34 (11.71) | 152.16 (2.64) | 152.68 (2.82) | 148.45 (7.52) | 151.86 (2.5) |
| CPU idle while queued to 16:00Z (Qh) | 48.77 (5.88) | 70.08 (10.48) | 44.46 (0.82) | 45.29 (1.46) | 48.26 (12.56) | 53.48 (10.41) |
| GPU idle while queued to 24:00Z (h) | 0.02 (0.0) | 0.02 (0.0) | 0.02 (0.0) | 0.02 (0.0) | 0.02 (0.0) | 0.02 (0.0) |
| urgent mean wait (min) | 44.19 (10.48) | 53.4 (31.85) | 21.41 (8.2) | 19.15 (5.23) | 40.99 (24.66) | 42.45 (21.54) |
| quiet collisions to 24:00Z | 0.12 (0.33) | 0.12 (0.33) | 1 (1.32) | 1.38 (0.86) | 1.88 (2.47) | 1.88 (1.05) |
| solver mean ms | 0.0 (0.0) | 0.0 (0.0) | 54.58 (10.32) | 76.55 (16.29) | 98.16 (8.24) | 97.95 (10.98) |

Reading the sweep:
- **C holds its gain under estimate error.** To 16:00Z it beats A by about 9 % and B by about 17 %, with a third of their spread. Its urgent wait is half of A's.
- **To 24:00Z, C and A are within noise** (152.2 ± 2.6 vs 150.6 ± 2.2).
- **B, the depth-1 uncapped EASY reservation, is the fragile one.** With ±30 % estimates its head reservation is placed at the wrong time and over-holds lanes. Its urgent wait sd is 32 min, and to 24:00Z it does 12 % less weighted work than greedy.
- **The lane-lock term is what makes C robust.** C-nolock's urgent wait is 41 ± 25 min.
- **C's one regression is BUILD-LANE collisions:** 1.0 ± 1.3 per day against 0.12. The C+b pricing did not fix it (1.9).

### Upper bound with the quiet rules switched off (QUIET-SERIAL and quiet-host-versus-loud)

| no-quiet upper bound (quiet rules off) | A | C |
|---|---|---|
| CPU busy to 16:00Z (Qh) | 136.5 | 112.2 |
| CPU idle while queued to 16:00Z (Qh) | 3.0 | 27.3 |

A is the meaningful bound: greedy with no quiet rules fills the CPU. C is not tuned for that regime, so it scores lower.

### Solver scaling (synthetic n rows sampled from today's trace)

| rows planned | one SGS evaluation (ms) | full 400-evaluation solve (ms) |
|---|---|---|
| 20 | 0.3 | 156.0 |
| 40 | 0.7 | 367.0 |
| 60 | 1.5 | 669.0 |

One SGS evaluation stays under 2 ms at 60 rows. With the 150 ms budget, C evaluates about 100 orders at 60 rows instead of 400. A live budget of 1 s (0.8 % of the 120 s tick) restores the full search at 60 rows.

## 9. What C would have done at the five decision points

Method: the *actual* state at each instant is rebuilt from the trace (running grants, released rows, build claims), and each strategy is asked what it would start. For 11:20 and 11:39 the keeper's real refusal of c21-r3 (foreign busy on q3, a pytest llama server) is modelled as a transient row gate of 240 s.

| at (Z) | live keeper did | A (model) | B | C would |
|---|---|---|---|---|
| 10:03 | granted ak-cpu-gdn-state-fwd-r2 (rank 100, est 4 h, ran 23 min) on q0 | starts aa-calibration (rank 60, 4.6 h) | starts nothing | starts nothing on CPU. A loud build claim holds q0; the plan holds the quiet lane for the best-ranked quiet-host row after the claim (specpit 11:33Z), so it does not lock QUIET-SERIAL for 4 h. c21-r2 was not visible yet (published 10:09Z), so no strategy could have planned for it. |
| 10:27 | granted aa-calibration-q-a3b (rank 60, 4.6 h) on q0 while c21-fold-cpu-r2 (rank 9) waited on the loud claim; owner STOPped it at 10:45 | same as live | holds for c21-r2 | plans c21-r2 first at the claim's end and starts nothing overlapping. The 10:45 STOP is unnecessary and c21-r2 starts when the claim releases. |
| 11:20 | granted specpit1-t1p100-r4 (rank 40, 6.4 h) on q0, because the quiet gate removed c21-r3 so nothing was reserved; owner STOP 11:26 | starts aa-calibration | holds | plans c21-fold-gpu-r2 at 11:22 and c21-r3 at 11:24 (when the foreign-busy gate clears), and starts no CPU row that overlaps c21-r3. |
| 11:39 | granted specpit1-t1p095 (rank 40, 19.8 h) after the RANK-SKIP T bug; owner STOP 11:42 | starts aa-calibration | holds | plans c21-r3 at 11:43, which is what the owner's STOP achieved by hand. |
| 15:52 | granted ak-df2-pointmass (rank 15, 46 min) on the GPU | starts vidya-r18d (rank 15, 102 min), plus specpit-r3 and aa-calibration on CPU | starts vidya | runs the short GPU rows first (ak-mmid-ub-ceil 5 min, c21-tree-official 40 min, gdn-pscale 10 min, specstale 8 min, …: WSPT on equal ranks). On CPU it leaves q1/q2 free for the whole-host / quiet-host rows planned after the build claim, rather than starting a 6 h quiet row. |

## 10. What actually limits churn on the CPU side

- **The idle CPU is structural.** Every strategy leaves 43-57 quarter-hours of CPU idle while CPU work is queued, out of 192 to 16:00Z. Almost every AK CPU row is quiet (QUIET-SERIAL host-wide, plus `QUIET_DEFAULT_OWNERS = {autokernel}`) or loud (`busy_fraction >= 0.6`), and a quiet-host row refuses any loud grant on the one host-wide NUMA side.
- **The bound.** With those rules off, greedy A reaches 136.5 busy quarter-hours and 3.0 idle-while-queued.
- **The levers are outside the scheduler, so each is an operator or measurement decision:**
  - measured per-NUMA-node quiet sides (NPS4 is already used in the c21 bandwidth preflight);
  - classifying AK rows quiet only when they carry a decision-grade timing claim;
  - giving light claims on 84-87 a quiet budget. At 11:20Z they blocked a rank-9 row.

## 11. Recommendation

**Build C, but as the planner on top of B's admission path, through shadow then enforce. Do not enforce B on its own.**

- **Why C:**
  - Under realistic estimate error it is the only strategy that improves both throughput to the end of the busy window (+9 % rank-weighted work over greedy to 16:00Z) and urgent latency (−52 % mean wait), with low spread.
  - It automates the 8 owner STOPs of section 2.
  - It costs about 50 ms per state change.
  - It removes six hand-coded reservation rules (rank_reservation/DRAIN, RANK-HOLD, RANK-SKIP, QUIET-RESERVE, QUIET-URGENT-PENDING, BACKFILL-IF-FITS) in favour of one objective.
- **Why not B on its own:**
  - B wins on the exact-estimate replay, but under ±30 % noise it loses to greedy on both weighted work and urgent wait.
  - The landing fix should therefore stay in `RESERVATION_MODE=shadow` until estimate error is measured live (rebook from `smoke_measure.json`; the overrun alert at 1.5x). Alternatively, B should become C's fallback path rather than the primary.
- **The ask's "maximize churn throughput" needs a caveat:**
  - Over a full 24 h day, C equals greedy on total weighted work within noise. The gain is in *when* the high-rank work lands, not in how much work lands.
  - The large throughput lever is the quiet model (section 10): about 46 quarter-hours of CPU to 16:00Z. That is an operator / measurement decision, not a scheduler one.
- **Build plan:**
  1. Port `Replan.solve` into `rowflow.py` as a pure function `replan(free, cands, running, now)` sharing `conflict()` with `plan()`.
  2. Run it in shadow: write `REPLAN-SHADOW` lines and `replan-plan.json` every tick, with no grant writes.
  3. Add a nightly replay gate that runs this simulator on that day's trace.
  4. **Enforce criteria,** for 7 shadow days:
     - zero `conflict()` violations in committed plans;
     - solver p99 < 1 s;
     - on each day's replay, C ≥ greedy on rank-weighted work to the end of the day;
     - urgent mean wait ≤ 0.7 x greedy;
     - BUILD-LANE quiet collisions ≤ 1 per day;
     - no row waits beyond the 12 h pin bound.
  5. Enforce behind `REPLAN_MODE=enforce`, falling back to B (shadowed) or greedy on any solver exception or timeout.
- **Open items to fix in the build, each with a shadow metric:**
  - Build-claim arrivals must enter the plan. The C+b pricing did not fix collisions under noise. The next candidate is to keep one quarter build-ready while `rho_build > 0`.
  - GPU smoke budget holds should be modelled. They are 2.0 h of real GPU idle that the sim does not see.
  - C' (pause at unit boundaries) adds nothing measurable over C (152.7 vs 152.2 weighted work; 19 vs 21 min urgent wait) and adds collisions. **Do not build C'.**

## Appendix: reproducing

```bash
cd /mnt/raid0/llm/tmp/pm-knapsack-sim-20261124
python3 trace.py                       # trace-raw.json from the live state (read-only)
python3 sim.py                         # baseline + snapshots -> results.json
nice -n 19 taskset -c 96-183 python3 sim.py --sens 8   # +-30 % sweep, ~8 CPU-min, no rowflow claim (84-87 are AK quiet cores)
python3 sim.py --bench                 # solver scaling -> bench.json
SIM_QUIET_SCOPE=none python3 sim.py --only A,C   # quiet-rules-off upper bound
python3 report.py                      # the tables in section 8
```
