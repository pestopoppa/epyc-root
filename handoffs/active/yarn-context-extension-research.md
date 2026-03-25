# YaRN Context Extension Research

**Status**: STUB — for future research
**Created**: 2026-03-09
**Priority**: LOW
**Workstream**: Research

## What is YaRN?

YaRN (Yet another RoPE extensioN) is a compute-efficient method to extend LLM context windows beyond their training length by modifying Rotary Position Embeddings (RoPE). It divides RoPE dimensions into groups and applies different linear scaling factors to each.

Two modes:
- **Fine-tuned**: Extends context ~2x with minimal training (0.1% of pre-training data)
- **Dynamic**: Extends >2x at inference time with zero fine-tuning

Zero overhead during inference — RoPE embeddings are pre-computed.

## Relevance to Our Stack

Qwen3.5 models have 256K native context, extensible to 1M with YaRN. Qwen3-Next-80B also supports 256K native + YaRN to 1M. Our ingest role (Qwen3-Next-80B) currently runs at default context. If we need >256K context for long document processing, YaRN is the path.

## llama.cpp Support

Fully supported with dedicated CLI flags:

```bash
# Extend a 256K model to 1M context
llama-server -m model.gguf -c 1048576 \
  --rope-scaling yarn \
  --rope-scale 4 \
  --yarn-orig-ctx 262144
```

| Flag | Purpose |
|------|---------|
| `--rope-scaling yarn` | Enable YaRN scaling |
| `--rope-scale N` | Context scaling factor (e.g., 4 for 4x extension) |
| `--yarn-orig-ctx N` | Original model context size |
| `--yarn-ext-factor N` | Extrapolation mix factor (0.0 = full interpolation) |
| `--yarn-attn-factor N` | Attention magnitude scaling |
| `--yarn-beta-slow N` | High correction dimension parameter |
| `--yarn-beta-fast N` | Low correction dimension parameter |

## Key Questions to Research

1. **Quality degradation curve**: How does RULER accuracy degrade from 256K → 512K → 1M with YaRN on our hardware?
2. **Memory impact**: KV cache for 1M context at Q4 — how much RAM does this consume?
3. **Speed impact**: Does YaRN affect generation speed or just prompt processing?
4. **Qwen3.5 vs Qwen3-Next**: Which model retains quality better under YaRN extension?
5. **GGUF metadata**: Do Unsloth GGUFs include YaRN parameters in metadata, or must we specify manually?

## References

- **Original Paper**: [YaRN: Efficient Context Window Extension of Large Language Models](https://arxiv.org/abs/2309.00071) (ICLR 2024)
- **GitHub**: [jquesnelle/yarn](https://github.com/jquesnelle/yarn)
- **llama.cpp PR**: [#2268 — YaRN RoPE scaling implementation](https://github.com/ggerganov/llama.cpp/pull/2268)
- **EleutherAI Analysis**: [YaRN paper summary](https://www.eleuther.ai/papers-blog/yarn-efficient-context-window-extension-of-large-language-models)
- **Tutorial**: [Understanding YaRN (Medium)](https://medium.com/@rcrajatchawla/understanding-yarn-extending-context-window-of-llms-3f21e3522465)
- **Qwen3-Next-80B**: [HuggingFace model card](https://huggingface.co/Qwen/Qwen3-Next-80B-A3B-Instruct) — RULER 91.8% avg across 4K-1M
- **Qwen3.5-27B**: [HuggingFace model card](https://huggingface.co/Qwen/Qwen3.5-27B) — 256K native, 1M with YaRN

## Research Intake Update — 2026-03-24

### New Related Research
- **[intake-191] "TurboQuant: Redefining AI efficiency with extreme compression"** (arxiv:2504.19874)
  - Relevance: Directly addresses question 2 (KV cache memory at 1M context). 6x+ KV cache memory reduction via 3-4 bit quantization without training.
  - Key technique: TurboQuant combines PolarQuant (polar coordinate compression) and QJL (1-bit Johnson-Lindenstrauss transform) for data-oblivious KV cache quantization.
  - Reported results: 6x+ memory reduction, 8x attention speedup on H100, perfect accuracy on needle-in-haystack.
  - Delta from current approach: We have no KV cache quantization. At 1M context, KV cache dominates RAM — 6x reduction would make extended context practical on our EPYC stack.
- **[intake-192] "PolarQuant: Quantizing KV Caches with Polar Transformation"** (arxiv:2502.02617)
  - Relevance: Component technique of TurboQuant. 4.2x KV cache compression via polar coordinate transformation. Eliminates normalization overhead.
- **[intake-193] "QJL: 1-Bit Quantized JL Transform for KV Cache Quantization with Zero Overhead"** (arxiv:2406.03482)
  - Relevance: Component technique of TurboQuant. 5x KV cache reduction to 3 bits. Has GitHub implementation (github.com/amirzandieh/QJL). Published at AAAI 2025.
