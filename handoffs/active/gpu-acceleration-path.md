# GPU Acceleration Path — CPU+GPU Hybrid Inference

**Status**: stub
**Created**: 2026-04-10 (via research intake deep-dive)
**Categories**: hardware_optimization, inference_serving, moe_optimization
**Priority**: LOW (activates when GPU hardware is acquired)
**Workstream**: Future
**Parent index**: [`inference-acceleration-index.md`](inference-acceleration-index.md)
**Related**: [`llama-cpp-v3-upstream-rebuild.md`](llama-cpp-v3-upstream-rebuild.md) (HIP build path), [`kv-cache-quantization.md`](kv-cache-quantization.md) (GPU KV strategy)

## Objective

Evaluate and implement GPU acceleration for the EPYC inference stack, focusing on CPU+GPU hybrid MoE inference where GPU handles attention + dense FFN while CPU handles routed experts via the existing NUMA 4-way infrastructure.

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-303 | rocWMMA: AMD MMA Library | medium | worth_investigating |
| intake-304 | WMMA on RDNA3 Guide | medium | worth_investigating |
| intake-305 | llama.cpp MI300X Acceleration | medium | worth_investigating |
| intake-306 | RDNA3 rocWMMA Performance Fixes | medium | worth_investigating |
| intake-307 | AITER: AI Tensor Engine for ROCm | medium | worth_investigating |
| intake-308 | hipBLASLt TensileLite GEMM Tuning | medium | worth_investigating |
| intake-309 | Stream-K++ Adaptive GEMM Scheduling | medium | worth_investigating |
| intake-310 | CPU+GPU Hybrid MoE Expert Offloading | high | new_opportunity |
| intake-311 | MI300X Inference Best Practices | medium | worth_investigating |

## Architecture Concept

```
┌─────────────────────────────────────────────────┐
│                  EPYC 9004 Host                  │
│                                                  │
│  ┌──────────┐ ┌──────────┐ ┌────────┐ ┌──────┐  │
│  │ NUMA Q0  │ │ NUMA Q1  │ │ NUMA Q2│ │NUMA Q3│  │
│  │ 48 cores │ │ 48 cores │ │ 48 core│ │48 core│  │
│  │ Expert   │ │ Expert   │ │ Expert │ │Expert │  │
│  │ compute  │ │ compute  │ │ compute│ │compute│  │
│  └────┬─────┘ └────┬─────┘ └───┬────┘ └──┬───┘  │
│       │             │           │          │      │
│       └─────────────┴─────┬─────┴──────────┘      │
│                           │                       │
│                    ┌──────┴──────┐                 │
│                    │  PCIe 5.0   │                 │
│                    └──────┬──────┘                 │
│                           │                       │
│                    ┌──────┴──────┐                 │
│                    │    GPU      │                 │
│                    │ Attention + │                 │
│                    │ Dense FFN + │                 │
│                    │ Shared Exp  │                 │
│                    └─────────────┘                 │
└─────────────────────────────────────────────────┘
```

**Expert offloading**: `-ot "exps=CPU"` keeps attention + dense FFN on GPU, routes MoE experts to NUMA-distributed CPU.

**Why this fits EPYC**: 192 threads + 1.1TB RAM (769GB free) = massive CPU headroom for expert compute. GPU only needs to handle attention + shared expert (small, compute-bound layers). Our MoE models (30B-A3B, 35B-A3B, 122B-A10B, 246B REAP) have small attention layers relative to expert FFNs.

## Build Configuration

```bash
# HIP backend for AMD GPU
cmake -B build \
  -DGGML_HIP=ON \
  -DAMDGPU_TARGETS=gfx942 \        # MI300X (adjust per GPU)
  -DGGML_HIP_ROCWMMA_FATTN=ON \    # Flash attention via rocWMMA (prefill only)
  -DGGML_CPU_ALL_VARIANTS=ON \      # Keep CPU backend for expert compute
  -DGGML_BACKEND_DL=ON \
  -DBUILD_SHARED_LIBS=ON \
  -DLLAMA_CURL=ON

# Runtime environment
export USE_HIPBLASLT_GROUPED_GEMM=1  # Grouped GEMM for MoE
```

## GPU Optimization Stack (priority order)

### Tier 1 — hipBLASLt Grouped GEMM
- Bundles MoE expert matmuls into single kernel launch
- 29% improvement measured, ~10x reduction in API calls
- CDNA3+ only (MI300X/MI325X)
- TensileLite: generate custom GEMM kernels per model shape (1.6-2.6x decode, 3.2x avg large)

### Tier 2 — rocWMMA Flash Attention
- `-DGGML_HIP_ROCWMMA_FATTN=ON`
- ONLY for prefill/prompt processing, NOT decode
- Adaptive KQ stride, `__launch_bounds__` occupancy, intelligent kernel selection
- Known issues: gfx1201+ROCm6.4 (fixed), ROCm 7.2 template conflicts (fixed in llama.cpp)
- If upstream fixes are inadequate, port the 4 community fixes from lhl/llama.cpp:
  1. Adaptive KQ stride (D≤128 → stride 128, reduces LDS footprint)
  2. Block residency enhancement (`__launch_bounds__` min 2 blocks/SM)
  3. Intelligent kernel selection (skip WMMA for decode, use VEC/TILE)
  4. Crash prevention fallback to VEC when TILE splits lack configs

### Tier 3 — Stream-K GEMM Scheduling
- Balances CU utilization for uneven tile counts
- Eliminates per-shape GEMM tuning (valuable for diverse MoE expert dims)
- Built into rocWMMA since ROCm 6.4

## GPU Hardware Decision Matrix

| GPU | VRAM | Memory BW | MoE Expert Offload | Flash Attn | Grouped GEMM | Price Point |
|-----|------|-----------|-------------------|------------|--------------|-------------|
| MI300X | 192GB HBM3 | 5.3 TB/s | All attn+dense fits | MFMA+rocWMMA | hipBLASLt | Datacenter |
| MI325X | 288GB HBM3E | 6.0 TB/s | All attn+dense fits | MFMA+rocWMMA | hipBLASLt | Datacenter |
| RX 7900 XTX | 24GB GDDR6 | 960 GB/s | Small models only | WMMA FP16 | No | Consumer |
| RX 9070 XT | 16GB GDDR6 | 640 GB/s | Very small only | WMMA improved | No | Consumer |

**Recommendation**: For EPYC hybrid, MI300X/MI325X is the only viable option — HBM bandwidth handles attention, VRAM holds all attention layers + KV cache, hipBLASLt grouped GEMM for MoE routing. Consumer GPUs too VRAM-limited for our model sizes.

## Decode Phase Breakdown (informs where GPU helps)

| Component | % of per-token time | Bound by | GPU benefit |
|-----------|-------------------|----------|-------------|
| Weight GEMMs | 85-92% (short ctx) | Memory BW | HIGH — HBM 5.3 TB/s vs DDR5 ~300 GB/s |
| Attention | 7-12% (short ctx) | Memory BW | MODERATE |
| Attention | 25-35% (long ctx) | Compute | HIGH — MFMA/WMMA |
| Attention | >50% (very long) | Compute | CRITICAL |

**Implication**: GPU most beneficial for (1) prefill (always compute-bound), (2) long-context decode (attention becomes compute-bound). For short-context single-token decode, our NUMA 4-way may remain competitive since it's memory-bandwidth-bound anyway.

## Open Questions

- What is the PCIe bandwidth cost of CPU↔GPU expert weight transfer during hybrid inference?
- Does the `-ot "exps=CPU"` path work with AMD HIP, or only CUDA? (Guide only tested CUDA)
- Can NUMA 4-way instances share a single GPU, or does each need dedicated GPU access?
- What's the minimum GPU VRAM to hold attention + shared expert for our largest model (246B REAP)?
- Does hipBLASLt grouped GEMM compose with expert offloading, or are they mutually exclusive paths?
- Can we implement our own WMMA flash attention fixes if upstream doesn't merge the community patches?

## Prerequisite: v3 Rebuild HIP Support

The llama-cpp-v3-upstream-rebuild currently builds CPU-only. Adding GPU support requires:
1. Add `-DGGML_HIP=ON` to build flags
2. Verify all 24 custom patches compile against HIP backend
3. Test paged attention patches (Tier 1 patches 7-13) with GPU memory management
4. Benchmark: CPU-only vs hybrid on same model/prompt to quantify actual gain

## Notes

This handoff activates when GPU hardware is acquired. Until then, all findings are preserved here for reference. The CPU+GPU hybrid MoE pattern (intake-310) is the most promising avenue — it leverages our existing NUMA infrastructure rather than replacing it.

AITER kernel performance numbers (17x MLA decode, 14x MHA prefill, 3x fused MoE) represent achievable ceiling but require vLLM/SGLang, not llama.cpp. The llama.cpp path through rocWMMA + hipBLASLt is more modest but integrates with our existing stack.
