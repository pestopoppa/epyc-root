# AutoKernel Unified-Surface Program — one champion, one accumulator, one runbook for CPU + GPU kernel work

**Status**: ACTIVE · opened 2026-09-07 · owner `ak-rebuild-20260828` (loop side) with `inf70-audit` /
`workspace-1c` (CPU side) · rider on [`autokernel-rebuild-program.md`](autokernel-rebuild-program.md)
(R23 series) and [`autokernel-champion-aggregate.md`](autokernel-champion-aggregate.md) (FOLD series)
**Index row**: `inference-research-index.md` → this file. **Domain**: inference research.

## Operator directive (2026-09-07, verbatim intent)

> "Shouldn't both CPU and GPU kernel work be subsumed by the autokernel loop (which would then be
> responsible for coordinating when heavy CPU is used for building kernels) and its accumulated keep +
> champion promotion runbook, and potentially have a single session monitoring autokernel's runs?"
>
> Ruling: **"unify the champion, the accumulator and the promotion runbook now, so CPU levers land on the
> same branch, get bundled toward the same serving gate, and inherit the durable bundle and the
> leave-one-out arm"** — relayed to the CPU session 2026-09-07 with the request to start immediately.
> Then, as the design step: a config-arm type and per-surface budgets; subsume INF-70's *measurement*
> into the loop first, its *authoring* only once the config arm exists; one session monitors both surfaces.

**Operator context added 2026-09-07 (north star for every phase):** *"autokernel, when running, should
own both GPU and CPU resources, and maximally use them to advance kernel research on all fronts. That's
what the loop needs to be built up to handle."* So U4 is not a courtesy scheduler: the loop is the OWNER of
both resources and their saturation is a KPI — idle-while-claimed is reported per resource, the CPU surface
is a co-equal search frontier (not a fold target), and while a GPU arm runs the CPU should be running CPU
arms or builds subject to the contention bounds in §3.4. The manual CPU campaign is transitional.

**Operator directive 2026-09-08 (verbatim; supersedes the cadence above until consolidation completes):**

> "I want no more pure kernel inference research until we have a FULLY consolidated champion collecting
> all GPU AND CPU performance progress."

> "WE CANNOT AFFORD to lose performance progress on either the GPU or the CPU inference work. WE MUST
> FOCUS on consolidating all kept performance levers and persisting them."

NO research relaunch after the fold window; consolidation only; relaunch is a separate operator go.
The CPU session (INF-70 / `workspace-1c`) received this directly and has parked all lever campaigns.

## Start here (executor)

1. Read §2 (evidence) once — it is why every phase below is shaped the way it is.
2. Phase 1 is the FOLD at run 30's next boundary; it is already specified as FOLD-0..3 in
   `autokernel-champion-aggregate.md` and `docs/design/inf70-cpu-fold-into-champion-20260907.md`. **Do not
   re-plan it; execute it, plus the two additions in §4 P1.**
3. Phases 2–5 are loop code in `epyc-inference-research/scripts/kernel_rnd/autokernel/loop/`. Every phase
   has a measured exit criterion; "tests green" is never one of them.
4. Run starts/stops are operator-gated. The loop is running (run 30, pgid 892348) on the champion tree at
   `/mnt/raid0/llm/tmp/champ2`; **nothing here lands on `ak/champion/llama-cpp-0db32c06e3e5` mid-run.**

## 1. The problem in one paragraph

Two campaigns optimise the same production kernel tree on the same host with two lineages, two ledgers,
two measurement disciplines and no shared scheduler. The single-champion invariant (ratified 2026-08-31,
`OPERATING_CONSTRAINTS.md` 35c1a6d1: one champion aggregates ALL work between promotions) is therefore
violated by construction — the exact fork `INC-20260831-champion-lineage-fork` ended once — and the two
campaigns corrupt each other's measurements because **no CPU on this host is free of the other's work**
(§2.3). The loop already owns the discipline the unified program needs (calibrated floors, paired
alternating A/B, drift detection, refusal ledger, durable bundle, anchor guard); what it lacks is a
*surface* dimension, a *runtime-config* arm, and a *resource broker*.

## 2. Evidence this design rests on (all measured 2026-09-07 unless noted)

### 2.1 The accumulator never confirmed anything — R23-51
The bundle was rebuilt from the anchor at every startup, so each restart reset the keeps AND advanced the
champion of record to the accumulated tip. **No `epyc.autokernel.serving_ab.v1` record exists on disk; the
R23-44 serving gate has never fired.** Bundle peaked at +6.13% (5 keeps) vs an +8.84% threshold. Fixed
(durable `Bundle`, `load_bundle()` refuses state the tree no longer contains; research `706e6894`); the true
cor must be re-seeded with a MEASURED tip-vs-cor bench at the next launch (R23-51a). A unified bundle
inherits this fix for free; a hand-kept CPU ledger cannot.

### 2.2 Numbers from a contended instrument are not banked value — R23-50, INF-70 HARNESS-1
Same day, same mechanism (`akm-q4k-q8-sum-sidecar`): +6.723/+2.978/+2.374/+1.952/+1.595% and four nulls,
against a 0.668% floor — a 6.6 pp spread; ~80 re-measurements since are null-to-negative. INF-70's cold-arm
A/A: ~5% clean, **pair_p95 19.89% contended**, one arm carrying 3218% foreign CPU. Their +4.50% champion
headline (supersedes the +4.27% quoted earlier that day; 1.5149× vs pristine on 0 s-eviction rounds) is at or below its instrument's floor (sign survives on 60/60 paired wins; magnitude does not).
Historical arms cannot be retro-screened: the sampler read `184-191` as disjoint until today, so labels are
wrong, not missing. Three of our 31 `kept` rows never reached the champion (tagged
`ak/orphan-keeps-quantize-20260829`), and the pass they touch is ≤3.6% of tg128, so their +12.5% was noise.
**Consequence for design: measurement must be one system with one contention model, or every magnitude
either side quotes is provisional.**

### 2.3 Isolation by placement is impossible on this host — R23-49 / OP-41
Kernel-read `thread_siblings_list`: logical `c` and `c+96` share a physical core, exhaustively. Our
`jobs=64` builds on `96-183` cover 88 of INF-70's 96 bench cores (9×`cc1plus`@100% measured live); our
bench host threads on `184-191` cover the other 8; our `llama-server` was unpinned (now pinnable,
`Recipe.cpu_list`, default off until the floor is re-calibrated under a pin). **"Fence tooling out of 0-95"
has nowhere to fence to. The only real options are SERIALIZE, SCHEDULE, or ACCEPT-AND-REGRESS**, and only
a single owner can serialize builds, CPU arms and GPU arms coherently. INF-70's own builds
(`build3.sh`, `-j40`, unpinned, unlocked) have the same defect.
**Placement is not even sufficient**: both sides were correctly pinned on 2026-09-08 and still poisoned
each other through DRAM bandwidth — see the admission-control bullet at the top of §3.4.

### 2.4 What already exists and must be reused, not rebuilt
| capability | where | status |
|---|---|---|
| calibrated per-surface floors (tg128 0.638% @20 pairs; dec-b4; serving 3.536%) | `loop-memory/calibration/`, `serving-floor.*.json` | GPU surfaces only |
| paired alternating A/B + residency + drift | `loop/bench.py`, `loop/residency.py` | GPU |
| **build-recipe arm (cmake defines as a champion arm)** | D3, shipped 2026-08-30 | exists — **runtime-config arm does not** |
| durable bundle + validated reload | `loop/accumulate.py` (2026-09-07) | single-surface |
| anchor guard by OBJECT digest + incremental build | `controller/anchor_integrity.py`, `loop/anchor.py` | GPU objects; works for CPU objects unchanged |
| leave-one-out per accumulated keep on PROMOTE | R23-48 | designed, not built |
| CPU region lock (`cpu_region.{role}.{region}.lock`) | `epyc-orchestrator/src/runtime/cpu_region_lock.py` | orchestrator-owned; loop does not take it |
| sibling-expanded live foreign-load sampler | `/mnt/raid0/llm/tmp/inf70/agents/sync19-20/foreign.py` (protected) | INF-70; `/proc/<pid>/stat` deltas, not `ps %CPU` |
| fold plan + two default-ON blockers | FOLD-0..3, `docs/design/inf70-cpu-fold-into-champion-20260907.md` | specified |
| promotion runbook | `docs/reference/kernel-freeze-runbook.md` (shipped v7/v8/v9) | single candidate build, never cherry-picks |
| **rescued kernel work not yet in the champion** | [`docs/design/champion-consolidation-audit-20260908.md`](../../docs/design/champion-consolidation-audit-20260908.md) | audited 2026-09-08: 23 superseded/archive, 2 candidates + 1 decline (P1b), 2 REFUTED, 1 must-not-fold, 4 single-copy refs pushed |

**Audit note (2026-09-08).** The reuse question "is this lever already in the champion?" cannot be answered by
patch-id: v9 was rebuilt from fresh upstream, so `git cherry` calls semantically-present levers unmerged. The audit
above used `git cherry` **plus** a content grep against the champion tip `bff30cebe`. The converse hazard is sharper —
**folding a superseded decision back in is a failure class ancestry checks cannot see and cherry-equivalence waves
through** (see the MUST-NOT-FOLD entry in P1b).

## 3. Design

### 3.0 The unified iteration — pseudocode first (rule: agent loops get pseudocode before the plan)

```
STATE (durable, in loop-memory):
  champion        = one branch, ak/champion/llama-cpp-<prod-sha>, anchor == tip (object digest)
  bundle[surface] = {champion_of_record, tip, keeps[], compounded_bench_pct (MEASURED vs cor)}
                    surfaces = {gpu.tg128, cpu.<recipe-name>, ...}; ONE cor shared, per-surface gain
  floors[surface] = calibrated A/A floor per (surface, n_pairs, host-state hash)
  budgets[surface]= max iterations in flight, max arm seconds, max concurrent builds

each iteration (lane picks a surface by budget share, not round-robin):
  hypothesis  ← planner(surface, context[surface])         # context = profile+ledger+inbox for THAT surface
  kind        ← SOURCE | BUILD_RECIPE | RUNTIME_CONFIG       # RUNTIME_CONFIG is new (§3.3)
  critic pass 1 → accept | reason back to planner
  patch/recipe/config ← author(kind)
  critic pass 2 → accept | reason back
  BROKER.acquire(build_slot)                                 # §3.4: builds are heavy CPU, scheduled
     build (incremental, object digest)   [skipped for RUNTIME_CONFIG: same binary, new launch args]
  BROKER.release(build_slot)
  BROKER.acquire(surface.arm_resource)                       # gpu claim | cpu region lock role=bench
     correctness oracle(surface)
     A/B paired alternating, n from floors[surface], residency + FOREIGN-LOAD sampled during the run
  BROKER.release
  keep? → commit onto champion (SOURCE/BUILD_RECIPE) or onto codified recipe (RUNTIME_CONFIG)
        → anchor guard → bundle[surface].add_keep(MEASURED tip-vs-cor) → bundle.save()
  if any bundle[surface] clears fire_multiple × floors[surface.serving]:
        serving gate for THAT surface (its own recipe, its own llama-server)
        PROMOTE surface → cor advances (shared)
                        → RE-BASELINE: every OTHER surface re-measures tip-vs-NEW-cor on its OWN harness before
                          any compounded_bench_pct is quoted again — never carried, never rescaled ("a baseline's
                          value is a property of the tip it was taken at", INF-70 review 2026-09-07)
                        → LOO: one reverted arm per accumulated keep, ALL surfaces, as a HARD GATE on the
                          promotion record (no LOO receipt → promotion refused: LOO skipped once is
                          indistinguishable from LOO never built). Cost n_keeps × n_surfaces arms — budgeted §3.4.
                          (a CPU keep can change a GPU number: shared ggml graph code — measure, don't assume)
        DIVERGE → hold, journal, planner evidence
promotion to production: ONE full candidate build of the champion tip, all surfaces' gates demonstrated,
                         kernel-freeze-runbook, freeze-aware agent overlay baked in
```

### 3.1 Track U1 — unify champion, bundle, runbook (NOW; no loop code needed)
- CPU levers are commits on `ak/champion/llama-cpp-0db32c06e3e5`, staged on a lane branch off its tip,
  folded at a loop boundary by the reconcile precedent (`a27287015`: merge-tree disjointness, zero
  conflicts, pre-fold tags). **Never mid-run**: the anchor guard proves anchor == tip by object digest, and
  a CPU commit changes library objects.
- Both default-ON blockers opt-in first (FOLD-0): `GGML_OP_MOE_TOPK_NORM`, INF-64 fused decoder.
- CPU keeps recorded in the same durable schema (`epyc.autokernel.accumulator_bundle.v1`) with measured
  compounded gain vs cor, so the fold merges one bundle, not two ledgers.
- LOO on PROMOTE applies to the whole stack (R23-48) — CPU keeps included.
- Promotion = one candidate build (runbook), never cherry-picks.

### 3.2 Track U2 — surface dimension on the bundle and the gates
`Bundle` gains `surface`; the store keeps one file per surface; the cor is shared. Each surface has its
own screen floor, confirm rung, serving recipe and serving floor — **and each floor carries its measurement
conditions (harness, n, contention model, host-state hash), not just a number**: ours is 3.452% p95 at n=20
tg128 pairs, INF-70's is ~5% clean / 19.89% contended on a 24-prompt served harness, and the same
`compounded_bench_pct` would otherwise mean two different things in one bundle (CPU: `Recipe` with `device=CPU`,
`cpu_list`, `numa`, threads — the CPU session's canonical recipe becomes the codified artifact). The
serving gate fires per surface. The headline card shows per-surface gain over the shared cor, never a
sum or product across surfaces.

**A floor must carry its UNIT (measured 2026-09-08, INF-70 RETEST-1) — this is the field whose absence
costs three orders of magnitude.** The conditions list above (harness, n, contention model, host-state hash)
was incomplete: add **`unit` ∈ {arm, session, process}**, the scope at which the knob under test varies.
Within-session (**arm**) sd is **0.501%**; between-session (**process launch**) sd is **2.793%** — a
process-scoped knob faces a floor **~13× coarser** than an arm-scoped one. Worked consequence: INF-70's
**0.171% arm** floor says CHAMP-2 THP needs **4 sessions/side**; the correct **session-unit** answer is
**4,780** — a **1200-fold** error, and it would have been spent as real host hours. So: every floor record
states its unit, and **a gate comparing an effect to a floor of a different unit REFUSES** rather than warns.
Mirror task: `autokernel-rebuild-program.md` **R23-55** (write `unit` into `loop-memory/serving-floor.*.json`
and the bench-floor records).

**Re-baselining rule (INF-70 review, 2026-09-07).** The cor is SHARED, so when any surface's promotion
advances it, every other surface's `compounded_bench_pct` is momentarily stated against a baseline its own
harness never measured. That number is INVALID until that surface re-measures tip-vs-new-cor on its own
harness: the bundle marks every non-promoting surface `stale_baseline` at PROMOTE and clears the flag only on
that measurement; a quote while flagged is refused. Carrying or rescaling it forward is the same laundering
class as pre-hook seeding. Per-surface cor was considered and rejected — it recreates two lineages inside one
branch; if the re-baseline arm ever proves too expensive, revisit that choice explicitly rather than skip the arm.

### 3.3 Track U3 — RUNTIME_CONFIG arm type
D3 gave us build-recipe arms (cmake defines). Most CPU wins are *runtime*: placement, NUMA mode, thread
topology, env knobs, launch flags. A RUNTIME_CONFIG hypothesis mutates a **codified recipe**, needs no
build, and is measured by the same paired A/B (two launches of one binary). A keep commits the recipe
change (recipes are code, in git) and the recipe hash becomes part of the epoch. Guard: a knob whose
`switch` covers more than its name (INF-70's `GGML_TINY_SOLO_CLAMP` fall-through gated 10 ops) is a
correctness-oracle failure, not a tolerance — the oracle must diff op coverage, not just outputs.

### 3.4 Track U4 — resource broker and per-surface budgets

- **Admission control, not screening (measured 2026-09-08, both directions):** during the fold window the
  GPU and CPU surfaces each measured the other as a confound, **with both sides correctly pinned and
  INF-70 holding the CPU region lock correctly**.

  | direction | victim instrument | confound | quiet reference | contaminated | ratio |
  |---|---|---|---|---|---|
  | 1 (INF-70 MEAS-6) | their hot-harness A/A (`llama-bench`, one process at a time, tg128, 20 alternating pairs, host threads `taskset -c 184-191`) | my bundle-seed bench, straddled deliberately | pair p95 0.80% drain-era; quiet-host subset re-measured **0.509%, sd 0.279%** | **7.223%** (n=5, sd 3.268%); restated **2.151%** on their adjacent subset | **~4.2×** |
  | 2 | my pinned serving-floor recalibration (10:05-10:08Z) | their RETEST-1 `llama-server` pid 1167737, `-t 48`, 242 threads, 4800% CPU across 0-95, launched 09:53:47Z by `session2.sh RA_AA`, holding q0-q3 as `retest1-campaign3` correctly | unpinned quiet-host floor **3.536%** (n=8, cv 1.572%) | **10.255%** p95 (cv 5.977%; 155.02/168.48/152.81/144.17/143.22 tok/s) | **~2.9×** |

  Direction 1 put the detectable effect at n=8/side at **4.575%**, i.e. 1-3% CPU levers are unmeasurable
  under concurrency, and their pre-registered gate halted before any lever arm ran. Direction 2 cost a
  quarantined floor file and an aborted n=10 run.

  **The channel is DRAM bandwidth, not cores.** INF-70's contention screen (foreign %CPU,
  sibling-expanded) PASSED every contaminated arm: prefill flat (±2%) while decode fell 7%, NUMA
  placement and AnonHugePages constant. **No CPU-occupancy screen on either side can see it.**

  **Halt semantics are part of the broker, not a courtesy.** Both sides had a "halt" that did not stop
  queued successors: my loop's drain let a lane start a `jobs=64` build at 09:31Z (killed at the build
  stage); INF-70's `chain2.sh` (launched 09:41:41Z) ran a `-j 48` build 09:48:11-09:49:17Z on its own
  after campaign 1 halted, and their agent re-ran a campaign at 09:53:41Z, reading "STOP and report" as
  "diagnose and re-run". Structural, not carelessness.

  **Rules this fixes into U4:** (a) the broker **admits ONE surface at a time** — time-slicing, with a
  quiet-host A/A at each switch; (b) the broker owns process **LIFECYCLE**, not just locks: *nothing
  queued may fire across a halt*; (c) CPU-occupancy screens stay **necessary for diagnosis but
  insufficient for admission**. Cost of the alternative (INF-70, arms at 80% power): detecting +1.0%
  needs 2 arms/side quiet, 10 concurrent, 168 during an excursion — serialising is worth **5×-84×**;
  CHAMP-2's pooled +0.16% needs ~48 sessions/side ≈ **10 h exclusive**, not resolvable on this host
  under any realistic booking.

The loop becomes the single scheduler for: build slots (pinned, `jobs` bounded, **locked**), GPU arms (the
`mi210_0` flock, as today), CPU arms (the orchestrator `cpu_region_lock`, role `bench`), and the
foreign-load sampler (sibling-expanded, `/proc/<pid>/stat` deltas — reuse `foreign.py`, do not rebuild).
A CPU arm and a build never overlap; a GPU arm and a build may (GPU-bound, host threads pinned) only if
the sampled foreign load on the GPU host threads' siblings stays under a declared bound. Budgets: a CPU
arm costs ~10× a GPU arm (reload + eviction), so surface share is by *arm-seconds*, not iterations, and the
CPU surface gets fewer, larger windows. This is the structural resolution of OP-41 (option A, built in).
**LOO budget, stated so it cannot be quietly skipped:** per promotion, `n_keeps × n_surfaces` arms plus one
re-baseline arm per non-promoting surface — at 5 keeps and two surfaces, 5 GPU arms (minutes) plus 5 CPU
arms (~30 min of arm time before builds) plus re-baselines. The broker reserves that window when the fire
decision is made; the promotion record carries LOO and re-baseline receipts as REQUIRED fields and a
promotion without them is refused, not warned.
**Precondition for P4 (INF-70 review):** `foreign.py` lives in scratch (`/mnt/raid0/llm/tmp/inf70/agents/
sync19-20/`) under a retention note, and a retention note is not a home — promote it into
`epyc-inference-research` (beside the recipe module PROD-1 is producing) with a test BEFORE the broker depends
on it. Owner `ak-rebuild-20260828` unless INF-70 takes it.
**§3.3 oracle, sharpened by the review:** INF-70's fall-through knob passed 18/18 output identity precisely
BECAUSE outputs were bit-identical — an output-diffing oracle cannot see the class; op-coverage diffing is
necessary, not nice-to-have.

**Region lock blind spot (measured 2026-09-08):** `cpu_region_lock` models regions as logical-CPU
ranges; a build pinned to 96-183 is OUTSIDE 0-95 yet occupies the siblings of 0-87, so the lock would
grant a bench arm during the compile. The broker must reserve by PHYSICAL core (sibling-expanded, via
`foreign_load.bench_logical_cpus`) — a build slot on 96-183 and a bench arm on 0-95 are the same resource.

**Third-party disturbance is PRICED, and serialisation is not the binding constraint (INF-70, 2026-09-08).**
Across the RETEST-1 Q2 arms the disturbance hit rate was **1 in 6 ≈ a 17% tax in arms** — and it is the
expensive kind, *paid on work identified as garbage only after running it*. Serialisation between the two
sessions **held**: both sides honoured the region lock and it still did not protect the instrument, because
> *"Region-lock serialises those who call it; nothing constrains those who don't."*

That sentence is the whole case for **admission control over cooperative locking**: the broker must gate
**entry to the host**, not participation in a protocol. Foreign, unattributed load (a python process at
**800% CPU**, `Cpus_allowed` 0-191, plus `opencode`) cost one Q2 arm outright. Host-state change for the
record: at **12:05Z** the operator stopped the orchestrator API (uvicorn :8000 + 6 workers, pid **3961116**,
up since 2026-08-26) via `orchestrator_stack.py stop orchestrator`; hub :8100, OCR :9001, sd_server :8190 and
the docker containers remain — a **candidate, unproven** source of that 800% python.

- **Gate guards (2026-09-08):** a gate cannot PASS on zero cases or an unobserved graph; verify process
  death by `/proc/<pid>` existence, not `ps` exit codes.

### 3.5 Track U5 — one monitoring session; authoring roles
One roster session monitors both surfaces (status, keeps, gates, errors — what `ak-rebuild-20260828`
does today). The CPU session's role becomes **diagnosis and hypothesis authoring into the inbox**
(sibling-expansion bug, fall-through knob: reading work the loop cannot do), and the loop measures.
Authoring of RUNTIME_CONFIG hypotheses by the loop's planner comes only after U3 exists (operator
sequencing: measurement first, authoring later).

## 4. Phases, exit criteria, tasks

### P0 — directive relayed, handoff filed ✅ 2026-09-07
- [x] Directive sent to `workspace-1c` with concrete instructions (rebase onto champion tip, opt-in the two
      blockers, record keeps in the bundle schema, LOO per promotion, fold at a loop boundary) ✅ 2026-09-07
- [x] This handoff + index row ✅ 2026-09-07

### P1 — the fold at run 30's next boundary (U1)  · exit: ONE champion tip carrying both lineages, GPU floors unchanged
- [x] **UD-0**: operator confirmed the fold DIRECTLY to `workspace-1c` ✅ 2026-09-07 — gate 1 (their windows clear) is theirs to signal; gate 2 (run 30 boundary) is ours
- [x] **FOLD-2 additions (UD-4)** ✅ 2026-09-08: on candidate `ef81196d5` — `test-backend-ops -o SSM_SCAN -b ROCm0` **7/7 OK**
      incl. the K=4 / K=3 rollback cases; `verify_ggml_linkage.sh` **PASS** before the serving gate; dispatch **observed**
      (`llama-bench -v` + `GGML_SCHED_DEBUG=2`: 27,516 nodes, SSM_SCAN=0, SSM_CONV 576 + GATED_DELTA_NET 576 all on ROCm0,
      CPU holds only 12 GET_ROWS); tg128 vs anchor-gen-021 **+0.052%** (20 pairs, floor 0.638%, not decisive, no drift).
      **UD-4 closed on observation.** Result file `/mnt/raid0/llm/tmp/fold-window-20260908/fold2-result.json`
- [x] Champion branch + orphan tag pushed to the GitHub fork ✅ 2026-09-08 (`ak-loop-tree` was swept from scratch mid-fold; `champ2` was one sweep from the same)
- [ ] INF-70 **RETEST-1 turn in progress** (A/A first, then RETEST-1 in priority order); **next fold = their keeps off `ef81196d5`** — they stage
      levers on a lane branch off that tip, prove merge-tree disjointness, and fold the same way
- [ ] FOLD-0 (`inf70-audit`): fold-ready commit with both blockers opt-in; bit-identity + `test-backend-ops -b CPU`.
      **FOLD-0 as written targets `6f032c48d`, two CPU champions old — re-base onto the CPU champion at the
      boundary (today `inf70/champion3` @ `9c4f73e29`, build 10241, `experimental-inf70-champion3` on the `fork`
      remote: +4.50% vs champion-1 on 117/120 per-prompt wins, 1.5149× vs pristine, bit-identical over 16
      arm-pairs, α 0.8209 unchanged) or the fold ships a superseded kernel and discards the +4.50%**
- [ ] Do not schedule the boundary under INF-70's live chains (SYNC-19/20 window 1 ~21:30Z + a second window,
      HARNESS-1 Phase B behind it) — rebasing under in-flight pre-registered arms invalidates them; clears in hours
- [x] FOLD-1..3 (champion owner) per `autokernel-champion-aggregate.md` ✅ 2026-09-08: fold executed, all FOLD-2 gates
      PASSED (G1 7/7, G2 1140/1140, G3 39/39, G4 dispatch observed, G5 +0.052% inside the 0.638% floor), then
      `ak/champion/llama-cpp-0db32c06e3e5` fast-forwarded `bff30cebe` → **`ef81196d5`** (`--ff-only`, tip == candidate) at
      11:16:49Z, lineage verified (`bff30cebe`, `445e93a8`, `9c4f73e29`, production `0db32c06e` all ancestors), worktree
      clean, pushed to fork `pestopoppa/llama.cpp`; pre-fold GPU tip tagged `ak/pre-fold-gpu-tip-20260908` (pushed).
      **Production branch untouched.** NO relaunch (operator directive stands)
- [x] **R23-51a in the same window** ✅ 2026-09-08: cor `445e93a8` seeded with a **MEASURED** tip-vs-cor tg128 bench,
      **+5.958%** (20 pairs, decisive, not drifting). The serving gate then ran on it: n=5 −5.19% (decisive, `diverged`),
      re-run n=10 **−2.18% NOT decisive** → disposition **UNCONFIRMED (not refuted)**; **cor HOLDS at `445e93a8`** and the six
      keeps stay on the tip as provisional and re-gateable. An **11-point proxy-vs-truth gap** the bench alone could never show
- [x] **R23-49 pin + re-calibration in the same window** ✅ 2026-09-08: `cpu_list` pinned `184-191` on the GPU serving recipe
      and the serving floor re-calibrated under the pin — **4.581% p95** (n=10, cv 3.136%, median 161.08 tok/s) on a
      verified-quiet host; the first attempt was CONTAMINATED (10.255%, INF-70's server live) and was quarantined. The pin
      costs ~1 pp of floor width vs the 3.536% unpinned quiet floor
- [ ] CPU keeps present in the fold recorded as `accumulator-bundle.cpu.<recipe>.json` (schema v1) — **with their
      magnitude flagged `provisional` and the contention label `pre-hook`**: every INF-70 arm before 2026-09-07
      carries a WRONG contention label (sampler read `184-191` as disjoint), and +4.50% is at or below its
      instrument's floor (sign solid, magnitude not). A bundle must never launder a non-claim into a settled number.
      **Further caveats (INF-70, 2026-09-07 ~20:20Z):** (i) SYNC-19/20 independently corroborates the ~5% floor — seven
      identical A arms, sd 1.79%, range 4.91%; (ii) **a harness-wide statistical defect**: 20 prompts inside one arm are ONE
      observation, and a sign test over pairings double-counts the shared treatment arm, so every INF-70 significance
      computed the old way is inflated — the corrected statistic is an arm-level permutation test; any magnitude the
      bundle ingests must carry which statistic produced it; (iii) linear within-block drift is ruled out (slope
      +0.03%/slot, R² 0.004), so CPU-surface scatter is contention (OP-40), not drift.
- [ ] NO relaunch by default (operator 2026-09-08). **Consolidation exit ACHIEVED for the GPU side ✅ 2026-09-08**: one tip
      carrying both lineages (**`ef81196d5`** = GPU tip + CPU champion3 `9c4f73e29`); **FOLD-2 passed**; the durable bundle
      **seeded MEASURED** (+5.958% tip-vs-cor) **and the serving gate run on it → UNCONFIRMED** (−2.18%, n=10, not decisive;
      cor holds `445e93a8`); **tip on the fork**. Consolidation is **complete for the GPU side pending INF-70's keeps**, which
      fold onto `ef81196d5` next. Phase-2 candidates below still to be gated or declined. Then ASK before any run 31.

### P1b — consolidation phase 2: rescued-ref candidates (each behind its own gate; measurement that serves consolidation is allowed)

Source of truth for the classification of all 31 `fork/rescued-*` refs:
[`docs/design/champion-consolidation-audit-20260908.md`](../../docs/design/champion-consolidation-audit-20260908.md).

- [ ] **Chunked GDN — `rescued-ak-g15-chunked-gdn-20260823` @ `719a8529d`** (upstream PR #24561 unified-MMA port;
      `ggml/src/ggml-cuda/gated_delta_net.cu` +527, `tests/test-backend-ops.cpp` +34). Surface: GPU PREFILL on GDN
      models (qwen35 / qwen35moe / qwen3next); the champion still carries `//TODO: Add chunked kernel for even faster
      pre-fill`. **Largest unrecovered GPU lever.** Gate: GPU prefill A/B on a GDN model **plus** `test-backend-ops`.
- [ ] **Quantize reciprocal — `rescued-ak-discovery-7e8da8ea-attempt1` @ `9f85ba2fb`** (`ggml/src/ggml-cuda/quantize.cu`
      +4/−1: reciprocal-multiply + `__shfl_sync` broadcast replacing per-lane `roundf(xi/d)`; the champion still does
      `roundf(xi / d)`). Gate: tg128, 20 pairs vs anchor.
- [ ] **Q5_0 `vecdotq.cuh` variants — `f9d74a2a3`, `d4b0a04e4`, `580e8d090`, `5d22a5463`: DECLINE.** Q5_0 is not a
      production quant and the work is re-derivable. Revisit only if a Q5_0 target appears on the fleet.
- [x] Single-copy refs pushed to the fork ✅ 2026-09-08 (`ak/orphan-keeps-quantize-20260829`,
      `ak/pre-anchor-fix-full-history` `b04fad244`, `ak/run14-01893a36-cumulative` `01893a36c`,
      `ak/admission/remove-funsafe-math-20260831` `3161d2dcf` — the last is already applied on the champion as
      `b861c32fa` (CH-7, 2026-08-31); pushed for durability only, nothing to fold)

**REFUTED — do not fold. A measured refutation is not a keep, and re-measuring a refuted lever is new research
(stopped by the operator).** Both read as candidates on the audit's first pass because absence from the champion is
exactly what a refuted lever looks like; corrected from the record by INF-70 2026-09-08:
- `rescued-inf10-gemv-fusion` `ea8ca0609` — measured and refuted 2026-08-27: gate+up **−2.11%**, QKV **+0.25%**, both
  **−0.57%** (verified window **−1.33%**) at tg128, region-locked q0-q3, canonical env, 5×4 rotated; correctness clean
  (PPL 5.5410 identical 4/4 arms). Closed `[x]` in `cpu-shape-specialized-gemv-decode.md`; evidence
  `epyc-inference-research/data/gemv-fusion-2026-08-25/` + `SHA256SUMS`. *"No further barrier-fusion work is justified
  on this target."*
- `rescued-cpu-opt-q8-8x8-avx512bw` `1f8868307` + `af6701d00` — the SIMD ukernel plan is an explicitly CLOSED appendix
  (8×8 GEMM body E3-gated, owned by `batched-decode-measurement.md`); the one measured angle `0467a5c17` (RMS_NORM
  intra-op parallel reduction) was **−8.8%** (4.41 → 4.02 t/s at 96t, Qwen3.6-27B Q8_0), kept env-gated
  `GGML_RMS_NORM_PARALLEL=1` default OFF as scaffolding. The 22% in `ggml_barrier` is barrier-COUNT-bound; the Q8 axis
  closed with *"the 4.4 t/s ceiling is genuinely architecture-bound."*

**MUST NOT FOLD `de447119f`** (`rescued-feature-tree-draft-v6`, "route Q8_0 `ne11<=1` MTP-verify to MMQ, +17.4%") — the
champion's `mmvq.cu` carries the LATER contradicting decision `akm-cdna2-q8-b4-mmvq-route` (Q8_0 `ne11<=4` through
MMVQ, `ne11>=5` on MMQ — "the July crossover"), reversal documented in-source. Folding it would REGRESS the champion.
Its other GPU commits (nwarps=4, async prefetch, GDN bf16 +21.5%, `GGML_CUDA_GDN_STATE_BF16` in 9 files) are already in.

### P2 — surface dimension (U2)  · exit: two bundle files, two floors, a CPU serving A/B record on disk
- [ ] `Bundle.surface`; per-surface store filenames; `load_bundle()` per surface; shared cor invariant test
- [ ] `serving.Recipe` CPU variant (device, cpu_list, numa, threads) — the CPU session's canonical recipe codified
- [ ] CPU A/A calibration: screen floor + serving floor, n=20 pairs, host-state hash recorded
- [ ] **Every floor record carries `unit` (arm | session | process)** alongside harness, n, contention model
      and host-state hash; a gate comparing an effect to a floor of a different unit REFUSES (INF-70 RETEST-1,
      2026-09-08: arm sd 0.501% vs process-launch sd 2.793%; the 1200-fold THP sizing error). See R23-55.
- [ ] Per-surface fire decision; dashboard accumulator card per surface (product-of-solos labelled ESTIMATE)
- [ ] **Re-baseline on cor advance**: `stale_baseline` set on every non-promoting surface at PROMOTE, cleared only by
      a tip-vs-new-cor measurement on that surface's own harness; test that a quote while flagged is refused
- [ ] First CPU serving gate produces an `epyc.autokernel.serving_ab.v1` record

### P3 — RUNTIME_CONFIG arm (U3)  · exit: a config keep committed to a codified recipe and re-measurable from a fresh checkout
- [ ] Hypothesis kind enum; author path that edits a recipe file, no build
- [ ] A/B of one binary under two recipes; recipe hash in the epoch
- [ ] Oracle extension: op-coverage diff for env-gated knobs (fall-through class)
- [ ] Known-good and known-null config patches classify correctly

### P4 — broker + budgets (U4)  · exit: 10 consecutive iterations mixing surfaces with zero unlocked builds and foreign load under bound on every arm
- [ ] Build slot: pinned + `jobs` bounded + region lock role `build`; per-lane concurrency cap
- [ ] CPU arm: acquire `cpu_region_lock` role `bench`; GPU arm: existing flock
- [x] **P4-0 precondition** ✅ 2026-09-07 (INF-70 took it): `scripts/utils/foreign_load.py` + `test_foreign_load.py` on
      research `main` `de51899c` (branch `inf70/foreign-load-sampler` `e441de78`, merged by `ak-rebuild-20260828`: merge-tree 0
      conflicts, 7 tests green). Importable `sample_once()` / `bench_logical_cpus()`; `--out`/`--bench-cpus`; fails CLOSED on
      unreadable sysfs; foreignness by `cpus_allowed` intersection (permissive by design, `on_bench_core` per row for the strict
      reading); the sibling test is mutation-isolated. Scratch copy stays until SYNC-19/20 + HARNESS-1 finish in-flight arms.
- [ ] **P4-0a (filed 2026-09-07, derived from the P4-0 merge)** — the shared, un-lane-owned research clone
      `/mnt/raid0/llm/epyc-inference-research` is **187 commits behind `origin/main` with 9 dirty tracked
      files** left by other sessions (a merge there failed on `ort`). Surfaced merging P4-0 in; no owner,
      so nobody syncs it. Do NOT `checkout`/`reset` it (destroys other sessions' uncommitted work) — needs
      an operator-assigned owner or a scheduled sweep session before it grows further.
- [ ] Foreign-load sampler wired into residency (reuse `foreign.py`; sibling-expanded; live deltas)
- [ ] LOO + re-baseline receipts are REQUIRED fields of the promotion record; promote refuses without them
- [ ] Budgets by arm-seconds; utilisation (held vs idle-while-claimed) on every row
- [ ] Retire the bilateral hold protocol with INF-70 (OP-41) — the broker replaces it

### P5 — single monitoring session (U5)  · exit: one roster entry monitors both surfaces; CPU session files hypotheses, measures nothing by hand
- [ ] Roster/ownership update; inbox is the CPU session's output surface
- [ ] Wiki: "measure the stack" + "one owner schedules" compiled from this program's results

## 5. Operator decisions (package, non-blocking)

| ID | Decision | Recommendation |
|---|---|---|
| **UD-4 — SSM_SCAN `K` port rides with the fold: measure, don't split (2026-09-08)** | INF-70 found the CPU lineage changes `ggml_backend_cuda_device_supports_op` for `GGML_OP_SSM_SCAN` (`K > 1` → decline on CUDA → CPU fallback), an UPSTREAM port (`4595b1bca` = ggml `1692f9e50`, recurrent-state rollback), with all 5 CPU levers committed ON TOP of it (27 commits after). Splitting = cherry-picking 27 commits = exactly what the runbook forbids and how keeps get dropped. Their operator: *"make sure the gpu-focused autokernel session is aware… reserve a quiet GPU window to verify impact on GPU performance… just make sure we don't lose any performance keeps."* | **Recommendation: take the whole `champion3` as ONE candidate; in the window run test-backend-ops SSM_SCAN with an explicit `K > 1` case, `verify_ggml_linkage.sh`, and OBSERVE the 27B's SSM_SCAN dispatch on ROCm0 (it is a hybrid; SSM_SCAN runs every token); hold K out only on measured evidence.** |
| **UD-0 — RESOLVED ✅ 2026-09-07 (~20:20Z)**: operator ruled DIRECTLY to `workspace-1c`: *"yes, fold onto the champion once the measurement windows clear."* Two gates remain, neither side controls both: (1) INF-70's windows clear (SYNC-19/20 w1 MTP block → w2 `AP` controls + 3 F1 arms → HARNESS-1 Phase B + hot session) — **they message us; do not schedule on an estimate**; (2) run 30's next boundary — ours. | The CPU session (`workspace-1c`) holds a DIRECT operator instruction from earlier this session — *"we're not folding into autokernel champion just yet. make sure we don't forget the canonical recipe."* — and correctly refuses to rebase on a relayed directive. **The operator must confirm the fold directly to that session**; a peer relay cannot override a direct instruction, and should not. | confirm directly; until then P1 proceeds only on the loop-side items (R23-51a seed, R23-49 recal) |
| OP-41 (open) | serialize / schedule / regress on CPU co-tenancy | **serialize, structurally** — P4 builds it; until then accept INF-70's bounded-hold requests |

**OP-41 headline evidence (2026-09-08):** two campaigns, both pinned, lock respected → **4.2× / 2.9×**
mutual degradation via DRAM bandwidth; see §3.4. (Master-index row update owed to its owning session.)

**OP-41 second evidence bullet (2026-09-08, RETEST-1 close-out):** cooperative serialisation **worked and was
still insufficient** — third-party disturbance ran at a **1-in-6 hit rate ≈ 17% tax in arms**, paid only after
the arm was run. *"Region-lock serialises those who call it; nothing constrains those who don't."* This is
evidence for the **admission-control broker** (option A) over any further tightening of the lock protocol;
see §3.4.
| UD-1 | CPU serving recipe = the gate for the CPU surface | the CPU session's canonical served recipe (Qwen3.8-Flash-Next), codified as `Recipe`; not a bench proxy |
| UD-2 | promotion granularity | one production candidate carries BOTH surfaces; a surface without a demonstrated gate does not block the other's keeps landing on the champion, but does block promotion |
| UD-3 | who authors CPU hypotheses after U3 | loop planner for RUNTIME_CONFIG/SOURCE on the CPU surface; CPU session keeps diagnosis; revisit after 10 CPU iterations |

## 6. Risks
- **Cross-surface interaction**: shared ggml graph/scheduler code means a CPU keep can move a GPU number. LOO across all surfaces on PROMOTE is the control; until P2, re-measure the GPU headline after every fold.
- **CPU arm cost** starves the loop if budgeted by iteration count — budget by arm-seconds (P4).
- **Two default-ON blockers** silently change GPU defaults if folded un-neutralised — FOLD-0 is a hard precondition.
- **Recipe drift**: RUNTIME_CONFIG keeps must land in codified recipes in git, never in a session's shell history (lesson: `gguf_swap_ple.py` lived in scratch; the pruner lived in scratch).

## 7. Dependencies
FOLD-0..3 (`autokernel-champion-aggregate.md`) · R23-48 LOO, R23-49 pin/recal, R23-50a/b recovery,
R23-51/51a durable bundle + seed (`autokernel-rebuild-program.md`) · OP-41 · INF-70 MEAS-1 / HARNESS-1 /
CHAMP-2 (`cpu-decode-roofline-program.md`) · `cpu_region_lock.py` · `sync19-20/foreign.py` ·
`docs/reference/kernel-freeze-runbook.md`.

## Key files
`scripts/kernel_rnd/autokernel/loop/{accumulate,run,serving,bench,anchor,pipeline}.py` ·
`controller/anchor_integrity.py` · `/mnt/raid0/llm/tmp/champ2` (champion tree) ·
`/mnt/raid0/llm/autokernel/loop-memory/` (store) · `docs/design/inf70-cpu-fold-into-champion-20260907.md`.
