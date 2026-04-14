# Log-Linear Gated DeltaNet — Readiness Tracker

**Status**: stub (MONITORING) — blocked on pretrained model availability
**Created**: 2026-04-14 (via research intake deep dive)
**Categories**: ssm_hybrid, context_extension, inference_serving
**Priority**: HIGH (strategic) — activates when gate criteria met

## Objective

Track readiness of Log-Linear Gated DeltaNet for deployment on EPYC. 75% of the production stack (Qwen3.5-35B-A3B: 30/40 layers) uses standard Gated DeltaNet. The Log-Linear variant (ICLR 2026, by Songlin Yang + Tri Dao + Yoon Kim) replaces the fixed-size hidden state with a logarithmically growing set of hidden states — O(L log L) complexity with <0.4% parameter overhead. When pretrained models emerge, implement in our llama.cpp fork and benchmark.

## Why This Matters

- **State size 4-10x reduction** (~2GB → ~200-500MB at 262K context) — enables sequential replay for speculation
- **O(log L) growth** makes 1M+ context feasible on same hardware (vs prohibitive ~6-8GB at 1M with standard GDN)
- **CPU-friendly**: matmul-rich parallel form maps to existing ggml infrastructure — no GPU-centric sparse kernels (unlike NSA/MoBA)
- **Highest strategic priority** in the sub-quadratic attention survey (see multiscreen-attention-evaluation.md)

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-356 | Log-Linear Attention (arxiv:2506.04761) | high | worth_investigating |
| intake-354 | Memory Caching: RNNs with Growing Memory (arxiv:2602.24281) | medium | worth_investigating |

## Gate Criteria

All must be true to activate implementation:

- [ ] Pretrained Log-Linear Gated DeltaNet model checkpoint publicly available (any size)
- [ ] Reference implementation (github.com/HanGuo97/log-linear-attention) includes inference code, not just training
- [ ] Model architecture documented sufficiently for GGUF converter implementation

## Implementation Plan (triggered when gate criteria met)

1. Clone reference impl, verify architecture matches paper description
2. Implement GGUF converter for log-linear variant tensors
3. New model variant `llm_build_log_linear_delta_net` in `src/models/`
4. New ggml operators: `ggml_log_linear_state_update()`, `ggml_log_linear_attention()`
5. GGUF metadata extensions: `architecture = "log_linear_gated_delta_net"`, state index tensors
6. State management: O(log L) indices per-sequence in `llama-memory-recurrent.cpp`
7. Benchmark: perplexity, throughput, memory at 8K / 32K / 262K / 1M context lengths
8. If speculation replay viable: prototype sequential replay on O(log L) state

Estimated effort: 2-3 weeks from gate activation.

## Monitoring Targets

| Target | Signal | Cadence |
|--------|--------|---------|
| github.com/HanGuo97/log-linear-attention | New releases, model checkpoints | Weekly |
| github.com/NVlabs/GatedDeltaNet | Log-linear variant merge | Weekly |
| HuggingFace | Models tagged log-linear or using log-linear GDN | Monthly |
| llama.cpp upstream (ggml-org) | PRs for log-linear layer support | Monthly |
| arxiv.org | Qwen4 or next-gen models adopting log-linear GDN | Monthly |

## Open Questions

1. Is O(N x L x log L) sequential replay cost low enough for net-positive speculation on CPU?
2. Does O(log L) state set work with q4_K_M weight quantization and q4/q8 KV cache quantization?
3. Context-folding synergy: Log-Linear reduces state via O(log L) growth, Context-Folding reduces context via hierarchical summarization. Complementary?
4. Timeline for pretrained models — no public checkpoints as of 2026-04-14.

## Cross-References

- **Deep dive**: `research/deep-dives/memory-caching-log-linear-attention.md`
- **Survey**: `handoffs/active/multiscreen-attention-evaluation.md` (priority ranking, literature survey)
- **Intake**: intake-356 (primary), intake-354 (related MC analysis)
- **Chapters**: 10-advanced-speculative-decoding (Section 13: Delta Net speculation blocked)
- **Handoffs**: routing-intelligence.md (Delta Net constraints, line 384)
- **Completed**: mtp-speculative-decoding.md, ssm-hybrid-acceleration.md (speculation exhausted on standard GDN)
- **Ref impl**: github.com/HanGuo97/log-linear-attention (278 stars, Python/Triton, training-only)
