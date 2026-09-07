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
- [ ] **UD-0 first**: operator confirms the fold DIRECTLY to `workspace-1c` (they hold a contrary direct instruction)
- [ ] FOLD-0 (`inf70-audit`): fold-ready commit with both blockers opt-in; bit-identity + `test-backend-ops -b CPU`.
      **FOLD-0 as written targets `6f032c48d`, two CPU champions old — re-base onto the CPU champion at the
      boundary (today `inf70/champion3` @ `9c4f73e29`, build 10241, `experimental-inf70-champion3` on the `fork`
      remote: +4.50% vs champion-1 on 117/120 per-prompt wins, 1.5149× vs pristine, bit-identical over 16
      arm-pairs, α 0.8209 unchanged) or the fold ships a superseded kernel and discards the +4.50%**
- [ ] Do not schedule the boundary under INF-70's live chains (SYNC-19/20 window 1 ~21:30Z + a second window,
      HARNESS-1 Phase B behind it) — rebasing under in-flight pre-registered arms invalidates them; clears in hours
- [ ] FOLD-1..3 (champion owner) per `autokernel-champion-aggregate.md`: stop at boundary (verified dead) →
      pre-fold tags → merge-tree disjointness → merge → gates on the SAME merged tree (GPU: ROCm0
      test-backend-ops incl. SSM_SCAN, tg128 vs gen-020 inside the floor; CPU: their bit-identity)
- [ ] **R23-51a in the same window**: seed the true cor (`445e93a8`) with a MEASURED tip-vs-cor tg128 bench
- [ ] **R23-49 pin + re-calibration in the same window**: `cpu_list` on the GPU serving recipe, serving floor re-calibrated
- [ ] CPU keeps present in the fold recorded as `accumulator-bundle.cpu.<recipe>.json` (schema v1) — **with their
      magnitude flagged `provisional` and the contention label `pre-hook`**: every INF-70 arm before 2026-09-07
      carries a WRONG contention label (sampler read `184-191` as disjoint), and +4.50% is at or below its
      instrument's floor (sign solid, magnitude not). A bundle must never launder a non-claim into a settled number.
- [ ] Relaunch (operator-gated) with `python3 -u`; verify `accum restored …` line and anchor == tip

### P2 — surface dimension (U2)  · exit: two bundle files, two floors, a CPU serving A/B record on disk
- [ ] `Bundle.surface`; per-surface store filenames; `load_bundle()` per surface; shared cor invariant test
- [ ] `serving.Recipe` CPU variant (device, cpu_list, numa, threads) — the CPU session's canonical recipe codified
- [ ] CPU A/A calibration: screen floor + serving floor, n=20 pairs, host-state hash recorded
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
- [ ] **P4-0 precondition**: promote `sync19-20/foreign.py` out of scratch into `epyc-inference-research` with a test
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
| **UD-0 (BLOCKING P1)** | The CPU session (`workspace-1c`) holds a DIRECT operator instruction from earlier this session — *"we're not folding into autokernel champion just yet. make sure we don't forget the canonical recipe."* — and correctly refuses to rebase on a relayed directive. **The operator must confirm the fold directly to that session**; a peer relay cannot override a direct instruction, and should not. | confirm directly; until then P1 proceeds only on the loop-side items (R23-51a seed, R23-49 recal) |
| OP-41 (open) | serialize / schedule / regress on CPU co-tenancy | **serialize, structurally** — P4 builds it; until then accept INF-70's bounded-hold requests |
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
