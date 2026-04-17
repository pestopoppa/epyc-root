# TQ3 / TurboQuant Quantization — Monitor List

**Status**: monitoring (do NOT merge TQ3_1S — see rationale below)
**Created**: 2026-04-01 (via research intake)
**Updated**: 2026-04-17 (PR #21038 confirmed landed upstream as commit `744c0c731` 2026-04-01; auto-enabled in v3. PR #21089 and ChunkKV remain open.)
**Categories**: quantization, hardware_optimization

## Why NOT to Merge TQ3_1S

1. **Immature**: 3 commits, 1 contributor, no peer review, no CPU kernels, undocumented conversion tool
2. **Wrong target**: Only benchmarked on Qwen3.5-27B vs Q4_0. No Q4_K_M comparison. No Qwen2.5 tests. Author warns smaller models are "much less forgiving"
3. **We don't need VRAM savings**: Our EPYC 9655 setup has ample RAM/VRAM. Q4_K_M fits comfortably. Bottleneck is throughput, not capacity
4. **Upstream going different direction**: ggerganov himself is working on Hadamard rotation for existing quant types (PR #21038) — no new types needed
5. **MoE risk**: WHT rotation creates ~367K ghost activations per forward pass, shattering sparse routing. Not applicable to dense Qwen2.5-Coder-32B but relevant for Qwen3.5 hybrid

## What to Monitor Instead (High Priority)

### PR #21038 — ggerganov's Hadamard Rotation ✅ LANDED
- **What**: Applies WHT rotation to ALL existing KV cache quant types (Q4_0, Q5_0, Q8_0 etc.)
- **Impact**: Q4_0 KV cache PPL improves 25-77% on small models. Q8_0 with rotation matches FP16 on reasoning benchmarks
- **Why it matters**: Free quality improvement — no model re-quantization needed, just rebuild llama.cpp
- **Status**: ✅ MERGED upstream as commit `744c0c731` (2026-04-01). Auto-enables in `production-consolidated-v3` when KV types are quantized. `--kv-hadamard` flag removed from orchestrator config (was our prior custom WHT impl, now redundant).
- **URL**: https://github.com/ggml-org/llama.cpp/pull/21038

### PR #21089 — CPU TurboQuant KV Cache (TBQ3_0/TBQ4_0)
- **What**: 3-bit and 4-bit KV cache quantization with CPU kernels
- **Impact**: 5.2x KV cache compression with minimal PPL loss. Extends effective context length
- **Status**: Open PR, under review
- **URL**: https://github.com/ggml-org/llama.cpp/pull/21089

### ChunkKV (arXiv:2502.00299) — Training-Free KV Compression
- **What**: Chunk-level KV cache compression preserving semantic structure. No retraining required
- **Impact**: Retains 12% of KV cache matching full cache quality. 26.5% throughput improvement via layer-wise index reuse
- **Why it matters**: Works on existing pretrained models — directly applicable to our stack
- **URL**: https://arxiv.org/abs/2502.00299

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-246 | llama.cpp-tq3 — TQ3_1S Weight Quantization | medium | worth_investigating (monitor) |
| intake-245 | MSA: Memory Sparse Attention | low | not_applicable (training-only) |
| intake-186 | bitnet.cpp — Ternary Quantization (TQ1_0/TQ2_0) | medium | already_integrated |

## Action Items

- [x] Watch PR #21038 for merge — ✅ LANDED 2026-04-01 as commit `744c0c731`, auto-enables in v3
- [ ] Evaluate PR #21089 when merged — test TBQ3_0 KV cache on Qwen2.5-Coder-32B context extension
- [ ] Read ChunkKV paper — assess if implementable in llama.cpp
- [ ] Revisit TQ3_1S weight quant only if: upstream adopts + multi-model benchmarks + Q4_K_M comparison + CPU kernels
