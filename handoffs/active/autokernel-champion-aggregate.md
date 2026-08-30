# AutoKernel — the standing aggregate candidate (champion)

**Owner:** operator audit session, 2026-08-27. **Depends on:** INF-06 (campaign), INF-64 (repair track).
**Operator requirement, 2026-08-27:** *"There should ALWAYS be an aggregate production candidate that
holds all the experimented tweaks and is ready for promotion gate testing."* And: AutoKernel screens
against that aggregate, *"attempting to make it better"*, rather than re-deriving deltas against a
fixed production anchor.

## Start here — open work (everything else on this page is closed evidence)

| task | what to do |
|---|---|
| **CH-14** | Write the manual-research loop runbook (admit → gate → attest) in `docs/guides/`, stating the authority boundary explicitly. |
| **CH-16** | Correct the loop champion's inflated per-commit claims at the branch tip and in `program.md` — blocked on run 19 finishing. |
| **CH-4 / CH-6 follow-ons** | See their entries; both are settled to a conclusion, follow-ons only. |
| **not on this page** | `AK-INST-3` (prove a campaign reaches `sci >= 1`), `AK-INST-2`, `AK-DEPLOY-2` live in [`autokernel-restart-and-strip.md`](autokernel-restart-and-strip.md). |

**Two different champions live on this page — do not conflate them.**

1. **The manual-admission champion**, instrument pin `270b48ed64d6`, ahead of frozen production and
   carrying MoE-Spec + DFlash2. Standing as of 2026-08-28: correctness proven, no regression on the
   default path, **+28–48% on the Qwen3.8-27B serving path that production cannot reach at all**.
   That evidence is operator-gated (CH-13) and carries **no promotion authority** — it is not a
   campaign receipt, and no campaign has yet banked one.
2. **The loop champion**, `5ad3e36d` on `ak/loop-champion-20260828`, 36 commits above frozen v9.
   Standing as of 2026-08-30: **+8.524% tg128 vs frozen production, decisive by 7.2×; ~0 on
   pp512** — the first measured default-path gain in the program. See *2026-08-30* below, and read
   **CH-16** before quoting anything from that branch's commit messages.

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
