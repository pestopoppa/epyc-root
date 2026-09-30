# AutoKernel champion aggregate — completed scope through 2026-09-29

> **Historical ledger only; current work lives in [`../active/autokernel-champion-aggregate.md`](../active/autokernel-champion-aggregate.md).**
> Split 2026-09-29 (workspace-8d wrap-up); verbatim from origin/main `2e239c9ca`.

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

  **⚠ ANNOTATED 2026-09-14 (INF-40) — the −2.92% pp512 row is VOID as evidence about MoE-Spec, and
  "fail[ed] to reproduce it on the surface that matters" was structurally impossible.** The arm was
  measured on **Qwen3.8-27B-Q8_0, a DENSE model**: `general.architecture qwen35`, **0 of 866** tensors
  match `*exps*`/`ffn_gate_inp`, and the GGUF carries **no `*.expert_count` key**
  (`model_registry.yaml:1596,1707` also say "dense"). `--moe-spec-budget` masks inside `build_moe_ffn`
  (`src/llama-graph.cpp:1985`, champion `c7c37a0d9`), a subgraph a dense graph never builds, so **both**
  GPU arms ran identical code — the same reasoning that voids `tg128` voids `pp512`, for a *stronger*
  reason (model class, not batch shape). It is also not significant on its own six samples: medians
  768.83 → 746.38 (−2.92%) but means 758.63 ± 27.80 → 745.37 ± 25.07 (**−1.75%, Welch t = −0.87**,
  ranges fully overlapping), so it is usable only as a ±3.7% same-window noise reading for that GPU
  surface. The paired champion-vs-anchor default-path rows (pp512 +2.74%, tg128 −0.02%) remain a valid
  no-regression check on the composed champion diff. The conclusion **MoE-Spec stays at default 0**
  survives; its stated reason does not — the live objection to the CPU +10.7% is its own thinness
  (n=3, Δ ≈ 2.9σ), not a countervailing surface. CH-4 is closed, so this is an annotation, not a
  re-litigation; the operator decision package lives in
  [`moe-spec-cpu-spec-dec-integration.md`](../active/moe-spec-cpu-spec-dec-integration.md).
- [x] **CH-5 — Run DF2-5 (np=8 concurrency) and DF2-6 (exact greedy parity), then admit DFlash2 as
  a parallel spec-decode capability.** Approved by the operator 2026-08-27. ✅ 2026-08-28 — both
  gates run against the champion. Full detail in
  [`dflash2-block-drafter-experimental-build.md`](../active/dflash2-block-drafter-experimental-build.md).

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

  **Correction, 2026-09-26 (research intake intake-1822#record; second reader CONFIRMED): the 27B-Q8_0 pp512 row
  never exercised MMQ-MFMA.** On CDNA2, dense Q8_0 dispatches to MMQ only at ne11 <= 128 (`mmq.cu:296-312`), and
  with `GGML_HIP_NO_MMQ_MFMA` the fall-through is `ne11 < MMQ_DP4A_MAX_BATCH_SIZE` (64). So both arms ran hipBLAS
  for the dense matmuls. The flag also switches MFMA flash-attention selection and MFMA tile primitives, which is
  where any residual +0.50% would come from. CH-6's decision stands (the flag buys nothing where the fleet runs pp512),
  but the stated mechanism ("the regime where MFMA has least to offer") is wrong. An MMQ-MFMA question needs ubatch
  <= 128 (`-ub 128`, pp64/pp128) or an MoE/Q4_0 surface.

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
[`autokernel-restart-and-strip.md`](../active/autokernel-restart-and-strip.md). This is the standing hazard
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

## FOLD → DO-NOT-FOLD ledger section: CHAMP-2, CHAMP-3

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
