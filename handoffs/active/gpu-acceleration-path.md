# GPU Acceleration Path — CPU+GPU Hybrid Inference

**Status**: researched (literature survey complete 2026-04-14, RX 7900 XTX + hybrid MoE path prioritized)
**Created**: 2026-04-10 (via research intake deep-dive)
**Updated**: 2026-04-21 (no GPU acquired; vLLM DDTree+Dflash plan still current)
**Categories**: hardware_optimization, inference_serving, moe_optimization, speculative_decoding
**Priority**: LOW (activates when GPU hardware is acquired)
**Workstream**: Future
**Parent index**: [`inference-acceleration-index.md`](inference-acceleration-index.md)
**Related**: [`llama-cpp-v3-upstream-rebuild.md`](../completed/llama-cpp-v3-upstream-rebuild.md) (HIP build path), [`kv-cache-quantization.md`](../completed/kv-cache-quantization.md) (GPU KV strategy)

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

## Research Intake Update — 2026-04-26

GPU-stack curriculum ingested (intake batch 458-472). All entries below are DGX-Spark-prep references; none are actionable on current CPU stack.

| ID | Source | Relevance Summary |
|----|--------|-------------------|
| intake-458 | FlashInfer (arXiv:2501.01005) | Block-sparse-as-unifier KV format + JIT attention templates. Production attention backend for vLLM/SGLang/MLC — Day-0 dependency when Spark lands. |
| intake-461 | SGLang repo | Engine itself (intake-041 covered RadixAttention paper). Zero-overhead CPU scheduler + cache-aware load balancer + compressed-FSM structured output are portable patterns. Has documented Intel Xeon CPU backend. |
| intake-462 | vLLM repo | Engine itself (intake-033 covered PagedAttention paper, intake-152/424/456 covered components). Active x86 CPU backend exists; chunked-prefill + automatic prefix-cache scheduling concepts portable. |
| intake-463 | TensorRT-LLM repo | NVIDIA peak stack with **Wide-EP (large-scale expert parallelism)**, DWDP on NVL72, FP8/FP4 native, Prefill/Decode disaggregated serving, MTP/EAGLE/n-gram spec dec. Has Jetson branch (closest analog to Spark). |
| intake-464 | FlashAttention-3 (arXiv:2407.08608) | Hopper-era warp-specialization + WGMMA + FP8 attention. Hardware-specific — DGX Spark Blackwell is the target. Producer/consumer warp pattern has speculative CPU prefetch/compute analogue. |
| intake-465 | CUTLASS repo | NVIDIA Tensor Core GEMM template library. CuTe layout abstractions + grouped-GEMM patterns inform CPU MoE expert-dispatch design. Listed compatibility includes DGX Spark (SM12.1, CUDA 13.0). |
| intake-466 | Triton repo | OpenAI kernel DSL. Most modern inference papers (FlashAttention 2/3, FlashInfer, MLA decode, log-linear GDN, BackLite) ship Triton reference impls — required literacy for kernel-paper consumption. CPU backend (triton-cpu) experimental. |

**Activation triggers** (unchanged): all become Tier-1 actionable when DGX Spark or equivalent GPU is acquired. Until then, treat as reading-list references.

**One non-DGX-Spark insight**: SGLang's structured-output via compressed FSM (~3× faster JSON decoding) is a clear upgrade target for llama.cpp's grammar engine independent of GPU acquisition. Worth a separate evaluation handoff if grammar throughput becomes a bottleneck.

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
- GPU works because parallel scan handles recurrent state, unlike CPU where each token traverses 30+ Delta Net layers sequentially — [DFlash deep-dive](../../research/deep-dives/dflash-dart-diffusion-speculation.md)
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
  - Delta from current approach: The NVFP4 variant described above is NOT actionable for the CPU-first stack (GPU-native format, Blackwell-only). However, the NVFP4 calibration recipe (dataset mix design, selective BF16 retention, AutoRound settings) is useful methodology if/when Blackwell hardware is acquired.
  - **2026-04-22 REVISION**: A **GGUF variant** (`0xSero/GLM-5.1-555B-A14B-REAP-GGUF`, Q4_K_M = 325GB) also exists and IS actionable for the CPU-first stack. This variant has its own dedicated evaluation handoff: [`glm51-reap-cpu-evaluation.md`](glm51-reap-cpu-evaluation.md). The NVFP4 variant documented above remains relevant only for future GPU deployment scenarios.

## Research Intake Update — 2026-04-23

### New Related Research

- **[intake-447] "Lucebox Hub: Hand-tuned LLM inference for consumer GPUs (Megakernel + DFlash GGUF port)"** (github.com/Luce-Org/lucebox-hub)
  - Relevance: First published GGUF Q4_K_M port of DFlash speculative decoding, running on a single RTX 3090 via a llama.cpp fork (`Luce-Org/llama.cpp-dflash-ggml`) with tree-mode support. Directly contradicts the "no llama.cpp / no GGUF" blocker recorded in [intake-158](../../research/intake_index.yaml) and the `vLLM DDTree+Dflash` note above — there is now a llama.cpp-native path (GPU only) for DFlash + DDTree on Qwen3.5-27B.
  - Key technique: persistent megakernel (single CUDA dispatch, all 24 layers of Qwen3.5-0.8B) + custom tree-aware SSM (DeltaNet) state-rollback kernels + GGUF Q4_K_M quant targeting. Ampere+ (sm_86+), CUDA 12+, PyTorch 2.0+, batch size 1.
  - Reported results: DFlash on RTX 3090 reaches **207.6 tok/s peak / 129.5 tok/s mean on HumanEval** (5.46x / 3.43x over autoregressive on the same card). Megakernel Qwen3.5-0.8B reaches **37,800 tok/s prefill, 413 tok/s decode** (1.55x vs llama.cpp BF16, 30% less power).
  - Delta from current approach: our completed DFlash evaluation (`handoffs/completed/dflash-block-diffusion-speculation.md`) concluded NOT VIABLE on CPU Q4_K_M; this is an orthogonal GPU path that becomes the natural integration reference if/when GPU hardware is acquired. RTX 3090 is not our target (DGX Spark GB10 / Blackwell is) — the kernels would need re-tuning for Blackwell, but the integration pattern (llama.cpp fork with tree-mode + GGUF) is the reusable piece. Credibility is medium-low (single author collective, self-reported benchmarks, no third-party replications yet).
  - Action: **track, do not activate**. Revisit at GPU-acquisition trigger. Pin `Luce-Org/llama.cpp-dflash-ggml` as the integration reference for the vLLM/llama.cpp + DFlash + DDTree reproduction plan documented above.

- **[intake-448] "Look Ma, No Bubbles! Designing a Low-Latency Megakernel for Llama-1B"** (hazyresearch.stanford.edu/blog/2025-05-27-no-bubbles)
  - Relevance: Foundational methodology paper that intake-447 ports to consumer GPUs. Hazy Research (Stanford) describes the persistent-megakernel + on-GPU-interpreter pattern that eliminates per-op kernel launch overhead.
  - Key technique: one persistent CUDA kernel; each SM runs a pre-scheduled instruction sequence via an on-GPU interpreter; shared-memory pagination (213 kB / 13 pages, explicit req/release); counter-based global-memory synchronization for instruction dependencies.
  - Reported results: **78% memory-bandwidth utilization on H100**, sub-1ms forward pass (2.5x vs vLLM, 1.5x vs SGLang); ~680 us on B200 (3.5x vs vLLM). Llama-1B workload.
  - Delta from current approach: direct relevance to any future Blackwell / DGX Spark inference engine we might build — establishes the pattern Lucebox uses and that Mirage Persistent Kernel (arXiv:2512.22219) and ThunderMLA extend. Not activatable until GPU hardware arrives.
  - Action: **read as design primer** at GPU-acquisition trigger. Candidate for future literature expansion: ThunderMLA + Mirage Persistent Kernel.

## Research Intake Update — 2026-04-24

### New Related Research

- **[intake-455] "Qwen3.6-27B Spec-Decoding on RTX 4090 with 1.7B Same-Family Draft (community note)"** (`inline:qwen36-27b-spec-decoding-rtx4090-2026-04-24`)
  - Relevance: consumer-GPU (RTX 4090, 24 GB) reference point for speculative decoding on the freshly-released **Qwen3.6-27B dense** target model (released 2026-04-22) with a vanilla Qwen3-1.7B draft via ik_llama.cpp. Directly adjacent to this handoff's future GPU spec-dec evaluation.
  - Reported results: 5.9× speedup over Ollama (26 → 154 tok/s peak @ 85.2% acceptance, 3-run avg ~127 tok/s); 128K–192K context retains 126–159 tok/s on 4000-tok generations; VRAM ~21.8 GB at 96K with Q4 KV cache + FA.
  - Key technique: same-family 1.7B draft beats a 4B distilled variant on **net throughput** (154 vs 85 tok/s) despite slightly lower acceptance — draft forward-pass cost dominates acceptance gain. ik_llama.cpp exposes `--draft-max 12 --draft-min 3 --draft-p-min 0.6` flags that Ollama/LM Studio do not.
  - Caveats (Tier 2b): (1) anonymous community note, not peer-reviewed; (2) run-to-run acceptance variance **49.6%–85.2% across 3 runs** is large — 154 tok/s is a best-case peak, not typical; (3) thc1006/qwen3.6-speculative-decoding-rtx3090 (2026-04-19) tested 19 configs on Qwen3.6-**35B-A3B** + 0.8B draft on RTX 3090 post-PR-#19493 and found **no net speedup** on Ampere + A3B MoE (MoE verification-wall / hybrid SSM issue); (4) vLLM issue #36872 documents spec-dec gibberish + throughput collapse under some configs, and Qwen acceptance-rate collapse (61.3% → 0.9% → 0.0%) across consecutive requests is documented elsewhere — fragility is real.
  - Delta from current approach: no GPU acquired; this is literature-only for now. Two durable takeaways worth recording even before hardware lands — (a) same-family small-draft heuristic (smallest-draft-that-preserves-vocabulary wins on **net** throughput), (b) 27B-dense + 1.7B-draft is a concrete GPU-era candidate worth re-checking at GPU-acquisition trigger. Do not transfer the 5.9× claim to the CPU/35B-A3B production stack — hybrid-SSM verification-wall documented in `wiki/speculative-decoding.md` makes these results non-portable.
  - Action: **bookmark only**. Promote to evaluation when GPU acquired OR when Qwen3.6-27B dense is a serious CPU-inference candidate for the worker/coder slot (see `../completed/qwen36-production-upgrade.md` for the model-intake flag).

## Research Intake Update — 2026-04-28

### New Related Research

- **[intake-488] "Speculative Decoding with Mamba"** (github.com/itsdaniele/speculative_mamba; arxiv:2408.15237 Mamba-in-Llama, NeurIPS 2024)
  - Relevance: PyTorch + CUDA + flash_attn + causal_conv1d implementation of pure-Mamba target+draft spec-dec. Direct GPU-era candidate to evaluate if/when GPUs are acquired AND a Mamba-architecture model (Falcon-Mamba, Codestral-Mamba) enters the stack.
  - Reported results: ~68% acceptance on a single English-prose example with K=3, fp16; CUDA-graph-on-draft to amortize launch overhead. Single-prompt anecdotal numbers, no benchmark suite.
  - Delta from current approach: bookmark-only — neither precondition (GPU + Mamba target) holds today. File alongside ik_llama.cpp / Qwen3.6-27B-RTX4090 community note as the SSM-on-SSM GPU baseline reference.

- **[intake-490] "Hybrid Models Meet SGLang: More than Full Attention"** (pytorch.org blog, Dec 2025) — verdict: **adopt_patterns**
  - Relevance: Production-grade hybrid-SSM serving on H200 with EAGLE/MTP — strongest existing reference for what GPU-era hybrid serving looks like at scale. Sets the upper-bound benchmark anchor for any future EPYC GPU port (Qwen3-Next-80B-A3B-FP8 → 324.57 tok/s with accept length 4.231).
  - Key technique: HybridReqToTokenPool + HybridLinearKVPool + MambaRadixCache + Elastic Memory Pool via CUDA VMM + State Transfer Channel for PD-disaggregation + EAGLE/MTP rollback over SSM state.
  - Delta from current approach: no GPU acquired, no SGLang deployment planned. Three durable takeaways: (a) per-layer KV-skip-remap for linear-attention layers is the canonical primitive; (b) elastic Mamba/KV pool partitioning under fixed memory budget is the canonical recipe; (c) EAGLE/MTP-on-hybrid is solvable on the architecture side once SSM rollback semantics are wired. Use as the design reference if/when GPUs are acquired and hybrid SSM serving is in scope.
  - Caveats (Tier 2b): per-request snapshot copy cost for in-place SSM state; agentic-workload Mamba-state cache pressure (sgl-project/sglang #20144); single-batch H200 demo.

## Research Intake Update — 2026-04-28 (deep-dive integration)

### New Related Research

- **[intake-497] "tile-ai/tilelang-puzzles + parent TileLang DSL"** (github.com/tile-ai/tilelang-puzzles; parent github.com/tile-ai/tilelang, 5.8k★)
  - **Deep-dive**: [`research/deep-dives/tilelang-puzzles-kernel-dsl.md`](../../research/deep-dives/tilelang-puzzles-kernel-dsl.md) — kernel-DSL evaluation matrix for GPU-day.
  - Relevance: MEDIUM (bumped from low after deep-dive). The puzzles repo on its own is a 10-script tutorial; the parent project is the Peking U + Microsoft Research kernel DSL underlying **BitBLAS** (low-bit GEMM, FP16/FP8 × INT4/INT8/INT2/INT1) and **AttentionEngine**. BitBLAS is the natural GPU successor to our Q4_K_M / Q6_K / Q8_0 ggml CPU path, which makes TileLang the right authoring DSL for any custom GGUF→GPU quant adapters.
  - **Strongest unique advantage is the AMD path**: parent README claims FlashMLA-MI300X parity vs hand-tuned assembly. If GPU-day path is RX 7900 XTX or MI300X (this handoff's AMD branch), TileLang is the differentiated kernel DSL. On NVIDIA Spark, FlashInfer + CUTLASS + TRT-LLM (intake-458/465/463) dominate; TileLang's CuTeDSL backend (Dec 2025) lowers to CUTLASS, which is an implicit concession that for NVIDIA peak, CUTLASS is the substrate.
  - **GPU-day action queue (gated on hardware)**: (1) Day-0: tilelang-puzzles 1-10 in 4 hours as engineer onboarding; (2) Day-1 NVIDIA: TileLang FA puzzle output vs Triton FA reference vs FlashInfer vs FA3 on actual GPU → DSL decision matrix; (3) Day-1 AMD: reproduce FlashMLA-MI300X parity claim on RX 7900 XTX or MI300X; (4) Day-2: BitBLAS GGUF compatibility — does it load Q4_K_M / Q6_K directly, or do we need a thin K-grouped quant adapter? Critical-path question for production GPU low-bit GEMM.
  - **Non-actions**: do NOT author CPU kernels in TileLang (Zen 5 / AVX-512BW / NUMA-4-way path remains hand-tuned ggml per `project_q8_8x8_avx512bw_outcome` and `project_x86_kquant_repack_gaps` memories). Do NOT pre-commit to TileLang before GPU lands.
  - Caveats: educational fork has weak signals (7 commits, idle 5w as of 2026-04-28); no peer-reviewed paper for the parent DSL itself; multi-backend portability claims always degrade in production — verify backend maturity at GPU-day.

- **[intake-498] "Agentic World Modeling: Foundations, Capabilities, Laws, and Beyond"** (arxiv:2604.22748, Chu et al., 42 authors) — *cross-listed here for the GPU-gated angle*
  - **Deep-dive**: [`research/deep-dives/agentic-world-modeling-levels-laws-taxonomy.md`](../../research/deep-dives/agentic-world-modeling-levels-laws-taxonomy.md) — full L×R taxonomy + EPYC-stack mapping.
  - GPU-gated angle: the survey's Levels × Laws taxonomy (L1 Predictor / L2 Simulator / L3 Evolver × physical/digital/social/scientific) provides the framing for **Agent-World Phase 2** (`agent-world-env-synthesis.md`), which is GPU-gated for multi-environment GRPO RL training. When GPU lands and Phase 2 trains, evaluate the trained policy vs autopilot-evolved policy on the four evaluation principles (long-horizon coherence, intervention sensitivity, constraint consistency, closed-loop use) as a cross-rubric transfer experiment — does Agent-World-style RL produce better-on-the-rubric L3 systems than autopilot's species loop?
  - CPU-feasible adoption (already underway in autopilot-continuous-optimization.md and agent-world-env-synthesis.md): vocabulary alignment (L1/L2/L3 + four-regime), four-principle AR-3 reporting rubric, L3-governance completeness check on autopilot SafetyGate. Bookmark MREP (Minimal Reproducible Evaluation Package, Section E.6) — proposed but not released; if it ships, run autopilot through it as external sanity check.
  - Note: this entry is primarily an autopilot/agent-world artifact; cross-listed here purely for the Phase-2 GPU-gated cross-rubric eval and the "watch for MREP shipment to integrate at GPU-day" hook.

- **[intake-500] "MLC LLM — Universal LLM Deployment Engine With ML Compilation"** (github.com/mlc-ai/mlc-llm + llm.mlc.ai docs) — verdict: **worth_investigating**
  - Relevance: MEDIUM. Completes the GPU-prep engine bundle alongside intake-461 (SGLang), intake-462 (vLLM), intake-463 (TensorRT-LLM). MLC-LLM is the only entry in the bundle that is **compiler-based** (Apache TVM Unity / Relax / TensorIR via Tianqi Chen's lineage) rather than hand-tuned-per-backend, and the only one targeting **Vulkan + WebGPU + iOS Metal + Android OpenCL** as first-class backends.
  - Activation triggers (concrete, GPU-acquisition-conditional):
    1. **Consumer AMD path (RX 7900 XTX / similar)**: MLC-LLM Vulkan backend is the simpler alternative to llama.cpp `-DGGML_HIP=ON gfx1100` build path documented above — Vulkan avoids ROCm/HIP toolchain complexity. Plan-B alongside the llama.cpp HIP build, not plan-A.
    2. **Browser / WebGPU demo**: WebLLM (sister project) is the canonical browser deployment path — only intake entry covering this.
    3. **Mobile demos (iOS / Android)**: only intake entry with first-class mobile-runtime support.
  - **NOT** activated by:
    - DGX Spark Blackwell / H100-server peak throughput targets — vLLM (intake-462, with DDTree+Dflash spec dec section above) and SGLang (intake-461) consistently lead 2026 H100 throughput tables; MLC-LLM is excluded from those head-to-head benchmarks. Use the existing vLLM plan for Spark.
    - CPU-only research as a *replacement* for llama.cpp — MLC-LLM **does** ship a CPU LLVM backend (prebuilt `mlc-ai-nightly-cpu` wheel; mlc-ai/mlc-llm#795), but it is unlikely to match our hand-tuned ggml path that encodes Zen 5 specifics (`project_q8_8x8_avx512bw_outcome` 8x8 AVX-512BW Q8_0, `project_zen5_vnni_vs_maddubs` MADDUBSW > VPDPBUSD, NUMA-4-way mmap layout). Worth a measurement rather than an assumption if the question becomes load-bearing. Production CPU path stays llama.cpp ggml.
    - MoE expert-offloading via `-ot "exps=CPU"` — that's a llama.cpp-specific lever; MLC-LLM has no analogous mechanism documented.
  - **Compile-step friction** (caveat): unlike GGUF point-and-run, MLC-LLM requires a per-model + per-target compilation step, and uses its own quant formats (q4f16_1, q4f16_ft) — not GGUF compatible. Dual-artifact storage cost if adopted alongside llama.cpp. Acceptable for stable production deployment, costly for rapid model-quant iteration.
  - **Hybrid SSM verification needed**: docs intro names Llama-3 and Phi-2; Qwen3.5/3.6 hybrid (Delta Net) support is not enumerated. Confirm before assuming production stack ports cleanly. TileLang/BitBLAS connection (intake-497) is relevant: same Apache TVM lineage, so any custom Delta Net kernel work would be authored in compatible DSLs.

## Research Intake Update — 2026-04-28 (Luce-DFlash Qwen3.6-27B writeup)

### New Related Research

- **[intake-501] "Luce DFlash Brings 2x Speculative Decoding to Qwen3.6-27B on a Single RTX 3090"** (NYU Shanghai RITS blog, 2026-04-28; writeup by Utku Ege Tuluk; method by Z Lab — Jian Chen, Yesheng Liang, Zhijian Liu)
  - Relevance: third-party writeup that extends intake-447 (Lucebox Hub) and intake-455 (RTX 4090 Qwen3.6-27B community note) with **Qwen3.6-27B specific data on a single RTX 3090** — the consumer-GPU lower bound for our gated-DeltaNet GPU path. Confirms Lucebox-style llama.cpp port (`Luce-Org/llama.cpp@luce-dflash`) is the integration reference for consumer-Ampere through Blackwell (sm_86 → sm_121 = DGX Spark); Compatible with: Ada (RTX 4090), Blackwell (RTX 5090), DGX Spark/Jetson AGX Thor (sm_121, sm_110).
  - Key technique: same DFlash block-diffusion drafter + DDTree (budget=22) + 3 custom CUDA kernels for tree-aware SSM state rollback as intake-447. **New external finding: Qwen3.5-27B-DFlash drafter loads on Qwen3.6-27B unchanged** (identical `Qwen35` identifier, layer/head dims) — drafter portability across point-version model upgrades.
  - Reported results (RTX 3090):
    - Qwen3.6-27B Q4_K_M peak **207.6 tok/s vs 38.0 autoregressive (5.46×)**
    - HumanEval mean **129.5 tok/s (3.43×)**, Math500 110.5, GSM8K 96.2
    - 128K context Q4_0 sustained **134.78 tok/s** — useful long-context anchor
    - Cross-version drafter penalty: acceptance length **9.18 (3.5)** vs **5.05 (3.6 with 3.5 drafter)** → ~2× speedup on 3.6 even without retraining
  - Delta from current approach: corroborates intake-447 with external data + new model target (Qwen3.6, released 2026-04-22). Does NOT change the GPU-acquisition gate. Adds a concrete drafter-portability data point (3.5 → 3.6) that reduces the "wait for new drafter at every model upgrade" risk in any future GPU port plan.
  - Caveats (Tier 2b not formally run; flagged inline): self-reported single-author writeup, commercial-product promotion (Luce-Org), no third-party replication of the 3.6-specific numbers. Acceptance length 5.05 on a release-day cross-version drafter is not the steady-state figure — a 3.6-native drafter when published should restore the ~9 acceptance-length range.
  - Action: **track, do not activate**. Keep `Luce-Org/llama.cpp@luce-dflash` pinned as the integration reference. At GPU-acquisition trigger, prefer the 3.6-native DFlash drafter once Z Lab publishes one; until then, the 3.5 drafter is a usable fallback.

## Research Intake Update — 2026-05-20 (ECHO 3-gate adoption trigger)

### ECHO — Terminal Agents Learn World Models for Free (intake-571 deep-dive)

- **Paper**: ECHO = Environment Cross-entropy Hybrid Objective; auxiliary CE loss on terminal-response tokens added to GRPO. Authors Shrivastava/Awadallah/Papailiopoulos (MSR). PDF only — `github.com/anadim/anadim.github.io/blob/master/papers/echo.pdf`. Numbers verified from local PDF read at `/tmp/echo.pdf`: TB-2.0 pass@1 Qwen3-8B 2.70%→5.17%, Qwen3-14B 5.17%→10.79%. Loss form: `L_total = L_GRPO + 0.05·L_Env`; λ=0.05 base / 0.02 SFT-init; warning-prefix tokens excluded from O′; cosmetic tokens (timestamps, ANSI) kept with 0.05-0.10 nat irreducible CE floor.

- **Status**: `worth_investigating` with three **hard gates** before upgrade to `adopt_patterns`:
  1. **Repo publication gate** — `github.com/microsoft/echo-rl` (advertised in the PDF as the official code repo) currently returns HTTP 404 as of 2026-05-20. No training code, no released ECHO-tuned checkpoints. Verified via `gh api repos/microsoft/echo-rl` (404) and direct `curl -I` (404). **Reproduction is blocked on this gate independent of GPU acquisition.**
  2. **Independent reproduction gate** — ≥1 external group must confirm the env-only verifier-free claim (Table 4) OR refute the TBLite −3.9pp regression. The verifier-free framing is the most novel and least-supported claim; until corroborated, the universal "world model for free" narrative is overstated by paper's own Table 4.
  3. **GPU + trainer gate** — DGX Spark acquired (`project_dgx_spark_target`: not yet) AND a single-node GRPO trainer is operational. The paper used **8×B200 GPUs**, 24-48h wallclock per run, ~15 runs across model × seed (~$10-30k at current rental). Even a single DGX Spark cannot match this throughput; multi-node rental may be required.

- **GPU-day priority when triggers fire**: when all three gates clear, ECHO reproduction lands as a Phase-2 candidate alongside Endless Terminals PPO consumption (intake-574, AW-9 in `agent-world-env-synthesis.md`). Order: (a) reproduce released Qwen3-8B ECHO checkpoint eval on TB-2.0 first (cheap, no training), (b) attempt env-only verifier-free fine-tune on a held-out env subset to test the universal-positive vs TBLite-regression framing, (c) only then commit to a full GRPO+ECHO training run.

- **CPU-actionable spinoff (NOT ECHO, intake-571 spike, no GPU needed)**: **PEAF — Prediction-Error-As-Feature** lives in `autopilot-continuous-optimization.md` and `scripts/autopilot/peaf.py` in epyc-orchestrator. Logs the controller's pre-trial forecast of (quality, speed, cost, reliability) and computes L1 surprise vs the actual `eval_result`. Behind `EPYC_AUTOPILOT_PEAF=1`, default off. Cheap-kill criterion: if Pearson r² between surprise and post-trial Pareto-rank improvement < 0.10 over 200+ predicted trials, abandon. Borrows the underlying "prediction error = understanding signal" intuition without any RL training — orthogonal to this handoff's GPU-gated work but worth noting as the only ECHO-adjacent thing buildable on EPYC today.

- **Related (intake-574, NOT GPU-gated for env-gen)**: Endless Terminals env-generation runs on EPYC today (decode-only Stages I-IV with gemma4-26B-A4B as filter substitute, ~50-100 wall-hr in low-priority worker slot — see master-index queue #46/#47 for AW-7/AW-8). Only the PPO **consumption** of the env corpus is GPU-gated (AW-9 in `agent-world-env-synthesis.md`). Decoupling means env corpus can accumulate now; training waits.

## Research Intake Update — 2026-05-20

### New Related Research

- **[intake-576] "Nemotron-Labs-Diffusion: A Tri-Mode Language Model Unifying Autoregressive, Diffusion, and Self-Speculation Decoding"** (NVIDIA tech report, 2026-05-19; no arXiv ID)
  - Relevance: direct sibling to the DFlash + DDTree + Lucebox GPU-acceleration plan tracked above. Self-speculation is **architecturally unified** (one set of weights, attention-pattern switch) rather than drafter+target, which removes the cross-model alignment cost that complicates DFlash deployment.
  - Key technique: tri-mode unified model with **shared KV cache** between diffusion-mode draft and AR-mode verify. Released family: 3B, 8B, 14B (Base + Instruct) + VLM-8B under NVIDIA Nemotron Open Model License (not Apache-2.0 — flag for legal review on commercial deployment but per `feedback_license_not_a_blocker` not a project blocker).
  - Reported results: **GB200, 8B, concurrency=1**: 850 tok/s self-spec vs 253 tok/s AR (3.3×), 1015 tok/s w/ custom CUDA kernels (4×); **DGX Spark (GB10), 8B, concurrency=1, w4a16**: 112 tok/s vs 41.8 tok/s AR (2.7×). 4× higher throughput on SPEED-Bench via SGLang. 5.9× tokens-per-forward vs Qwen3-8B-no-MTP, 3× higher acceptance length and 2.2× speedup vs Qwen3-8B-Eagle3.
  - Delta from current approach: this is a parallel candidate to DFlash + DDTree on Spark. DFlash retains the Qwen-family advantage (drafter portability across 3.5 → 3.6 per intake-455); Nemotron-Diff retains the unified-model + shared-KV advantage. Both are vLLM/SGLang-only, BF16/w4a16-only — no llama.cpp path announced. **DGX Spark (sm_121) is one of the two reported hardware targets** in the Nemotron-Diff report, alongside GB200 — so this entry is **Day-0 eligible** if/when DGX Spark is acquired.
  - Caveat: all reported numbers are concurrency=1. Intake-567 (ECHO) showed vanilla Eagle3 underperforms AR at batch≈128; whether Nemotron-Diff self-spec degrades at high concurrency is open and not addressed in the report.
  - Sibling intake entries (URL-dedup): intake-577 (NVIDIA research landing), intake-578 (HF collection — 7 variants, BF16-only).
  - Action: tracked here as a parallel candidate alongside the DFlash path. No code action until DGX Spark lands or a credible community port surfaces. Re-run Tier 2b contradicting-evidence search in ~30 days when independent replications / llama.cpp issue tickets accumulate.
  - **Deep dive 2026-05-20**: [`research/deep-dives/nemotron-labs-diffusion-tri-mode.md`](../../research/deep-dives/nemotron-labs-diffusion-tri-mode.md) — full PDF parse, per-mode algorithms, verbatim benchmark tables (Tabs. 5–10), per-GPU speedups (Fig. 9), SOL ceiling (7.60× acceptance / 76.5% real-TPF headroom over Linear SS), 15–25 day CPU port effort estimate vs DFlash's 13–20 days but with better prerequisites. DGX Spark numbers honest read: INT4-vs-INT4 is 2.69× (not the 4.56× the model card implies by comparing INT4-SS to FP8-AR). Headline acceptance length is **5.46 native / 6.82 LoRA on SPEED-Bench** vs Eagle3's 2.75 and Qwen3-9B-MTP's 4.24.
