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

> **In four lines, 2026-08-31.**
> 1. **There is ONE champion now, by ratified invariant** (INC-20260831-champion-lineage-fork, root
>    `35c1a6d1`): the reconciliation merge **`a2728701`** (manual `270b48ed` + loop `4925b208`,
>    zero conflicts, disjoint file sets), measured **+12.618% tg128 vs production resolved live**
>    (264.53→297.91 tok/s, 20 pairs, decisive by 10.6×; pp512 +0.078% = NO CHANGE, floor still
>    uncalibrated — R18-D). Inside the chain-estimate band [11.2–15.3] → **additive, no
>    interaction**; the pre-committed contingency did not fire. Oracle 3/3.
> 2. **Run 21 is LIVE (pid `2767457`), operator-approved — worktree `champ2` on THE champion
>    branch @ `a2728701`, ranking ON. Do not touch it** (see the R21 block).
>    *(SUPERSEDED 2026-09-01: **run 23 is LIVE, pid `2214942`, surface dec-b4** — see the R23
>    block; R23-5's curve showed the tg128 headline collapsing on production shapes.)*
> 3. **Run starts are operator-gated** behind a verifiable readiness package — *"don't start ANY
>    run without my explicit permission"* — and the champion's baseline is the **CURRENT frozen
>    production, resolved live**, never a pinned sha.
> 4. **Next:** R18-B (run-18 forensics, still OPEN), **P5 the strip**, and the R21 follow-ups
>    (headline-at-startup, A/B evidence promotion, loop-branch retirement decision).

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
- **⚠ SUPERSEDED 2026-08-31 — the loop lineage below was a FORK (INC-20260831), merged into the
  single champion `a2728701`. Historical record only from here to the run-19 bullet.**
- **CHAMPION (loop lineage, historical): `5ad3e36d`** (`akm-q4k-chained-dp4a`) on branch
  `ak/loop-champion-20260828` in `/mnt/raid0/llm/tmp/ak-loop-tree` — **36 commits above the
  frozen v9 tip `0db32c06`**. Provenance: run 11 (2) · run 13 (1 surviving of 4; the other three
  were cumulative artefacts, demoted and tagged `ak/pre-anchor-fix-full-history`) · run 16 (2) ·
  run 17 (30) · run 18 (1). **Run 17's 30 commits were audited as a block** against what
  the run started from (`432e501f`): **+3.942%, decisive, no drift, residency 40/40, clocks
  stable** (`run17-audit/total.json` in the store) — so they were KEPT rather than rolled back.
  Their individual attribution is not recoverable (D14) and is not worth the device time.

- **THE HEADLINE MEASUREMENT EXISTS — champion `5ad3e36d` vs frozen production v9 `0db32c06`,
  2026-08-30.** Both arms built fresh from named commits with the *identical* recipe, 20
  alternating pairs, one claim held across both surfaces.

  | surface | production | champion | effect | floor | reading |
  |---|---|---|---|---|---|
  | **tg128** (decode) | 264.918 tok/s | 287.499 tok/s | **+8.524%** | 1.188% (calibrated) | **decisive by 7.2×** |
  | **pp512** (prefill) | — | — | +0.090% | 0.029% (**uncalibrated**) | **NO CHANGE** |

  Neither arm drifting · **40/40** invocations resident · clocks pinned 1700 MHz across all **80**
  invocations · correctness oracle rc=0, `2/2 backends passed`, on **both** arms. Published as
  `/mnt/raid0/llm/autokernel/loop-memory/champion-vs-production.json`
  (`epyc.autokernel.champion_vs_production.v1`), five-entry capability list, each entry carrying
  its own on-disk evidence path.

  **The pp512 row's `decisive=True` is an artifact and the row means NO CHANGE.** Its floor is
  the superseded uncalibrated construction (see the noise-floor bullet). The verdict does not
  depend on the floor anyway, because **the diff predicts it**: the 36 commits touch only the
  matrix-*vector* decode path and FA-vec — `mmvq.cu`, `vecdotq.cuh`, `quantize.cu`, `rope.cu`,
  `fattn-vec.cuh`, `fattn.cu` — and **nothing in `mmq.*`**, the batched prefill path.

- **⚠ THE PER-COMMIT RECORD ON THAT BRANCH IS INFLATED 20×. DO NOT QUOTE IT.** The 36 commit
  messages claim gains **compounding to +171.7%** (arithmetic sum +101.8%). The block measures
  **+8.524%**. This is run 17's cumulative-attribution defect (D14) at twenty times the magnitude.
  The only defensible statement about `ak/loop-champion-20260828` is the block number. Anyone
  reading those commit messages as marginal effects is reading a false claim — see R18-C.

- **RUN 18 WAS STOPPED, AND MOST OF IT WAS INVALID.** 188 iterations · 138 measurements · **1
  keep**. Stopped via the STOP sentinel; drained cleanly at **20:10:23Z** with `state: complete`.
  Split at the 11:03 champion promotion:

  | segment | n | median effect | **best** effect |
  |---|---|---|---|
  | BEFORE promotion | 16 | −1.441% | +0.060% |
  | AFTER promotion | 122 | −9.539% | **−5.642%** |

  After 11:03, **not one candidate of 122 could ever have been kept** — the whole distribution
  sits below zero by more than the +9.321% champion advance that had just landed. **The evidence
  sat in `experiments.db` for six hours while this session reported the run as healthy**; it was
  found only because the operator pushed back on the keep rate. *A loop still emitting well-formed
  measurements is not thereby working — "it is producing output" answers a liveness question, and
  nobody had asked one.*

- **RUNS 18–20 OPTIMISED THE WRONG BASE (INC-20260831-champion-lineage-fork).** The rebuilt loop
  was seeded 2026-08-30 from bare frozen v9 as a NEW sibling branch while THE champion
  (`ak/champion/llama-cpp-0db32c06e3e5` @ `270b48ed`, +3371/−146 over v9, DFlash2 + iqk dispatch
  gating + speculative, admitted via CH-7) sat one branch over. Surfaced when the operator asked
  why DFlash2 was absent from the dashboard capability list. **Ruling ratified into
  `agents/shared/OPERATING_CONSTRAINTS.md` (root `35c1a6d1`): one single champion per production
  kernel tree; seed-from-production legal only immediately after a promotion; a second lineage is
  a defect the moment it exists; standing resolved against CURRENT frozen production, live.**
  Enforcement shipped: single-champion **startup refusal** + live-resolved production baseline
  (research `470378a9`, 34/34 mutants, proven live both directions,
  attachment-stronger-than-tip-equality).
- **RUN 20 was killed on operator order** — STOP was honoured only at iteration boundary, so the
  loop "drained" ~50 min of idle-GPU through external codex calls. Fixed: **drain tiers**
  (research `95eeb0ae`) — STOP abandons at actor boundaries recording `stopped_mid_formation`,
  never mid-tail.
- **RUN 21 IS LIVE — OPERATOR-APPROVED — DO NOT TOUCH IT.** pid `2767457`, started ~11:5xZ
  2026-08-31. Worktree `champ2` attached to THE champion branch @ `a2728701` (startup refusal
  verified — first log line); anchor = the measured reconciliation build with provenance. 7
  lanes, continuous, 20 pairs, `tg128`, floor 1.188%, **ranking ON** (P-AK-SEARCH-1-A3). Off
  limits for every session: pid `2767457`, `/mnt/raid0/llm/tmp/ak-lanes`, `ak-lane-builds`,
  `champ2`, `build-champ-a2728701`. No GPU/CPU inference, no builds, no process management.
- **SURFACES CONSOLIDATED 2026-08-30** — there is now exactly **one** kernel dashboard page,
  `/loop`, titled **Kernel R&D**; `/kernel` 301-redirects to it and `kernel.html` is deleted.
  See P6.1–P6.4 for what landed and P6.5–P6.8 for what is knowingly left open. The champion
  headline card is now **one number against one named anchor** and renders `NOT YET MEASURED`
  until the A/B exists (root `bdeb450f` → `e1d22546`, 19/19 mutations caught).
- **Next action:** let run 21 run. Then (a) close out **R18-B** — the run-18 post-promotion
  forensics, still OPEN with three hypotheses refuted — and (b) **P5, the strip**, which is
  unblocked: it was gated on the replacement being proven, and the run-17 block audit plus the
  champion-vs-production A/B are that proof. The run-17 audit driver was ad-hoc at
  `/workspace/tmp/ak-loop-deploy/audit.py`; it has since been promoted as
  `scripts/benchmark/autokernel_champion_block_audit.py` (research) — use that, not the ad-hoc copy.
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
  verdict (**R18-D**; the champion-vs-production pp512 row is the first verdict this has actually
  bitten). `--pairs` must be ≥5; `WARMUP_PAIRS = 1` is discarded before measurement.
  Artifacts: `artifacts/autokernel-aa-noise-floor/` and `loop-memory/aa-campaign/` (research).
  The table lives at `scripts/kernel_rnd/autokernel/loop/bench.py:43`; the recalibration driver
  already exists — `scripts/benchmark/autokernel_recalibrate_floor.py` (it has an `--apply` mode
  that rewrites the table in place).

- **CORRECTION 2026-08-30 — GPU idle-while-claimed is NOT ~35%, and the 13.5% serialized tail is
  RETIRED.** Both figures were published by this session and both are wrong.
  `gpu_reading()` (`loop/run.py:358`) defines busy as **summed `Comparison.device_seconds`**
  (`run.py:367`), which counts only outcomes that produced a `Comparison` — so warmup pairs,
  `test-backend-ops` and every rocprofv3 profile contribute **zero busy while consuming held wall
  time**, even though the device is under load throughout. Roughly two thirds of the reported idle
  is GPU work the metric does not count; **the device is closer to ~88% busy.** The 13.5%
  serialized-tail figure was a single-lane number from run 13; run 18's tail cycle measured
  **265.8 s median, IQR 263.3–270.6** — saturated. *An efficiency target derived from a metric that
  under-counts its own numerator is a target for the metric, not for the machine — and this one was
  written into this handoff as "the next efficiency target".* Fix filed as **R18-E**.

- **CORRECTION 2026-08-30 — iqk is in EVERY build of this tree, production included.** This
  session reported it absent from the candidate build. That was wrong, and the reasoning that
  rested on it is void. **`GGML_IQK` is not a cmake option at all**: `GGML_USE_IQK_MULMAT` is set
  *unconditionally* for the CPU backend, and `GGML_IQK=1` is a **runtime env gate** read at
  `iqk_dispatch.cpp:49`. Verified: **23 iqk symbols in `libggml-cpu.so` in both arms.**

- **NEW FACT 2026-08-30 — our house recipe reproduces production's frozen build on BOTH backends.**
  Compared artifacts rather than flags: production's shipped `libggml-cpu.so` vs our fresh v9
  build — **584 defined symbols each, zero diff**; production's `libggml-hip.so` vs ours — **918
  distinct device kernels each, zero symbols unique to either side.** This is direct evidence
  against `build_recipe.py:43`'s `PRODUCTION_RECIPE_IS_VERIFIABLE = False`, which was set because
  production's *recipe* could not be recovered from disk (`build-hip/` has only `bin/`, no
  `CMakeCache.txt`). *Verifiability of a recipe and equivalence of its output are two different
  claims; we could not get the first and stopped, while the second was available the whole time
  and is the one that licenses using the recipe as a production stand-in.* Flip filed as **R18-A**.
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
  - **Scope note 2026-08-31:** the legacy `controller/` suites carry **~75 pre-existing failures
    outside the enforced CI floors** — do not repair them; the strip retires those suites with the
    code they test. Their existence is one more argument for P5, not a P5 prerequisite.
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
  - [ ] P7.4 — **THE LOC BUDGET IS NOW BINDING: 3400 of 3400, zero headroom** (was 3218/3400;
        `c39ecc43`'s promotion A/A guard consumed the rest). Verified by running the counter:
        `loop package: 3400 LOC across 15 files (budget 3400)`, `0 guard violation(s)` — **the
        next added line fails CI.** Constant at `check_regrowth_guards.py:50`, counter
        `loop_package_loc()` at `:70` (raw `splitlines()`; blanks, comments and docstrings all
        count), pinned by `test_check_regrowth_guards.py:98`.
        The two honest options stand — trim `run.py` (553 lines, the largest of the 15) or exclude
        comment/docstring lines — and **another round-number bump is not one of them**; raising the
        number is the failure mode the budget exists to catch. Record the choice here when it is
        made.
        **Correction while measuring this:** the constant's own doc comment at
        `check_regrowth_guards.py:41-42` claims *"2,102 lines are code and 1,071 are docstrings and
        comments — 34% of the package is prose."* Measured now: **2082 code / 810 prose / 508 blank
        = 23.8% prose.** The 34% figure does not reproduce and evidently folded blanks in. Fix the
        comment in the same change — a stale number in the annotation of the constant it justifies
        is how the "just bump it" argument gets made from bad data.

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

**STATUS 2026-08-30: all three are resolved. D1 approved (operator write outstanding), D2 declined
on measurement, D3 approved and shipped.** Detail in each entry.

- [x] **D1 — RATIFIED AND BUILT** ✅ 2026-08-31. The operator applied the amendment (root
      `4e42e8db`, heading flipped `c5ddc4fc`) and the capability was then actually built —
      research `198f5b4b` (see R18-G). Run 21 runs with ranking ON under it.
      *(original, retained)* **APPROVED BY THE OPERATOR 2026-08-30. The one outstanding action is the operator's
      own write:** run `scripts/operator/ratify_ak_search_1_a3_20260828.sh --apply`. Annex K is
      human-amendment-only (invariant 15), so no agent may apply it.
      **⚠ Correction to this handoff's own earlier claim: the capability does NOT ship.** This page
      previously said *"the store already ships with `ranking_authorized=False`; applying this is
      what lets that flag be turned on."* Half of that is false. The parameter exists —
      `ExperimentStore.recall(..., ranking_authorized: bool = False)` at
      `controller/experiments.py:157`, recorded onto the recalled row at `:193` — but **no
      production call site anywhere passes `True`**; the only caller that does is
      `test_experiments.py:150`, and the identifier does not appear in the `loop/` package source
      at all. So after ratification the **ranking capability still has to be built** (**R18-G**).

      *What was requested and approved (retained verbatim):* amend `P-AK-SEARCH-1` denial 4, which
      permits a later campaign to use a prior record *"for hypothesis formation only — never to
      **rank**, bank, compose, or contribute to readiness."* Choosing what to attempt next *is*
      ranking, so a planner that reads its own history to prioritise is non-conformant on a strict
      reading — very likely why the memory was never built and why one patch was proposed 38 times.
      **Option 4:** prior records may inform ranking, provided each carries the hash of its epoch
      (anchor commit, build recipe, host state) and cross-epoch records are validity-penalised at
      retrieval. No banking, no promotion authority, no readiness contribution — those denials stay
      verbatim. The mechanism is borrowed from autopilot's AP-28 store, not invented.
      `--show` reads it; `--apply` stages the amendment with an isolated `git apply --index`.
      P1.2(a) ships regardless — it is a bug fix, and denial 4 governs *cross-campaign* reuse only.
- [x] **D2 — DECLINED ON MEASUREMENT 2026-08-30.** ✅ 2026-08-30 — resolved to a decline, not
      deferred. **The deciding number is 0.0 s per iteration.** D2 proposed dropping four T0
      preconditions for screening; **none of the four is implemented in the rebuilt loop at all**,
      so the time they cost is zero and the saving D2 was justified by does not exist. What
      survives is a *conformance* question, not a throughput one — the loop produces records that
      no ratified tier authorizes — and that is a different request needing its own framing.
      Separately, **D2's precondition 4 (byte-for-byte anchor re-verification at both window edges)
      is unsatisfiable by construction** while the anchor advances mid-run, which it does by design
      (CH-3). Do not re-file D2 as written. Original request retained below for the conformance
      question's benefit.
      *(original)* **add a `T-screen` tier below T0**, requiring only: held claim, residency evidence, named
      anchor commit, codified recipe, and a once-per-host-state A/A noise floor. Drops, **for
      screening only**, the per-campaign calibration solve, byte-for-byte anchor re-verification at
      both window edges, evaluator runtime source-label attestation, and the storage-floor re-check.
      Every denial in *"what this protocol does NOT authorize"* stays verbatim.
      Context: P-GPU-1, the inherited rule, gates the **claim class, not the run**. The eight
      experiment-time preconditions come from P-AK-SEARCH-1, ratified 2026-08-03T08:30:05Z — six
      hours after this program's first commit (`75764052`, 02:15) and cited as a requirement by its
      third (`10843b6f`, 11:29, *"conforming to the ratified P-AK-SEARCH-1"*).
- [x] **D3 — build recipe as a champion arm. APPROVED AND SHIPPED** ✅ 2026-08-30 (research
      `6cbb608c` + `3ba4339f`). A champion now carries a build recipe. **Neither standing config
      win was adopted** — CH-6 settled both (`MMQ_MFMA` +0.50% on the 27B; `ubatch` a null arm,
      since llama.cpp clamps `n_ubatch = min(n_batch, n_ubatch)` so both screens ran one identical
      binary) — and both are **recorded in the recipe with the numbers that correct them**, so the
      carrier ships its own refutations rather than inviting a re-run. Decision-arithmetic floor
      raised 101 → 109. The recipe module is
      `scripts/kernel_rnd/autokernel/controller/build_recipe.py`; see **R18-A** for the one
      constant in it that the 2026-08-30 symbol-identity evidence now contradicts.

---

## R18 — what run 18 and the champion-vs-production A/B left behind (2026-08-30, second pass)

### Landed this pass

- [x] **R18-L1 — the promotion A/A guard, and the abort that was being swallowed.** ✅ 2026-08-30
      (research `c39ecc43`). After every promotion the new anchor is benched against a fresh
      champion build and must read **inside the noise floor**, else `RunAborted`
      (`loop/anchor.py:71`, assertion at `:98`).
      **The assertion is magnitude-vs-floor and deliberately NOT `Comparison.decisive`:**
      `decisive` returns `False` for a drifting arm *regardless of effect size*, so a
      `decisive`-based guard would have certified run 18's −9.539% regime as indistinguishable
      from zero. A guard whose predicate does not answer its stated subject is not a guard.
      **Abort propagation was genuinely broken** — `RunAborted` was caught by a blanket handler and
      filed as an ordinary `iteration_error`, so the guard would have aborted nothing; fixed at
      `loop/loop.py:357` (re-raise before the blanket `except Exception` at `:359`) and
      `loop/pipeline.py:249` (run-ending, not lane-ending: the anchor is shared, so the budget is
      zeroed and every lane stops at its next draw — continuous runs included).
      **Promotion now BUILDS** rather than `shutil.move`-ing: `pool.promote_anchor` builds the
      champion into the anchor slot and writes `provenance.json` (`loop/pool.py:372`).
      18 of 18 mutants caught, 1 control survived. Cost: the loop package hit **3400/3400 LOC**
      (P7.4).
- [x] **R18-L2 — the champion headline is one number against one named anchor.** ✅ 2026-08-30
      (root `bdeb450f` → `e1d22546`). Renders **NOT YET MEASURED** until the A/B exists rather than
      inheriting a number from somewhere else. 19 of 19 mutations caught.
- [x] **R18-L3 — epyc-root CI had failed 8 of 8 runs since creation.** ✅ 2026-08-30 (root
      `437f751f` → `54d2b8ad`). `actions/checkout` defaults to `fetch-depth: 1`; `index_state.py`
      derives `last_advanced` with a `git log -S'- [x]'` pickaxe, so against a one-commit clone
      **every handoff attributed to the tip** and the freshness check reported a stale generated
      block on a tree that was in sync. Both root workflows and the research one are now green.
      Same shape as P7.1 in a different repo: **a check fed an input it cannot answer from is not a
      failing check, it is an absent one.**

### Open

- [ ] **R18-A — flip `PRODUCTION_RECIPE_IS_VERIFIABLE` to `True`, with the symbol-identity evidence
      attached.** `controller/build_recipe.py:43`. It was set `False` because production's recipe
      cannot be read back from disk (`build-hip/` has only `bin/`, no `CMakeCache.txt`), and it is
      recorded, not gated — nothing refuses on it; it is emitted as
      `production_reference_is_verifiable` in `Recipe.to_dict()` (`:152`) and pinned by
      `test_build_recipe.py:66` plus the serialized key in `test_journal.py:249` and
      `test_schemas.py:464`, all of which move with it. The evidence: **584/584 defined symbols,
      zero diff, on `libggml-cpu.so`; 918/918 distinct device kernels, zero unique either side, on
      `libggml-hip.so`.** Attach the evidence to the flip — a `True` with no artifact behind it is
      the same defect in the other direction.
- [ ] **R18-B — run-18 forensics: what binary was actually in `anchor-gen-001`, and why were
      post-promotion effects −9.5%? OPEN — three hypotheses raised, three refuted.**
      (a) *candidates missing the champion patch* — **REFUTED**, every lane source tree is at
      `5ad3e36d`. (b) *CMake build-directory relocation at promotion* — plausible, **unconfirmed**.
      (c) *arms swapped* — **REFUTED**: benching the actual binaries gives `anchor-gen-001`
      **295.429** tok/s vs `lane0` **286.043**, a −3.2% gap, not −9.5%.
      Two cautions that must travel with this task: the anchor slot benched **~2.8% FASTER than a
      clean champion build** (295.429 vs 287.499), which is the wrong direction for every story
      told about this failure; and that is a **single unpaired r=5 bench** near the 5-pair floor
      (2.422%), so it is **not a finding**. What it establishes is only that *today's artifacts do
      not reproduce the failure* — which is why no fix was shipped.
      Start from the datum that is missing: `provenance.json`'s `"built_at"` key holds
      `str(promoted)` — a **path, not a timestamp** (`loop/pool.py:372`) — and build time
      (CMakeCache 06:01 vs libs 08:29 vs run start 09:37) is exactly what diagnosed run 18 by hand.
      Make `built_at` a real timestamp as part of this.
- [ ] **R18-C — record the champion branch's per-commit inflation where a reader of that branch
      will find it.** 36 commit messages claiming **+171.7% compounded / +101.8% summed** against a
      measured block effect of **+8.524%**. Commit messages are immutable, so the correction has to
      live where someone lands: a `NOTES-attribution.md` at the tip of
      `ak/loop-champion-20260828`, and the same statement in `loop/program.md`'s *Settled — do not
      re-open* section so both actors read it. Cross-referenced from INF-65 (CH-16).
      **Unblocked 2026-08-31**: run 19/20 are over, the branch is merged into `a2728701` and
      tagged (`ak/pre-reconcile-loop-20260831`), and `ak-loop-tree` is NOT on run 21's off-limits
      list. Coordinate with **R21-3** (the retirement decision) — if the operator retires the
      branch, the `NOTES-attribution.md` half lands at the tag instead; the `loop/program.md` half
      is doable now either way.
- [ ] **R18-D — recalibrate `bench.MEASURED_FLOOR_PCT["pp512"]`; until then no prefill verdict is
      backed.** `loop/bench.py:43`. The prefill row is still the superseded construction (p95
      |median effect| over subsets of ONE fixed 20-pair sample, which cannot exceed that sample's
      own tail), which is why the champion-vs-production pp512 row reported `decisive=True` on a
      +0.090% effect. The driver exists —
      `scripts/benchmark/autokernel_recalibrate_floor.py` has an `--apply` mode that rewrites the
      table. Needs a GPU window; **do not run it against run 19.**
- [ ] **R18-E — instrument the tail, and stop under-counting device busy-time.** Three parts, one
      change:
      1. Add a `time.monotonic()` pair around `gates.run_all` (`loop/gates.py:140`) and an
         `elapsed_s` field on `Verdict` (`:30` — it currently has `gate`, `passed`, `reason`,
         `detail` and **no timing field at all**). The **53 s op-oracle figure is an estimate from
         a single code comment** (`gates.py:23`, sitting next to a `CORRECTNESS_TIMEOUT_S = 1800`
         that does not corroborate it) and it is the largest term in the idle split — nothing
         verifies it at runtime.
      2. Publish `tail_seconds` on live runs.
      3. Count oracle, warmup and profile seconds as busy so `idle_fraction_while_claimed`
         (`loop/run.py:375`) stops over-reporting by ~2×. **Model the fix on the controller-side
         implementation that already does this correctly**: `controller/gpu_utilization.py`
         `from_sampling` derives busy from an actual sample trace (`:56-62`) rather than from
         elapsed wall time, and returns `None` on an absent trace rather than 0 (`:81` — a missing
         measurement is not evidence of an idle device).
      **Second defect found while locating this, fix it in the same change:** the loop's `busy`
      term sums `Comparison.device_seconds`, which `bench.py:262` computes as
      `time.monotonic() - started` for the *whole* `compare()` call — process spawn, model load,
      residency sampling and the CPU-side gaps between paired runs included. So within its own
      scope busy is *over*-stated even while the excluded oracle/warmup/profile time makes the
      total *under*-stated. `held` uses `time.time()` and `busy` uses `time.monotonic()`: two
      clocks in one ratio.
- [x] **R18-F — the loop code budget is freed, not bumped.** ✅ 2026-08-31 (research `33715a7e` →
      `f2c05dc1` → `95eeb0ae`). The guards now bound **code** and compute the prose share instead
      of remembering it wrong (`check_regrowth_guards.py`: `LOOP_CODE_BUDGET = 2100` enforced;
      `LOOP_LOC_BUDGET = 3450` still printed for the split). The trim took code 2099 → **2040/2100**
      by deletion, not by budget motion: the pool now owns the consecutive-error breaker — **the
      pooled path previously had NONE and would spin forever** — the sequential path is deleted
      (`loop.run` kept as a documented test-only seam), `SINGLE_PAIR_P95` deduped, dead code
      removed. 13/13 mutants; decision-arithmetic floors argued 304→309.
- [x] **R18-G — the ranking capability D1 authorizes is BUILT.** ✅ 2026-08-31 (research
      `198f5b4b`, epoch-scoped, default off; companion `068ffb67` emits the champion-vs-production
      headline at every advance). Run 21 runs it ON. Building it surfaced a **real conformance
      breach**: `actors.py` pooled **cross-epoch** magnitudes into a do-not-re-measure median —
      biting at every epoch transition; fixed by checking **both** provenance markers. The earlier
      claim that the store "already ships" the flag was FALSE and stands corrected (parameter
      existed inert; capability did not).

---

## R21 — the reconciliation (2026-08-31): INC-20260831, the merge, the measurement, run 21

Full session record: `progress/2026-08/2026-08-31-ak-rebuild-20260828.md`.

### Landed this pass

- [x] **R21-L1 — single-champion invariant ratified and ENFORCED.** ✅ 2026-08-31. Ratification
      root `35c1a6d1` (operator-applied; the stale-worktree recovery en route — the shared clone's
      `OPERATING_CONSTRAINTS.md` was missing 28 lines of ratified 08-27 content, caught by
      `git apply --index` refusing). Enforcement research `470378a9`: startup refusal proven live
      both directions, attachment-stronger-than-tip-equality, pool champion ref aliased to the
      canonical branch, 34/34 mutants; plus the live-resolved frozen-production baseline in
      `production.py` (per-commit build cache).
- [x] **R21-L2 — the reconciliation merge and its measurement.** ✅ 2026-08-31. `a2728701` =
      `270b48ed` + `4925b208`, zero conflicts, disjoint file sets, parents tagged
      `ak/pre-reconcile-{manual,loop}-20260831`. **+12.618% tg128 vs production resolved live**
      (264.53→297.91, 20 pairs, 10.6× the 1.188% floor; pp512 +0.078%, uncalibrated floor —
      R18-D), oracle 3/3, inside the pre-committed chain-estimate band [11.2–15.3] → additive, no
      interaction. Bundle published; `generated_at` was stamped 5.5 min in the future by the
      publishing agent, the reader refused it, restamped from raw-file mtime with a correction
      note. Capability list now **artifact-derived** incl. DFlash2 symbols (`build_dflash2_conv`,
      libllama 10125→10180); corrected finding: **iqk shipped in v9 already** — the champion adds
      dispatch gating only.
- [x] **R21-L3 — run-20 drain flaw fixed (drain tiers).** ✅ 2026-08-31 (research `95eeb0ae`).
      STOP abandons at actor boundaries recording `stopped_mid_formation`, never mid-tail. (The
      trim itself is under R18-F.)
- [x] **R21-L4 — dashboard: the anchor is resolved, staleness is semantic, the champion is the
      branch tip.** ✅ 2026-08-31 (root `479ffb47`, `2a3881d4`, `86bc7b8b`, `f9c00551`).
      Live-resolved frozen production + `SUPERSEDED-BASELINE` state, source-guard banning 40-hex
      literals (19/19 mutants); a measurement of a superseded champion is not "fresh"; **the
      champion branch tip defines "current champion"** — run 20's dead status file had the panel
      calling the fresh merged measurement superseded by its own parent; five operator notes incl.
      computed scope-line ancestry (`270b48ed` reads "ancestor — its work is IN the current
      champion") and the accumulated-knowledge card reading `experiments.db` read-only (1051
      attempts / 326 mechanisms / 79 revisited / 18 kept / 402 measured-null / 132
      refused-at-formation) with a per-card staleness audit table (12/12 mutants).
- [x] **R21-L5 — CI identity fix.** ✅ 2026-08-31 (research `af43cfb0`). Champion-keep tests drove
      a real `git commit`: green locally via host gitconfig, red on the runner ("Author identity
      unknown", run 33384448851). Fixed with fixture-local identity, proven under
      `GIT_CONFIG_GLOBAL=/dev/null`.
- [x] **R21-L6 — run 21: the loop advanced the champion TWICE, unattended, end-to-end.**
      ✅ 2026-08-31. Each advance ran keep → anchor rebuild → A/A guard → self-measured headline →
      publish with no human step. (1) `akm-rmsnorm-1536-float4-384` +1.359% — **first rms_norm
      keep in program history** (hotspot 7.3%, 34 prior mechanisms, 0 kept); guard −0.263%;
      headline `cb617372` +15.326%. (2) `akm-q6k-paired-scale-pk-fma` +1.811%; guard +0.327%;
      headline `aba5a815` **+16.180% vs frozen production** (resolved live). Trajectory today
      +12.618 → +16.180, all direct measurements. First keeps under ranked memory: 2 keeps /
      26 iterations after 68 dry.
- [x] **R21-L7 — the two operator-gated-card fixes.** ✅ 2026-08-31 (root `9425eaef`,
      `5f2151c9`). Hypothesis-ledger card walks the hotspot-first agenda from the real store
      (`mul_mat_vec_q` 49.3%/63 tried; `k_set_rows` never targeted; `flash_attn` 12.3%
      0-kept-over-29 visible), card compacted to one summary line + accordion (17/17 mutants);
      staleness for episodic evidence is SUBJECT-anchored (relevant/superseded/unverifiable,
      movement outranks, clock advisory; 4/4 mutants both directions).
- [x] **R21-L8 — run-22 prep landed.** ✅ 2026-08-31 (research `a95581c8`, pushed). `dec-b2/4/8`
      surfaces (llama-bench source PROVEN: tg can never express `ne11>1`; the prompt path with
      `-b/-ub N` can); 3-layer uncalibrated-floor discipline (`decisive=None`; commit-path
      re-derivation); `--calibrate-surface` reusing the D8 method (byte-for-byte reproduces the
      tg128 k=5 floor); flag admission branch + greedy-parity harness (verdict encodes the
      operator's conditional). Budget consequence filed as R21-7.
- [x] **R21-L9 — serving-evidence refresh package.** ✅ 2026-08-31 (research `8179dde0`, pushed;
      CH-14 pointer root `a5e23465` — coordinate via INF-65). Original +48.9% bundle traced, all
      four steps scripted (CH-4 validation → 24-cell concurrency grid → greedy parity → sealing
      emitter); "production ceiling" = MTP arm on the champion binary because v9 cannot load the
      DFlash2 GGUF (now documented); one-command `serving_evidence_refresh.py`, claim-held
      (refuses while run 21 lives); next bundle carries `generated_at` + `champion.commit`.

### Open

- [ ] **R21-5 — Standing community-intake → hypothesis-inbox pipeline.** Operator 2026-08-31:
      "I imagine we could distill a lot of autokernel-valuable insights from the wider internet
      community." The qwen38-mtp sweep is the pilot; make it a repeatable flow. Three source
      tiers by evidence quality: (1) **upstream llama.cpp commits/PRs since the 0db32c06 freeze**
      — each CUDA/HIP kernel improvement is a pre-validated hypothesis with its own PR-thread
      numbers, attempted by the loop as a gfx90a port rather than merged blind; (2) community
      forks/writeups; (3) papers via the existing research-intake stages. Contract per sweep:
      normalize claims to bandwidth utilization, map to the live hotspot profile, check
      experiments.db for known nulls, emit inbox-format seeds with provenance URLs, operator
      reviews before injection (run starts and inbox writes stay operator-gated). Zero compute
      until the loop itself elects a seed. **Piloted 2026-08-31 — the pipeline stays open as
      STANDING; the pilot sub-items below are done:**
  - [x] Pilot sweep (a) — qwen38-mtp ✅ 2026-08-31. BW-utilization arithmetic: MI210 production
        49.4% vs CUDA band 54–78%, 7900 XTX HIP 52.4% → the deficit is a **ggml-HIP-backend
        property**, not CDNA2 hardware. 3 seeds: multi-column MMVQ (untouched surface),
        quantized-KV FA (revisit-with-justification), Q8_0 GEMV roofline.
  - [x] Pilot sweep (b) — upstream llama.cpp v0.2.0 delta since the 0db32c06 freeze
        ✅ 2026-08-31. ~260 commits, 19 CUDA; 6 seeds incl. MMVQ nwarps, MMQ decode crossover
        (no CDNA rows), and the **`-funsafe-math-optimizations` finding** — upstream removed it
        for flipping greedy argmax; our v9+champion still compile with it (verified, line 134).
        Operator ruled: "2% hit worth it IF quality demonstrated" — demonstration is a boundary
        step (R21-6), never merge-by-default.
  - [x] All 13 seeds from the two sweeps injected into the live hypothesis inbox
        (operator-authorized) ✅ 2026-08-31. The loop elects on its own schedule.
  - [ ] Decide the upstream-rebase cadence for the experimental branch (filed 2026-08-31): the
        tree is ~260 commits behind upstream since the freeze; today's posture is
        port-as-hypothesis only (each upstream kernel change enters as an inbox seed, never a
        blind rebase). Either ratify that posture as the standing answer or set a periodic
        delta-sweep cadence (e.g. per upstream release, reusing sweep (b)'s method).
- [x] **OP-34 RESOLVED 2026-08-31** (minted as OP-32; renumbered 2026-09-01 — the queue reconciliation reassigned OP-32 to the uniform-IQ4_XS decision and this lane's third minted ID was missed) — operator: "pre-authorize run 22 if all boundary steps are green." The boundary driver launches run 22 iff the exact all-green conjunction holds (run 21 dead · flag A/B clean exit either verdict · all three dec-b* calibrations written · serving bundle sealed · final-champion --dry-run verified); any single non-green holds for morning. ✅ 2026-08-31
- [ ] **R21-6 — BOUNDARY tonight, 2026-08-31 22:00Z (operator-ordered).** Driver
      `scripts/benchmark/boundary_20260831.sh` (research lane; being written + stub-tested by the
      active research-lane agent). Sequence: stop run 21 (STOP+SIGTERM, +25 min group-SIGKILL) →
      `-funsafe-math` flag parity/speed A/B (merge ONLY on demonstrated divergence per the
      operator's conditional; tagged; oracle-gated) → `dec-b*` calibrations → full serving
      refresh (`serving_evidence_refresh.py`) → run-22 readiness report. ~5–7.5 h device.
      **Run 22 is NEVER auto-started** — operator gate, property mutation-tested. Open operator
      question (in the queue): pre-authorize run-22 on all-green, or hold for morning go.
- [x] **R21-10 RESOLVED 2026-09-01 — the +1.765% was the INSTRUMENT, not the build.** Read-only
      investigation (report in `artifacts/r2110-anchor-guard-abort/`, research lane): ccache is
      NOT INSTALLED on this host (`GGML_CCACHE_FOUND-NOTFOUND` — the "~80s ccache-warm builds"
      belief was false); a controlled double-build of `14ba0262` is bit-identical in every code
      section (1 byte of RUNPATH `.dynstr` differs); the loop's own gen-010/fresh pair differs
      only in relocation-table offsets. Builds are DETERMINISTIC, funsafe included. The abort was
      a 4.2σ measurement excursion (pooled A/A sd 0.417%, n=11) — and it sits 0.006pp from the
      keep that preceded it (+1.759%), back-to-back in one session: either the keep is real and
      the guard fluked, or ONE ~12-min instrument excursion manufactured BOTH. The 4th keep's
      authenticity is decided by the staged device experiment (below). Headline integrity is
      unaffected either way — champion-vs-production is measured direct, so a dead patch in the
      lineage costs hygiene, not truth. ✅ 2026-09-01
- [ ] **R22-6 — Harden `read_inbox` (3-line fix, coordinate with R22-3's lane work).**
      `run.py`'s `read_inbox` does a bare `read_text(encoding="utf-8")` per file, per
      iteration, with no error handling: one invalid-UTF-8 or unreadable file in the live
      inbox raises inside `build_context()` on EVERY iteration — all lanes error, the
      consecutive-error breaker fires, the run dies. The operator's injection channel is
      also a kill switch. Fix: per-file try/except → skip with a logged
      `inbox_file_unreadable` note, never raise. Verified 2026-09-01: all 17 current seeds
      read cleanly (42,783 chars, well within prompt budget), so this is preventive, not
      urgent.
- [ ] **R23-2 — Demote/annotate the two benign-but-alarming DFlash2 load warnings.** "failed
      to measure draft model memory" and "legacy draft hidden size 5120" print identically in
      healthy 70 t/s runs and in a genuinely broken load — a peer session escalated a false
      champion-regression on exactly that signature (2026-09-01, retracted). Make the log
      distinguish "benign legacy path, sizes verified matching" from a fault, at the source in
      the champion lineage. Small; pairs naturally with R23-1's admission window.
- [x] **R23-5 — H1 transfer falsifier EXECUTED (H1-first, operator-approved) ✅ 2026-09-01.**
      **H1 CONFIRMED in substance: the +17.9% headline is ne11=1-concentrated and collapses on
      production serving shapes.** Champion `9e18beb0` vs frozen v9, 20 pairs/surface, all four
      effects decisive on bootstrap-calibrated floors: **+17.259%** (tg128, ne11=1) → **+3.834%**
      (dec-b2, floor 0.866%) → **+1.178%** (dec-b4, floor 0.668%) → **−1.462% a decisive
      REGRESSION** (dec-b8, floor 0.656%). Dispatch sanity proven by rocprofv3 (MMVQ ncols=1 →
      ncols=2 → MMQ across the curve — the instrument isolates ne11, not vacuous). Formally the
      partial-decay bracket, so the curve went to the operator; ruling: run 23 hunts **dec-b4**;
      the b8 repair is seed 18. Full record `/mnt/raid0/llm/tmp/r23-5-results/` (VERDICT.md,
      per-surface drain points, binary digests). Original task text kept below for provenance:
      One measured data point says ~1/28th of the tg128 headline transferred to the DFlash c1
      serving cell (70.0 → 70.4 across the merge that added all loop kernels). Two candidate
      causes, both structural: (a) ne11=1 vs the verify-batch shapes production actually runs
      (llama-bench tg cannot express ne11>1 — proven from source); (b) model-shape
      specialization — many keeps are `fixed-1536` (the 1.5B instrument model's n_embd);
      production's 27B is n_embd=5120, so those kernels never fire in serving. Falsifier:
      champion vs frozen production at ne11 ∈ {1,2,4,8} via the CALIBRATED dec-b* surfaces
      (~30-40 min). Collapse at ne11≥2 → dec-b* becomes the gate and the workload question
      (production-shaped rung, 5120-class/Q8_0 — the original P2 intent) reopens; hold across
      ne11 → H1 dies, the 1536-specialization half remains. H2 rider: after the falsifier, one
      run with ne11∈{2,4,8} in the seed surface — a disjoint winner set proves the search was
      half-blind. Provenance: peer msg 2fa07724 + our own commit titles.
- [ ] **R23-6 — H6 prompt-class ranking stability** (cheap, piggybacks R23-3's instrument work):
      score one candidate pair on code-heavy vs prose-heavy prompt sets; stable ranking →
      stratification unnecessary, only the span (2.4x measured) needs reporting. H5 (calibratable
      ~13% instrument gap) folds into R23-3: measure 3-4 arms on both instruments; wide ratio
      variance → cross-instrument claims stay banned rather than corrected.
- [ ] **R23-4 — One-factor sweep: config vs draft acceptance and run-over-run stability**
      (from the peer's 2026-09-01 seam; feeds INF-22 P3-4 and INF-62). Two findings need
      attribution: (a) P3 decays monotonically across repeated requests at the verbatim c1
      config `[67.3, 52.6, 46.7]` while the 32K config is tight `[57.6, 61.1, 62.9]`; (b)
      acceptance moved 0.537 → 0.371 on identical prompts/model/drafter across configs. The
      peer's arm deliberately bundled THREE differences (context 32768 vs 4096, kv-unified vs
      --no-kv-unified, taskset) — attribution requires one factor at a time. If config moves
      acceptance that much, the serving recipe may leave ~15% on the table. Instrument note
      recorded: server-side 70.4 vs client-side 61.1 ≈ 13% expected gap; prompt-dependence spans
      2.4x within one arm, so single-prompt headlines are banned from this comparison. Also:
      32K-beats-4K REFUTED the VRAM-pressure prediction.
- [ ] **R23-3 — probe.py client-side instrument for the MTP-vs-DFlash2 serving A/B** (feeds
      INF-22 P3-4): peer session workspace-62 has offered to run the correct `--spec-type
      dflash2` arm under the qwen38-mtp repo's client-streaming instrument in a seam we name.
      Two independent instruments on the same arms; standing numbers to beat: DFlash2 70.4 t/s
      c1 (server-side), native MTP 46.8 median n-max 8 (probe.py). Schedule at a future boundary.
- [ ] **R23-1 — Admit the llama-cli EOF fix at the run-23→24 boundary (manual path).** Peer
      patch (epyc-root `b9607cd3`, operator-approved): `ui::read_input` discards EOF so
      `llama-cli` re-prompts forever on closed stdin — the root cause of the 2026-09-01
      funsafe-harness hang (worked around with `-st`) and of a peer's 322 GB/11 h runaway that
      held a region claim overnight. Present in frozen v9 (untouched, per doctrine). Host-tool
      correctness fix → CH-7 manual admission, not a loop keep. Keep the harness's `-st` +
      slice-extraction as belt regardless. **Operator decision attached: file the fix upstream?**
      v9-era llama.cpp carries the same defect for anyone running llama-cli non-interactively.
- [ ] **R22-5 — Boundary-length correctness matrix in the oracle (screen upgrade, from the
      M4-prefill intake relay, H5).** Validate kernels at M ∈ {33, 127, 128, 129, 512, 1023,
      1024, 2047, 2048} — off-by-one probes around tile boundaries — in `gates.op_correctness`.
      Rationale from our own record: nearly every INF-67 fused-decoder defect (span overflow,
      conv-window layout, copy-back overrun, scratch overflows) was a boundary condition; the
      dominant defect class that kernel-isolated perf tests miss. Cheap; loop-budget cost is
      near zero if the case list lives in controller/. Source: intake-1295#record.
- [ ] **R22-3 — Guard robustness, post-trim (spec from R21-10, budget-gated on R21-7):**
      (1) persist the guard's full `Comparison` in the AnchorVerdict archive row — the abort's
      samples/drift/clocks died with the process; (2) **hash pre-check as the primary fix**:
      compare code-section hashes (`.text`+`.hip_fatbin`, ignore `.dynstr`/`.rela*`) before
      measuring — identical code + above-floor A/A indicts the SESSION (log `anchor_guard_excursion`,
      continue), differing code is deterministic run-18 proof (abort, no pairs wasted); (3) heal
      once: one rebuild+re-verify before aborting. Verify-and-adopt evaluated and REJECTED
      (adopted arm would itself be unverified; determinism makes it moot).
- [ ] **R22-4 — Next-boundary device experiment (builds staged at `/mnt/raid0/llm/tmp/r2110-build-{a,b,parent}`):**
      A/A a-vs-b (identical binaries, distinct paths) → instrument sanity; A/B parent-vs-a twice,
      order-swapped → ≈+1.76% both = the 4th keep stands; ≈0 = the keep was manufactured by the
      excursion and gets a hygiene revert. ~25 min device time.
- [ ] **R21-7 — the loop code budget is BINDING AGAIN: 2100/2100, zero headroom** (run-22 prep
      consumed the `95eeb0ae` trim's headroom; filed 2026-08-31). Next trim candidate: delete the
      `loop.run` test-only seam (kept as a documented seam by `95eeb0ae`; its tests move to the
      pooled path). Same rule as R18-F: the budget is freed by deletion, never bumped.
- [ ] **R21-8 — `MEASURED_FLOOR_PCT` is keyed by SURFACE ONLY; the model identity behind the
      calibration is unenforced** (filed 2026-08-31). A floor calibrated on one workload silently
      gates a run on another — same defect class as R18-D's stale pp512 floor. Add the model (or
      workload identity) to the floor key, or refuse a mismatch at gate time.
- [ ] **R22-1 — run-22 primary surface: default STAYS tg128** (filed 2026-08-31, resolves at the
      run-22 go). `dec-b2/4/8` enter as secondary, individually calibrated surfaces (R21-L8);
      promotion of any of them to primary is an operator call made on the boundary's readiness
      report — the report must carry the per-surface floors so the choice is decidable there.
- [ ] **R22-2 — evaluate `llama-batched-bench` as the parallel-sequence surface** (filed
      2026-08-31). llama-bench is source-proven unable to express `ne11>1` on the tg path
      (R21-L8); `llama-batched-bench` expresses parallel decode natively and is closer to the
      serving shape. Needs its own floor calibration (`--calibrate-surface` method) before any
      verdict may cite it; zero compute until then.
- [ ] **R21-1 — refresh the champion headline at STARTUP, not only per-advance.** A restart after
      an unmeasured advance briefly shows `SUPERSEDED-BASELINE` until the first advance re-emits.
      Small: emit the headline once during loop startup from the same path `068ffb67` added.
- [x] **R21-2 — promote the reconciliation A/B evidence out of volatile tmp.** ✅ 2026-09-01 —
      landed as research `2ee10ff5` (`artifacts/autokernel-champ-a2728701-ab/`, 24 files ≈1.4 MB:
      result JSON, `run_ab.py`, `run_ab.log`, 3 oracle logs, symdiff; regenerable dumps excluded),
      verified on `origin/main`. Queue row OP-31 deleted at the 2026-09-01 wrap-up — it had gone
      stale after the commit landed without the flip (recurrence-check catch).
- [ ] **R21-2b — re-point the published bundle's evidence paths at the repo copy** at the next
      boundary the bundle is rewritten anyway (never touch the live bundle mid-run).
- [x] **R21-3 — RETIRED ✅ 2026-09-02 (operator executed).** `ak-loop-tree`, `-b`, `-c` worktrees
      removed and branches `ak/loop-champion-20260828{,b,c}` deleted (`-D`); ~495 MB reclaimed.
      Safety RE-VERIFIED same day rather than trusting the 2026-08-31 record: `4925b2084` is an
      ancestor of the **current** champion tip `732389d6d` (not just the older `a2728701`) with
      **zero** commits unique to the branch, tag `ak/pre-reconcile-loop-20260831` still resolves
      and the object is intact, all three trees idle on two samples 48 s apart, and nothing live
      depends on them (driver + run 24 pass `--worktree champ2` explicitly). Post-deletion checks:
      0 worktrees, 0 branches, tag resolves, `4925b2084` still ancestor of the live champion,
      `champ2` untouched on the canonical champion branch. **The review changed the command**:
      `ak-loop-tree-c` held 82 uncommitted lines present in NO commit on any ref, so plain
      `worktree remove` would have refused and a reflex `--force` would have destroyed them —
      rescued first (R21-5), and only then was `--force` scoped to that one tree.
- [ ] **R21-4 — the non-hermetic dashboard tests (4 red loop-down).** They assert on LIVE loop
      state and were red between runs 20 and 21; with run 21 up, the six live-reading files pass
      (157 tests, verified 2026-08-31). The exact red set was never persisted and cannot be
      recovered without taking the loop down; the live readers are in
      `test_dashboard_operator_gates.py` (real gate bundle), `test_dashboard_controller_state_contract.py`
      (live `state.json`), `test_dashboard_knowledge_card.py` (real `experiments.db`),
      `test_dashboard_champion_headline.py` (real bundle + production resolution). Standing debt
      already noted in `.github/workflows/tests.yml` ("Report what was NOT run") and P6. Fix is
      recorded producer fixtures, not skips — fold into the P6 rewrite.

### Declined 2026-08-31 — deliberate

- **STOP refusing tail ENTRY for post-stop completed formations (~2 lines + test). NOT BUILT.**
  The operator is aware and did not request it; drain tiers already stop everything upstream of
  the tail, and a formation that completed before STOP finishing its one paired measurement is
  bounded (~one tail cycle). Re-raise only if a future stop shows the tail entry mattering.
- **`test_production.py`'s dated mutation-note narrates the old breaker path for 3 mutants
  (M19/M20/M40 "reach `loop.run`, which turns three consecutive faults into `RunAborted`" — the
  breaker is the pool's since `95eeb0ae`).** Kept as a dated record per the operator; a one-line
  parenthetical was added pointing at the pool so a reader tracing those mutants today is not sent
  to a breaker that no longer exists there.
- **Legacy `controller/` suites carry ~75 pre-existing failures outside the enforced floors.**
  Not filed as its own task: it predates this pass and is **P5-strip territory** — noted in P5's
  scope so the strip retires the suites with the code they test rather than repairing them first.

---

## R23 — H1 verdict, run 23 launch, production-shaped rung (2026-09-01)

**Run 23 is LIVE (pid `2214942`, started 10:21Z), operator-approved** ("proceed" on H1-first, then
the dec-b4 go): `--surface dec-b4 --pairs 20 --workers 7 --rank-prior-experiments`, anchor = the
attested clean build `/mnt/raid0/llm/tmp/build-champ-tip-clean`, champion worktree `champ2` @
`9e18beb0`, floor 0.668%, startup refusal verified (anchor == champion tip), monitor armed. This
is the first run pointed at a surface production actually occupies — R23-5's curve (see the
flipped box above) showed the tg128 headline collapsing to +1.2% at ne11=4 and inverting to a
decisive −1.462% at ne11=8. First dec-b4 profile: **Tensile GEMM (`Cijk_…HSS…`) is the top
hotspot** — a different target than the MMVQ templates every prior run chased. **Seed 18 injected**
(operator channel): `loop-memory/inbox/18-b8-regression-repair.md` (repair the dec-b8
regression); inbox now 18 seeds. Do not touch pid `2214942`, `champ2`, `build-champ-tip-clean`,
or `loop-memory/`.

**The production-shaped rung decision package is drafted** (research `b15c480b`,
`docs/design/autokernel-production-shaped-rung.md`, subagent, zero compute) — recommendation:
two-rung screen/confirm (1.5B keeps screening; keeps gated + headline confirmed on the 27B
production model at pairs=5, ~18% cadence overhead). Six operator decision items D1–D6 in §6.

### Open (R23 follow-ups)

- [ ] **R23-7 — fix stale `PRODUCTION_QUANT_FAMILY` (`workload_contract.py:58` refuses
      production's own Q8_0 model).** Verified: `Q8_0` is absent from the frozenset, so
      `verify_workload()` refuses production's own Qwen3.8-27B-Q8_0 while passing the mismatched
      1.5B instrument. Land at the run-23 boundary, never mid-run. (Rung design §5.1.)
      *Folded into R23-11 (2026-09-01 D1–D6 ruling); flips with it.*
- [ ] **R23-8 — floor keying (surface, workload-class) per rung design §5.1/R21-8.**
      `bench.floor_rows()` keys by surface only; calibration artifacts record `"model"` but
      nothing reads it — confirmed structurally. Key by (surface, workload-class); mismatch →
      uncalibrated/refuse. Land at the run-23 boundary, never mid-run.
      *Folded into R23-11 (2026-09-01 D1–D6 ruling); flips with it.*
- [ ] **R23-9 — DFlash2 standalone llama-bench smoke (2 min GPU) + 27B confirm-surface A/A
      calibration window (~5–6 h) — OPERATOR-GATED, next boundary.** Frozen v9 carries the dflash
      arch (verified in `0db32c06e`), so the 2 GB rung is loadable by both arms; the smoke decides
      D5, the A/A window is D6's only real device cost.
      **D6 SCHEDULED 2026-09-01: operator — "let run 23 hunt until 22:00Z, full boundary then."**
      Boundary sequence: stop run 23 (graceful drain, captured PID 2214942) → merge R23-11
      (review-token gated) → apply re-anchored seeds (R23-12, staged copies) → rocprof dispatch
      sanity (R23-13) → DFlash2 smoke → 27B A/A on dec-b4+dec-b8 (keyed calibration artifacts) →
      readiness package.
- [x] **R23-14 — boundary driver drafted, reviewed, armed** ✅ 2026-09-01 —
      `boundary_20260901.sh` + helper (research side branch `8634f0c7`), modeled on the 20260831
      trio (state-file resume, fail-closed refusals, PID-verified stop). **Review fix
      `6f405233`**: run 24 launches from the latest guard-verified anchor-gen — the drafted
      incremental-tip-rebuild + `--allow-unverified-anchor` path was the 2026-08-31
      attestation-failure pattern and was removed. Driver LIVE: pid 2715782 (waiting for
      22:00Z), `REVIEW_TOKEN_R23_11` + `PREAUTH_RUN24` placed per OP-35.
- [x] **OP-35 RESOLVED 2026-09-01 — operator: run 24 PRE-AUTHORIZED on the all-green
      conjunction** ("yes, you're pre-authed"): run 23 drained clean · R23-11 merge landed +
      full hardware-free suite green · re-anchored seeds applied · dispatch-sanity recorded ·
      27B A/A calibrations written and sane. The owning session places
      `/mnt/raid0/llm/tmp/boundary-20260901/PREAUTH_RUN24` in the evening ONLY after reviewing
      the R23-11 commits (separate `REVIEW_TOKEN_R23_11`) and the driver's `--dry-run`; the
      driver launches run 24 (~04:00–05:00Z) iff token AND all-green — any single non-green
      holds everything for morning review. Mirrors OP-34/run-22. ✅ 2026-09-01
- [x] **R23-10 — production-shaped rung decision package drafted**
      (`docs/design/autokernel-production-shaped-rung.md`, research `b15c480b`) ✅ 2026-09-01 —
      **RULED 2026-09-01: operator approved the two-rung screen/confirm recommendation** — D1(iii)
      two-rung · D2 confirm gate on dec-b4+dec-b8, tg128 kept for headline context · D3 pairs=5
      gate / 20 headline · D4 headline MOVES to the 27B rung · D5 screen swap deferred to the
      §5.6 smokes (DFlash2 first if it passes) · D6 window scheduling stays the operator's call.
- [x] **R23-11 — implement the approved rung design in loop code** ✅ 2026-09-02 (§5.1 census-based
      quant-family + rung-parity check · §5.2 (surface, workload-class) floor keying — subsumes
      R23-7/R23-8 · §5.3 KEEP_CANDIDATE screen→confirm gate, headline-on-rung, rung on every
      record). Built on side branch `ak/rung-fixes-20260901` (never the lane mid-run); merged at
      the boundary — lane at `765fc6bb` (research), gate suite green 06:51Z (see R23-15 for the
      two refusals on the way there).
- [x] **R23-12 — re-anchor inbox seeds to the rung they will be measured on (§5.4)** ✅ 2026-09-02 —
      9 seed files applied by the driver at 06:51Z (manifest
      `/mnt/raid0/llm/tmp/boundary-20260901/step3-seeds-manifest.txt`); loop was verified dead
      first, live inbox never edited mid-run.
- [x] **R23-13 — rung identity artifact (§5.6 step 2)** ✅ 2026-09-02 — production dispatch tables
      recorded per confirm surface on the 27B:
      `/mnt/raid0/llm/tmp/boundary-20260901/rung-identity/dec-b{4,8}.Qwen3.8-27B-Q8_0.json`.
- [x] **R23-15 — boundary step2 gate defect found + repaired (operator-approved)** ✅ 2026-09-02 —
      the drafted gate demanded ABSOLUTE green on `pytest loop/ controller/`, but controller/
      carries 74–76 pre-existing legacy-red tests (StaticBuildCache sealed-key fixtures, Arena
      adapters, V8Deterministic setup errors) — the gate could never pass and was armed without a
      dry-run of its exact command. Refusal #1 22:17Z (fail-closed, lane rolled back — GPU idle
      overnight). A/B in fresh worktrees proved the failing sets at `74b936b5` and `9c40429d`
      byte-identical (merge introduces 0, adds 35 passing). Fix 1 `ecb6288a`: pytest becomes a
      DELTA gate vs the pre-merge tag. Refusal #2 06:45Z: one legacy test audits the
      *checkout's own git-cleanliness* (passes in a fresh worktree, fails in any working lane at
      the same commit) — fresh-baseline-vs-live-lane compared environments, not commits. Fix 2
      `9fa7a6fa`: environment parity, both sides in fresh detached worktrees. Gate green 06:51Z:
      74 = 74, 0 introduced. Floors + regrowth guards stayed absolute and green throughout.
      OP-35's "full suite green" conjunct is read as this delta-green per operator "proceed"
      (2026-09-02 morning). NOT filing a fix-the-legacy-red task: Phase 5 strip deletes those
      suites; fixing them first is work the teardown plan already declines.
- [x] **R23-16 — DFlash2 smoke result (D5 settled for run 24)** ✅ 2026-09-02 — smoke FAILED
      rc=1, non-gating as designed: `llama-bench` cannot load
      `Qwen3.8-27B-DFlash2-Q8_0.gguf` standalone (2.06 GB drafter HEAD, present and readable —
      it is a companion artifact, not a self-contained model). Run 24 screens on the 1.5B rung.
- [x] **R23-17 — DFlash2 capability verification on the post-keep champion: PASS** ✅ 2026-09-02 (OWNED here —
      operator reassignment 2026-09-02: "I want you to own this"; "We can't afford having any
      issues with the DFlash2 performance boost. It is central to this champion's feature set").**
      Exposure: run 23's keeps were validated ONLY on the 1.5B dec-b4 surface; `db18f393` edits
      `fattn-wmma-f16.cu` (on the 27B batched draft-verify path) and `732389d6` rewrites 119
      lines of `mmvq.cu` — the DFlash2 path has never been exercised post-keep. Built
      `scripts/benchmark/dflash2_capability_smoke.sh` (research lane `b412f37d`): replays the
      DF2-5 server recipe verbatim on a given build, gates on acceptance ≥0.58 (bar 0.6205) and
      speculation boost ≥1.5× none-control (bar 2.6×); step5's standalone `llama-bench` on the
      drafter head could never work (companion artifact, not a model — R23-16). **Run-24 launch
      HELD**: `PREAUTH_RUN24` → `.held-for-dflash2-verify` + `HOLD_REASON.txt`; at step6
      completion (~13:00Z) run the smoke on anchor-gen-014 with the GPU seam quiet, then PASS →
      re-place PREAUTH + resume driver; FAIL → no launch, bisect which keep broke the path
      (candidates in commit order), report with rollback options.
      **RESULT 2026-09-02 ~12:00Z on anchor-gen-014 (champion `732389d6`): PASS.** acceptance
      **0.6501** (bar 0.58; DF2-5 reference 0.6205); DFlash2 **72.65 t/s** vs non-speculative
      **30.51 t/s** = boost **2.38x** (bar 1.5x). Verdict at
      `/mnt/raid0/llm/tmp/boundary-20260901/dflash2-smoke/verdict.json`.
      **Reading**: the three keeps did NOT damage the DFlash2 path — speculative throughput is up
      on DF2-5's 70.0 t/s and acceptance is slightly up. The boost RATIO fell (2.6x -> 2.38x) only
      because the non-speculative arm improved MORE (26.6 -> 30.51 t/s, +14.7%): the kernel keeps
      helped plain decode more than the speculative path, compressing the ratio while making BOTH
      arms faster. A falling ratio here is not a regression.
      **Caveat**: DF2-5 came from a different binary and harness; the load-bearing comparison is
      the same-binary internal control (none vs dflash), which is sound. Run-24 gate SATISFIED.
      **Instrument defect fixed mid-flight**: the build-capability check used
      `llama-server --help | grep -q`, and under `set -o pipefail` grep -q closes the pipe ->
      SIGPIPE(141) -> a SUCCESSFUL match read as a failed pipeline -> false REFUSE (rc=2).
      Capture-then-match now.
- [x] **R23-19 — MEASURED ✅ 2026-09-02 — the +27.363% headline is a SCREEN-RUNG number; the production-facing headline
      has never been measured.** Proven 2026-09-02 from the headline evidence record
      `champion-vs-production.732389d6d9d0.json`: `peak_vram_bytes` 1.49 GB and samples 536→684
      t/s — that is the 1.5B DeepSeek-R1-Distill screen rung, not Qwen3.8-27B-Q8_0 (~29 GB,
      ~65 t/s on the same surface per the 10:03Z keyed floor). Run 23 predates R23-11, so
      `headline_model` fell back to `--model` by construction; this is the design working, not a
      defect — D4 exists precisely because a screen-rung headline does not transfer (CH-6
      precedent: MMQ_MFMA +23.09% on the 0.5B vs **+0.50%** on the 27B, ~46× attenuation).
      **Standing operator instruction violated by my own reporting** (headlines MUST be the
      production recipe), corrected in-session. ACTION: measure champion-vs-production on the 27B
      at the step6→step7 seam (~1 h device, 20 pairs, anchor-gen-014, alongside the DFlash2
      smoke), and until it exists quote the headline as "+27.363% (1.5B screen rung)" — never
      bare. Until then the champion's production-facing gain is UNKNOWN, not 27%.
      **MEASURED 2026-09-02T12:49Z — the production-rung headline is `-1.600%`, and the run is
      DRIFT-FLAGGED so it is INCONCLUSIVE, not a proven regression.**
      champion `732389d6` vs frozen production-v9 on Qwen3.8-27B-Q8_0, dec-b4, 20 pairs, floor
      0.949%: production median **66.09 t/s** vs champion **65.05 t/s**. Residency clean (40/40
      resident, 1 KFD proc, 28.0 GB VRAM, clocks pinned 1700/1700, `clock_stable` true), so this
      is NOT a placement or throttle artifact. BUT `drifting: True` — both arms declined together
      (anchor -0.535%, candidate -0.654%; trend rho -0.481 / -0.668), and the instrument therefore
      returns `decisive: False` despite |effect| > floor. Contrast the SAME surface at 06:52-10:03Z
      (the A/A calibration): drift 0.13/0.27, rho 0.06/0.21, `drifting: False` — the machine was
      steady this morning and is not now, after ~6 h of continuous GPU load.
      **What is established**: the +27.363% figure does NOT transfer to production; the champion's
      production-rung gain is at best flat and possibly negative. **What is NOT established**: that
      it is a real -1.6% regression.
      **Consequence**: run 24 stays HELD (pre-auth not restored). Next action is R23-22.
- [x] **R23-22 — DONE ✅ 2026-09-02 — re-measure the production-rung headline on a SETTLED device.** The 12:49Z run is
      drift-flagged and cannot carry a verdict either way. Let the GPU idle (no benches) before
      re-running `headline_on_confirm_rung.py` with the same arguments, and check `drifting` is
      False before believing the number. If the settled re-measure is inside the floor -> champion
      is production-NEUTRAL (the keeps bought screen-rung speed that does not transfer); if it
      reproduces beyond the floor -> the keeps are a real production REGRESSION and the lineage
      needs a bisect (`7d2ea88b` / `db18f393` / `732389d6`) before any promotion. Either outcome is
      a decision package for the operator, not an autonomous action.
      **RESULT 2026-09-02T14:2xZ, 30 min idle settle, device verified 0% before start:
      `-1.414%`, `drifting: False`, `decisive: True`.** production median **65.92 t/s** vs
      champion **65.00 t/s**; drift 0.385/0.318, rho -0.307/-0.389 (inside tolerance), 40/40
      resident, clocks pinned 1700/1700. It REPRODUCES the drift-flagged 12:49Z run (-1.600%),
      two independent measurements agreeing within 0.19 pp.
      **VERDICT: the champion is a REAL ~1.4% production REGRESSION on dec-b4** — while being
      +27.363% on the 1.5B screen rung on THAT SAME SURFACE. The keeps are model-scale-specific
      and actively harmful at production scale. This is the sharpest possible vindication of the
      two-rung design (R23-10/R23-11) and of holding run 24.
      **Note the workload split**: DFlash2 generation is FINE on this champion (R23-17: 72.65 t/s,
      acceptance 0.6501). The regression is specific to the dec-b4 prefill-shaped surface — the
      very surface the loop optimized on the 1.5B.
- [x] **R23-23 — RESOLVED ✅ 2026-09-02 — OPERATOR DECISION: what to do with the regressing champion lineage before run 24.**
      Run 24 would launch WITH the confirm gate active, so it cannot repeat this defect going
      forward — but it would start from a base that is already -1.4% on production. Options:
      (a) **Bisect then repair** — first measure the pre-keep parent `9e18beb0` vs production
      (~50 min, ONE measurement): if it is neutral, today's three keeps own the regression and the
      culprit is isolated in 1-2 more runs; if it is already negative, the regression predates them
      and the whole lineage is suspect. Most informative; tells us WHICH mechanism class hurts
      production. (b) **Re-anchor to production-v9** — discard all three keeps, start run 24 clean
      with the confirm gate on. Cheapest, zero measurement, loses only screen-rung work that is
      worthless on production anyway. (c) **Launch run 24 as-is** — the confirm gate protects
      future keeps but bakes in the -1.4%. NOT recommended.
      **CORRECTED 2026-09-02 (before acting — two errors in the options above):**
      **(i) Option (b) is BARRED by the ratified single-champion invariant.** "Seed Champion = frozen
      production" is correct in exactly ONE moment: immediately after a promotion. We are MID-cycle,
      so applying it would silently discard the accumulated research — the precise 2026-08-31
      incident whose ruling reads *"I NEVER WANT TO SEE YOU MAKE THIS MISTAKE EVER AGAIN."*
      Option (b) is withdrawn; it must never be recommended mid-cycle again.
      **(ii) The -1.414% is the AGGREGATE's standing, NOT proven to be the three keeps' fault.**
      The champion is **67 commits / +4720 -310** above v9 and contains the manual-admission
      aggregate — DFlash2 loader + metadata, iqk fallbacks, speculative work (`5c278648a` verified
      an ancestor) — as well as every autokernel keep. Attributing the regression to run 23's three
      keeps was premature; R23-23's `9e18beb0` probe is exactly the test that attributes it.
      **Revised options**: (a) probe `9e18beb0` (RUNNING, result ~15:55Z) — if it is neutral the
      three keeps own the regression and a 3-commit revert cleans the base; if it is also ~-1.4%
      the regression predates them and lives in the older aggregate. (c) **launch run 24 as-is with
      the confirm gate already configured** — invariant-compliant, zero GPU cost, and every FUTURE
      keep must clear the 27B, so the loop cannot deepen the hole.
      **Recommendation: (a) then (c)** — the probe is already in flight and free, and run 24 cannot
      start before it finishes anyway (a second GPU workload would contend and corrupt both).
      **Recommendation (superseded): (a) then (b)** — spend one 50-minute measurement on `9e18beb0` to learn
      whether the defect is today's keeps or the whole lineage, then re-anchor accordingly.
      **RESOLVED 2026-09-02T16:15Z — probe (a) run, keeps EXONERATED, run 24 launched as-is (c).**
      `9e18beb0` (the pre-keep parent) measures **-1.751%** vs production — `drifting: False`,
      `decisive: True`, cleanest drift of any run yet (0.080/0.079, rho 0.081/0.090); production
      66.10 t/s vs 64.91 t/s. Against the champion's -1.414%, the three run-23 keeps moved
      production by **+0.337 pp — INSIDE the 0.949% floor** — so they are production-NEUTRAL, not
      the cause. **The regression predates them and lives in the older aggregate.** A 3-commit
      revert would have fixed nothing; none was made.
      **Reframing: this is very likely a FEATURE COST, not a defect.** The aggregate's
      -1.4/-1.75% is measured on dec-b4 = `pp=512, tg=0, ubatch=4` — a PREFILL-shaped surface that
      by construction cannot see DFlash2, whose entire value is in DECODE. The same champion
      delivers **2.38x speculative decode** at acceptance 0.6501 (R23-17). Paying ~1.7% of prefill
      for 2.38x decode is a good trade for real serving, not a regression to repair.
      Run 24 launched **pid 260751**, confirm gate ACTIVE (27B, 5 pairs, dec-b4 1.142% + dec-b8
      1.753%), screen parity waived-and-recorded, claim held on mi210_0.
- [ ] **R23-26 — the champion-vs-production HEADLINE SURFACE is wrong for this aggregate.**
      Established by R23-22/R23-23: the headline is measured on dec-b4 (`pp512/tg0`), a
      prefill-only shape, while the champion's largest asset (DFlash2, 2.38x) is a DECODE feature
      that surface cannot observe. The published headline therefore systematically UNDERSTATES the
      champion and reads as a regression while the aggregate may be strongly net-positive in real
      serving. Propose: the headline for an aggregate carrying decode features must include a
      decode/speculative surface (tg128 and/or a DFlash2-enabled arm) reported ALONGSIDE prefill,
      never replacing it. Until then quote the headline as "prefill-only".
- [x] **R23-27 — run 24 STOPPED and reconfigured to hunt ON the confirm rung** ✅ 2026-09-03
      (operator: *"do the third"*). **Why**: run 24 ran 14 h and produced **116 measurements, ZERO
      keeps** — best effect +0.650% against a 0.668% floor, only 4 attempts above +0.468%: the 1.5B
      screen surface is exhausted. Worse, R23-19/22/23 established that surface is anti-correlated
      with production for exactly the size-dependent families the planner keeps proposing (R23-25),
      so its verdicts were not worth the GPU claim. The confirm gate was NEVER exercised (no screen
      keep -> no KEEP_CANDIDATE -> the 27B path never ran).
      **Also degrading**: 161 planner transients, escalating 0-5/hr (evening) -> 23 at 01:00Z -> 21
      at 04:00Z -> **64 at 05:00Z against 7 measurements**, all malformed structured output
      (`hypothesis is missing [...]` 63+26, `authoring returned no changed paths` 26, `no parseable
      JSON object` 25) — the same class as the v3-v27 planner-outage spin. A fresh process clears it.
      **New configuration (dry-run PROVEN before launch)**: `--model Qwen3.8-27B-Q8_0` (was the 1.5B),
      `--surface dec-b4 --pairs 5`, NO `--confirm-model` (redundant once the screen IS the confirm
      rung). Dry-run reports `workload Qwen3.8-27B-Q8_0: n_embd=5120, dominant Q8_0`, floor
      **1.142%** correctly keyed to the 27B, and — the tell that this is right — **no "screen parity
      WAIVED" line**, because the hunting rung is now production-shaped by construction.
      **Consequences, stated honestly**: throughput drops (a 5-pair 27B A/B is ~14 min of device vs
      ~8 min for a 20-pair 1.5B run, so roughly 3/hr instead of 8/hr) and the keep bar rises to
      1.142%. In exchange every verdict is a PRODUCTION verdict, false negatives from rung transfer
      vanish by construction, and `headline_model` now equals the production model so the loop's own
      headline republish lands on the right rung (partially addressing R23-26; the SURFACE is still
      prefill-only, which R23-26 still owns).
      Run 24 stopped by SIGTERM to captured pid 260751, death verified before relaunch.
- [x] **R23-31 — Q4_K SIGNAL PROBE: +7.066%. The banked-gains thesis is CONFIRMED** ✅ 2026-09-03
      (step 1 of the operator-approved two-step). Champion `732389d6` (anchor-gen-014) vs frozen
      production-v9 on **`gemma-4-26B-A4B-it-Q4_K_M`** — an **in-fleet production role model** (the
      worker), not a hypothetical target — `dec-b4`, 5 pairs:
      **production 175.96 t/s -> champion 188.40 t/s = +7.066%**, `drifting: False`, residency clean
      (10/10 resident, 17.4 GB VRAM, clocks pinned 1700/1700, `clock_stable` true).
      **Status: SIGNAL, not a verdict** — no calibrated floor exists for this (surface, model), so
      `decisive` is `None` by construction. For scale: the 27B's dec-b4 floor at 5 pairs is 1.142%,
      so +7.07% is ~6x a comparable bar and very unlikely to be noise — but that reasoning borrows
      another model's floor and is NOT a substitute for calibrating this one.
      **What it establishes**: the Q4_K-gated keeps (`7d2ea88b`, `732389d6`) **do fire and do help**
      on a real Q4_K workload. R23-29's "dormant, not dead" reading is correct, and my earlier
      "worthless on production" framing was wrong in a way that mattered.
      **The champion's real standing is workload-dependent, not a single number**:
      | workload | champion vs production-v9 |
      |---|---|
      | Qwen3.8-27B Q8_0, dec-b4 (prefill) | **-1.414%** (decisive; Q4_K keeps inert, DFlash2 feature cost) |
      | gemma-4-26B-A4B Q4_K_M, dec-b4 (prefill) | **+7.066%** (signal; Q4_K keeps active) |
      | Qwen3.8-27B Q8_0, speculative decode | **2.38x** with DFlash2 (R23-17) |
      A single "champion vs production" headline cannot express this — which is R23-26's point,
      now with hard numbers behind it.
- [x] **R23-32 — DONE ✅ 2026-09-03 — step 2: calibrate the Q4_K surface and convert the +7.066% signal into a claim.**
      Approved shape (operator, 2026-09-03: cheap signal first, then calibrate only if promising —
      the signal is promising). Run the A/A bootstrap for
      (`dec-b4`, `gemma-4-26B-A4B-it-Q4_K_M`) to produce a keyed floor (~3 h, the 27B dec-b4
      calibration took 3 h 11 m), then re-measure with `headline_on_confirm_rung.py`, which will
      then pass its uncalibrated-surface refusal (rc=3) instead of tripping it.
      **Why it is worth the 3 h**: this is a production win available on a model we ALREADY SERVE.
      If it holds, the promotion argument changes from "the champion is neutral-to-negative" to
      "the champion is +7% on the worker", which is a different conversation entirely.
      **Needs a GPU window** — no run is currently hunting, so the window is open now.
      **RESULT 2026-09-03T12:1xZ — CLAIM-GRADE: `+7.206%`, `decisive: True`, `drifting: False`.**
      Champion `732389d6` vs frozen production-v9 on `gemma-4-26B-A4B-it-Q4_K_M`, dec-b4, **20
      pairs against the freshly calibrated 0.456% floor** — production **174.26 t/s** vs champion
      **186.76 t/s**, i.e. **15.8x the floor**. Drift inside tolerance (-0.223/-0.061, rho
      -0.311/-0.215), residency clean (40/40 resident, 1 KFD proc, clocks pinned 1700/1700).
      It reproduces the 5-pair signal (+7.066%) within 0.14 pp — two independent measurements,
      different pair counts, same answer.
      **The calibration that made it claim-grade** (R23-32's prerequisite): floor curve
      1.843/1.257/0.936/0.699/0.456 for k=1/3/5/9/20 — a 4.04x fall against the ideal sqrt(20)=4.47x,
      i.e. textbook parametric scaling and structurally believable (contrast dec-b8's anomalous 45x,
      which only the parametric guard caught). A/A effect **-0.061%**, `drifting: False`, despite a
      peer running a 48-thread CPU bench concurrently — the flagged memory-bandwidth co-residency
      did NOT contaminate it.
      **Isolation held**: run in the scratch store, so the live `champion-vs-production.json` still
      carries the 27B production headline (-1.414%, model field = Qwen3.8-27B-Q8_0) and was not
      overwritten by a Q4_K number.
      **What this establishes.** The champion is **+7.206% on a model the fleet already serves**
      (the worker). The Q4_K-gated keeps are not merely dormant — they are worth ~7% where they
      fire. The program's standing is now three measured workloads, not one number:
      -1.414% (27B Q8_0 prefill, decisive) · **+7.206% (26B-A4B Q4_K prefill, decisive)** ·
      2.38x (27B speculative decode, DFlash2). R23-26's "the headline surface is wrong for this
      aggregate" is now backed by two decisive measurements pointing opposite directions.
- [x] **R23-34 — planner/critic model split (operator directive 2026-09-03: "swap the models
      used by planner/critic. Use Fable-5.1-medium for the planner and gpt-5.6-sol-high for
      critic") — DONE, NOT launched** ✅ 2026-09-03. Research lane `f81bbeb6`.
      **Before**: both roles ran one `codex exec` argv with NO model/effort flag — whatever
      `~/.codex/config.toml` said (`gpt-5.6-sol`/`high`, so the critic target was already the
      implicit default, but unpinned). **After**: `actors.Backend.argv` is the per-CLI contract;
      `backend_for(model, effort)` routes `claude-*` to the `claude` CLI, else codex. Defaults =
      the directive; `--planner-model/--planner-effort/--critic-model/--critic-effort` override;
      the startup banner prints `actors    planner=claude:claude-fable-5-1@medium
      critic=codex:gpt-5.6-sol@high` (dry-run verified) so a run records what drove it —
      provenance R23-19 showed is not optional. Classes `CodexPlanner/CodexCritic` ->
      `AgentPlanner/AgentCritic`. 390/390 loop tests, 5 new ones pin exact argv tokens.
      **Measured constraints that shaped it (all live smokes, one call each):**
      · codex `-c` is TOML — `model_reasoning_effort="high"` MUST be quoted (unquoted rejected).
      · `claude -p --bare` would skip the worktree's CLAUDE.md but accepts ONLY
        `ANTHROPIC_API_KEY`/apiKeyHelper — OAuth is never read; this host is claude.ai-OAuth-only,
        so `--bare` and `CLAUDE_CODE_SIMPLE=1` both fail "Not logged in". Not used.
      · The lane worktrees carry the llama-tree freeze overlay CLAUDE.md. A deliberately hostile
        fake ("never create files") made Fable REFUSE ("The project's CLAUDE.md marks this
        directory as frozen"); `--system-prompt` does not suppress it. **But the REAL overlay
        scopes its freeze to `production-consolidated-*` and says to check the branch — in a real
        detached champion worktree (probe `worktree add --detach` @732389d6, removed after) Fable
        AUTHORED cleanly.** The fake was harsher than reality; the real artifact is what counts.
      · Mitigation shipped: `_CLAUDE_SANDBOX_NOTE` via `--append-system-prompt` states that scoping
        explicitly so authoring does not depend on the model re-deriving it. Residual risk: the
        overlay IS loaded and the real-worktree proof is n=1 — watch the first iterations of the
        next run for `planner_transient` refusals of the "frozen" shape.
      **Regrowth guard** 2160 -> 2210 (+44 code lines, reason recorded in the guard per its own
      doctrine). **Also fixed en route** (`078d9c3c`, separate commit): `test_bench`'s live-store
      test asserted the 27B is uncalibrated (None) — true 09-01, false since the 09-02 keyed
      floors; now asserts the actual intent (27B rows != 1.5B rows). R21-4 family.
      **Cost note**: 2 of the 4 actor calls per iteration (propose, author) now run on Fable 5.1;
      2 (both critic passes) stay on codex. **NO RUN WAS STARTED** — standing instruction; the
      config is the default, so the run-25 launch shape restarts it unchanged when the operator
      says so.
      **RUN 26 LAUNCHED 2026-09-03T12:59Z, pid 24549** (operator: "start the run"). Preflight gated the
      launch: GPU 0%, zero loops, champ2 tip == anchor-gen-014 provenance (732389d6). Banner confirms
      `actors    planner=claude:claude-fable-5-1@medium  critic=codex:gpt-5.6-sol@high`, claim held,
      27B production rung, floor 1.142% @5 pairs. Monitor armed for keeps/advances, measured rows,
      transient counts, frozen-shaped refusals (the R23-34 residual risk) and death.
      **Run 26 STOPPED 13:05->13:22Z and RUN 27 LAUNCHED 13:24Z, pid 2047396** — operator ("I have
      no issue restarting") took the second-surface guard: `--confirm-model` = the same 27B,
      `--confirm-surfaces dec-b8 --confirm-pairs 5` (floor 1.753%). Screen==confirm model, so
      parity is EXACT (no waiver line). Every dec-b4 keep candidate must now clear dec-b8 before
      touching the champion; the gate fires only on candidates (~14 min each). **Run 26's 25 min
      delivered the end-to-end proof of the planner swap**: `akm-gdn-next-token-register-prefetch`
      went propose->critic->author->critic->build->MEASURED (+0.305%, null) — a `gated_delta_net`
      target the 1.5B could never have surfaced. Not guarded: decode. tg128 has no 27B floor
      (each floor is per (surface, model) — see the operator Q&A in progress 2026-09-03); the
      DFlash2 path is llama-server-only and is guarded by R23-18's smoke, still open.
- [x] **R23-35 — first confirm-gate keep + the planner-backend evolution** ✅ 2026-09-03.
      **Run 27 keep** `akm-cdna2-q8-b4-mmvq-route`: **+23.339% dec-b4** decisive (floor 1.142%),
      **cleared the dec-b8 confirm gate** (+0.313%) — the FIRST time the two-rung gate fired. It is
      a production number: headline **+22.443%** vs frozen production-v9 on the 27B, champion now
      `b0eb4fab` / anchor-gen-015. Mechanism: Q8_0 ne11<=4 rerouted MMQ->MMVQ (the in-tree lever
      around the vendor Tensile GEMM). Banked regardless of planner.
- [x] **R23-36 — actor exit-1 storm made diagnosable** ✅ 2026-09-03 (`b5cd2817`). Run 27 logged 74
      `actor exited 1:` with EMPTY detail because `claude -p` reports errors on STDOUT (empty stderr)
      and `_run_agent` kept only the stderr tail. Fix: non-zero exits carry backend id + BOTH tails.
      Storm was intermittent (~40% iters), cleared on its own; live repro ruled out auth/concurrency/
      overlay/prompt-size. **NOT root-caused** — see R23-38.
- [x] **R23-37 — planner backend is now DeepSeek V4 Flash @max via opencode** ✅ 2026-09-03
      (`c2bfe916`). Third `Backend` kind wired: `opencode run --auto --dir <wt> -m
      deepseek/deepseek-v4-flash --variant max <prompt>`; `backend_for` routes `provider/model`
      (has `/`) to opencode. Path was Fable 5.1 @medium (`f81bbeb6`, ~75s/call, 54-71% GPU-idle) ->
      Opus 5 @high (`1ffe4fdf`, default set but NEVER launched) -> DeepSeek (smoke: authored in a
      real champion worktree in ~4s). **TRUST BOUNDARY**: opencode drives an EXTERNAL provider, so
      planner prompts egress off-host — operator-sanctioned as the backup, recorded in code+commit.
      Run 28 live pid 470013 with this planner + the dec-b8 confirm gate.
- [x] **R23-40 — FIXED+CONFIRMED ✅ 2026-09-04 — INCIDENT: Run-18 build-non-determinism fault recurred on the 445e93a8 anchor
      promotion; run 28 aborted.** After the second keep (`akm-cdna2-q8-b4-y-stream-amortize`
      +10.098%, dec-b8-confirmed, champion `445e93a8`), the anchor guard found the promoted
      anchor-gen-016 binary's code-section digest DIFFERS from a fresh champion rebuild even after
      one heal (`d6d195bb...` vs `5e3ca1e7...`) — the Run-18 fault class — and raised RunAborted
      ("proven with zero pairs spent"). The integrity system worked: it refused to seat a
      non-reproducible anchor. Consequences: headline never republished for 445e93a8 (still shows
      b0eb4fab +22.443%); run 28 is a ZOMBIE (pid 470013 alive but `run_aborted` recorded, step
      None, GPU idle, 1 child, no measurement since 21:58); no anchor-gen-017 recovery. **BOTH
      KEEPS ARE SAFE in git** (champion 445e93a8 = b0eb4fab +23.3% + 445e93a8 +10.1%, both
      screen-decisive + dec-b8-confirmed). ROOT CAUSE to find: why champ2 builds are
      non-deterministic (ccache? -j race? worktree state?) — same class as the 2026-08-31 anchor
      attestation doctrine. **BLOCKS relaunch**: the next keep will hit the same guard abort until
      the build is reproducible. Decision for operator: (a) kill the zombie + investigate build
      determinism before relaunch; (b) relaunch anyway and accept aborts at each keep. Recommend
      (a).
      **ROOT-CAUSED 2026-09-03 (cheap, no rebuild): `libggml-hip.so` is non-reproducible; the
      CPU executable is NOT.** champ2 clean at 445e93a8, ccache absent -> genuine non-determinism.
      Hashing existing binaries' .text: `llama-bench` is BYTE-IDENTICAL across anchor-gen-016 +
      champ2 + all 7 lanes (`7337b4bb`), but `libggml-hip.so` (`6bac92af` vs `55f783de`),
      `libggml.so`, `libllama.so` all DIFFER. The guard (`anchor_integrity.build_digest`,
      run.py:405/475) hashes `bin/libggml-hip.so` ALONE — the gfx90a HIP kernel lib, which is the
      non-deterministic one. Cause class: hipcc gfx90a code-object generation is not reproducible
      build-to-build (parallel-compile ordering / embedded metadata), plausibly aggravated by the
      7-lane concurrent build load; contradicts the guard's R22-3/R21-10 determinism premise, so
      something regressed. FIX (operator design call): (i) make the HIP build reproducible — hipcc
      determinism flags / libggml-hip.so at -j1 / isolate the anchor build from lane builds;
      (ii) hash a deterministic proxy (defeats purpose — the kernels ARE the artifact); (iii) widen
      the guard to accept a hash mismatch when a functional A/A confirms equivalence (weakens the
      R18/R21 doctrine). Recommend (i). Until fixed EVERY keep aborts at its anchor guard, so the
      loop cannot advance past one keep. Both current keeps remain safe in git.
      **FIX CONFIRMED 2026-09-04**: `build_champion` -> `-j1` (research `f4f13116`). The
      determinism probe built champion 445e93a8's `libggml-hip.so` twice at `-j1`: byte-identical
      code digests (`1d04c67a...595bb4`, A=B), VERDICT DETERMINISTIC. So `-j64` parallelism was the
      root cause and serial build fixes it; the promoted anchor and the guard's fresh build now
      match. Measured cost: ~13 min per `-j1` build (786s/794s), per-KEEP only, lane builds stay
      `-j64`. **RELAUNCH-READY** (operator-gated): run 29 = run 28's command on the current champion
      445e93a8/anchor-gen-... rebuilt clean, DeepSeek planner + codex critic + dec-b8 confirm gate.
      Follow-up R23-41: hipcc determinism flags to restore parallel anchor builds later (optional).
- [ ] **R23-42 — the dec-b4 keeps do NOT move DFlash2 decode; run 29 pivoted to tg128 (operator
      2026-09-04).** MEASURED the DFlash2 smoke on champion 445e93a8 (both new keeps): **71.22 t/s**
      decode, acceptance 0.6427, 2.35x boost — vs 72.65 on the prior champion 732389d6 (R23-17) and
      70.0 at the DF2-5 baseline. So the two keeps that measured **+23.3% and +10.1% on dec-b4**
      (batched prefill) produce **~0% on DFlash2 decode** — the R23-26 non-transfer lesson, now with
      the sharpest contrast yet (decisive +35% prefill -> flat decode). dec-b4 keeps optimize a
      batched-forward path the DFlash2 decode loop is not bottlenecked on (its speed is set by the
      draft model + acceptance, not the target verify). Operator corrected the arithmetic
      `70*1.233*1.101=95` -> measured 71. **Run 29 pivots to hunt a decode-relevant surface**:
      `--surface tg128` (target single-token decode — the "none"/fallback path, ~30 t/s; more
      serving-relevant than dec-b4 prefill, though still not a DIRECT DFlash2 measure since
      llama-bench can't drive the spec-decode loop), dec-b8 confirm gate retained. Needs a tg128 27B
      floor first — **calibration RUNNING** pid 3807583 (~1h), run 29 launches once it writes a sane
      floor. Champion 445e93a8 = anchor-gen-016; -j1 build fix (R23-40) in place so keeps won't abort.
      Open sub-question: is there a surface that DIRECTLY tracks DFlash2 throughput? (would need a
      server-based spec-decode bench, not llama-bench.)
- [ ] **R23-43 — RE-ARCHITECT: keeps demonstrated on llama-server under the champion's CANONICAL
      RECIPE, not llama-bench (operator directive 2026-09-04, four messages).** Principle: "the only
      performance that matters is serving performance; no point boosting llama-bench numbers not
      reflective of a live environment." Proven necessary: dec-b4 keeps +23.3%/+10.1% (bench)
      -> DFlash2 decode 71.22 t/s FLAT (R23-42). Design (operator's):
      · **Champion = (kernel commit + canonical serving recipe).** The recipe is a GENERAL,
        parameterized artifact describing the champion's optimal serving config on its hardware:
        model, quant, `spec_decode.type` in {none, draft-dflash, draft-mtp, ...}, drafter (if any),
        concurrency (np), ctx, ctk/ctv, server flags, and the metric (aggregate vs per-slot tok/s).
        Flexible by construction: a non-DFlash2 model carries `spec_decode: none`/`mtp` + its own
        optimal np -- NO DFlash2 assumption in the framework. It is also the PROMOTION recipe
        (production needs it anyway), so it is not extra work.
      · **llama-bench = experiment/screen layer** (fast, deterministic, planner hypothesis testing,
        null-killing). NEVER decides a keep.
      · **llama-server under the canonical recipe = keep gate + headline.** A keep is real only if it
        improves SERVING throughput under the champion's own optimal recipe.
      BUILD ORDER: (a) canonical-recipe schema + the current champion's recipe (27B/GPU/DFlash2 at
      optimal np -- DF2-5 grid peaked np4-8 ~154 t/s aggregate; pin the optimal); (b) generalize
      `dflash2_capability_smoke.sh` -> a recipe-driven serving A/B (champion vs candidate,
      paired/alternating, reads the recipe); (c) calibrate the SERVING noise floor under the recipe
      (A/A x~12, like dec-b4/b8) so a keep is decisive vs serving noise; (d) wire as the keep gate,
      llama-bench demoted to screen. Supersedes the dec-b8-llama-bench confirm rung and subsumes
      R23-18 (DFlash2 regression guard) and R23-26 (headline surface). Substantial -- a new
      measurement core. Run 29 HOLDS until (a)-(d) exist; champion 445e93a8 + -j1 fix are ready.
- [ ] **R23-38 — root-cause the claude -p exit-1 storm before Fable/Opus are used as a planner
      again.** The instrumentation (R23-36) will now capture the reason, but the storm cleared
      before it landed, so the cause is still unknown. It gated ~40% of run-27 iterations and cost
      the retry-backoff ladder each time. Only matters if a claude-CLI backend is reselected;
      opencode/DeepSeek is the current planner, so this is NOT blocking. Re-open if the exit-1
      pattern recurs with the new instrumented build.
- [ ] **R23-39 — measure whether DeepSeek/opencode restores throughput.** Run 28's open question:
      does the ~4s DeepSeek call latency close the 54-71% GPU-idle gap the Fable planner opened?
      Read idle_fraction_while_claimed + iterations/hour after run 28 has a few hours, compare to
      run 26 (all-codex) and run 27 (Fable). Decides whether the external-provider trust cost is
      worth it or the planner should return to a local CLI.
- [ ] **R23-33 — OPERATOR DECISION: does +7.206% on the worker change the promotion calculus?**
      Before today the promotion argument was "the champion is neutral-to-negative on production".
      It is now "the champion is decisively +7.2% on an in-fleet production role model, -1.4% on
      the 27B prefill surface, and 2.38x on speculative decode". That is a materially different
      conversation and it is the operator's to have. Inputs: the freeze runbook
      (`docs/reference/kernel-freeze-runbook.md`), R23-29's promotion-time condition (the Q4_K paths
      are now performance-VALIDATED by this measurement, closing that gap for dec-b4), and R23-26
      (a promotion headline must state its workload). **No run starts, and no promotion step is
      taken, without explicit operator permission** (standing instruction 2026-09-03).
- [ ] **R23-30 — the boundary driver's 15-min SIGTERM grace is WRONG for a confirm-rung run and
      will SIGKILL every stop.** Measured 2026-09-03 stopping run 25 (27B rung, 7 workers):
      graceful drain took **~87 min** (SIGTERM 07:59:09Z -> last publish ~09:25Z), because each lane
      holding a measurement finishes it and lanes serialize on the claim. Publish cadence was
      steady at **17.3 / 17.5 / 17.8 min** per lane; 2 lanes abandoned at formation, 5 completed.
      `boundary_20260901.sh:98` sets `KILL_WAIT_S=900` with the comment *"drain-tier loop: <=5 min
      historically"* — true for the 1.5B screen rung (run 23 drained in 15 min) and **false by ~6x
      for the 27B rung**. As written the next boundary SIGKILLs mid-measurement every time,
      discarding up to ~17 min of device work per in-flight lane and losing those verdicts.
      **Fix**: scale the grace to `workers x per-measurement-time` for the configured rung (~2 h for
      7 workers on the 27B), or make the driver poll for loop exit rather than use a fixed deadline.
      **Diagnostic note for whoever reads a drain**: `loop-status.step` names only the ONE active
      lane, never the queue — lanes serialize on the claim, so remaining work must be derived as
      `workers - (abandoned + published)`, not inferred from the step field. Two ETAs were wrong in
      this session for exactly that reason.
- [ ] **R23-28 — a FAITHFUL cheap screen rung may be impossible; route by SENSITIVITY AXIS**
      (operator question 2026-09-03: *"shouldn't we then use a different screening model in the
      appropriate quantization?"*). Refines R23-25. A screen must match production on THREE axes:
      **quant family**, **architecture**, and **GEMM dimensions**. The first two are cheap to match;
      the third is not, and that is the trap: the winning tile (`MT128x96x64`, 23.89% of production
      device time) is selected by rocBLAS/Tensile FROM THE MATRIX DIMENSIONS, which derive from
      n_embd=5120. Any model small enough to be a cheap screen has different dims and therefore
      dispatches different tiles — **the property that makes a screen cheap is the property that
      destroys its fidelity for GEMM work.**
      **Measured evidence** (run 25's first profile vs run 24's): production top hotspot
      `MT128x96x64` (23.89%) then `MT64x64x64` (18.44%) then `gated_delta_net_cuda` (13.55%) then
      `MT64x32x64` (11.97%) then `dequantize_block_q8_0_f16` (10.75%). The 1.5B Q4_K screen's top
      was `MT64x64x64` and it dispatches NO Q8_0 dequant and NO gated_delta_net at all.
      **So**: a same-quant same-architecture small model WOULD faithfully screen dequant kernels,
      SSM/gated_delta_net work and attention geometry, but NOT GEMM tiling or occupancy. Those must
      be hunted on production (which run 25 now does).
      **Availability check (2026-09-03): no such screen exists on disk** — the Qwen3.8 (SSM-hybrid)
      family has only the 27B. `Qwen3-1.7B-Q8_0.gguf` is a DENSE transformer and would not exercise
      `gated_delta_net` at all. Filing rather than acting: sourcing or building a small
      SSM-hybrid Q8_0 screen is a real piece of work with its own value question.
- [ ] **R23-29 — the Q4_K keeps are BANKED for a future Q4_K GPU target, not wasted** (operator
      question: *"could the gains obtained through the current screening model still be useful if we
      were to one day choose a Q4_K target model on the GPU?"* — yes, and this CORRECTS my earlier
      "worthless on production" framing, which was too strong).
      **VERIFIED by reading the diffs**: `7d2ea88b` gates on `GGML_TYPE_Q4_K` and `732389d6` on
      `type == GGML_TYPE_Q4_K` — both are hard-gated and **cannot execute on a Q8_0 model**. That is
      precisely WHY the champion measures production-NEUTRAL (+0.337 pp, inside floor): the code
      never fires. They are DORMANT, not harmful. `db18f393` (fattn) carries no quant gate and is
      the only one of the three that runs on the current production model.
      **Consequence**: on a Q4_K GPU serving path — the large-MoE-with-CPU-offload roadmap item is
      exactly that class — these become live again. **Caveat against over-claiming**: the +5.097%
      and +13.930% were measured on a 1.5B Q4_K; a large Q4_K model has different GEMM dims, so the
      quant PATH transfers but the MAGNITUDE does not. Treat them as promising leads to re-measure
      on the real target, never as banked numbers.
      **Actionable**: record a `quant_family` / `applies_to` field on every keep so (i) the headline
      can be reported per target, (ii) a future Q4_K path inherits them deliberately rather than by
      archaeology, (iii) the loop can be told which quant family to hunt. llama.cpp already templates
      per quant type and our keeps already gate correctly, so this is metadata, not restructuring.
      **PROMOTION-TIME CONDITION (folded in 2026-09-03 at operator request).** These paths have
      **zero performance validation on any Q4_K workload since they were written** — every
      measurement since has run on Q8_0, where they cannot fire. Correctness coverage is probably
      fine (the gate runs `test-backend-ops -o MUL_MAT`, which sweeps quant types by design, 1139/1139
      passing) but is NOT provable from the stored record: the gate `detail` field is truncated to
      **500 chars**, so grepping it for `type_a=q4_K` returns nothing and that absence proves nothing
      (see [[feedback_verify_negatives_before_concluding_absence]]). Before any promotion ships these
      into production they must EITHER be exercised against a real Q4_K workload OR be explicitly
      marked carried-but-unvalidated-on-this-path in the freeze runbook — otherwise the first person
      to serve Q4_K on the promoted kernel is the one who discovers the state of them.
      **Q4_K targets available on disk for that check (inventoried 2026-09-03)**:
      `gemma-4-26B-A4B-it-Q4_K_M.gguf` (16.8 GB, MoE, and **already an in-fleet production role
      model** — the worker — so this is not a hypothetical future target),
      `gemma-4-31B-it-Q4_K_M.gguf` (18.7 GB, dense), `MathSmith-...-Qwen3-8B.Q4_K_M.gguf` (5.0 GB).
      All fit the MI210's 64 GB comfortably and carry production-scale GEMM dims, unlike the 1.5B.
      **Cost warning — it is NOT a quick check as gated**: `headline_on_confirm_rung.py` REFUSES on an
      uncalibrated (surface, model) pair (rc=3, mutation-tested), and no Q4_K floor exists; the A/A
      bootstrap that produced the 27B floor took **3 h 11 m**. Cheap first step instead: an
      UNGATED llama-bench A/B (champion vs production on a Q4_K model, ~15 min) as a signal only —
      not claim-grade, but enough to decide whether the 3 h calibration is worth spending. Needs a
      GPU window: run 25 holds the mi210_0 claim.
- [ ] **R23-24 — FALSE-NEGATIVE exposure: screen-rung rejections may hide production WINS**
      (operator question, 2026-09-02: *"Doesn't the above also mean that measured regressions
      performed by autokernel could have actually been beneficial in production?"* — yes).
      **Why today's result raises this, not just the false-positive risk**: the prior working
      model was ATTENUATION (CH-6: +23.09% on the 0.5B -> +0.50% on the 27B). Attenuation is
      monotone — it shrinks magnitude but preserves sign, so it can only manufacture false
      POSITIVES. R23-22 measured a **sign INVERSION** (+27.363% screen -> -1.414% production on
      the same surface). Once the transfer function can flip sign it can flip in BOTH directions,
      so the same evidence that convicted the keeps also admits false negatives.
      **Structurally they may be MORE likely than false positives**: an optimization with fixed
      setup cost + size-scaling benefit looks NEGATIVE at n_embd=1536 (overhead dominates) and
      POSITIVE at n_embd=5120 (benefit dominates). That is the textbook false negative.
      **Bounded exposure, measured**: run 23 produced 80 `measured_null` rows, but **71 were
      INSIDE the floor** — inconclusive on the screen rung, carrying no information about
      production either way. Only **9 were decisive negatives**, and they are the candidates:
      `akm-fattn-causal-tile-skip` -4.851% · `akm-cdna2-mmvq-256-thread-block` -1.885% ·
      `akm-cdna2-b1-mmvq-eight-nwarps` -1.699% · `akm-mmvq-dense-256-thread-launch` -1.055% ·
      `akm-mmvq-gfx90a-four-wave-launch` -1.020% · `akm-q4k-wave-scale-broadcast-rerun` -0.959% ·
      `akm-mmvq-gfx90a-256-thread-launch` -0.928% · `akm-mmvq-cdna2-256-thread-launch` -0.830% ·
      `akm-fattn-gfx90a-prefill-eight-wave-vkq` -0.720%.
      **They cluster in exactly the size-dependent families** (MMVQ thread-block/wave-launch
      geometry, fattn wave geometry) — the same families as the keeps whose sign just inverted.
      **Nothing is lost**: every negative carries mechanism, statement, falsifier and full sample
      vector in `experiments.db` (a rebuild design goal), so all 9 are re-testable on the confirm
      rung at ~50 min each (~7.5 h for all). Do NOT chase all of them reflexively.
- [ ] **R23-25 — route hypotheses to a rung by MECHANISM FAMILY, not uniformly.** Follows from
      R23-24. A screen-rung verdict is only informative for mechanisms whose effect is
      size-INDEPENDENT (removing redundant work, algebraic simplification, fewer dispatches).
      For size-DEPENDENT families — launch geometry, occupancy, wave/thread-block counts, tiling —
      the 1.5B verdict is uninformative and today's evidence suggests it can be anti-informative.
      Proposal: mark those families to SKIP the screen and go straight to the confirm rung,
      accepting the higher per-attempt cost in exchange for a verdict that means something.
      Decide after R23-23's bisect names the culprit family.
      **APPROVED + ARMED 2026-09-02** (operator: "approved"). Tool:
      `scripts/benchmark/headline_on_confirm_rung.py` (research `HEAD`) — reuses the loop's own
      `production.refresh` + `bench.compare`, so the bundle is schema-identical and carries
      R23-11's `model` provenance field (the absence of which made the screen-rung headline
      unreadable in the first place). Floor re-keyed via `noise_floor_pct` to the 27B: **0.949%**
      at 20 pairs, not the 1.5B's 0.668%. Dry-run green; BOTH refusals mutation-tested live —
      provenance mismatch (rc=2) and uncalibrated surface (rc=3, proven against dec-b8 while its
      calibration was still running). Baseline reuses the cached `v9v-build-base` (no rebuild).
      SEAM ORDER: DFlash2 smoke first (~10 min, gating for run 24), then this (~1 h, dec-b4).
- [x] **R23-19a — the confirm-rung headline instrument built and proven** ✅ 2026-09-02 —
      `scripts/benchmark/headline_on_confirm_rung.py`: dry-run resolves the 27B keyed floor
      (0.949% @20 pairs) and the dec-b4 shape (pp=512 tg=0 ub=4); BOTH fail-closed paths
      mutation-tested rather than assumed — provenance mismatch rc=2, uncalibrated surface rc=3
      (fired against dec-b8 live, while its calibration was still running). Cached
      `v9v-build-base` reused, so no production rebuild. Measurement itself is R23-19.
- [x] **R23-20 — the 27B dec-b4 keyed floor landed and was verified sane** ✅ 2026-09-02 (10:03Z)
      — `calibration/dec-b4.Qwen3.8-27B-Q8_0.json`: floor 0.949% @20 pairs (1.142% at the pairs=5
      confirm gate), A/A effect +0.576% sitting INSIDE its own derived floor as a clean A/A must,
      drift 0.13/0.27% with no trend, residency 40/40 resident and clocks pinned 1700 MHz,
      device_seconds 3282 per condition. First 27B floor the program has ever had.
- [ ] **R23-21 — decide whether the confirm-rung headline also gets measured on dec-b8** — dec-b4
      is the approved scope (operator 2026-09-02); dec-b8 would cost another ~1 h and is the other
      confirm surface. NOT auto-run: it doubles the hold on run 24 for a second view of the same
      question. Decide after R23-19's dec-b4 number is in hand — if dec-b4 shows heavy
      attenuation, dec-b8 becomes informative rather than confirmatory.
- [ ] **R23-18 — standing rule candidate: DFlash2 smoke joins the confirm gate** — any future
      keep touching fattn*/mmvq/mmq/speculative-verify files should trigger the capability smoke
      before the champion advances (cheap: ~5 min; the confirm rung already owns the 27B).
      Decide after R23-17's first measured result whether this goes in loop code or stays a
      boundary-step; if loop code, it rides the regrowth budget conversation.

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

### Second pass, 2026-08-30 — two more, both deliberate

- **A CPU non-regression gate at every champion advance. DEFERRED BY THE OPERATOR — design
  recorded, NOT built.** The operator raised it and the reasoning is correct and important: *"if
  the champion is the promotion candidate, it cannot present a regression vs the CPU kernel
  anchor."* Then deferred it explicitly — *"we can discuss CPU coupling later"*, *"I'd like to get
  GPU science working once and for all."*
  **The design, recorded so it is not re-derived:** an **unconditional** gate at every champion
  advance, **once per keep** — emphatically *not* a per-patch file-scope check. Static file-scope
  analysis cannot bound influence through shared headers, inlining or link order, so *"this patch
  only touched `ggml-cuda/`"* is not a proof of CPU non-regression and must not be used as one.
  **Named blocker:** this session is GPU-only by standing operator constraint, and the gate needs a
  CPU window. **Do not build it** until that window and the operator's CPU-coupling discussion
  exist.
- **A fix for the "arms were swapped" hypothesis. NOT BUILT, on purpose.** The hypothesis was
  **refuted by direct benchmarking** (R18-B(c)), so any patch would have been aimed at a mechanism
  that had already been excluded. Recorded as open forensics rather than as a guessed patch. *The
  temptation here is real and worth naming: three refuted hypotheses feel like an obligation to
  ship the fourth, and a fix for an unidentified cause is indistinguishable from a coincidence.*

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
