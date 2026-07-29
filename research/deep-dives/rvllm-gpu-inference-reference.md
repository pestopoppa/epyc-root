# rvllm GPU Inference Reference — Deep Dive

- **Source**: https://github.com/m0at/rvllm
- **Date**: 2026-04-20
- **Intake ID**: intake-424
- **Author**: m0at
- **Verdict (initial)**: worth_investigating

---

## 1. What rvllm Is

A high-performance LLM inference engine with two paths:
- **GPU path**: Pure Rust + CUDA (no Python) targeting H100, using FP8 quantization, CUDA graph capture, Flash Attention 3
- **TPU path**: Pure JAX + XLA (~500 lines) targeting TPU v6e

Primary target: Gemma 4 models (E4B MoE, 31B dense). Explicitly NOT a general-purpose serving framework — it's a model-specific speed demon.

## 2. Architecture Decisions Worth Noting

### 2a. Zero-Python GPU Serving

The entire GPU serving path is Rust. No Python GIL, no PyTorch overhead, no framework tax. This is the same philosophy behind llama.cpp (C++) — eliminate runtime overhead via systems-level implementation.

**Relevance**: Validates the "no framework" approach. rvllm benchmarks show +24% over vLLM at B=128, which is entirely attributable to eliminating Python/PyTorch overhead. Our llama.cpp approach gets this for free.

### 2b. Single CUDA Graph for Entire Model

Instead of per-layer or per-block graph capture, rvllm captures a **single graph spanning all 60 layers** (~935 nodes, 14 kernel launches per transformer layer). This eliminates all CPU-side dispatch overhead.

**Relevance to CPU**: We don't have GPUs, but the principle is the same — minimize dispatch overhead. On CPU, this maps to: avoid unnecessary function call overhead in the hot loop, keep the forward pass as a tight inner loop. Our fork's model-specific `build_graph()` implementations already do this.

### 2c. EAGLE-3 Implementation Details

- **Draft head**: 450M parameters (separate model)
- **K=5 token proposals** per step
- **Projected 1.8x speedup** (experimental, not fully benchmarked)
- Tree-based verification: draft model proposes a tree of candidates, target model verifies in one forward pass

**Relevance**: EAGLE-3 is already documented in chapter 10 (intake via arXiv:2503.01840). The rvllm implementation confirms that K=5 with a 450M draft head is the practical sweet spot for Gemma 4 31B. For our models (Qwen3.6-35B-A3B), similar ratios would suggest a ~500M draft head proposing K=4-6 tokens.

### 2d. Dual-Path Attention for Long Context

- **Short context (≤32K)**: Single contiguous attention scan
- **Long context (>32K)**: Split KV cache into blocks + blockwise global attention

This automatic switching avoids the overhead of paged attention for short sequences while supporting 128K inference.

**Relevance**: Our models rarely exceed 32K context in production (orchestrator conversations are compacted). But if we ever need long-context inference, the "short path / long path" split is a clean pattern. Currently our llama.cpp fork uses flat KV cache (no paging needed at batch_size=1).

## 3. Benchmark Data — Reference Points

| Model | Hardware | Metric | Value |
|-------|----------|--------|-------|
| Gemma 4 E4B | TPU v6e-4 | B=1 tok/s | 78.3 |
| Gemma 4 E4B | TPU v6e-4 | Peak tok/s | 16,794 |
| Gemma 4 31B | TPU v6e-4 | Peak tok/s | 9,600 |
| Gemma 4 31B | TPU v6e-4 | 128K ctx latency | 40.56 ms/step |
| Gemma 4 31B | H100 FP8 | Peak tok/s | 8,786 |
| Gemma 4 31B | H100 FP8 | vs vLLM | +24% at B=128 |
| Cost efficiency | TPU v6e-4 | tok/s/$ | 3,230 |

**Context for our stack**: Qwen3.6-35B-A3B on our EPYC CPU does ~15-25 tok/s at B=1 (varies by params). The H100 does 78 tok/s on a similar-size model. That's ~4x faster per-token, but we don't pay $2/hr for the hardware — our amortized cost is effectively $0/hr after the server purchase.

## 4. What We Can't Use

| Feature | Why not |
|---------|---------|
| FP8 quantization | Requires H100 FP8 tensor cores |
| Flash Attention 3 | SM90 (H100/H200) only |
| CUDA graph capture | No GPU |
| JAX/XLA TPU path | No TPU |
| Gemma 4 model support | Gemma 4 dropped from our stack ("no value") |

## 5. What We Can Learn From

| Pattern | Our equivalent | Delta |
|---------|---------------|-------|
| Zero-runtime-overhead serving | llama.cpp (C++) | Already have this |
| Model-specific optimizations | Fork's per-model `build_graph()` | Already have this |
| EAGLE-3 K=5 with 450M draft | Tree speculation with small draft model | **Config reference**: 450M/31B = ~1.5% draft/target ratio |
| Aggressive graph fusion | Our forward pass is sequential layers | Could explore batch-of-layers fusion on CPU (unlikely to help) |
| Dual-path attention | Flat KV (no paging needed at B=1) | Not needed — our contexts are compacted below 32K |

## 6. The gpu-acceleration-path.md Connection

If we ever acquire GPU hardware (H100/H200 or DGX Spark — see project_dgx_spark_target.md), rvllm provides:
- Concrete H100 throughput targets to calibrate expectations
- Validation that Rust-native serving beats vLLM by 24%
- EAGLE-3 implementation reference for GPU speculation
- FP8 quantization workflow reference

This is LOW priority per existing handoff assessment, contingent on hardware acquisition that hasn't happened.

## 7. Verdict Delta

| Aspect | Initial Assessment | Post Deep-Dive |
|--------|-------------------|----------------|
| Relevance | low (GPU/TPU only) | **low** — confirmed, nothing directly usable |
| Novelty | medium (Rust serving, benchmark data) | **low** — validates known patterns, no new concepts |
| Verdict | worth_investigating | **not_applicable** for current stack; **reference_bookmark** for GPU acquisition roadmap |
| Actionable now | No | **No** — but EAGLE-3 draft/target ratio (1.5%) is a useful reference for our tree speculation work |
| Future trigger | GPU hardware acquisition | Same — activate when H100/DGX arrives |

**Updated verdict: `not_applicable`** — File as reference data for gpu-acceleration-path.md. No current action items. The +24% over vLLM data point validates the "no-framework" philosophy we already follow with llama.cpp.
