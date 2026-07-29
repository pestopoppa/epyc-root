# Deep Dive: Memory Caching (2602.24281) + Log-Linear Attention (2506.04761)

**Date**: 2026-04-14
**Intake IDs**: intake-354, intake-356
**Trigger**: Research intake deep dive on growing-memory RNN architectures and their inference implications for Qwen3.5-35B-A3B hybrid Delta Net stack

## Executive Summary

Two papers address the fundamental fixed-memory limitation of linear attention / recurrent models:
- **Memory Caching** proposes segmented state checkpointing with gated retrieval (O(NL) complexity)
- **Log-Linear Attention** proposes logarithmically growing hidden state sets (O(L log L) complexity)

Both require pretraining. Neither can be retrofitted to existing Qwen3.5 models. However, Log-Linear Attention (ICLR 2026, by the DeltaNet and FlashAttention creators) has high strategic relevance: if future models adopt it, our inference stack benefits significantly.

**Critical correction from deep dive**: The initial intake analysis overweighted state checkpoint size (2GB) as the speculation bottleneck. Profiling shows the real killer is sequential verification latency (220ms/token through 30 Delta Net layers), not state copy time.

## The Actual Bottleneck: Verification Latency, Not State Size

### State Management Architecture in llama.cpp

Qwen3.5-35B-A3B recurrent state per layer:
- **R tensor** (convolution state): `(ssm_d_conv - 1) * (ssm_d_inner + 2*ssm_n_group*ssm_d_state)` = 3 * 4352 = **13,056 bytes/layer**
- **S tensor** (recurrent state): `ssm_d_state * ssm_d_inner` = 16 * 4096 = **65,536 bytes/layer**
- Total per layer: ~79 KB
- Total 30 layers: ~2.3 MB per token position

Implementation files:
- `llama.cpp/src/models/qwen35.cpp:198-374` — Delta Net forward pass (`build_layer_attn_linear()`)
- `llama.cpp/src/llama-memory-recurrent.cpp:755-846` — checkpoint/restore with shadow buffer double-buffering
- `llama.cpp/src/models/delta-net-base.cpp` — Three compute modes (chunking, autoregressive, fused)

### Speculation Round-Trip Cost Breakdown

| Component | Time | % of Round |
|-----------|------|------------|
| Checkpoint (tensor copy, 2GB) | 50-100ms | ~5% |
| Draft generation (freeze or recompute) | variable | ~5% |
| **Verification (N tokens x 30 layers)** | **220ms x N** | **~90%** |
| Restore (O(1) pointer swap) | ~0ms | ~0% |

Self-speculation benchmark results (from experiments/self-speculation-benchmark.md):

| Model | Baseline | With Speculation | Delta |
|-------|----------|------------------|-------|
| Qwen3.5-9B | 15.91 t/s | 8.83 t/s (exit=8) | **-44%** |
| Qwen3.5-27B | 4.51 t/s | 2.85 t/s (exit=16) | **-37%** |

**Root cause**: Delta Net recurrence is nonlinear in state:
```
s_new = exp(g) * s_old + k (x) beta * (v - s_old^T k)
```
The `s_old^T k` term prevents tree-masked cumulative sum factorization. Each token must traverse all 30 recurrent layers sequentially. At 220ms/token, verifying 6 draft tokens costs 1320ms — far worse than generating 6 tokens autoregressively (~660ms at baseline).

### What freeze-recurrent buys

The only viable mitigation is `--freeze-recurrent-draft` (implemented in `qwen35.cpp:276-354`): skip all state writes during speculation. Tradeoff:
- Saves: ~100ms/round (no checkpoint, no state update ops)
- Costs: ~13pp acceptance rate drop (draft tokens use stale context)
- Net: +30-42% on lookup speculation only (zero draft cost). Pure speculation stays net-negative.

## Memory Caching (intake-354): Revised Assessment

### What MC Actually Offers

MC proposes four variants for augmenting fixed-memory RNNs with cached state checkpoints:

1. **Residual Memory (RM)**: y_t = M_online(q_t) + SUM(M_cached_i(q_t)) — simple summation
2. **Gated Residual Memory (GRM)**: gamma_t = softmax(<u_t, MeanPool(S_i)>) — input-dependent gating over segments
3. **Memory Soup**: Interpolate cached memory parameters theta = SUM(gamma_i * W_i) — blend model weights
4. **Sparse Selective Caching (SSC)**: MoE-style router selects top-k checkpoints by relevance score

Best results: GRM at 256-token segments. Logarithmic segmentation (O(L log L)) also effective.

### Why MC Doesn't Help Current Inference

1. **Training-time modification**: MC modifies the forward pass to attend over cached checkpoints. Cannot be applied to a pretrained standard Delta Net model.
2. **State copy is marginal**: Even if MC-style partial restore were possible at inference time, saving 50ms against 1320ms verification is noise.
3. **The fundamental bottleneck is sequential computation**: No caching strategy addresses the O(N) per-token verification cost through 30 nonlinear recurrent layers.

### What MC Does Offer

- **Design space mapping**: MC formally characterizes the O(L) → O(NL) → O(L²) continuum of memory capacity. This is useful context for evaluating future architectures.
- **GRM/SSC patterns**: If a future model architecture adopts MC-style explicit state checkpointing, inference engines would need to support segment-aware state retrieval. Understanding GRM/SSC now prepares for that.

## Log-Linear Attention (intake-356): Upgraded Assessment

### Why This Matters More Than Initially Scored

Relevance upgraded medium → **high** because:

1. **75% of production stack is Gated DeltaNet** (Qwen3.5-35B-A3B: 30/40 layers, Qwen3-Next-80B-A3B: 40/80+ layers)
2. **Authored by the architecture creators**: Songlin Yang (Gated DeltaNet, NeurIPS 2024) + Tri Dao (FlashAttention) + Yoon Kim
3. **ICLR 2026**: Top-venue acceptance signals maturity
4. **CPU-friendly**: Matmul-rich parallel form maps to existing ggml infrastructure — unlike NSA/MoBA which require GPU-centric sparse kernels

### Inference Impact Analysis

| Dimension | Standard Gated DeltaNet | Log-Linear Gated DeltaNet | Delta |
|-----------|-------------------------|---------------------------|-------|
| Hidden state size (262K ctx) | ~2 GB | ~200-500 MB | 4-10x smaller |
| Hidden state size (1M ctx) | ~6-8 GB (prohibitive) | ~300-400 MB | 20-25x smaller |
| Verification approach | Sequential O(N), 220ms/tok | Sequential O(N), but smaller state replay | Potentially viable replay |
| Speculation status | **Blocked** | Replay cost drops → potentially **unblocked** | +20-35% throughput if viable |
| Parameter overhead | baseline | +0.4% | negligible |

### llama.cpp Implementation Path

Would require:
1. New model variant: `llm_build_log_linear_delta_net` in `src/models/`
2. New ggml operators: `ggml_log_linear_state_update()`, `ggml_log_linear_attention()`
3. GGUF metadata: `architecture = "log_linear_gated_delta_net"`, state index tensors
4. State management: O(log L) indices per-sequence in `llama-memory-recurrent.cpp`

Estimated effort: 2-3 weeks once reference models and code are available.

### Open Questions

1. **Replay feasibility**: Is O(N x L x log L) sequential replay cost (vs current O(N x L)) low enough to make speculation net-positive on CPU?
2. **Quantization interaction**: Does O(log L) state set work with our q4_K_M weight quantization and q4/q8 KV cache quantization?
3. **Context-folding synergy**: Log-Linear reduces state via O(log L) growth; Context-Folding (intake-154) reduces context via hierarchical summarization. Are these complementary?
4. **Timeline**: When will pretrained log-linear Gated DeltaNet models be available? No public checkpoints yet.

## Monitoring Plan

| Target | Signal | Action |
|--------|--------|--------|
| github.com/HanGuo97/log-linear-attention | New model checkpoints released | Clone repo, convert to GGUF, benchmark |
| github.com/NVlabs/GatedDeltaNet | Log-linear variant merged | Check for pretrained weights |
| arxiv.org | Qwen4 or similar using log-linear GDN | Priority implementation in llama.cpp fork |
| openreview.net | MC paper reviews / ICLR decision | Update credibility score |
| llama.cpp upstream | Log-linear layer support PRs | Evaluate for merge into production-consolidated-v3 |

## Cross-References

- **Chapters**: 10-advanced-speculative-decoding (Section 13: Delta Net speculation blocked)
- **Handoffs**: multiscreen-attention-evaluation (sub-quadratic attention survey), log-linear-gated-deltanet-readiness (readiness tracker), routing-intelligence (Delta Net constraints)
- **Experiments**: self-speculation-benchmark (profiling data), seal-control-vector-results (GDN layer behavior)
- **Intake**: intake-141 (Contextual Memory Virtualisation), intake-333 (IHA), intake-354 (MC), intake-356 (Log-Linear)
