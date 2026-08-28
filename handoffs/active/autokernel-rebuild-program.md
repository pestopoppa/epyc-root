# AutoKernel — teardown and rebuild program

**Owner:** operator-directed audit + rebuild session, 2026-08-28.
**Code lanes:** `lane/ak-rebuild-20260828` (epyc-root, this file) and a matching lane in
**epyc-inference-research** for the loop itself.
**Owning index row:** **INF-66** in [`inference-research-index.md`](inference-research-index.md).
**Riders on:** [`autokernel-restart-and-strip.md`](autokernel-restart-and-strip.md) (INF-64),
[`autokernel-research-loop.md`](autokernel-research-loop.md) (INF-06),
[`autokernel-champion-aggregate.md`](autokernel-champion-aggregate.md) (INF-65).
This page does not re-open their backlogs.

**Trigger.** Operator audit, 2026-08-28: *"we have been working on autokernel for close to a month
with virtually no progress… told by agents that things are working and/or built only to later
discover they're either NOT built or constructed in vacuous and useless ways."* Five parallel
read-only audits were run over `scripts/kernel_rnd/autokernel/`, all 62 deployments under
`/mnt/raid0/llm/autokernel/`, and the epyc-root coupling surface. Every headline figure below was
re-verified independently against source or on-disk runtime state; `README.md` (167 KB),
`FOOTPRINT.md` (44 KB) and `program.md` were treated as unreliable and are — `FOOTPRINT.md`
documents 29 dead modules in detail while omitting **14 of the 17 that actually execute**, which is
why every prior reachability audit was wrong.

**Plan of record:** the approved plan for this program. Published reference artifact:
`https://claude.ai/code/artifact/aef00ecd-5198-4d60-b191-230898849fcb`.

---

## CURRENT STATE — read this first on pickup

- **P0 DONE** (root `7f86e383`) · **P1 DONE** · **P2 DONE** incl. the measured A/A floor ·
  **P3 DONE except two items deliberately unshipped** (anchor build cache, ccache — see P3) ·
  **P4.1 DONE** (the loop-design doc) · **P7 DONE** (research `10f0214e`).
- **P4 loop package BUILT** (research `6408f685`): 8 files, **828 LOC** against a 3,000 budget
  and against the 153,865 it replaces. Control flow is pure — every side effect injected — so
  17 tests run in 0.05s with no GPU, no API key and no ROCm. **Its exit criterion is NOT met:**
  ten consecutive real iterations need the external codex planner and hours of GPU.
- **Next action:** run the new loop end to end (P4 exit). Until it passes, **P5 must not start** —
  the strip is gated on the replacement being proven, and that gate is the point.
- **Measured A/A noise floor (2026-08-28, n=20 alternating pairs, residency proven 80/80).**
  Recomputed exhaustively — p95 |median effect| over EVERY C(20,k) subset, so it re-derives
  exactly (`bench.MEASURED_FLOOR_PCT`, research):

  | pairs | prefill | decode |
  |---|---|---|
  | 1 | 2.175% | 3.452% |
  | 5 | **0.479%** | **1.502%** |
  | 9 | 0.168% | 1.175% |

  **4 of 20 pure-noise decode pairs exceed the superseded loop's 3% bar.** An earlier
  hand-written table quoting 0.753% / 1.848% at k=5 reproduces by no method from the raw pairs
  and is superseded. The loop **enforces** 0.973% / 1.544% — above the measured rows on purpose,
  since 20 pairs is a thin sample of a heavy tail. `--arm-pairs` must be ≥5.
  Artifact: `artifacts/autokernel-aa-noise-floor/` (research).

### Runs 5–9, and the four harness defects they exposed (2026-08-28 evening)

Nine real iterations produced **zero measurements**, and every cause was in the harness rather
than the actors. Recorded because each one looked like planner quality and was not:

1. **The placeholder guard rejected real answers** (research `bb468613`). `_PLACEHOLDER` listed
   a bare `"<"`, so any falsifier stating `delta < 0.97%` or naming `mul_mat_vec_q<Q4_K>` read
   as our own prompt echoed back. Three consecutive correct hypotheses retired — a guard
   forbidding its own compliant idiom.
2. **The worktree was never reset between iterations** (research `edc004ac`). A failed authoring
   attempt left its edits behind, so the next iteration's "did the actor actually change
   something" check was satisfied by the previous attempt's leftovers.
3. **The profile described a surface the A/B never measured** (research `30b71b44`) — the big
   one. `hotspots.profile` defaulted to `pp=0, tg=32` (DECODE) and `run.py` never overrode it,
   while `--surface` defaults to `pp512` (PREFILL). **No hypothesis derived from that table
   could ever have been kept.** `pp`/`tg` are now required arguments. Found by the loop's own
   critic, unprompted, at a cost of one planner call.
4. **Three inconsistent noise floors** (research `7fe7bd4d`), resolved above.

**Structural finding, now in `program.md`:** on `pp512` about **51% of device time is
rocBLAS/Tensile GEMM** (`Cijk_*`) — vendor library code this loop cannot patch. Prefill is a
dequantize-then-vendor-GEMM path: `dequantize_block_q4_K` (15.06%) → `convert_unary` (9.32%) →
Tensile (51.33%) = **75.7%** of device time. `tg128` by contrast dispatches `mul_mat_vec_q`,
entirely our source. **Surface selection is an open operator decision**, and note that every
seeded hypothesis is a decode hypothesis.

### The information base is seeded (2026-08-28 evening)

The loop shipped with two inbound channels and nothing in either — the `inbox/` directory did
not exist. Harvested from the backlog and verified into the live rendered context, not merely
onto disk:

- **`inbox/`** — `AK-H-QL-1/2/3`, the quant-ladder occupancy knee (`autokernel-research-loop.md`
  §22.1, still unchecked), and the ranked dequant-gap levers L1–L8
  (`mi210-q8-dequant-gemv-roofline.md`), each carrying its falsifier.
- **Measured negatives** into the experiment store under a synthetic historical epoch, so
  `recall()` marks them stale: the mechanism transfers, the number does not.
- **`program.md` now reaches the actors at all** (research `c4e74739`). Its own "Settled — do not
  re-open" section names `GGML_IQK`, MMQ and HIP graphs as already in v9 — exactly what the
  planner proposed for nine straight iterations. Nothing had been wired to hand it to anyone.
  It also now carries the measured gfx90a receipts (32 LDS banks / 8 phase cliques, no fp8
  MFMA, our `mma.cuh` tile ≡ HipKittens `rt_base`) and what `test-backend-ops` cannot catch.

Tooling: `python3 -m autokernel.loop.seed --store <store>` (idempotent). A test refuses any
seeded lever that a seeded negative refutes — added after this session seeded
KV-quant-at-long-context as live when 05c gap-list L14 had already killed it (−16.7% GDN,
−6.9% dense 27B).

- **Run 9 is executing** (10 iterations, `pp512`, seeded, profile and measurement now matched).
  P4 exit remains **UNMET**: it needs ≥6 measurements and ≥1 champion commit.
- **The loop is visible at `:8100/loop`** (root `c639a01c`) — state, three-valued freshness,
  every disposition including negatives, and GPU held-vs-busy. That last number reported
  **100% idle across 62 minutes of held claim** on run 6, which is what the surface exists to
  make impossible to miss. A sub-iteration heartbeat (research `f46c2860`) keeps a healthy
  long iteration from reading `stale`.

---

## The five verified causes

Each is independently sufficient to guarantee zero promoted improvements.

### 1. Promotion is disabled by configuration, and always has been

`"promotion_claim": false` appears **4,797** times across every artifact on disk; `true` appears
**zero** times. All 32 controller state files run under
`authority: nonpromotable_candidate_only_discovery`. All four `CHAMPION_UPDATED` records are
byte-identical bootstrap seeds pointing at the production commit the champion already was.

"Zero promotions after a month" was therefore never a discovery outcome — the output type excludes
it. Nothing in 107,707 lines of tests asserts that the configured authority permits the result the
campaign exists to produce.

### 2. The benchmark model is not what its filename says

Workload is pinned to `Qwen2.5-Coder-0.5B-Q4_K_M.gguf`. Parsing the GGUF header directly, 290
tensors: **132 × Q5_0**, 121 × F32, 13 × Q8_0, 12 × Q6_K, **12 × Q4_K**. `n_embd = 896`; K-quants
need a 256-element superblock and 896/256 = 3.5, so llama.cpp fell back to Q5_0 for nearly the whole
model. The kernel trace agrees: `mul_mat_vec_q<(ggml_type)6,…>`, 13,803 calls.

Production serves 122B IQ2 and 27B-class models whose hidden dims **are** divisible by 256 and
dispatch Q4_K/Q6_K/IQ2. **The Q5_0 path being optimized is never dispatched in production**, and the
loop's flagship hypothesis — proposed 38 times — is `akh-v2-q5-type-specific-dequant`. CH-6 measured
the transfer gap directly: `MMQ_MFMA` OFF-vs-ON is **+23.09%** on this model, **+0.50%** on
Qwen3.8-27B.

Compounding it, `discovery_deployment_factory.py:2052` passes only `GGML_HIP`, `AMDGPU_TARGETS`,
`GGML_NATIVE`. `GGML_HIP_ROCWMMA_FATTN` is never named, so it fell to CMake's default OFF — a path
measured to produce non-finite values at longer sequence lengths on gfx90a under `-fa on`. That was
an omission, not a decision.

### 3. The estimator is biased by more than the effects it reports

`scripts/benchmark/run_autokernel_gpu_discovery.py:3143` sets
`center = sum(anchor_samples)/len(anchor_samples)` — the **mean**. `:3209` reports `median(effects)`
— the **median** of candidate-versus-that-mean. Mixed estimators on the two arms.

Recomputed across all 25 two-arm results ever produced: reported mean effect **+2.22%**;
like-for-like median/median **+0.20%**. A **+2.01 pp** injection on every run, because the anchor arm
reliably carries a cold-start low outlier. **10 of 25 flip sign** when corrected; 7 crossed the 3%
nomination threshold as reported, **3 do honestly**. The observed nomination rate (7/25 = 28%) is
what bias-plus-noise predicts under a true null (≈29%).

Design compounds it: `anchor_processes: 1, candidate_processes: 1` with nine reps inside each process
means n<sub>effective</sub> = 1 per arm. The same candidate identity in v31 measured **+5.369%** and
**−1.714%** on two runs of identical code.

### 4. The planner is blind, and so is the critic

- **Refusal reasons never reached it.** `prior_authoring_refusals` filtered on status
  `planner_refused`; the status actually written is `authoring_refused`. Measured across v28–v34:
  **22 vs 1**. Fixed on a lane 2026-08-28 (`1b9beb88`); the *memory* was not.
- **No memory.** 355 hypothesis-ledger events across 123 ledgers, and only three of seven event kinds
  have ever fired: `CLAIM_AUTHORIZED` 209, `OPENED` 129, `ATTEMPTED` 17.
  **`RESOLVED` 0 · `ADOPTED` 0 · `FALSIFIER_PROPOSED` 0 · `REOPENED` 0.** The loop has never resolved
  or adopted a hypothesis. Every crash minted a fresh sealed deployment and reset the counters.
- **No live profile.** `rocprofv3 --kernel-trace` runs on every attempt under a sealed closure,
  producing per-kernel durations, dispatch counts and workgroup geometry — and
  `discovery_controller.py:1575` reads exactly one field (`relative_improvement_fraction`).
  3,869 LOC of `gpu_source_evidence.py` delivering one float into one branch.
- **No compounding.** Screening ran against the frozen anchor until CH-3 on day 25, so gains could
  not stack and no trajectory was visible.
- **The critic's own work was charged against the hypothesis.** `critic_revise` increments the same
  3-strike `bounded_authoring_skip` counter as a real authoring failure
  (`discovery_controller.py:3624`), so in v33 three turns retired
  `akh-v2-q5-type-specific-dequant` **without ever testing it**.

### 5. The gate moved, and that is what produced every KEEP

| run | anchor_drift | drift_bound | keep | blocks |
|---|---|---|---|---|
| r29 | 0.1527 | 0.0308 | false | 10 |
| r30 | 0.1879 | 0.0308 | false | 10 |
| r31 | 0.1406 | 0.0308 | false | 10 |
| r32 | 0.2010 | 0.0308 | false | 10 |
| r37 | 0.1104 | 0.0308 | false | 15 |
| — | — | **bound 0.0308 → 0.1850 (6.0×)** | — | — |
| r38 | 0.0708 | 0.1850 | **true** | 15 |
| r39 | 0.0927 | 0.1850 | **true** | 15 |
| r40 | 0.1100 | 0.1850 | **true** | 15 |
| r41 | 0.1585 | 0.1850 | **true** | 15 |
| r43 | 0.1504 | 0.1850 | **true** | 15 |

`r41` and `r43` were accepted at drift **exceeding** `r29`'s, which was rejected. Nothing in the test
suite caught it. The rebuild emits any change to a threshold, bound or block count alongside the
results it changes.

---

## Supporting measurements

| measure | value | source |
|---|---|---|
| funnel | 660 planner intents → 567 `planner_transient` → 91 pre-screen → **17 benchmarked** → 0 promoted | all `events.jsonl` |
| gate refusals | 83, outbidding completed measurements 4.9 : 1 | same |
| journal contents | 2,279 records = 2,275 `STOP_STATE` + 4 `CHAMPION_UPDATED`; **zero measurement records** | same |
| executing system | **29 files / 48,634 LOC** of 132 files / 153,865 LOC — 68% never runs | `discovery_supervisor.py:49 GRAPH_EXECUTION_MODULES` (byte-attested, runtime-enforced) |
| GPU held, lifetime | **1.403 h** across 122 claims, mean 41.4 s | `operations/claims/device.jsonl` |
| compiling, lifetime | **29.0 h**; `-j 1` in **77/77** build logs on a 192-thread host | `discovery_static_registry.py:3139`; build logs |
| iteration breakdown | median 2,675 s = build 2,025 (75.7%) · planner 412 · critic 100 · **measured 105 (3.9%)** | journal |
| anchor rebuilds | 44 of 51 compiled a byte-identical tree — `build_key` hashes `patch_sha256`, which the anchor does not depend on | `discovery_static_registry.py:1953` |
| churn since 2026-07-25 | **271,216 insertions / 92 deletions** (2,948 : 1), 514 commits, 427 in one week | `git log --numstat` |
| runtime state | 41 GB, plus 111 sealed execution closures at 1.7 GB | `du` |
| scale | machine is **6.2×** the size of the CUDA/HIP backend it edits (42,494 LOC) | `wc -l` |
| the harnesses that worked | `mmq_mfma_recheck.py` (154) + `champion_anchor_validation.py` (156) = **310 LOC** | — |

`CampaignScreener` — `campaign.py`'s only bridge to the live loop — appears **exactly once** in all
three repos: its own `class` statement at `discovery_controller.py:1415`. Never instantiated,
imported or tested.

---

## Phases

Ordered so nothing expensive runs before the thing it depends on is correct. **Every exit criterion
is a measurement, not a checkbox** — work reported complete on the strength of a green test is the
failure mode this program exists to end.

- [ ] **P0 — File this rider + index row.** Exit: `python3 scripts/handoffs/index_state.py --check`
      exits 0 and this page names the current phase and next action.

- [x] **P1 — Close the feedback loop.** ✅ 2026-08-28. Research `e1ebf691` (P1.1), `8248e3d7`
      (P1.2), `c3034ede` (P1.4); root `a353381a` (P1.5).
  - [x] P1.1 Route the per-kernel hotspot table (already produced) to the planner and both critic
        passes. Extend `gpu_source_evidence._exact_duration_comparison` (`:3059`); thread into
        `discovery_controller.py:1521-1591`.
  - [x] P1.2 Experimental memory. **(a)** Long-lived campaigns — stop every crash re-minting the
        deployment and resetting counters; the supervisor already resumes from durable state.
        **(b)** `experiments.md` + a small SQLite index carrying hypothesis, mechanism, patch summary,
        gates, effect with sample vector, verdict — **negatives written up as carefully as wins**.
        **(c)** Epoch-hash staleness borrowed from
        `repos/epyc-orchestrator/orchestration/repl_memory/strategy_store.py` (AP-28): each record
        stores a hash of the files defining its epoch; retrieval validity-penalises cross-epoch
        records. **Idea only — no FAISS, no FTS5, no RRF.** That store is 2,076 LOC; ours is ~150.
  - [ ] P1.3 Planner and both critic passes receive the same bundle: hotspots · `experiments.md` ·
        prior refusal reasons verbatim · `hypotheses/inbox/` · champion diff to date.
  - [x] P1.4 Fix the estimator (`run_autokernel_gpu_discovery.py:3143`) — one estimator on both arms
        — then re-score all 25 historical results and publish before/after.
  - [x] P1.5 Fix `scripts/vidya/cli.py:633` (`choices=["intake"]`), which strands **2,601** gradeable
        ClaimTuples the ten autokernel adapters already produce correctly.
  - **Exit — MEASURED 2026-08-28:**
    - Re-score published (`artifacts/autokernel-rescore/rescore.json`, research). All 25 historical
      two-arm screens, every stored `median_relative` reproducing exactly from raw samples through
      the producer's own centre rule: reported **+2.215%** vs like-for-like **+0.202%** —
      **+2.014 pp** injected. **10 of 25 flip sign.** Nominations **7 → 3**. Anchor median-vs-mean
      gap **+1.959%**, the mechanism.
    - `vidya` ledger 12,538 → **13,141**: **603 autokernel frames persisted for the first time**
      (aux_receipt 234, reward_integrity 159, governed_receipt 135, rocm_diagnostic 66,
      evaluation_event 9). The audit's "2,601 tuples" figure did **not** reproduce on the real
      walk; 603 is what the corpus yields today, and the walk reports its own four-way accounting
      (projected / refused / declined / not-an-entry-point) rather than a single number.
    - Context wiring pinned by test rather than by transcript (no campaign may launch before
      Phase 2): `kernel_hotspots`, `prior_experiments`, `prior_authoring_refusals` and
      `prior_results` all present in the bundle both actors read.

- [x] **P2 — Fix the measurement surface.** ✅ 2026-08-28, research `abcdf787` + the recipe/
      contract commit before it.
  - [x] Replace the 0.5B Q5_0 workload with a quant-ladder rung sharing a dispatch path and size
        regime with production. **Measure prefill** — `-p 0` means it currently never is.
  - [x] Write the explicit versioned build recipe: every flag named, and every flag differing from
        production carrying its reason. Divergence becomes a recorded decision, never an unset
        variable.
  - [x] Paired design — alternating arms across *processes* (`--arm-pairs`, default 1 so
        existing sealed operations resume byte-identically; `arm_schedule()` is a real function
        the runner calls, not a shape reimplemented in a test). Model on
        `scripts/benchmark/mmq_mfma_recheck.py:131-141`.
  - [x] Emit gate parameters alongside the results they gate — `gate_parameters.snapshot()` on
        the row it decided, `diff()` labelling a loosening **WIDENED** with its ratio, both
        reaching the planner and both critic passes.
  - **Exit:** A/A run, n=20, publishing the measured noise floor, which becomes the keep-threshold; a
    known-good and a known-null patch both classify correctly.

- [x] **P3 — Throughput.** ✅ 2026-08-28, research `c05b1bdb` — **except two items
      deliberately unshipped rather than shipped blind**, both recorded below.
  - [x] `BuildParallelism(jobs=1)` → `jobs=64` with `cpu_list` / `load_average_cap` (fields
        `execution/worktree.py` already carries at `:2249` and `:2597`).
  - [x] **SHIPPED and validated on a real build 2026-08-28** (research `d9254d31`).
        **Measured first:** a full HIP build of frozen v9 with the house recipe took **1,012 s at
        `-j1`** (the median across 77 logs) and **65 s at `-j64`** — 15.6×, so the width fix alone
        takes an attempt from 33.7 min of compiling to 2.2. `anchor_build_key` is the contract
        minus exactly the candidate fields; reuse is verified on source-tree digest, defines,
        anchor key, artifact presence and recorded targets, and any failure falls through to a
        fresh build rather than raising. **Validated against the real 65 s build:** reuse HIT in
        **0.18 s**, MISS after a one-line change to `vecdotq.cuh`, HIT again after reverting.
        The replayed `BuildResult` is the real one, persisted beside the build, because the
        materialization record downstream hashes it.
        *Bug this caught:* `integrity.hash_source_tree` returns a `TreeDigest`, not a string, so
        the receipt would not canonicalise — and a broad `except` was swallowing it into a
        permanent silent cache miss. The except is now narrowed to `OSError`/`StaticRegistryError`.
  - [ ] ~~NOT SHIPPED — cache the anchor build.~~ *(superseded by the entry above)* `_build_key_contract` hashes
        `patch_bundle_sha256`/`patch_sha256`/`proposal_sha256` into ONE key covering BOTH plans,
        so the anchor — built from the instrument commit, independent of the patch — gets a new
        key per candidate; **44 of 51 anchor builds compiled a byte-identical tree.** Splitting it
        needs two cache transactions where the reservation, `_validate_ref`, materialization and
        recovery paths all assume one entry per operation, and reusing a completed build means
        relaxing `BuildDirNotFresh` (§8.5.1). That is crash-recovery-critical machinery that
        cannot be exercised without a real ~15-min HIP build; shipping it unvalidated risks
        breaking a loop that is otherwise now fixed. **Worth ~50% of build time.**
  - [ ] **NOT SHIPPED — ccache.** `execution/README.md` documents that `GGML_CCACHE=OFF` is
        FORCED because with it on `chain.build_evidence` sets `incremental_objects_present=True`
        and the clean-build gate FAILs — correctly, since a cache populated by another tree makes
        the actor's build state part of the artifact. Same class of change as above, for a benefit
        that overlaps the anchor fix. (`-DGGML_CCACHE=OFF` in 77/77 — the §8.5.1 clean-build
        rule governs *promotable* artifacts and this path is non-promotable by construction).
  - [x] Disk expiry — `storage.expire_artifact` had zero callers; `autokernel_storage_report.py`
        is the missing caller and REPORTS (`--force` refused: reclamation authority is
        operator-only). Measured 33.16 GB / 358 dirs: 16.03 GB reclaimable build trees,
        17.13 GB unclassified and deliberately untouched; run `_recover_incomplete_attempt`
        at controller start for all incomplete attempts.
  - [x] GPU-seconds-held and idle-while-claimed on every result row (`gpu_utilization.py`).
  - **Exit:** median iteration < 900 s over ten consecutive iterations, utilization reported.

- [ ] **P4 — Rebuild the loop** (~1,500 LOC), in a lane alongside the current one, never in place.
      Two-pass critic with explicit loopbacks (below). Seed Champion₀ = frozen v9 + the build recipe;
      screen against the champion so gains compound. Drop the pre-declaration contract
      (`source_candidate.py:476`).
  - [x] P4.1 ✅ 2026-08-28 — `docs/guides/agent-workflows/agent-loop-design.md` — the loop block as the normative spec,
        plus the convention that agent-loop work opens with one. `program.md` in the loop package
        carries the same block as its first section.
  - **Exit — NOT MET.** Ten consecutive iterations, zero crashes, ≥6 reaching a measurement, ≥1
    accepted patch committed onto the champion branch and re-measurable from a fresh checkout.
    Transcripts must show a **completed loopback** — a pass-1 rejection whose reason appears
    verbatim in the planner's next hypothesis, which is then accepted, and the same for pass 2.
    The loopback is proven **in test** (mutation-tested three ways: discarding the pass-1 reason,
    charging a patch rejection to the hypothesis budget, and ignoring the noise floor each fail
    exactly the two tests that should catch them). It is **not** proven against a real planner on
    real hardware, and this handoff does not claim it is.

- [ ] **P5 — Strip.** Only after P4 proves the replacement. Delete `FOOTPRINT.md` and
      `test_campaign_footprint.py` **first**, so later deletions stop costing a regeneration each.
  - **Exit:** after each deletion batch the loop still passes P4's criterion. Not "tests green" —
    *the loop still measures*.

- [ ] **P6 — Reconnect the surfaces.** CI DONE (root `.github/workflows/tests.yml`); the
      surface rewrite is not started.

      **Measured baseline for the red tests, so the next session does not re-derive it:** the
      dashboard autokernel suites are **11 failed / 60 passed at `origin/main`** — verified in a
      clean worktree, so they are pre-existing and unrelated to this program's changes. They fail
      because `server.py` pins content digests of *another repository's* source modules (29 paths,
      47 digests). **Do not re-pin them.** That is the defect P6 exists to remove, and re-pinning
      digests on code slated for replacement only re-arms the landmine. Rewrite, then delete the
      6 obsolete test files.

      One audit claim did NOT reproduce: `tests/test_dashboard_operator_gates.py:51-57` *does*
      override `OPERATOR_GATE_BUNDLE_JSON`, so "zero of 168 override it" was overstated. The
      hermeticity concern stands for the autokernel suites specifically. Rewrite the `dashboard/server.py` kernel surface (~11,500 of
      12,841 function/class lines) with **no cross-repo pinning** — it currently pins 29 producer
      source paths and 47 SHA-256 digests of another repo's modules, so renaming a producer module
      silently drops a deployment off the live surface. Repoint the vidya adapters. Fix the 40
      currently-red root tests and their non-hermetic `OPERATOR_GATE_BUNDLE_JSON` reads. Add CI that
      runs pytest — `.github/workflows/` contains only `docs.yml`.
  - **Exit:** dashboard reports correctly with the loop up **and** down.

- [x] **P7 — Anti-regrowth** ✅ 2026-08-28, research `10f0214e`., as enforced mechanisms rather than documentation: a CI-enforced LOC
      budget on the loop package; **no test may assert the contents of a documentation file**; one
      end-to-end test that cannot pass vacuously (a deliberately-slower patch must be rejected and a
      known-faster patch accepted, both through the real build and the real benchmark); the weekly
      artifact is the scoreboard, and a week with no rows reports exactly that.
      **Note on the guard itself:** its first doc-coupling detector was VACUOUS — a regex over
      assert lines found zero hits against `test_readme.py`, which does pin README prose, because
      the real assertions compare a module constant against `self.text` rather than an inline
      literal. It now detects the coupling, and a test fails if it ever stops finding
      `test_readme.py`, so the vacuous version cannot return silently.

---

## The rebuilt loop

**This block is the canonical specification of the loop and the alignment artifact for the whole
program.** Published verbatim as
[`docs/guides/agent-workflows/agent-loop-design.md`](../../docs/guides/agent-workflows/agent-loop-design.md),
which also carries the convention itself. It is normative: if an implementation and this block disagree, the block wins until it is
deliberately amended here. Operator convention, ratified 2026-08-28 — *agent-loop work opens with a
pseudocode expression of the loop (actors, what each reads, what gates it, where every rejection
goes, and which single step is expensive) and gets alignment on that before any plan is written
around it.* Three design corrections came out of one review round on this block that prose had hidden
across several turns. Carry it verbatim into the guide docs (P4) so its shape outlives the session.

```
when the champion changes (at most weekly otherwise):
    rocprofv3 the champion → ranked hotspots

each iteration, planner works in a worktree with the full toolbox:
    reads   champion · experiments.md · hotspots · hypotheses/inbox/
    probes  FREELY — llama-bench, rocprofv3, test-backend-ops -o OP --perf,
            llvm-objdump for VGPR/occupancy, env-flag sweeps. Nothing gated.
    forms   hypothesis H, backed by evidence it gathered itself

HYPOTHESIS REVIEW LOOP · budget 3 rounds
    CRITIC PASS 1 reviews H — no patch exists yet.
      rejects on: already measured · mechanism unsupported by the profile ·
        no falsifier · wrong surface · already present in v9
      REJECT → reason returned VERBATIM to the planner, which refines or
        regenerates H and re-enters. It still has the toolbox and may go
        probe to answer the objection.
      BUDGET SPENT → record refused_at_formation with every reason and pick a
        DIFFERENT hypothesis. H is NOT retired; it re-enters the pool carrying
        its rejection history and may be revisited once the profile moves.
      cost of a rejection: one planner call. No patch, no build, no GPU.

    planner writes patch P implementing the accepted H

PATCH REVIEW LOOP · budget 2 rounds
    CRITIC PASS 2 reviews the committed diff P.
      rejects on: P does not implement the accepted mechanism · scope creep ·
        correctness risk · edits a file that must stay byte-identical to production
      REJECT → reason returned VERBATIM; planner rewrites P. H is untouched —
        a bad patch is not evidence against the idea.
      BUDGET SPENT → record refused_at_authoring and hand control BACK to the
        hypothesis loop, so H can be refined knowing it could not be implemented
        cleanly.
      cost of a rejection: one authoring call. No build, no GPU.

    build (ccache, -j64)   → fails? reason returns to the planner, rewrite P
    test-backend-ops       → fails? reason returns to the planner, rewrite P
    A/B alternating, n=10  ← the only GPU spend in the whole iteration

    keep → commit onto the champion branch
    else → negative, with mechanism and sample vector, into experiments.md
```

**Three separate budgets, none feeding another:** hypothesis rounds, patch rounds, measured attempts.
**Every rejection returns its reason to the actor that can act on it**, and nothing is retired without
the planner having seen why. Pass 2 sits **before** the build, since the build is the most expensive
step; the tradeoff is that it judges the diff without knowing it compiles, which is acceptable because
a compile failure is cheap and returns automatically.

Custody is **not** rebuilt. Promotion stays
[`docs/reference/kernel-freeze-runbook.md`](../../docs/reference/kernel-freeze-runbook.md) plus
`kernel_freeze_scope.py` — seven steps, ~100 lines, and they shipped v7, v8 and v9.

---

## Strip inventory

Reachability from `GRAPH_EXECUTION_MODULES`, corroborated by AST import closure and on-disk artifact
search. **Do not act on this before P4 passes.**

| order | target | src | tests | evidence |
|---|---|---|---|---|
| 1 | `release/**` | 18,770 | 13,379 | No entry point — zero `__main__`, zero argparse. 7 of 8 output schemas have zero instances on disk. Never executed. |
| 2 | `campaign.py` + 16 modules that fall with it | 14,649 | ~9,000 | `CampaignScreener` never instantiated; `HostOps` constructed only from `main()`. |
| 3 | `evaluator/statistics.py` + `controls.py` | 6,095 | 4,310 | Refused by its own driver — `campaign.py:158`: *"made the gate unpassable at B_min"*. 578 LOC never referenced anywhere. |
| 4 | `controller/arena_*` (5 vendor adapters) | ~8,500 | — | Admitted as source-availability providers; never wired into discovery, never ran a search. |
| 5 | orphan roots (`fault_rehearsal`, `prior_art`, `substrate`, `lanes`, `profile_report`, …) | 7,274 | ~2,400 | Zero non-test importers; no artifacts beyond four one-off 2026-08-12 rehearsal dirs. |
| 6 | `c3_epyc_*` · `adapters/whisper_stt` + `qwentts_tts` · `c5_*` · 3 of 5 `least_commitment_*` | 11,437 | ~5,900 | STT/TTS adapters serve the unreachable release plane; deleted once by `2d89e90b`, restored by `b367d09f` **without a caller**. `archives/` is empty. |
| 7 | `chain.py`, `screening_baseline`, `provider`, `claim_witness`, `baseline_honesty` | 3,602 | ~4,475 | `campaign.py`-only; zero artifacts. |

**Rewrite-smaller** (live but oversized): `gpu_source_evidence` 3,869→850 · `hypotheses.py`
4,493→150 · `correctness.py` 4,160→800 · `microbench.py` 4,734→150 · `schemas.py` 3,783→350 ·
`do_not_repeat.py` 2,205→0 · `discovery_static_registry` 3,344→750 · `worktree.py` 3,134→1,300.

**Keep unchanged:** `resource/device_claim.py` · `gpu_residency_sampler.py` ·
`split_runtime_verifier.py` (encodes the three-ggml-generations hazard) · `instrument_integrity.py` ·
`device_sampler.py` · `inference_window.py` · `gpu_source_proofs.py` · `discovery_telemetry.py` ·
`execution/sandbox.py` · `powercap_broker.py` · `physical_bounds.py` · `oracle_integrity.py` ·
`campaign.decide()` (147 LOC — it correctly refused six runs on anchor drift).

---

## Operator decision package

Prepared as `scripts/operator/ratify_*.sh` for the operator to run. **None of these blocks the
program**; each phase proceeds without them.

- [ ] **D1 — amend `P-AK-SEARCH-1` denial 4.** It permits a later campaign to use a prior record
      *"for hypothesis formation only — never to **rank**, bank, compose, or contribute to
      readiness."* Choosing what to attempt next *is* ranking, so a planner that reads its own
      history to prioritise is non-conformant on a strict reading — very likely why the memory was
      never built and why one patch was proposed 38 times.
      **Requested (Option 4):** prior records may inform ranking, provided each carries the hash of
      its epoch (anchor commit, build recipe, host state) and cross-epoch records are
      validity-penalised at retrieval. No banking, no promotion authority, no readiness contribution
      — those denials stay verbatim. The mechanism is borrowed from autopilot's AP-28 store, not
      invented. Annex K is human-amendment-only (invariant 15), so this is the operator's write.
      **Staged for you:** `scripts/operator/ratify_ak_search_1_a3_20260828.sh --show` to read it,
      `--apply` to stage the amendment with an isolated `git apply --cached`. The store already
      ships with `ranking_authorized=False`; applying this is what lets that flag be turned on.
      P1.2(a) ships regardless — it is a bug fix, and denial 4 governs *cross-campaign* reuse only.
- [ ] **D2 — add a `T-screen` tier below T0**, requiring only: held claim, residency evidence, named
      anchor commit, codified recipe, and a once-per-host-state A/A noise floor. Drops, **for
      screening only**, the per-campaign calibration solve, byte-for-byte anchor re-verification at
      both window edges, evaluator runtime source-label attestation, and the storage-floor re-check.
      Every denial in *"what this protocol does NOT authorize"* stays verbatim.
      Context: P-GPU-1, the inherited rule, gates the **claim class, not the run**. The eight
      experiment-time preconditions come from P-AK-SEARCH-1, ratified 2026-08-03T08:30:05Z — six
      hours after this program's first commit (`75764052`, 02:15) and cited as a requirement by its
      third (`10843b6f`, 11:29, *"conforming to the ratified P-AK-SEARCH-1"*).
- [ ] **D3 — build recipe as a champion arm.** Recommend adopting **neither** standing config win —
      CH-6 settled both (`MMQ_MFMA` +0.50% on the 27B; `ubatch` a null arm, since llama.cpp clamps
      `n_ubatch = min(n_batch, n_ubatch)` so both screens ran one identical binary) — but extending
      `champion.py` to carry a build recipe anyway, since that is where the real wins have always
      lived and it is currently inexpressible.

---

## Notes for whoever picks this up

- **The science inputs are good.** All 21 portfolio hypotheses name a real `ggml-cuda` file and a
  real kernel symbol, with rocprof-measured device-time shares and pre-declared nulls. The failure is
  entirely downstream. Do not rewrite the hypotheses; carry them as a seed file for the generator.
- **The vidya adapters work** — 2,601 gradeable ClaimTuples against the real corpus, and adapters that
  should refuse do refuse. They have never persisted a row because of one line (P1.5).
- **`experiments.md` is the loop's real product**, not the receipts. It is the selector, and it
  replaces 5,713 LOC of `hypothesis_portfolio.py` + `controller/hypotheses.py`. Negatives get the same
  care as wins, or the planner learns nothing.
- **The diagnosis, in one line:** AutoKernel chose verification by *proof* where verification by
  *reproduction* was available. Proof's cost grows with the number of steps and has no stopping
  condition; reproduction costs one re-run. A `llama-bench` re-run costs 90 seconds and the tree is a
  git commit — proving a run was honest cost 3,869 lines to deliver one float.
