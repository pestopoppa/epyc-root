# AutoKernel — the standing aggregate candidate (champion)

**Owner:** operator audit session, 2026-08-27. **Depends on:** INF-06 (campaign), INF-64 (repair track).
**Operator requirement, 2026-08-27:** *"There should ALWAYS be an aggregate production candidate that
holds all the experimented tweaks and is ready for promotion gate testing."* And: AutoKernel screens
against that aggregate, *"attempting to make it better"*, rather than re-deriving deltas against a
fixed production anchor.

## Start here — open work (everything else on this page is closed evidence)

| task | what to do |
|---|---|
| **CH-14** | Write the manual-research loop runbook — START FROM `scripts/benchmark/serving_evidence_refresh_runbook.md` (research repo, 2026-08-31): the serving-side procedure is now fully documented+scripted there (emitter chain, ceiling derivation, claim/residency gates); CH-14's remaining scope is the authority-boundary statement in docs/guides/ wrapping it.  (admit → gate → attest) in `docs/guides/`, stating the authority boundary explicitly. |
| **CH-16** | Correct the loop champion's inflated per-commit claims at the branch tip and in `program.md` — UNBLOCKED 2026-08-31 (branch merged + tagged); coordinate with INF-66 R21-3 (if the branch is retired, the note lands at tag `ak/pre-reconcile-loop-20260831`). |
| **CH-4 / CH-6 follow-ons** | See their entries; both are settled to a conclusion, follow-ons only. |
| **not on this page** | `AK-INST-3` (prove a campaign reaches `sci >= 1`), `AK-INST-2`, `AK-DEPLOY-2` live in [`autokernel-restart-and-strip.md`](autokernel-restart-and-strip.md). |

**CONSOLIDATION COMPLETE 2026-09-08 — the champion is `ef81196d5`** (GPU tip `bff30cebe` + CPU
champion3 `9c4f73e29`, FOLD-2 G1-G5 PASS). INF-70 has **no CPU keeps to fold**; the operator's
*no-kernel-research-until-a-fully-consolidated-champion* condition is satisfied. Loop relaunch is a
**separate operator go**. Before any sweep picks up "an unfolded CPU branch", read the **DO-NOT-FOLD
ledger** at the bottom of this page (`inf70/sync17-fix2 @ 2516c9807` is a measured **regression**).

**RECONCILED 2026-08-31 — there is ONE champion now, by ratified invariant.** The two lineages
this page used to distinguish were the incident (INC-20260831-champion-lineage-fork: the rebuilt
loop was seeded 2026-08-30 from bare v9 as a NEW sibling branch while THE champion sat one branch
over; runs 18–20 optimised the wrong base; surfaced when the operator asked why DFlash2 was absent
from the dashboard capability list). Operator ruling, ratified into
`agents/shared/OPERATING_CONSTRAINTS.md` (root `35c1a6d1`): **one single champion per production
kernel tree**, aggregating ALL improvement work (manual + AutoKernel) between promotions;
seed-from-production is legal only immediately after a promotion; a second lineage for the same
tree is a defect the moment it exists; standing is resolved against the CURRENT frozen production,
live, never a pinned sha; the champion exists so promotion = take the one precompiled branch.

**The current champion: `a2728701` on `ak/champion/llama-cpp-0db32c06e3e5`** — merge of the
manual-admission side (`270b48ed`, MoE-Spec + DFlash2, tag `ak/pre-reconcile-manual-20260831`)
and the loop side (`4925b208`, tag `ak/pre-reconcile-loop-20260831`); zero conflicts, disjoint
file sets. **Measured 2026-08-31: +12.618% tg128 vs production resolved live** (264.53→297.91
tok/s, 20 pairs, 10.6× the calibrated 1.188% floor; pp512 +0.078% = NO CHANGE, floor
uncalibrated), oracle 3/3, inside the pre-committed chain-estimate band [11.2–15.3] → the
lineages are **additive, no interaction**. `270b48ed` is an *ancestor* — its work is IN the
current champion. The +28–48% Qwen3.8-27B serving-path evidence remains operator-gated (CH-13)
with no promotion authority. The loop-side per-commit history remains inflated — read **CH-16**
before quoting anything from the old branch's commit messages. Enforcement: single-champion
startup refusal (research `470378a9`) — the loop refuses to start off the canonical branch; run
21 runs attached to it at `a2728701`.

**STANDING UPDATED 2026-09-03 — the champion has advanced to `732389d6`, and its standing is
THREE measured workloads, not one number.** The paragraph above records `a2728701`; run 23 then
added three keeps (`7d2ea88b` MMVQ crossover, `db18f393` fattn eight-wave VKQ, `732389d6` Q4_K
weight-block hoist), all ancestors of the current tip. Measured against frozen production-v9,
resolved live:

| workload | surface | result | evidence |
|---|---|---|---|
| `gemma-4-26B-A4B-it-Q4_K_M` (**in-fleet worker**) | dec-b4 | **+7.206% DECISIVE** (174.26→186.76 t/s, 20 pairs, floor 0.456% — 15.8× it) | `champion-vs-production.732389d6d9d0.gemma-4-26B-A4B-it-Q4_K_M.json` |
| `Qwen3.8-27B-Q8_0` (production) | dec-b4 (prefill) | **−1.414% DECISIVE** (66.09→65.00 t/s, 20 pairs, floor 0.949%) | `champion-vs-production.732389d6d9d0.json` |
| `Qwen3.8-27B-Q8_0` | speculative decode | **2.38× with DFlash2** (acceptance 0.6501) | `boundary-20260901/dflash2-smoke/verdict.json` |

**Reading it.** The two decisive numbers point OPPOSITE directions and both are correct: the Q4_K
keeps are hard-gated on `GGML_TYPE_Q4_K` and therefore fire on the worker and are inert on the
Q8_0 production model, where the residual −1.4% is the aggregate's DFlash2/feature machinery
measured on a prefill-only surface that cannot observe DFlash2's own 2.38× decode win. A single
champion-vs-production headline cannot express this (INF-66 R23-26); quoting one without naming
its workload is the defect that made the +27.363% screen-rung number misleading (R23-19).

**Not superseded, still true:** the +12.618% tg128 standing above was measured on `a2728701` and
has NOT been re-measured on the current tip — treat it as the last known value for that surface,
not as the current champion's tg128 standing.

## The finding that reframes this

**`champion.py` already implements composition, not best-of.** `compatible_groups` is documented as
*"Deterministic **maximal compatible sets**; no ranking and no gain inspection"*, and the module
contract is *"member results are never combined into a new result… Member performance fields are not
read anywhere in this module."* The composed tree is rebuilt and re-measured **as a whole** and must
earn its own T0/T1/T2 against the anchor; it even names a branch, `ak/champion/<tree>-<anchor12>`.

So the design is right and matches the requirement. Three things are wrong with the reality:

1. **It has never run.** `champion.py` is reachable only from `release/closeout.py` and
   `release/live_material.py`, never from the discovery controller. Dashboard funnel:
   `{candidate: 38, champion: 0, promotable: 0, strict_keep: 1}`.
2. **Nothing makes it always-exist.** Composition is an end-of-campaign release action, not a
   standing invariant.
3. **Discovery screens against the frozen anchor, not the champion**, so gains cannot compound.

## What may and may not go in — measured, not assumed

Audited 2026-08-27. Only **two** unpromoted items are real llama.cpp source diffs, and both fork off
v9 (`0db32c06e`) exactly:

| Arm | Branch | Size | ggml? | Status |
|---|---|---|---|---|
| MoE-Spec (`moe_spec_budget`) | `inf40-moespec-v9` @ `c7c37a0d9` | 8 files, ~81 LOC | none | flag-gated **default 0**; strongest genuine arm |
| DFlash2 block drafter | `ak/dflash2-qwen38-20260820` @ `2046c64e9` | 20 files | none | **ADMIT (operator, 2026-08-27)**: a PARALLEL spec-decode capability, not an MTP replacement — see the ruling below |

**Verified independently: their file sets overlap in exactly one file — `src/llama-context.cpp` —
and neither touches `ggml/`.** Composition is mechanically near-trivial.

Everything else on the intuitive list is a different class and must NOT be composed as a diff:

- **Already in v9**: `GGML_IQK` (since v8), MMQ `a6b4b5263`, HIP graphs (upstream default ON).
- **Build/runtime configuration**, not source: `GGML_HIP_MMQ_MFMA` (+26.6% prefill), `ubatch`
  512→1024 (+46.9%), `-fa` (+4.9%), `GGML_IQK`. These belong in the candidate's **build recipe**,
  which `champion.py` does not currently model — a real gap.
- **Retracted**: ngram 2.8× (warm-context self-copy artifact; corrected to −0.0%/+0.2%/+1.7% CPU and
  **−17.4%** on 122B-IQ2 GPU).
- **Unexploited source residue**: iqk `IQ1_S`/`IQ1_M` are vendored (`iqk_gemm_1bit.cpp`) but omitted
  from CMake, audited clean 2026-07-29, never staged; `iqk_flash_attn.cpp` present, not built.

**Do not seed the champion from the dashboard's 44 rows.** 43 are screening-only `promotion_claim:
false` observations with `"SEARCH RECORD, NOT A CLAIM"` receipts, and the single `strict_keep`
(+28.86% `GGML_IQK` prefill) is a positive-control canary re-measuring a feature already frozen into
production. Banking those would launder observations into a champion — the exact failure the
apparatus exists to prevent — and would destroy the comparability of every later result.

## Tasks

- [x] **CH-1 — Seed Champion₀ = frozen v9 plus an explicit build recipe.** ✅ 2026-08-30. Both
  halves now exist. The *seed* half landed with CH-2 (research `38bbd045`,
  `_seed_champion_if_absent()` at campaign start, citing the ratified production digests). The
  *build recipe* half — the part this task named as genuinely new ("the build-recipe carrier
  (config arms) is a separate field the champion record does not model yet") — landed as **D3**,
  research `6cbb608c` + `3ba4339f`: a champion now carries a build recipe.
  **Neither standing config win was adopted**, per CH-6, and both are recorded *in the recipe with
  the numbers that correct them*, so the carrier ships its own refutations instead of inviting a
  re-run. Decision-arithmetic floor raised 101 → 109.
  One constant in that recipe module is now contradicted by measurement —
  `build_recipe.py:43`'s `PRODUCTION_RECIPE_IS_VERIFIABLE = False`; see CH-15 and INF-66 R18-A.
- [x] **CH-2 — Make "a champion always exists" an invariant**, re-seeded from production on every
  promotion, rather than an end-of-campaign action. ✅ 2026-08-28 (research `38bbd045`).
  `_seed_champion_if_absent()` runs once at campaign start, before any iteration. The gap it closes
  was concrete: `seed_champion()` had **no production caller at all** — it was reachable only from
  its own unit test — so early in a campaign there was simply no aggregate to screen against.

  The seed cites the **ratified** production digests from `scripts/session/verify_llama_cpp.sh`
  (both verified against the on-disk binaries), because `champion_seed` refuses a mismatch and
  anchoring Champion₀ on an unratified build would silently re-anchor every later comparison. It is
  idempotent on resume (so it can never displace a champion composition has advanced), skipped
  rather than fatal when no production tree is configured, and skipped on dry runs, which promise
  no durable side effects.

  Five tests, **mutation-tested three ways** — seed never runs / ratified digests ignored /
  idempotence removed — each mutation failing exactly the test that should catch it.

  **It also uncovered and fixed a live bug in the earlier inflight-discard change.** That block set
  `precompute_refused` and then *fell through* to the `recovery.status == "sealed_result"` test, so
  on the very path it was written for — the adapter returning a non-`Recovery` — it dereferenced
  `None.status`. The restart-loop fix would have become an `AttributeError` crash on the first
  unreconcilable inflight, and with restarts now permitted, a crash loop again. Found by probing
  two red blackbox tests instead of assuming they were merely stale; whole-suite failure **sets**
  were diffed against `origin/main` rather than compared by count (2 fixed, 0 newly broken).
- [x] **CH-3 — Screen against the champion** (SOLE baseline; settled by operator 2026-08-27) so
  gains compound. Production stays the promotion reference via the mandatory re-validation of the
  composed champion against the anchor at composition time. ✅ 2026-08-27 — no controller change was
  needed: the anchor arm has always been built from the instrument, and `_verify_instrument` only
  requires a descendant of the frozen production head. Instrument re-pinned to
  `ak/champion/llama-cpp-0db32c06e3e5` @ `5c278648a` (research `a086c95a`).
- [x] **CH-4 — Compose MoE-Spec as the first real arm** (`c7c37a0d9`). ✅ 2026-08-28
  (research `f54e5262`, harness `scripts/benchmark/champion_anchor_validation.py`, artifacts
  `artifacts-df25/champion_anchor_20260828/`).

  **Wording discipline: this is NOT "the champion passed T0/T1/T2".** `champion.py` records those
  from campaign tier *events*, which only a full campaign produces. What ran is the set of
  measurements those tiers stand for, against the same sealed anchor:

  | check | result |
  |---|---|
  | T0-equivalent — `test-backend-ops -o MUL_MAT` | 2/2 backends passed |
  | T0-equivalent — `test-backend-ops -o MUL_MAT_ID` | 2/2 backends passed |
  | T0-equivalent — `test-backend-ops -o FLASH_ATTN_EXT` | 2/2 backends passed |
  | T1/T2-equivalent — Qwen3.8-27B pp512 vs anchor | 748.34 → 768.83 (**+2.74%**) |
  | T1/T2-equivalent — Qwen3.8-27B tg128 vs anchor | 28.21 → 28.20 (**−0.02%**) |

  Sample ranges overlap heavily on both surfaces, so the honest reading is **no regression**, not a
  prefill win — which is exactly what should happen, since MoE-Spec is inert at budget 0 and
  DFlash2 only activates on `--spec-type`. The FA result also independently confirms the rocWMMA
  path is numerically sound, which is the defect CH-8 was raised over.

  **MoE-Spec has NOT earned its keep.** At `budget=32` on the production model it measures
  **−2.92% on pp512** — a regression, not a win. The `tg128` row (−0.06%) is uninformative **by
  construction** and is reported as such: batch-1 decode never reaches `--moe-spec-min-batch 4`, so
  that arm executed identical code. This does not so much contradict the original n=3 evidence as
  fail to reproduce it on the surface that matters, and that evidence was already below
  `MEASUREMENT_POLICY.md:37`'s ≥5 reps for a ≥5% claim with the 5-rep confirm declined. MoE-Spec
  stays in the champion as a **capability defaulting to 0**, enabled nowhere. Re-open only with a
  surface and budget where it demonstrably wins.
- [x] **CH-5 — Run DF2-5 (np=8 concurrency) and DF2-6 (exact greedy parity), then admit DFlash2 as
  a parallel spec-decode capability.** Approved by the operator 2026-08-27. ✅ 2026-08-28 — both
  gates run against the champion. Full detail in
  [`dflash2-block-drafter-experimental-build.md`](dflash2-block-drafter-experimental-build.md).

  **DF2-5 PASS.** 24/24 cells, 192 per-slot rows, zero refusals. DFlash2 beats MTP at every
  concurrency — +28.4% / +48.9% / +47.0% / +47.8% at 1/2/4/8 in-flight (kv-unified off). **The
  #27117 concurrency phenomenon does not reproduce on gfx90a**: per-slot acceptance is flat across
  the sweep (DFlash2 0.62→0.66, MTP 0.47→0.50) with no degradation at 8, where every upstream
  report places onset. Throughput alone could not have shown that; it needed the per-slot parsing.
  Replicates DF2-4 at np=1 almost exactly (70.0 t/s, acceptance 0.6205 vs 0.62049) on a different
  binary and a rewritten harness. The paired `--kv-unified` control came back **negative** —
  slightly worse at c4 (142.7 vs 153.6) — which retires the leading root-cause hypothesis for free,
  exactly as the gate predicted a negative would.

  **DF2-6: DFlash2 is NOT bit-exact, and that is NOT a DFlash2 defect.** Per-prompt verdicts:
  dflash2 7 PASS / 5 FAIL, **draft_simple 7 PASS / 5 FAIL**, ngram_simple 11 PASS / 1 FAIL,
  baseline negative control clean (drafted nothing). The controls carry the whole conclusion:
  `draft-simple` contains **no DFlash code at all** yet diverges at the same rate and at three
  *identical* first-differing token indices (34, 216, 238). Two unrelated drafters diverging at the
  same token positions locates the divergence in the shared speculative-verify path, reproducing
  upstream #27407. ngram, through the same multi-token verify path, diverges 1/12 rather than 5/12
  — consistent with #25618 and pointing at the external-drafter verify path specifically.
  Consequence: DFlash2's losslessness claim fails bit-exactness, but it is **no worse than the
  generic speculative path**, so this is not a reason to withhold it.
- [x] **CH-7 — Build the manual→champion admission pipeline.** A documented, repeatable path to
  admit an externally developed source arm (branch + evidence manifest) as a champion MEMBER, with
  the composed candidate rebuilt and re-measured. This is the reusable mechanism for all future
  manual inference research, not a one-off for MoE-Spec and DFlash2. ✅ 2026-08-27 — exercised on
  both manual arms; DFlash2 is preserved rather than rediscovered, which was the operator's
  explicit requirement. The path is: external branch → merge onto the current champion → build with
  the house flags (**including `GGML_HIP_ROCWMMA_FATTN=ON`, see CH-8**) → gates → re-pin the
  instrument. See *The champion as built* below.

  One design note worth carrying: MoE-Spec and DFlash2 both touch `src/llama-context.cpp`, and
  `compatibility()` conservatively treats any two arms touching the same file as an explicit
  conflict — so as separate members they could **never** have composed. Synthesised into a single
  arm they compose trivially, and the combination earns its gates as a unit, so interactions get
  measured rather than assumed.

  **Correction, 2026-08-28: this was closed one half short.** CH-7 was ticked on 2026-08-27 for the
  *admission* pipeline alone, and the closure was reported to the operator as the manual-research
  loop being available. It was not. The operator's requirement is the full loop — *do manual
  research → update the champion → **see its standing*** — and the attestation half did not exist,
  so manually gated evidence stayed invisible on the surface that reports champion standing. The
  gap was then filed as CH-13 rather than built, across four repeated asks. Both halves exist as of
  2026-08-28; **CH-7 alone does not constitute the loop and must not be cited as such** — cite
  CH-7 + CH-13 together, or CH-14's runbook once written.
- [x] **CH-6 — the config leaders. SETTLED 2026-08-28: neither belongs in the champion.** ✅
  Both were investigated to a conclusion; the earlier framing ("the highest-EV unexploited leads…
  settleable in hours") is **withdrawn**. One was never a lead; the other is real but buys nothing
  where the fleet runs. Measured results below; harness `scripts/benchmark/mmq_mfma_recheck.py`
  (research `46de4e1e`), artifacts `artifacts-df25/mmq_recheck_20260828/`.

  | surface | OFF vs ON |
  |---|---|
  | Qwen2.5-Coder-0.5B-Q4_K_M pp512 (the original surface) | **+23.09%** |
  | Qwen3.8-27B-Q8_0 pp512 (production model) | **+0.50%** |
  | Qwen3.8-27B-Q8_0 tg128 | **−0.28%** |

  The +26.6% **replicates** where it was taken (+23.1% here) and **vanishes** on the production
  model — precisely what the recorded counter-argument predicted, since pp512 single-stream is the
  regime where MFMA has least to offer. **Do not adopt `MMQ_MFMA=OFF` into the champion's build
  recipe.** The re-run fixed the original design: arms ALTERNATED rather than block-sequential (so
  drift hits both arms equally instead of loading onto one), n=6 pairs instead of 3 single-rep
  observations, full sample vectors printed rather than medians alone, and an automatic max/min >
  1.3× spread check — which fired once, on a cold first sample, and does not change the conclusion.

  Original detail retained below.
  - **`ubatch 512→1024` (+46.9%) is a NULL ARM — do not re-run it.** llama.cpp clamps
    `n_ubatch = min(n_batch, n_ubatch)` (`src/llama-context.cpp:265`), and the screen passed
    `-b 512 -ub 1024`, so **both arms ran at an effective ubatch of 512 on one identical binary**.
    The +46.9% is a bimodal sample (`25409, 18083, 25372, 16175, 25381`) whose median landed on the
    fast mode, measured against an anchor bank ~30% below the independently established steady state
    (AK-BH-2, n=30: 24647 t/s vs this screen's 17275 anchor). Its `batch_up` sibling, equally null,
    reported +0.59% purely by landing on the other mode — two null arms 46pp apart. The "sign
    conflicts and 53.5pp spread" that made this look like a live lead were the artifact, not a
    signal. A guard now refuses this class at the producer (`run_autokernel_gpu_discovery.py`,
    research `c84ecdb7`), mutation-tested to fire on `ubatch_up` and stay silent on `ubatch`-down,
    `batch`, `batch_up`, `poll_zero` and `mmap`.
  - **`MMQ_MFMA ON→OFF` (+26.6%) is real** for `Qwen2.5-Coder-0.5B-Q4_K_M @ pp512, np=1, gfx90a`,
    independently reproduced at n=30 (+26.81%). But it is a **build-time** flag: `champion.py`
    requires source evidence for every member, so it cannot be constructed as one, and
    `discovery_static_registry` accepts no CMake flag from planner output. Re-run it as a
    build-config A/B on the champion, and note the open question is not the 0.5B pp512 number but
    whether it survives a real model at `-np > 1` — the champion's own state file records MMQ
    forcing *inverting* on MoE workloads (B2 −30%, B4 −21%, B8 −10.5%).
- [ ] **CH-8 (new, 2026-08-27) — AutoKernel's GPU builder omits the house flash-attention flag.**
  `discovery_deployment_factory.py:2052` passes only `GGML_HIP=ON`, `AMDGPU_TARGETS=gfx90a`,
  `GGML_NATIVE=OFF`, so every AutoKernel GPU candidate is built with `GGML_HIP_ROCWMMA_FATTN`
  **OFF** while production, the AK-BH factorial builds and the standalone DF2 build are all ON.
  Consequences: candidates are measured on a different flash-attention kernel than production runs,
  which undercuts transferability of any GPU result; and the OFF path is the one measured below to
  produce non-finite values at longer sequences under `-fa on`.
  **RULED 2026-08-28, and done.** Operator: *"if it leads to better performance finds, I don't care
  if it breaks comparability with prior GPU screens. We only added the GPU recently anyways."*
  Prior GPU screens are therefore **superseded, not reconciled** — they were taken on a kernel
  configuration production does not run. Two flags changed in
  `discovery_deployment_factory.py` (research `71db62e9`):

  | flag | was | now |
  |---|---|---|
  | `GGML_HIP_ROCWMMA_FATTN` | unset → CMake default **OFF** | **ON** |
  | `GGML_NATIVE` | explicitly **OFF** | **ON** |

  `GGML_NATIVE` was ruled the same way and for the same reason: every reference build on this host
  is ON, and matching production is what makes a find transferable. It is the portability trade
  taken deliberately — OFF is what a portable build wants, and this is a single-host program.
  Verified by mutation test that both survive `_sealed_cmake_defines()` rather than being dropped
  as unknown keys (only the RPATH keys are force-overridden there), and confirmed present in the
  live v33 execution closure.

  The repo README gained a *"Build configuration — read this before forking or reproducing"*
  section at the operator's request, recording which flags are host-specific and why, so a fork
  knows these numbers hold for this hardware and these flags and that reproducing them elsewhere
  means re-measuring rather than re-reading.

  Scope discipline, unchanged: the non-finite behaviour was observed in the DFlash
  **target-feature** path; whether plain non-speculative decode also degrades at length on an OFF
  build is **not measured** and is not asserted.
- [x] **CH-9 — the MMQ route instrument. RESOLVED 2026-08-28, and MY FIRST DIAGNOSIS WAS WRONG.** ✅

  **What I originally wrote here — that `ggml_cuda_log_mul_mat_route` is never called from
  `ggml_cuda_mul_mat_id`, so MoE expert matmuls are invisible — was true but was NOT why DF2-6
  captured nothing.** I instrumented `mul_mat_id`, rebuilt, and the log was *still* empty. So was a
  level-2 build that logs every type. The actual cause is that **common's log callback filters
  backend `GGML_LOG_INFO` at the default verbosity**; `ggml_cuda_init` is visible only because it
  logs during backend registration, before that callback is installed. `--verbose` yields **4705
  route lines from a single 24-token generation**. The operative fix was a runtime flag, not a code
  change. Recorded because the wrong root cause was published first.

  Two code changes were kept anyway, on their own merits (champion `270b48ed6`): `mul_mat_id`
  route logging, since MoE routes genuinely were uninstrumented; and a verbosity **level**, so that
  an empty log is no longer ambiguous between "nothing was routed" and "the instrument never
  fired" — the exact ambiguity that made this expensive to diagnose.

  **The deployment gate then refused an over-reach, correctly.** The first attempt also edited
  `ggml/src/ggml-cuda/mmvq.cu`, and validation failed with `production/instrument reviewed target
  differs`. `_TARGET_SOURCE_SHA256` pins files that must be byte-identical between frozen
  production and the instrument, because those are the files the planner is allowed to **mutate**;
  an instrument that pre-modifies a mutation target corrupts attribution at the root. The mmvq.cu
  edit was reverted (digest back to the pinned value) and only `ggml-cuda.cu`, which is not a
  mutation target, remains.

  **The evidence DF2-6 mandated is now captured**, per arm (24-token probe):

  | arm | routes | Q8_0 decisions |
  |---|---|---|
  | baseline (`none`) | MMQ 1984 / MMVQ 581 | ne11=1 → mmvq; 2,4,7 → mmq |
  | dflash2 | MMQ 4687 / MMVQ 3 | ne11=1 → mmvq; 2,4,5,7,8 → mmq |
  | draft_simple | MMQ 13595 / MMVQ 759 | ne11=1 → mmvq; 2…9 → mmq |
  | ngram_simple | MMQ 1984 / MMVQ 581 | identical to baseline |

  This is `a6b4b5263`'s rule (`Q8_0: ne11 <= 1`) firing exactly as written: **every speculative
  verify batch takes MMQ while greedy decode takes MMVQ.** Since that patch is "numerically-valid
  (not bit-exact)" by its own commit message, it is now a **directly evidenced** candidate cause of
  DF2-6's non-parity rather than a speculative one.

## The champion as built — 2026-08-27

`ak/champion/llama-cpp-0db32c06e3e5` @ `5c278648a4af2735587b4023613310ccf2341f46` — 35 files,
+3371/−146 over frozen v9, both merges clean, `llama-server` version 10139:

```
5bbcc5498  reviewed measurement instrument (correctness oracle, llama-bench, iqk sources)
 + c7c37a0d9  MoE-Spec  — per-batch top-B expert budget, --moe-spec-budget, default 0 (inert)
 + 2046c64e9  DFlash2   — block-diffusion drafter, a parallel --spec-type pathway
= 5c278648a  the champion
```

It exposes **both** `--moe-spec-budget` and `--spec-type draft-dflash` alongside `draft-mtp`, and it
loads the DFlash2 GGUF that frozen v9 refuses (`wrong number of tensors; expected 81, got 58`).

**The champion must be built ON the reviewed instrument.** A first attempt (`fdc56acb3`) was
synthesised onto raw v9 and was refused by `_instrument_review_receipt`. That refusal was correct:
it had dropped the measurement apparatus, so every screen would have run on a baseline missing its
own instruments. Exactly one pinned measurement blob changed in the rebuild — `llama-bench.cpp`
(MoE-Spec's 8-line env-var fallback for a flag that defaults to 0). `test-backend-ops.cpp`, the
correctness oracle that decides verdicts, is **unchanged**.

### The build flag that is not optional

`GGML_HIP_ROCWMMA_FATTN` **defaults to OFF** (`ggml/CMakeLists.txt:219`). On gfx90a with `-fa on`
the non-rocWMMA flash-attention path produces **non-finite values at longer sequence lengths**.
Measured on the champion built with it OFF: every one of the 12 pinned olympiadbench prompts failed
on task 0 —

```
E process: rejecting DFlash batch after 3020800/3020800 non-finite target features (limit=16)
E srv  decode: failed to process speculative batch
```

— while a 25-character prompt succeeded on the same binary. **Prompt length is the discriminator**,
which is why a short smoke test passes and hides it.

Attribution was verified rather than assumed. The first hypothesis — that merging MoE-Spec into
DFlash2 broke it — was **wrong**: the standalone DFlash2 build `2046c64e9` ran the identical prompts
and flags at 46.1 / 69.4 / 58.9 t/s with zero non-finite errors, and
`git diff 2046c64e9 5c278648a -- src/ common/` is **+67 insertions, 0 deletions**, so DFlash's
source is byte-identical between them. Rebuilt with the flag ON: all prompts pass, zero errors.
MoE-Spec is separately exonerated — it is guarded by `moe_spec_budget > 0` (`llama-graph.cpp:1985`)
and defaults to 0, so the champion carries the capability, not the behaviour.

Had the gates not been run before relaunching discovery, AutoKernel would have spent days screening
against a reference that fails on every real prompt.

## Why this is safe

Production is FROZEN (`production-consolidated-v9` @ `0db32c06`, branch pattern pinned in
`human_only_paths.yaml`, `on_pin_mismatch: refuse`); AutoKernel builds only in throwaway worktrees
off `llama.cpp-experimental`; every discovery receipt is `promotion_claim: false` by construction.
Per the 2026-08-27 ruling ([`ruling_op19_e8_chain_20260827.json`](../../artifacts/operator/ruling_op19_e8_chain_20260827.json)),
gates bind at the PROMOTION boundary, not at discovery.

## Operator rulings — 2026-08-27

These settle the open questions in this handoff. Recorded here because they change what the
champion is *for*.

1. **AutoKernel is NOT responsible for promoting kernels to production.** It runs with minimal
   friction. Every promotion gate is operator approval at promotion time, *outside* AutoKernel.
   The champion is a standing, ready-to-test aggregate — not a release process.

2. **CH-3 settled: SOLE-CHAMPION screening.** Dual-arm is unnecessary. If Champion₀ = production and
   every step is measured better than the previous champion, each champion is by construction better
   than production. The drift risk is real — v29 and v31 both produced S1 positives (+4.89%, +5.37%)
   that flipped negative on replication — and it is caught by the mandatory re-validation of the
   COMPOSED champion against the production anchor at composition time, which `champion.py` already
   requires. That re-validation is not optional.

3. **DFlash2 is a PARALLEL spec-decode pathway, and the kernel must SUPPORT it.** Correcting an
   earlier mischaracterisation in this file: "`--spec-type` takes one value" binds a single *server
   instance*, not the kernel. Roles run separate servers, so one kernel supporting both spec types
   serves MTP for most of the stack and DFlash2 for Qwen3.8-27B at the same time. DFlash2 therefore
   composes as ADDED CAPABILITY, not a mutually-exclusive swap, and the earlier "policy-barred /
   not additive" framing is withdrawn. Not every model has a DFlash2 drafter head; current intent is
   Qwen3.8-27B only, with the rest of the stack staying on MTP. The lean registry compiler is
   adjusted at promotion time to select per role.

4. **Run the DFlash2 gates.** DF2-5 (np=8 concurrency) and DF2-6 (exact greedy parity) are approved
   to run. Note DF2-6 may fail for a reason unrelated to DFlash2: the in-production MMQ patch
   `a6b4b5263` is numerically valid but **not bit-exact**, so a parity failure must be attributed
   before it is charged to DFlash2.

5. **Manual research admits as a MEMBER, never as a claim.** `champion.py`'s contract already
   supports exactly this: "member results are never combined into a new result… a champion can cite
   only a *combined candidate's* passing T0/T1/T2 events against the current sealed production
   anchor." So an externally developed source arm enters as a member and the COMPOSED tree is
   rebuilt and re-measured; its original numbers are never inherited. The earlier caution in this
   file applies ONLY to the 43 config screening rows, which carry no source diff and therefore
   re-enter as build-recipe settings to be re-tested (CH-6), not as banked results.

## CH-1 implementation notes (groundwork done 2026-08-27)

Read of `champion.py` before writing any code:

- **A champion record already exists in empty form.** `_empty_champion(anchor, status=…,
  blocking=…, detail=…)` builds `{member_candidates: [], combined_candidate_id: None,
  last_t0/t1/t2: None, branch: ak/champion/<tree>-<anchor12>, …}` and validates it via
  `schemas.validate_champion`. `record_no_champion()` uses it with
  `status="no_champion", blocking=["NO_GREEN_COMPOSITION"]`.
- **The seed is a DIFFERENT state from `no_champion`.** `no_champion` means "we have nothing";
  Champion₀ means "the aggregate exists and currently equals production". The seed therefore wants
  zero members with an EMPTY blocking list — it is not blocked, it is simply empty.
- **The schema's always-green rule does not obstruct this**: the `blocking_conditions must not be
  empty while status is not 'pass'` check applies to the nested tier events (`last_t0/t1/t2`), and a
  seed has none.
- **BLOCKER, and it is correct-by-design**: `AnchorIdentity` refuses construction with
  `anchor.artifacts must be non-empty, unique, canonically sorted`. Each `AnchorArtifact` needs
  `backend`, `tool`, `binary_sha256`, `linkage_sha256`. So Champion₀ cannot be conjured — it must
  cite the REAL frozen-v9 binary and linkage digests, per backend (CPU and HIP). Those are exactly
  what `scripts/session/verify_llama_cpp.sh` already enforces, so the seeding routine should source
  them from the same place rather than inventing a second truth.
- Consequence for CH-1's shape: a `seed_champion(book, anchor)` entry point, plus a small helper
  that derives the production `AnchorIdentity` (including per-backend artifact digests) from the
  verified frozen tree. The build-recipe carrier (config arms) is a separate field the champion
  record does not model yet — that part is genuinely new.


## 2026-08-28 — the champion card asserted something false, and CH-3 had a second cost

Two consequences of CH-3 ("the instrument IS the champion") surfaced only once the dashboard was
made legible. Both are recorded here because they are properties of the champion model, not of the
dashboard.

**1. The card said "equals production (seeded)" while the champion carried DFlash2 and MoE-Spec.**
It reported the campaign's champion RECORD (seeded from the frozen production anchor
`0db32c06e3e5`) and counted `members` from *this campaign's* banked iteration rows — zero on a
fresh campaign — while the champion KERNEL the campaign screens against is the sealed instrument
pin `270b48ed6`. Two different objects, conflated, asserting the wrong one as fact about work done
the night before. Fixed (epyc-root `42033897`): the card reports the instrument branch/commit and
whether that commit differs from frozen production, which is a commit comparison rather than a
count, so a champion loaded by manual admission reads as loaded from turn zero.

**The aggregate candidate and the champion are ONE object** — the page had drawn two cards that
disagreed with each other. There is now one.

**2. CH-3 was refused in code and killed four campaigns.** The timed-output gates compared the
anchor arm's source commit for equality against the ORIGINAL instrument, so no
champion-instrumented campaign could pass preflight. See **AK-INST-1** in
[`autokernel-restart-and-strip.md`](autokernel-restart-and-strip.md). This is the standing hazard
of the champion-as-instrument design: **anything that pins the instrument by equality breaks the
moment the champion advances**, and the champion advances by design.

- [x] **CH-10 — the champion's dashboard identity is the instrument pin, not the seeded record.**
      ✅ 2026-08-28 (epyc-root `42033897`). Mutation-tested: restoring the "equals production"
      wording fails `test_a_champion_ahead_of_production_is_never_called_equal_to_it`.
- [x] **CH-11 — lane leaders now state why they are not champion members.** ✅ 2026-08-28. The
      hero cards showed bare percentages that read as uncollected gains. Three of the four headline
      leaders cannot be collected at all: `GGML_IQK` is ALREADY IN PRODUCTION (in v9, which the
      champion is built on), `ubatch_size` is REFUTED (the null arm proved on 2026-08-28), and
      `flash_attention` is CONFIG, NOT A MEMBER (a flag; `champion.py` requires source evidence).
      The funnel's own `champion: 0` was already saying this; the leaders simply were not labelled.
- [x] **CH-12 — RETRACTED AND CORRECTED 2026-08-28. The champion DOES have a measured effect vs
      production; what is missing is that evidence in the RECEIPT FORM the dashboard reads.** ✅

      The original wording ("no measured effect vs production yet") was wrong, and the operator was
      right to challenge it. It conflated two different things:

      1. **The v27 cumulative performance receipt** — a specific sealed artifact produced by an
         AutoKernel campaign's cumulative performance operation. That genuinely does not exist, and
         no campaign has reached one (see AK-INST-1 for why: every campaign since the re-pin died at
         preflight).
      2. **The champion's measured effect vs production** — which EXISTS, was gated, and was
         measured this session.

      **What is measured, on the champion, against production:**

      | measurement | result |
      |---|---|
      | `test-backend-ops` MUL_MAT / MUL_MAT_ID / FLASH_ATTN_EXT | 2/2 backends each |
      | default path vs frozen anchor, Qwen3.8-27B pp512 | 748.34 → 768.83 (+2.74%) |
      | default path vs frozen anchor, Qwen3.8-27B tg128 | 28.21 → 28.20 (−0.02%) |
      | **DFlash2 vs MTP, in-flight 1 / 2 / 4 / 8** | **+28.4% / +48.9% / +47.0% / +47.8%** |

      The DFlash2 row IS an effect versus production, not merely versus MTP: **frozen v9 cannot run
      DFlash2 at all** — it rejects the GGUF with `wrong number of tensors; expected 81, got 58` —
      so MTP at 54.5 / 104.9 t/s is production's *ceiling* for this model, and the champion reaches
      70.0 / 155.0. That was measured across a 24-cell grid with a no-drafter attribution arm, per-slot
      acceptance, and a paired `--kv-unified` control, and it replicated a prior independent campaign
      at np=1 to three significant figures.

      So the champion's standing is: **correctness proven, no regression on the default path, and a
      +28–48% measured gain on the Qwen3.8-27B serving path that production cannot reach.**

- [x] **CH-13 (new, 2026-08-28) — manual gate evidence has no path into the receipt surface.** This
      is the real gap CH-12 was groping at. The champion's best evidence (CH-4 validation, the DF2-5
      grid, DF2-6 parity) came from operator-run gates, and the dashboard's aggregate card reads only
      a campaign-produced cumulative performance receipt — so the strongest measured result in the
      program is invisible to the surface that reports champion standing. This is the receipt-side
      twin of CH-7 (the manual→champion *admission* pipeline): admission works, attestation does not.
      ✅ 2026-08-28 — **both halves built** (research `5677cd51`, epyc-root `91da1172`).

      **Write side**: `scripts/benchmark/emit_operator_gate_bundle.py` seals the manual gate
      harnesses' own artifacts into `epyc.autokernel.operator_gate_bundle.v1`. Every gate carries
      its source artifact path AND that artifact's SHA-256, so a claim resolves to the file that
      produced it and a silently edited artifact invalidates the bundle. A gate whose artifact is
      missing is **RECORDED as missing**, never dropped — absence cannot masquerade as a pass.

      **Read side**: `_read_operator_gate_bundle()` in `dashboard/server.py`. Verified live on
      `:8100/api/kernel` this session — bundle SHA `56ceede0f738…`, champion `270b48ed64d6`,
      headline `+48.9% at 2 in-flight vs production's ceiling`, gates PASS / PASS / NOT_BIT_EXACT,
      `gates_missing: []`.

      **The design decision worth carrying.** The cheap fix was to emit a
      `epyc.autokernel.cumulative_performance.v2` — the receipt the card already read. That was
      deliberately NOT done: that schema's authority derives from a chain only a campaign builds,
      so minting one from operator evidence would launder manual measurement into campaign
      authority and poison every later comparison that trusts its provenance. The bundle is a
      separate carrier that declares what it is (`authority: operator_gated_manual_research`,
      `promotion_claim: false`), and the reader **refuses** any bundle claiming more — including
      one wearing the campaign schema. Mutation-tested: deleting the authority check fails
      `test_a_bundle_claiming_campaign_authority_is_refused` and
      `test_a_bundle_claiming_promotion_is_refused`.
- [ ] **CH-14 (new, 2026-08-28) — document the manual-research loop as a runbook.** CH-7 + CH-13
      now compose into a complete loop (research → admit → gate → attest → visible standing), but
      it is only reconstructible by reading two handoffs and three scripts. Write it up in
      `docs/guides/` as the standing procedure, with the authority boundary stated explicitly so a
      future session does not "simplify" it by emitting a campaign receipt.

## 2026-08-30 — the champion finally has a measured effect against production on the DEFAULT path

CH-12 (retracted and corrected on 2026-08-28) established that the champion's measured effect vs
production existed *on the DFlash2 serving path production cannot reach at all*. What did **not**
exist was an effect on the default path beyond "no regression": CH-4's rows were 748.34 → 768.83
pp512 and 28.21 → 28.20 tg128, read honestly as no change.

**That gap is now closed, for the LOOP champion.** Note the two champions are different objects
and must not be conflated: CH-4/CH-12 measured the *manual-admission* champion `5c278648a`
(MoE-Spec + DFlash2); what follows measures the *loop* champion `5ad3e36d` on
`ak/loop-champion-20260828`, 36 commits above frozen v9.

| surface | production `0db32c06` | champion `5ad3e36d` | effect | floor | reading |
|---|---|---|---|---|---|
| **tg128** | 264.918 tok/s | 287.499 tok/s | **+8.524%** | 1.188% (calibrated) | **decisive by 7.2×** |
| **pp512** | — | — | +0.090% | 0.029% (uncalibrated) | **NO CHANGE** |

Both arms built fresh from named commits with the identical recipe · 20 alternating pairs · one
claim held across both surfaces · neither arm drifting · 40/40 resident · clocks pinned 1700 MHz on
all 80 invocations · correctness oracle rc=0, `2/2 backends passed`, on **both** arms. Stored as
`/mnt/raid0/llm/autokernel/loop-memory/champion-vs-production.json`
(`epyc.autokernel.champion_vs_production.v1`), five capability entries each carrying its evidence
path. The pp512 `decisive=True` is a floor artifact — and the changed files predict ~0 prefill
independently, since the 36 commits touch only the matrix-*vector* decode path and FA-vec and
nothing in `mmq.*`.

- [x] **CH-15 — the house recipe reproduces production's frozen build on BOTH backends.**
      ✅ 2026-08-30. Established by comparing *artifacts* rather than flags: production's shipped
      `libggml-cpu.so` vs our fresh v9 build, **584 defined symbols each, zero diff**; production's
      `libggml-hip.so` vs ours, **918 distinct device kernels each, zero symbols unique to either
      side**. This matters here because `champion.py`'s anchor identity and CH-1's build recipe both
      rest on our recipe standing in for production's, which was previously unevidenced.
      Follow-on, filed in INF-66 as **R18-A**: flip `build_recipe.py:43`'s
      `PRODUCTION_RECIPE_IS_VERIFIABLE = False` with this evidence attached.
- [ ] **CH-16 — the loop champion's per-commit claims are inflated 20× and must be corrected where
      a reader of the branch will land.** The 36 commit messages on `ak/loop-champion-20260828`
      claim gains **compounding to +171.7%** (arithmetic sum +101.8%) against a measured block
      effect of **+8.524%** — the same cumulative-attribution defect as run 17's (INF-66 D14) at
      twenty times the magnitude. **No individual percentage on that branch is a marginal effect.**
      Commit messages are immutable, so the correction goes at the tip
      (`NOTES-attribution.md`) and into `loop/program.md`'s *Settled — do not re-open* section.
      Owned by INF-66 as **R18-C**; listed here because this page is where someone comes to ask
      what the champion is worth. **Blocked on run 19 finishing** — `ak-loop-tree` is off limits
      while it runs.

## FOLD — INF-70 CPU kernel work into THE champion (operator request 2026-09-07)

Plan: [`docs/design/inf70-cpu-fold-into-champion-20260907.md`](../../docs/design/inf70-cpu-fold-into-champion-20260907.md).
Same lineage (fork `270b48ed6` on this branch), merge-tree **0 conflicts**; two default-ON blockers on
the CPU side must be fixed first; PROD-2 was operator-deferred 09-06 and today's request reverses it.

- [x] **FOLD-OP — operator decided 2026-09-07** ✅: (a) fold IS wanted — no reversal ceremony needed,
      folding at the right time is fine (NOTE: the CPU work is NOT yet in the champion; it sits on
      `inf70/champion @ 6f032c48d`, forked from this lineage but unmerged); (b) **timing: fold as soon as
      run 29 ends — the operator will stop it to reboot the machine; that reboot boundary is the fold
      trigger.** Do not stop run 29 for the fold; do not hand FOLD-0 to `inf70-audit` yet — this was a
      preliminary investigation for clarity on blockers. Surface FOLD-0 to `inf70-audit` when the
      run-29 / reboot boundary approaches, so the fold-ready commit is prepared in time.
- [ ] **FOLD-0 (`inf70-audit`, own branch)** — *note 2026-09-08: the re-base onto the CPU champion
      (`inf70/champion3` @ `9c4f73e29`) was done by INF-70 inside the fold candidate, so `ef81196d5` already
      carries champion3; the remaining FOLD-0 items below are theirs to close in their own turn*: fold-ready commit on `6f032c48d` — `GGML_OP_MOE_TOPK_NORM`
      opt-in (or CUDA kernel + test-backend-ops case), INF-64 fused decode opt-in, `ggml-alloc.c` stray
      define; re-run greedy bit-identity + `test-backend-ops -b CPU`; record the PROD-2 reversal in the
      INF-70 ledger; **push** `inf70/champion` (private clone today).
- [x] **FOLD-1 (champion owner)** ✅ 2026-09-08: loop stopped at the boundary (verified dead), pre-fold GPU tip
      tagged `ak/pre-fold-gpu-tip-20260908` (pushed), fold candidate `ef81196d5` built at
      `/mnt/raid0/llm/tmp/build-fold-ef81196d5`; `verify_ggml_linkage.sh` PASS.
- [x] **FOLD-2 gates, SAME merged tree** ✅ 2026-09-08 — all PASS with real tallies on `ef81196d5`:
      G1 `test-backend-ops -o SSM_SCAN -b ROCm0` 7/7 OK (incl. K=4/K=3 rollback), G2 MUL_MAT 1140/1140 OK
      (326 unsupported type combos), G3 GATED_DELTA_NET 39/39, G4 dispatch **observed** (`llama-bench -v` +
      `GGML_SCHED_DEBUG=2`: 27,516 nodes, SSM_SCAN=0, SSM_CONV 576 + GATED_DELTA_NET 576 on ROCm0, CPU holds only
      12 GET_ROWS), G5 tg128 vs gen-021 **+0.052%** (20 pairs, floor 0.638%, not decisive). Result file
      `/mnt/raid0/llm/tmp/fold-window-20260908/fold2-result.json`. NOTE: the first G1-G4 run reported PASS with
      **OK=0** (ANSI-coloured verdicts defeated the `\bOK\b` match; `llama-bench` swallowed scheduler logs
      without `-v`) — structural guards added: a gate PASSES only with ≥1 case run AND an agreeing `N/N tests
      passed` tally, and the graph check only with a plausible node count AND the expected recurrent ops present.
- [x] **FOLD-3** ✅ 2026-09-08 — **fast-forward + push, NOT a relaunch** (operator directive: no relaunch):
      `ak/champion/llama-cpp-0db32c06e3e5` `bff30cebe` → **`ef81196d5`** (`--ff-only`, tip == candidate) at
      11:16:49Z, lineage verified (`bff30cebe`, `445e93a8`, `9c4f73e29`, production `0db32c06e` all ancestors),
      worktree clean, pushed to fork `pestopoppa/llama.cpp`. Production branch untouched. Consolidated champion =
      GPU tip (6 unconfirmed keeps) + CPU champion3 `9c4f73e29`. PROD-1 still owes the CPU launch recipe before
      any promotion headline.

### CONSOLIDATION COMPLETE — `ef81196d5`, 2026-09-08

- [x] **FOLD-4 — consolidation is CLOSED; there are no CPU keeps pending** ✅ 2026-09-08. INF-70 reported
      its final RETEST-1 results at ~12:10Z with **no keeps to fold**. The consolidated champion is
      **`ef81196d5`** on `ak/champion/llama-cpp-0db32c06e3e5` = GPU tip `bff30cebe` + CPU champion3
      `9c4f73e29`, FOLD-2 G1–G5 all PASS. The operator's standing condition — *no kernel research until a
      FULLY consolidated champion* — is **satisfied**. Loop relaunch remains a **separate operator go**;
      nothing on this page launches or schedules it.

#### DO-NOT-FOLD ledger — branches that exist on the CPU lineage and must NOT be picked up by a sweep

| branch @ commit | disposition | why | condition if ever folded |
|---|---|---|---|
| `inf70/sync17-fix2` @ `2516c9807` | **DO NOT FOLD — CLAIM, and the claim is a REGRESSION** | **−2.136%** (ratio 0.9786, CI [0.9771, 0.9804], p=0.0286, n=4v4 in one hot session, 24/24 outputs byte-identical). Both knobs default **ON** on that branch, **and that default IS the regression**. | If ever folded, **both knobs must flip default OFF**. Its value is as an **instrument**, not a keep. |

**Why this negative is admissible where SYNC-19's was not.** The `P` arm is a *directional positive
control*: the knob demonstrably reaches dispatch, confirmed by per-arm server knob readback. Decomposition
of the −2.136%: **C→P (FIX-3's yield alone) −1.883%**; **P→F (column split alone) −0.258%**. The tiny-solo
run was the better choice — the same barrier arithmetic that refuted `inf10-gemv-fusion`. SYNC-19's model
predicted **+3.31%**; the sign is wrong.

- [x] **CHAMP-2 (THP) — RESOLVED 2026-09-08: KEEP, 6/6 pairs ON-faster, early stop at the FIRST look.** ✅ 2026-09-08
      Prior state: +3.458%, **NON-CLAIM** (p=0.143, CI [0.9962, 1.0632]); the hypothesis that VEC_Q8K/QSPLIT had
      already removed its traffic is **contradicted** — the estimate is positive and *larger* than the +1.0% it
      supposedly lost.
      **CORRECTION OF RECORD (2026-09-08).** The operator did **NOT** cancel this test — the CPU session (INF-70)
      had it backwards. INF-70 **registered the test at 14:08:05Z** and it is running:

      | element | value |
      |---|---|
      | design | alternating ON/OFF launches, **session** as the unit |
      | looks | two only — **6/6 after 6 pairs**, or **≥9/10 after 10 pairs** |
      | α (exact, two-sided) | **0.0430** |
      | cap | **10 pairs ≈ 1.27 h**; hard cap **14** with replacements |
      | ≥9/10 ON faster | **KEEP**, staged as a lane off `ef81196d5` |
      | ≥9/10 OFF faster | **no keep** |
      | otherwise | **CANNOT TELL** — no keep, no default flipped |

      Verdicts are **pre-fixed**; do not renegotiate them after the looks. Read a **CANNOT TELL** against
      **R23-57** (champion launch-to-launch instability, ~12% spread on an identical configuration) before
      concluding the effect is weak. Still: do not fold it and do not retire it as refuted.

      **VERDICT (INF-70, 2026-09-08 ~14:55Z).** 6/6 ON-faster, early-stop boundary fired at the first look,
      exact two-sided α = 0.0430, order-balanced 3/3, all 12 sessions passed both screens and the fail-closed
      `THP_enabled` assertion, no pair dropped. Median **+5.23%** (range +0.32% to +5.93%) — **magnitude NOT
      claimed**; the design sized for direction only.

      **THE KEEP IS A LAUNCH-RECIPE CHANGE, NOT A KERNEL CHANGE — there was nothing to fold.** The shim's code
      is already in `ef81196d5`; the keep is the env var `GGML_NOHUGEPAGE_PROCESS=1` (`prctl(PR_SET_THP_DISABLE)`
      taken before the 92 GB allocation) **set at launch**. Default in `ef81196d5` today is **OFF (opt-in)**;
      INF-70's recommendation is **ON**, taken to the operator as a recipe change. No branch, no rebuild, no
      merge-tree, no FOLD-2, champion binary bit-identical, trivially reversible. **Do not conflate it with
      `GGML_NOHUGEPAGE`** (the madvise, already on) — different mechanisms, opposite-sounding names. A code
      default-flip is the alternative and was **not** measured (it would need its own build, `THP_enabled`
      verification and a correctness gate).

      **Unit: SESSION.** Evidence is 6 paired launches; the floor is between-launch (2.510% OFF / 0.481% ON).
      The arm floor (0.171-0.501%) does not transfer — that substitution is the 4-vs-4,780 error (R23-55). The
      shim cannot be switched between arms in a live process, so a per-arm number for it is meaningless by
      construction.

      **ADOPTED 2026-09-08 (operator ruling, relayed by INF-70: "we should totally adopt it").**
      `GGML_NOHUGEPAGE_PROCESS=1` is now part of the **canonical launch recipe** for the champion, set at
      launch, session unit. **The champion artifact is `ef81196d5` + shim ON** — a commit hash alone no
      longer identifies it, and the first thing to force that was a recipe change rather than a code change
      (the worked instance for R23-59 / INF-73 U3, adopted and in use rather than hypothetical). No fold, no
      branch, no FOLD-2, binary bit-identical. Spell BOTH knobs out wherever this is cited: adopted
      `GGML_NOHUGEPAGE_PROCESS` (prctl, at launch) vs pre-existing `GGML_NOHUGEPAGE` (madvise) — the names
      are close enough to be transcribed wrong, which is exactly the PROD-1 failure mode.
      **The stronger claim than the speedup:** the 9-launch spread table was measured shim-OFF, the
      configuration now retired, so it is the *before* picture — the adopted change bought **precision as
      well as throughput** (25.3x variance reduction), and precision is what makes every later measurement
      cheaper on a shared host. INF-70's final characterisation is re-running with the shim ON, sized from
      the ON sd (0.481%) rather than OFF's (2.510%), which is what makes a +/-1% headline affordable at all.
      Tracked as INF-73 U3-SEED / U3-DEFAULTS; GPU-side transfer test is R23-58.

      #### ⚠ THE ADOPTION IS **CPU-ONLY**. R23-58 SETTLED THE GPU SIDE, AND THE ANSWER IS NO.

      **Read this before quoting the champion recipe anywhere.** The GPU-side transfer test **ran on 2026-09-08
      and returned a BOUNDED NULL** (T0/D0; 48 launches / 24 couples; `p95_dev` ratio OFF/ON 0.713, p = 0.3159;
      5/10 ON faster). The ON arm was if anything slightly **WIDER**. Full verdict and evidence:
      `autokernel-rebuild-program.md` → R23-58.

      | surface | `GGML_NOHUGEPAGE_PROCESS=1` | authority |
      |---|---|---|
      | **CPU decode** (canonical launch recipe) | **ON — ADOPTED** | operator ruling 2026-09-08, CHAMP-2, 6/6 pairs, session unit, direction only |
      | **GPU serving** (`qwen3.8-27b-q8-gpu-dflash2-np4`) | **NOT SET — DO NOT ADD** | R23-58, bounded null, registered action "do not adopt" |

      > **The champion artifact is `ef81196d5` + `GGML_NOHUGEPAGE_PROCESS=1` ON THE CPU DECODE PATH.**
      > On the GPU serving path the shim is measured null and is **not** part of the recipe.

      **Why the qualifier is load-bearing rather than pedantic.** Without it a reader concludes "the champion runs
      with the shim" and adds a knob to the GPU launch path that buys nothing — **the PROD-1 failure mode
      exactly** (a recipe transcribed by hand cost seven MTP arms to a flag that does not exist). This is also the
      second worked instance of R23-59 / INF-73 U3: the champion is not fully described by a commit, and now not
      even by a commit plus one recipe — **the recipe is PER-SURFACE.** A `champion.py`/`Bundle` record that
      carries one recipe per champion is under-specified by construction.

      **The bounded null is a RESULT, not an absence.** At n=24/arm the test had ~0.97 power against a 3x
      dispersion ratio and ~0.69 against 2x: **a large effect is excluded, a small one is not.** And the mechanism
      demonstrably fired — OFF arm AnonHugePages ~53% of RSS, ON arm 0.0% on every launch, `THP_enabled` read back
      correct in both directions all 48 times. That is what separates it from SYNC-18, which was untestable
      because its knob never reached dispatch.
- [x] **CHAMP-3 — DELIVERED 2026-09-08: the final champion headline is MULTI-LAUNCH with a session-unit CI.** ✅ 2026-09-08
      (R23-57; INF-73 U2). The champion **characterisation was STOPPED mid-run** on operator instruction
      (*"stop measuring the champion. It's not final yet!"*) and is re-run on the **final** champion, after the
      CHAMP-2 THP decision and any fold that follows it.

**Method note inherited from INF-70 (applies to this page's gates).** INF-70's `gate.py` now routes all
statistics through a single `screened()` function — it *cannot* compute over screen-dropped arms and *cannot*
PASS on zero cases — mutation-tested in both directions. This **generalises the ak-rebuild FOLD-2
vacuous-pass guard**: the guard is not a fold-window one-off, it is the shape every gate should have.


      **FINAL NUMBERS (INF-70, 18 launches 15:05:39-16:12:47Z, none dropped, region held; unit = LAUNCH,
      every precision figure between-launch).** Champion = `ef81196d5` + `GGML_NOHUGEPAGE_PROCESS=1`.

      | configuration | n | central t/s | between-launch sd | 95% CI |
      |---|---:|---:|---:|---|
      | champion plain | 6 | **27.893** | 0.609% | +/-0.487% |
      | champion MTP | 6 | **43.281** | 0.356% | +/-0.285% |
      | pristine plain | 3 | 12.762 | 0.360% | +/-0.408% |
      | pristine MTP | 3 | 23.709 | 0.926% | +/-1.048% |

      Ratios: plain **2.1857x** [2.1730, 2.1974], MTP **1.8255x** [1.8081, 1.8399], MTP/plain 1.5516x.
      MTP acceptance 82.1%, identical champion and pristine. **Headline as SIGN claims with bounded
      magnitudes** (95% CI lower ends over launches): the champion is faster than pristine by **at least
      117% plain** and **at least 81% served-MTP**; served-MTP beats plain by **at least 54%**.

      **The variance before/after — the more valuable half:**

      | | launches | between-launch sd | range |
      |---|---:|---:|---:|
      | BEFORE, shim OFF (retired) | 9 | **5.081%** | 12.55% |
      | AFTER, shim ON (adopted) | 6 | **0.609%** | 1.79% |

      **8.3x on sd, ~70x on variance**, corroborated by the paired test's 25.3x. **+/-0.5% precision fell
      from ~25 h to ~23 min.** The ON sd was VERIFIED (0.609% observed against a 0.481% projection) and the
      observed value is what is quoted.

      **TWO CAVEATS THAT MUST TRAVEL WITH THESE NUMBERS.**
      1. **The ratio is recipe-to-recipe, NOT knob-controlled.** Pristine contains neither THP knob (no
         marker, zero occurrences of either env string), so an equal shim state is impossible by
         construction. What IS controlled: same harness, same window, adjacent interleaved launches.
         **This applies to the GPU side too — no champion-vs-pristine ratio this campaign has ever quoted
         was knob-controlled; the THP difference sat inside all of them, unlabelled.** Disposition: LABEL
         the affected cross-lineage ratios, do not re-derive them (the label costs nothing; re-deriving
         costs hours and changes no decision). **Narrower on the GPU side, and checked:** FOLD-2 G5
         (candidate vs `anchor-gen-021`) **stands as measured** — only the candidate's lineage carries the
         knob at all and it defaults OFF, so both arms ran with THP enabled.
      2. **`CHAMPION-DIVERGENCE.md` stays OPEN.** Plain ratio 2.1857x against the standing 1.7151x. Two
         conditions differ at once (shim state, harness/window), so this NARROWS the causes without closing
         them: pristine reproduces across both (12.762 vs 12.366, +3.2%), the champion does not. Adoption
         explains part of the movement and part of the instability; **it is not asserted to explain all of
         it.** Keep R23-57 open on that basis.

      **CPU-side ledger CLOSED 2026-09-08 — fold queue EMPTY, nothing staged, nothing pending.**

      | item | disposition |
      |---|---|
      | champion artifact | `ef81196d5` + `GGML_NOHUGEPAGE_PROCESS=1` at launch |
      | CHAMP-2 THP shim | ADOPTED — recipe change, session unit, direction only, no fold |
      | FIX-1 / FIX-3 | CLAIMED REGRESSION -2.136%; `inf70/sync17-fix2` @ `2516c9807` **DO-NOT-FOLD** |
      | SYNC-18 | untestable as built (knob reaches only `ggml_get_n_tasks()`, which no longer gates execution) |
      | SYNC-16 / SYNC-13 | not reached; no evidence either way |
      | `inf10-gemv-fusion`, `q8-8x8-avx512bw` | measured refutations, record-only |
      | `feature/tree-draft-v6` | **MUST-NOT-FOLD** — champion carries the later contradicting decision |

      **Joint open items, unruled:** INF-70's MEAS-1/OP-40 with our OP-41 (two campaigns, correct pinning
      both sides, each destroying the other's resolution ~3x, plus a ~17% third-party tax from tooling
      neither campaign controls), and the champion divergence above.

---

## CHAMPION MAXIMUM-PERFORMANCE HEADLINE — 2026-09-08 (the postable numbers)

**Canonical, citable artifact: [`docs/design/champion-max-performance-20260908.md`](../../docs/design/champion-max-performance-20260908.md).**
Quote from there; do not re-derive from this summary and do not re-type the recipe.

Champion `ef81196d5` (everything folded), Qwen3.8-27B-Q8_0, MI210 gfx90a, DFlash2 drafter, canonical serving
recipe `qwen3.8-27b-q8-gpu-dflash2-np4` with **only `np` varied**, 3 launches per point, **residency `proven` on
all 12 launches**, peak VRAM 33.1–43.1 GiB, sclk pinned 1700 MHz. Unit: **LAUNCH**.

| slots (`np`) | aggregate tok/s | per slot | p95 dev across 3 launches | runs |
|---:|---:|---:|---:|---|
| 1 | **79.25** | 79.25 | 0.44% | 79.2, 79.2, 79.6 |
| 2 | 109.41 | 54.70 | 1.60% | 109.4, 108.9, 111.2 |
| 4 | 167.76 | 41.94 | 3.33% | 167.8, 162.2, 169.7 |
| 8 | **179.12** | 22.39 | 1.82% | 182.4, 178.2, 179.1 |

> **79.25 tok/s single user · 179.12 tok/s aggregate at peak concurrency.**

- **`np=4` is the operating point.** The curve turns over hard between 4 and 8 slots: **+6.8% aggregate for
  roughly HALF the per-user rate.** np=4 delivers **93.7% of peak aggregate** while each user still sees
  ~42 tok/s. The canonical recipe is already np=4 — this **confirms** the standing choice, it does not change it.
- **Dispersion GROWS with concurrency** (0.44% at np=1 → 3.33% at np=4). A single reading at np=4 is far less
  trustworthy than one at np=1; anything gated at np=4 must state its `n`. Directly relevant to R23-61.

Raw: `/mnt/raid0/llm/tmp/maxperf-20260908/sweep.json` + `sweep.log`; promoted into the research repo (`data/`) at
commit `48a6f6f2`.

- [x] **HEAD-1 — file the maximum-performance sweep as a canonical citable artifact** ✅ 2026-09-08
      (`docs/design/champion-max-performance-20260908.md`; referenced from this page).

## ⚠ THERE IS NO CHAMPION-VS-PRODUCTION RATIO FOR THIS CONFIGURATION, AND THERE NEVER WAS ONE

**Production v9 never ran this lane.** `artifacts/operator/ratify_v9_final_freeze_20260811.json` →
`production_certification` records:

| field | value |
|---|---|
| `qwen36_27b_q8_dflash` | `lane_ineligible_acceptance_below_floor` |
| `dflash_kernel_capability` | `certified` |
| `dflash_lineup_enabled` | **`false`** |

So production was frozen with the DFlash drafter **compiled in but deliberately NOT enabled for the 27B** —
acceptance was below floor at the time. The v9 qualification summary
(`artifacts/operator/v9-qualification-20260810T235723Z-0db32c06e/summary.json` →
`gates.gpu_candidate_functional_observation`) carries GPU decode for **other roles only**: architect native MTP
**53.359** tok/s, coder (request_cap 0, no draft activity) **30.268**, worker vision **96.671** — and that block
is itself stamped `decision_grade: false`.

Three separate reasons the comparison does not exist:

1. **Different model.** The key is `qwen36_27b_q8_dflash` — **Qwen3.6**-27B, not 3.8. Qwen3.8-27B replaced
   Qwen3.6-27B-MTP-Q8_0 in production only on 2026-08-20/21, **nine days after** this freeze.
2. **Different drafter, and the frozen binary cannot load ours.** Frozen v9 **rejects the DFlash2 GGUF outright**
   — `wrong number of tensors; expected 81, got 58`. Production's ceiling for Qwen3.8-27B is **MTP self-draft**,
   not DFlash2.
3. **The lane was disabled on purpose.** `dflash_lineup_enabled: false` is a decision, not an omission.

> **The champion's advantage on this surface is partly a CAPABILITY, not a speed delta.** Anyone quoting a
> champion-vs-production ratio for Qwen3.8-27B + DFlash2 is quoting a number that was never measured, because
> production cannot produce the denominator.

- [ ] **PROD-BASE-1 — if a champion-vs-production headline is ever wanted, measure production AT ITS OWN BEST.**
      Its own `np` sweep, whatever spec configuration it actually supports (MTP self-draft for Qwen3.8-27B),
      under the same host discipline and with residency proven — **never** forcing production through the DFlash2
      recipe, which measures a lane it does not have and would report a capability gap as a speed gap. Until that
      exists, the champion headline stands **alone**, as an absolute number, with no ratio attached. Not blocked
      on anything; not scheduled — it needs the host and an operator go.

## METHODOLOGICAL CAUTION — a BENCH-surface number is not a SERVING number

**Recorded as an error of mine, 2026-09-08.** I quoted the `tg128` llama-bench figures (production 29.4 /
champion 31.0, **+5.63%**) as "single-stream GPU decode". That was wrong.

**`llama-bench` cannot do speculative decoding at all.** `tg128` is therefore a **bench PROXY** for a serving
path that has a drafter in it, and it understates the real single-stream serving rate by **~2.5×**
(**79.25** measured on the recipe vs **31.0** on the bench surface). It also violated the standing rule that
**headline numbers come from the production recipe**.

| surface | valid use | invalid use |
|---|---|---|
| `tg128` / llama-bench | **A/B kernel comparison** — both arms share the surface, so the drafter's absence cancels | **any absolute headline**, any cross-surface ratio, anything the operator would post |
| serving recipe (`serving.calibrate_floor` / the gate) | absolute headlines, operating-point choice, capacity claims | — |

The +5.63% tg128 delta is **not retracted as an A/B** — it remains a valid kernel-vs-kernel comparison on its own
surface. What is retracted is its use as a **rate**. Compiled into the wiki with the R23-58 bounded null.

- [x] **METH-BENCH-1 — the bench-vs-serving distinction is recorded where headlines are formed** ✅ 2026-09-08
      (this page, `docs/design/champion-max-performance-20260908.md`, and the wiki compile).
