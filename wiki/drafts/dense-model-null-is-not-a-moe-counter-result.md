# A dense-model null is not a MoE-specific counter-result

**Category**: `benchmark_methodology`
**Confidence**: verified (structural: GGUF tensor inventory + source-level gate inspection + re-analysis
of the run's own sample arrays; zero inference, zero builds)
**Date**: 2026-09-14
**Source**: INF-40 reconciliation, handoff `handoffs/active/moe-spec-cpu-spec-dec-integration.md:424-436`;
GPU record `/mnt/raid0/llm/artifacts-df25/champion_anchor_20260828/champion_anchor_validation.json`;
CPU record `epyc-inference-research/data/moe-spec-bsweep-2026-08-25/`
**Folds into**: [Speculative Decoding](../speculative-decoding.md) — the 2026-09-03 compiled update
"MoE-Spec on live CPU verification batches is role-dependent"; also corrects
[Hardware Optimization](../hardware-optimization.md) §champion composition.

## The mechanism

An architecture-conditional kernel flag can only produce evidence on a model whose graph contains the
code the flag guards. `--moe-spec-budget` masks `selection_probs` **inside `build_moe_ffn`**
(`src/llama-graph.cpp:1985`, champion `c7c37a0d9`), under a three-part gate:
`budget > 0 && budget < n_expert && n_tokens >= moe_spec_min_batch`. A dense model never calls
`build_moe_ffn` at all — there is no router, no `ffn_gate_inp`, no `*_exps` tensors — so the flag's
code is **not in the graph**, not merely unreached.

The 2026-08-28 champion validation measured `--moe-spec-budget 32` on **Qwen3.8-27B-Q8_0**, which is
dense: `general.architecture qwen35`, **0 of 866 tensors** match `*exps*` or `ffn_gate_inp`, and the GGUF
carries **no `*.expert_count` key at all**. Both GPU arms therefore executed identical code. The record
already flagged the `tg128` arm as "uninformative by construction" (batch-1 never reaches
`min_batch 4`) — the same verdict applies to the `pp512` arm, for a *different and stronger* reason:
`tg128` failed one clause of the gate, `pp512` failed the model-class precondition of the whole
mechanism.

Re-analysed on its own samples (n=6/arm), the `pp512` "regression" is also not significant: medians
768.83 → 746.38 t/s = −2.92%, but **means 758.63 ± 27.80 → 745.37 ± 25.07 t/s = −1.75%, Welch
t = −0.87** with fully overlapping ranges (720.8–791.8 vs 716.9–774.1). A median-quoted delta smaller
than the per-arm spread, on a code path that cannot fire, is a null *test* reported as a null *finding*
— and then re-quoted downstream as a regression.

## The rule

1. **Before quoting a flag's delta, prove the flag's code is in the measured model's graph.** For an
   architecture-conditional flag that means a structural check (tensor inventory / metadata key), not
   "the flag was on the command line". Naming the flag is not evidence it fired; a mechanism-fire
   control is (the CPU B-sweep's `B = n_expert` gate-skip arm, bit-exact 3/3, is the right shape).
2. **An inert-arm measurement is evidence about the host and the harness, never about the mechanism.**
   It bounds run-to-run noise on that surface — a useful by-product — and must be published as such.
3. **A null on model class A is never a counter-result to a positive on model class B.** Reconciliation
   starts by asking whether the two rows are even on the same mechanism, before it appeals to surface
   (CPU vs GPU), harness (`llama-bench` vs live serving) or era. "Different surfaces, so they do not
   disagree" was the right conclusion from the wrong premise here: the rows do not disagree because
   only one of them is a measurement of MoE-Spec at all.

## Why it cost something

The dense null was carried into the handoff as "the countervailing surface" and became the stated reason
not to act on the CPU result ("Do not integrate on the +10.7% alone"), into
`autokernel-champion-aggregate.md` CH-4 as "MoE-Spec has NOT earned its keep … a regression, not a
win … fail[s] to reproduce on the surface that matters", and into two wiki pages. Reproduction on that
surface was structurally impossible. The genuine open objection to the CPU result was always the *thin*
evidence — n=3/cell, Δ ≈ 2.9σ, below `MEASUREMENT_POLICY.md`'s ≥5 reps for a ≥5% claim, with the 5-rep
confirm declined — and that objection was obscured, not supported, by the dense row.
