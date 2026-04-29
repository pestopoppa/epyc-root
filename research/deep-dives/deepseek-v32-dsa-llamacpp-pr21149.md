# DeepSeek-V3.2 + DSA — Deep Dive

**Source intake**: intake-506 (arxiv:2512.02556)
**Date**: 2026-04-29
**Status**: FACT-CHECKED against llama.cpp upstream as of 2026-04-29

## TL;DR

DeepSeek-V3.2 introduces **DSA (DeepSeek Sparse Attention)**, a two-stage mechanism: a **Lightning Indexer** (FP8, head-weighted scorer with block-64 quantized key cache) selects top-k=2048 tokens, then standard MLA runs on the selected subset. Core attention compute drops from O(L²) to ~O(L·k).

**The implementation status I previously claimed ("no llama.cpp DSA forward pass exists; we'd need a fork patch") was WRONG.** Active draft PR exists upstream — see "Reality Check" below. The genuine question is *when* to pull, not *whether* to write it.

## DSA mechanism (from V3.2 technical report)

```
Input tokens
   │
   ▼
┌───────────────────────────────────┐
│ Lightning Indexer (per layer)     │
│   - FP8 head-weighted scorer      │
│   - Separate index-key cache      │
│     (block-64 quantized)          │
│   - Output: per-query top-k=2048  │
│     token indices                 │
└───────────────────────────────────┘
   │
   ▼ (mask construction)
┌───────────────────────────────────┐
│ MLA forward pass on selected      │
│ tokens only                       │
│   - Standard MLA KV cache         │
│   - Sparse attention via mask     │
└───────────────────────────────────┘
```

Composition with MLA is **orthogonal**:
- MLA compresses each token's KV representation (low-rank latent)
- DSA selects *which* tokens to attend to per query
- Two independent compression axes — they multiply, not interfere

## Reality check: llama.cpp upstream state (verified 2026-04-29)

Prior claim from glm51-reap-cpu-evaluation.md: "indexer is not yet supported." That was true for **PR #19460** (merged Feb 2026) which added GLM-MoE-DSA arch loader-only. **It is no longer the full picture.**

Current state per direct GitHub query:

| PR/Issue | State | Date | What it adds |
|----------|-------|------|--------------|
| **#19460** | merged | 2026-02-13 | GLM-MoE-DSA architecture (loader, falls back to dense MLA) |
| **#21785** | merged | — | DeepSeek V3.2 chat template + parser |
| **#22102** | merged | 2026-04-20 | GLM-DSA crash fix in vocab-only tokenize |
| **#21149** | **DRAFT, ACTIVE** | opened 2026-03-29, last commit **2026-04-28** | **Full DSA implementation by fairydreaming** |
| #20363 | open (tracking) | — | Feature request umbrella for DSA indexer |
| #21458 | open | — | `GGML_OP_GATHER` proposal supporting #21149 |
| #21696 | open | — | Tensor parallelism for `glm-dsa` |
| #21162 | closed | — | CUDA `top_k()` crash on large tensors (resolved) |

PR #21149 implements:

- New ggml ops: `GGML_OP_HADAMARD`, `GGML_OP_LIGHTNING_INDEXER`
- New KV cache classes: `llama_kv_cache_dsa`, `llama_ik_cache` (indexer keys)
- Specialized **flash-attention MMA kernel sparse path** for token generation
- Conversion tooling: requires `add_bos_token=true` in tokenizer_config.json
- **All three backends working**: CPU ✅, CUDA ✅ (WMMA-optimized), Vulkan ✅ (after #22177 f16 FILL fix)
- Metal: not mentioned — likely the lone gap

**Author's own caveat (from PR description, paraphrased)**: "Due to the way it's currently implemented it doesn't improve long context performance yet." The plumbing is there; the speed-up isn't fully realized yet.

**Author**: fairydreaming — known DeepSeek-series llama.cpp contributor, shipped V2/V3 support. High-credibility source.

**Status**: Draft, awaiting architectural confirmation and code review. ~30 days open with regular activity.

## What this changes for us

The "highest-signal finding" from the intake report should be reframed:

**Old framing**: "DSA implementation gap is the blocker; any single fork patch unblocks two top-tier models."

**Corrected framing**: "DSA implementation is *being built upstream by a respected contributor*. Our action is **track + test**, not **write from scratch**."

Concretely:

1. **Pull-and-test on EPYC** is now feasible. PR #21149 + V3.2 GGUF (Q4_K_M, ~380 GB) fits in our 1.1 TB RAM with substantial headroom. CPU backend is supported per author's claim.
2. **Fork integration** (cherry-pick into `production-consolidated-v3`) becomes a real option once the PR stabilizes — likely some weeks out given the "long-context performance not improved yet" caveat. The pre-merge PR can also be cherry-picked early as a feature branch.
3. **GLM-5.1 unblocks for free**: PR #21149 reuses the indexer ops and KV cache classes for any DSA model. GLM-5.1 (555B-A14B, Q4_K_M ~325 GB) becomes runnable on EPYC at the same time.
4. **Three concrete ways to contribute upstream** — see "How we'd contribute" section below for the full breakdown. Short version: (a) post CPU-only benchmark numbers as comment, (b) pick up the deferred prompt-processing sparse path follow-on PR, (c) add AVX-512BW SIMD optimization for `GGML_OP_LIGHTNING_INDEXER` on Zen 5.

## How we'd contribute

Author fairydreaming explicitly flagged help requests + deferred work in the PR description and recent commits. Three sub-tracks fall out cleanly, with different effort / visibility / risk profiles:

### D1 — Pull / build / smoke test (lowest-hanging fruit)

**Author quote (paraphrased from PR description)**: *"I really could use some help with verifying the implementation correctness. If you have large GPU cluster and can run some benchmarks..."*

Our angle: we don't have a GPU cluster, but we *do* have EPYC 9655 with 1.1 TB RAM — V3.2 Q4_K_M (~380 GB) fits comfortably. **The PR is currently CUDA-dominated and has zero CPU-only benchmarks.** A first CPU data point is independently useful even if our t/s numbers are slow vs. the H100 reference.

Concrete deliverable:
- Pull PR #21149 as a feature branch in `llama.cpp-experimental`
- Build on EPYC (CMake + standard cpu/cuda-off configuration)
- Run the canonical baseline (per `feedback_canonical_baseline_protocol`): `taskset -c 0-95 -t 96 -fa 1 --mmap 0 numactl --interleave=all`
- Quality gate: GSM8K + GPQA-Diamond at 32K context; replicate "V3.2-Exp ≈ V3.1-Terminus" claim
- Throughput gate: t/s at 16K / 64K / 128K context, comparing V3.2 with DSA active vs MLA-only baseline
- Post numbers as a comment on PR #21149

Effort: **~1 day** of focused work (mostly waiting for downloads + benchmark cycles).
Gating: **`feedback_no_concurrent_inference.md` rule** — explicit user approval required before any benchmark execution. The benchmark itself is several hours of EPYC time and would clash with anyone else's measurement work.

### D2 — Prompt-processing sparse path follow-on PR

**Author quote (paraphrased)**: *"Token generation (tg) shows 25-35% speedup at 131K context; prompt processing (pp) shows minimal gains. ... only for very long contexts ... a separate PR for advanced sparse fattn kernel optimization."*

The PR's current sparse path applies to token generation but not to prompt processing. Author identifies extending it as a separate PR. **This is the deferred work item that closes the long-context-speedup gap** — it's the thing preventing the headline DSA benefit from materializing.

Concrete deliverable:
- New feature branch off PR #21149
- Extend the sparse fattn kernel to consume the same DSA top-k mask in prompt-processing mode
- The current code path uses `ggml_get_rows()` on KQ mask for token gen; extension to PP requires either invasive `ggml_get_rows()` changes (author flagged this as messy) OR a new sparse fattn kernel variant that accepts top-k indices as input
- Validate quality preserved (PPL bit-exact via `llama-perplexity` 32-chunk gate) and throughput improvement on long-context PP
- Open as a separate upstream PR or as a comment+patch on #21149

Effort: **~1-2 weeks** of focused kernel work.
Visibility: **High** — this is real upstream contribution territory, not just a comment.
Risk: requires CUDA/CPU kernel expertise. Our `cpu-shape-specialized-gemv-decode` track shows we have CPU ggml expertise; CUDA side may need a co-contributor or be CPU-only as v1.

### D3 — AVX-512BW Lightning Indexer optimization (Zen 5 SIMD)

**Author observation (from recent commits)**: *"ggml : optimized GGML_OP_LIGHTNING_INDEXER (added WMMA kernel >= Ampere)"* — the CUDA path got a WMMA optimization on 2026-04-28. The CPU path is presumably scalar or unoptimized.

Our angle: we have established Zen 5 SIMD expertise per `project_zen5_vnni_vs_maddubs` memory (VPMADDUBSW 2/cycle beats VPDPBUSD 1/cycle on Zen 5) and per `project_q8_8x8_avx512bw_outcome` memory (AVX-512BW 8x8 Q8_0 kernel: +31.8% at 1t, +1-3% at 12-96t, production-viable). **The Lightning Indexer's FP8 head-weighted scoring with block-64 quantized key cache is exactly the kind of operation our existing SIMD work targets.**

Concrete deliverable:
- Profile current CPU path of `GGML_OP_LIGHTNING_INDEXER` with `perf record` to confirm it's compute-bound (not BW-bound — per `feedback_cpu_decode_bw_bound`, BW-bound work doesn't benefit from SIMD optimization)
- If compute-bound: write AVX-512BW kernel for the indexer's dot-product-and-top-k path. Template from existing `gemv_q8_0_8x8_q8_0_avx512bw` in `arch/x86/repack.cpp`
- Run before-vs-after benchmarks at 16K / 64K / 128K context
- Falsify or confirm hypothesis: "indexer FP8 emulation overhead kills DSA's O(L·k) advantage on CPU"

Effort: **~1 week** including profiling + kernel development + benchmark sweep.
Visibility: **High** — first CPU SIMD optimization on the DSA path.
Risk: profile may show the indexer is BW-bound after all (memory traffic dominates), in which case SIMD optimization is a no-op and we should redirect to D2. The profile step is the gate.

### 2-models-for-1 leverage

All three sub-tracks pay off twice. PR #21149's DSA infrastructure is reused identically for GLM-MoE-DSA (the architecture GLM-5.1-555B-A14B uses, per `glm51-reap-cpu-evaluation.md`). When PR #21149 stabilizes (with or without our contributions), GLM-5.1 unblocks the same week.

## Comparison: DSA vs our deployed retrofit selection methods

| Axis | DSA (intake-506) | Expected Attention (deployed, intake-288) | TriAttention (intake-284) | Attention Matching (intake-351, deployed) |
|------|-----------------|-------------------------------------------|---------------------------|------------------------------------------|
| **When** | training-time integrated | post-hoc retrofit | post-hoc retrofit | post-hoc retrofit |
| **Mechanism** | learned FP8 indexer | Gaussian future-query model | trigonometric K/V scoring | NNLS+OLS attention-mass match |
| **Compression** | top-k=2048 (fixed) | k% eviction (configurable) | per-head budget | k× compression ratio (NNLS-fitted) |
| **Runtime cost** | one indexer forward pass / query | one Gaussian MM / query | trigonometric scoring | NNLS+OLS solve / compaction |
| **Can stack with quantization?** | yes (already FP8 internally) | yes (Hadamard q4_0 stacking, S3 gate) | unknown (vLLM-only) | yes (deployed with Hadamard) |
| **Llama.cpp status** | PR #21149 (draft) | deployed | not ported | deployed |
| **EPYC actionability** | 30 days out | now | wait | now |

**Hypothesis worth testing**: integrated selection (DSA) should preserve quality better than retrofit selection at high compression ratios because the indexer is co-trained with the model weights. Our existing S1 (PPL at 50% eviction) gate from `triattention-kv-selection.md` would directly apply — when DSA lands, run the same gate on V3.2 and compare against retrofit Expected Attention numbers on Qwen2.5-7B.

## Risks / caveats

1. **PR #21149 long-context speed-up not yet realized** per author — if we test now we might not see DSA's headline benefit. Wait for the optimization passes.
2. **DSA top-k=2048 is fixed** in V3.2's training. Generalization to short-context or non-retrieval workloads not characterized — could be a non-issue (top-k clamping for short context is degenerate to full attention) but unverified.
3. **RoPE-in-indexer bug** flagged early in PR cycle (now fixed). Suggests subtle correctness traps in the indexer — re-validate quality (PPL, GSM8K parity vs V3.1) before trusting decode speed numbers.
4. **V3.2-Exp slightly regresses on Humanity's Last Exam vs V3.1** per third-party. DSA isn't pure pareto.
5. **FP8 lightning indexer** is a CPU-unfriendly compute pattern. PR claims CPU works but the indexer overhead at 192-thread EPYC is unmeasured. Could be that decode throughput on CPU is dominated by indexer FP8 emulation, killing the theoretical O(L·k) advantage.

## Action items (ranked)

1. **Watch PR #21149**: subscribe / poll weekly. Trigger event for our action: PR description updated to remove the "doesn't improve long context performance yet" caveat, OR maintainer review with merge intent.
2. **When PR stabilizes** (or when fairydreaming flags it ready for testing): pull as feature branch in `llama.cpp-experimental`, build on EPYC, run smoke test on V3.2-Exp Q4_K_M GGUF (~380 GB needed — verify disk space first; we have 3.7 TB raid0 per `user_hardware` memory).
3. **Quality gate**: compare V3.2 with DSA active vs V3.1 baseline on GSM8K + GPQA-Diamond at 32K context. Replicate the V3.2-Exp ≈ V3.1-Terminus claim from the PR description.
4. **Decode throughput gate on CPU**: measure t/s at 16K, 64K, 128K context on EPYC 9655 96-thread bind. Compare against MLA-only V3.1 baseline. **Hypothesis to falsify**: indexer FP8 overhead dominates on CPU and DSA's O(L·k) advantage is GPU-only.
5. **GLM-5.1 follow-on**: same tests on GLM-5.1 once V3.2 path validated. The 2-models-for-1 leverage holds; the integration cost is shared.
6. **Optional upstream contribution**: post EPYC CPU benchmark numbers as a comment on PR #21149. Adds a useful CPU-only data point to a PR currently dominated by CUDA results.

## Cross-references

- `/workspace/handoffs/active/glm51-reap-cpu-evaluation.md` — the GLM-5.1 evaluation that's been gated on this exact DSA implementation
- `/workspace/handoffs/active/triattention-kv-selection.md` — retrofit-vs-integrated selection comparison frame, S1 PPL gate template
- `/workspace/handoffs/active/multiscreen-attention-evaluation.md` — sub-quadratic attention survey, DSA cluster
- `/workspace/handoffs/active/llama-cpp-fork-rebase.md` — already carries the V3.2 chat template commit (1c0d9081f); cherry-pick target for #21149
- intake-502 (KSA) — explicitly cites V3.2 as same first-principle of sequence-level KV compression
- arxiv:2502.11089 (NSA) — DSA's parent paper

## Notes

The "we'd need to write a fork patch" framing was generated by extrapolation from a stale glm51 handoff line ("indexer not yet supported") that was true for PR #19460 in February but no longer reflects upstream state. Lesson: when the action plan turns on a missing piece of infrastructure, *check the actual repo* before committing to the framing — `gh pr list` / `gh issue list` against `ggml-org/llama.cpp` would have caught this in 30 seconds.
