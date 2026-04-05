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
