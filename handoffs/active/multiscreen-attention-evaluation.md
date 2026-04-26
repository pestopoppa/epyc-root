# Multiscreen Attention — Evaluation for EPYC Inference

**Status**: active (literature survey complete 2026-04-14, priority ranking established)
**Created**: 2026-04-04 (via research intake)
**Updated**: 2026-04-21 (monitoring confirmed — no new pretrained checkpoints; priority ranking unchanged from 2026-04-14 survey)
**Categories**: kv_cache, inference_serving, ssm_hybrid
**Scope note**: This handoff expanded beyond Multiscreen evaluation into a comprehensive sub-quadratic attention mechanism survey. Multiscreen-specific evaluation is Section 1. Log-Linear GDN readiness tracked in [log-linear-gated-deltanet-readiness.md](log-linear-gated-deltanet-readiness.md).

## Status as of 2026-04-21

Backburner survey — awaiting pretrained weight releases for the prioritized architectures (Diff Attn V2, MoBA, Multiscreen). No upstream movement detected since 2026-04-14 survey. Section 1 (Multiscreen evaluation) remains gated on Section 2 priority items shipping weights first.

## Objective

Evaluate the Multiscreen architecture (arXiv:2604.01178) as a potential next-generation attention mechanism for EPYC inference. Multiscreen replaces softmax attention with absolute query-key screening, achieving 40% parameter savings and 2.3-3.2x latency reduction at 100K contexts.

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-256 | Screening Is Enough — Multiscreen Architecture | high | new_opportunity |
| intake-464 | FlashAttention-3 (arXiv:2407.08608) | medium | worth_investigating — canonical Hopper attention paper (added 2026-04-26). DGX Spark prep + CPU producer/consumer thread-split analog candidate. |

## Key Claims to Verify

- 40% parameter savings at comparable validation loss
- 2.3-3.2x inference latency reduction at 100K context
- Near-perfect retrieval at context lengths far beyond training
- Stable training at learning rates where Transformers diverge

## Relevance to EPYC

1. **vs Delta Net**: Our Qwen3.5 hybrid models use Delta Net (gated linear attention). Multiscreen preserves the attention paradigm but makes it sub-quadratic — potentially compatible with existing KV cache and speculation infrastructure (unlike Delta Net which broke all tree speculation)
2. **Parameter efficiency**: 40% fewer parameters for same quality would shift model selection calculus — smaller models could replace larger ones
3. **Long context**: Our models degrade at long context; Multiscreen claims stable performance beyond training length
4. **llama.cpp compatibility**: Key blocker — no GGUF support exists. Would require implementing screening mechanism in ggml

## Open Questions

- Will any major model provider (Google, Meta, Qwen) adopt Multiscreen architecture?
- Can screening be implemented efficiently in ggml/llama.cpp?
- Is the 2.3-3.2x speedup achievable on CPU (EPYC) or only GPU?
- How does Multiscreen interact with KV cache quantization (Hadamard)?
- Does screening mechanism support speculative decoding?

## Blockers

- No pretrained Multiscreen models available for download
- No GGUF/llama.cpp implementation exists
- Paper is very new (April 2026) — needs community validation

## Notes

This is a WATCH item, not an implementation item. Monitor for:
1. Community reproduction of results
2. Model releases using Multiscreen architecture
3. llama.cpp PRs implementing screening mechanism

## Expanded Attention Mechanism Cluster (2026-04-12 research intake)

Three additional cross-head attention mechanisms identified during deep-dive. Together with Multiscreen, these form a 2025-2026 cluster of alternatives to standard MHA. All require pretraining — no retrofit possible.

| Mechanism | Intake | FlashAttention | Key Benefit | EPYC Notes |
|-----------|--------|----------------|-------------|------------|
| **IHA** (Interleaved Head Attention) | intake-333 | YES (mixes before attention) | +112% RULER at 16K multi-key retrieval. MHA ⊂ IHA strictly. | **Priority watch** — FlashAttention-compat is key for our llama.cpp stack |
| **MEA** (Explicit Multi-head Attention) | intake-342 | YES (HLC on K/V) | 50% KV cache reduction via virtual heads. GroupNorm critical. | KV compression directly useful for memory-constrained inference |
| **KHA** (Knocking-Heads Attention) | intake-343 | YES (absorbed at inference) | **Zero inference overhead** (linear variant absorbed into projections). V-only interaction. | Prefer KHA-trained models when available — zero cost at inference |

**Ranking for EPYC**: IHA (most expressive, FlashAttention-compat) > MEA (KV compression bonus) > KHA (zero inference cost, but lower expressivity) > Multiscreen (most radical, no implementations)

**Monitor for**: GGUF implementations of models trained with any of these mechanisms. None currently available.

---

## Literature Survey: Sub-Quadratic Attention for CPU Inference (2025-2026)

Compiled 2026-04-14. Target: AMD EPYC 9655 (192 threads), all-CPU inference via llama.cpp.

### 1. Mechanisms Requiring Pretraining (Architecture Changes)

**Native Sparse Attention (NSA)** — DeepSeek, Feb 2025 (arXiv:2502.11089)
ACL 2025 Best Paper. Three parallel branches: compressed attention (coarse), selected attention (fine-grained), sliding window (local). Sub-quadratic scaling; substantial speedups on 64K sequences. Foundation for DeepSeek V3.2's DSA. vLLM/SGLang have GPU kernel support (SM90+ only). No llama.cpp support; GPU-centric design (block-sparse CUDA kernels).
- CPU applicability: **low** (hardware-aligned to GPU tensor cores)
- llama.cpp compat: **unlikely** without major porting
- Verdict: **monitor_only** — wait for CPU-friendly reformulation

**MoBA (Mixture of Block Attention)** — MoonshotAI, Feb 2025 (arXiv:2502.13189)
Applies MoE routing to attention blocks. Queries dynamically select relevant KV blocks. 6.5x prefill speedup at 1M tokens, 16x at 10M. Llama-8B-1M-MoBA model exists (128K-1M context). Deployed in Kimi production. FlashMoBA kernel achieves 14.7x over FA2 for small blocks. Open source: github.com/MoonshotAI/MoBA.
- CPU applicability: **medium** (block-sparse structure amenable to CPU, but kernels are CUDA)
- llama.cpp compat: **possible** — standard transformer weights, block selection could be implemented in ggml
- Verdict: **worth_investigating** — Llama-8B-1M-MoBA model could be converted to GGUF for testing

**Differential Transformer V2** — Microsoft, 2026 (HuggingFace blog)
Computes attention as difference of two softmax maps, canceling noise. V2 matches baseline decoding speed, uses standard FlashAttention (no custom kernels). 0.02-0.03 lower loss at 1T tokens. Needs ~65% of baseline params/tokens for equivalent quality.
- CPU applicability: **high** (standard attention ops, just doubled query heads with subtraction)
- llama.cpp compat: **possible** — requires new head-pairing logic in ggml, but ops are standard
- Verdict: **worth_investigating** — FlashAttention compatibility makes ggml port feasible

**Multiscreen** — Apr 2026 (arXiv:2604.01178)
Replaces softmax with absolute query-key screening. 40% param savings, 2.3-3.2x latency reduction at 100K. Very new (2 weeks old); no reproductions, no community benchmarks, no implementations outside the paper. No models available.
- CPU applicability: **unknown** (screening op simplicity suggests potential, but unverified)
- llama.cpp compat: **unlikely** near-term — requires novel ggml op
- Verdict: **monitor_only** — too early, no artifacts to test

### 2. Training-Free / Retrofit Methods (Apply to Existing Models)

**CSAttention (Centroid-Scoring)** — Apr 2026 (arXiv:2604.08584)
Training-free sparse attention for reusable contexts. Pre-computes centroid scores offline, applies sparse selection at decode time. 4.6x speedup at 128K context over best accurate baseline. GPU-optimized score accumulation.
- CPU applicability: **low** (GPU-friendly design, prefill/decode split less relevant for CPU)
- llama.cpp compat: **possible** but niche — most useful for batched GPU serving
- Verdict: **monitor_only**

**HiP Attention** — 2024 (arXiv:2406.09827)
Hierarchical pruning of attention scores, sub-quadratic. Older but more mature. Applicable as drop-in during inference.
- CPU applicability: **medium** (pruning reduces compute, but overhead of hierarchy unclear on CPU)
- llama.cpp compat: **possible**
- Verdict: **monitor_only**

### 3. llama.cpp Attention Support Status (as of Apr 2026)

| Feature | Status |
|---------|--------|
| GQA (Grouped Query Attention) | **Supported** — default for Llama 3, Mistral, Qwen |
| MQA (Multi-Query Attention) | **Supported** |
| Flash Attention (CPU) | **Limited** — no improvement for text gen (memory-bound); helps prefill. Head size 64/128 only |
| Sliding Window Attention | **Partial** — basic SWA works; interleaved SWA (Gemma 2/3) is open issue #12637 |
| MLA (Multi-head Latent Attention) | **Supported** — for DeepSeek V2/V3 models |
| NSA / MoBA / Diff Attention | **Not supported** — no PRs found |
| Multiscreen | **Not supported** — no implementations anywhere |

### 4. KV Cache Compatibility Assessment

| Mechanism | KV quant (q4/q8 + Hadamard) | Speculative decoding | KV eviction |
|-----------|----------------------------|---------------------|-------------|
| NSA | Incompatible (custom KV layout) | Unknown | Built-in (sparse selection) |
| MoBA | Compatible (standard KV, sparse routing) | Likely compatible | Compatible (block-level eviction natural) |
| Diff Attn V2 | Compatible (standard KV) | Compatible (standard decode loop) | Compatible |
| Multiscreen | Unknown (novel KV access pattern) | Unknown | Unknown |
| CSAttention | Compatible (standard KV) | Incompatible (offline prefill assumption) | N/A (own sparsity) |

### 5. Priority Ranking for EPYC CPU Inference

1. **Diff Attn V2** — Highest priority. Standard ops, FlashAttention-compatible, no custom kernels. When pretrained models ship, GGUF conversion should work with minor ggml additions. KV cache and speculation compatible.
2. **MoBA** — Second priority. Llama-8B-1M-MoBA exists now. Block-sparse structure could be implemented in ggml. Standard KV layout preserved. Test GGUF conversion of existing model.
3. **IHA/MEA/KHA** (from existing stub) — Third priority. FlashAttention-compatible variants that preserve standard inference stack.
4. **NSA** — Monitor only for CPU. GPU-aligned design; wait for CPU-friendly derivative.
5. **Multiscreen** — Monitor only. No artifacts, no reproductions, too early.

### Key Finding

No sub-quadratic attention mechanism has a llama.cpp implementation today, but **we have full fork control** (`production-consolidated-v3`) and can implement custom ggml ops.

### Custom ggml Implementation Feasibility

| | Diff Attn V2 | MoBA | Multiscreen |
|---|---|---|---|
| **Spec clarity** | Yes (full pseudocode) | Yes (open-source code) | Partial (no ref impl) |
| **New ggml ops** | 0 (all ops exist) | 2 (top-k, online softmax merge) | 2-3 (TanhNorm, trim-square, cos mask) |
| **Patch size** | ~200-400 LOC | ~500-800 LOC | ~800-1200 LOC |
| **Models available** | No (Microsoft pending) | No (requires cont. training from Llama) | No |
| **Risk** | Low | Medium | High |

**Diff Attn V2 implementation path** (priority #1):
- Q projected to 2h heads (doubled), K/V remain standard
- After standard FlashAttention: split outputs into even/odd pairs per GQA group
- `out = attn1 - sigmoid(lambda) * attn2` where lambda is a small W_lambda projection (d_model → h)
- Changes: GGUF converter (new W_lambda tensor), model loader, attention forward pass
- All ops already exist in ggml (matmul, softmax, sigmoid, subtract, multiply, strided view)
- **Can build now, test when models ship**

**MoBA implementation path** (priority #2):
- Router scores blocks by `dot(q, mean(K_block))`, selects top-k + causal block
- Full attention on selected blocks, results combine via online softmax
- Needs two new primitives: top-k selection, online softmax merge
- Performance gains demonstrated at 1M+ tokens — unclear benefit at our 8K-32K range

**Multiscreen** — monitor only. No reference implementation, partial spec, high risk.

## Research Intake Update — 2026-04-14

### New Related Research
- **[intake-354] "Memory Caching: RNNs with Growing Memory"** (arxiv:2602.24281)
  - Relevance: Bridges fixed-memory RNNs (O(L)) and quadratic Transformers (O(L²)) via cached state checkpoints. Maps the growing-memory RNN design space (O(L) fixed → O(NL) segmented → O(L²) full attention)
  - Key technique: Gated Residual Memory (GRM) — input-dependent gating over cached segment checkpoints. Also: Sparse Selective Caching (MoE-style top-k checkpoint retrieval)
  - Reported results: +12.8pp S-NIAH-2 on Titans at 16K; +20pp SWDE/FDA retrieval; 0.9 ppl improvement at 760M scale
  - Delta from current approach: Training-time modification only. **Deep dive correction**: state copy is ~5% of speculation round-trip cost (50-100ms); the real bottleneck is 220ms/token sequential verification through 30 Delta Net layers. MC's segmented caching would save ~25-50ms against ~1320ms verification for 6 tokens — marginal. Value is architectural context, not a practical optimization path for current models.

- **[intake-356] "Log-Linear Attention"** (arxiv:2506.04761) — **HIGH RELEVANCE**
  - Relevance: **ICLR 2026** paper applying log-linear complexity directly to Gated DeltaNet (75% of our production stack). Authored by Songlin Yang (DeltaNet creator) + Tri Dao (FlashAttention creator) + Yoon Kim
  - Key technique: Replaces fixed-size hidden state with logarithmically growing set of hidden states; O(L log L) complexity; <0.4% parameter overhead
  - Reported results: Log-Linear Gated DeltaNet outperforms standard Gated DeltaNet in perplexity and reasoning benchmarks; outperforms layer-matched Transformer across all metrics
  - EPYC inference impact: (1) State size 4-10x reduction (~2GB → ~200-500MB) enables sequential replay approach for speculation; (2) O(log L) growth makes 1M+ context feasible on same hardware; (3) matmul-rich form maps to existing ggml infrastructure — no GPU-centric sparse kernels needed
  - Reference implementation: github.com/HanGuo97/log-linear-attention (278 stars, Python/Triton, training-only)
  - llama.cpp effort: ~2-3 weeks (new model variant class, new ggml ops, GGUF metadata). Blocked on pretrained model availability.

### Updated Priority Ranking (incorporating deep dive)

1. **Diff Attn V2** — Highest near-term priority. All ops exist in ggml, can build now. Standard attention models.
2. **Log-Linear Gated DeltaNet** — Highest strategic priority for EPYC specifically. Directly upgrades 75% of our production stack's architecture. CPU-friendly (matmul-rich, no sparse kernels). Blocked on pretrained models. Tracked in: [log-linear-gated-deltanet-readiness.md](log-linear-gated-deltanet-readiness.md).
3. **MoBA** — Existing model available for GGUF testing. Benefit unclear at our 8K-32K context range.
4. **IHA/MEA/KHA** — FlashAttention-compatible, standard inference stack preserved.
5. **NSA** — GPU-only. Monitor.
6. **Multiscreen** — Too early. Monitor.
