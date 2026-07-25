# iqk IQ-quant Enablement — a live defect on every IQ-quant model we run

**Status**: RE-LANDED ON v8 — BUILT, correctness-attested (3 models), speed matrix IN FLIGHT. **Carrying vehicle is now `experimental-v8-refresh-20260724`** (commits `b8ad9d292` enable+harden, `1977a5d78` Q2_K/Q3_K fallback preserve), a hardened SUPERSET of the branch below. See the 2026-07-25 audit section for residual defects + new tasks.
**Created**: 2026-07-21 (via research-intake deep dive on intake-872/873)
**Priority**: HIGH — this is a live defect, not an experiment. We ship an acceleration flag that silently skips the majority of the weights on four deployed models.
**Branch**: ~~`iqk/enable-iquants-v7-20260721` @ `f78ec18fe`, worktree `/mnt/raid0/llm/llama.cpp-iqk-iquants`~~ **superseded 2026-07-25** — the v8 branch re-implemented this as `b8ad9d292` (same 5-type whitelist + tests + IQ3_XXS small-shape NMSE guard) WITHOUT merging `f78ec18fe`; the worktree branch is now historical. Retire it after v8 promotes.
**Superseded branch**: `iqk/enable-iquants-20260721` @ `e06f5368f` (off the experimental tip, only 3 of 5 types) — do not use
**Related**: [tq3-quantization-evaluation.md](tq3-quantization-evaluation.md), [glm52-reviewer-capability-gates.md](glm52-reviewer-capability-gates.md), [v7-promotion.md](v7-promotion.md), completed [iqk-port.md](../completed/iqk-port.md)

---

## Executor start here

Build the worktree, run the per-model gates in B2-B4, promote via B5. Everything below explains *why this is worth doing promptly*; the tasks are at the bottom.

## Why this matters (the case for doing it now)

**1. We are paying for an optimisation we are not receiving.** `GGML_IQK=1` exists to swap in ik_llama's AVX-512 GEMM kernels — measured **+7.9-8.8% decode on Q4_K** and **+22-49% prefill** on other quant families during the original port. But iqk dispatches **per quant type** through `iqk_typeA_supported` (`ggml/src/ggml-cpu/iqk/iqk_dispatch.cpp`), and that whitelist contained only K-quants and legacy quants. `iqk_set_kernels_iquants` and `iqk_convert_iquants_q80_r8` were linker stubs returning `false`. So on an IQ-quant model the flag accelerates the attention and shared-expert tensors and **falls back to the stock kernel for the parameter bulk** — with no error, no warning, and no log line. It looks enabled and is mostly inert.

**2. It is not one model — it is every IQ-quant model in the registry.** Tensor counts parsed directly from GGUF headers (2026-07-21, header bytes only):

| Model | Tensors covered by this change | Not covered |
|---|---:|---|
| **GLM-5.2 UD-IQ2_M** | **221** (148 IQ2_XXS + 71 IQ3_XXS + 2 IQ2_S) | IQ4_XS ×4 |
| **Qwen3.5-122B-A10B UD-IQ2_M** | **143** (94 IQ2_XXS + 47 IQ3_XXS + 2 IQ2_S) | IQ4_XS ×1 |
| **Qwen3-Next-80B-A3B i1-IQ2_M** | **433** (414 IQ2_S + 19 IQ3_S) — **54% of all 807 tensors** | — |
| **Hy3-IQ1_M-mtp** | **157** (79 IQ3_XXS + 78 IQ2_XXS) | IQ1_M ×82 (needs the still-stubbed 1bit family) |

In every case the covered tensors are the MoE routed experts (`ffn_gate_exps` / `ffn_up_exps` / `ffn_down_exps`). For a 256-expert/8-active MoE those *are* the model: the parameter bulk, the dominant term in decode bandwidth, and the dominant term in prefill FLOPs. **Qwen3-Next-80B is the biggest proportional beneficiary** — more than half its tensor count — which was not obvious before the headers were parsed, and is a reason not to treat this as a GLM-only fix.

**3. The code already predicted this exact failure.** `iqk_stubs.cpp:8-12`, written at port time:

> *"The registry shows ZERO use of IQ-quants … so these families are stubbed to satisfy the linker … **If/when we adopt IQ-quants (e.g. future GLM IQ2), these MUST be replaced with the real ik kernels + their block types — do not leave them stubbed for a quant we deploy.**"*

That was correct when written — the registry genuinely had no IQ-quant models. Four have since been added. This is a stale-assumption defect with a written expiry condition that has passed, not a design gap.

**4. The change is small because the hard work was already done.** The 202KB kernel file `iqk_gemm_iquants.cpp` was vendored during the port and simply never added to the build. `IQ2_XXS=16`, `IQ2_XS=17`, `IQ3_XXS=18`, `IQ3_S=21`, `IQ2_S=22` are **native ggml enum values** — so no type registration, no `type_traits` growth, no `GGML_TYPE_COUNT` change, no GGUF format change, no requantisation, and no downloads. Three files, +13/−2.

**5. Expected payoff, stated honestly.** Prefill-dominant, decode-modest. Decode at 2-3 bpw sits deep in the memory-bandwidth-bound regime where the original port measured ~0% on Q8_0; the +22-49% figures came from prefill. GLM-5.2 prompts run 3-12K tokens and its measured decode is 2.49 t/s (5.33 with MTP), so prefill is the operative axis for that role. **Do not promote this on an assumed decode win** — B3 exists to measure it.

## What changed (committed, 3 files, +13/−2)

| File | Change |
|---|---|
| `ggml/src/ggml-cpu/CMakeLists.txt` | add `ggml-cpu/iqk/iqk_gemm_iquants.cpp` to the build |
| `ggml/src/ggml-cpu/iqk/iqk_stubs.cpp` | remove the two `return false` stubs so the real symbols link |
| `ggml/src/ggml-cpu/iqk/iqk_dispatch.cpp` | whitelist IQ2_XXS, IQ2_XS, IQ2_S, IQ3_XXS, IQ3_S |

The whitelist matches the kernel's real capability **exactly**: both `iqk_set_kernels_iquants` (`:2760-2775`) and `iqk_convert_iquants_q80_r8` (`:2810-2814`) implement precisely these five native types. The `*_R4` repacked variants in the same file are ik-only and unreachable from our GGUFs. IQ4_XS and IQ1_M are deliberately excluded — no kernel exists for them here.

**Pre-verified statically (no build):** every `GGML_TYPE_*` referenced by `iqk_gemm_iquants.cpp` resolves — the five natives from `ggml.h`, the `*_R4` variants via the `iqk_ext_types.h` shim, and `Q8_2_X4` via `#define … 99` in `iqk_config.h:18` (used only inside comments in this file).

## Why it is not already on production v7

Verified 2026-07-21: host load average ~48, seven llama-servers resident, and a **decision-grade architect-model-selection bench in flight on the production v7 binary** — including arm `A1_qwen35_122b_iq2m`, one of the four affected models. Rebuilding production would have corrupted an active measurement. Independently, CLAUDE.md freezes production kernels and routes all kernel work through experimental branches, and a no-regression claim across four models requires inference evidence we could not gather.

## Outstanding tasks (require a quiet window)

- [x] **B1 — Build.** ✅ 2026-07-25 — re-anchored to v8: `b8ad9d292` compiles `iqk_gemm_iquants.cpp` in `build-v8-cpu`/`build-v8-hip`/`build-v8-sanitize`; `test-iqk-ser` + `test-iqk-valid-control` pass on all three builds. Historical HIP CTest was `56/59`, with all 3 failures classified baseline with paired differentials; exact-tip HIP is `59/62` with the same 3 failure classes. This is not a green full-HIP-CTest claim. Exact-tip CPU and sanitizer qualification and paired evidence are durable under `epyc-inference-research/data/kernel-v8-candidate/`. The commit also fixed real UB in the kernels AND in the native `arch/x86/quants.c` reference paths (load-bearing for test validity).
- [x] **B2 — Correctness before speed, operator-scoped.** ✅ 2026-07-25 — exact 6-arm/24-task, three-model attestation `epyc.iqk_real_model_correctness.attestation.v1`, bound to exact tip `67a433bf4`, passed at `epyc-inference-research/data/kernel-v8-candidate/iqk-real-model-correctness/run-20260725T102000Z-67a433bf4/` (nested `101945Z`). It covers GLM-5.2-IQ2, Qwen3-Next-80B-IQ2, and Hy3-IQ1 with same-seed IQK-on/off coherence, anti-garbage, and per-token-logprob evidence. qwen3.5-122B is excluded by deprecation; Laguna IQ2 CPU/IQK is excluded by operator direction in favor of GPU IQ2, so this does not claim a Laguna IQK-on/off test.
- [ ] **B3 — Speed.** `llama-bench` under the canonical baseline protocol (`taskset -c 0-95 -t 96 -fa 1`, OMP env stack mandatory), `GGML_IQK=1` vs `=0`, prefill and decode reported separately. Start with **Qwen3-Next-80B** (largest covered share, 54%) and **GLM-5.2** (highest operational value), then the other two.
  - 2026-07-25 status: the current `cpu_prefill_v8_regression_runner.py` era-stamps artifacts,
    proves that the clean sustained window covers all measured repetitions, and sets
    `GGML_IQK_Q8_0=1` for Q8_0 rows. The prospective live run
    `data/kernel-v8-candidate/cpu-prefill-regression/run-20260725T082414Z-v3-live/`
    is invalid and supplies no decision number: the Qwen3.6-35B Q8 MoE prefill arm sustains
    about 50–55 target core-equivalents and cannot satisfy the ratified 72-core eligibility
    floor. Awaiting the operator's `RATIFY-48`, `WAIVE-Q8`, or `REPLACE-Q8` decision.
- [ ] **B4 — Non-IQ regression check.** Confirm K-quant/legacy models are unaffected. The dispatch change is purely additive so this should be a formality — but it is the claim that lets this reach production.
  - 2026-07-25 audit note: **this exact risk class already materialized** — `b8ad9d292` incidentally reclassified Q2_K/Q3_K activations Q8_2_X4→Q8_K, engaging never-validated iqk kquant kernels and corrupting Hy3 output (caught on live output at 20:47Z, NOT by tests; fixed same day by `1977a5d78` + static_asserts). The measured non-IQ check is therefore NOT a formality for v8 — it is mandatory, and default CI still cannot catch a re-introduction (see NEW-4 below).
- [ ] **B5 — Promote.** If B2-B4 pass, fold into the next experimental→production promotion per the four-step workflow. Do NOT hand-patch production v7.

## Decision gates

- **B2 fails on any model** → do not promote; isolate kernel vs convert path, and consider a narrower whitelist (e.g. IQ2_XXS + IQ3_XXS only).
- **B3 shows a decode regression** → may still be worth promoting if prefill dominates for the affected roles, but that becomes an operator call with numbers attached, not an assumption.
- **B4 shows any non-IQ delta** → stop. An additive dispatch change must not move the K-quant path; a delta means something else moved.

## Adjacent: the KT/trellis family (folded in from tq3-quantization-evaluation.md)

Chasing the *trellis* stub is what uncovered the IQ-quant defect above, but the two are not comparable in cost and should not be sequenced together.

**Trellis is 3-6 days and medium-high risk, not a flag flip.** `iqk_gemm_ktquants.cpp` is absent from `CMakeLists.txt`; the `block_iq2_kt`/`block_iq4_kt` structs do not exist in our tree (only in `/mnt/raid0/llm/ik_llama.cpp`); and the KT types are **synthetic casts at 153-158 against `GGML_TYPE_COUNT = 43` with no `type_traits` row**, so a KT GGUF cannot load at all — the same OOB class commit `715383cde` already had to fix once. Honouring ik's IDs against a dense `type_traits` array ripples into the CUDA/HIP per-type tables. KT is also CPU-only, so the MI210 cannot participate.

**And the bpw arithmetic undercuts the motivating use case.** `block_iq2_kt` is 68 B per 256 weights = **2.125 bpw**, versus **IQ2_XXS at 2.0625 bpw** — trellis is *larger* than what GLM-5.2 already uses, so it saves zero bandwidth while adding per-weight arithmetic. It is a **quality-at-equal-bpw play mis-framed as a speed play**. Against Q4_K_M the saving is ~17.5%, but our own iqk data (+7.9-8.8% on Q4_K, ~0% on Q8_0) shows we are not fully bandwidth-saturated at 4-bit, so added arithmetic eats into it. ik's own author states KT quants are "generally slower for token generation on CPU due to likely compute bottleneck".

**Sequencing (do not reorder):**
- [ ] **T1 — Do B1-B5 above first.** Cheap, additive, and it targets models we actually run.
- [ ] **T2 — Gate trellis in `ik_llama.cpp`, not in our tree.** `/mnt/raid0/llm/ik_llama.cpp` is already on disk and is the reference implementation. Build it in a scratch dir purely as a measurement instrument and bench IQ4_KT vs Q4_K_M and IQ2_KT vs IQ2_XXS *there*. This answers the whole question without porting anything. Needs operator inference approval; it is a bench harness, not a second serving binary.
- [ ] **T3 — Port only if T2 wins.** Gate: IQ4_KT must reach **≥95% of Q4_K_M tg128** under the canonical protocol **and** show a measurable PPL/eval win. Slower than 95% ⇒ **DROP permanently** — 17.5% fewer bytes that decode slower is strictly dominated.
- NOTE: no `IQ*_KT` GGUF exists under `/mnt/raid0/llm`, and public KT producers (ubergarm, ik-community) cover giant MoEs we do not serve. Viterbi is the **encoding** cost only — at inference the trellis LCG runs forward — so self-quantising is hours on 192 cores plus an imatrix, not prohibitive, but not free.

## Key files

- Worktree / branch: `/mnt/raid0/llm/llama.cpp-iqk-iquants`, `iqk/enable-iquants-v7-20260721` @ `f78ec18fe`
- Kernel: `ggml/src/ggml-cpu/iqk/iqk_gemm_iquants.cpp` (set_kernels `:2760-2775`, converters `:2810-2814`)
- Dispatch: `ggml/src/ggml-cpu/iqk/iqk_dispatch.cpp`
- Stubs: `ggml/src/ggml-cpu/iqk/iqk_stubs.cpp`
- GLM-5.2 tensor map: `/mnt/raid0/llm/tmp/gguf-inspect-20260721/`

## Reporting instructions

Append build/bench artifacts and protocol ids here, update [tq3-quantization-evaluation.md](tq3-quantization-evaluation.md) with the outcome, and flip B1-B5 / T1-T3 with `✅ YYYY-MM-DD`. All numbers are OBSERVATIONS under MEASUREMENT.md until produced by a codified recipe with operator approval.

---

## Addendum 2026-07-21 — the 1-bit family, and why KT must be gated outside our tree

### A. The stubbed 1-bit family (IQ1_M / IQ1_S) — folded in for the kernel session

`iqk_set_kernels_1bit` and `iqk_convert_1bit_q80_r8` are still `return false` stubs in
`iqk_stubs.cpp`, exactly like the IQ-quant pair was. The consequence today:

- **Hy3-IQ1_M-mtp** has **82 IQ1_M tensors** (`blk.*.ffn_gate.weight` and friends) that this
  change does **not** cover. Its other 157 IQ3_XXS/IQ2_XXS tensors do get accelerated by B1-B5,
  so Hy3 is partially fixed — the 1-bit remainder is the leftover.
- No other registry model currently carries IQ1_* tensors, so Hy3 is the sole beneficiary as of
  2026-07-21.

Whether this is as cheap as the IQ-quant un-stub is **unverified** and must be checked before it
is scheduled — the IQ-quant case was cheap for a specific reason (native enum values, kernel
already vendored), and that reason has to be re-established here rather than assumed:

- [ ] **B6 — Scope the 1bit family.** Confirm (a) `iqk_gemm_1bit.cpp` is vendored in our tree,
  (b) which types its `set_kernels`/`convert` switches actually implement, (c) whether those are
  native ggml enum values (`IQ1_S=19`, `IQ1_M=29` are native; ik-only `_R4` variants are not), and
  (d) whether it needs block structs or `type_traits` rows we lack — the KT failure mode. If all
  four come back clean it is the same one-day shape as B1-B5 and should ride the same build. If any
  come back dirty, file it separately rather than bundling it into this promotion.
- NOTE: the payoff is narrower than B1-B5 — one model, 82 tensors — so do not let it block B5.

### B. Why the KT/trellis gate belongs in `ik_llama.cpp`, not our tree (operator question)

The premise of the question is right: we **did** fold ik_llama's work into our fork at v6, and
v7 carries it. But what was folded is the **iqk GEMM kernel subsystem** — the `mul_mat` dispatch
path gated by `GGML_IQK`. The **KT block types and their format plumbing were deliberately not
folded**, which is precisely what `iqk_stubs.cpp` documents.

Verified in our tree at `production-consolidated-v7 @ 6ad45fa3f`:

| capability | our tree | ik_llama.cpp |
|---|---|---|
| `IQ2_KT`/`IQ4_KT` in the public `ggml_type` enum (`ggml/include/ggml.h`) | **0 references** | present |
| KT rows in the `type_traits` table (`ggml/src/ggml.c`) | **0 references** | present |
| `llama-quantize` can *produce* a KT GGUF | **0 references** — no KT option | present |
| `GGML_TYPE_COUNT` | 43 (KT ids are 153-158) | extended |

So our binary can neither **produce** a KT GGUF nor **load** one. A KT tensor would index
`type_traits` out of bounds — the same OOB class commit `715383cde` already had to fix once.

That is the whole argument, and it is narrower than "use ik because it's better": **to answer
"is IQ4_KT worth 3-6 days of porting?" you must first create an IQ4_KT GGUF and read it back, and
only ik_llama.cpp can currently do either.** Using it as a *measurement instrument* to decide
whether to build the capability in our tree is not a second serving path and does not reopen the
deprecation — CLAUDE.md deprecates ik_llama as a **serving** binary, which this is not.

The alternative is legitimate and should be stated plainly: **do the port first and measure in our
own tree.** That is the cleaner end-state and avoids touching a deprecated tree at all. It simply
costs the 3-6 days up front on a question whose expected answer is unfavourable — IQ2_KT is
2.125 bpw against the 2.0625 bpw IQ2_XXS we already run (so *negative* bandwidth), and ik's own
author reports KT as slower for CPU token generation. Spending the port to find that out inverts
the usual order of cheap-test-then-build.

**Operator's call.** If the deprecated-tree usage is unwelcome, T2 should be replaced by "port on
`llama.cpp-experimental` and measure there", accepting the cost. Either way T1 (B1-B5) comes first
and is unaffected.


## Laguna S 2.1 intake integration — 2026-07-22
_Via /research-intake Stage-2 (intake-880); see [laguna-s21-cpu-port.md](laguna-s21-cpu-port.md)._
- [x] Add Laguna-S-2.1-UD-IQ2_M as the 5th beneficiary model to the B2/B3 gate list. ✅ 2026-07-25 — recorded and operator-scoped to GPU IQ2; it is not a B2 CPU IQK-on/off-tested model. Its routed-expert bulk is IQ2_XXS(51%)+IQ3_XXS(37%)+IQ2_S(1.4%) = the same set the committed `iqk/enable-iquants-v7-20260721` branch already accelerates (89.9% of the model); only 2 IQ4_XS tensors (2.3%) stay uncovered, the same remnant GLM-5.2/Qwen already carry — NO new kernel needed

---

## 2026-07-25 v8 audit (Claude session, operator-requested) — residual defects + new tasks

Full 4-agent audit of the v8 carrying commits (`b8ad9d292`, `1977a5d78`). Verified against
measured GLM-5.2 UD-IQ2_M GGUF headers: the five native types cover **89.1% of bytes**
(IQ2_XXS 51.5% + IQ3_XXS 36.7% + IQ2_S 0.9%), IQ4_XS is 2.9% (4 MoE down-expert tensors),
Q2_K/Q3_K 1.5%, Q8_0 2.2%. Both GEMV and GEMM are enabled, dense + MoE, no batch gating;
runtime gating/fallback is clean (GGML_IQK=0 → zero overhead; non-AVX512 → functional #else
paths). Findings ordered by leverage:

- [x] **NEW-1 (perf, ~3 lines) — enable IQ4_XS dispatch.** ✅ 2026-07-25 — landed in `8890e2b14`; focused CPU/sanitizer evidence passed. A real compiled IQ4_XS kernel
  already exists (`iqk_gemm_kquants.cpp:2712-2714` via `DequantizerIQ4XS`, routed at
  `iqk_mul_mat.cpp:906-917`) but the type is excluded from `iqk_typeA_supported`, so it is
  never reached. The landed change adds it to the dispatch whitelist + `iqk_weight_uses_q8_k` + the
  `repack.cpp` parity list, closing the last 2.9% of GLM-5.2 bytes (and the IQ4_XS remnants on
  122B/Laguna) at near-zero risk. Same B2-style correctness gate applies. (IQ4_NL likewise
  exists unused — registry-irrelevant today, note only.)
- [x] **NEW-2 (perf waste, defect) — stop paying the Q2_K/Q3_K double penalty.** ✅ 2026-07-25 — landed in `8890e2b14`; focused CPU/sanitizer evidence passed. Before the fix,
  Q2_K/Q3_K remained in `iqk_typeA_supported` but could never pass `MulMat::prepare` → every such
  matmul under `GGML_IQK=1` paid the full cooperative Q8_2_X4 activation quantize +
  `ggml_barrier` (`iqk_dispatch.cpp:146-162`, MoE `:229-264`) and THEN falls back to native
  rerunning from scratch — pure per-call waste on GLM-5.2's blk.48/78 expert layers — while
  `repack.cpp:4544-4546` simultaneously withheld these tensors from CPU_REPACK. The landed
  change removes both types before activation quantization, restores v7 behavior, and fixes
  the stale header comment that claimed "Q8_K for Q2_K/Q3_K".
- [x] **NEW-3 (correctness risk, NDEBUG) — invalid-expert-ID OOB on the fallback path.** ✅ 2026-07-25 — landed in `8890e2b14`; focused CPU/sanitizer evidence passed. The
  iqk MoE hook zeroes/skips invalid expert ids (`iqk_dispatch.cpp:239-262`), but the native
  path that Q2_K/Q3_K experts fall back to only `assert()`s id validity (`ggml-cpu.c:1649`) —
  a no-op under NDEBUG, then an OOB row-mapping write. The invalid-id scenario is exactly what
  `test-iqk-ser` exists for; the fallback path was unprotected. The landed change adds an
  explicit NDEBUG-safe bounds guard that zeroes inactive invalid routes.
- [x] **NEW-4 (test gap) — close default CI's IQK corruption gap.** ✅ 2026-07-25 — landed in `8890e2b14`; focused CPU/sanitizer evidence passed. Before the fix, the
  new `test-backend-ops` IQ cases compare against a sound `use_ref` reference, but nothing in
  ctest exports `GGML_IQK=1`, so default runs exercise only native kernels; the only
  iqk-engaging default test is `test-iqk-ser` — a **structural** smoke (MUL_MAT_ID, IQ2_XXS
  only, one shape, no numerical comparison vs reference). The Hy3 corruption would pass
  default CI. The landed change adds a `GGML_IQK=1` ctest variant of the MUL_MAT/MUL_MAT_ID backend-ops
  cases for all 5 types + dense GEMV/GEMM shapes, and extends `test-iqk-ser` to numerically
  compare iqk-vs-control within NMSE tolerance.
- [x] **NEW-5 (Zen5 decode experiment, cheap) — GEMV inner loop is on the disfavored
  instruction.** ✅ 2026-07-25 — NO-GO: `160/216` focused evidence did not justify the change; source restored. `multiply_add_1` (`iqk_gemm_iquants.cpp:683-717`) selects the
  **VPDPBUSD** (`_mm256_dpbusd_epi32`) branch under HAVE_FANCY_SIMD on this host, while the
  **VPMADDUBSW** variant sits in the same function's `#else`. Prior Zen5 measurement
  (`project_zen5_vnni_vs_maddubs`) found VPMADDUBSW faster; the GEMM path already uses
  maddubs+VPDPWSSD. A/B the swap on the decode path (expectations modest — decode is BW-bound
  — but it is a compile-time toggle test). NOTE: this is moving OFF VNNI, i.e. NOT the killed
  "AVX-512VNNI vec_dot" ledger item.
- [ ] **NEW-6 (prefill headroom, post-v8 riders, one bundle):** (a) `func16` 16-wide kernels
  are `nullptr` for the plain IQ types (`iqk_gemm_iquants.cpp:2754`) — prefill capped at
  8-column micro-kernels; (b) the large-Ny `Q8_K_R16` convert-repack path is disabled in
  `is_dequant_better` (`iqk_mul_mat.cpp:246-254`) over an un-root-caused Zen4 correctness
  issue — root-cause it rather than leave ik's 16-wide prefill path off; (c) fused MoE
  up/gate exists (`iqk_mul_mat.cpp:811`) but no GGML hook calls it; (d) `iqk_flash_attn.cpp`
  is not in the build; (e) the IQ3_XXS `n_rows>=32` NMSE gate (`iqk_dispatch.cpp:88-93`) is an
  accuracy exclusion that was shape-gated, not root-caused — thin numerical margin by
  admission; (f) all kernels are 256-bit ymm — no zmm variant exists (Zen5 512-bit datapath +
  `k_x_step`/`IQK_MAX_NY` tiling inherited from ik's Zen4 tuning, unexamined). None of these
  gate v8 promotion; they are the next iqk perf tranche.
- [x] **NEW-7 (evidence hygiene, do before container restart):** ✅ 2026-07-25 — durable
  exact-tip CPU/HIP/sanitizer CTest evidence is under
  `epyc-inference-research/data/kernel-v8-candidate/{exact-tip-build,final-focused,sanitize-final}/`;
  paired thread-safety and quant-selection evidence is under
  `data/kernel-v8-candidate/pre-final-audit-evidence/run-20260725T0945Z/paired-thread-quant/`.
  The post-`6c44557bf` thread-safety rerun passed. Historical HIP was `56/59`, all 3 failures
  classified baseline with paired differentials; exact-tip HIP is `59/62` with the same three
  failure classes, not green.
