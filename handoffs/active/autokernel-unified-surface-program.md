# AutoKernel Unified-Surface Program — one champion, one accumulator, one runbook for CPU + GPU kernel work

**Status**: ACTIVE DESIGN · opened 2026-09-07 · original campaign owners `ak-rebuild-20260828` (loop)
and `inf70-audit` / `workspace-1c` (CPU); both research sessions closed. Current documentation iteration:
`autokernel-plan-20260908` · rider on [`autokernel-rebuild-program.md`](autokernel-rebuild-program.md)
(R23 series) and [`autokernel-champion-aggregate.md`](autokernel-champion-aggregate.md) (FOLD series)
**Index row**: `inference-research-index.md` → this file. **Domain**: inference research.

> **2026-09-08 planning update — documentation only.** The operator is iterating on a VERY detailed
> autonomy plan, including IMPLEMENTATION details; this session is explicitly **not implementing it**.
> [§8 — autonomy design notebook](#autonomy-design-20260908) captures accepted preferences, dated audit
> findings, proposed interfaces/algorithms, migration, tests, and provisional numerical defaults.
> It is not an approved implementation specification or permission to launch research. Consolidation
> ownership and the no-relaunch directive below remain in force. P1 records the fold at `ef81196d5`;
> earlier pending-fold/running-run-30 descriptions are historical, not live-process observations.
> **Final-close-out audit:** [§8.16](#final-closeout-audit-20260908) reconciles both completed sessions,
> ratified measurement rules, measured-versus-delivery identity, per-surface recipes, and implementation
> refinements. It supersedes conflicting earlier design assumptions, not the operator's sequencing gates.
> **Fresh implementation-contract review:** [§8.17](#implementation-contract-review-20260908) resolves
> search-phase policy, the already-ruled four-keep cadence, validation transactions, bounded scheduling,
> scoped evidence use, restart fencing and control/status consistency. Details remain proposals except
> where explicitly identified as existing ratified policy; no campaign restart or implementation follows.

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

## Start here (current design iteration)

1. Read §8.1 for accepted preferences and authority, §8.16 for final-session findings, and §8.17 for
   implementable contracts. Then use §8.13 to locate each proposal's existing owner/task mapping.
2. **Current task is PLAN-DOC-2: refine this notebook, not execute P1–P5.** §1–7 retain the original
   campaign design/history and other owners' checkboxes. Re-resolve their state by task text before any
   future dispatch. The fold/run-30 process descriptions are historical; neither closed session is revived.
3. Ratified measurement rules and operator directives outrank every proposal. Within proposed design,
   §8.17 refines §8.16/§8.3–15 and explicitly identifies replacements for §3 pseudocode. It does not
   silently replace current runtime behavior or waive a protocol, release gate, or operator decision.
4. Research relaunch remains a separate operator go. OP-41 implementation remains operator-owned,
   after champion finalisation → production promotion → host reboot. This documentation authorizes none.

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

### 2.3 Placement alone cannot isolate the historical full-host recipe — R23-49 / OP-41
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

**Historical starting design.** §8 proposes the runtime fast path, phase-specific evidence handling and
separate accumulated/validated pointers; §8.17 makes those replacements explicit. The two universal
critic passes and any-surface `cor` advancement below are not the current implementation specification.

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

**And the champion arm itself is not stable across launches (measured 2026-09-08, INF-70) — so HEADLINE
ADMISSIBILITY is a U2 property, not a reporting style.** An **identical** champion configuration measured
**24.4 → 27.4 tok/s** plain across four of that day's sessions (~**12%** spread: gate 25.6-25.9, THP-OFF
24.4-25.3, FIX-1 controls 27.3-27.4, characterisation 27.3-27.4) while the **pristine control reproduced**
(12.637 vs 12.366 standing, **+2.2%**). Champion 27.383 vs standing ~21.21 is **+29.1%**, and the
champion/pristine ratio reads **2.167×** today against **1.7151×** standing. A hot-vs-cold harness offset
(**+4.36%**) would move *both* arms; only the champion moved, so the harness does not explain it. **The
mechanism is UNEXPLAINED.** Two rules follow for this track:

- **A headline is admissible only from ≥N independent launches with a session-unit CI.** One tight session
  is not a headline whatever its internal spread, because the arm-unit floor is the wrong instrument for a
  quantity that varies at process-launch scope. N is sized from the between-session sd (**2.793%**), never
  the arm sd (0.501%).
- **Investigate the source of the between-launch variance on the champion** — page-cache / NUMA placement,
  THP state, HIP graph capture, allocator — before any final champion number is published. Until it is
  explained, a **"cannot tell"** verdict (CHAMP-2 THP) is as consistent with this instability as with a weak
  effect. Mirror task: `autokernel-rebuild-program.md` **R23-57**.

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

**SEED CASE — the first RUNTIME_CONFIG arm already exists, measured, from outside the loop (2026-09-08).**
CHAMP-2's THP shim (`GGML_NOHUGEPAGE_PROCESS=1`) *is* a RUNTIME_CONFIG arm by this section's own
definition: no build, one binary, two launch configurations, paired, session-unit. INF-70 ran it to a
verdict (6/6 ON-faster, α = 0.0430, direction only) before the arm type exists in the loop. Specify U3
against this instance rather than in the abstract — it arrives with a validated measurement design, a
knob whose scope is known, and a recipe that a keep would mutate. Two properties of it that the arm type
must therefore support, neither of which a SOURCE arm needs:
- **The unit is the SESSION and cannot be otherwise.** A launch-time knob cannot be switched between arms
  inside a live process, so a per-arm number for it is meaningless by construction (R23-55).
- **The effect was a compressed downside TAIL, not a shifted mean** (sd 2.510% OFF vs 0.481% ON, 25.3x).
  A comparator that only tests means can return "no effect" on a real one. U3's compare step must report
  spread alongside the point estimate, and the keep grammar must be able to accept "reduces variance".

**Cross-surface transfer — the programme's thesis, demonstrated (2026-09-08).** This is the FIRST result
either campaign has produced that pays on the *other* surface: a knob found on the CPU decode path is a
candidate fix for the GPU **serving floor** (4.581% p95 n=10), which is the binding constraint on every
GPU keep (R23-58). Everything before it was surface-local or a constraint. Record it as evidence for the
unified surface, against the standing cost of the same design (serialisation throughput, coordination
overhead) — this is the first entry on the other side of that ledger.

**Status precision (do not over-record):** the *verdict* is settled (LIKELY IMPROVEMENT, keep, session
unit, direction only, no fold). The *recipe change* is INF-70's recommendation to their operator and is
**not yet adopted**; the champion default remains OFF until it is.

> **CORRECTION OF RECORD, 2026-09-08 — THE TRANSFER WAS TESTED AND IT DID NOT TRANSFER.** The paragraph
> above was written while R23-58 was still a *candidate*. R23-58 has since **run to its registered stop
> rule and returned a BOUNDED NULL** on the GPU serving path (T0/D0; 48 launches / 24 couples; `p95_dev`
> ratio OFF/ON **0.713**, p = 0.3159; the ON arm slightly *wider*), with the mechanism proven to have fired
> (ON-arm AnonHugePages 0.0% on every launch, `THP_enabled` correct 48/48). Verdict and evidence:
> `autokernel-rebuild-program.md` → R23-58.
>
> **So the ledger entry changes sign, and the honest version is the more useful one.** What the unified
> surface demonstrated is **not** "a CPU finding fixed the GPU floor" — it is that the unified surface let
> a CPU finding be **cheaply and decisively falsified on the GPU surface in ~27 minutes**, which is itself
> the argument for the design. A cross-surface *candidate* is only worth the coordination cost if the
> transfer test is cheap; here it was, and it said no. Record the transfer as **TESTED, NEGATIVE, BOUNDED**
> — never as "demonstrated". The CPU adoption stands on its own CPU evidence and is now **ADOPTED there**
> (operator ruling); the GPU recipe does **not** take the knob.
>
> **Also now settled: the recipe is PER-SURFACE.** One champion, one commit, **two different launch
> recipes**. That is a second worked instance of R23-59 / U3 — `champion.py`/`Bundle` carrying a single
> recipe per champion is under-specified by construction.

- [ ] **U3-SEED — specify the RUNTIME_CONFIG arm type against the THP instance**: session-unit paired
      launches, spread reported with the point estimate, a variance-reduction keep grammar, and the recipe
      hash in the epoch. Blocked on nothing; do it before authoring any RUNTIME_CONFIG hypothesis.
- [x] **U3-DEFAULTS — RESOLVED 2026-09-08: NOT APPLICABLE. R23-58 did NOT confirm the shim on the GPU
      serving path, so it does NOT go into the loop's recipe defaults.** ✅ 2026-09-08. The conditional this
      task was written under evaluated **false**: bounded null, T0/D0, registered action "do not adopt".
      **Do not add `GGML_NOHUGEPAGE_PROCESS` to any loop-launched `llama-server` on the GPU surface** — the
      premise that the loop "pays the OFF variance today" is refuted for that surface (OFF p95_dev 6.657%
      vs ON 9.334%; the ON arm was wider). Closing this as *resolved-negative* rather than deleting it, so a
      later reader does not re-derive the same candidate and re-spend the 27 minutes.
> ### THE RECIPE FORMAT — NOT THE KERNELS — IS THE BINDING CONSTRAINT ON WHAT THIS CAMPAIGN CAN ASK
>
> **Three expressiveness gaps in the recipe schema were found and fixed on ONE DAY, 2026-09-08.** Each one
> surfaced only when somebody asked a slightly new question, and each one made a measurement **impossible**
> rather than merely slow:
>
> | # | research commit | what the recipe could not carry | how it surfaced |
> |---|---|---|---|
> | 1 | `b5f58b74` | **an env var** — so a RUNTIME_CONFIG arm (the THP shim) had nowhere to live, and serving compare reported only the mean | CHAMP-2 needed a launch-time knob and a *spread* comparison |
> | 2 | `4952e95e` | **its own identity hash** — so a floor was keyed by recipe NAME and a gate could be fed a floor calibrated under a different recipe | R23-58 needed floors that could not be silently swapped |
> | 3 | `c3e362a1` | **a self-drafting model** — `Recipe.server_argv` required `spec_decode["drafter"]` unconditionally, so an MTP model raised `KeyError` and **could not be expressed at all** | the Qwen3.6-35B-A3B sweep |
>
> Gap 3 is the sharpest statement of the pattern. MTP carries its draft head *inside the model weights*
> (`blk.N.nextn.*`), so there is no drafter file to name. Absence of `drafter` is now itself the declaration
> that the model self-drafts: `-md`/`-ngld` are omitted and `--spec-type` is still passed. Tests cover both
> shapes and spec=none, **and carry a control proving the negative assertion can fail** (suite 587 → 592).
>
> **The generalisation, and it is a U3 statement:** every one of these was found by *tripping over it*, at the
> moment a measurement was wanted. The schema is the interface between "a question we can ask" and "a question
> we cannot", and it has now failed that test three times in a day. **Do not wait for the fourth question to
> expose the fourth gap** — U3-EXPRESS below is a deliberate pass over the schema instead of a reactive one.
>
> Gap 3 also had an immediate consequence beyond its own sweep: it means the **dense Qwen3.8-27B is now
> expressible as an MTP recipe too** (it carries `blk.64.nextn.*` and `nextn_predict_layers = 1`), which is
> exactly the configuration frozen production supports for that model — the missing PROD-BASE-1 denominator.
> Tracked as **MTP-27B-1** in `autokernel-champion-aggregate.md`.

- [x] **U3-EXPRESS-3 — a self-drafting model is expressible as a recipe** ✅ 2026-09-08
      (research `c3e362a1`: `spec_decode.drafter` optional, `-md`/`-ngld` omitted when absent, `--spec-type`
      still passed; `test_selfdraft_recipe.py` covers both shapes, spec=none, and a fail-control; suite
      587 → 592). Third of the three gaps above; the first two landed the same day as `b5f58b74` and
      `4952e95e`.
- [ ] **U3-EXPRESS — run a DELIBERATE expressiveness pass over the recipe schema instead of waiting for the
      next question to expose the next gap.** Three gaps in one day (env var, identity hash, self-draft), each
      found by tripping over it mid-measurement, each blocking a measurement outright. Enumerate what a
      `Recipe` must be able to express for the surfaces this campaign already runs — multi-GPU / split modes,
      tensor-split and per-device `ngl`, LoRA and control vectors, RPC/distributed serving, per-arm env sets
      (not just one), draft models with their own recipe fields (`draft_p_min`, `draft_n_min`), grammar and
      sampler variants, `--no-kv-offload`/`--cache-type` combinations, and the *absence* semantics that gap 3
      showed can be load-bearing — then write a failing test per gap before fixing any of them. Belongs with
      **U3 (RUNTIME_CONFIG arm type)**: a RUNTIME_CONFIG arm mutates a codified recipe, so the arm type is
      bounded by exactly what the recipe can say. Blocked on nothing.

- [ ] **U3-DEFAULTS-b — carry a PER-SURFACE recipe on the champion record.** R23-58 makes the champion
      `ef81196d5` + *CPU* recipe (shim ON) + *GPU* recipe (shim NOT set). `champion.py`/`Bundle` can express
      one recipe per champion, which is now demonstrably under-specified. Extend the record to key the
      recipe by surface, and make the gate refuse a measurement whose (surface, recipe_hash) pair does not
      match. Ties to R23-59 and R23-55 (`unit`). Blocked on nothing.

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

- **OP-41 RULED (operator, 2026-09-08) — the operator owns this design, and it lands LAST.** The admission-control
  broker is **the operator's own design**, refined through this handoff (INF-73 §3.4); it will be **implemented by
  the operator**, and only **AFTER**, in order: **(1)** the champion is finalised, **(2)** the champion is promoted to
  production, **(3)** the host is rebooted. **No action now** — no broker code, no scheduler, no admission daemon,
  and no session may start building one. Until then the standing behaviour is unchanged: cooperative region-lock
  plus INF-70's bounded-hold requests, with the measured 4.2×/2.9× mutual degradation and the ~17% third-party arm
  tax accepted and labelled, not engineered around.
  - [ ] **U4-SEQ — hold admission control until the operator's three gates clear**, then hand this section's
        evidence (both degradation directions, the 1-in-6 disturbance tax, *"region-lock serialises those who call
        it; nothing constrains those who don't"*) to the operator as the design input. Gates: champion finalised →
        promoted to production → host reboot. Nothing in U4 is buildable before that, and this row exists to record
        the sequencing, not to authorise work.

- **OP-40 IS NOW PART OF OP-41 — ONE item, owned by `ak-rebuild-20260828` (transferred 2026-09-08).**
  INF-70 closed today and, on an **operator ruling**, transferred its **OP-40** (unfenced tooling inside the
  measured region) to this session, where it **folds into OP-41**. They are **one item from here on**, so
  co-tenancy is not tracked twice; INF-70's own record stays readable at
  [`cpu-decode-roofline-program.md`](cpu-decode-roofline-program.md) -> **MEAS-6**.
  - **Both directions, both sides correctly pinned, no rule broken by either.** Their CPU A/A degraded
    **0.80% -> 7.223%** under **our** pinned GPU bench chain; **our** serving floor degraded
    **3.536% -> 10.255%** under **their** lock-holding CPU session.
  - **Attribution caveat — this must never be dropped when either number is quoted, and must not be
    paraphrased away.** The split between *"the chain costs ~6.4 pp"* and *"the drain-era floor was
    optimistic"* is **NOT separable** from those two points; the **CONJUNCTION is what is established**,
    never either limb on its own. **Later evidence favours us**: their quiet floor came back at **0.509%**
    on the adjacent subset — *tighter* than the 0.80% reference — so **their baseline was conservative
    rather than self-flattering**.
  - **The ~17% third-party tax: serialisation is necessary and demonstrably NOT sufficient.** With both
    campaigns serialised on an **operator-mandated exclusive host**, an 8-core `python` plus `opencode`
    (`Cpus_allowed_list=0-191`, belonging to **neither** campaign) still cost an arm at a **1-in-6** rate.
    **Serialising the two campaigns against each other is necessary and demonstrably NOT sufficient.**
  - **The channel is DRAM bandwidth, not cores** — prefill flat within **+/-2%** while decode fell **7%**.
    **No CPU-occupancy screen on either side can see it.** That is precisely why the remedy is **admission
    control rather than a better screen**, and it is the **strongest argument for the U4 broker owning
    process LIFECYCLE on both surfaces**, not merely holding locks.
  - [x] **OP-40 transferred from INF-70 (operator ruling) and folded into OP-41; this session owns the
        single resulting item, and no duplicate row is carried** ✅ 2026-09-08

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
- [ ] CPU A/A calibration: screen floor + serving floor, unit and host-state hash recorded; gating-floor calibration n≥24 with interval (FLOOR-UNIT-1 supersedes the earlier n=20 proposal)
- [ ] **Every floor record carries `unit` (arm | session | process)** alongside harness, n, contention model
      and host-state hash; a gate comparing an effect to a floor of a different unit REFUSES (INF-70 RETEST-1,
      2026-09-08: arm sd 0.501% vs process-launch sd 2.793%; the 1200-fold THP sizing error). See R23-55.
- [ ] **Headline admissibility: ≥N independent launches with a session-unit CI**, N sized from the
      between-session sd (2.793%), not the arm sd; a single-session headline is refused (R23-57)
- [ ] **Investigate the source of between-launch variance on the champion** (page-cache/NUMA placement, THP
      state, HIP graph capture, allocator) — ~12% spread on an identical config, pristine control stable (R23-57)
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
| **OP-41 — RULED ✅ 2026-09-08** | serialize / schedule / regress on CPU co-tenancy | **Operator owns the admission-control design**, refined through this handoff (§3.4), and implements it himself **after** champion finalised → promotion to production → host reboot. **No action now**; until then accept INF-70's bounded-hold requests and label contended arms. |

**OP-41 headline evidence (2026-09-08):** two campaigns, both pinned, lock respected → **4.2× / 2.9×**
mutual degradation via DRAM bandwidth; see §3.4. (Master-index row update owed to its owning session.)

**OP-41 second evidence bullet (2026-09-08, RETEST-1 close-out):** cooperative serialisation **worked and was
still insufficient** — third-party disturbance ran at a **1-in-6 hit rate ≈ 17% tax in arms**, paid only after
the arm was run. *"Region-lock serialises those who call it; nothing constrains those who don't."* This is
evidence for the **admission-control broker** (option A) over any further tightening of the lock protocol;
see §3.4.

| ID | Decision | Recommendation |
|---|---|---|
| UD-1 | CPU serving recipe = the gate for the CPU surface | the CPU session's canonical served recipe (Qwen3.8-Flash-Next), codified as `Recipe`; not a bench proxy |
| UD-2 | promotion granularity | one production candidate carries BOTH surfaces; a surface without a demonstrated gate does not block the other's keeps landing on the champion, but does block promotion |
| UD-3 | who authors CPU hypotheses after U3 | loop planner for RUNTIME_CONFIG/SOURCE on the CPU surface; CPU session keeps diagnosis; revisit after 10 CPU iterations |

## 5b. INF-70's unowned residue — PARKED, explicitly NOT adopted (2026-09-08)

**Why this list lives here and not in the rebuild program.** The rebuild program
(`autokernel-rebuild-program.md`) carries only work **this campaign will execute** — its R23 rows are the
loop's own queue. This handoff is where the **cross-campaign relationship with INF-70** is recorded (§3.4,
OP-41, the OP-40 fold above), so the inventory of what INF-70 left behind belongs beside it. Putting it in
the rebuild program would put unowned items inside an execution queue, which is exactly how silence gets
read as ownership.

**Status of everything below: recorded for DISCOVERABILITY, and NOT OWNED.** This session is **parking**
these, not adopting them. There is **no owner**. Nothing here is scheduled, and no row in any index claims
it. If someone needs one of these done, it needs an owner first.

| item | what it is | pointer |
|---|---|---|
| **PROD-1** | canonical recipe as **importable constants** (not prose). It must now also carry the **THP knob with its unit** and its **distinctness from `GGML_NOHUGEPAGE`** — the two are not the same knob and a recipe that conflates them is wrong. Draft promoted to git | `data/inf70-prod1-recipe-draft-2026-09-08/` (`epyc-inference-research`, commit `1780fa7b`) |
| **MEAS-2** | adopt `build_locked.sh` as the standing build idiom and promote it out of scratch — **19 of 21 build scripts are still unlocked** | `cpu-decode-roofline-program.md` -> MEAS-2 |
| **MEAS-3** | retention row: the `sync16` scratch directory is a **cross-campaign dependency**, not spent scratch | `cpu-decode-roofline-program.md` -> MEAS-3 |
| **MEAS-4** | the instrument **reserves 96 cores to run 48 threads**, and blocks a second agent while doing it | `cpu-decode-roofline-program.md` -> MEAS-4 |
| **MEAS-5** | the **MTP (serving) block is ~2.8x more precise** than the plain block, i.e. **~8x fewer arms** for the same precision — an unclaimed instrument upgrade | `cpu-decode-roofline-program.md` -> MEAS-5 |
| **SYNC-21** | prove or kill the profiler-overhead hypothesis for SYNC-16's null; also tests whether the per-node census systematically overprices cheap single-threaded nodes | `cpu-decode-roofline-program.md` -> SYNC-21 |
| **METH-2** | the back-to-back A/A registration rule **and its own correction** (bracketing is worse than pooling when there is no trend) — a methodology rule with no home outside INF-70's file | `cpu-decode-roofline-program.md` -> METH-2 |
| **NOFOLD-1** | `feature/tree-draft-v6` **MUST NOT FOLD**; the constraint existed nowhere in `handoffs/active/` until INF-70 recorded it | `cpu-decode-roofline-program.md` -> NOFOLD-1 |
| **HYG-2b** | the commit-hygiene hook **still misparses compound shell commands** (and blocks its own idiom) | `cpu-decode-roofline-program.md` -> HYG-2b |
| **G2-CONC** | blocking promotion gate — **must run on the PROMOTION CANDIDATE binary, never inherited from an ancestor** | `cpu-decode-roofline-program.md` -> G2-CONC |
| **UP-1 / UP-2** | **four upstream ggml contributions**, patches **ready and UNSUBMITTED**. Promoted to git so they survive a scratch sweep; submission has no owner | `data/inf70-upstream-patches-2026-09-08/` (`epyc-inference-research`, commit `1780fa7b`) |

Two items from INF-70 were **transferred and ARE owned here** and are deliberately absent from the table
above: **OP-40** (folded into OP-41, §3.4) and the **champion divergence** (filed as **R23-62** in
`autokernel-rebuild-program.md`).

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

<a id="autonomy-design-20260908"></a>

## 8. Autonomy design notebook — 2026-09-08, evolving and documentation-only

### 8.1 Purpose, authority, and accepted decisions

**Session purpose:** collect and refine the plan in this handoff across multiple operator iterations,
including implementation details. Do not implement, deploy, launch experiments, modify production,
or alter running campaigns as a consequence of this section. The operator explicitly clarified:
"by details, I also mean IMPLEMENTATION details" and "We won't actually be implementing the plan
in this session." Retaining concrete designs does not make those designs approved.

The eventual outcome is one standalone AutoKernel service: the operator supplies its resource envelope
and targets, then follows the dashboard. CPU/GPU research, compilation, measurement scheduling, routine
recovery and evidence handling should no longer require two manually coordinated agent sessions.

**Vocabulary:** accepted = explicitly selected/agreed by the operator; observed = dated finding with
source; proposed = engineering design for later discussion; provisional default = suggested number or
policy, not ratified and not a measured performance result. Existing operational policy remains
authoritative until deliberately changed in a later session.

**Binding close-out updates:** `MEASUREMENT.md` INSTRUMENT-CLASS-1, FLOOR-UNIT-1 and BOUNDED-NULL-1
were operator-ratified after the first notebook draft; they are requirements, not provisional defaults.
OP-41 (§3.4) reserves admission-broker implementation to the operator **after champion finalisation →
production promotion → host reboot**. R23-64/65 wait for the operator's BIOS/reboot boundary. The architecture
below is a dependency design, not permission to move those gates earlier. No implementation is authorized
by this audit. Current evidence and corrections are consolidated in §8.16.

| Topic | Accepted direction / preference |
|---|---|
| Compute | Declare CPU, GPU, or both; explore production workloads applicable to those interfaces. |
| Prospective models | Seed a model outside the lineup; preserve production/candidate distinction. |
| Scheduling | **Adaptive, seed prioritized**: initial exploration window, then adaptation with continuing production coverage. |
| CPU experiment size | Smallest informative allocation for the mechanism; no full-host reservation by default for discovery. |
| Transfer | Mechanism-specific applicability; a small-allocation result is not automatically a full-serving gain. |
| Beliefs | Deeper integration for memory, applicability, transfer, invalidation and experiment selection. |
| Friction | Automatic capture, cached routes, asynchronous projection; no extra routine approval/review layers. |
| Runtime fast path | **Deterministic checks** for prevalidated recipe options, without the two critic rounds. New options and code retain review. |
| Dashboard | **Minimal controls**: pause/drain/resume and model/hypothesis seeding; advanced configuration stays in CLI/manifest. |
| This session | Documentation and iterative design only; no implementation authorization. |

Documentation checklist (only these boxes describe this session's work):

- [x] **PLAN-DOC-1** — capture audit, accepted choices, implementation proposals, tests and provisional defaults in the owning handoff. ✅ 2026-09-08
- [ ] **PLAN-DOC-2** — iterate §8 with the operator before converting proposals into an implementation queue. Documentation-only; no compute or deployment authorized.
- [x] **PLAN-DOC-3** — audit both final September 8 close-outs and refine the notebook with evidence-scoped implementation contracts and tests (§8.16). ✅ 2026-09-08
- [x] **PLAN-DOC-4** — fresh independent audit; reconcile protocol/cadence contradictions and delineate scheduler, evidence, validation and lifecycle implementation contracts (§8.17). ✅ 2026-09-08

### 8.2 Dated audit findings and corrections

The audit covered August 25–September 8 reports and inspected the newer research lane
`/mnt/raid0/llm/worktrees/mains/ak-rebuild-research` (`bdfab023`) and research `origin/main` (`624adbdd`)
during that pass. The shared research checkout was behind those refs. Code-present, merged and loaded
in a process are separate statements. Resolve symbols at the recorded revision and current code before
implementation. This planning session ran no new benchmarks and re-certifies no historical percentages.

| Finding | Evidence / correction | Design consequence |
|---|---|---|
| Builds contaminated CPU arms | [Sept 7 co-tenancy audit](../../progress/2026-09/2026-09-07-ak-rebuild-20260828.md): build `96–183` shares cores with bench `0–95`; some manual builds were also unpinned/unlocked. | Broker all build paths; do not attribute all contamination to one session. |
| Seven workers did not mean seven concurrent builds | `loop/pipeline.py::SerializedTail.session` serializes build → oracle → A/B → commit; `run.py::gate_for` documents its `jobs=64`. | Preserve ancestry protection; process-local serialization does not protect external CPU experiments. |
| Threads are not physical allocation | [CPU roofline handoff](cpu-decode-roofline-program.md), C5/B2/MEAS-4: `-t 48` in a 96-core reservation, OMP spread, interleaved memory. | Fewer threads spread over the host do not prove a NUMA-local quarter equivalent. |
| Disjoint cores still share bandwidth/fabric | CPU roofline C0 concurrent node-local streams; this handoff §3.4 later DRAM contention. | Core locks alone cannot certify measurement coexistence; compare against quiet controls. |
| Wrong screening workloads | [Sept 1 transfer study](../../progress/2026-09/2026-09-01-ak-rebuild-20260828.md), [Sept 3 retargeting](../../progress/2026-09/2026-09-03-ak-rebuild-20260828.md): quantization, dimensions and speculative verify changed dispatched kernels. | Preserve shapes/dispatch; same quant label or a smaller model is insufficient transfer evidence. |
| NUMA/stale builds/dead controls masqueraded as kernel behavior | [Sept 2 audit](../../progress/2026-09/2026-09-02-inf70-audit.md), [Sept 5 audit](../../progress/2026-09/2026-09-05-inf70-audit.md). | Bind actual build/library, placement and effective path, not just source or requested env. |
| Transfer depends on mechanism and composition | CPU roofline SYNC-17 and final plain→MTP correction: tiny parallel work may lose to serial; universal transfer divisor retracted; later keeps change prior benefits. | No timeless class multiplier; small-only nulls cannot retire scale-sensitive ideas. |
| Persistence fix retained unsafe recovery in inspected code | `loop/accumulate.py::save/load_bundle`: direct write; missing/corrupt/lineage-invalid state sets cor=anchor; advanced tip retains old gain. | Replayable state; no implicit confirmation; invalidate affected values. Reinspect before fixing. |
| Serving metric/statistics differed from labels | `loop/serving.py`: sums per-request rates; always A then B; calibration uses individual-run deviations. | Separate metric identities, counterbalance, calibrate the actual estimator; incompatible floors cannot transfer. |
| Source fixes were not deployed-contract proof | [Sept 8 report](../../progress/2026-09/2026-09-08-ak-rebuild-20260828.md); ~09:47 UTC snapshot: running, age 879 s, budget 1800 s, no step/actor_health, health ok. | Snapshot does not prove a stalled process; new producer contract was not exposed then. Show loaded version and independent health axes. |
| New heartbeat had lifecycle/progress gaps | Inspected `run.py`: heartbeat always writes running, stop event not set/joined, claim/profile failures outside failed handler. Hub `panels.py` shares silence/progress budget; `loop_status.py` watermark omits stage. | Single status writer, terminal ordering, separate heartbeat/stage/science clocks. |
| Belief wiring largely covered older producers | Current loop reads local archive; legacy execution has capture. `ClaimTuple.to_frames` omits value/unit/extra; `UsePolicy` lacks workload matching. | Current-loop prospective capture + typed applicability; grade alone cannot establish transfer. |
| Resource plumbing requires reconciliation | `instance_topology.py::parse_cpu_list` drops IDs >95; cross-role global locks already exist. Ratified daemon authority differs from inspected inference-only/disabled-GPU config. | Fix normalization and existing provider path; no self-grants or second build-lock authority. |
| Serving contention allowance is not experimental equivalence | Existing contention provider allows bounded serving degradation. | Separate research coexistence use; do not turn serving allow into measurement-isolation proof. |

**Later consolidation supersedes early state:** P1 records fold `ef81196d5`, a real serving gate,
pin/recalibration and **UNCONFIRMED** bundle with cor held at `445e93a8`. Thus "gate never fired",
"pin not activated", "fold pending" and "run 30 live" are historical. Do not undo that work or seed
a new lineage. Remaining source findings require current-code reinspection, not an assumption that
another session has not fixed them. Root handoff snapshot at capture: `e5d1846d`.

### 8.3 Proposed architecture and loop

One service owns campaign state; coordination policy owns grants; broker suballocates within them using
existing physical providers. Actors own hypotheses/changes; adapters own execution/validity; journal owns
durable transitions; Vidya owns evidence/relationships; dashboard projects state and submits typed commands.

```text
START
  resolve manifest + registry snapshot + candidate seeds
  recover journal, desired state, candidate and validated evidence
  request authority and physical claims through existing policy
WHILE active
  apply controls at boundaries
  scheduler chooses target using coverage, cost, seed priority and scoped evidence
  if prevalidated runtime combination:
    deterministic recipe/compatibility checks; no critic calls
  else:
    planner reads current profile + scoped history + cached beliefs + inbox
    forms hypothesis and mechanism annotation
    existing critic pass 1: objection -> exact reason to planner
    author source/build/novel-recipe change
    existing critic pass 2: objection -> exact reason to author
  choose cheapest informative route; unknown transfer permits scoped exploration
  resolve phase/protocol/category/use and freeze its ExperimentPlan
  broker admits build if needed, correctness, load/place/warm/profile, comparison
  compile/correctness failure -> tool reason to author, separate bounded retry budget
  classify interference under phase/protocol -> retain noise or invalidate/checkpoint as authorized
    ordinary foreign load is recorded noise, not a search-admission veto (P-AK-SEARCH-1-A2)
  unavailable actor/resource -> other eligible work, or release claims and wait visibly
  stale parent -> superseded, preserve idea, rebase/retest; not refutation
  discovery completed -> advisory nomination only; schedule separate strict confirmation if selected
  completed valid comparison -> typed scoped conclusion for planner
    inconclusive / direction_only / estimated_effect / bounded_null / regression
    purported null missing power record or fired-mechanism control -> untested, no negative warrant
    valid measured contrast with inadequate resolution -> inconclusive; preserve data/uncertainty
  strict-confirmed eligible experimental keep -> integration lock, parent check, intent, commit, completion
  due validation batch -> assembled candidate + serving + required LOO; evidence matrix
  advance validated record only after applicable production-serving rows pass at exact identities
    bench/non-production BASELINE rows remain research/addenda, not production vetoes
BACKGROUND
  native journal -> local memory/status -> async Vidya/index projection
  supervisor -> bounded recovery; broker-aware storage maintenance
```

Retain existing independent hypothesis/patch review budgets. No additional reviewer or per-attempt
protocol-writing step. Runtime fast-path approval is the accepted exception. Tool failures return to
the author without another critic ceremony. Retiring an attempt does not retire its idea. Build and
measurement are expensive brokered stages; correctness/validation follow where they need produced output.
Brokered probes replace uncontrolled actor host compute, without requiring an operator for each probe.

### 8.4 Proposed campaign and target interfaces

Proposed supported commands, not installed by this update:

```text
autokernel start --manifest campaign.yaml
autokernel status --campaign ID [--json]
autokernel pause --campaign ID
autokernel drain --campaign ID
autokernel resume --campaign ID
autokernel seed --campaign ID --file seed.yaml
```

Manifest declares campaign/consumer, requested CPU regions/affinity and GPUs, build job/memory/disk
limits, duration/budget or continuous mode, production selectors and seeds, configured actors/explicit
fallbacks, recipes/objectives/acceptance-policy refs, scheduling/validation and control-access settings.
Resolve an immutable launch snapshot of registry/model/recipe/topology/policy/instrument/controller
identities. Dry-run before admission; no silent active-campaign change when registry or checkout moves.
Report requested, granted, physically held and actively used resources separately.

Target records bind model/hash, architecture/tensor census, backend/kernel tree, context/concurrency,
speculation/drafter, environment, metric/direction, correctness and regression requirements, route and
calibration refs. Key recipes by target/surface/operating mode, not one global recipe or backend alone.
Deduplicate roles only on complete workload-signature equality. A seed creates its own
candidate target without changing production or inheriting another calibration. If production cannot
load it, use the first compatible experimental build as exploration baseline, never a fabricated
production delta. Missing artifact blocks only that target; others continue.

**Proposed v1 scope:** llama.cpp CPU/GPU first, retaining per-kernel-tree identity for future speech;
local artifacts and registered references first. Remote downloads, requantization and lineup edits
are outside this proposed v1, subject to operator iteration. Do not silently dismiss a source/model as
inapplicable. Candidate rows are advisory unless explicitly included in the required validation set.

### 8.5 Proposed durable event model and migration compatibility

Reuse `scripts/kernel_rnd/autokernel/journal.py`: fsynced append, validation, torn-tail recovery and
durable cursors. Extend narrow current-loop kinds; do not restore the old deployment factory or create
another WAL/outbox. Current-loop records must not manufacture legacy `evaluation_event.v5` receipts.

| Record group | Automatically captured fields |
|---|---|
| Identity | campaign/hypothesis/attempt/execution, actual measured source/build/object digests, intended delivery candidate, compiled defaults and effective runtime state, recipe-map entry, target/model, instrument/protocol. |
| Scope | backend/architecture, quant/dispatch/op shapes, serving recipe, threads, physical cores/siblings/NUMA, placement, grant, neighbor envelope. |
| Measurement | instrument_class (bench/serving), category (OPTIMUM/BASELINE/CANDIDATE), phase/protocol_ref and record_class, metric/direction/physical unit/value, comparison_kind and changed factors, raw artifacts/hashes, estimator version, order/block and stopping plan, independent experimental unit/IDs, attempted/completed/valid/scored counts, window timestamps. |
| Validity | correctness/effective path, loaded-library/residency, contamination/drift/refusal; invalid timing never becomes a null. |
| Annotation | planner mechanism class and uncertainty, explicitly not measured fact. |
| Conclusion | estimand (level/dispersion/etc.), conclusion type, permitted claim strength, interval/power and effect-size bounds, both-direction fired-mechanism control refs; lack of significance alone is not a bounded null. |
| Relationships | reduced->target transfer, quiet->overlap, individual->assembled benefit, supersession/retraction, original evidence IDs. |

Mint attempt ID before execution; retries have separate execution IDs. Related arms retain their
shared support/independence grouping. Keep large data in references, not copied into each projection.
Capture facts from launchers/instruments rather than asking an actor to author evidence paperwork.

Journal is authoritative; SQLite history, Bundle JSON, Markdown memory, status and belief index are
projections. Integration: record `keep_intent` (attempt/parent/tree) -> integration lock/current-parent
check -> commit with attempt trailer -> `keep_committed` -> projections. Replay reconciles exactly once.
An unexpected tree advance preserves code but clears affected measurements; it cannot silently confirm.

Derived files use temp/write/fsync/rename/directory fsync. Missing/corrupt Bundle replays journal;
insufficient evidence means last provable validated head or `validation_required`, never cor=anchor.
Local journal failure stops new irreversible transitions and drains; downstream Vidya/dashboard failure
does not. Preserve legacy records as history; do not infer missing write-side provenance on read.

### 8.6 Proposed broker and resource foundation

**Sequencing constraint:** the operator owns admission-control implementation and its post-promotion,
post-reboot gate (§3.4). These interfaces are retained as design input only. Until that gate clears,
existing cooperative locks and bounded-hold coordination remain; this plan creates no scheduler/daemon.

```text
acquire(StageRequest) -> AllocationReceipt
launch(AllocationReceipt, ExecutableRequest) -> OwnedProcess
release(AllocationReceipt, outcome)
drain(reason) / resume() / recover()
```

Requests bind stage, CPU affinity/GPU set, memory/build limits, workload signature, bounded duration and
coexistence profile. Reuse lease/provider open/close fields. Reconcile inspected config with ratified
D4 and verify the actual grant/activate/renew/release path; never impersonate inference or self-grant.

Normalize CPUs using discovered sibling topology, not dropping 96+ or assuming historical NUMA labels.
Proposed v1 keeps four existing region claims: a microtest can use fewer cores while reserving its
containing region. No second fine-grained lock authority. Reuse cross-role global exclusion; build is
attribution, not a private nonconflicting namespace.

Broker ALL compute: candidate/anchor/validation/recovery builds, correctness/profiling, load/place/warm,
calibration/bench/serving/ablation. Enforce limits on descendants and bound/account actor local work.
Multi-resource acquisition uses deterministic order and releases partial claims on failure. External
grants cover useful batches, not a bus transaction per hypothesis/compiler. Internal admission uses one
broker lock. Preserve current tail serialization until immutable-base stages and integration locking
can reject/rebase/retest superseded candidates safely.

Check control/grant validity at every expensive stage, including queued work. No new bounded stage
past expiry without acknowledged renewal. Follow existing grant drain semantics, invalidate incomplete
evidence and manage only owned PID-start/process-group/cgroup identities. Never name-pattern kill or
delete locks. Release claims during no-runnable-work outages and reacquire through policy on recovery.

### 8.7 Proposed partition routes and coexistence profiles

Correctness transfer, reduction of local work, and end-to-end speedup transfer are separate claims.
Fewer threads across the host are not a smaller physical allocation: cache/CCD distribution, memory
placement, per-thread shape, clock and dispatch can change. More production threads are not inherently
better; final validation targets the best intended serving recipe, not all cores by definition.
The final MEAS-4 correction establishes that t48 was a measured optimum in earlier recipes, spread over
all 12 CCDs/four NUMA nodes—not an arbitrary half-instance or a contiguous unused half. That optimum need
not survive changed dispatch costs or BIOS settings. R23-64 owns the gated re-sweep; topology-shaped
partition discovery remains a separate experiment from simply lowering `-t`.

| Family | Proposed cheapest informative route | Transfer limitation |
|---|---|---|
| Local SIMD/arithmetic/redundant work/dispatch | Op test in one quarter preserving production shapes/quant/path; then target model on reduced allocation. | Benefit may disappear when serving becomes bandwidth-bound; never assume same percentage. |
| Copies/traffic reduction | Small allocation retaining relevant memory level and representation. | Cache vs DRAM and preprocessing cost change the claim. |
| Blocking/prefetch/layout/repack | Match working set, cache, placement and dispatch. | Same quant label is insufficient; cache route only under matching dependencies. |
| Barriers/scheduling/partitioning/NUMA/scaling | Representative thread/topology geometry. | Small-only null cannot retire a scale-sensitive idea. |
| Unknown/mixed | Safe exclusive exploration, uncertainty recorded. | Missing transfer/classification is not a blocker to all experimentation. |

Prefer actual target on fewer cores over a tiny model that changes the kernel under study. Intermediate
sizes are optional tests of a specific scaling uncertainty. Periodically sample rejected small-screen
candidates to detect false negatives; rate/selection remain proposed design choices.

**Transfer and coexistence are independent:** predictive partitions may still be contaminated by a
compiler, and isolated tests may still mispredict serving. Research profiles bind workload+neighbor,
allocation/pressure bounds, topology/runtime dependencies and quiet-versus-overlap evidence. Store them
through the existing contention provider, separately from serving-throughput allowances.

No profile means serialize incompatible **owned** work under its applicable admission policy, not seek
operator approval or veto search for ordinary foreign load (§8.17A). Cache validated routes and
profiles until relevant dependency/declared expiry/drift changes. Telemetry alone is not absence proof
for fabric/DRAM interference: certify against quiet controls and monitor the envelope DURING arms,
including placement/warmup/residency. Apply the protocol's predefined disposition: recorded search noise
can widen reported uncertainty, not an acceptance threshold; invalidate/repeat only on that protocol's
actual invalidity conditions. No selective favorable samples. Indexing/hashing/cleanup/actor CPU are
neighbors too. Quiet/overlap profiling is a separate planned experiment, not an ad hoc quiet-host demand.

### 8.8 Proposed adaptive scheduling and independent budgets

Adaptive seed priority and production coverage are accepted; algorithm/numbers below are provisional:

- Weighted deficit scheduling by held physical-region and GPU-device time, including GPU stages' CPU
  claims; retain the resource vector and charge load/warmup/build/validation, not just timed inference.
- New target weight 2 until three valid comparisons **or** a finite charged-time/attempt cap; normal
  weight 1; one boosted seed/backend, FIFO. Duplicates earn no new boost (§8.17D).
- Thereafter weights bounded 1–3, revisited every ten valid comparisons using target-scale confirmed
  outcomes, not screen gains alone. Exact update formula remains open for iteration.
- Bounded production-coverage rounds and reservations supplement weights; §8.17D defines the service
  bound and eligibility/outage assumptions. Bound the ready queue to limit obsolete work.
- Calibration and validation are explicit budgeted work, not unbounded priority. Invalid arms/outages
  cost operational budget but are not scientific nulls. No runnable backlog -> release and wait visibly.
- Count informative bounded transfer negatives and precision improvements as research outcomes, with
  their scope/power retained; do not reward only positive mean-throughput keeps. Forecast measurement
  cost from completed independent units under the current recipe, not a retired recipe's spread.

Separate provider retry, hypothesis review, patch repair, contamination retry, calibration, serving/LOO
and campaign budgets. Learn cost from observed stage durations. Report exclusion, resource waiting,
actor waiting and no-eligible-work separately. Optimize valid research per budget; contaminated hardware
saturation is not productivity. §8.17D supplies the proposed deterministic algorithm; numerical budgets
and adaptive coefficients remain for iteration, not unstated runtime defaults.

### 8.9 Proposed runtime fast path and measurement repairs

Versioned recipe option sets declare supported model/backend, argv/env mapping, compatibility and
effective-path witness. In-contract combinations are deterministic, reuse binary, skip critic calls,
and use ordinary correctness/measurement. New options/arbitrary env/build/source changes retain review.
Flag acceptance is insufficient: detect absent compiled knobs, no-op controls, unexpected fall-through
or op coverage. Runtime recipe hashes are part of experiment and champion identity.

Serving instrument proposals:

- Version common-window completed-token throughput separately from sum-of-slot decode rates.
  Exclude declared startup/warmup from the metric but charge scheduling; retain production concurrency
  and speculation. Report request latency, and TTFT via suitable streaming capture if adopted.
- Counterbalance AB/BA and use identical declared estimator for A/A calibration and comparisons.
  Calibrate its actual distribution at the independent arm/block count, not individual-run deviation.
- Floors bind model/resolved recipe/metric/estimator/instrument/placement/coexistence and independent
  `unit ∈ {arm, session, process}`. A gating-floor calibration requires **n≥24 and an interval**, not
  just a point; missing/cross-unit floors refuse. This minimum is for calibration, not every experiment.
  Preserve historical dispositions; older floors acquire rederivation debt, not retroactive re-verdicts.
- Register fixed N **or a complete sequential look/stopping plan** before execution using reusable
  protocol templates; no outcome-chosen extension. The CPU two-look sign test is a worked example,
  not a reason to ban registered early stopping. Direction-only evidence cannot mint a magnitude.
- Replay stored samples through the declared estimator/version once per immutable calibration and
  applicable policy identity; cache the validated result for routine arms. Require reproducibility
  before gate use. A differing quantile convention/normalization is not rounding to accept
  silently. Changes cannot inherit an incompatible floor; n≥24 alone does not guarantee useful precision.
- Preserve attempted/completed/valid/scored counts; prompts within one arm and reuse of the same
  treatment arm do not manufacture independent samples. Pairing alone does not prove contamination cancels.
- Preserve correctness/library/dispatch/residency evidence; search cannot edit its measurement policy.
- Dispatch comparator by **estimand**, not only experiment type: same-binary env arms can test level
  and/or dispersion without rebuilding. Emit separate conclusions; a nonsignificant level contrast does
  not answer a tail-compression hypothesis. A null needs power/bounds and both-direction mechanism controls.

Exact per-target objective/window, estimator, calibration design, non-regression/equivalence margins
and legacy metric migration remain explicit discussion items, not accepted thresholds. Reinspect source
and run controls before implementing a repair; do not widen policy to fit observed noise.

### 8.10 Proposed champion evidence matrix and validation cadence

Distinguish accumulated source+recipe candidate, last globally validated candidate+recipe record, and
current frozen-production comparator. Matrix rows bind actual measured build and proposed candidate,
model/backend/operating mode/resolved recipe/metric/
instrument, correctness, validity and effect. CPU pass cannot certify GPU; runtime keep changes identity
even with unchanged source SHA. A new candidate cannot reuse earlier combined-candidate rows for its own
manifest; those rows remain valid for their original immutable batch, as do per-change historical findings.

Proposed global validated advancement waits for required **production-optimal serving** rows at identical candidate
identities. §8.17C explicitly replaces §3.0's proposed any-surface/shared-cor transition with an immutable
validation batch and one atomic advancement; existing policy remains until adoption. Preserve required
re-baseline/LOO rules. Missing resources hold their
validation rows while scoped research continues. Candidate models are advisory unless explicitly required.
Absolute headlines require serving-class evidence with its registered recipe and protocol status visible;
bench relative comparisons remain on their own surface, never cross-class ratios or conversion factors.
Non-production BASELINE and bench cells that cannot exercise the registered recipe are addenda, not
production promotion vetoes (MEASUREMENT.md §5). Products of solo gains remain estimates.

Retain compound-then-gate and the **already-ruled four-keep cadence**, OR the configured gain trigger
(R23-54; research `56195d3e`, `SERVING_GATE_EVERY_KEEPS=4`). The durable counter resets on every completed
gate run regardless of outcome; trigger reason is threshold/cadence/both. No calibrated floor means no
serving spend under the existing guard. A proposed additional 24-hour due signal is for iteration, not a
replacement for four keeps and never weaker acceptance. §8.17C separates that counter from outstanding
validation debt. Budget required LOO at validated advancement over assembled
candidate/required surfaces. Neutral/inconclusive removal evidence does not automatically justify deletion.
Record drops with evidence; resulting new candidate needs applicable validation. Do not globally discard
dormant quant-specific improvements based on another target's null, or seed from production mid-cycle.

### 8.11 Proposed low-friction Vidya integration

Reuse the already-filed **VB-INF70-ARMS / SC75** source/task for CPU arm capture; do not recreate it.
At future implementation start, register any distinct current-loop capture source in
[`scripts/vidya/adapters/README.md`](../../scripts/vidya/adapters/README.md) and link its task in
[`vidya-belief-substrate-program.md`](vidya-belief-substrate-program.md). This documentation update
creates no measurement producer and claims no new hook. Adapter verifies original artifact identities,
projects into `ClaimTuple`, and delegates to existing `grade()`; no new ladder. Invalid attempts stay
operational records. Typed versioned applicability projection links value/unit/scope/dependencies to
event/claim/evidence IDs without dumping arbitrary extra into legacy frames or changing their IDs.

```text
retrieve(target_scope, mechanism?, intended_use, limit=40)
  -> exact | supported_transfer | hypothesis_only | incompatible
     findings, scoped nulls, transfer links, conflicts/staleness,
     missing-evidence suggestions, snapshot frontier and reasons
```

Quality and applicability filter independently. Supported transfer requires recorded source/target
comparisons; class labels are priors. Unknown historical scope cannot certify overlap/exact transfer.
Apply warrant/epoch rules by record class and intended use (§8.17A/E). Cross-epoch P-AK search history
can supply attempted mechanisms/conclusions, **not comparable numerical values** (A3). Separately, the
operator permits pre/post-BIOS absolute serving observations: show those rates under their actual
authority, while simultaneous changes limit causal attribution and changed dispersion requires new floors.

Async consumer tails journal at a durable cursor, ingests deterministic IDs, advances on acknowledgment,
quarantines malformed events individually and publishes an atomic local index. Planner reads once per
proposal batch plus unprojected local attempts to avoid immediate repeats. No network query per arm,
compiler or scheduler tick, no corpus rescan per iteration, and no additional LLM call for classification.
Use existing journal as outbox, not another delivery ledger.

Vidya outage permits fresh local measurements and established safe exploration; new overlap requiring
missing evidence falls back to serialization. A validation decision waits on its own evidence, not all
research. Recovery catches up idempotently. Invalidate topology/neighbor->coexistence, recipe/instrument
->calibration, model/shape->matching, relevant code/dispatch->transfer, candidate->combined validation.
Age alone is not universal invalidation. Retain scoped history and supersession/retraction reasons.

Provisional targets: query p95 ≤100 ms on 100k events; normal lag ≤30 s outside quiet windows; batch
≤100 events or five seconds; added bookkeeping <1% of campaign wall time with denominator reported.
Append at lifecycle boundaries, not tokens; never weaken fsync for a target. Hash immutable verified
artifacts once and cache; broker/suspend heavy projection/hashing/cleanup around quiet windows. Accepted
nonnumeric constraint: zero added routine operator interactions or critic calls for established sweeps.

### 8.12 Proposed standalone lifecycle, dashboard and storage

Small research-owned supervisor wraps existing engine, independent of tmux/monitoring agents/orchestrator
API. Coordination grant service remains necessary for new authority. Avoid old controller custody machinery.
Persist desired state separately from observed worker state. Proposed states: starting, recovering,
running, waiting_resource, waiting_actor, paused, draining, drained, validation_required, failed, complete.

- Pause closes new admissions, completes safe active work and releases compute when quiescent; service remains.
- Drain closes admissions, completes or invalidates bounded work, stops workers and releases claims.
- Resume reconciles identities and reacquires authority/claims; paused state survives restart.
- Actor outages honor reset/retry hints, otherwise bounded exponential backoff; repeated identical
  failure becomes visible cooldown, not spin. No silent model/provider changes outside explicit fallback list.
- Recover owned children using PID-start/process-group/cgroup identity, not names/stale JSON. Respect
  valid long-running measurement drain boundaries and make partial invalidation visible.

CLI/UI share typed idempotent commands, requested -> applied/refused(reason); daemon is sole writer.
UI says pending until acknowledgment. Duplicate clicks/reconnect/concurrent requests cannot duplicate
seeds. Keep /loop in existing hub, registered health/freshness. Proposed **research-producer-owned**
gateway uses owner-only Unix
socket plus token-paired browser session, token+trusted origin for writes, no credentials in URL, no
arbitrary shell/executable request. Current GET/CORS is not authentication. Token lifecycle/storage and
gateway detail remain design choices; minimal controls are accepted. Browser contacts the producer
directly; the hub owns page/nav/registry and does not proxy commands or acquire broker authority
([plane rule](../../dashboard/README.md)). Advanced configuration stays in CLI.

Display loaded producer/schema/instance, heartbeat, stage/activity/deadline, last valid scientific result,
actor last success/retry/reset, requested/granted/held/used resources, target/seed coverage, refusal/
contamination/supersession, accumulation vs validation, evidence age/projection lag and exact prerequisites.
Fold actor/evidence availability into health; HTTP reachability is separate. Proposed heartbeat 30 s and
missing-producer deadline 180 s do not define stage progress. Single synchronized writer stops/joins
the worker's status publisher before terminal publish and covers startup claim/profile and shutdown
errors; the retained supervisor heartbeat remains live (§8.17G). Verify loaded
version, not just source commit, when claiming deployment.
Scientific cards also expose instrument class, actual measured artifact, resolved recipe, independent
unit, n/interval, protocol/calibration status, and supported conclusion strength. Separate single-user
rate, highest **measured** aggregate point and selected operating point; never label a sweep endpoint
as an established ceiling. Preserve historical sum-of-slot-rate identity until a versioned metric migration.

Reserve space before builds; protect active, validated and in-flight/referenced generations (absolute
RUNPATH means copied builds need original paths). Reclaim only explicitly unreferenced disposable
artifacts through recoverable operations, never age-only guesses. Keep source/recipes/journal/results
durable; rotate logs and bound campaign-owned actor storage. Maintenance is brokered; disk pressure
pauses storage-heavy admissions while reporting/control remain. Do not prune unrelated users' databases.

### 8.13 Proposed work packages and existing-task mapping

**NOT A DISPATCH QUEUE.** IDs retain implementation detail for iteration; no new implementation
checkboxes are created. PLAN-DOC-2 owns review. P1/P1b consolidation remains its owners' operational work.

| Proposal | Deliverable | Dependencies | Acceptance / existing mapping |
|---|---|---|---|
| AK-AUTO-01 | Reconcile code/fold state and dated findings | — | No stale live claims; final aggregate anchors future launch; preserve P1/P1b. |
| AK-AUTO-02 | Native current-loop journal and safe recovery | 01 | Keep replay once; corrupt bundle cannot certify; expands R23-51. |
| AK-AUTO-03 | Topology and policy/claim-provider path | 01; OP-41 operator gate | Sibling affinity conflicts; standalone activate/renew/release; design dependency does not move broker implementation ahead of promotion/reboot. |
| AK-AUTO-04 | Manifest/target enrollment | 01 | CPU/GPU/both/candidate resolve without lineup mutation; P2 expansion. |
| AK-AUTO-05 | Broker all compute/build paths | 02,03,04; OP-41 operator gate | Operator-owned implementation after finalisation/promotion/reboot; no unlocked build paths or queued-stage expiry gaps in eventual acceptance. |
| AK-AUTO-06 | CPU adapter and serving repairs | 04,05 | Explicit metric/calibration/units and witnesses; recheck fixes; P2. |
| AK-AUTO-07 | Runtime fast path and mechanism routes | 05,06 | No extra critic calls; scale-sensitive null not globally retired; P3. |
| AK-AUTO-08 | Prospective Vidya and scoped local retrieval | 02,04 | Typed scope, idempotence/outage recovery, unchanged grader; reuse SC75 and register only distinct current-loop sources. |
| AK-AUTO-09 | Certified coexistence/adaptive scheduling | 05,06,07,08 | Cache reuse, uncertified incompatible owned work serialized under policy, seeds advance and production not starved; P4. |
| AK-AUTO-10 | Evidence matrix/batched serving/LOO | 02,06,08 | One surface cannot certify others; assembled evidence; P2/R23-48. |
| AK-AUTO-11 | Supervisor/minimal authenticated controls | 02,04,05 | Persistent idempotent lifecycle, honest health, bounded recovery; proposed replacement for P5 endpoint. |
| AK-AUTO-12 | Migration/bounded live run/unattended acceptance | 07–11 | Tests below, no monitoring agent required for routine recovery. |

Retain one INF-73 row; future implementation reuses existing task text/owners instead of duplicating
P2–P5/R23/FOLD checkboxes. Update normative loop description only when adopted. Do not rewrite measurement
constitution or compute-authority policy as a side effect of this documentation update.

### 8.14 Proposed tests, migration and completion criteria

| Area | Test scenarios |
|---|---|
| Recovery | Crashes around intent/commit/completion/checkpoint; corrupt/missing bundle, torn tail, replay/cursor, disk full, missing artifact, branch movement; exactly one keep and no false validation. |
| Candidate concurrency | Two racing keeps -> one integrates, one superseded/retested; runtime change cannot reuse source-only evidence. |
| Claims | Sibling-only affinity, cross-role conflicts, partial acquisition rollback, denied/disabled provider, renewal/expiry, queued build after pause, orphan recovery; no lock deletion. |
| Coexistence | Serving allow not research proof; unvalidated shared DRAM serialized; stale topology invalidates; quiet controls detect bias even when occupancy looks clean. |
| Statistics | Instrument-class separation; unit and n≥24/interval floor admission; replay equality; registered sequential looks; level vs dispersion; complete screened units only; power plus both-direction controls for bounded nulls. |
| Transfer | Same threads/different topology, same quant/different shape/dispatch, absent/supported/refuted transfer, scaling null not global rejection, composition-dependent invalidation. |
| Beliefs | Legacy frame IDs/grader unchanged; scope retained, epochs not pooled, quarantine, replay equivalence, outage safe exploration and idempotent catch-up. |
| Controls | Duplicates/concurrent CLI/UI, paused/draining restart, unauthorized writes, browser disconnect, no silent actor fallback, orchestrator-API outage. |
| Health | Long healthy stage vs stalled child, quota/auth/malformed output, producer death with live hub, hub restart, terminal overwrite prevented, loaded-version proof. |
| Storage/overhead | Referenced RUNPATH generation protected; maintenance obeys quiet windows; projection/retrieval and campaign overhead measured; no routine extra review/operator steps. |

Proposed migration: isolated pinned runtime -> inventory final champion/bundles/recipes/evidence -> import
legacy observations without retrofitted warrant -> preserve rollback stores -> authorized owner boundary
-> initially serialized broker -> partition routes -> only certified overlaps -> adaptive scheduling/
controls after bounded checks. This does not authorize a stop/relaunch now; cutover remains separate.
The broker step is additionally held behind the operator's finalise → promote → reboot sequence;
R23-64/65 and new post-BIOS calibration dependencies remain explicit rather than inferred completed.

Proposed acceptance: bounded mixed run, then **48-hour** unattended soak with production CPU, production
GPU and seeded local candidate. Source/build and prevalidated runtime routes; **ten valid comparisons
per active backend**, target-scale confirmation (valid null acceptable), useful overlap under one certified
profile; actor/worker/dashboard/Vidya faults and pause/drain/resume. Duration/counts are provisional.

Eventual completion: no routine manual relaunch/monitoring agent; no unlocked builds, protocol-invalid
units accepted as evidence, implicit confirmation, false full-scale transfer, or eligible-production starvation; seed progress;
no extra critic calls for established sweeps; visible bounded overhead; durable reproducible candidate
and truthful dashboard. Positive kernel gains are not required to prove the service works.

### 8.15 Provisional defaults and next discussion

Accepted directions are in §8.1; the operator did not approve every number/detail in the previous draft.

| Proposed detail | Open refinement |
|---|---|
| Local artifacts / llama.cpp-first v1 | Remote enrollment and speech-adapter scope. |
| Four claim regions, sub-quarter execution | Discovered topology and actual concurrency; region is not assumed to be NUMA node. |
| Seed 2×/three comparisons; weights 1–3/ten-result update | Exact formula, normalization, starvation and repeated-null/futility policy. |
| Sample small-screen rejects | Rate and selection avoiding expensive universal confirmation. |
| Existing gain trigger + **ruled four-keep cadence**; proposed 24-hour addition | Only the time trigger/new multi-surface budgeting remain provisional; preserve R23-54. |
| Global validation before shared cor advance | §8.17C specifies the replacement transition and LOO semantics; not yet adopted/implemented. |
| Common-window throughput / counterbalanced comparison | Objective, estimator/calibration, margins and legacy migration. |
| 30 s lag; 100 events/5 s; query 100 ms at 100k; overhead <1% | Feasibility, denominators, quiet-window behavior, invalidation dependencies. |
| Heartbeat 30 s / missing 180 s | Independent stage/activity and retry deadlines. |
| Socket + token-paired browser controls | Token lifecycle and gateway security without per-command ceremonies. |
| 48-hour / ten comparisons per backend soak | Workload/cost and fault schedule; positive gains unnecessary. |

**Next action here:** iterate these implementation details with the operator and update this notebook.
Do not run proposed work packages or turn defaults into new approval friction. The broker enforces
allocations; belief-backed mechanism awareness should make choices cheaper and less conservative while
preserving the distinction between permission to explore and evidence sufficient for production claims.

<a id="final-closeout-audit-20260908"></a>

### 8.16 Final-close-out audit — refinements to implement later, not a new execution queue

**Audit basis:** root `2a710cab`, both final September 8 progress records, the committed CPU close-out
packet, GPU sweep and R23-58 receipts, and targeted source inspection. Research shared checkout inspected
at `6ab403ed`; self-draft support separately inspected at `c3e362a1`. No benchmarks, servers, builds,
reboots, policy amendments or deployment changes were performed. This section refines the implementation
notebook; it does not adopt §5b's unowned residue or reopen either closed research session.

#### A. Evidence that changes the plan

| Final finding | What follows for unified AutoKernel |
|---|---|
| CPU process-THP recipe adoption, but GPU R23-58 ends T0/D0 bounded null after 48 launches; controls fired in both directions. | One source champion needs a target/surface recipe map. CPU adoption must not set GPU defaults; GPU non-transfer must not retract CPU evidence. R23-58's coarse simulated power was ~0.97 for a 3× dispersion effect and ~0.69 for 2×; this is not proof of no smaller effect. |
| CPU final characterisation uses instrument `bin-r1`/build 10303, with champion-control state explicitly set; THP fold record identifies source `2516c9807`, not clean `ef81196d5`. | Store actual measurement identity separately from intended delivery. The instrument adds knob-page/dispatch controls and is explicitly NOT TO FOLD. Reports' champion label is not a binary identity witness. |
| Pristine contains neither THP knob; CPU final contrast changes source and adopted recipe. | Preserve `recipe_to_recipe` scope; it is not a source-only or THP-only attribution. The asymmetric champion divergence remains R23-62, not explained away by adoption. |
| Late MEAS-4 correction: t48 was previously measured, with spread placement over all CCDs/NUMA nodes. | “Unused cores” is not unused cache/memory capacity. Encode placement geometry and test partition recipes; do not infer an available contiguous half. R23-64/65 own the post-BIOS revisit. |
| Same-build runtime and dispersion questions needed a separate runner; env, recipe hash and self-draft support were added during the campaign. | Reuse those fixes at verified revisions. Generalize experiment plans/estimands and run a recipe expressiveness matrix, rather than creating another ad hoc runner for each knob. |
| Stored/recomputed floor values differ; n=10 tail floors are unstable; new n≥24/interval/unit rules are ratified. | Version and replay the estimator, retain raw sample membership, check calibration applicability. Never treat an estimator change or different build/window as proof of changed host variance. |
| Partial MTP arm looked ~7% faster because its prompt/token mix was incomplete. | Completion and screening are scientific admission conditions, not UI formatting. An in-flight fast arm cannot enter means, spread, beliefs or scheduling scores. |
| GPU curves differ by model, and v9 has no measured matching DFlash2 production baseline. | Optimize an operating frontier under an explicit objective; distinguish highest measured point from ceiling and capability gain from an unmeasured speed ratio. |

Sources: [final CPU report](../../docs/design/inf70-close-out-20260908/CHAMPION-FINAL.md),
[THP fold record](../../docs/design/inf70-close-out-20260908/FOLD-RECORD-THP.md),
[CPU final progress](../../progress/2026-09/2026-09-08-inf70-audit.md),
[AutoKernel final progress](../../progress/2026-09/2026-09-08-ak-rebuild-20260828.md),
[GPU sweep](../../docs/design/champion-max-performance-20260908.md), and R23-58/61/62/64/65 in
[the rebuild handoff](autokernel-rebuild-program.md). Raw CPU `PREREG-FINAL.md` and GPU
`VERDICT.json` are in research `data/inf70-retest1-2026-09-08/` and
`data/ak-r2358-shim-serving-2026-09-08/`; original evidence commits are recorded in the final progress.

#### B. Recipe identity and expressiveness — one resolution path, no hand transcription

Proposed contracts refine AK-AUTO-04/06/07/10 and existing U3-EXPRESS/U3-SEED/U3-DEFAULTS-b:

```text
resolve_recipe(template, target, surface, operating_point, build, environment_policy)
  -> ResolvedRecipe + CapabilityReport
ResolvedRecipe:
  template_id/version/hash; model and optional drafter identities
  speculation_kind: none | self_draft | external_draft
  resolved argv; measurement-relevant env; explicit_unsets
  declared defaults; requested overrides; dependency/master-off semantics
  controls[]: {set_at: process_launch | runtime_arm, scope_definition, state_witness}
  effective_state_witnesses; normalized_execution_digest
ChampionRecord:
  intended_source; build_manifest
  recipes[(target_id, backend, operating_mode)] -> normalized_execution_digest
EvidenceBinding:
  actual_measured_source/build/object_digests; runtime_state_snapshot
  intended_delivery_id; typed_equivalence_receipts[permitted_uses] | validation_required
```

Resolve/load once per immutable generation and reuse it for launcher, calibration, comparisons, report
and dashboard. Keep template/module-source hashes as provenance, distinct from resolved execution identity.
Normalize launch to process only when each sample is an independent process; preserve the policy's
arm/session/process distinctions with explicit unit definitions and IDs. The comparison unit belongs to
ExperimentPlan, while activation scope belongs to each control—a recipe can contain launch and runtime
controls together. No new LLM call or per-run approval is needed for this resolution.

**Source-confirmed holes to design out, not fixes made by this audit:**

- `Recipe.with_env(KNOB=None)` at `c3e362a1` removes only the declared recipe override, while
  `server_env()` starts from inherited environment. A parent `KNOB=1` can survive an intended unset;
  the declared recipe hash does not expose that difference. Model **unset / set / permitted inherit**
  separately; apply explicit unsets after constructing the inherited environment. Hash/record only the
  allowlisted measurement-relevant resolved environment; never dump credentials into evidence.
  R23-58's THP readback would catch this mismatch, so this finding does **not** invalidate that run;
  generic recipes with no readback do not have that protection.
- The rescued CPU draft declares `CHAMPION_PIN_RESOLVED=False`, but its `preflight()` does not test
  the flag and its digest function checks old champion3 objects. A declarative flag/test of the flag
  is not an enforced refusal. Final-candidate admission must execute the unresolved-pin check; a
  diagnostic `--skip-digests` path must never emit verified final-candidate evidence. The existing draft
  is a starting point, not a proven final-candidate launcher.
- THP `prctl` and model-buffer `madvise` are separate controls. Record master-off dependency and verify
  `THP_enabled` in the launched process; time-dependent AnonHugePages alone is not a general switch
  witness. Diagnostic knob-page defaults differ from champion state: capture each arm's effective state,
  not just the process environment or source defaults.

Expressiveness fixtures should cover existing admitted targets first: CPU/GPU placement, none/self/external
speculation, drafter-specific flags, per-arm and per-launch state, unset/master-off, cache/batch/context
and concurrency. Unsupported combinations return structured capability reasons. Future multi-GPU/RPC,
LoRA and sampler extensions remain scoped capability entries, not a demand to implement every backend
before first use. Existing `c3e362a1` absence semantics map to explicit self-draft in the proposed schema;
do not break existing JSON recipes silently. Recipe validation/plan creation must be useful without compute.

Sources: research `loop/serving.py::{Recipe.with_env,Recipe.server_env,Recipe.recipe_hash}` at the inspected
revisions; [CPU recipe draft](../../docs/design/inf70-close-out-20260908/qwen38_flash_next_recipe.py.draft),
[pin caveat](../../docs/design/inf70-close-out-20260908/README.md), and research `PREREG-FINAL.md`.

#### C. One typed comparison plan and admissible-unit pipeline

Proposed `ExperimentPlan` carries `instrument_class`, `category`, `phase`, `protocol_ref`, `record_class`,
`intended_use`, `comparison_kind`, `estimand`, changed factors,
metric/estimator identities, required unit/control/completeness predicates, pairing/order, fixed-N or
registered sequential stopping rule, power model/margins, calibration reference and permitted conclusions.
`comparison_kind` distinguishes controlled mechanism attribution, assembled candidate comparison and
best-supported-recipe product comparison. `estimand` distinguishes level, dispersion and separately
registered objectives; a variance effect cannot be inferred from a mean test or vice versa.

Use reusable deterministic templates, populated from the resolved recipe and existing policy, then
freeze/hash once before execution. One shared validator feeds comparison, journal publication, planner,
dashboard and Vidya projection; it validates existing warrants and delegates grading to `ClaimTuple.grade()`.
It is not another grading ladder or critic review. Missing formal serving-protocol registration
(RATIFY-MEAS-2) stays visible: exploration/evidence collection can proceed within authority, but a template
cannot invent an approved protocol ID or auto-ratify a gating claim. Apply-time human boundaries stay intact.

```text
native samples -> complete independent unit -> predefined screen disposition
  -> immutable admissible-unit view -> exact estimator + registered stopping rule
  -> typed conclusion + claim eligibility -> journal / planner / dashboard / belief projection
```

Completeness includes expected prompt IDs/counts, workload/token-mix identity, terminal marker and required
witnesses. Preserve `flagged_but_retained(reason)` separately from CLEAN and rejected, following the declared
policy. All consumers use the **same unit set**; a dropped arm cannot reappear in floor estimation or CI.
Repeated prompts inside one process do not multiply independent launch N. Control assertions must witness
the execution path in both directions—not merely a profiler's task-plan counter that execution ignores
(SYNC-18's exact failure). Zero/insufficient observations return invalid rather than an empty PASS.

Typed results keep `inconclusive`, `direction_only`, `estimated_effect`, `bounded_null` and `regression`
distinct. A purported null missing its power record or fired-knob control is `untested` under
BOUNDED-NULL-1; retain the raw measurements and missing-warrant reason. This is different from a valid
measured contrast whose documented power/resolution is inadequate: that is `inconclusive`, with its
effect/uncertainty preserved. Do not encode the
CPU six-pair direction-only THP keep as a validated +5.23% magnitude, or the joint FIX-1+FIX-3 regression
as two separately significant component effects. Save the original registered action separately from
today's claim eligibility; policy upgrades do not silently rewrite historical decisions.

Sources: [FIX1 result](../../docs/design/inf70-close-out-20260908/FIX1-RESULT.md),
[final-arm completeness](../../docs/design/inf70-close-out-20260908/CHAMPION-FINAL.md),
[ratified rules](../../MEASUREMENT.md), and final CPU progress §§6/10.

#### D. Calibration, precision economics and host changes

A proposed `CalibrationReceipt` contains exact model/build/resolved recipe, metric and estimator version,
quantile/normalization convention, independent-unit definition and IDs, raw sample digest, n, interval,
window/host/neighbor envelope, sampler version and protocol. Deserialize → replay → compare **once per
immutable calibration, estimator and applicable policy identity**, then cache validation for routine
arms; invalidate the cache when those dependencies change. No raw-sample replay per arm.
The 4.581/4.494 and 6.657/6.596 discrepancies are **unreconciled estimator/provenance observations**, not
permission to choose a convenient value or assume rounding. A changed estimator creates a new identity.

Maintain reference precision and observed per-treatment precision separately. The CPU shim's paired test
and later six-launch characterisation support examining precision as a resource-saving lever, not a
universal fixed noise multiplier. Estimates from a few launches remain uncertain. Forecast cost under the
current recipe with that uncertainty; a cheap low-power “null” is not cheaper useful science. Select the
cheapest instrument that exercises the mechanism **and** matches intended use; MTP's better precision in
one CPU block does not license applying its floor to plain decode or another target.

For BIOS/reboot, retain pre/post absolute serving rates when metric/workload semantics match; classify
the difference as unattributed if several conditions changed. Do not hide improved capability behind an
era label or attribute it solely to a kernel. Re-resolve topology/host settings and recalibrate gating
floors because dispersion may change. No assumption that C8's prepared BIOS proposal equals the operator's
actual changes. R23-61a's pre/post choice and gated R23-64/65 remain the existing route, not duplicate tasks.

#### E. Selection, transfer memory and honest dashboard objectives

Seed the mechanism/transfer fixture with CPU-THP adopted / GPU-THP bounded non-transfer. Store source and
target scopes, actual mechanism controls, bounds, effect statistic, dependencies and registered disposition.
Unknown transfer permits scoped exploration; negative evidence suppresses **the same tested claim** until
relevant dependencies or the effect-size question change. It must neither retire all small possible
effects nor propagate CPU defaults to GPU. Cheap bounded disproof is useful progress, not a failed campaign.

For each target, retain the tested concurrency/placement frontier, objective and SLO, not only one scalar
best. `single_user`, `aggregate_capacity` and a selected responsiveness/throughput operating point are
different objectives. Choose under an explicit workload/resource envelope and policy; missing SLO does
not authorize inventing one. Publish sweep bounds and operator stop reason. The dense np=8 result is the
highest tested point with diminishing returns, **not a measured turnover/global ceiling**; the MoE np=16
endpoint likewise leaves its ceiling unknown. Small-n spread is descriptive, not a certified floor.

For kernel attribution hold a compatible recipe fixed. For product improvement compare each build at its
own best **supported** recipe under the same workload/objective/resources, with the changed factors visible.
Production lacking the experimental drafter is `unsupported_capability`, not a zero denominator;
`baseline_not_measured` emits no ratio. A candidate model outside production still gets a baseline in a
compatible experimental build. Cross-model architecture comparisons are not kernel gains. Preserve the
historical aggregate metric's exact definition; migrating to common-window throughput needs a new metric
identity and calibration, not a relabeled card.

#### F. Lifecycle coverage, durable closure and cross-campaign reuse

One campaign sampler should cover allocation/setup/eviction/load/placement/warmup, **between-arm gaps**,
request phases and teardown, with timestamp coverage attached to each unit. Otherwise foreign work can
change cache/placement before timed sampling begins. Recovery/re-admission uses the existing declared
quiescence/reset conditions; this notebook invents no magic cooldown duration. Retain ownership and
samples rather than guessing a culprit: the API stop was subsequently observed as a non-event in the
sampled CPU window, superseding the earlier suspected attribution, not proving global noninterference.

Reuse SC75's prospective CPU arm wiring. Its pre-September-7 erroneous sibling-isolation labels must not
be upgraded into clean measurements; keep historical records discoverable but emit no eligible measurement
claims from that known-bad set under the existing adapter policy. A corrected sampler version invalidates
dependent **warrant**, not the fact that a run occurred. New GPU residency capture R23-60 is already landed;
reuse its raw readbacks and inspect the loaded revision rather than restating it as missing.

Before releasing a campaign, derive a retention manifest from all evidence/candidate/recipe references,
including non-branch refs and absolute RUNPATH dependencies. Verify the backup actually covers the named
ref/object/artifact closure, not merely that a bundle command succeeded. Commit compact receipts/checksums
and explicit large-artifact provenance; never silently promote a hedge copy into the evidence record.
Drafts remain drafts, no-fold refs remain exclusions, and a closed researcher does not transfer ownership
of unadopted tasks. This is automated bookkeeping and validation, not an additional sign-off ceremony.

#### G. Acceptance fixtures and integration into the existing plan

| Fixture | Required behavior | Existing design/task mapping |
|---|---|---|
| Parent env sets treatment, control requests unset | Resolved control really unsets; digest distinguishes relevant state; THP readback still catches mismatch | AK-AUTO-04/07; U3-EXPRESS |
| Unresolved champion pin with old digests matching | Actual admission refuses; diagnostic bypass cannot claim final validation | AK-AUTO-01/04/10; PROD-1 context only |
| Instrument build in champion-control state | Preserve measured identity; no automatic clean-candidate timing/correctness inheritance | AK-AUTO-10; G2-CONC requirement |
| CPU adoption plus GPU bounded null | Two recipe entries; independent dispositions and power bounds; no cross-surface default leak | AK-AUTO-08/10; U3-DEFAULTS-b |
| Partial fast arm / dropped arm / zero evidence | Exclude consistently until complete/valid; never a gain or vacuous PASS | AK-AUTO-02/06 |
| Direction-only / component non-claim / dispersion-only effect | Claim serializer and all projections preserve conclusion strength | AK-AUTO-06/08 |
| Floor wrong unit, missing interval, n<24, or replay mismatch | Refuse new gate use with exact reason; queue scoped recalibration; keep historical record | AK-AUTO-06; R23-55/61/65 |
| Hypothesis control only changes profiler counters | No executed-path warrant; record untested and diagnose before spending measurement budget | AK-AUTO-07; SYNC-18 fixture |
| Production cannot load candidate recipe | Capability status, no invented speed ratio; optional own-best supported baseline | AK-AUTO-04/10; PROD-BASE-1 |
| BIOS change / superseded sampler | Absolute rate remains visible; attribution and calibration/coexistence eligibility updated separately | AK-AUTO-03/08; R23-64/65 |
| Operator stops sweep at highest measured point | Record endpoint/stop reason; do not claim saturation or resume without authority | AK-AUTO-11 |
| Scratch cleanup or session retirement | Referenced evidence/refs/build dependencies survive; unresolved ownership remains explicit | AK-AUTO-02/11 |

**No duplicate execution queue:** these are refinements to §8.13's proposals and PLAN-DOC-2, not newly
authorized implementation tasks. Declined to create separate dispatch rows because this session's scope
is iterative design and existing U3/R23/SC75 rows already route applicable work. Before implementation,
re-resolve their actual state and ownership. OP-41 stays operator-owned and sequenced last as recorded.

**Audit cautions retained rather than copied into formulas:** some summaries call the final +5.958% bench
versus −2.18% serving contrast an “11-point” gap (arithmetic is 8.138 points, and cross-class subtraction is
not a performance claim); the listed sd values 2.793/0.501 do not themselves imply a 13× ratio; and one GPU
discussion compares unlike concurrency points as though they establish better per-user responsiveness.
Do not import those shorthands as evidence or thresholds. The ratified rules remain unchanged; this audit
does not edit protected policy or re-verdict historical experiments. Exact estimators and original
receipts, not persuasive prose, must drive future automated decisions.

<a id="implementation-contract-review-20260908"></a>

### 8.17 Fresh review — deterministic implementation boundaries

**Basis:** three independent read-only reviews of root `452bee84`, followed by reconciliation against
the ratified protocols, R23-54 and research `loop/accumulate.py` at `6ab403ed`. These are design refinements,
not implementation, new measurements, retroactive verdicts or adoption of unowned tasks. A–B identify
existing authority; the concrete interfaces/algorithms below are proposed ways to enforce it cheaply.

#### A. Phase-specific admission and evidence-use authority

The earlier blanket contamination/refusal wording conflicted with **ratified P-AK-SEARCH-1-A2**.
Ordinary foreign builds, agents, filesystem activity and host load are recorded noise for AutoKernel
search, not reasons to wait/refuse/abort or request quiet. This applies to search, not merely its cheapest
screen. The sole environmental-interference blocker is witnessed competing model inference overlapping
the held claim. Correctness, identity, power/frequency envelope and claim-witness gates remain mandatory.
The planner may reduce overlap among its **own** queued jobs under authorized resource policy, but cannot
turn that scheduling choice into a foreign-load veto, a signal to foreign processes, or a quiet-host demand.

| Phase / authority | Execution and reuse | Permitted consequence |
|---|---|---|
| A2 discovery, category CANDIDATE | Exactly three anchor invocations create an immutable baseline bank; exactly three candidate-only invocations per screen, zero new anchors while the full common frame matches. No strict T1 floor prerequisite. | Advisory nomination only; no banking, champion entry, readiness or headline claim. |
| Original P-AK confirmation, narrowed by its amendments | Fully paired, randomized, calibrated selection/confirmation; frozen ordering/stopping/control requirements. Never pool discovery samples into confirmation. | Strict evidence can satisfy the protocol's experimental banking/composition prerequisites; remains a search record, not a release claim. |
| Serving observation or owning release protocol | Execute the identified instrument and registered recipe; apply that protocol's validity/isolation requirements, not a search default. Missing RATIFY-MEAS-2 is observation-only where applicable. | Only the actual registered authority can supply a production gate/headline. A serving-class label alone grants nothing. |

Bank identity includes the full runtime/environment frame, not just a build hash. A2 runtime screens
require exactly one unequal runtime field and identical sealed executable/DSOs; no build/worktree.
Source-changing screens retain identical runtime semantics. No-op or multi-factor screens are invalid;
broader recipe combinations/product comparisons need their appropriate plan, not a fabricated A2 attestation.
Ordinary noise may widen **uncertainty** or reduce nomination priority, never the acceptance threshold.
Complete identity-matching phases survive restart and changes in ordinary load. Identity drift closes a
baseline bank; no relabeling it to the new frame. No retrospective application to pre-ratification records.

Proposed shared interface, evaluated from templates and cached receipts rather than actor paperwork:

```text
eligibility(record, intended_use, policy_snapshot)
  -> permitted | refused(reason, missing_dependencies)
inputs: record_class = discovery_screen | strict_search | observation | registered_claim
        category = OPTIMUM | BASELINE | CANDIDATE
        phase, protocol_ref/status, instrument_class, actual scope/identities, warrant refs
uses: explore | nominate | rank | bank | certify_transfer | certify_overlap | validate | headline
```

This is a **use/applicability check**, not a second grading ladder: `ClaimTuple.grade()` remains the
existing warrant grader. Persist the original authority/disposition; derive present use eligibility
without rewriting history. BASELINE diagnostics cannot veto or justify production promotion; required
rows concern the production-optimal serving recipe and its candidate counterpart. A3 permits same-epoch
search ranking, but cross-epoch search retrieval exposes attempted mechanisms/conclusions with staleness,
not comparable magnitudes. The separately authorized absolute pre/post-BIOS serving observations in
§8.16D do not repeal that search restriction.

Sources: [Annex K A2/A3](../../measurement/protocols/kernel-research.md),
[category and instrument rules](../../MEASUREMENT.md), and R23-54 in the
[rebuild handoff](autokernel-rebuild-program.md). These restrictions already exist; no policy amendment here.

#### B. Calibration applicability and measured-to-delivery identity

Separate **exact provenance** (`CalibrationReceipt` in §8.16D) from **applicability to a comparison**:

```text
calibration_applicability(receipt, complete_ExperimentPlan, registered_rule_version)
  -> applicable | recalibration_required(reason) | policy_undefined(reason)
```

The rule considers both actual arm identities, declared changed factor(s), resolved recipes, estimator,
experimental unit, planned count/stopping scheme, metric and host/coexistence envelope. It specifies
which intended source/build differences can share calibration and which runtime/placement/instrument
changes require a new one. Exact build provenance does not mean every source patch automatically needs
a wholly new floor; conversely, matching a model name or n does not establish applicability. A runtime
intervention affecting variance needs the registered treatment-aware comparison/calibration method;
do not transplant a control-only noise estimate or assume equal arm variances.

Resolve the gate's scalar floor and its use from the **existing registered estimator/policy**, retain
the calibration interval alongside it, and apply any registered precision requirement. Do not silently
substitute an interval endpoint, increase a multiplier, or reinterpret a percentile. If that mapping or
allowed transfer is undefined, mark only the dependent gate `policy_undefined`/`recalibration_required`;
discovery continues under A2. A new gate floor still needs n≥24 at the declared unit and an interval.
Cache applicability by receipt + complete plan dependencies + rule version; a cheap key check suffices
before each admitted stage. Neither every-arm raw replay nor an actor-selected calibration is required.

Equivalence receipts have explicit assertion/use types: output correctness, local-work/path equivalence,
or timing under a named workload/envelope. Correctness equivalence cannot certify timing. No receipt
overrides an exact-candidate requirement: **G2-CONC uses the promotion candidate binary**. A measured
instrument in champion-control state remains evidence about that instrument, not clean-delivery timing.
Historical measurements stay discoverable even when current validation requires a different build.

#### C. One accumulated candidate, one validation transaction, one frozen production reference

Proposed durable pointers—not separate per-surface champions:

```text
production_ref       # frozen kernel set and ratified serving recipe identities; never mutated by loop
integration_tip      # one assembled source/build/recipe-map manifest; experimental keeps may accumulate
validated_candidate  # one immutable manifest + complete required validation batch; may lag integration
ValidationBatch:
  id; candidate_manifest; comparator_manifest; required_row_set_version
  exact per-row target/recipe/instrument/protocol/objective identities
  required LOO treatments; receipts; outstanding debt; terminal disposition
```

Freeze a due batch at a specific integration manifest; newer keeps do not retarget its running arms.
Reserve budget to finish it, so perpetual integration cannot postpone validation forever. A passing
batch advances `validated_candidate` once through a journaled compare-and-swap on its expected predecessor;
it never claims a newer integration tip is validated. Per-row recipe hashes may differ across targets,
but all rows must belong to the **same manifest and required-set version**. CPU pass/GPU missing leaves
the batch pending; a newer recipe cannot inherit old rows. Missing capabilities/resources have explicit
row status, not zero denominators, fictitious pass values, or a veto from an unrelated optional model.

**Proposed replacement for §3.0/U2:** `cor` denotes this validated candidate, not the most recently passing
surface. Any-surface pass fills a row; it no longer advances shared `cor`. After a full batch advances,
mark all outstanding tip-versus-old-cor summaries stale and remeasure under each applicable harness
before quoting against the new baseline. Never rescale old percentages or copy a gain across surfaces.
Production promotion remains a separate runbook/operator action requiring its owning gates. Until this
design is adopted, preserve current behavior and annotate its limitations rather than silently migrating it.

Integration must survive source and recipe changes in **different repositories**: under the integration
lock verify parent, persist intent, create retained immutable source/recipe refs, then journal one
content-addressed manifest and atomically publish its pointer. Git commits across repositories are not
one atomic transaction. Recovery reconciles intent/trailers/refs; orphan refs remain retained until
resolved, and no half-published manifest becomes a champion. Workers never advance these pointers.

Each keep records source/build/runtime delta, parent manifest, affected scopes and dependencies. LOO
constructs a derived candidate with that treatment absent, not a blind commit revert on the live tip.
Runtime-only ablations reuse the same binary with a distinct recipe. Dependent source changes or two
keeps overwriting the same knob require an identifiable registered treatment; if impossible, record
`nonidentifiable`/`unsupported`/`build_failed`, not a neutral measurement or a satisfied required gate.
Evaluate required applicable production surfaces; preserve dormant-quant findings as scoped history.
Neutral/inconclusive LOO is not automatic deletion authority. Removing a keep creates another candidate
manifest requiring its own applicable validation; nothing rebases or rewrites frozen production.

Preserve R23-54's **four keeps OR gain trigger**, durable count and reset on every completed gate run,
including inconclusive outcomes. Refusal before a gate starts is not a completed run. Proposed unified
cadence counts each integrated keep once, not once per affected surface, and schedules a frozen validation
batch; retain per-surface receipts. Maintain separate `validation_debt` until required rows pass: resetting
the cadence counter cannot erase unresolved rows or falsely validate. Calibration absence exposes debt
and schedules its authorized prerequisite instead of spinning. The additional 24-hour trigger is still
proposed; it creates a due reservation, not permission to violate grants, policies or serving budgets.

#### D. Enrollment, accounting and bounded coverage without scheduler ceremony

```text
enroll(request_id, seed_spec) -> immutable TargetRevision + enrolled_event
  status: baseline_pending | ready | artifact_missing | unsupported_capability
Proposal:
  versioned_claim_key; target_revision; immutable parent/control/intervention identities
  mechanism/estimand/effect-bound question; route; required witnesses
  estimated stage resource vector/deadline; evidence snapshot + dependency generations
```

Keep the launch snapshot; later seeds append target revisions rather than mutate it. Resolve registered
references and pin the intended compatible baseline at enrollment (or the first capability-resolving
transition before execution), using actual model/build/recipe identities. Retries cannot silently follow
a moved reference. An artifact appearing later creates an explicit resolution event. Deduplicate aliases
by full workload signature, retain the union of production obligations/candidate roles, and grant no new
boost for a duplicate. Missing/unsupported targets report a precise prerequisite while other work proceeds;
this is not a decision to dismiss that model or permission to download/convert it outside v1 scope.

Proposed deterministic scheduler, implemented within one admission owner:

1. Charge each stage the time integral of its **held claims**: physical-region fraction, GPU-device
   seconds and any separately limiting memory reservation. A quarter claimed for four executing cores
   costs the quarter; GPU stages also pay their CPU claims. Include setup/load/warmup/build/teardown,
   invalid attempts and held idle time. Record estimated versus actual service; attribute shared builds
   once by a recorded apportionment rule, not once per beneficiary or to nobody.
2. At a coverage-round boundary freeze the continuously eligible production-frontier set and `K`/`D`.
   Give each member one bounded stage opportunity; arrivals/seeds cannot reset the round. Count **every**
   admitted expensive stage, including prerequisites/calibration/validation/reject audits/maintenance,
   exactly once against either its frontier's coverage slot or the `K` noncoverage slots. No uncounted
   priority queue may bypass this bound. With `N` members and maximum stage-plus-teardown `D`,
   conservative serial completion is bounded by `(N + K) * D`, plus explicitly recorded authority/resource
   outages and any already-running bounded stage. This bounds **service opportunities**, not valid results
   under unbounded noise/failures. Oversized jobs need a declared larger bound or scientific-safe chunking;
   never interrupt arbitrary samples to make a scheduling theorem look true. Reserve at least one
   noncoverage seed opportunity per round when an eligible seed and budget exist (`K>=1` then); otherwise
   “at most K” would allow zero forever. Use oldest eligible FIFO seed, skipping temporarily ineligible
   entries without resetting their history/budget. Dry-run refuses conflicting reserved-slot totals;
   new eligibility joins the next round rather than silently changing the current bound.
3. In noncoverage slots use weighted deficit over actual charged resource service. A normalized dominant
   share supplies a scalar ordering while the vector remains visible; grant changes start an accounting
   epoch without forgiving prior service. Normal weight 1; seed weight 2 ends after three valid comparisons
   **or its finite attempt/charged-time cap**, whichever first. One boosted seed/backend, FIFO; campaign
   budget bounds seed admission. Invalid-only seeds cannot monopolize a boost or block later seeds forever.
4. Adapt weights in the proposed 1–3 range at batch boundaries using same-epoch target-confirmation and
   informative bounded negatives/precision results per charged cost, plus uncertainty. No screen-only gain
   jackpot or cross-epoch numerical search ranking. Keep coefficients/reward normalization versioned and
   provisional; weights never override coverage, budget or evidence eligibility.
5. Reserve calibration, target-scale reject audits and due validation explicitly. Full-region reservations
   stop new incompatible backfill early enough to finish current bounded work; certified backfill cannot
   extend the reservation. Record budget exhaustion, infeasible stage demands and external outages
   separately. Resume existing rounds/debts after recovery instead of awarding a fresh startup boost.

Finite manifest defaults for stage limits, `K`, seed caps and reserve shares must be selected before
eventual deployment; dry-run reports the resulting bound/cost. This is configuration, not a new review
for each experiment. The coverage test uses fake time/claims; real service can promise no hard wall-time
bound while its external authority is unavailable. Initial admission stays serialized under §3.4;
certified overlap is an eventual policy revision within OP-41's sequence, not a per-profile operator task.

#### E. Transfer, coexistence and retrieval contracts

The versioned claim key covers target scope, intervention/control, mechanism, estimand, effect-size
question and dependency identities. A planner annotation is a hypothesis, never a path witness. Transfer
edges are **directed and nontransitive**, separately typed `correctness`, `local_work`, `serving_effect`:
A→B and B→C do not establish A→C, nor does CPU→GPU follow from a shared mechanism name. A bounded null
suppresses only its tested effect-size question under matching dependencies; changing a bound defines
a new question, not positive evidence or automatic renewed priority.

Routes declare preserved dimensions, required executed-path witnesses, covered targets and disposition
authority: `exploration_only` or `may_screen_out(scope, effect_bound)`. Matching a mechanism class alone
does not certify rejection transfer. Audit a configured fraction of rejects via a stable hash of claim
key + route revision, stratified by mechanism/allocation; record selection probability and charge a
separate bounded target-confirmation budget. Restart keeps the same sample. A successful target-scale
audit of a rejected candidate revokes the route's negative-screen authority in the affected scope, not
its true local result or unrelated correctness evidence. Audit-budget exhaustion stays visible.

Coexistence receipts bind measured workload, **complete neighbor multiset or certified pressure envelope**,
physical claims, all lifecycle phases, dependencies, registered equivalence margins, estimands and
uncertainty. No significant difference is not equivalence. A+B and A+C do not certify A+B+C; B tolerating
A does not certify A tolerating B. Certify each victim direction, including setup and burst exposure;
average pressure alone cannot cover untested bursts. Missing evidence/margins leaves owned incompatible
admission serialized, subject to A's explicit search/foreign-noise distinction. A serving-throughput
allowance is never a research equivalence receipt.

```text
retrieve(scope, claim_key, intended_use, limit=40)
  -> ranked_findings[<=limit] + mandatory_applicable_conflict/retraction_status
     dependency_generations + snapshot_frontier + complete_for_intended_use
admit_cached(proposal, local_generations) -> eligible | stale(affected_dependencies)
```

Indexed conflict/retraction checks occur **before top-k truncation**; a relevant refutation cannot hide
in position 41. Preserve raw grade separately from applicability. Maintain a reverse dependency index
and local invalidation generations; compare cached generations immediately before expensive admission.
A local retraction/recipe/topology change takes effect even while asynchronous Vidya projection lags.
Malformed invalidation events are quarantined with affected eligibility marked incomplete, not silently
clean. If dependencies cannot be identified, withhold certificate-dependent uses at the uncertain
frontier; fresh exploration remains available. Unrelated changes preserve cache reuse. No corpus scan,
network request, raw-calibration replay or LLM classification is added to the per-arm fast path.

#### F. Supervisor fencing, controls, grant expiry and scientific restart

One campaign-scoped exclusive supervisor/writer lock plus a monotonic **supervisor incarnation** fences
workers and command application. Use the host's service-manager restart facility with bounded backoff
and an explicit failed state; tmux or a monitoring agent is not the recovery mechanism. Separate process
incarnation from immutable campaign/config generation: an unchanged restart preserves campaign evidence.
Relevant topology/recipe/policy changes resolve a new generation and scoped invalidation before admission,
not a silent snapshot mutation or automatic research relaunch beyond the operator's authority.

Persist `launch_intent` with allocation/worker generation and a preassigned owned process-container ID
**before spawn**. On crash, reconcile that container and PID-start identities before replacement. This
closes the spawn-before-PID-receipt gap; recovery cannot assume absence because its JSON lacks a PID.
Workers return results tagged with campaign/config generation, supervisor incarnation and worker/allocation
identity, never write journal/pointers directly. Reject stale responses;
retain their raw artifacts as history. Another supervisor cannot steal a live lock or act on an old grant.

Commands contain campaign/generation, request ID, payload digest and expected control revision. Persist
acceptance before acknowledgment and linearize it with admissions. Duplicate ID/payload returns prior
result; same ID/different payload refuses; stale expected revision returns current state. CLI and browser
use the same contract. Show **accepted** separately from **completed**, with reason/deadline.

| Command | Admission boundary | Completion |
|---|---|---|
| pause | Close new expensive-stage admission. Already admitted bounded stage may finish within its grant/deadline; its queued successor needs fresh admission. | Quiescent, compute released, supervisor/control live; desired pause survives restart. |
| drain | Close admissions, finish only permitted bounded active stage or invalidate/tear it down at its declared boundary. | Owned workers/descendants gone, final state durable, claims released; no implicit restart. |
| resume | Reconcile retained work, config dependencies, control revision and authority; fresh admission only after checks. | Running or explicit waiting/prerequisite state; cannot erase a later accepted drain. |

An interrupted independent unit is invalid. Reuse completed units only if the frozen plan explicitly
permits continuation with unchanged identities, unit membership, ordering and stopping rules; otherwise
new comparison execution ID, old observations retained. Drain midway through a pair cannot create an
unpaired winner or an outcome-dependent extension. Reuse sealed completed phases per A2 instead of
restarting the entire campaign. Record reused-phase IDs in the new execution's lineage.

Each allocation receipt binds grant identity/deadline and ownership generation. Admission must fit the
bounded stage **plus teardown** within the remaining authorization or the provider's existing explicit
drain allowance; admission one second before expiry is not enough. A renewal watchdog blocks successors
on renewal failure; an already authorized stage may finish within its current deadline/drain allowance.
Distinguish failed future renewal from current revocation, and start bounded owned teardown in time to
meet the applicable provider deadline. Verify the affected allocation's owned descendants exited before
releasing its claims or admitting replacements. Uncertain ownership stops affected replacement, not a broad name-pattern
kill. The provider remains grant authority; this proposed consumer contract does not implement OP-41 early.

#### G. Coherent dashboard snapshots and lifecycle-aware health

Publish one versioned snapshot from the journal projection: campaign/config generation, supervisor
incarnation, journal cursor, projection sequence, generated time, producer/loaded schema/build identity,
desired/observed state, applied command revision and worker stage/deadline. Assign a durable monotonic
`stream_epoch` at producer incarnation/config-generation changes, plus a sequence increasing within that
epoch; compare `(stream_epoch, sequence)` within a campaign, never order content hashes lexically. Worker
telemetry carries its worker/allocation incarnation so delayed old telemetry cannot enter a new snapshot.
Health-only refreshes advance sequence without pretending the scientific journal advanced. Consumers
reject older stream keys; after an epoch change request a full snapshot, not a partial old/new merge.
Capture journal cursor, command revision and derived state atomically from one projection revision;
attach heartbeat/resource observations with their own sample timestamps and matching worker incarnation.
A stale cached page may display history but cannot acknowledge commands or claim live progress.

Separate supervisor heartbeat, worker stage/activity and last scientific result clocks. Paused/drained
campaigns intentionally have no active worker; that is not failed-worker health. A retained service keeps
its own heartbeat while its campaign is terminal; if the service exits, the terminal record is historical,
not live. Stop/join the **worker's** status publisher before terminal publication so it cannot resurrect
`running`. An actor/evidence outage degrades the dependent capability, not transport. Use existing `/health`
versus `/api/health` semantics and freshness envelopes; do not invent a second hub health definition.
Commands go directly to the authenticated producer gateway; hub pages remain non-proxy projections.

#### H. Code seams, versioning and acceptance fixtures

Keep changes in the existing ownership boundaries. The names below describe proposed seams, not installed
APIs; no monolithic second controller, second WAL, new evidence grader or new grant authority is intended.

| Existing home | Proposed extension / test seam |
|---|---|
| Research `autokernel/journal.py::Journal` | Typed phase/control/integration/validation events, replay and schema migration; crash/torn-tail fixtures. |
| Research `loop/run.py` and `loop/pipeline.py::SerializedTail` | Extract small campaign-service/admission interfaces around current engine; fake actors/workers/clock/claim provider. Preserve serial tail until immutable parent checks exist. |
| Research `loop/accumulate.py` | Immutable candidate manifests, validation batches/debt and cadence; CAS/restart/LOO fixtures. |
| Research `loop/serving.py`, `loop/bench.py`, `loop/residency.py` | Shared resolved recipe and ExperimentPlan/use validator, applicable calibration, unit view and lifecycle witnesses; no duplicated estimator per consumer. |
| Existing orchestrator claim/contention providers | Eventual operator-owned grant/region/coexistence contract; research supplies an adapter, not a competing policy daemon. |
| Root Vidya adapters and existing retrieval/projection | Prospective source registration at implementation, existing grader, scoped use/transfer and invalidation index; reuse SC75. |
| Research status/control producer; root dashboard hub | Producer-side command/snapshot schema and gateway; hub rendering/registry/freshness/health probes. |

Version event and manifest schemas; defaults for absent provenance are `unknown`, never clean/validated.
Keep legacy records readable as history; unsupported schema versions cannot grant evidence eligibility.
Migration writes a replayable versioned snapshot without rewriting the original journal. Rollback must
refuse unsupported newer state rather than fall back to `cor=anchor`; preserve the last compatible
read-only view and require a compatible engine for further admissions. New fields need adapter fixtures
and producer/consumer compatibility tests, not silent deserialization defaults that change authority.

| Deterministic fixture | Required result |
|---|---|
| Ordinary foreign build during A2; overlapping foreign model inference | First remains recorded noise; second follows witnessed checkpoint/resource rule; no foreign signalling. |
| A2 nominee/serving-class search record presented for banking/headline | Intended-use refusal; strict confirmation and owning release authority remain separate. |
| Wrong calibration unit/estimator, runtime variance intervention, output-equivalent delivery build | No incompatible floor or timing inheritance; exact-candidate gate stays exact. |
| Fourth keep, restart at count 3, inconclusive completed gate | Cadence fires/persists/resets as ruled; unresolved validation debt remains. |
| CPU row passes, GPU missing; recipe changes; crash during cross-repo integration | Accumulation preserved; no partial validation or half-published manifest. |
| Dependent source keeps, overwritten runtime knob, unsupported ablation | Identifiable LOO or explicit missing gate; failed revert never counts as measured neutral. |
| Duplicate seeds, moving refs, invalid-only seed, larger region than affinity, GPU host CPU | Stable enrollment/baseline; finite boost; exact charged claims and persisted coverage round. |
| Full-host validation waits while short jobs arrive; grant outage | Reservation prevents backfill starvation; opportunity bound excludes explicitly recorded outage only. |
| A→B/B→C, correctness-only transfer, rejected small-scale scale-sensitive idea | No transitive/timing inference; reproducible reject audit and scoped authority revocation. |
| Pairwise-safe but triple-contended work; asymmetric/bursty overlap | No composed or symmetric certificate; lifecycle/neighbor envelope enforced. |
| Refutation ranks 41st; retraction after proposal; malformed invalidation; projection outage | Mandatory status survives top-k; cheap local fence invalidates dependent use; fresh exploration survives. |
| Crash after spawn before PID receipt; two simultaneous supervisors | Reconcile preassigned owned container; one writer, no duplicate worker/claim use. |
| Duplicate/stale pause-resume-drain commands; restart mid-pair; grant expiry | Ordered durable controls, no successor leak, exact unit membership, teardown before release. |
| Delayed old snapshot after resume; hub restart while paused | No false running/command completion; intentional worker absence not producer failure. |

Run these with fixtures/fake time before any hardware spend; later real lifecycle/contention and unattended
acceptance remain §8.14, after their existing authorization gates. Integrate under AK-AUTO-02/04/06–11;
no new dispatch rows. The remaining numerical/objective choices in §8.15 are still iterative design,
but these failure modes now have explicit data, transition and test contracts. **Friction budget remains
zero additional routine operator decisions or critic calls for established runtime sweeps.**
