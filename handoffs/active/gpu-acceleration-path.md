# GPU Acceleration Path — CPU+GPU Hybrid Inference

**Status**: researched (literature survey complete 2026-04-14, RX 7900 XTX + hybrid MoE path prioritized)
**Created**: 2026-04-10 (via research intake deep-dive)
**Updated**: 2026-04-21 (no GPU acquired; vLLM DDTree+Dflash plan still current)
**Categories**: hardware_optimization, inference_serving, moe_optimization, speculative_decoding
**Priority**: LOW (activates when GPU hardware is acquired)
**Workstream**: Future
**Parent index**: [`inference-acceleration-index.md`](inference-acceleration-index.md)
**Related**: [`llama-cpp-v3-upstream-rebuild.md`](../completed/llama-cpp-v3-upstream-rebuild.md) (HIP build path), [`kv-cache-quantization.md`](kv-cache-quantization.md) (GPU KV strategy)

## Status as of 2026-04-21

Backburner — no GPU hardware acquired (DGX Spark / RX 7900 XTX / alternate path). Plan of record is vLLM DDTree+Dflash spec-dec on CPU+GPU hybrid MoE when hardware lands (community benchmark 91 tok/s on GB10, added 2026-04-15). Activation trigger unchanged: acquisition of training-capable GPU. Per `project_dgx_spark_target` memory: DGX Spark external benchmark files are compiled reference data, not local measurements.

## Objective

Evaluate and implement GPU acceleration for the EPYC inference stack, focusing on CPU+GPU hybrid MoE inference where GPU handles attention + dense FFN while CPU handles routed experts via the existing NUMA 4-way infrastructure.

## DGX Spark Target (2026)

### Hardware: NVIDIA GB10 Grace Blackwell Superchip

| Spec | Value |
|------|-------|
| Architecture | Grace (ARM) + Blackwell GPU on single SoC, 3nm |
| Unified Memory | 128GB LPDDR5X (CPU+GPU coherent, single pool) |
| Memory Bandwidth | 273 GB/s (LPDDR5X 8533, 16-channel) |
| NVLink-C2C | 600 GB/s bidirectional (CPU-GPU interconnect) |
| Tensor Cores | 5th-gen (FP4/FP8/FP16 native) |
| AI Performance | 1 PFLOP FP4 (w/ sparsity), ~31 TFLOPS FP32 |
| CPU | 20 ARM cores (10x Cortex-X925 + 10x Cortex-A725) |
| TDP | 140W (desktop form factor) |
| Price | $4,699 (Founders Edition, available now) |
| Models supported | Up to 200B parameters |

### Why This Changes Everything for MoE Inference

The unified memory architecture eliminates the CPU-to-GPU PCIe bottleneck that dominates the entire existing survey below. On discrete GPU systems, expert weights must transfer across PCIe (~64 GB/s) during hybrid MoE inference. On DGX Spark, all 128GB is a single coherent pool accessible by both CPU and GPU at full bandwidth -- expert weights are simply *there*, no transfer needed.

**Benchmark results (llama.cpp / vLLM on DGX Spark):**
- MoE models: ~70 t/s decode from a single chip (Gemma 26B MoE: 69.9 t/s)
- llama.cpp MoE optimizations: 35% uplift on DGX Spark (CES 2026 software update)
- vLLM: GPT-OSS-120B at 58.8 t/s (MXFP4, single node); Llama 3.1 8B FP4 at 924 t/s prefill
- Qwen3-Coder-30B Q4: 20-25 t/s at 16k context, 15-17 t/s at 32k context
- Two DGX Sparks linkable via NVLink for 256GB unified pool (Qwen3 235B: 23.4k t/s prefill)

**Comparison with EPYC 9655 CPU-only:** DGX Spark memory bandwidth (273 GB/s) is comparable to our DDR5 (~300 GB/s), but the Blackwell GPU adds massive compute throughput for attention and prefill that CPU lacks. On GPT-OSS-120B, an EPYC 7702 scored ~15.7 t/s vs Spark's ~11.7 t/s at launch, but post-CES 2026 software updates delivered up to 2.5x improvement. The real advantage is architectural: no PCIe bottleneck means MoE expert routing is a memory access, not a data transfer.

**Caveats:** ARM CPU (20 cores) is far weaker than EPYC 9655 (192 threads) for expert compute. Memory bandwidth is slightly lower than our EPYC DDR5 setup. FP4 scaling underperforms theoretical expectations (FP8-to-FP4 yields ~1.3-1.5x, not 2x). Not a drop-in replacement for the NUMA 4-way architecture -- it's a fundamentally different inference paradigm.

**Verdict:** At $4,699, DGX Spark is the most cost-effective path to GPU-accelerated MoE inference. It obsoletes the hybrid CPU+GPU offloading architecture (the entire `-ot "exps=CPU"` paradigm) by making expert offloading unnecessary. Primary path for models up to ~70B; pair two units for 200B+.

### vLLM + Speculative Decoding on DGX Spark (Future Work)

Speculative decoding on Qwen3.5 hybrids is **dead on CPU** (exhaustively tested — see [DFlash handoff](../completed/dflash-block-diffusion-speculation.md), [tree speculation handoff](../completed/tree-speculation-numa-drafting.md), [MTP-1 handoff](../completed/mtp-speculative-decoding.md)). The root cause is Delta Net's sequential recurrence: verifying N draft tokens costs N× single-decode, not ~1× like on pure attention models. But on **GPU, the recurrent state uses parallel scan** — the verification bottleneck disappears, and speculation becomes viable again.

**Community benchmark to reproduce** (2026-04-15):
- Setup: DDTree + Dflash, vLLM, Qwen3.5-27B AWQ, GB10
- Result: **91.08 tok/s accepted**, 94.48 tok/s drafted, 96.4% acceptance rate
- DDTree = tree-based multi-candidate verification strategy
- Dflash = block diffusion drafting (no separate draft model — generates candidate token blocks via iterative denoising, conditioned on target model hidden states)

**Our research validates this direction:**
- DFlash paper reports τ=6.49 accepted tokens per round on Qwen3.5-35B-A3B (GPU) — [intake-158](https://arxiv.org/abs/2602.06036)
- GPU works because parallel scan handles recurrent state, unlike CPU where each token traverses 30+ Delta Net layers sequentially — [DFlash deep-dive](../research/deep-dives/dflash-dart-diffusion-speculation.md)
- Our C++ DFlash implementation verified forward pass correctness (hidden states match HF to <0.01) — the problem was never the algorithm, it was CPU sequential verification cost

**Reproduction plan (activates when Spark is acquired):**
1. Install vLLM on DGX Spark (requires CUDA 13.0+ / Blackwell support)
2. Obtain Qwen3.5-27B AWQ (check HF for AWQ quant availability)
3. Configure DDTree + Dflash speculation in vLLM (check vLLM version requirements — may need nightly for Blackwell + Dflash support)
4. Benchmark: match/exceed 91 tok/s accepted throughput
5. Compare against llama.cpp baseline on same hardware (no speculation) to measure actual speedup
6. If viable, evaluate for Qwen3.5-35B-A3B and larger models

**Key difference from our CPU experiments:** This is vLLM-native, not llama.cpp. The entire speculation pipeline (diffusion drafting, tree verification, KV cache management) is GPU-optimized. Our llama.cpp DFlash port was fighting the wrong battle — GPU is the natural habitat for block diffusion speculation.

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
- Which vLLM version first supports DDTree + Dflash speculation on Blackwell? Is it mainline or nightly-only?
- Does the 91 tok/s community benchmark hold under real workloads (multi-turn, long context), or only synthetic single-prompt?
- Can Dflash block diffusion compose with AWQ quantization without acceptance rate degradation? (Our CPU experiments showed Q4_K_M killed DFlash acceptance — 27% per-token — but AWQ is a different quantization method and runs on GPU)
- Is there a published Dflash drafter for Qwen3.5-27B specifically, or does the Qwen3.5-35B-A3B drafter transfer? (Our DFlash inventory only has Qwen3-Coder-30B-A3B drafter)

## Prerequisite: v3 Rebuild HIP Support

The llama-cpp-v3-upstream-rebuild currently builds CPU-only. Adding GPU support requires:
1. Add `-DGGML_HIP=ON` to build flags
2. Verify all 24 custom patches compile against HIP backend
3. Test paged attention patches (Tier 1 patches 7-13) with GPU memory management
4. Benchmark: CPU-only vs hybrid on same model/prompt to quantify actual gain

## Notes

This handoff activates when GPU hardware is acquired. Until then, all findings are preserved here for reference. The CPU+GPU hybrid MoE pattern (intake-310) is the most promising avenue — it leverages our existing NUMA infrastructure rather than replacing it.

AITER kernel performance numbers (17x MLA decode, 14x MHA prefill, 3x fused MoE) represent achievable ceiling but require vLLM/SGLang, not llama.cpp. The llama.cpp path through rocWMMA + hipBLASLt is more modest but integrates with our existing stack.

**vLLM speculation is the highest-priority experiment when Spark arrives.** The community DDTree+Dflash benchmark (91 tok/s on Qwen3.5-27B AWQ) reopens the speculation story that is conclusively dead on CPU. This should be the first thing tested after basic llama.cpp inference is verified on the hardware. Cross-reference: [speculative-decoding wiki](../../wiki/speculative-decoding.md), [DFlash deep-dive](../../research/deep-dives/dflash-dart-diffusion-speculation.md).

## Research Intake Update — 2026-04-12

### New Related Research
- **[intake-334] "MegaTrain: 100B+ Training on Single GPU"** (arxiv:2604.05091)
  - CRITICAL: Works on consumer GPUs — RTX 3090 ($300-400 used): 35 TFLOPS at 7B, 30 at 14B (DeepSpeed OOMs).
  - CPU-centric param storage + GPU transient compute. 1.84x over DeepSpeed ZeRO-3.
  - EPYC path: With RTX 3090 + our 256GB+ RAM → local 14B model training. Most practical route to Doc-to-LoRA.
  - Code: github.com/DLYuanGod/MegaTrain
- **[intake-339] "Gemma 4 31B NVFP4 Turbo"** — Blackwell FP4, 68% memory reduction, +142% prefill. Requires RTX 5090+.
- **[intake-332] "Ouro LoopLM"** — 2.6B matches 12B. Not llama.cpp compatible but could run via transformers on CPU.

## Literature Survey — 2026-04-14

### 1. CPU+GPU Hybrid MoE Expert Offloading

| Resource | Date | Verdict |
|----------|------|---------|
| [Doctor-Shotgun MoE Offload Guide](https://huggingface.co/blog/Doctor-Shotgun/llamacpp-moe-offload-guide) (intake-310) | 2025 | **directly_applicable** |
| [Doctor-Shotgun extended gist](https://gist.github.com/DocShotgun/a02a4c0c0a57e43ff4f038b46ca66ae0) | 2025 | **directly_applicable** |
| [Understanding MoE Offloading (DEV Community)](https://dev.to/someoddcodeguy/understanding-moe-offloading-5co6) | 2026 | **directly_applicable** |
| [Two-tier GPU+RAM expert cache proposal (llama.cpp #20757)](https://github.com/ggml-org/llama.cpp/issues/20757) | 2026 | **worth_investigating** |
| [David Sanftenberg: Qwen-235B partial offload guide](https://medium.com/@david.sanftenberg/gpu-poor-how-to-configure-offloading-for-the-qwen-3-235b-a22b-moe-model-using-llama-cpp-13dc15287bed) | 2025 | **directly_applicable** |

**Key findings**: The `-ot "exps=CPU"` syntax and `--n-cpu-moe N` flag are production-ready in llama.cpp. The guide uses CUDA syntax (`CUDA0`) exclusively -- AMD/ROCm compatibility is **unconfirmed** (replace `CUDA0` with `HIP0` in theory, but no published test). PCIe latency is the bottleneck, not CPU compute speed. The two-tier expert cache proposal (LRU hot experts pinned in VRAM, cold experts in CPU RAM) shows 12-14 t/s vs 0.5-1 t/s pure CPU offload in proof-of-concept -- this is the most impactful pending feature for our use case. Still a feature request, not merged.

### 2. AMD GPU Inference Performance

| Resource | Date | Verdict |
|----------|------|---------|
| [RX 7900 XTX llama-bench ROCm results](https://github.com/1337hero/rx7900xtx-llama-bench-rocm) | 2025-2026 | **directly_applicable** |
| [AITER: AI Tensor Engine for ROCm (AMD blog)](https://rocm.blogs.amd.com/software-tools-optimization/aiter-ai-tensor-engine/README.html) | 2025 | **monitor_only** (MI300X/vLLM only) |
| [AITER MLA decode on MI300X (AMD blog)](https://rocm.blogs.amd.com/software-tools-optimization/aiter-mla/README.html) | 2025 | **monitor_only** |
| [hipBLASLt TensileLite tuning (AMD blog)](https://rocm.blogs.amd.com/artificial-intelligence/hipblaslt-tensilelite-tuning/README.html) | 2025 | **worth_investigating** |
| [llama.cpp ROCm HIP discussion #15021](https://github.com/ggml-org/llama.cpp/discussions/15021) | ongoing | **directly_applicable** |
| [Accelerating llama.cpp on MI300X (AMD blog)](https://rocm.blogs.amd.com/ecosystems-and-partners/llama-cpp-oct2025/README.html) | 2025 | **worth_investigating** |

**Key findings**: RX 7900 XTX benchmarks (ROCm 7.1.1, gfx1100): 7B Q4_0 at **127-139 t/s decode** (FA on), **3.8k t/s prefill**; 70B Q4_K_M dual-GPU at **13.4 t/s decode**, **341 t/s prefill**. AITER numbers (17x MLA decode, 3x fused MoE) are MI300X + vLLM only, not llama.cpp -- ceiling reference only. hipBLASLt TensileLite tuning shows 1.6-2.6x decode speedup on MI300X for small GEMM shapes relevant to single-token decode. Grouped GEMM for MoE yields 29% improvement (CDNA3+ only).

### 3. llama.cpp GPU Offloading State

| Resource | Date | Verdict |
|----------|------|---------|
| [llama.cpp n_gpu_layers guide (2026)](https://bmdpat.com/blog/llama-cpp-n-gpu-layers-explained-2026) | 2026 | **directly_applicable** |
| [Automation for GPU layers + tensor overrides (discussion #18049)](https://github.com/ggml-org/llama.cpp/discussions/18049) | 2026 | **worth_investigating** |
| [Running Llama 4 on consumer GPUs (Botmonster)](https://botmonster.com/posts/how-to-run-llama-4-on-consumer-gpus-2026/) | 2026 | **worth_investigating** |

**Key findings**: `-ngl N` (GPU layer offloading) and `-ot` (tensor overrides) are mature. The split-mode graph scheduler improves prompt processing with partial offload. MoE expert offloading via `--n-cpu-moe` counts from the highest layer down. Multi-GPU via tensor split (`-ts`) works but MoE + multi-GPU has reported bugs (#15263, #15136 -- uneven CPU-MoE distribution). ROCm HIP build is functional but reports of performance regressions on Qwen3.5 models vs Vulkan backend, and RDNA4 GPU idle-state bugs.

### 4. Consumer GPU Options

| GPU | VRAM | Est. Price | ROCm Status | llama.cpp Decode (7B Q4) | Verdict |
|-----|------|-----------|-------------|--------------------------|---------|
| RX 7900 XTX | 24GB GDDR6X | ~$750-900 | **Stable** (ROCm 7+, gfx1100) | ~130 t/s | **directly_applicable** |
| RX 9070 XT | 16GB GDDR6 | ~$550 | **Experimental** (gfx1201, bugs: idle-state, mmproj) | untested | **monitor_only** |
| MI100 | 32GB HBM2 | ~$300-500 used | Supported (older arch) | ~80-100 t/s est. | **worth_investigating** |
| RTX 3090 | 24GB GDDR6X | ~$350-450 used | N/A (CUDA) | ~140 t/s | **worth_investigating** (MegaTrain) |

**Key findings**: RX 7900 XTX is the best AMD consumer option -- 24GB VRAM, stable ROCm, ~85-90% of RTX 4090 throughput. RX 9070 XT has RDNA4 native FP8 WMMA (promising) but ROCm bugs remain (GPU stuck at 100% after inference). MI100 is mostly phased out of used market. For our hybrid MoE use case, 24GB VRAM holds attention + shared expert for models up to ~30B-A3B; larger models need MI300X-class VRAM.

### 5. KV Cache CPU/GPU Split

| Resource | Date | Verdict |
|----------|------|---------|
| [NVIDIA KV cache offload blog](https://developer.nvidia.com/blog/accelerate-large-scale-llm-inference-and-kv-cache-offload-with-cpu-gpu-memory-sharing/) | 2025 | **worth_investigating** |
| [TurboQuant extreme KV cache quantization (discussion #20969)](https://github.com/ggml-org/llama.cpp/discussions/20969) | 2026 | **worth_investigating** |
| [Context kills VRAM (Medium)](https://medium.com/@lyx_62906/context-kills-vram-how-to-run-llms-on-consumer-gpus-a785e8035632) | 2025 | **monitor_only** |

**Key findings**: KV cache for 128k context on a 70B model consumes ~40GB alone. For our hybrid approach, keeping KV cache in GPU VRAM alongside attention weights is ideal but VRAM-limited. Quantizing KV to Q8 halves the footprint. Our 1.13TB RAM is the fallback -- CPU-side KV is viable with PCIe 5.0 bandwidth (~64 GB/s bidirectional). TurboQuant (extreme KV quantization) could compress KV cache enough to fit long contexts in 24GB VRAM alongside model weights.

### Summary Assessment

**Primary path: NVIDIA DGX Spark ($4,699)**
DGX Spark's unified memory architecture sidesteps the PCIe bottleneck that makes every other option in this survey a compromise. At ~70 t/s decode on MoE models, with 128GB unified memory and active software optimization from NVIDIA, it is the most practical GPU acceleration path. For models exceeding 128GB (our 122B-A10B, 246B REAP), two units link via NVLink for 256GB. The ARM CPU is weaker than EPYC for raw expert compute, but expert compute is no longer separated from GPU compute -- the entire model lives in one memory space.

**Secondary paths (retained as fallback/reference):**
1. **Near-term** (no GPU): Current CPU-only NUMA 4-way remains competitive for short-context MoE decode (memory-bandwidth-bound, GPU gains marginal)
2. **Budget AMD GPU** ($750-900): RX 7900 XTX for hybrid MoE offload -- attention+dense on GPU (~130 t/s on small models), experts on CPU via NUMA. Requires confirming `-ot` works with HIP backend. Less attractive now that DGX Spark costs only ~5x more while eliminating the PCIe bottleneck entirely.
3. **Datacenter AMD** (MI300X/MI325X): Still the ceiling for raw throughput (5.3 TB/s HBM3, hipBLASLt grouped GEMM). Only relevant if workload scales beyond what two DGX Sparks can handle.
4. **Open investigation**: Two-tier expert cache (#20757) remains valuable for discrete GPU setups but is irrelevant on unified memory architectures like DGX Spark.

## Research Intake Update — 2026-04-21

### New Related Research
- **[intake-427] "0xSero/GLM-5.1-555B-A14B-REAP-NVFP4"** (huggingface.co/0xSero/GLM-5.1-555B-A14B-REAP-NVFP4)
  - Relevance: NVFP4 quantization (4-bit weights + FP8 per-group scales) of REAP-pruned GLM-5.1 (256→192 experts, 14B active). Compresses 1.1TB BF16 to 320GB. Requires Blackwell sm_100+ (B200) or sm_120 (RTX PRO 6000) — will NOT run on H100 natively.
  - Key technique: REAP expert pruning + NVFP4 quantization; Intel AutoRound 0.12.2 calibration (50 iters, 512 nsamples); selective BF16 retention for quant-sensitive layers; sglang deployment on 8x RTX PRO 6000 Blackwell 96GB.
  - Reported results: 3.4x compression (1.1TB→320GB); no published quality benchmarks yet.
  - Delta from current approach: NOT actionable for current CPU-first stack — 320GB exceeds working memory budget, NVFP4 is GPU-native format, and llama.cpp DSA indexer is unimplemented. However, the NVFP4 calibration recipe (dataset mix design, selective BF16 retention, AutoRound settings) is useful methodology if/when Blackwell hardware is acquired. The 7-variant GLM-5.1 REAP family table (spanning BF16/NVFP4/GPTQ/GGUF across 192/154 expert counts) is a valuable reference catalog.
