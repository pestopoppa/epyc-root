# iqk IQ-quant Enablement — shipped in v8, residual research active

**Status**: PROMOTED AND FROZEN IN v8 — `production-consolidated-v8` at `67a433bf45a8a091d83b4ea0b32ff0735fd51800`, `llama-server` version `10107`. The terminal both-mode lineup passed `24/24` smoke and `6/6` API; final-freeze attestation `artifacts/operator/ratify_v8_final_freeze_20260725.json` has SHA `e7fce2c5cd720940fc84b669f57b78a61589fd8baef9b4e03030ed0dc4a3175b`. The CPU Q4 architect remains live at `8083`. The campaign-scoped WAIVE-Q8 means v8 makes no Q8 performance or non-regression claim. See the 2026-07-25 audit section for residual post-v8 work.
**Created**: 2026-07-21 (via research-intake deep dive on intake-872/873)
**Priority**: POST-v8 RESEARCH — the production enablement defect is closed;
NEW-6, trellis gates, and the remaining riders below stay open.
**Branch**: ~~`iqk/enable-iquants-v7-20260721` @ `f78ec18fe`, worktree `/mnt/raid0/llm/llama.cpp-iqk-iquants`~~ **superseded 2026-07-25** — the v8 branch re-implemented this as `b8ad9d292` (same 5-type whitelist + tests + IQ3_XXS small-shape NMSE guard) WITHOUT merging `f78ec18fe`; the worktree branch is historical after the v8 freeze.
**Superseded branch**: `iqk/enable-iquants-20260721` @ `e06f5368f` (off the experimental tip, only 3 of 5 types) — do not use
**Related**: [tq3-quantization-evaluation.md](tq3-quantization-evaluation.md), [glm52-reviewer-capability-gates.md](glm52-reviewer-capability-gates.md), [v7-promotion.md](../completed/v7-promotion.md), completed [iqk-port.md](../completed/iqk-port.md)

---

## Executor start here

B1-B5 are complete in frozen v8. Start from the unchecked post-v8 tasks below;
do not rebuild or re-promote the frozen production branch.

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

## What changed (initial enablement plus v8 hardening)

| File | Change |
|---|---|
| `ggml/src/ggml-cpu/CMakeLists.txt` | add `ggml-cpu/iqk/iqk_gemm_iquants.cpp` to the build |
| `ggml/src/ggml-cpu/iqk/iqk_stubs.cpp` | remove the two `return false` stubs so the real symbols link |
| `ggml/src/ggml-cpu/iqk/iqk_dispatch.cpp` | whitelist IQ2_XXS, IQ2_XS, IQ2_S, IQ3_XXS, IQ3_S, and IQ4_XS; reject Q2_K/Q3_K before activation quantization |

The initial five IQ2/IQ3 types use `iqk_gemm_iquants.cpp`. Final v8 commit
`8890e2b14` also enables native IQ4_XS through the already-vendored
`iqk_gemm_kquants.cpp` kernel (`set_kernels` at `:2724`, conversion at `:2780`) and
adds compile-time dispatch assertions. The `*_R4` repacked variants remain ik-only
and unreachable from our GGUFs. IQ1_M remains excluded because its 1-bit family is
still stubbed.

**Pre-verified statically (no build):** every `GGML_TYPE_*` referenced by `iqk_gemm_iquants.cpp` resolves — the five natives from `ggml.h`, the `*_R4` variants via the `iqk_ext_types.h` shim, and `Q8_2_X4` via `#define … 99` in `iqk_config.h:18` (used only inside comments in this file).

## Why it is not already on production v7

Verified 2026-07-21: host load average ~48, seven llama-servers resident, and a **decision-grade architect-model-selection bench in flight on the production v7 binary** — including arm `A1_qwen35_122b_iq2m`, one of the four affected models. Rebuilding production would have corrupted an active measurement. Independently, CLAUDE.md freezes production kernels and routes all kernel work through experimental branches, and a no-regression claim across four models requires inference evidence we could not gather.

## Outstanding tasks (require a quiet window)

- [x] **B1 — Build.** ✅ 2026-07-25 — re-anchored to v8: `b8ad9d292` compiles `iqk_gemm_iquants.cpp` in `build-v8-cpu`/`build-v8-hip`/`build-v8-sanitize`; `test-iqk-ser` + `test-iqk-valid-control` pass on all three builds. Historical HIP CTest was `56/59`, with all 3 failures classified baseline with paired differentials; exact-tip HIP is `59/62` with the same 3 failure classes. This is not a green full-HIP-CTest claim. Exact-tip CPU and sanitizer qualification and paired evidence are durable under `epyc-inference-research/data/kernel-v8-candidate/`. The commit also fixed real UB in the kernels AND in the native `arch/x86/quants.c` reference paths (load-bearing for test validity).
- [x] **B2 — Correctness before speed, operator-scoped.** ✅ 2026-07-25 — exact 6-arm/24-task, three-model attestation `epyc.iqk_real_model_correctness.attestation.v1`, bound to exact tip `67a433bf4`, passed at `epyc-inference-research/data/kernel-v8-candidate/iqk-real-model-correctness/run-20260725T102000Z-67a433bf4/` (nested `101945Z`). It covers GLM-5.2-IQ2, Qwen3-Next-80B-IQ2, and Hy3-IQ1 with same-seed IQK-on/off coherence, anti-garbage, and per-token-logprob evidence. The qwen3.5-122B B2 arm is omitted under the separate operator instruction to skip its regression tests. GPU-IQ2 arm excluded; CPU Q4 architect remains live. Laguna CPU/IQK is excluded by operator direction in favor of GPU IQ2, so this does not claim a Laguna IQK-on/off test.

  **2026-07-25 operator correction / provenance:** this session incorrectly treated the R7 "A4 suffices" benchmark verdict as an executed Qwen3.5-122B deprecation. It is a pending operator lineup decision, not a serving-lineup change. The restored both-mode contract serves the CPU Q4 architect on `8083`; only its B2 regression arm remains out of scope under the separate regression-skip instruction.
- [x] **B3 — Speed.** ✅ 2026-07-25 — the ratified `P-BENCH-PREFILL-1`
  matrix passed all 14 executed v7/v8 pairs with zero throughput failures at
  `epyc-inference-research/data/kernel-v8-candidate/cpu-prefill-regression/run-20260725T155655Z-v4-waive-q8-kfd-procrace-swapoff/summary.json`.
  IQK-on utility ratios `(pp2048, tg128)` were GLM-5.2 `(1.4274, 1.0013)`,
  Hy3 `(1.3297, 1.0035)`, and Qwen3-Next `(1.3900, 0.9875)`; all three
  satisfy the ratified IQ rule. The operator's campaign-scoped WAIVE-Q8
  excludes four Qwen3.6 Q8 arms, so v8 makes no Q8 performance or
  non-regression claim.
- [x] **B4 — Non-IQ regression check.** ✅ 2026-07-25 — Gemma Q4 passed the
  ratified throughput check at `1.0830x` pp2048 and `1.0075x` tg128. The
  terminal paired quality gate used one pinned 200-question MMLU-Pro +
  195-question GPQA set and produced exact v7/v8 ties with zero errors:
  worker Gemma Q4 `36.5% / 24.6%`, architect Qwen3.5-122B Q4
  `63.5% / 56.9%`. Evidence is committed in research at `965e353e` under
  `data/kernel-v8-candidate/quality-gate/run-20260725T204443Z-fullcontract-both-mode/`.
  - 2026-07-25 audit note: **this exact risk class already materialized** — `b8ad9d292` incidentally reclassified Q2_K/Q3_K activations Q8_2_X4→Q8_K, engaging never-validated iqk kquant kernels and corrupting Hy3 output (caught on live output at 20:47Z, NOT by tests; fixed same day by `1977a5d78` + static_asserts). The measured non-IQ check is therefore NOT a formality for v8 — it is mandatory, and default CI still cannot catch a re-introduction (see NEW-4 below).
- [x] **B5 — Promote.** ✅ 2026-07-26 — promoted and frozen as `production-consolidated-v8` at `67a433bf45a8a091d83b4ea0b32ff0735fd51800` (version `10107`). Terminal both-mode lineup passed `24/24` smoke and `6/6` API; final-freeze attestation `artifacts/operator/ratify_v8_final_freeze_20260725.json` SHA `e7fce2c5cd720940fc84b669f57b78a61589fd8baef9b4e03030ed0dc4a3175b`. Do not hand-patch the frozen production kernel.

- [ ] **NEW-8 — Q38FN IQ\*_K/KS self-quant, measured in ik_llama.cpp before any port.** (filed 2026-10-04) Operator ruling
  2026-10-03/04: self-quant allowed "exceptionally if justifiable" (lifts the no-requant constraint for this
  option only). Evidence: [`docs/reviews/cpu-quant-research-20261003.md`](../../docs/reviews/cpu-quant-research-20261003.md) §3.3 #3 / §4.
  - Step 0: `/mnt/raid0/llm/ik_llama.cpp` @ `c04881fc0` has **no `qwen4exp` arch**. Fetch newer ik upstream
    into a scratch worktree and build it there. Measurement instrument only: ik is deprecated as a serving
    path, and its binaries never serve. Prove build currency (binary mtime vs commit date) before reading any number.
    - *(2026-10-28 private build and metadata preparation.)* Isolated upstream source `/mnt/raid0/llm/tmp/refactor-01a16fc3/inf26-new8-ik-upstream-20261028` at `1c5ea124098890184b297023cd9fc9655451b1ec` contains `qwen4exp` and IQ*_K/KS support. An incremental Release CPU build at `/mnt/raid0/llm/tmp/refactor-01a16fc3/inf26-new8-ik-cpu-build-20261028` completed the quantizer, perplexity, bench, server and imatrix targets with IQK mul-mat, flash attention and all-quants enabled. The binaries are newer than the source commit and the bench resolves this build's libraries. A header-only scan of the existing UD-IQ4_XS shards matched 144 expert tensors (48 each gate/up/down); input identities were stat-checked, not freshly fully hashed. The scan and bounded resource log are in `/mnt/raid0/llm/tmp/refactor-01a16fc3/inf26-new8-mapping-check-20261028/`. The Q8 source and a real model load remain outstanding; no quantization, quality or performance result is claimed. [belief: cc]
  - Step 1, source and base: no high-precision Q38FN GGUF is on disk. Pull unsloth `Q8_0/` (188.2 GB, about 5.8 h
    at ~9 MB/s, one download at a time) as both quantize source (`--allow-requantize`) and KLD base. BF16 (354 GB)
    is cleaner but leaves under 50 GB free once an output arm exists (500 GB free on 2026-10-04). Caveat: a Q8_0
    reference has a KLD floor of about 0.022–0.027.
  - Step 2: imatrix, then quantize 1–2 arms: IQ4_KS or IQ3_K gate/up, IQ5_KS/IQ4_KS dense, IQ4_NL down (640-wide).
    About 85–100 GB per arm.
  - Step 3: in the same ik binary, measure UD-IQ4_XS and the new arm(s) (IQ4_XS-uniform dropped: retired 2026-10-20, keeper UD-IQ4_XS): `--kl-divergence` (mean KLD,
    same-top-1), PPL, `llama-bench -p 5,256 -n 128` r3, and the serving shape (MTP d4, verify N=5). Compare ratios
    within ik only, never absolute numbers across trees.
  - Budget: about 3–5 CPU-window hours excluding the download (imatrix ≤ 30 min, quantize ~0.5–1.5 h per arm, KLD
    ~7 min per file plus base, bench ~25 min), in a DS41 pause window with DS41 unloaded. Peak disk ≈ 188 + 2×95 +
    25 (logits) ≈ 400 GB; delete Q8_0 after the base logits are saved.
  - **Justifiable means all of:** the IQ\*_K arm is ≥ +8% decode vs UD at the serving shape; ≥ +3.4–4.5% (the admission
    floor) over IQ4_XS-uniform, otherwise the zero-port file swap dominates (INF-70 XFER-3) — **criterion
    retired 2026-10-20**: the operator retired the uniform file (keeper UD-IQ4_XS), which takes the zero-port
    swap off the table, and the 2026-10-04 EXL3 window measured it at +17.8% PPL vs UD
    (`exl3-cpu-mi210-implementation.md`, EXL3-6c5), so it is no quality-equivalent competitor. Mean KLD ≤ UD's and
    same-top-1 within 1 pp; a paired per-item task eval no worse than UD. If any fails, the port is closed. If all
    pass, port in `llama.cpp-experimental`: register about 15 types (decide the ID policy first), compile the vendored
    iqk kernels and quantizer, respect the `715383cde` OOB class — 2–4 sessions.
  - 2026-10-04 (ak-ds41-main, backlog drain): backlog item c3 (IQ4_K/IQ4_KS on Q38FN via the ik instrument) is
    **BLOCKED** on this item's Steps 0 and 1. Checked on disk: `/mnt/raid0/llm/ik_llama.cpp` has no `qwen4exp` arch,
    no IQ4_K/KS Q38FN GGUF exists, and no Q8_0/BF16 Q38FN source exists. So c3 cannot run inside the drain; it needs
    the scratch ik build (Step 0) and the ~5.8 h Q8_0 download (Step 1) first. Schedule:
    `/mnt/raid0/llm/tmp/backlog-schedule-20261004.md` row 3. Justification bar: INF-70 XFER-3 (uniform IQ4_XS is
    +24-34% faster than UD at +17.8% PPL, `artifacts/cpu-window2-20261004/`).

- [x] **NEW-9 — Compare Magnitude's CPU IQ2/IQ3 decode and VNNI repack against iqk (documentation-only, zero compute).** ✅ 2026-10-20 — each difference classed (decode-bound / prefill-GEMM-bound / layout-only) in the note below; NEW-5 not reversed; NEW-6(b) fed. Read `inference/seismic/native-cpu/src/weights.rs` (IQ grid CPU decode, rows16/rows8 repack; the vector-coded representation near L1271) and its x86v4vnni `dot_u8_i8` path in `/mnt/raid0/llm/tmp/dive-1979/repo` @ `940e51b` against `ggml/src/ggml-cpu/iqk/iqk_gemm_iquants.cpp` for IQ2_XXS, IQ2_XS and IQ3_XXS (IQ1 is stubbed and out of scope). Record any decode-then-int8-dot structure iqk lacks, cross-checked against NEW-5 (NO-GO: VPDPBUSD is not a decode win on this Zen5 host) and NEW-6(a)(f) (no 16-wide func16 kernels, no zmm variant). Done when each difference is classed decode-bound, prefill/GEMM-bound or layout-only and either feeds a NEW-6 rider or is closed with its reason; no build and no bench.
  - **Factual note 2026-10-20 (NEW-9; read-only, no build, bench or run; checkbox left open for main review).** Sources: Magnitude `inference/seismic/native-cpu/src/weights.rs` @ `940e51b`; production tree `ggml/src/ggml-cpu/iqk/iqk_gemm_iquants.cpp` and `iqk_mul_mat.cpp` @ `ffc1bac82` (the x86 branch is `#ifdef __x86_64__` at `iqk_gemm_iquants.cpp:12` to `#else` at `:2817`; file last changed `b8ad9d292`). Cross-checked against NEW-5 and NEW-6(a)(b)(f).
  - **Decode-then-int8-dot structure.** Magnitude decodes each 32-value packet to signed i8 codes (`weights.rs:1296-1304` `grid_codes`; `Grid::dot_q8` `:1452-1480`) and takes an integer dot per packet via `dot_i8_i8` (`:632-643`): VPDPBUSD with a +128 weight offset and a per-call activation-sum correction (`:635-639`), or AVX2 maddubs (`:640-641`). iqk already has this structure in its direct x86 IQ kernels: EvenSignHelper plus VPDPBUSD (`iqk_gemm_iquants.cpp:685-691`, under HAVE_FANCY_SIMD) or VPMADDUBSW (`:693-696`), and the `minv = 43` offset in `DequantizerIQ2XXS` (`:137-224`). So the decode-then-int8-dot form itself is not missing from iqk. What iqk has and gates off for these types is the decode-then-int8 repack: `iqk_convert_iq2_xxs_q8_k_r8` (`:1909`), `iqk_convert_iq2_xs_q8_k_r8` (`:1961`), `iqk_convert_iq3_xxs_q8_k_r8` (`:2464`). `is_dequant_better` returns `type` unchanged for IQ2_XXS, IQ2_XS, IQ2_S, IQ3_XXS and IQ3_S (`iqk_mul_mat.cpp:297-306`), so the repack is not taken for them. Magnitude has no repack step at all: rows16 planar rows are decoded at use (`weights.rs:1415-1433`).
  - Differences and class:
    1. **Sign placement and dot form.** Magnitude: weight-side sign, then VPDPBUSD with +128 offset and correction (`weights.rs:632-639`). iqk GEMV path: activation-side sign with unsigned grid magnitudes (`iqk_gemm_iquants.cpp:199-202`, `:207-211`, into `multiply_add_1` `:685-691`). iqk q8_K path: weight-side sign with the minv=43 offset. Class: **decode-bound** (inner per-packet dot of the GEMV-shaped `dot_q8`). Closed: the offset and correction are extra work per packet, and VPDPBUSD is the form NEW-5 measured as no decode win on this host (NEW-5 NO-GO, `iqk_gemm_iquants.cpp:683-717`). No new lever.
    2. **Group-16 (IQ2_XS) dot.** Magnitude runs two full 32-lane dots per packet, each with the other half of the activations zeroed (`weights.rs:1472-1476`), each with its own correction. Class: **decode-bound**. Closed: redundant lanes by construction; nothing to import.
    3. **Repack.** Magnitude: none. iqk: the convert path exists but is gated off for these types (`iqk_mul_mat.cpp:297-306`) and is reached only when `npt >= 16` (`:618-619`). Class: **layout-only** (the repack is the layout change). Feeds **NEW-6(b)** as the gated path only: Magnitude supplies no root cause for the Zen4 correctness issue. The NEW-6(b) locator `iqk_mul_mat.cpp:246-254` is stale at this tip: that range is the dispatch loop; the gate is at `:297-306`.
    4. **Tile width.** Magnitude's rows8 tile is 8 rows (`weights.rs:122-130`; Grid ROWS8 names at `:1313`, `:1337`, `:1366`). iqk: k_nr=16 under HAVE_FANCY_SIMD, 8 otherwise (`iqk_gemm_iquants.cpp:1910-1916`); `func16 = nullptr` for the plain IQ types (`:2754`). Class: **prefill/GEMM-bound**. Feeds **NEW-6(a)**: Magnitude has no 16-wide IQ kernel, so it gives no evidence either way; (a) stays open.
    5. **Vector width.** Magnitude's VNNI path is 256-bit `_mm256_dpbusd_epi32` (`weights.rs:618-627`) with no 512-bit variant. Class: **prefill/GEMM-bound**. Feeds **NEW-6(f)** as a cross-check only: the same 256-bit pattern appears in Magnitude and it has no zmm reference; (f) stays open.
    6. **Scale and factor.** Magnitude: odd scale `2s+1` per 16 or 32 values with one f32 factor per 256 (`weights.rs` `Grid::packet`, impl `:1387-1412`). iqk: `2s+1` in `load_scales` and d = 0.125 * f16 (inside `:137-224`). Class: **layout-only** (storage placement; same arithmetic). Closed: no kernel gain.
    7. **Sign parity.** Same trick: Magnitude `signs.count_ones() & 1` (`weights.rs:1296-1304`); iqk EvenSignHelper popcount (`iqk_gemm_iquants.cpp:71-91`). No difference. Closed.
  - Verdict: no decode-then-int8-dot structure is missing from iqk's direct IQ2/IQ3 kernels. The only candidate, the repack path, is gated at `iqk_mul_mat.cpp:297-306` and reaches NEW-6(b) as a pointer only. NEW-5 is not reversed by this reading. No build, bench or run.

## Decision gates

- **B2 fails on any model** → do not promote; isolate kernel vs convert path, and consider a narrower whitelist (e.g. IQ2_XXS + IQ3_XXS only).
- **B3 shows a decode regression** → may still be worth promoting if prefill dominates for the affected roles, but that becomes an operator call with numbers attached, not an assumption.
- **B4 shows any non-IQ delta** → stop. An additive dispatch change must not move the K-quant path; a delta means something else moved.

## Adjacent: the KT/trellis family (folded in from tq3-quantization-evaluation.md)

**Format boundary (2026-09-25):** IQ*_KT and EXL3 are distinct tensor formats, codebooks, loaders, and
kernel paths. T2/T3 below govern IQ*_KT only. Project-owned EXL3 CPU and MI210 work is tracked by
[`exl3-cpu-mi210-implementation.md`](exl3-cpu-mi210-implementation.md) (`INF-80`) and may proceed independently.

Chasing the *trellis* stub is what uncovered the IQ-quant defect above, but the two are not comparable in cost and should not be sequenced together.

**Trellis is 3-6 days and medium-high risk, not a flag flip.** `iqk_gemm_ktquants.cpp` is absent from `CMakeLists.txt`; the `block_iq2_kt`/`block_iq4_kt` structs do not exist in our tree (only in `/mnt/raid0/llm/ik_llama.cpp`); and the KT types are **synthetic casts at 153-158 against `GGML_TYPE_COUNT = 43` with no `type_traits` row**, so a KT GGUF cannot load at all — the same OOB class commit `715383cde` already had to fix once. Honouring ik's IDs against a dense `type_traits` array ripples into the CUDA/HIP per-type tables. KT is also CPU-only, so the MI210 cannot participate.

**And the bpw arithmetic undercuts the motivating use case.** `block_iq2_kt` is 68 B per 256 weights = **2.125 bpw**, versus **IQ2_XXS at 2.0625 bpw** — trellis is *larger* than what GLM-5.2 already uses, so it saves zero bandwidth while adding per-weight arithmetic. It is a **quality-at-equal-bpw play mis-framed as a speed play**. Against Q4_K_M the saving is ~17.5%, but our own iqk data (+7.9-8.8% on Q4_K, ~0% on Q8_0) shows we are not fully bandwidth-saturated at 4-bit, so added arithmetic eats into it. ik's own author states KT quants are "generally slower for token generation on CPU due to likely compute bottleneck".

**Sequencing (do not reorder):**
- [x] **T1 — Do B1-B5 above first.** ✅ 2026-07-26 — satisfied by the
  frozen v8 promotion; continue with T2 only under its separate gate.
- [ ] **T2 — Gate trellis in `ik_llama.cpp`, not in our tree.** `/mnt/raid0/llm/ik_llama.cpp` is already on disk and is the reference implementation. Build it in a scratch dir purely as a measurement instrument and bench IQ4_KT vs Q4_K_M and IQ2_KT vs IQ2_XXS *there*. This answers the whole question without porting anything. Needs operator inference approval; it is a bench harness, not a second serving binary.
- [ ] **T3 — Port only if T2 wins.** Gate: IQ4_KT must reach **≥95% of Q4_K_M tg128** under the canonical protocol **and** show a measurable task-eval win (paired per-item flips vs the reference; report PPL/KLD beside it as fidelity context only — a near-baseline KLD/PPL ordering is not a quality ordering, intake-1510, intake-1519#05). Slower than 95% ⇒ **DROP permanently** — 17.5% fewer bytes that decode slower is strictly dominated.
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

- [x] **B6 — Scope the 1bit family.** ✅ 2026-07-29 static source audit at frozen
  `production-consolidated-v8` `67a433bf45a8a091d83b4ea0b32ff0735fd51800`: (a)
  `ggml-cpu/iqk/iqk_gemm_1bit.cpp` is vendored but omitted from the CPU CMake source list; (b) both
  architecture variants implement the native `IQ1_S` and `IQ1_M` cases in
  `iqk_set_kernels_1bit` and `iqk_convert_1bit_q80_r8` (the latter routes exactly those two types);
  (c) they are native `GGML_TYPE_IQ1_S=19` / `GGML_TYPE_IQ1_M=29`; and (d) their
  `block_iq1_s`/`block_iq1_m` plus core and CPU `type_traits` already exist. The source also carries
  ik-only `_R4`/BN paths, but `iqk_ext_types.h`/`iqk_ext_blocks.h` already provide their compile-only
  shims, so enabling the standard pair needs no enum, block-layout, or traits change. **Conclusion:
  clean same-shape candidate as B1-B5**; stage only on a fresh experimental branch and retain the
  normal build/correctness/measurement gates. No build, server, benchmark, or production-tree change
  was made by this audit.
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
  - **Locator correction 2026-10-20 (factual, box text not rewritten):** the NEW-6(b) gate site is `iqk_mul_mat.cpp:297-306 @ffc1bac82` (IQ2_XXS/IQ2_XS/IQ2_S/IQ3_XXS/IQ3_S return `type` unchanged in `is_dequant_better`). The `:246-254` locator in (b) is stale: that range is the dispatch loop.
- [x] **NEW-7 (evidence hygiene, do before container restart):** ✅ 2026-07-25 — durable
  exact-tip CPU/HIP/sanitizer CTest evidence is under
  `epyc-inference-research/data/kernel-v8-candidate/{exact-tip-build,final-focused,sanitize-final}/`;
  paired thread-safety and quant-selection evidence is under
  `data/kernel-v8-candidate/pre-final-audit-evidence/run-20260725T0945Z/paired-thread-quant/`.
  The post-`6c44557bf` thread-safety rerun passed. Historical HIP was `56/59`, all 3 failures
  classified baseline with paired differentials; exact-tip HIP is `59/62` with the same three
  failure classes, not green.

## Research intake 2026-10-21 — open-model backdoors, control-vector projection, Qwen3.8 post-train (research intake entries 2191–2213, see research/intake_index.yaml)

- [x] **NEW-11 — iqk coverage table for the ISTA-DASLab GSQ-RCO Q38FN builds (text only, no weights).** From the four published tensor-allocation files, compute per build the byte-weighted share of routed-expert bytes on iqk-accelerated types versus native fallback types (Q2_0, IQ4_NL, IQ1_M) before any download decision (intake-2206#01). ✅ 2026-10-21: table in epyc-inference-research `artifacts/intake-backdoor-cvec-20261021/NEW-11-gsq-rco-iqk-coverage.md` (c5661c5f9 lineage, cd9b3cfa6). Routed-expert non-iqk (decode/prefill): Q2_0 100/100%, IQ2_XS 35/35%, IQ3_XXS 36/45%, IQ3_S 41/62%; recommend IQ3_XXS first, skip Q2_0, IQ3_S conditional; download call stays operator's.
  - IQ3_S conditional resolved 2026-10-22 (workspace-58): **not pulled.** IQ3_XXS cleared the load smoke but failed PPL/KLD (NEW-10 verdict FAIL), so this table's IQ3_S condition is not met.
- [x] **NEW-10 — GSQ-RCO arm for Q38FN versus served UD-IQ4_XS.** After NEW-11 and an operator disk/download call, pull IQ3_XXS and IQ3_S from ISTA-DASLab at sha ed59f920 (not the community relay); v10 load smoke, then PPL plus mean KLD and same-top-1 against one shared reference, then coherence at production prompt length; only on a pass, the serving-shape bench; record which layers fall back to non-iqk types; the card's --lazy-mode flag does not exist in v10 (intake-2206#04). ✅ 2026-10-22 — DONE, verdict **FAIL** (G1-G3 miss the strict predeclared bars); the GSQ IQ3_XXS arm is closed for serving and IQ3_S is not pulled. Verdict block below.
  - Operator disk/download call made 2026-10-22: IQ3_XXS first (~65 GB); IQ3_S only if needed. The download is booked by workspace-58 (calendar owner).
  - 2026-10-22 (workspace-58): **download started, quality row armed, pass rule pinned.** Not ticked.
    - Download: the true size is **75.84 GB**, not ~65 GB. Shard 1 is 47.04 GB (sha `219ea929…`) and shard 2 is 28.80 GB (`per_layer_token_embd`, sha `316b46f3…`, identical across all four builds). It goes to `/mnt/raid0/llm/models/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF/IQ3_XXS/` and is pinned to `ed59f920`; the repo is public and ungated, so no token is used. Free space after: ~530 GB, above the 200 GB floor.
    - The download is one sequential job, `/mnt/raid0/llm/tmp/new10-q38fn-20261022/dl/download_iq3xxs_v2.sh` (PID 2076182, started 14:28:24Z, ~10 MB/s, ETA ~16:35Z). It writes the end flag `/mnt/raid0/llm/tmp/compute-flags/NEW10_IQ3XXS_DL_ENDED` (`rc`, `time`, `bytes`, `sha`) and checks sha256 against the HF API `lfs.oid`. v1 had a 404 URL (the `IQ3_XXS/` subfolder was missing); main killed it with operator approval.
    - Quality row: FILLERS `new10-q38fn-iqxxs-quality` is ARMED (owner workspace-58, block-correctness, CPU, one quarter, about 50 min estimated, 30 min minimum window, peak host RAM 168 GiB). Launcher: `filler_run7.sh --repeat`. The job script is `/mnt/raid0/llm/tmp/new10-q38fn-20261022/job/new10_quality_job.sh`.
    - The job first runs its precondition (download rc=0 and sha OK, else rc=5), then `ram_admit 168`. The steps after that: v10 store load smoke, then llama-perplexity UD-IQ4_XS on wiki.test.raw (c512, b512, 40 chunks, the EXL3-6c5 Q38FN recipe) with `--kl-divergence-base` as the ONE shared reference. Next, GSQ `--kl-divergence`, then coherence_gate on 5 greedy prompts (two of at least 4096 prompt tokens, plus 40/90/250-token prose). It ends with the per-layer non-iqk fallback list. The header predicts 96 native tensors (58 IQ4_NL, 38 Q2_0) and 12 decode-only IQ3_XXS tensors across all 48 layers.
    - Pass rule, pinned before any run: `/mnt/raid0/llm/tmp/new10-q38fn-20261022/job/PREDECLARED.json`, sha256 `1a5e5ca94146bf14aab0eb1cd30100ba230015ef5e8ac9c37e29aef8ca60a81b`. Every bar is required:
      - G1: mean ln(PPL(Q)/PPL(base)) ≤ 0.005, one-sided (the 2026-10-06 low-bit contract).
      - G2: mean KLD ≤ 0.1045. This is the survey rule "≤ 1.25 × UD's", times UD's published 0.0836.
      - G3: same-top-1 ≥ 88.55%, from the "within 1 pp" rule applied to UD's published 89.55%.
      - G4: zero coherence regressions.
      - G2 and G3 are TRANSLATIONS of reference-based gates onto a UD base, because no high-precision Q38FN base is on disk.
    - PASS authorises only the serving-shape speed bench. FAIL closes the arm, and IQ3_S is not pulled. Adoption still needs the paired task eval as sized by NEW-14 (landed 223b0e298): a 2 pp margin, required N from `degradation_stats.py size`, and the one-sided exact verdict. NEW-14 landed after the pin, so it is recorded in a non-rule addendum, `job/PREDECLARED.ADDENDUM-NEW14.md` (sha `e4f33abb…`); the bars are unchanged.
    - Belief kernel: the job writes `out/quantcmp_receipt.json` (`epyc.quantcmp.receipt.v0`) for the VB-QUANTCMP-WIRE adapter.
    - The card's `--lazy-mode` flag is not used.
  - 2026-10-22 evening (workspace-58): **strict bars kept, download done, first quality run aborted at its smoke step and root-caused.** NEW-10 stays open.
    - Operator ruling: keep the strict predeclared bars (`job/PREDECLARED.ADDENDUM-OPERATOR-BARS.md`); `PREDECLARED.json` sha `1a5e5ca9…` unchanged.
    - [x] IQ3_XXS download: ENDED rc=0 sha=OK at 16:27:55Z, 75.84 GB, both shards verified against the HF lfs oids (`/mnt/raid0/llm/tmp/compute-flags/NEW10_IQ3XXS_DL_ENDED`). ✅ 2026-10-22
    - First run `new10-q38fn-iqxxs-quality` FAILED rc=19 at the smoke step, 19:36Z (granted q3 19:30Z): the production CPU `llama-completion` aborted with SIGABRT "double free or corruption (out)" after a NaN on the first fused decode token. Log `/mnt/raid0/llm/tmp/new10-q38fn-20261022/out/smoke.log`. No quality number was produced.
    - Root cause (subagent, RCA notes `/mnt/raid0/llm/tmp/new10-ple-rca-20261022/`): not the PLE tensor type. GSQ stores `blk.*.ffn_down_shexp` as IQ4_NL (UD uses Q8_0); under `GGML_IQK=1` CPU_REPACK interleaves it (`iq4_nl_8x8`), and v10's fused single-token decode (`qwen4exp-fused.cpp` `lora_mm`) ignores the repack, so layer 0 goes NaN → layer-1 router all-NaN, `best=-1` → `probs[-1]=-INF` heap write → glibc abort. Same chain as FD-DIV-1 (`cpu-fused-decoder-blocks.md`).
    - The job's actual defect: it ran without the registered Q38FN serving env `GGML_FUSED_DECODE_OFF=1` (`model_registry.yaml`). Added to `CPU_ENV` for both arms; addendum `job/PREDECLARED.ADDENDUM-FUSED-OFF.md`, sha256 `e4aade94e31be3764d35cc1998581c72b096250ebd0a53e5bac9ad3893a04a26`. Bars unchanged; G1-G3 perplexity never enters the fused path.
    - [x] **NEW-10 quality re-run with the serving env (`GGML_FUSED_DECODE_OFF=1`).** Booked tonight on q3 after `dhm-mining-full` (writer `grant-night-q3-20261022.sh` v2, 90 min grant, cap 02:30Z). Done when `out/` holds the G1-G4 verdict against the unchanged `PREDECLARED.json` and the `quantcmp_receipt.json`; on PASS book the serving-shape bench (with the fused path off, as served), on FAIL close the arm. (filed 2026-10-22, workspace-58)
      ✅ 2026-10-22 — ran on q3 (re-placed by the q3 writer), COMPLETE 20:23:33Z; verdict FAIL, arm closed.
  - 2026-10-22 late evening (workspace-58): **NEW-10 verdict FAIL — the GSQ IQ3_XXS arm is closed for serving.** Source: `/mnt/raid0/llm/tmp/new10-q38fn-20261022/out/VERDICT.md` and `RESULT.json`, against the unchanged `PREDECLARED.json` (sha `1a5e5ca9…`) plus `PREDECLARED.ADDENDUM-FUSED-OFF.md` (sha `e4aade94…`, run with `GGML_FUSED_DECODE_OFF=1`). Production v10 CPU store binaries (`10303`, `cpu-20260921-ffc1bac82`); one shared logits base from the served UD-IQ4_XS; wiki.test.raw c512/b512/40 chunks.
    | Gate | Value | Bar | Result |
    |---|---|---|---|
    | G0 load smoke | rc 0, non-empty, all finite | — | PASS |
    | G1 mean ln(PPL(Q)/PPL(base)) | 0.0150 ± 0.0100 | ≤ 0.005 | FAIL |
    | G2 mean KLD (nats/token) | 0.322 ± 0.007 | ≤ 0.1045 | FAIL |
    | G3 same-top-1 | 82.9% ± 0.4 | ≥ 88.55% | FAIL |
    | G4 coherence | 0 regressions, 4 needs_review, 1 identical | 0 regressions | gate INCOMPLETE (passes the bar's letter; not eyeballed) |
    - PPL (descriptive, lower = better): UD-IQ4_XS 2.9925 ± 0.063 (base run), GSQ IQ3_XXS 3.0346 ± 0.062. Median KLD 0.062, max 9.73: the mean is carried by a heavy tail.
    - Fallback census: 96 native (non-iqk) tensors and 12 decode-only iqk IQ3_XXS tensors, as the header predicted (`out/fallback_layers.json`).
    - Consequences: no serving-shape speed bench; the NEW-14 paired task gate is not run (moot on FAIL); **IQ3_S is not pulled** by the predeclared rule (NEW-11: IQ3_S only if IQ3_XXS clears the load smoke and PPL/KLD). The four G4 needs_review texts under `out/coh/` are not eyeballed: declined, because G1-G3 already close the arm and no decision reads G4.
    - Weights: the operator ruled (2026-10-22 ~20:5xZ) KEEP the 75.8 GB IQ3_XXS weights until NEW-13 runs, then delete them (task under NEW-13).
    - Belief kernel: `out/quantcmp_receipt.json` is a job-written `epyc.quantcmp.receipt.v0` and is **refused** by the VB-QUANTCMP-WIRE strict reader (`qwen4exp_quality_reader.read_project` → `ValueError: unsupported receipt schema`, checked at this wrap-up). Capture task VB-QUANTCMP-NEW10 is filed in `vidya-belief-substrate-program.md`; it must run before the weights are deleted.

- Trigger (no checkbox): the GSQ code release adds a GGUF IQ-type or Q2_0 export path or a Qwen3.8-Flash-Next recipe. Then assess self-quantising with it (the paper's GGUF evidence covers K-quants only, intake-2207#01).

## Research intake 2026-10-22 — SLQ / IST-DASLab / kaitchup Qwen3.8-27B SLQ (intake-2461..2493)

Source: research intake session intake-ist-slq-20261022, Stage-3 plan `/mnt/raid0/llm/tmp/intake-ist-slq-20261022/stage3/STAGE3_PLAN.md` (sha256 db108374cd1bd164e5baaac2586b9d3abf26daaba46aec4085192e4b0c0232ad); operator ruling 2026-10-22 approved a subset. Trigger prose and knowledge notes from that plan are still pending the operator and are not filed here.

- [x] **NEW-13 — Zero-training prefill/decode weight-set handoff probe on CPU for Q38FN (intake-2467, intake-2485).** (filed 2026-10-22 via research intake, operator-approved 2026-10-22; after NEW-10's IQ3_XXS download) On a fresh llama.cpp-experimental branch, a tools/ harness prefills in one llama_context with the served UD-IQ4_XS (P), copies the sequence state (llama_state_seq_get_data/set_data: KV plus recurrent state) into a second context holding the GSQ-RCO IQ3_XXS (D), then teacher-forces a 256-token held-out continuation and records per-token KLD against one shared reference. Arms: A D-only, B P->D, C P-only, D reverse (D prefill, P decode). N = 120 passages of 2048 + 256 tokens, paired bootstrap 95% CI, R = (KLD_A - KLD_B)/KLD_A. Gate 0: KLD_A - KLD_C < 0.005 nats means uninformative, stop. PASS: R >= 0.25 with CI lower bound > 0.10 and coherence OK; FAIL: R < 0.10 or CI spans 0, record refuted and close. PMPD only tested nested quantizations, so a FAIL at independent quants does not refute PMPD. Compute (estimates): correctness class, region-lock --cpu-list 0-95, one process, RAM = both GGUFs mmap'd, 2-4 h plus about 1 h for arm D.
  - 2026-10-22 late evening (workspace-58): harness **in progress** — another workspace-58 subagent is building it on `experimental/new13-weight-handoff-20261022` (no runs yet). BACKLOG until armed, then booked on the 10-23 calendar (0-95, correctness, 2-4 h + ~1 h for arm D). NEW-10's FAIL does not cancel NEW-13: the probe asks whether a P prefill rescues D's decode, and a weak D is the case it tests.
  - ✅ 2026-10-23 — **COMPLETE 13:52Z, verdict PASS** (workspace-58). Harness `experimental/new13-weight-handoff-20261022` @ `6b3ac87fe` (tools/ only); rule `job/PREDECLARED.json` sha `c27090ff…` (unchanged); reference **P** chosen by the operator 06:32Z (served UD-IQ4_XS = arm C; `job/REFERENCE.json`, read-only). Ran on 0-95 in two grants (10:05-11:17Z, 46/120 passages, then 12:14-13:52Z). Source: `/mnt/raid0/llm/tmp/new13-weight-handoff-20261022/out/VERDICT.md` (sha `a505a3a0…`) and `RESULT.json` (sha `b3811466…`).
    | Gate | Value | Bar | Result |
    |---|---|---|---|
    | Gate 0 informative | KLD_A − KLD_C = 0.213 [0.197, 0.233] nats | ≥ 0.005 | informative |
    | R = (KLD_A − KLD_B)/KLD_A | 0.2828, paired bootstrap 95% CI [0.2458, 0.3219] | R ≥ 0.25 and CI_low > 0.10 | PASS |
    | Coherence (B vs C) | 0 regressions, 4 needs_review, long prompts ≥ 4096 | 0 regressions | OK |
    - Mean KLD (nats/token, 120 passages × 256 tokens, lower = better): A (GSQ IQ3_XXS only) 0.213, B (UD prefill → GSQ decode) 0.153, C (UD only) 0, D (GSQ prefill → UD decode) 0.101; reverse R_rev = 0.525 [0.485, 0.563]. Same-top-1 vs C: A 84.2%, B 85.9%, D 90.0%. Self-test state round trips ~1.1e-7.
    - **Speed caveat (descriptive only, not gated).** Teacher-force tok/s: A 15.9, B 15.8, C 21.9, D 22.6; prefill P 236.5, D 203.3. The GSQ IQ3_XXS decode is ~27% slower than UD-IQ4_XS on this CPU (15.9 vs 21.9), so B's quality recovery buys no speed: a P→D handoff is slower than serving P alone. The PASS shows that a high-bit prefill state transfers into a low-bit decoder, not that the handoff is a serving win.
    - Per the predeclared PASS branch: open C-L3, no kernel work yet (below). Derived, declined (not filed): the C-L4 ODP-port trigger (Stage-3 plan `intake-ist-slq-20261022` C-L4 needs ≥ 25% KLD-gap recovery AND a capacity or speed case). The recovery leg is met (R 0.28), but there is no speed case (decode −27%) and no capacity case is stated, so it is not triggered. The 4 coherence needs_review texts (`out/coh/`) are not eyeballed: the gate passes on 0 regressions and no decision reads them.
    - Belief kernel: `out/handoff_receipt.json` is a hand-written `epyc.new13.receipt.v0` that no strict reader accepts. Filed VB-NEW13-WIRE in `vidya-belief-substrate-program.md`.
  - [x] **C-L3 — NEW-13 follow-on: the same P→D handoff on a low-bit (IQ2_XXS-class) dense pair of an already-served 27B-class model, with ppl/coherence at production prompt length (opened by NEW-13's predeclared PASS branch, 2026-10-23; Stage-3 plan `intake-ist-slq-20261022` C-L3, intake-2467).** It calibrates against the paper's untrained-prefill reference (27B IQ2_XXS: MMLU-Pro 70.50 weight-only vs 76.06 with an RTN-NVFP4 prefill) and checks DFlash2 acceptance with P-produced hidden states. No kernel work yet. **Carry NEW-13's speed caveat**: on Q38FN the low-bit decoder was ~27% slower than the served quant, so C-L3 must report decode tok/s beside KLD, and must state a capacity or speed case before anything is built on it. Gate: an operator disk/download call for the IQ2_XXS GGUF (Stage-3 plan). Done when the predeclared KLD/coherence verdict and the descriptive speed table are recorded here. (filed 2026-10-23, workspace-58 wrap-up) ✅ 2026-10-23 **CLOSED SUPERSEDED, not completed** (operator 2026-10-23: the 27B IQ2 pair is dropped, and the live follow-on is C-L3-Q38FN below).
    - *Re-scoped 2026-10-23 (operator): "27B runs on Q8 on the GPU. We don't need to explore IQ2 there (except maybe to study kernel optimisation for those quants). Q38FN kernels are much more important to run in lower quants, if quality can be kept comparable and speed increased."* So C-L3's 27B IQ2_XXS pair is DROPPED. The live follow-on is C-L3-Q38FN below; the GSQ IQ3_XXS weights are kept for it.
  - [ ] **C-L3-Q38FN — make Q38FN low-bit decode faster than the served UD-IQ4_XS at comparable quality (operator 2026-10-23).** Evidence: NEW-13 PASS (UD prefill → GSQ IQ3_XXS decode recovers 28% of the KLD gap, R 0.28 [0.25,0.32]), but GSQ IQ3_XXS teacher-forced decode is ~28% SLOWER (15.8-15.9 vs 21.9-22.6 tok/s on 0-95). Step 1 (no compute): profile why. Is IQ3_XXS on an iqk fast path for these shapes? NEW-10 recorded 12 decode-only iqk fallback tensors; Q2_0 ffn_down_exps also matter. Step 2: an experimental kernel branch (AutoKernel low-bit lane) targeting IQ3_XXS/Q2_0 decode on CPU. Step 3: re-run NEW-13 arm B speed + a quality gate vs UD at production prompt length. Weights: /mnt/raid0/llm/models/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF/IQ3_XXS/ (kept).
    - [x] **C-L3-Q38FN-PROFILE-PREP-01a16fc3:** prepared and sent the diagnostic profile packet at NEXT priority; source-bound preflight `fbbb711cf768de5b0ad9361a27fa9cd1d5a9075818de4da3` and model-free perf-window and cleanup fixtures passed. The one-repetition synthetic decode comparison uses 48 threads, CPUs 0–95 and exclusive GPU quiet; requested 3600 s (minimum 1800), 200 GiB RAM plus 64 GiB admission margin. Receipt `bfac3cd3-2605-4df3-9095-cd66e7225c21` proves transport only: consumption, arming and execution unconfirmed. This does not reproduce the historical teacher-forced slowdown; parent remains open. Packet `/mnt/raid0/llm/tmp/refactor-01a16fc3/cl3-q38fn-next-profile-ready/READINESS.md`. ✅ 2026-10-27 [no-belief: tooling preparation]
    - [x] **C-L3-Q38FN arm P — UD with ONLY ffn_gate/up_exps IQ3_S→IQ4_XS, every other tensor at its UD type (filed + started 2026-10-24, workspace-58; operator: "check cheap PPL first").** Survey: UD keeps attn/ssm/shexp/hc at Q8_0, down_exps IQ4_NL/Q8_0, output Q6_K, gate/up mostly IQ3_S, so the old uniform file's +17.8% PPL came from degrading the Q8_0 tensors. Arm P is 96970 MiB vs 89332. v1 (09:21Z): PPL P 2.9701 vs UD 2.9761 (both without GGML_IQK, recorded as a sidecar); coherence VOID (harness ran without the serving env, so the fused decode default-ON made even UD garbage, see FD-DIV-2). v2/P2 re-run (recipe env, llama-server chat) COMPLETED 2026-10-25 and the speed A/B (pp256 >= +27%, pp5 >= +19%, tg128 >= -2.0%, INDICATIVE on one quarter) COMPLETED: **P2 PPL 2.979 (lower better, bar <= 3.10) vs paired UD 2.9868; UD control and P2 coherence PASS (p1 Paris in first 120 chars; P2 outputs 448/463 chars, common prefix 236 >= 40); speed INDICATIVE FAIL: pp256 +31.91% (pass), pp5 -6.12% (fail), tg128 -8.85% (fail) => P2 does NOT ship, no kernel-wide performance claim.** This ticks the arm-P/P2 probe (harness repair + speed half) ONLY; the parent **C-L3-Q38FN stays OPEN** (faster low-bit decode at comparable quality is not achieved) and the other INF-26 tasks are untouched. MAIN acceptance: `/mnt/raid0/llm/tmp/codex-ni-20261025-coordination/inf26-armp-MAIN-ACCEPTED.md` (audit packet sha 156b8f22..., addendum e8fe5f82...). Do not rerun the completed probes. Jobs: `/mnt/raid0/llm/tmp/ws58-q38fn-armP-20261024/`, `/mnt/raid0/llm/tmp/ws58-q38fn-armP2-20261024/`, `/mnt/raid0/llm/tmp/ws58-q38fn-armP2-speed-20261024/`. ✅ 2026-10-25 (filed 2026-10-27, workspace-58 wrap) [no-belief: probe closure on a completed INDICATIVE run; no run ClaimTuple is minted retroactively, and the cc register row is added only after this commit exists]
      - *(2026-10-27, workspace-58.)* Evidence: arm P2 recipe preserved at `docs/reference/agent-config/recipes/q38fn-armP2-20261024/` (job.sh, pins.txt, genpins.py, launcher.cmd, VERDICT.md); 101 GB GGUF `q38fn-armP2.gguf` reclaimed 2026-10-27 (no-ship); rebuild from recipe.
  - [x] **NEW-13-RM — delete the GSQ-RCO IQ3_XXS weights once NEW-13 has run (operator ruling 2026-10-22: keep until NEW-13 runs, then delete).** Path `/mnt/raid0/llm/models/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF/IQ3_XXS/` (75.84 GB, 2 shards). Order: NEW-13 arms A-D done and recorded, and VB-QUANTCMP-NEW10 captured (it needs these weights), then delete with operator-confirmed `scripts/safety/guarded_rm.sh`. Delete NEW-10's 5.07 GB logits base `/mnt/raid0/llm/tmp/new10-q38fn-20261022/out/ud_iq4xs.kldbase` in the same step unless NEW-13 reuses it; keep `VERDICT.md`, `RESULT.json` and the receipts. Done when both are gone and the deletion is recorded here. (filed 2026-10-22, workspace-58 wrap-up) **Decided 2026-10-23 (operator): KEEP the GSQ weights — not deleted (C-L3 scope to be settled); ✅ 2026-10-23.**
    - *(2026-10-23 14:0xZ, workspace-58 wrap-up.)* Both preconditions are now met: NEW-13 COMPLETE (PASS, above), and VB-QUANTCMP-NEW10 captured AND ingested into the ledger (13:55Z, `vidya-belief-substrate-program.md`). **Pending operator: keep the weights for C-L3, or delete them now** (operator-queue row OP-NEW13-RM). Premise check for that decision: the Stage-3 plan scopes C-L3 to a 27B-class IQ2_XXS dense pair, not to these Q38FN weights, so keeping them only helps if C-L3 is re-scoped to re-use Q38FN GSQ. NEW-13 does not reuse NEW-10's `ud_iq4xs.kldbase`. The VB recapture's `out/vb-capture/base-a1.kldbase` was written by the capture and is another logits base, so delete it in the same step.
- [x] **NEW-14 — Size the NEW-10 and T2 (and NEW-12, if it is ever un-held) paired task gates before they run (intake-2483#record, intake-2484).** (filed 2026-10-22 via research intake, operator-approved 2026-10-22) Replace 'a paired per-item task eval no worse than UD' with a declared margin (default 2 pp) and an item count read from the paired-TOST tables of arXiv 2608.15046, or report the margin the available n supports; add the one-sided exact degradation verdict from EV-DEGR1 beside the two-sided P-PAIRED verdict, printing n_discordant and direction.

  *NEW-14 note 2026-10-22 (workspace-58).* Helper: `scripts/autopilot/degradation_stats.py` in epyc-orchestrator (commit 0993affc; tests `tests/unit/test_degradation_stats.py`). `python -m scripts.autopilot.degradation_stats verdict --b B --c C` prints n_discordant, direction (b = baseline correct/candidate wrong vs c) and the one-sided exact p (scipy binomtest, alternative=greater); `size --p-flip P [--n N] [--margin 0.02]` prints required N, power at N and the margin N supports. Required N = ceil(p_flip*(2.486/delta)^2), one-sided alpha 0.05, 80% power (intake-2484#02; our arithmetic from the paper's SNR relation, no N table is in the paper). The 'no worse than UD' criterion is replaced by: declared margin 2 pp (default). The exact one-sided verdict tests H0 'no degradation', not equivalence within the margin, so it is printed beside the two-sided P-PAIRED verdict and the gate additionally states required N for the margin; report `margin_supported_by_n` when N falls short). For reference the dive's reading of arXiv 2608.15046 Table 1 puts pooled churn-based need near 1.9k paired items for 2 pp (stage-3 ledger A-L7); our own arithmetic gives the grid below. The paper's TOST tables themselves were not re-derived here.
| p_flip (grid, not an estimate) | delta 1 pp | 2 pp | 3 pp | 5 pp |
|---|---|---|---|---|
| 5% | 3091 | 773 | 344 | 124 |
| 10% | 6181 | 1546 | 687 | 248 |
| 15% | 9271 | 2318 | 1031 | 371 |
| 20% | 12361 | 3091 | 1374 | 495 |
  Per-gate inputs (all blanks; none invented): **NEW-10** (Q38FN IQ3_XXS/IQ3_S vs served UD-IQ4_XS) N = ____ (task-bank paired items), p_flip = ____ (measure: UD-IQ4_XS vs UD-IQ4_XS rerun on the bank, greedy); **NEW-13** has no task gate (KLD bootstrap, N=120 passages) - out of scope; **T2** (IQ4_KT vs Q4_K_M, IQ2_KT vs IQ2_XXS in ik scratch) N = ____, p_flip = ____ (measure: Q4_K_M and IQ2_XXS self-rerun flip floors). NEW-12 is HELD; if un-held, size it the same way. At 2 pp the gate needs 773-3091 items for p_flip 5-20%; a 250-item bank supports only ~3.5-7 pp.

- *NEW-12 — HELD (operator 2026-10-22: "stick to NEW-10 and then we reassess later"); no checkbox, no compute booked.* Q38FN allocation transplant plus bytes-budgeted per-tensor type allocator from the Stage-3 plan (intake-2470#record, intake-2466#record, intake-2487#record). Reassess after NEW-10's IQ3_XXS quality result. If it is ever run, use the lean form: one candidate at a time, no P0 ISTA GSQ-weights comparison, ~190 GB disk peak, and delete the Q8_0 source at the end.
