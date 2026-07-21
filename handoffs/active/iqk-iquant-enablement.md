# iqk IQ-quant Enablement — a live defect on every IQ-quant model we run

**Status**: CODE COMPLETE, **NOT BUILT, NOT VALIDATED** — blocked on a quiet inference window
**Created**: 2026-07-21 (via research-intake deep dive on intake-872/873)
**Priority**: HIGH — this is a live defect, not an experiment. We ship an acceleration flag that silently skips the majority of the weights on four deployed models.
**Branch**: `iqk/enable-iquants-v7-20260721` @ `f78ec18fe`, worktree `/mnt/raid0/llm/llama.cpp-iqk-iquants`, branched **fresh from `production-consolidated-v7` @ `6ad45fa3f`** per the four-step workflow
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

- [ ] **B1 — Build.** `cmake --build` the worktree with the v7 CPU flags. First real risk gate: `iqk_gemm_iquants.cpp` has never been compiled in this tree. Watch for fallout from the `*_R4` shim types and the `Q8_K_R8` converter return path (the `iqk_row_size()` fix from `715383cde` should already cover the known OOB hazard — confirm it does).
- [ ] **B2 — Correctness before speed, per model.** For each of the four models: short coherence + garbage check with `GGML_IQK=1` vs `GGML_IQK=0`, same prompt and seed. iqk is **not bit-exact by design**, so the gate is output sanity and eval parity, never bit-compare. Pair every speed number with a correctness check.
- [ ] **B3 — Speed.** `llama-bench` under the canonical baseline protocol (`taskset -c 0-95 -t 96 -fa 1`, OMP env stack mandatory), `GGML_IQK=1` vs `=0`, prefill and decode reported separately. Start with **Qwen3-Next-80B** (largest covered share, 54%) and **GLM-5.2** (highest operational value), then the other two.
- [ ] **B4 — Non-IQ regression check.** Confirm K-quant/legacy models are unaffected. The dispatch change is purely additive so this should be a formality — but it is the claim that lets this reach production.
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
