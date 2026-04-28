# Log-Linear Gated DeltaNet — Readiness Tracker

**Status**: stub (MONITORING) — blocked on pretrained model availability
**Created**: 2026-04-14 (via research intake deep dive)
**Updated**: 2026-04-21 (monitoring confirmed — no pretrained release yet)
**Categories**: ssm_hybrid, context_extension, inference_serving
**Priority**: HIGH (strategic) — activates when gate criteria met

## Status as of 2026-04-21

Backburner monitoring — no pretrained Log-Linear Gated DeltaNet checkpoint released yet (per HF/arxiv checks). Gate criteria unchanged. Stub retained as reference for rapid activation when upstream ships weights. Cross-ref intake-356 remains authoritative research context.

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

## Research Intake Update — 2026-04-28

### New Related Research

- **[intake-488] "Speculative Decoding with Mamba"** (github.com/itsdaniele/speculative_mamba; arxiv:2408.15237) — Pure-Mamba target+draft spec-dec; CUDA-only; no Delta-Net coverage. Verdict: not_applicable.

- **[intake-489] "SpecMamba: Accelerating Mamba Inference on FPGA with Speculative Decoding"** (arxiv:2509.19873)
  - Relevance: Memory-aware hybrid backtracking strategy directly addresses the SSM hidden-state rollback problem that has blocked spec-dec on hybrid SSMs (chapter 10 §13). FPGA hardware-bound but algorithmic frame is reusable.
  - Reported results: 2.27× over GPU, 2.85× over prior FPGA Mamba.
  - Delta: FPGA-only — no CPU port path. Catalog as algorithmic reference for if/when Delta-Net spec-dec is reopened with proper rollback semantics.

- **[intake-490] "Hybrid Models Meet SGLang: More than Full Attention"** (pytorch.org blog, Dec 2025) — verdict: **adopt_patterns**
  - Relevance: SGLang's resolution of in-place SSM state updates (MambaRadixCache + HybridReqToTokenPool + EAGLE/MTP rollback over SSM state) demonstrates that "spec-dec dead on hybrid SSM" is solvable in principle on the architecture side. Direct counter-evidence for the chapter-10 §13 blocker if/when CPU-side rollback semantics are implemented in llama.cpp.
  - Reported results: 324.57 tok/s, accept length 4.231 on Qwen3-Next-80B-A3B-FP8 (H200) with EAGLE/MTP.
  - Delta: CUDA/H200/FP8 only — does not run on EPYC, but four named primitives (HybridReqToTokenPool, HybridLinearKVPool, MambaRadixCache, Elastic Memory Pool) form the reference design that GDN serving on llama.cpp would need to mirror.

- **[intake-491] "Mamba Drafters for Speculative Decoding"** (arxiv:2506.01206; Findings of EMNLP 2025)
  - Relevance: External SSM drafter is the inverse direction of GDN serving — uses an SSM as the cheap drafter rather than the expensive target. MAB-optimized tree-shape selector applies orthogonally.
  - Reported results: At 8k context, Mamba 52GB total memory vs EAGLE 72GB; throughput preserved while Transformer drafters degrade.
  - Delta: principle generalizes to GDN drafters once a small Delta-Net or hybrid is available. Track alongside readiness for log-linear GDN target inference.
