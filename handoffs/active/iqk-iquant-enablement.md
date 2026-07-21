# iqk IQ-quant Enablement (IQ2_XXS / IQ3_XXS / IQ2_S)

**Status**: CODE COMPLETE, **NOT BUILT, NOT VALIDATED** — blocked on a quiet inference window
**Created**: 2026-07-21 (via research-intake deep dive on intake-872/873)
**Priority**: HIGH — this is a live defect, not an experiment
**Categories**: hardware_optimization, quantization, moe_optimization
**Branch**: `iqk/enable-iquants-20260721` @ `e06f5368f`, worktree `/mnt/raid0/llm/llama.cpp-iqk-iquants` (branched from `experimental-v7-refresh-20260716` @ `8bb53c520`)
**Related**: [tq3-quantization-evaluation.md](tq3-quantization-evaluation.md), [glm52-reviewer-capability-gates.md](glm52-reviewer-capability-gates.md), [v7-promotion.md](v7-promotion.md), completed [iqk-port.md](../completed/iqk-port.md)

## Problem

`GGML_IQK=1` swaps in ik_llama's AVX-512 GEMM kernels (measured +7.9-8.8% decode on Q4_K, +22-49% prefill on other families). But iqk kernels are dispatched **per quant type**, and `iqk_typeA_supported` (`iqk_dispatch.cpp:58`) whitelisted only K-quants and legacy quants. `iqk_set_kernels_iquants` and `iqk_convert_iquants_q80_r8` were linker stubs returning `false`.

Consequence: **models whose weight bulk is IQ2/IQ3 got no iqk acceleration on those tensors**, silently, even with the flag on.

GLM-5.2 UD-IQ2_M is the motivating case. Its tensor histogram:

```
F32 709 | Q8_0 476 | Q5_K 313 | IQ2_XXS 148 | Q6_K 82 | IQ3_XXS 71 | IQ4_XS 4 | IQ2_S 2 | Q2_K 2 | Q4_K 1 | Q3_K 1
```

It is a 256-expert MoE with 8 active, so the **221 routed-expert tensors (148 IQ2_XXS + 71 IQ3_XXS + 2 IQ2_S) are the model** — the bulk of parameters and of bytes moved per token. Attention and shared experts (Q8_0/Q5_K/Q6_K) were accelerated; the part that dominates decode bandwidth and prefill FLOPs was not.

This is precisely what the port's own comment predicted — `iqk_stubs.cpp:8-12`:

> *"The registry shows ZERO use of IQ-quants … so these families are stubbed … **If/when we adopt IQ-quants (e.g. future GLM IQ2), these MUST be replaced with the real ik kernels — do not leave them stubbed for a quant we deploy.**"*

True when written. Then GLM-5.2 IQ2 was deployed and nobody returned to it.

## What changed (already committed, 3 files, +9/-2)

| File | Change |
|---|---|
| `ggml/src/ggml-cpu/CMakeLists.txt:58` | add `ggml-cpu/iqk/iqk_gemm_iquants.cpp` to the build (the 202KB kernel file was vendored but never compiled) |
| `ggml/src/ggml-cpu/iqk/iqk_stubs.cpp:26,31` | remove the two `return false` stubs so the real symbols link |
| `ggml/src/ggml-cpu/iqk/iqk_dispatch.cpp:64` | whitelist `GGML_TYPE_IQ2_XXS`, `GGML_TYPE_IQ3_XXS`, `GGML_TYPE_IQ2_S` |

Why this is cheap where the KT/trellis family is not: `IQ2_XXS=16`, `IQ3_XXS=18`, `IQ2_S=22` are **native ggml enum values**. No type registration, no `type_traits` growth, no GGUF change, no requant, no download. (The KT types are synthetic casts at 153-158 against `GGML_TYPE_COUNT=43` with no `type_traits` row — see tq3-quantization-evaluation.md.)

**IQ4_XS deliberately excluded**: `iqk_gemm_iquants.cpp` has no kernel case for it, and GLM-5.2 uses it for only 4 tensors.

**Pre-verified (static, no build):** all `GGML_TYPE_*` referenced by `iqk_gemm_iquants.cpp` resolve — `IQ2_S/IQ2_XS/IQ2_XXS/IQ3_S/IQ3_XXS` native; the `*_R4` repack variants via the `iqk_ext_types.h` shim; `Q8_2_X4` via `#define … 99` in `iqk_config.h:18` and used only inside comments in this file.

## Why it is NOT on production v7

Two hard reasons, both verified 2026-07-21:

1. **Blast radius is 4 models, not 1.** Registry scan for IQ2/IQ3/IQ1 quants:
   | Role | Quant |
   |---|---|
   | `qwen35_122b_iq2m` | UD-IQ2_M |
   | `glm_52_ud_iq2m` | UD-IQ2_M |
   | `qwen3_next_80b_a3b_instruct_iq2m_local` | IQ2_M |
   | `hy3_angelslim_iq1m_mtp` | IQ1_M |
   A no-regression claim requires evidence per affected model, which requires inference.
2. **A decision-grade benchmark was in flight on the production v7 binary** at the time of the change (`v7_quality_gate_runner.py`, architect-model-selection-bench, aime25 — including arm `A1_qwen35_122b_iq2m`, one of the affected models). Host load average was ~46 with 7 llama-servers resident. Rebuilding production v7 would have corrupted an active measurement.

Per CLAUDE.md the production kernel is FROZEN and all kernel work happens on `llama.cpp-experimental` branches anyway; this follows that workflow.

## Outstanding tasks (require a quiet window)

- [ ] **B1 — Build.** `cmake --build` the worktree `/mnt/raid0/llm/llama.cpp-iqk-iquants` with the same flags as the v7 CPU build. First real risk gate: `iqk_gemm_iquants.cpp` has never been compiled in this tree. Expect possible fallout from the `*_R4` shim types or the `Q8_K_R8` converter return path (the known OOB hazard — the `iqk_row_size()` fix from commit `715383cde` should already cover it, but verify).
- [ ] **B2 — Correctness first, speed second.** For EACH of the 4 affected models: short coherence + garbage check with `GGML_IQK=1` vs `GGML_IQK=0` on the same prompt/seed. iqk is **not bit-exact by design**, so the gate is output sanity and eval parity, NOT bit-compare. Pair every speed number with a correctness check.
- [ ] **B3 — Speed, GLM-5.2 first.** `llama-bench` under the canonical baseline protocol (`taskset -c 0-95 -t 96 -fa 1`, OMP env stack mandatory) with `GGML_IQK=1` vs `=0`. **Expect prefill-dominant, decode-modest**: decode at 2-3 bpw is deep in the bandwidth-bound regime where iqk measured ~0% on Q8_0, whereas prefill gains on other families ran +22-49%. GLM prompts run 3-12K tokens, so prefill is the operative axis for that role.
- [ ] **B4 — Regression check on the non-IQ path.** Confirm K-quant/legacy models are byte-for-byte unaffected (the dispatch change is additive, so this should be a formality — but it is the claim that lets this reach production).
- [ ] **B5 — Promote.** If B2-B4 pass, fold into the next experimental→production promotion per the four-step workflow. Do NOT hand-patch production v7.

## Decision gates

- **B2 fails (incoherent output on any affected model)** → do not promote; isolate whether it is the kernel or the convert path, and consider whitelisting a subset (e.g. IQ2_XXS only).
- **B3 shows a decode regression** → still potentially worth promoting if prefill gains dominate for the GLM role, but that becomes an operator call with numbers attached, not an assumption.
- **B4 shows any non-IQ delta** → stop; the dispatch change was supposed to be additive and a delta means something else moved.

## Key files

- Worktree: `/mnt/raid0/llm/llama.cpp-iqk-iquants` (branch `iqk/enable-iquants-20260721`)
- Kernel: `ggml/src/ggml-cpu/iqk/iqk_gemm_iquants.cpp` (set_kernels `:2760-2791`, converters `:2810-2813`)
- Dispatch: `ggml/src/ggml-cpu/iqk/iqk_dispatch.cpp:58`
- Stubs: `ggml/src/ggml-cpu/iqk/iqk_stubs.cpp`
- GLM-5.2 tensor map: `/mnt/raid0/llm/tmp/gguf-inspect-20260721/`

## Reporting instructions

Append build/bench artifacts and their protocol ids here, update [tq3-quantization-evaluation.md](tq3-quantization-evaluation.md) with the outcome, and flip B1-B5 with `✅ YYYY-MM-DD`. All numbers are OBSERVATIONS under MEASUREMENT.md until run under a codified recipe with operator approval.
