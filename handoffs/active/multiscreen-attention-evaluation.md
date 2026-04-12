# Multiscreen Attention — Evaluation for EPYC Inference

**Status**: stub
**Created**: 2026-04-04 (via research intake)
**Categories**: kv_cache, inference_serving, ssm_hybrid

## Objective

Evaluate the Multiscreen architecture (arXiv:2604.01178) as a potential next-generation attention mechanism for EPYC inference. Multiscreen replaces softmax attention with absolute query-key screening, achieving 40% parameter savings and 2.3-3.2x latency reduction at 100K contexts.

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-256 | Screening Is Enough — Multiscreen Architecture | high | new_opportunity |

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
