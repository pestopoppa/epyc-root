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
  17 tests run in 0.05s with no GPU, no API key and no ROCm. It has since grown continuous
  operation, a seven-lane pool with one serialized tail, an advancing anchor and a STOP sentinel;
  each attempt costs the external codex planner and hours of GPU.
- **P4 exit MET BY THE LETTER in run 11** (2026-08-29: 10 iterations, 8 reached a measurement,
  2 champion commits). **Do not read it as met in spirit before run 16.** Until D9 was fixed the
  anchor was a fixed v9 binary while the candidate tree accumulated every keep, so **every effect
  through run 13 was CUMULATIVE, not marginal** — a −2.864% regression was committed as a
  "+1.846% keep". The **first genuinely marginal champion advances are run 16's two and run 18's
  `5ad3e36d`.** Runs 12–18 and defects D7–D14 are written up in `progress/2026-08/2026-08-29.md`
  and `progress/2026-08/2026-08-30.md`.
- **CHAMPION: `5ad3e36d`** (`akm-q4k-chained-dp4a`, +9.321% marginal) on branch
  `ak/loop-champion-20260828` in `/mnt/raid0/llm/tmp/ak-loop-tree` — **36 commits above the
  frozen v9 tip `0db32c06`**. Provenance: run 11 (2) · run 13 (1 surviving of 4; the other three
  were cumulative artefacts, demoted and tagged `ak/pre-anchor-fix-full-history`) · run 16 (2) ·
  run 17 (30) · run 18 (1 so far). **Run 17's 30 commits were audited as a block** against what
  the run started from (`432e501f`): **+3.942%, decisive, no drift, residency 40/40, clocks
  stable** (`run17-audit/total.json` in the store) — so they were KEPT rather than rolled back.
  Their individual attribution is not recoverable (D14) and is not worth the device time.
- **RUN 18 IS LIVE and unattended** — pid `3307803`, ~6.5 h in as of 2026-08-30, anchor
  `8fd1b23a`, **7 lanes, continuous, 20 pairs, floor 1.188%**. Holds the `mi210_0` claim, pid also
  in `/workspace/tmp/ak-loop-deploy/run18.pid`, writing to
  `/mnt/raid0/llm/autokernel/loop-memory/` (`loop-status.json` is the live view). **One keep so
  far:** `5ad3e36d akm-q4k-chained-dp4a +9.321%`, champion advanced correctly.
  **GPU idle-while-claimed is running 35–40%** and is now reported on every row — that is the
  next efficiency target, and it is only visible because the row carries it.
  Do not start GPU work, builds, `llama-bench` or `test-backend-ops` while it runs, and do not
  touch `/mnt/raid0/llm/tmp/ak-lanes`, `ak-loop-tree` or `ak-lane-builds`.
- **SURFACES CONSOLIDATED 2026-08-30** — there is now exactly **one** kernel dashboard page,
  `/loop`, titled **Kernel R&D**; `/kernel` 301-redirects to it and `kernel.html` is deleted.
  See P6.1–P6.4 for what landed and P6.5–P6.8 for what is knowingly left open.
- **Next action:** let run 18 finish, then audit its block the way run 17's was audited — rebuild
  both ends of the range from `ak-loop-tree`, `gates.op_correctness`, then `bench.compare` at 20
  pairs under a held claim. The run-17 audit ran from an ad-hoc driver at
  `/workspace/tmp/ak-loop-deploy/audit.py`; **promote it into the research repo before reusing
  it**, or it is untracked evidence. Then **P5 — the strip** is unblocked: it was gated on the
  replacement being proven, and the run-17 audit is that proof.
- **Noise floor — RECALIBRATED 2026-08-29 (D8), the 2026-08-28 table is SUPERSEDED for decode.**
  The old table was p95 |median effect| over subsets of ONE fixed 20-pair sample, which cannot
  exceed that sample's own tail and so understated p95 by construction. Rebuilt by bootstrap from
  a three-condition A/A campaign (fresh pairs, true effect zero) — `bench.MEASURED_FLOOR_PCT`:

  | pairs | prefill (UNCALIBRATED, old method) | decode (bootstrap) |
  |---|---|---|
  | 5 | 0.479% | **2.422%** |
  | 9 | 0.168% | **2.021%** (was 1.175% — low by 0.846 pp) |
  | 20 | 0.029% | **1.188%** (was 0.067%) |

  **All runs from 13 onward use 20 pairs at 1.188%.** `pp512` was not measured by that campaign
  and its row is still the superseded construction — recalibrate before trusting any prefill
  verdict. `--pairs` must be ≥5; `WARMUP_PAIRS = 1` is discarded before measurement.
  Artifacts: `artifacts/autokernel-aa-noise-floor/` and `loop-memory/aa-campaign/` (research).
- **Filed, not fixed:** the loop keeps on a SINGLE comparison and cannot pool repeated
  measurements of one mechanism, even though its planner reached for pooling unprompted twice
  (run 11 measured one patch six times, run 15 measured one five times). See D8.

### Runs 5–9, and the harness defects they exposed (2026-08-28 evening; D5–D6 in
`progress/2026-08/2026-08-29.md`, six in total)

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
entirely our source. **Surface selection was resolved 2026-08-29 in favour of decode** after
the `GGML_CUDA_FORCE_MMQ` build arm returned a bounded null (+0.105%, inside the 0.973% floor,
9 pairs, no drift): prefill's one structural lever does not exist, and every seeded hypothesis
is a decode hypothesis. Prefill's MICRO lever is untested rather than refuted — run 9's seven
`MUL_MAT` refusals were fabricated.

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

- **Run 9 finished 0/10** — 10 iterations, 149 min, zero measurements. Every refusal was
  produced by a broken instrument, not by the science: 7 of 10 died on a `MUL_MAT` verdict
  that was never measured (see D5 below).
- **Run 10 FINISHED (2026-08-29 morning)** — `tg128` decode, 9 alternating pairs, floor **1.175%**
  (the measured row, not the parametric 1.151% which sits below what the instrument resolves).
  10 iterations, 91.7 min, **5 measurements, 0 kept**. The full pipeline ran end to end for the
  first time (hypothesis → critic → patch → critic → build → correctness oracle PASSED → 9-pair
  A/B, 18/18 resident). **P4 exit was UNMET as of this run: it needs ≥6 measurements AND ≥1
  champion commit.** (Run 11 met it by the letter the same day — see CURRENT STATE.)
- **The run-10 finding — the anchor drifted, and the anchor cannot change.** 4 of the 5
  measurements were vetoed for drift, and in *every* one of them the drifting arm was the
  **anchor**: a fixed binary at `0db32c06`, same build and same workload on every invocation.
  Anchor drift ran **−1.465% to +4.175%** against a 1.175% floor, and for two of the four the veto
  was decision-changing (+1.664% and −2.067% both exceed the floor in magnitude and would otherwise
  have read as decisive). Root cause confirmed by **direct observation**, not inference: a passive
  read-only sysfs trace (2,554 samples / 21.7 min) found
  exactly two clock states — 800 MHz at 0.05% mean busy, 1700 MHz at 72.4% — so the card idled at
  800 and jumped to 1700 at the start of every benchmark window, a **2.125× transition**, and since
  each `llama-bench` invocation is its own process it paid that ramp every time. Detail and the
  per-mechanism table: `progress/2026-08/2026-08-29.md`.
- **Resolved — clocks are pinned.** The operator set `power_dpm_force_performance_level = high`
  (root-owned; we are uid 1000); verified `high` with `pp_dpm_sclk` pinned at 1700 MHz.
  **Run 11 IS EXECUTING** — identical to run 10 in every respect *except* the pin (same surface,
  pairs, floor, store, anchor), so the two are a clean comparison of clock policy alone.
  Independently of the pin, every residency proof now records `sclk_min_mhz` / `sclk_max_mhz` /
  `clock_stable` (research `44da8b2e`): a result taken across a clock change says so in its own
  record. The pin is host policy a reboot or another session can undo — the record is ours.
- **Decode is 99.70% our own kernels, 0.00% vendor** (`mul_mat_vec_q<Q4_K>` 32.79%,
  `quantize_q8_1` 17.90%, `flash_attn_ext_vec` 10.31%) against ~51% vendor on prefill.
  That, plus every seeded hypothesis being a decode hypothesis, is why the surface moved.
- **The DVFS question is CLOSED** — it was opened at n=2 against `auto` clocks and is answered
  above by run 10's full drift distribution plus the passive trace. Pinned clocks were chosen over
  extra warm-up pairs; if the drift veto still fires on the anchor under run 11's pin, DVFS was not
  the whole cause and the next candidate is more warm-up pairs (ours, no operator needed).
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
  - **Exit — MET BY THE LETTER, run 11 (2026-08-29); box left unticked pending operator sign-off.**
    The bar: ten consecutive iterations, zero crashes, ≥6 reaching a measurement, ≥1 accepted
    patch committed onto the champion branch and re-measurable from a fresh checkout.
    **Run 11 delivered 10 iterations, 8 measurements, 2 champion commits**; run 17 delivered 464
    iterations and 30 champion commits with zero lanes lost, and its block re-measures at
    **+3.942%** from a fresh build of both ends. **The caveat that matters:** every keep through
    run 13 was cumulative against a static v9 anchor rather than marginal against the champion,
    so "screen against the champion so gains compound" — this phase's own requirement — was only
    actually satisfied from run 15 onward. See CURRENT STATE.
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

      **Partial credit 2026-08-30, recorded so the rewrite does not redo it.** Four commits on
      `lane/ak-rebuild-20260828` (root): `0a18b132`, `7feec9d4`, `e0ceada9`. The loop-up/loop-down
      exit criterion is met for the surviving surface; what remains is listed as open boxes below.

  - [x] P6.1 — **`/loop`'s GPU panel had been dark since the surface's first commit** ✅ 2026-08-30
        (`0a18b132`). The reader looked for `held_s`/`busy_s`; the producer has always written
        `claim_held_s`/`device_seconds_under_load`. 41 tests passed over it because the hand-built
        fixture invented the *reader's* spelling, so fixture and reader agreed with each other and
        disagreed with the producer. **A fixture authored from the consumer's guess cannot witness
        the contract** — build fixtures from a real producer record.
  - [x] P6.2 — the `/kernel` card labelled "AutoKernel loop" was showing the **superseded v37
        controller**; corrected ✅ 2026-08-30 (`0a18b132`).
  - [x] P6.3 — **both named freshness gaps closed** ✅ 2026-08-30 (`7feec9d4`). The operator-gated
        Aggregate-champion `+48.9%` card had no envelope at all (`_read_operator_gate_bundle()`
        read no timestamp, so the number rendered identically forever after its producer died);
        the funnel's staleness verdict rendered only inside a collapsed `<details>`. Verified by
        aging the real record to 4 d and 20 d → `stale`, and deleting it → `absent`.
  - [x] P6.4 — **one surface, not two** ✅ 2026-08-30 (`e0ceada9`). `/loop` is now the single page
        titled **Kernel R&D**; `/kernel` 301-redirects to it; `dashboard/static/kernel.html` is
        deleted (1,833 lines); the operator-gated champion card moved across; the controller card
        was deliberately **not** ported. Verified live: redirect works, `/static/kernel.html` and
        two sibling paths 404, 24 routes swept with a non-vacuity control. Mutation 13/13 — and
        **M7 initially SURVIVED**, producing a green pill reading "STALE", because the test harness
        exposed only `innerHTML`/`textContent` so the assertion was literally unwritable; the
        harness now emits `class_by_id`. Dashboard failures 40 → 12, not byte-identical and
        legitimately so: 28 of the 40 lived in the deleted page's own test class.

      **Open, derived from the merge (2026-08-30) — do not close P6 with these outstanding:**

  - [ ] P6.5 — **retire the retired page's API surface.** `/api/kernel`, `/api/kernel/live` and
        `/api/kernel/health` still serve data nothing renders. Removing them strands
        `panels.PANELS["kernel"]` / `["kernel_live"]` and changes what `health_payload()` folds —
        a peer's live file, so it was deliberately left alone rather than done blind. Do it as part
        of the rewrite, with the panel registry and the health fold changed in the same commit.
  - [ ] P6.6 — **a hole in the freshness contract itself.** `/api/kernel` reports
        `reporting=observed, watchdog=idle` over a **16.8-day** export, because that producer
        travels the *compliant-silence* path the hub honours. The JSON therefore does not read
        stale even though the data is. Fix the contract, not the one endpoint: compliant silence
        must still carry an age, and an age past the envelope must degrade the verdict.
  - [ ] P6.7 — **`/api/loop/health` folds only the loop producer**, not the operator-gate bundle
        that moved onto the page in `e0ceada9`. A human is never misled — the verdict travels in
        the body and renders loudly — but an automated consumer is under-informed. It is pinned by
        a test, so widening the fold is a deliberate edit, not a drift.
  - [ ] P6.8 — **coverage genuinely lost.** The funnel and lane-hero render tests went away *with*
        the deleted page rather than being fixed. The reader still exists and nothing renders it;
        restore render coverage against the surviving surface when the funnel is re-hosted.

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

  - [x] P7.1 — **the guard's CI had never run a single assertion** ✅ 2026-08-30 (research
        `ac785d2d`). The autokernel-guards workflow was red on **43 of 43 runs since its first
        commit**, every one dying on `No module named pytest` before collection —
        `actions/setup-python` ships a bare interpreter. Because it looked identically red whatever
        the code did, it hid two real regressions for two days: `test_check_regrowth_guards` still
        asserted `LOOP_LOC_BUDGET == 3000` after the deliberate raise to 3400, and
        `test_experiments` asserted that the same refusal at two different times *deduplicates* —
        the exact opposite of the identity fix in `5090931d`, which put `recorded_at` in the hashed
        material precisely because identity had collapsed and repeated refusals were being dropped.
        **A permanently-red check is indistinguishable from an absent one.**
  - [x] P7.2 — **suite-floor guard** ✅ 2026-08-30 (research `7ee090a5`). Installing pytest closed
        the hole but not its *shape*: a suite that runs FEWER assertions reports the same green.
        pytest exits 5 on zero collected (verified) but a **partial** collapse exits 0. Floors
        declared for both suites (101, 196), `>=` never `==`. The guard found two defects in itself
        on first run — it laundered a collection error into a plausible "93 collected" (pytest
        prints the count on the same line as ", 1 error"), and its own test module had a
        cwd-dependent import. CI is green on research `main` with real counts in the log.
  - [ ] P7.3 — **`test_experiments.py` silently depends on cwd.** It imports only from the repo
        root, so 4 `MemorySurvivesADeployment` tests fail with
        `ModuleNotFoundError: No module named 'scripts'` when pytest runs from
        `scripts/kernel_rnd`. CI is green only because it happens to run from the root. Add a
        `conftest.py` with a `sys.path` insertion so the suite is location-independent.
        (epyc-inference-research.)
  - [ ] P7.4 — **the LOC budget is 182 lines from binding** (loop package at 3218/3400). When it
        next binds, the honest options are trimming `run.py` or excluding comment lines — 34% of
        the package is docstring and incident prose — **not another round-number bump**. Raising
        the number again is the failure mode the budget exists to catch; record the choice here
        when it is made.

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

## Declined 2026-08-30 — proposed, deliberately NOT filed as tasks

Recorded so they are not re-proposed. The operator narrowed this session's scope to the
kernel/AutoKernel surfaces; each item below was raised, then dropped on purpose.

- **Retiring the `autopilot`, `benchmarks` and `orchestrator-legacy` dashboards. DECLINED.**
  Proposed after widening a staleness audit past what was asked. Operator correction, verbatim:
  *"WHy would you touch autopilot???? THat loop AND dashboard both work… Stick to reviewing the
  kernel devlopemnt/autokernel dahsboard. That is ALL I asked you about."* Nothing was touched —
  verified: the registry diff changed only the two kernel rows.
- **The staleness verdict on `autopilot` was also wrong on the merits. DECLINED as a finding too.**
  `autopilot_alive: false` / `paused: true` is a **quiescent** producer, and a dashboard showing
  the last known state of a paused system is *correct*. A dead-producer rule was applied to a
  quiescent one. Generalises: quiescent ≠ dead, and the freshness contract must distinguish them.
- **`/dashboard/api/pareto` returns `decision_grade: true` while carrying its own
  `legacy_state_archive_warning`** saying the data is a legacy state-cache that must not be used
  for decisions — and `autopilot.html` renders two other warning fields but not that one. Verified
  directly. **Surfaced to the operator as a finding; not filed as our task** — it belongs to
  autopilot's owner and is outside this program's scope.
- **`machine` and `autopilot` have no entry in `panels.PANELS` at all**, so `/api/health` is silent
  about two of the eight registered surfaces. Structural and real; **out of scope now**, and not
  filed here because this handoff does not own those surfaces.

## Notes for whoever picks this up

- **Deploying a dashboard change: push to `origin/main` and STOP.** The hub supervisor gained
  `sync_dashboard_from_origin` + `check_hub_stale_source` on 2026-08-28: it fetches `origin/main`
  every 300 s, syncs changed `dashboard/` files and restarts the hub itself. This session twice
  asked the operator to `kill -TERM` the hub by hand when the supervisor would have done it
  unattended — because the usage text says *"Never restarts a healthy hub"* and the log that shows
  deploy-sync running was never opened. Hand-patching `/workspace` is both unnecessary and fragile:
  the sync has a provenance test that trusts only a blob which has existed on `origin/main`.
  **Read the log, not the usage string.**
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
