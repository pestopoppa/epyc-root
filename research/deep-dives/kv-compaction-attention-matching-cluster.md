# KV Compaction Deep-Dive Cluster: Attention Matching + Related Multi-Agent KV Approaches

**Date**: 2026-04-13
**Entries analyzed**: intake-350 (Latent Briefing), intake-351 (Attention Matching), intake-352 (KVCOMM), intake-353 (LRAgent)
**Trigger**: Research intake of github.com/CuriousCaliBoi/latent-briefing

## Executive Summary

Attention Matching (2602.16284) is the standout finding: first closed-form decomposition of KV compaction, 50x compression on narrative QA, Pareto-dominant over all token-selection baselines. At 10x compression (our realistic target for coding contexts), HighestAttnKeys-fast achieves near-lossless quality in ~14 seconds. Implementation path for llama.cpp is surgical: Python preprocessing for compaction + one-line attention bias addition in decode kernel.

The three other entries (Latent Briefing, KVCOMM, LRAgent) are not applicable to our stack due to broken implementations, hard same-model requirements, or LoRA-specific mechanisms.

## Detailed Findings

### intake-350: Latent Briefing (github.com/CuriousCaliBoi/latent-briefing)

**Source code audit revealed critical issues:**

1. **PGD beta optimization is a no-op.** The loss function computes `MSE(Q @ (K_kept * beta)^T, Q @ K_kept^T)` — optimizing beta to reproduce the KEPT-ONLY attention pattern, not the FULL-CACHE pattern. The `target` variable (computed from K_full) is created but never referenced in the loss. Beta converges to ~1.0.

2. **Ridge C2 correction is a no-op.** The V_full parameter is accepted but ignored. Self-reconstruction with X=Y=V_kept and lambda=1e-4 produces a transform matrix negligibly different from identity.

3. **"Cross-model KV transfer" is misleading.** Claude produces TEXT via Anthropic API. Qwen3-14B encodes that text through its own forward pass. The KV cache being compacted is Qwen3's own — no internal representations cross the model boundary. The "cross-model" aspect is standard multi-agent text-based communication.

**What it actually is:** Attention-score MAD thresholding (token selection) with broken correction steps, wrapped in a standard text-passing multi-agent architecture. The scoring and selection steps (RMS aggregation, MAD threshold, GQA handling) are correctly implemented but are the well-covered part of the literature.

**Assessment**: novelty=low, relevance=low, verdict=not_applicable. The repo should not be used as an implementation reference. The Attention Matching paper (intake-351) is the proper formalization.

### intake-351: Fast KV Compaction via Attention Matching (2602.16284)

**Authors**: Adam Zweiger, Xinghong Fu, Han Guo, Yoon Kim (MIT + MIT-IBM Watson AI Lab)

**Core method**: Construct synthetic compact KV entries (C_k, beta, C_v) that reproduce both attention outputs AND attention mass of the original cache. The key innovation is per-token scalar biases (beta) that allow each retained key to represent the mass of multiple removed keys.

**Decomposition into closed-form subproblems** (no gradient descent):
1. Select compact keys C_k from original key subset (RMS heuristic or OMP)
2. Fit beta via NNLS (nonneg least squares) to match attention mass
3. Fit C_v via OLS to match attention outputs

**Benchmark results (Qwen3-4B)**:

| Compression | QuALITY Accuracy | LongHealth Accuracy | Notes |
|---|---|---|---|
| 1x (full context) | 72.1% | ~70% | Baseline |
| 10x | ~71% | ~65% | Near-lossless on narrative |
| 50x | ~71% (AM-OMP) | ~55% | Information-dense degrades |
| 100x | degrades | degrades further | Cartridges beats AM here |

**Online compaction (AIME 2025)**: 2048 physical KV + 6 repeated 50% compactions = 8192 effective context = 13/30, matching uncompacted 8192 result. Reasoning state preserved across consecutive compactions.

**Timing (60k tokens, Gemma-3-12B, H200)**:
- HighestAttnKeys-fast (repeat-prefill only): ~14s total
- HighestAttnKeys (+ self-study): ~153s total
- OMP: ~710s total
- OMP-fast: ~250s total

**vs Expected Attention (our S1 candidate)**: AM consistently outperforms KVzip (top KVPress method) at all ratios, especially 20x+. Gap narrows at 5-10x. Expected Attention's advantage: simpler implementation (pure token selection, no attention biases needed).

**Failure modes**:
- Information-dense content (LongHealth, medical records) degrades faster than narrative
- Coding benchmarks NOT TESTED (listed as TODO in reference repo)
- GPU-only — all linear algebra via PyTorch CUDA
- Key subset restriction limits quality at extreme compression (100x)
- No inference engine integration (vLLM/SGLang/llama.cpp TODO)

**Implementation path for EPYC stack**:

| Component | Where | Effort |
|---|---|---|
| Attention scoring + key selection | Python (offline) | Trivial — forward pass + argsort |
| Beta fitting (NNLS) | Python (scipy.optimize.nnls) | Trivial |
| Value fitting (OLS) | Python (numpy.linalg.lstsq) | Trivial |
| Compact KV serialization | Python → llama.cpp format | Medium |
| Attention bias in decode | C++ (llama.cpp attention kernel) | Medium — one-line score addition |
| Logical vs physical length | C++ (llama.cpp KV metadata) | Medium — RoPE position tracking |
| llama-server slot loading | C++ (new API endpoint) | Medium |

The compaction step does NOT need ggml — it's offline preprocessing. The decode-side change (attention bias) is the one hard requirement.

### intake-352: KVCOMM (2510.12872, NeurIPS'25)

**Mechanism**: Anchor-based offset estimation for KV cache reuse across agents with diverging prefixes. Stores observed KV offsets under varying prefix contexts, interpolates offsets for new text based on embedding distance.

**Triple hard blocker for our stack**:
1. Same-model requirement is MATHEMATICAL (shared W_K, W_V, W_Q). Our Claude+Qwen3 heterogeneous stack is incompatible. Even different quantization levels break the assumption.
2. Prefill-only speedup. Our bottleneck is decode (memory bandwidth on EPYC). KVCOMM actually HURTS decode indirectly — anchor pool consumes memory, reducing effective KV cache budget (admitted as cause of AIME accuracy drops).
3. No llama.cpp path. Requires direct tensor-level KV manipulation. Built on HuggingFace transformers with full Python tensor access.

**Quality issues on hard reasoning**: AIME shows 8-11 point accuracy drops despite 71-78% reuse rates. Not quality-neutral.

**Assessment under current architecture**: relevance=low, verdict=not_applicable. Our heterogeneous stack (Claude+Qwen3 at mixed quants) is incompatible.

**Reassessment: applicable to homogeneous worker pools within the orchestrator.** The key insight: KVCOMM doesn't need the ENTIRE stack to be homogeneous — only the collaborating agents. When the orchestrator delegates to 3+ parallel coder-32B instances (same model, same quant) all sharing the same codebase context (10K-50K tokens), KVCOMM eliminates redundant prefill across the worker pool. Example: frontdoor → architect → 3x coder-32B on NUMA 0/1/2, each implementing different functions from the same plan against the same codebase. Without KVCOMM: 3 independent 50K-token prefills. With KVCOMM: ~1.3x prefill for 3 agents.

Compounds with AM compaction: AM compacts shared codebase KV (10x reduction: 50K → 5K entries), then KVCOMM shares the compact result across worker instances. AM reduces size, KVCOMM eliminates redundant computation — complementary.

Open questions: (1) offset estimation with q4_0 quantized KV untested, (2) cross-NUMA IPC for anchor pool, (3) AIME 8-11pp drop on hard reasoning. Upgraded to relevance=medium, verdict=worth_investigating.

### intake-353: LRAgent (2602.01053)

**Core principle**: KV cache decomposes into shared base (from pretrained weights W_0) + low-rank adapter delta (from LoRA A*B). Base cache has >0.95 cosine similarity across agents; adapter delta is 14-27x smaller in norm. Store only the low-rank form of the adapter delta (16x compression of adapter-specific component).

**Flash-LoRA-Attention**: Exploits associativity — compute `(P * V_lr) * B` instead of `P * (V_lr * B)`. Intermediate result is (L x r) instead of (L x d), dramatically cheaper. Up to 1.35x throughput.

**Why not_applicable is correct**: Without LoRA adapters, same tokens produce identical KV entries. The decomposition principle requires the additive structure W = W_0 + A*B. Standard prefix caching handles the sharing case without LoRA. No hidden generalizable insight beyond what we already have.

## Revised Assessment Matrix

| Entry | Original Assessment | Post-Deep-Dive | Change |
|---|---|---|---|
| intake-350 | medium novelty, medium relevance, worth_investigating | low novelty, low relevance, not_applicable | DOWNGRADE — broken corrections, misleading cross-model claim |
| intake-351 | high novelty, high relevance, new_opportunity | high novelty, high relevance, new_opportunity | CONFIRMED — realistic target is 10-20x not 50x for us |
| intake-352 | medium novelty, medium relevance, worth_investigating | medium novelty, medium relevance, worth_investigating | REFINED — not applicable to full heterogeneous stack, but applicable to homogeneous worker pools (parallel coder-32B instances). Compounds with AM. |
| intake-353 | medium novelty, low relevance, not_applicable | medium novelty, low relevance, not_applicable | CONFIRMED |

## Revised Recommended Actions

1. **Implement AM HighestAttnKeys-fast as Python preprocessing tool.** Target 10x compression on Qwen2.5-Coder-32B coding contexts. Use adamzweiger/compaction as reference. Benchmark against Expected Attention (S1 in triattention handoff) on same tasks.

2. **Prototype llama.cpp attention bias support.** The one surgical change: `score[j] += beta[j]` in the attention inner loop. Plus KV metadata for logical vs physical length. This unblocks both AM compaction and potentially other latent-space KV methods.

3. **Expected Attention (S1) vs AM comparison**: At 5-10x, Expected Attention may be sufficient and simpler (no attention biases needed). At 20x+, AM dominates. Run both on the same benchmark to determine the crossover point for our models.

4. **Do NOT use Latent Briefing repo.** Broken corrections, misleading claims. The AM paper + reference implementation is the correct starting point.

5. **Track KVCOMM for parallel worker pools.** When orchestrator delegates to 3+ same-model coder instances, KVCOMM eliminates redundant prefill of shared codebase context. Compounds with AM compaction. Open: q4_0 offset estimation, cross-NUMA IPC. Drop LRAgent (LoRA-specific, no path).
