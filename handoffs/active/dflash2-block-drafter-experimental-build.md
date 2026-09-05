# dFlash2 block drafter — experimental build + measured comparison vs MTP

**Status**: active (created 2026-08-20) — build/regression/np1 complete; np2/4/8 and greedy parity remain
**Categories**: speculative_decoding, hardware_optimization, local_inference, kernel_experimental
**Parent index**: [`inference-research-index.md`](inference-research-index.md)
**Related**: [`speculative-decoding-mtp-refresh.md`](speculative-decoding-mtp-refresh.md) (this is its Qwen3.8 rider),
[`deepseek-v4-flash-0731-dspark.md`](../completed/deepseek-v4-flash-0731-dspark.md) (historical DFlash-family sidecar workflow on v9),
[`autokernel-research-loop.md`](autokernel-research-loop.md); completed:
[`dflash-block-diffusion-speculation.md`](../completed/dflash-block-diffusion-speculation.md) (DFlash NO-GO on **CPU** — sequential
DeltaNet verification, not a DFlash defect; does not apply to this GPU path)

**AutoKernel routing:** this is the Qwen3.8-27B replacement campaign's `experimental_runtime` sibling,
not an additional source-mutation portfolio arm. It reuses AutoKernel's planner/critic, device claim,
stop/resume, typed refusal, telemetry, and dashboard pulse contracts, while owning separate build,
proof, and measurement roots. ~~No DFlash2 result may enter the kernel-source champion frontier.~~

> **SUPERSEDED 2026-08-27 by operator ruling.** DFlash2 **is** in the aggregate champion
> (`ak/champion/llama-cpp-0db32c06e3e5` @ `5c278648a`): *"It is the superior spec decode path for
> running qwen3.8-27b. Our future production candidate should support this new spec decode type"*,
> and *"DFlash2 is a parallel spec decode pathway. Not all models have dflash2 drafter heads. When
> we promote to production, we will adjust the lean registry compiler accordingly."* `--spec-type`
> binds a server instance, not the kernel, so one kernel carrying both `draft-mtp` and
> `draft-dflash` is a capability, not a conflict. Program handoff:
> [`autokernel-champion-aggregate.md`](autokernel-champion-aggregate.md).

## ⭐ OPEN — DRAFTER-PER-MODEL: a served model without a DFlash2 head serves slow (Qwopus3.8-27B, 2026-09-05)

**Why this matters (operator-flagged):** DFlash2 is the champion's serving edge (2.38× on Qwen3.8-27B).
The operator's own ruling above — *"Not all models have dflash2 drafter heads"* — got its first concrete
measurement: **Qwopus3.8-27B-Flash** (a Qwen3.8-27B fine-tune, same `qwen35` arch) benched on the champion
build at **identical raw speed** (30.3 t/s, coherent) but its serving spec-decode is capped by drafter quality:

| spec-decode path | decode t/s | speedup | acceptance |
|---|---|---|---|
| its own native MTP head | 45.5 | 1.50× | 0.590 |
| our DFlash2 drafter (base-trained) | 45.7 | 1.51× | **0.356 — does NOT transfer** |
| (ref) Qwen3.8-27B + its DFlash2 | ~72 | 2.38× | high |

**The lesson generalizes:** a base-trained DFlash2 drafter does not transfer to a fine-tune (distribution
shift), so **each model we want to serve at champion speed needs its own DFlash2-class drafter.** Qwopus's
shipped MTP (1.5×) is a floor, not the ceiling.

- [ ] **DF2-QWOPUS — scope + estimate training a DFlash2 head for Qwopus** (before committing card-days).
      DFlash2/EAGLE-style drafters are distillation of a small (~2 GB) head from the frozen target — NOT a
      pretrain — so tractable: capture Qwopus hidden states + outputs over a corpus (teacher-forcing), train
      the draft head, validate acceptance. Rough recon: **~2–5 days on the single MI210** (inference-bound
      feature gen + light head training), pending the exact DFlash2 recipe/data volume — which this scoping
      pass must nail. Weigh against: (a) the native MTP already gives 1.5× for free; (b) GPU contention — the
      one MI210 also runs AutoKernel/serving, so training days compete with everything else on the card.
- [ ] **DF2-DRAFTER-CAPABILITY — generalize:** treat "train a DFlash2 drafter for target model X" as a
      reusable capability (the pipeline, not a one-off), since every new serving candidate will need one.


The runtime receipt chain is fixed and resumable: `experimental_build` → `cpu_gpu_regression` →
`matched_np1` → `concurrency_grid` → `greedy_parity` → `decision`. Each receipt binds the candidate,
build/model/protocol identities, predecessor hash, and (for GPU stages) the claim window. A stopped
campaign resumes at the first missing or invalid receipt and never reruns a sealed cell. The dashboard
must identify this as `campaign_kind=experimental_runtime`, keep the AutoKernel/planner tails open,
and show only headline np1/np8/parity/decision values while keeping raw grids and receipts collapsed.

## Objective

Decide, on measured evidence, whether the dFlash2 block-diffusion drafter beats our in-file MTP head for
**Qwen3.8-27B on the MI210**. This is an *alternative* to MTP, not additive — `--spec-type` takes one value.

## Why this is a build task and not a bench task

v9 already ships `--spec-type draft-dflash` and `draft-dspark` (verified 2026-08-19 from `llama-server --help`),
so DFlash1/DSpark drafters run on frozen production today. **dFlash2 weights do not.** Only DFlash2 GGUFs are
published for Qwen3.8-27B — there is no DFlash1 build of this drafter — and v9's loader is the DFlash1
implementation. Measured, not assumed:

```
load_arch_hparams: missing target_hidden_size; using legacy draft hidden size 5120
llama_model_load: error loading model: done_getting_tensors:
    wrong number of tensors; expected 81, got 58
```

The file is a valid GGUF declaring `dflash.*` keys; v9 requires 81 tensors and a `target_hidden_size` key
(`src/models/dflash.cpp:19-21`) that DFlash2 weights do not carry. 58-vs-81 is a **format difference, not a bad
download**. Evidence: `epyc-inference-research/artifacts/architect-bench-gpu-20260814/dflash2_20260819/dflash2_n8/server.stderr`.

So this needs llama.cpp **PR #27342** (open, NOT merged as of 2026-08-18), built per the four-step workflow in
`CLAUDE.md`: pull fresh production → build on `llama.cpp-experimental` → validate no regressions (GPU + CPU) →
deploy as a NEW production version. **The frozen v9 tree is never edited.**

## The bar it has to clear — measured 2026-08-19, not assumed

There was **no plain-vs-MTP baseline for Qwen3.8-27B anywhere in the repo** before this. There is now.
Protocol: np=1, 12 real olympiadbench prompts, 2048-token cap, v9 `0db32c06e` / build `10125`, one flag varied.
Artifacts: `artifacts/architect-bench-gpu-20260814/mtp_ab_20260819/` and `mtp_nmax_sweep_20260819/`.

| `--spec-draft-n-max` | plain | 2 | 3 | 4 | 6 | **8** | 12 |
|---|---|---|---|---|---|---|---|
| decode t/s | 27.78 | 39.77 | 46.61 | 51.03 | 55.22 | **55.46** | 51.14 |
| draft acceptance | — | 0.842 | 0.773 | 0.702 | 0.579 | 0.482 | — |

- **MTP is worth 1.85× at n-max 4 and 2.00× at n-max 8.** dFlash2 must beat **55.46 t/s**, not 27.78.
- The vendor's 2.7–4.6× headline is versus *plain*, at batch 1, on an Apple M5 Max. We already capture 2.00×
  of that for free from the in-file head. Their like-for-like claim is 4.80 vs MTP's 4.28 accepted tokens ≈ **+12%**.
- **Suffix decay is real on our own drafter**: acceptance nearly halves from depth 2 → 8. That is the effect
  dFlash2 claims to fix, so the headroom is real — but it is ~12%, not 2.7×.

## Tasks

- [x] **DF2-1 — Build.** Fresh production tip → `llama.cpp-experimental`, apply PR #27342, build HIP/gfx90a.
      Forward-port our local gfx90a patches into the candidate, **notably `a6b4b5263`** (routes small Q8_0
      MTP-verify batches to MMQ, `ne11<=1`, +17.4% single-stream MTP on MI210).
- [ ] **DF2-2 — Check the MMQ patch still fires.** `a6b4b5263` is *MTP-verify-shaped* (`ne11<=1`); a dFlash2
      block verify has `ne11≈8` and may land on a less-tuned path. **This is the single most likely cause of a
      disappointing first number** — confirm before attributing any shortfall to dFlash2 itself.
- [x] **DF2-3 — No-regression validation vs v9** (GPU + CPU) before any comparison is quoted.
- [x] **DF2-4 — Matched comparison.** Replay the exact protocol above (same 12 prompts, np=1, 2048 cap) with
      `--spec-type draft-dflash` + `incoai/Qwen3.8-27B-DFlash2-GGUF:Q8_0`
      (already downloaded: `/mnt/raid0/llm/models/Qwen3.8-27B-DFlash2-Q8_0.gguf`, 2,056,414,752 bytes, Apache-2.0).
      Report decode t/s **and** acceptance against the table above.
- [x] **DF2-5 — Concurrency.** ✅ 2026-08-28 — PASS, see the results section below. *(compute-gated; design REVISED 2026-08-21 by intake-1277 — the earlier
      wording would have returned a clean sheet that means nothing.)* Re-run against the MTP grid
      (47.6 / 75.4 / 108.7 / 157.3 t/s) with five design changes, each of which fixes a specific way
      the naive version fails:
      1. **Sweep IN-FLIGHT REQUESTS 1/2/4/8, not `-np`.** Upstream #27117 establishes with its own
         control matrix that `-np` alone is inert — a `-np 16` server carrying only 4 concurrent
         requests is *bit-identical* to `-np 4`. A grid that varies `-np` while issuing serially sits
         entirely in the healthy region. Hold `-np` at or above the request count.
      2. **Instrument per-slot `draft acceptance` and `mean accepted length`**, not aggregate
         throughput. Throughput cannot separate a scheduling cost from a correctness defect — which is
         exactly why the whole upstream PR #27342 concurrency argument is still unresolved.
      3. **Three arms at every point: none / MTP / DFlash2.** Without the no-drafter arm a regression
         cannot be attributed to speculation; without the MTP arm it cannot be attributed to DFlash.
         **#27117 is DFlash-1 and predates PR #27342 by three days**, so an unattributed result would
         blame DFlash-2 for a defect that is not its own.
      4. **Hold `--spec-draft-n-max` FIXED across the sweep.** `accepted/generated` is structurally
         n_max-dependent: measured upstream at 0.708 (n-max 1) vs 0.523 (n-max 3) on the same drafter
         and a single slot, with per-position acceptance 0.719 / 0.496 / 0.353. If n_max is varied at
         all, report mean accepted length beside the ratio.
      5. **Run every cell twice, with and without `--kv-unified`.** *(the highest-value item here)*
      **Gate:** the paired `--kv-unified` arm is the single discriminating control that **nobody
      upstream has ever run, on any backend, for any drafter** — the #27117 reporter demonstrably never
      used it (verified three ways). A negative retires the leading root-cause hypothesis for free; a
      positive localises a real defect that is present verbatim in frozen v9. Note that the flag
      correlation cited for that hypothesis is 3-point with a counter-example and fully confounded
      with CUDA-vs-AMD (see intake-1264 as corrected), and that a `split_equal` row-permutation defect
      is backend-agnostic *by construction*.
      Reported onset is at **8 concurrent**, and 4 is healthy in every report including #27117 — so a
      sweep that stops at 4 cannot see the phenomenon at all. Our production role runs np up to 8.
- [x] **DF2-6 — Greedy-parity check.** ✅ 2026-08-28 — non-parity CONFIRMED but NOT attributable to DFlash2; see below. dFlash2 claims losslessness; verify exact-token parity vs `--spec-type none`
      at temp 0, reusing the method preserved in
      [`deepseek-v4-flash-0731-dspark.md`](../completed/deepseek-v4-flash-0731-dspark.md).
      *(2026-08-21, intake-1277: add a `draft-simple` control before concluding.)* Upstream #27407
      establishes that **batched speculative verification ALONE** deterministically diverges from the
      greedy baseline at near-ties, reproducing with `draft-simple` and no DFlash code involved. A
      DF2-6 non-parity result is therefore **not automatically a DFlash2 defect**, and without the
      control this task cannot distinguish the two.
      **THIRD FINDING, 2026-08-22 — the two-arm control is STILL insufficient, because of a patch of
      our own.** Frozen v9 carries EPYC-local commit `a6b4b5263` (`ggml/src/ggml-cuda/mmvq.cu:341-344`,
      verified absent upstream) that **deliberately** routes Q8_0 to a different kernel at `ne11>=2`:
      `// MMVQ->MMQ campaign ... so MTP verify blocks (4-col batch) use batched mul_mat_q instead of
      per-column mul_mat_vec_q` → `case GGML_TYPE_Q8_0: return log_decision(ne11 <= 1);`. Its own
      commit message says it is **"numerically-valid (not bit-exact)"**, taken for +17.4 % single-stream
      MTP on MI210. A verify batch is `ne11 = n_max+1 >= 2`; the non-speculative baseline is `ne11 = 1`.
      **So on gfx90a a DF2-6 parity failure may be entirely attributable to a performance patch we
      knowingly accepted, and none of the currently-filed arms can tell the difference.**
      Two consequences, both mandatory: capture **`GGML_CUDA_LOG_MMVQ_ROUTE=1`** on every arm (it is a
      runtime env var — `ggml-cuda.cu:1812-1814` — so it needs no rebuild) and report which kernel each
      verify batch actually took; and note that **`--spec-draft-n-max 1` is NOT a safe bit-exact
      reference** here, because it still produces a 2-column batch and our local rule splits at exactly
      `ne11 >= 2`. The same `N==1` vs `N>1` split exists on both CPU paths too (`llamafile_sgemm`'s
      `mnpack` register blocking; iqk's `funcs[ny-1]` dispatch), so batch invariance is not a property
      any of our three compute planes holds.
- [x] **DF2-6b — add an `ngram` arm.** ✅ 2026-08-28 — ngram 11/12 vs external drafters 7/12. *(2026-08-22.)* Upstream #25618 — a five-week-older, far
      better-diagnosed thread that #27407 never cites, with 15 comments and reproductions on Vulkan,
      Metal and ROCm — reports `ngram-simple` and `ngram-mod` staying **byte-identical on the same
      quantized target even with accepts**, through the same `common_sampler_sample_and_accept_n` path,
      while `draft-dspark` diverges. Nobody in 15 comments revisited it. If a multi-token verify batch
      alone were sufficient, ngram should break too.
      **Gate:** ngram byte-identical while `draft-simple` diverges, on our identical target and prompts,
      would localise the defect to the **external-drafter verify path** rather than to multi-token
      verify as such — and would overturn #27407's headline for our stack. v9 supports both spec types.
- [x] **DF2-6c — protocol fixes that decide whether DF2-6 means anything.** *(2026-08-22.)*
      (i) **Run at least 5 prompts, not 1.** #27407's own `draft-simple` arm was byte-identical on one
      workload and divergent on the other; a third-party run went 0/5 → 4/5 depending on patch. A
      single-prompt parity check returns a false clean sheet at a rate near 50 %.
      (ii) **Fresh process per phase.** One reporter measured 1/5 with a reused server versus 4/5 with
      fresh processes *despite* `cache_prompt=false`.
      (iii) **Run at `-ctk f16 -ctv f16`.** Quantized KV alone moves greedy output even with
      `--spec-type none`, so a q8_0-KV arm needs its own non-speculative baseline first or non-parity
      is unattributable.
      (iv) Compare by stripped-output hash **plus** first-differing *generation-token* index via
      same-vocab `llama-tokenize`, and report per-prompt PASS/FAIL — never an aggregate verdict.
- [x] **DF2-7 — `draft-dflash` multi-slot guard. CLOSED 2026-08-28 AS UNNECESSARY, not done.** ✅
      Its own trigger condition was *"if DF2-5 reproduces #27117 on gfx90a"*. **DF2-5 did not
      reproduce it**: DFlash2 scales cleanly to 8 in-flight requests (+47.8% over MTP at 8) with
      per-slot acceptance FLAT across the sweep (0.6205 → 0.6294), and 8 is precisely where every
      upstream report places onset. There is no failure to guard against, so adding a guard would
      forbid a configuration we have measured to be healthy and would cost real throughput.
      Closed on the operator's instruction, 2026-08-28.

      Retained for the record: frozen v9 hard-refuses `draft-dspark` above `--parallel 1` citing
      #26741 and has no equivalent guard for `draft-dflash`. That asymmetry is now understood as
      **correct rather than an oversight** — the two drafters do not share the defect. Should a
      multi-slot DFlash failure ever be observed, reopen with the measurement that shows it; a
      guard is only justified by a reproduced fault.
- [ ] **DF2-10 (2026-09-02, owned by ak-rebuild-20260828 per operator reassignment) — post-keep
      capability verification.** Run 23 advanced the champion three keeps past `5c278648a`
      (`7d2ea88b` mmvq · `db18f393` fattn-wmma-f16 · `732389d6` mmvq rewrite) with zero DFlash2
      exercise. `scripts/benchmark/dflash2_capability_smoke.sh` (research `b412f37d`) replays the
      DF2-5 server recipe on any build and gates acceptance ≥0.58 / boost ≥1.5×; first run
      targets anchor-gen-014 at the boundary GPU seam (~2026-09-02T13:00Z), run-24 launch held on
      its PASS. Tracking + verdict live in `autokernel-rebuild-program.md` R23-17/R23-18.
- [ ] **DF2-8 (B, blocked on DF2-6b / DF2-6c producing a non-parity result at all) — widen
      `use_serial_speculative_verify` on the experimental branch to give DF2-6 a bit-exact
      reference.** *(2026-08-23, wave-2 plan B4.)* **Upstream item: DF2-6b's ngram arm and DF2-6c's
      protocol fixes. If parity holds across >=5 prompts once those land, this work is unnecessary
      and should be CLOSED, not carried.** The problem it solves is that DF2-6 currently has no arm
      that is *guaranteed* bit-exact, so a divergence cannot be localised.
      **`--spec-draft-n-max 1` is NOT a safe substitute** and must not be used as one: it still
      produces a **2-column** verify batch, and our local `a6b4b5263` rule splits at exactly
      `ne11 >= 2` (`ggml/src/ggml-cuda/mmvq.cu:341-344`) — so the "reference" arm would take the same
      MMQ route as the arms under test and prove nothing. Capture `GGML_CUDA_LOG_MMVQ_ROUTE=1` on it
      like every other arm.
      **Experimental branch only**, branched from the current production tip per the four-step
      workflow. **Decline any v9 change outright**; frozen v9 is not modified for a diagnostic.
      [intake-1288#record]

- [ ] **DF2-6b-bis (new, 2026-08-28) — re-run the ngram arm at COMPARABLE DRAFT VOLUME.**
      The 2026-08-28 ngram arm drafted 218 tokens against dflash2's 4012 and draft_simple's 11951,
      and drafted nothing at all on one of the 12 prompts, so its 11/12 parity is explained by lack
      of exposure rather than by immunity. Its kernel-route profile is byte-identical to the
      no-drafter baseline, confirming it barely speculated. Until an ngram arm speculates at a
      comparable rate, #25618's localisation cannot be tested on our stack. Use `ngram-cache` or
      `ngram-mod`, or prompts with high n-gram repetition, and REPORT `draft_n` per arm beside the
      verdict so exposure is visible rather than assumed.
- [x] **DF2-9 (new, 2026-08-27) — pin `GGML_HIP_ROCWMMA_FATTN=ON` in every DF2/champion build
      recipe.** The flag **defaults to OFF** (`ggml/CMakeLists.txt:219`), and on gfx90a with
      `-fa on` the non-rocWMMA path produces non-finite values at longer sequence lengths — see the
      2026-08-27 checkpoint below. The standalone DF2 candidate build already carries it ON, so no
      DF2 result to date is affected; this task is to make that explicit in the recipe rather than
      inherited by luck. Related: **CH-8** in
      [`autokernel-champion-aggregate.md`](autokernel-champion-aggregate.md), where AutoKernel's own
      GPU builder omits it.

## 2026-08-28 RESULTS — DF2-5 PASS, DF2-6 non-parity but not DFlash2's fault

Both gates run against the champion `5c278648a` (rocWMMA ON), GPU exclusively held.
Artifacts: `artifacts-df25/dflash2_concurrency_20260827/` and `…/dflash2_greedy_parity_20260828/`.

### DF2-5 — PASS. 24/24 cells, 192 per-slot rows, zero refusals.

| in-flight | none | MTP | DFlash2 | DF2 vs MTP |
|---|---|---|---|---|
| 1 | 26.6 | 54.5 | **70.0** | +28.4% |
| 2 | 31.4 | 78.7 | **117.2** | +48.9% |
| 4 | 54.2 | 104.5 | **153.6** | +47.0% |
| 8 | 58.0 | 104.9 | **155.0** | +47.8% |

*(`--kv-unified` OFF; the ON half of the grid is in `cells.json` and tells the same story.)*

**The #27117 phenomenon does not reproduce on gfx90a.** Per-slot acceptance is FLAT across the
sweep — DFlash2 0.6205 → 0.6294 and MTP 0.4782 → 0.4818 from 1 to 8 in-flight — with no degradation
at 8, which is where every upstream report places onset. Aggregate throughput could never have
shown this; it required the per-slot parsing that no prior parser captured (the `id N` field was
present in the logs all along).

**Replication is exact where it can be checked**: np=1 DFlash2 gives 70.0 t/s and weighted
acceptance 0.6205 against DF2-4's 70.0 and 0.62049 — a different binary, a rewritten harness, the
same answer.

**The `--kv-unified` control came back NEGATIVE** — DFlash2 is slightly *worse* with it on at c4
(142.7 vs 153.6) and c8 (151.9 vs 155.0), and acceptance is unmoved. Per this handoff's own gate
wording, a negative "retires the leading root-cause hypothesis for free". It is retired.

**The `none` arm earned its place**: it scales weakly (26.6 → 58.0), so without it the concurrency
gains could not have been attributed to speculation rather than ordinary scheduling.

### DF2-6 — DFlash2 is NOT bit-exact, and the controls prove that is not a DFlash2 defect

| arm | PASS | FAIL | drafted? |
|---|---|---|---|
| baseline (`--spec-type none`) | — | — | **no** (negative control clean) |
| dflash2 | 7 | 5 | yes |
| **draft_simple** | **7** | **5** | yes |
| ngram_simple | 11 | 1 | yes |

`draft-simple` contains **no DFlash code whatsoever**, yet fails at the same rate and at three
**identical first-differing generation-token indices** (34, 216, 238). Two unrelated drafters
diverging at the same token positions places the divergence in the shared speculative-verify path,
reproducing upstream #27407 on our stack.

> **RETRACTED 2026-08-28 — the ngram claim in the first version of this section.** It read: *"ngram
> — same multi-token verify path, no external drafter — diverges 1/12 rather than 5/12, consistent
> with #25618 and pointing at the external-drafter verify path specifically."* **That comparison is
> confounded and does not support the conclusion.** Drafting volumes over the same 12 prompts:
>
> | arm | total `draft_n` | accepted | prompts that drafted nothing |
> |---|---:|---:|---:|
> | dflash2 | 4012 | 2479 | 0 |
> | draft_simple | 11951 | 1541 | 0 |
> | **ngram_simple** | **218** | 135 | **1** |
>
> ngram drafted **18× less than dflash2 and 55× less than draft_simple**, and produced no draft at
> all on one prompt. Its 11/12 pass rate is largely explained by **near-absence of exposure**, not
> by immunity to the divergence mechanism. The route capture agrees: ngram's kernel-route profile
> is byte-identical to the no-drafter baseline (MMQ 1984 / MMVQ 581), i.e. it barely speculated.
> A #25618-style localisation needs an ngram arm with **comparable draft volume**; until then this
> arm adjudicates nothing. Filed as **DF2-6b-bis**.

**Verdict: DFlash2's losslessness claim fails bit-exactness, but DFlash2 is no worse than the
generic speculative path, so this is not a reason to withhold it.** Combined with DF2-5, DFlash2 is
the superior spec-decode path for Qwen3.8-27B on this hardware.

**One mandated instrument did NOT produce evidence — stated plainly rather than glossed.**
`GGML_CUDA_LOG_MMVQ_ROUTE=1` yielded **zero** route lines on all four arms, and a dedicated probe
with the flag passed directly on a successful generation also yielded zero. Cause:
`ggml_cuda_log_mul_mat_route` is called only from `ggml_cuda_mul_mat` (`ggml-cuda.cu:1863–1890`)
and **never from `ggml_cuda_mul_mat_id`**, so MoE expert matmuls are invisible to it. Therefore the
`a6b4b5263` attribution question is **not settled by direct evidence**; it is addressed only
indirectly by the ngram asymmetry above. Tracked as **CH-9** in
[`autokernel-champion-aggregate.md`](autokernel-champion-aggregate.md).

## 2026-08-27 checkpoint — runners landed, grid running, and a build-flag trap

**Gate runners now exist** (epyc-inference-research `c84ecdb7`). The DF2-5 reader contract
(`epyc.g2_df25_draft_grid.v1` in `scripts/vidya/adapters/research_sweeps.py`) already existed and
its docstring stated *"G2–G4 runners do not exist yet"* — that gap is closed:

- `scripts/benchmark/g2_df25_concurrency_grid.py` — DF2-5. Implements all five revised design
  rules, including the paired `--kv-unified` control and **per-slot** acceptance parsing (the
  `id N` field is present in every `slot print_timing` line and every prior parser dropped it).
  Written as a new runner rather than an extension of `dflash2_followups.py`, whose sealed
  `EXPECTED_PROTOCOL` / `REQUIRED_ARM_FILES` contracts carry DF2-4's receipts and would be
  invalidated by adding arms.
- `scripts/benchmark/df2_greedy_parity.py` — DF2-6, with the `draft-simple` and `ngram` controls
  (DF2-6b), `GGML_CUDA_LOG_MMVQ_ROUTE=1` on every arm, `-ctk f16 -ctv f16`, a fresh process per
  arm, ≥5 prompts, per-prompt PASS/FAIL with the first-differing generation-token index, and the
  `draft_n == 0` / `draft_n > 0` negative controls carried from the k35 dspark method — without
  which a PASS can be a false clean sheet produced by speculation never engaging.

**DF2-5 grid launched 2026-08-27 22:15Z** against the champion `5c278648a` (24 cells: in-flight
1/2/4/8 × none/MTP/DFlash2 × `--kv-unified` off/on). First cell `none_c1_kvu0` = 26.6 t/s.

**The build-flag trap, recorded because it nearly invalidated the whole grid.**
`GGML_HIP_ROCWMMA_FATTN` defaults to OFF. A champion built with it OFF failed **every** pinned
olympiadbench prompt on task 0:

```
E process: rejecting DFlash batch after 3020800/3020800 non-finite target features (limit=16)
```

while a 25-character prompt succeeded on the same binary — **prompt length is the discriminator**,
so a short smoke test passes and hides it. Attribution was verified, not assumed: the standalone
DF2 build `2046c64e9` ran the identical prompts and flags at 46.1 / 69.4 / 58.9 t/s with zero
non-finite errors, and `git diff 2046c64e9 5c278648a -- src/ common/` is +67/−0, so DFlash's source
is byte-identical between them. Rebuilt with the flag ON: all prompts pass, zero errors. Scope
discipline: this was observed in the DFlash **target-feature** path; whether plain non-speculative
decode also degrades at length on an OFF build is **not measured** and is not claimed.

## 2026-08-20 measured checkpoint

The manual PR #27342 forward-port is complete on the isolated experimental branch
`ak/dflash2-qwen38-20260820` at `2046c64e9948671c7557428b198acebc6f416575`; frozen v9 was not modified.
The full Release/gfx90a HIP build completed, CPU and real-model GPU smoke tests passed, and the one initially
observed broad-suite `SOFT_MAX+sinks` failure passed on exact v9 and candidate reruns at both `-j1` and `-j4`.
`a6b4b5263` is already an ancestor of v9 and remains present; DF2-2 stays open until the DFlash2 block-verify
dispatch itself is proven rather than inferred from source presence.

The matched np=1 campaign used the same 12 prompts, 2048-token cap, seed 42, temperature 0.6, top-p 0.95,
top-k 20, and no-thinking envelope for all three arms. All 36 requests completed without error:

| arm | decode t/s | mean acceptance | weighted acceptance |
|---|---:|---:|---:|
| plain | 29.4 | — | — |
| MTP nmax8 | 55.2 | 0.48246 | 0.47823 (19,220/40,190) |
| DFlash2 block8 | **70.0** | **0.62804** | **0.62049 (19,960/32,168)** |

DFlash2 is **+26.81%** over the matched MTP arm, **+26.22%** over the historical v9 MTP value of 55.46 t/s,
and **+138.10%** over matched plain. This clears the single-stream half of the decision rule but is not yet a
promotion result: DF2-5 np=8 scaling and DF2-6 exact greedy parity remain mandatory.

Evidence: `epyc-inference-research/artifacts/architect-bench-gpu-20260814/dflash2_np1_20260820/`;
campaign summary SHA-256 `e4f9e21fd399c37fceca31e171be0299bcd4c35284d5a5828e3201a8bf50b053`;
59-file manifest SHA-256 `ebfc55f5706d549e7c5e00cf814e968f299491fe9ab23466f83a7dfb6cb6be4e`.
All three official GPU claims released, captured KFD processes exited, and VRAM returned to the 13,094,912-byte
idle baseline.

## Known negative evidence — do not wave this away

`llama.cpp` issue #25117 reports DFlash at **0.48× baseline** on AMD (gfx1151 APU, Q4_K MoE target), attributed
partly to a BF16-trained drafter meeting a quantized target and partly to HIP-backend immaturity. That is an APU
with a MoE target, not our discrete MI210 with a dense Q8_0 target — but it is a **real AMD-specific negative
datapoint** and DF2-2/DF2-5 are the checks that would catch the same failure mode here.

## Decision rule

If dFlash2 does not beat **55.46 t/s single-stream** *and* hold up at np=8, it does not displace MTP. A ~12%
acceptance gain bought with a 2.0 GB extra resident model and its KV-injection overhead is not obviously worth
it; say so plainly rather than shipping a marginal win.

## Adjacent finding this surfaced (separate work, not part of DF2)

The v9 24-cell throughput grid was captured at `--spec-draft-n-max 4`, i.e. **below peak** — 6–8 is optimal,
worth ~8% single-stream. Re-collecting that grid at n-max 8 is outstanding. Also `model_registry.yaml:849` ships
`draft_max: 4` while `epyc-orchestrator/stack_templates/default.yaml:148` ships `24`; **measured, both are wrong**
(24 is far past the turnover). That config conflict gates the pending Qwen3.6→3.8 registry swap and belongs with
whoever owns the swap, not with this handoff.

## Sources

[inco.ai/blog/dflash2](https://inco.ai/blog/dflash2/) · [z-lab/dflash (MIT)](https://github.com/z-lab/dflash) ·
[Qwen3.8-27B-DFlash2-GGUF (Apache-2.0)](https://huggingface.co/incoai/Qwen3.8-27B-DFlash2-GGUF) ·
[llama.cpp PR #27342](https://github.com/ggml-org/llama.cpp/pull/27342) ·
[llama.cpp issue #25117](https://github.com/ggml-org/llama.cpp/issues/25117) ·
[arXiv 2602.06036](https://arxiv.org/html/2602.06036v2)

All vendor speedup figures above are **CLAIMS**, unverified on gfx90a. Every number in the n-max table is a
**measured OBSERVATION** (MEASUREMENT.md) — none gates a keep/deploy decision on its own.
