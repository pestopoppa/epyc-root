# Hardware Optimization

**Category**: `hardware_optimization`
**Confidence**: verified
**Last compiled**: 2026-04-14
**Sources**: 19 documents

## Summary

The entire project is built around the AMD EPYC 9655 "Turin" processor: 96 physical cores (192 threads), 1.13 TB DDR5-5600 ECC across 12 memory channels (~460 GB/s theoretical bandwidth), and true 512-bit AVX-512 (not Intel's double-pumped variant). The storage layer is a 2x Solidigm P44 Pro 2TB NVMe RAID0 array delivering 12.5 GB/s sequential reads, enabling a 280 GB model to be mmap'd in about 22 seconds.

The single most impactful optimization discovered in this project is NUMA-aware CPU pinning. The EPYC 9655 has 2 NUMA nodes (cores 0-47 and 48-95, with hyperthreads 96-191), each with ~566 GB of RAM. Running a model naively across all 192 threads yields dramatically worse performance than NUMA-pinned instances. For the 35B-A3B frontdoor model, 4 independent instances on NUMA quarters (48 threads each) achieved 49.66 t/s aggregate -- a 6.9x improvement over the 7.25 t/s baseline. This is a config-only change requiring zero code modifications. The production stack now runs 4-way NUMA quarters for frontdoor (~50.8 t/s) and coder_escalation (~43.3 t/s), with single-node pinning for larger models.

Three runtime settings are non-negotiable: OMP_NUM_THREADS=1 (llama.cpp handles its own parallelism; nested OpenMP can halve throughput), numactl --interleave=all for single-instance models (distributes data across all 12 channels), and using only physical cores (hyperthreading hurts inference due to cache contention). The production stack uses taskset -c for NUMA pinning since numactl --membind is blocked in the container environment, relying on first-touch memory policy instead.

The system's 1.13 TB RAM enables a HOT/WARM/COLD three-tier memory architecture. HOT models (~701 GB with multi-instance copies) are always resident with --mlock, eliminating 15-90 second cold-start penalties. WARM models load on demand via mmap from NVMe (~12 GB/s, so a 140 GB model loads in ~12 seconds). COLD models remain on disk. The 120 GB OS SSD is strictly protected -- a December 2025 incident where Claude Code filled /tmp/claude with 20 GB crashed the machine, prompting a three-layer defense (bind mount, real-time monitoring, emergency cleanup). Another incident in January 2026 demonstrated that pytest -n auto on a 192-thread machine spawns 192 workers, each loading ~3 GB of embedding models, exhausting the full 1.13 TB of RAM.

## Key Findings

- **NUMA is the dominant optimization**: 4-way NUMA quarter pinning delivers 6-7x aggregate throughput on models up to 65 GB. Single-node (96 threads on one NUMA node) is 1.85x faster than all-cores (192 threads) for MoE models because cross-NUMA memory access penalty is devastating. [progress/2026-03-18, numa-orchestrator-deployment.md]
- **MoE models are NUMA-sensitive, dense models are compute-sensitive**: Models with few active parameters (MoE) see 6-7x gains from NUMA pinning because cross-node memory access dominates cheap compute. Dense models see only ~2x because all parameters are active and 48 threads is not enough compute. Large hybrids (122B+) are recurrent-bottlenecked at ~12 t/s regardless of NUMA config. [numa-orchestrator-deployment.md]
- **Node 1 is ~85% of Node 0 performance**: Consistent across all configs, likely due to first-touch page cache bias (Node 0 loads first, OS caches pages there). Production should account for this asymmetry. [progress/2026-03-18]
- **Concurrent vs sequential cross-node**: When both NUMA nodes generate simultaneously, per-instance throughput drops ~25% (13.3 to 9.4 t/s) due to inter-node traffic. Sequential queries to alternating nodes avoid this penalty. [progress/2026-03-18]
- **Q4_K_M is optimal for hybrid models**: Recurrent state update (constant cost) fills most compute in hybrid architectures. Q8 costs 17-39% speed for marginal quality gain. Q4_K_M is also optimal for the coder: f16 offers zero quality improvement despite halving speed and using 3.5x RAM. [ssm-hybrid-acceleration.md, numa-orchestrator-deployment.md]
- **SpecExec thesis partially refuted on this hardware**: Verification cost scales 4-5x from N=1 to N=64 for Q4_K_M models due to dequantization compute overhead. Only f16 models (no dequant) show near-flat verification (1.69x at N=64). The pure bandwidth-bound regime SpecExec assumes does not hold for quantized CPU inference. [specexec-verification-profile.md]
- **NUMA distribute is dramatically better for single-token processing**: 75-94% faster for large models vs isolate mode. The gap narrows at larger batch sizes. Production should always use --numa distribute for single-instance models. [specexec-verification-profile.md]
- **Model load times scale linearly**: 0.5-1.5B models: 2-5s (acceptable for WARM tier). 7-32B: 10-20s. 80-235B: 30-60s. 480B: 60-90s. Parallel tensor repack on production branch reduces load time by 2.2x. Sequential model loading is mandatory -- concurrent mlock crashes the system. [04-production-server-stack.md]
- **--mlock eliminates 30x cold-start penalty**: Measured in S2 benchmarks. All HOT-tier models now use --mlock (~701 GB locked, 429 GB remaining for KV caches and OS). The host requires unlimited memlock ulimit. [numa-orchestrator-deployment.md]
- **Hyperthreading provides no benefit**: 96 physical cores at -t 96 outperforms 192 threads for compute-bound LLM inference. Hyperthreads add cache contention without meaningful throughput gain. [01-hardware-system.md]
- **Draft model speed varies 4x within same parameter class**: Qwen2.5-Coder-0.5B generates at 185 t/s vs Qwen3.5-0.8B at 44 t/s. Architecture matters more than parameter count for draft models. [specexec-verification-profile.md]
- **192-thread pytest is catastrophic**: Each worker loads its own embedding models (~3 GB), and 192 workers exhaust 1.13 TB RAM. Fixed with lazy model loading in test mode, memory guard at 100 GB minimum free, and blocking pytest -n auto. [02-storage-safety.md]
- **Comprehensive spec param sweep (1,290 measurements) overturned multiple prior assumptions**: Tree speculation helps Q4KM coders (was assumed harmful), hurts 480B MoE (-19%, was assumed beneficial), and registry throughput values were 2.3-3.6x inflated from warm-cache measurements. Never trust single-run benchmarks. [progress/2026-03-21]
- **Prompt lookup (--lookup) segfaults on Qwen3.5 hybrid SSM models** after 1-3 prompts due to prompt cache + recurrent state corruption. moe6-only is stable. Do not use until fixed upstream. [numa-orchestrator-deployment.md]

## Actionable for EPYC

- **Deployed NUMA configuration**: Frontdoor (4x48t quarters, ~50.8 t/s), coder_escalation (4x48t quarters, ~43.3 t/s), architect_general (1x96t node0, 4.3 t/s), architect_coding (1x96t node0, 7.0 t/s), ingest (1x96t node0, ~12 t/s). Total model footprint ~515 GB.
- **Every inference command must use**: `OMP_NUM_THREADS=1`, `taskset -c <cpulist>` for NUMA pinning, `-t 48` or `-t 96` (physical cores only). Missing any of these can halve throughput.
- **Storage safety is non-negotiable**: All LLM files must reside on /mnt/raid0/. Path verification (`[[ "$TARGET_PATH" == /mnt/raid0/* ]]`) before every write. Never enable core dumps (120 GB root SSD). Never use pytest -n auto.
- **Model servers must load sequentially** with 5-second cooldown between large models. Concurrent mlock crashes the system. Vision servers need 90-120s timeout for mmproj + main model.
- **Architect 2-instance opportunity**: Qwen3.5-122B-A10B at 69 GB could run 2x96t for ~2x aggregate if architect throughput bottlenecks. Currently single-instance.
- **Qwen3.5 hybrids are 2-3.6x faster than pure MoE at 122B+ scale** due to recurrent layers avoiding KV cache bandwidth costs. Consider replacing remaining MoE architect roles with hybrids if quality permits.
- **Always sweep before deploying**: The bench_all_spec_sweeps.sh script produces comprehensive verification. Single-run extrapolations have been wrong by up to 3.6x.

## Open Questions

- NUMA node asymmetry (Node 1 at ~85% of Node 0) may be addressable with explicit memory binding or model-loading order changes, but numactl --membind is blocked in the container.
- Transparent Huge Pages (THP) are enabled (`echo always | sudo tee /sys/kernel/mm/transparent_hugepage/enabled`) but their impact has not been isolated in benchmarks.
- CPU paged attention (production-consolidated-v3, patch #7-10) is deployed but RSS impact under NUMA 4-way has not been validated.
- The OMP_NUM_THREADS=1 devcontainer bug (all DFlash server benchmarks invalid due to single-thread OpenMP) suggests environment variable validation should be added to benchmark scripts.
- GPU acceleration path researched (2026-04-14): NVIDIA DGX Spark ($4,699, 128GB unified memory, 273 GB/s, Blackwell GPU) is the primary path. Unified memory eliminates PCIe bottleneck -- expert weights are directly accessible by both CPU and GPU, making `-ot "exps=CPU"` offloading unnecessary. ~70 t/s decode on MoE models from a single chip. Two units linkable via NVLink for 256GB.
- Consumer AMD GPU: RX 7900 XTX ($750-900, 24GB, ROCm stable, ~130 t/s decode 7B Q4) is the best budget option for hybrid MoE offloading. ROCm HIP compatibility with `-ot` tensor overrides is **unconfirmed**.
- CPU+GPU hybrid MoE expert offloading (`-ot "exps=CPU"`, `--n-cpu-moe N`) is production-ready in llama.cpp. PCIe latency is the bottleneck, not CPU compute speed. Two-tier expert cache proposal (#20757) shows 12-14 t/s vs 0.5-1 t/s pure CPU offload -- most impactful pending feature for discrete GPU setups.
- For short-context single-token decode, NUMA 4-way CPU may remain competitive with GPU since decode is memory-bandwidth-bound. GPU most beneficial for prefill (always compute-bound) and long-context decode (attention becomes compute-bound at >50% of per-token time).

## Related Categories

- [Benchmark Methodology](benchmark-methodology.md) -- all benchmark results depend on hardware configuration
- [Speculative Decoding](speculative-decoding.md) -- speculation effectiveness varies dramatically by NUMA config and quantization
- [Inference Serving](inference-serving.md) -- production stack topology built around NUMA optimization
- [MoE Optimization](moe-optimization.md) -- MoE models are the primary beneficiaries of NUMA pinning
- [Local Inference](local-inference.md) -- llama-server launch parameters are hardware-optimized

## Source References

- [Chapter 01: Hardware System](/workspace/docs/infrastructure/01-hardware-system.md) -- EPYC 9655 specifications, runtime optimizations, baseline performance
- [Chapter 02: Storage Architecture & Safety](/workspace/docs/infrastructure/02-storage-safety.md) -- 192-thread pytest danger, HOT/WARM/COLD tiers, root FS crisis
- [Chapter 04: Production Server Stack](/mnt/raid0/llm/epyc-orchestrator/docs/chapters/04-production-server-stack.md) -- Server topology, memory architecture, worker pool, concurrent inference sweep
- [NUMA Orchestrator Deployment](/workspace/handoffs/completed/numa-orchestrator-deployment.md) -- 6-7x NUMA throughput, deployment config, coder quant decision matrix, comprehensive sweep
- [Tree Speculation + NUMA Drafting](/workspace/handoffs/completed/tree-speculation-numa-drafting.md) -- NUMA 4-way results, tree vs linear at 48t, 480B tree+NUMA
- [SSM Hybrid Acceleration](/workspace/handoffs/completed/ssm-hybrid-acceleration.md) -- MoE self-draft results, architecture analysis, Q4_K_M optimality
- [SpecExec Verification Profile](/mnt/raid0/llm/epyc-inference-research/docs/experiments/specexec-verification-profile.md) -- Verification latency curves, NUMA impact on verification, draft model costs
- [Progress 2026-03-18](/workspace/progress/2026-03/2026-03-18.md) -- NUMA parallel decode S2 benchmark, production model sweep, T5/T6 tree+NUMA
- [Progress 2026-03-21](/workspace/progress/2026-03/2026-03-21.md) -- Comprehensive spec param sweep (1,290 measurements), corrected registry values
- [GPU Acceleration Path](/workspace/handoffs/active/gpu-acceleration-path.md) -- DGX Spark analysis, consumer GPU benchmarks, hybrid MoE offloading survey, KV cache split strategies
- [HSD + Hierarchical Self-Speculation](/workspace/handoffs/completed/hsd-hierarchical-self-speculation.md) -- SSM checkpoint overhead analysis, self-speculation failure modes
