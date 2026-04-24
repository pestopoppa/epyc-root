# Hardware Optimization

**Category**: `hardware_optimization`
**Confidence**: verified
**Last compiled**: 2026-04-23
**Sources**: 24 documents

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
- GPU acceleration path researched (2026-04-14, updated 2026-04-15): NVIDIA DGX Spark ($4,699, 128GB unified memory, 273 GB/s, Blackwell GPU) is the primary path. Unified memory eliminates PCIe bottleneck -- expert weights are directly accessible by both CPU and GPU, making `-ot "exps=CPU"` offloading unnecessary. ~70 t/s decode on MoE models from a single chip. Two units linkable via NVLink for 256GB. **vLLM speculation opportunity**: community benchmark shows 91 tok/s on Qwen3.5-27B AWQ with DDTree+Dflash (block diffusion) on GB10 -- GPU parallel scan removes the Delta Net sequential verification bottleneck that killed all CPU speculation approaches. Reproduction plan in gpu-acceleration-path.md.
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
- [GPU Acceleration Path](/workspace/handoffs/active/gpu-acceleration-path.md) -- DGX Spark analysis, consumer GPU benchmarks, hybrid MoE offloading survey, KV cache split strategies; 2026-04-23 adds Lucebox + Hazy megakernel research
- [CPU Shape-Specialized GEMV Decode](/workspace/handoffs/active/cpu-shape-specialized-gemv-decode.md) -- new 2026-04-23 handoff stub for Zen 5 AVX-512 M=1 GEMV microkernel investigation; 4-phase plan with falsification gates
- [Deep Dive: Lucebox Hub](/workspace/research/deep-dives/lucebox-hub-consumer-gpu-dflash.md) -- consumer-RTX-3090 DFlash GGUF port + DeltaNet-hybrid megakernel; resolves intake-158's "no llama.cpp / no GGUF" blocker on GPU side
- [Deep Dive: Hazy Research Megakernel](/workspace/research/deep-dives/hazy-megakernel-llm-inference.md) -- single-dispatch kernel methodology; 78% H100 memory bandwidth vs ~50% for vLLM/SGLang; foundational for any future GPU engine we build

## 2026-04-23 Additions

### CPU throughput levers — post-TIDE deprecation landscape

The TIDE calibration-router early-exit track was deprecated 2026-04-23 (projection quality could not be solved with linear or bottleneck-adapter approaches, after 1.76× speed was confirmed at 50% layers). Remaining CPU throughput levers:

- **Weight-reduction strategies (mature/in-production)**: NUMA 4-way, MoE expert pruning (REAP), AM KV compaction, KV quantization, ngram-simple spec. These are the workhorses.
- **Operator fusion (ruled out empirically)**: Hadamard + unfused `q4_0` beat TurboQuant + fused dequant by 2.2× on our hardware. Upstream llama.cpp has stopped investing in CPU fusion (recent fusion commits all target CUDA/SYCL/WebGPU). Fusion hides compute latency, not memory latency; our workloads are bandwidth-bound (or recurrence-bound for hybrid).
- **Shape-specialized GEMV microkernels (uncharted)**: the one remaining lever. Prior art: llamafile 2.8× on Zen 4, KleidiAI 2.0× decode on Graviton 3. Zen 5's 512-bit AVX-512 datapath (doubled from Zen 4) favors this path. Full investigation handoff at `cpu-shape-specialized-gemv-decode.md`; Phase 0 profiling gate before committing code. Projected 1.5–2.5× end-to-end decode speedup if lever proves out.

### Perf-gap decomposition: Qwen3.6-27B at 4.8 t/s on EPYC 9655

Important clarification to prior benchmarks: **the 25.6 t/s figure in `qwen36-production-upgrade.md` is for Qwen3.6-35B-A3B (MoE, 3B active), not Qwen3.6-27B (dense hybrid)**. The 27B dense baseline is **4.8 t/s** (`progress/2026-04/2026-04-22-kernel-push.md:63`). Dense vs A3B is a ~9× bandwidth-per-token difference because the dense variant touches all 27B params per token while A3B touches only 3B.

Roofline check: Qwen3.6-27B Q8 is 26.6 GB; effective DDR5 BW ~460 GB/s → **17 t/s ceiling** if bandwidth-bound. We're at 4.8 t/s → **28% of roofline**. Compute-bound on DeltaNet sequential recurrence (75% of layers), not bandwidth-limited. Getting to 50% of roofline via ukernel work → 8.5 t/s (1.77×); 80% → 13.6 t/s (2.83×). Anything past 80% requires parallel-scan SSM state, which is GPU-only.

### Megakernel / GPU roofline context

For any future GPU engine: Hazy Research megakernels hit 78% memory bandwidth utilization on H100 (vs ~50% for vLLM/SGLang) via an on-GPU instruction interpreter per SM, shared-memory pagination, counter-based dependency tracking. Lucebox ports this to RTX 3090 + Qwen3.5-0.8B (1.55× vs llama.cpp BF16) and separately ships a DFlash GGUF port for Qwen3.5-27B at 207 tok/s peak / 129.5 t/s mean on HumanEval via llama.cpp fork with tree-mode support. These establish the GPU roofline target (78% MB utilization) for any future engine we build or evaluate.

### Single-instance vs aggregate throughput gap — and the uncharted CPU TP lever

On our EPYC 9655, 4×48t NUMA-pinned instances give **6.7× aggregate throughput** on 30B-A3B (95.8 t/s) vs 1×192t interleaved (14.2 t/s). A single interactive session only sees per-instance speed — **single-session decode is at ~20–50% of what the hardware can physically deliver**. The other 50–80% shows up only as aggregate across independent processes. Cause on a single socket: thread scaling plateaus around 48–64 threads per instance (GGML barrier cost dominates past that); the 12 memory channels are shared as one contention target; per-CCD L3 locality is wasted. Current single-instance 192t measured: 14.2 t/s × 16 GB = ~227 GB/s effective, i.e. ~50% of the 460 GB/s socket ceiling — confirms barrier-bound, not BW-bound.

Two paths to close the gap (both new 2026-04-23 handoffs):

- **Intra-process tensor-parallel decode across CCDs + comm-hiding** (`intra-process-tensor-parallel-decode.md`): shard each matmul column-wise across 12 CCDs, each CCD's threads read their local weight slice from local memory channels, reduction via shared-L3 buffer (240 KB per reduce, effectively free), comm-hiding via next-layer prefetch in the barrier window, per-CCD hierarchical thread pools. Unlike GPU TP, the "communication" is the same shared memory system the compute uses — bandwidth savings come from weight locality (each CCD reading its slice from its local channels), not from avoiding a fabric. **No known CPU prior art with CCD-fabric awareness** — GPU-native design pattern ported to CPU. Projected 2–3.5× single-instance under NPS2, 3.5–5× under NPS4/L3-as-NUMA. Combined with GEMV ukernels (1.5–2.5×), total 5.5× conservative / 12.5× stretch, capped by 460 GB/s BW ceiling.

- **System-level tuning audit** (`single-instance-system-tuning.md`): NPS mode (currently NPS2 — 2 NUMA nodes / 6 channels each; candidates NPS4 or L3-as-NUMA exposing 4 or 12 nodes), THP (currently `madvise`; candidate `always`), explicit 1 GB hugepages (currently 0 allocated), IRQ affinity, per-CCD sync primitive (replaces GGML global barrier), SMT on/off for AVX-512-heavy decode, per-NUMA weight replication for small models under NPS4/L3aaN. Projected 15–40% alone; gating multiplier for TP-sharding's full gain.

### Physical state at 2026-04-23 (baseline for future optimization work)

| Knob | Current |
|------|---------|
| NUMA mode | NPS2 (2 nodes, 6 channels each, distances 10/12) |
| THP | `madvise` |
| Explicit hugepages | 0 allocated |
| Governor | `performance` ✅ |
| SMT | enabled (192 logical threads from 96 cores) |
| NUMA balancing | default (kernel-controlled; AMD recommends explicit off) |
| IRQ affinity | default (not pinned) |
| Free memory | ~318 GB (out of 1.13 TB) |

These become the baseline for CPU3 Phase 0 measurements under the new `cpu-inference-optimization-index.md` backlog.

- [Intra-Process Tensor-Parallel Decode](/workspace/handoffs/active/intra-process-tensor-parallel-decode.md) -- new 2026-04-23, CCD sharding + comm-hiding, projected 2–5× single-instance
- [Single-Instance System Tuning](/workspace/handoffs/active/single-instance-system-tuning.md) -- new 2026-04-23, NPS/THP/hugepages/barrier/IRQ audit, projected 15–40% alone
- [CPU Inference Optimization Index](/workspace/handoffs/active/cpu-inference-optimization-index.md) -- new 2026-04-23, backlog umbrella for all unimplemented CPU throughput techniques (CPU1–CPU14)
- [HSD + Hierarchical Self-Speculation](/workspace/handoffs/completed/hsd-hierarchical-self-speculation.md) -- SSM checkpoint overhead analysis, self-speculation failure modes

## 2026-04-23 late-session measurement update (supersedes projections above)

Phase 0 of the CPU optimization coordinated pickup executed 2026-04-23 with `perf record --call-graph dwarf` (installed via user sudo), on `llama.cpp-experimental` at `cpu-optimization/backlog-2026-04-23` (HEAD `9e048fbc1`). Findings materially revise the earlier-in-this-document projections:

### CPU2 GEMV ukernels — FALSIFIED by measurement

Phase 1 Target #1 implemented: ported `ggml_vec_dot_q8_0_q8_0` from AVX2 (256-bit) to AVX-512VNNI (512-bit) using the existing `mul_sum_i8_pairs_acc_int32x16` helper in `avx512-helpers.h`. Disassembly verified — new binary emits `vpdpbusd %zmm1,%zmm0,%zmm2` + `vpabsb %zmm,%zmm` + `vpmovb2m`; baseline emits `{vex} vpdpbusd %ymm`. Measured on Qwen3.6-27B Q8_0 decode:

- 96t pinned: AVX2 = 4.241 t/s, AVX-512VNNI = 4.313 t/s → **+1.7%** (within noise)
- 1t pinned: AVX2 = 1.020 t/s, AVX-512VNNI = 0.983 t/s → **−3.6%** (port overhead regressed)

Projection was 1.46× end-to-end; measured 1.017× at 96t. **Falsified by factor 30×.** Root cause: the 63.43% perf-sample count in `ggml_vec_dot_q8_0_q8_0` was cycles waiting for DRAM loads inside the inner loop, not ALU-bound compute. Doubling ALU width can't help when the CPU is stalled on memory. Change reverted; `quants.c` is clean. Same pattern observed for tinyBLAS (`GGML_USE_LLAMAFILE` on/off = 0% delta on both Q4_K_M and Q8_0 decode) and BLIS 5.2 (AOCL LD_PRELOAD on/off = 0% delta).

Implication: **compute-focused CPU ukernel work for quantized decode is not the right lever on EPYC 9655.** The earlier projection of 1.5–2.5× end-to-end was based on mis-reading perf samples. Memory-side levers (CPU1 TP-sharding, CPU4 sync primitive, KV compression) are the real opportunities. CPU2 may still help for prefill (M > 1) or batched decode where compute/BW ratio shifts.

### CPU1 TP-sharding Phase 0 — GATE PASSED

Phase 0 feasibility gate criteria from `intra-process-tensor-parallel-decode.md`:

- Gate (a): 192t single-instance <60% of 460 GB/s roofline → measured 18.7 t/s × ~2 GB/token = **8% of roofline**, PASS by huge margin.
- Gate (b): barrier cost >15% of per-token time → measured **32–45%** of cycles in libomp spin/barrier at 96t (`0x0000000000026580` family unresolved in perf), PASS.

Phase 1 prototype is gated GO. 96t single-node / 192t full-machine throughput ratio = **2.63×** (49.11 / 18.7) is the concrete closing target for CCD-local weight sharding.

### CPU4 per-CCD sync primitive — PROMOTED to HIGH standalone

32–45% of decode cycles in OpenMP barrier/spin is a concrete measurement (not speculation). Originally MED / bundled into CPU3 Phase 3; now a standalone HIGH lever. ROI: halving barrier cost → +16% end-to-end on Q8_0, +22% on Q4_K_M.

### CPU3 zero-reboot knobs — within noise on canonical workload

User-applied 2026-04-23 via sudo:
- `kernel.perf_event_paranoid=1` (enables userspace perf profiling in container)
- `kernel.numa_balancing=0` (disable)
- `/sys/kernel/mm/transparent_hugepage/enabled=always`
- `/sys/kernel/mm/transparent_hugepage/defrag=always`
- 1× 1GB hugepage allocated on node 1 (kernel did not honor 40-page request — needs boot param for bulk 1GB allocation)

Re-benched 96t Qwen3-Coder-30B-A3B Q4_K_M across 3 runs after knobs: 46.4 / 46.4 / 48.2 t/s. Pre-knob baseline was 49.1 t/s. Net delta within measurement variance (cold-cache effects dominate). Knobs kept but not materially impactful on this workload. Further CPU3 work (NPS BIOS window, IRQ affinity, per-NUMA weight replication) still pending.

### New single-instance operating point — 96t-ALL-PHYSICAL-CORES (corrected 2026-04-24)

**Correction to 2026-04-23 labeling**: `taskset -c 0-95` is **all 96 physical cores across BOTH nodes (no SMT)**, NOT "full node 0". NUMA map:
- node 0 cpus: `0-47, 96-143` (physical + hyperthreads)
- node 1 cpus: `48-95, 144-191`

The real driver is avoiding hyperthreads — verified 2026-04-24: 96t all-physical (0-95) = 49.3 t/s vs 96t node 0 with HT (0-47,96-143) = 44.6 t/s → **−9.5% penalty from enabling HT**.

**Correction to +26% universal claim**: the 2026-04-23 "+26%" conflated (a) different models, (b) different session page-cache states. Apples-to-apples same-session measurement on Qwen3-Coder-30B-A3B Q4_K_M: 24t (cores 0-23) = 44.32 t/s, 96t all-physical = 49.34 t/s → **+11%**, not +26%. See `research/deep-dives/cpu-96t-production-sweep-2026-04-24.md` for the corrected multi-model matrix.

### Original thread sweep (numbers unchanged, labels corrected)

Systematic thread sweep on Qwen3-Coder-30B-A3B Q4_K_M (canonical baseline model, `-n 64 -r 3`, quiet host):

| Threads | CPU set | t/s (avg) | stddev | Note |
|---|---|---|---|---|
| 24 | taskset 0–23 (node 0 Q0A physical) | 40.76 (2026-04-23) / 44.32 (2026-04-24) | 0.11 / 0.03 | Production worker_explore registry value = 39.1; measured higher today |
| 48 | taskset 0–47 (node 0 physical) | 39.59 / 45.80 | 0.21 / 0.10 | Barrier cost offsets BW gain over 24t |
| **96** | **taskset 0–95 (ALL PHYSICAL, BOTH NODES)** | **49.11 / 49.34** | **0.08 / 0.09** | **Peak** — uses all 12 DDR5 channels, no SMT |
| 96 (HT) | taskset 0-47,96-143 (node 0 phys+HT) | 44.63 (2026-04-24) | 0.04 | **-9.5% vs 96 all-physical** — HT hurts |
| 144 | taskset 0–143 (crosses NUMA unevenly) | 25.74 | 18.50 (bimodal 12.66/38.83) | Cross-NUMA disaster |
| 192 | full machine, `--numa distribute --mlock` | 18.69 | 7.23 (bimodal) | Production registry value = 14.2 |

**Corrected finding (2026-04-24 multi-model sweep)**: 96t-all-physical vs 48t-half-node is **model-dependent**:

| Model | Class | 48t | 96t all-phys | Δ |
|---|---|---|---|---|
| Qwen3-Coder-30B-A3B Q4_K_M | MoE Q4 (3B active) | 45.80 | 49.34 | **+7.7%** |
| Qwen3.6-27B Q4_K_M | Dense hybrid Q4 | 6.67 | **8.97** | **+34.5%** |
| Qwen2.5-Coder-32B Q4_K_M | Dense Q4 | 6.92 | **10.80** | **+56.1%** |
| Qwen3.6-27B Q8_0 | Dense hybrid Q8 | 4.26 | 4.19 | −1.6% |
| Qwen3.6-35B-A3B Q8_0 | MoE Q8 (frontdoor class) | 27.28 | 24.93 | **−8.6%** |

**Dense-Q4 models win big** (1.3-1.6×); MoE Q4 gets small gain; Q8 models flat-or-worse (closer to BW roofline at 48t).

**Concurrent-load sweep** (2026-04-24, SMT-paired splits, `-p 0 -n 32 -r 2`, **N INDEPENDENT llama-bench processes in parallel** — not single-instance TP-sharding): aggregate throughput **monotonically increases** as we split the socket into more concurrent instances.

| Model | 4×48t | 8×24t | 16×12t | 32×6t | **48×4t** | Peak | Δ 4→peak |
|---|---|---|---|---|---|---|---|
| Qwen3.6-27B Q8 (dense hybrid) | 6.62 | 7.91 | 8.55 | 10.47 | **15.39** | 48×4t | **+133%** |
| Qwen3.6-35B-A3B Q8 (frontdoor class) | 64.26 | 76.35 | 85.89 | 92.75 | **135.08** | 48×4t | **+110%** |
| Qwen2.5-Coder-32B Q4 (dense) | 13.64 | 15.08 | 16.01 | **20.03** | 17.34 ↓ | 32×6t | **+47%** |

**Biggest production finding of the session**: switching the orchestrator from **4×48t quarters** (current production) to per-model-optimal splits delivers **+47% to +133%** aggregate throughput with NO code changes. **35B-A3B Q8 at 48×4t hits 135 t/s, ≈100% of the 460 GB/s BW socket roofline** (up from 49% at 4×48t). Per-session throughput at 48-way split is tiny (2.8 t/s per session on 35B-A3B Q8) — this is strictly for concurrent/bulk workloads; single-session latency paths stay on 1×48t/1×96t. Coder-32B Q4 peaks at 32×6t and regresses at 48×4t (per-instance compute too small to saturate BW share).

Hypothesized mechanisms (Phase-0 perf data supports #1 and #2):
1. **Barrier cost is O(threads per instance)**: perf showed 32-45% of cycles in libomp barriers at 96t. Smaller instance barriers (6t vs 48t) are dramatically cheaper. 32 small barriers in parallel beat 4 large ones.
2. **CCD locality**: 6 physical cores ≈ <1 CCD on EPYC 9655 (8 cores/CCD). Smaller instances keep their working set within a single CCD → minimal cross-CCD L3/IOD coherence traffic.
3. **Page cache coherence**: all instances mmap the same GGUF, so weight reads share the page cache. No extra memory pressure from more instances.
4. **BW channel interleaving**: finer-grained instance → finer-grained memory channel contention resolution.

**Single-session crossover**: 1×48t isolated on 35B-A3B Q8 = 27.3 t/s. Split 32×6t aggregate 92.75 / 32 = 2.9 t/s per session. Single-session wins up to ~3 concurrent users; split wins at ≥4 concurrent.

Full corrected analysis: `research/deep-dives/cpu-96t-production-sweep-2026-04-24.md`.

### Memory note on decode-path perf interpretation

Going forward: when `perf report` shows a large overhead percentage inside a quantized-decode inner dot/matmul function on this hardware, treat those samples as **DRAM-wait cycles, not ALU-bound work**, unless separately verified. A cheap A/B test (wider-SIMD port) resolves the question in hours. See `feedback_cpu_decode_bw_bound.md` in auto-memory.

### Session artifacts landed

- `research/deep-dives/cpu-optimization-phase0-baseline.md` — full Phase 0 baseline + thread sweep + per-function perf profile + GGUF metadata for Qwen3.6-27B + revised CPU1/CPU2/CPU4 gate decisions.
- `research/deep-dives/cpu-optimization-cheap-checks-2026-04.md` — tinyBLAS/BLIS/compiler A/B all within noise.
- `progress/2026-04/2026-04-23-cpu-optimization-kickoff.md` — session narrative + step closures.
- `handoffs/active/cpu-inference-optimization-index.md` — pickup-sequence + revised priorities.
- `handoffs/active/cpu-shape-specialized-gemv-decode.md` — deprioritized status + negative-result writeup.
- `handoffs/active/intra-process-tensor-parallel-decode.md` — Phase 0 gate-passed annotation + data.

---

## 2026-04-24 late: Phase 1.4 shipped, fusion track closed, Zen 5 VNNI surprise

Outcome of the CPU optimization sprint's software-level phase on NPS4:

### Current operating point (reproducible)

```
GGML_CCD_POOLS=1 GGML_NUMA_WEIGHTS=1 GGML_CCD_WORK_DIST=1 GGML_BARRIER_LOCAL_BETWEEN_OPS=1 \
  taskset -c 0-47 llama-server -t 48 --flash-attn on --mlock
```

- Single-instance peak (llama-bench, `-n 64 -fa 1 -r 5`): **48.81 ± 0.08 t/s** on Qwen3-Coder-30B-A3B Q4_K_M.
- Layered with production stack (server + spec decode dm=8 + ngram-simple lookup) on code prompts: **58 t/s** (+27% on top of Phase 1.4).
- 4×48t concurrent aggregate: 77.5 t/s (new baseline after CCD-cpuset hang fix).

### Phase 1.4 (shipped)

`acb1bbdd7` — axis-0-aligned partitioning in element-wise ops (ADD, MUL, SCALE, UNARY) + safe CCD-local between-op barrier downgrade. Together with Phase 1.0/1.1/1.2/1.3 (CCD pools, pinning, work-dist, NUMA_WEIGHTS mempolicy interleave), this represents the full exploitation of CCD-locality in a single-instance decode path. Gains: 40 t/s session-start → 48.81 t/s (+22%). Phase 1.4 profile: barrier 43% → 28%, GEMV steady at ~33.5%, other 28% → 38%.

### Op-fusion infrastructure — reverted (no signal)

`b2154f3f3` (infra) + `9ea5b40e8` (Phase 2 graph-construction) briefly shipped with PPL-bit-exact correctness and a repack-path fusion kernel to handle the Q4_K_M repacked-weight path. Throughput gain on MUL_MAT+ADD fusion: **within ±0.4% noise in both fa=0 and fa=1 modes**. Why it didn't matter: the fused ADD is a tiny 2048-float tensor; the barrier it saves is ~0.5% of per-layer cost; and attention-internal fusion (the other potential target) is already fully handled by `ggml_flash_attn_ext` (single graph op covers Q@K + softmax + V@KQ). With no remaining leverage target, keeping fusion infra meant pure technical debt. Reverted as `c34aac61b` + `138b26cd4`.

**Takeaway**: on models where flash attention is enabled (which is all our production MoE workloads), there is no CPU-general op-fusion lever left to pull. Future fusion work only makes sense if (a) attention is NOT using flash attn for some reason, or (b) we discover a specific multi-op sequence with disproportionately large barrier cost that the Phase 1.4 local-barrier downgrade can't already catch.

### Q4_K GEMV VNNI probe — net-negative on Zen 5 (NOT committed)

Profile showed 33.5% of decode cycles in `ggml_gemv_q4_K_8x8_q8_K` (AVX2 kernel using `_mm256_maddubs_epi16` + `_mm256_madd_epi16`). Straightforward AVX-512VNNI port: replace the 8× `maddubs_epi16` + 7× `add_epi16` + 1× `madd_epi16` chain with 8× `_mm256_dpbusd_epi32` + 1× `_mm256_mullo_epi32`. PPL bit-exact with baseline (10.9882), so correctness holds. Throughput: **tg64 48.81 → 48.18 t/s** (slight regression outside of baseline's tight stddev).

**Root cause — Zen 5 instruction throughput asymmetry**:
- `VPMADDUBSW` 256-bit: **2 ops/cycle**
- `VPDPBUSD` 256-bit or 512-bit: **1 op/cycle**
- `VPMULLD` 256-bit: 1 op/cycle, 3-cycle latency

Total cycle count:
- AVX2 path: 16 ops / 2 per cycle = **8 cycles/sub-block**
- VNNI path: 9 ops / 1 per cycle = **9 cycles/sub-block**

The existing AVX2 kernel is actually **better-matched to Zen 5's pipeline** than a VNNI replacement, even though it's nominally more instructions. This contradicts the common assumption that VPDPBUSD always beats maddubs+add+madd — on Zen 5 specifically, maddubs has 2× the throughput of VNNI for this kernel shape. The same negative conclusion now holds for both Q4_K_M (compute-bound candidate, this probe) and Q8_0 (BW-bound, 2026-04-23 probe). Not committed; stash dropped.

**Actionable**: do not port other quantized GEMV kernels (Q5_K, Q6_K, Q2_K, etc.) to VNNI on Zen 5 without a measured A/B. The speed assumption flips on different CPUs (Zen 4, Intel Sapphire Rapids have VNNI-favorable throughput ratios). Revisit if/when we acquire Zen 6 or a different server class.

### llama-bench `-fa` default gotcha

`llama-bench` defaults to `-fa 0` (flash attention OFF) while `llama-perplexity` uses `-fa auto` (which enables it). This is a ~8–10% swing on CPU decode throughput and caused a false "regression" scare this sprint. **Always pass `-fa 1` explicitly when benchmarking decode**. Production `llama-server` uses `--flash-attn on` in the standard stack — that corresponds to `-fa 1` in llama-bench.

### Production-stack composability verified

Before committing to the L3-as-NUMA reboot, layered the production-stack accelerations on top of the Phase 1.4 experimental kernel via `llama-server` + curl (prompt: Python linked-list scaffold, 170 prompt tokens / 256 generated):

| Model | Config | tg (t/s) |
|---|---|---|
| Qwen3-Coder-30B-A3B Q4_K_M | base | 45.63 |
| Qwen3-Coder-30B-A3B Q4_K_M | + spec (dm=8) | **55.47** (+22%) |
| Qwen3-Coder-30B-A3B Q4_K_M | + spec + ngram-simple | **58.01** (+27%) |
| Qwen3.5-35B-A3B Q4_K_M (hybrid) | base | 31.25 |
| Qwen3.5-35B-A3B Q4_K_M (hybrid) | + moe6 + q4_0 KV | 32.61 |
| Qwen3.5-27B Q4_K_M (dense hybrid) | base | 7.56 |
| Qwen3.6-27B Q4_K_M (dense hybrid) | base | 7.14 |

All production accelerations compose cleanly with the experimental kernel — no regressions.

### Decision gate: L3-as-NUMA BIOS reboot is next

Every software-level lever on NPS4 has been exercised or ruled out. The 48.81 t/s single-instance peak (Qwen3-Coder-30B-A3B Q4_K_M) represents the ceiling of non-BIOS optimizations. L3aaN would expose **12 NUMA domains (one per CCD)** rather than NPS4's 4, enabling genuine per-CCD weight locality via per-CCD replicas. Expected gain from L3aaN: +10–20% on decode, contingent on whether the 12-domain layout delivers CCD-local reads where the 4-domain NPS4 currently forces cross-channel traffic for most accesses.

### Q4 vs Q8 throughput on the experimental kernel (2026-04-24)

Same stack, code-completion prompt, via llama-server + curl:

| Model | Quant | Config | tg (t/s) |
|---|---|---|---|
| Qwen3-Coder-30B-A3B | Q4_K_M | base | 45.63 |
| Qwen3-Coder-30B-A3B | Q4_K_M | + spec (dm=8) + ngram | 58.01 |
| Qwen3.5-35B-A3B | Q4_K_M | base | 31.25 |
| Qwen3.5-35B-A3B | Q4_K_M | + moe6 + q4_0 KV | 32.61 |
| Qwen3.5-35B-A3B (abliterated proxy) | Q8_0 | base | 22.20 |
| Qwen3.5-35B-A3B (abliterated proxy) | Q8_0 | + moe6 + q4_0 KV | 24.83 |
| Qwen3.6-35B-A3B | Q8_0 | base | 22.29 |
| Qwen3.6-27B (dense hybrid) | Q4_K_M | base | 7.14 |
| Qwen3.6-27B (dense hybrid) | Q8_0 | base | 4.36 |

Q4→Q8 ratios: **0.71 on 35B-A3B hybrid** (SSM compute partially amortizes the BW doubling), **0.61 on 27B dense hybrid** (closer to the pure BW ratio since dense weights dominate). MoE expert reduction (moe6 + q4_0 KV) scales with Q4 and Q8: +4% on Q4, +12% on Q8 — the expert-reduction gain grows when BW cost per expert is larger. No Q8-specific kernel bugs observed.

### x86 K-quant + Q8_0 repack dispatcher gaps (2026-04-24)

`ggml/src/ggml-cpu/repack.cpp:ggml_repack_get_optimal_repack_type` has NEON-only dispatch branches for `GGML_TYPE_Q5_K`, `GGML_TYPE_Q6_K`, and `GGML_TYPE_Q8_0`. On x86 these types fall through to `nullptr` → tensors remain in the non-repacked layout and run the single-row `ggml_vec_dot_*` kernels from `arch/x86/quants.c`.

Profile consequences on Qwen3.6-27B (dense hybrid) decode:
- Q4_K_M quant: 49.3% cycles in `ggml_gemv_q4_K_8x8_q8_K` (repacked AVX2, fast), **18.2% in `ggml_vec_dot_q6_K_q8_K` (non-repacked)**, 4.6% in `ggml_vec_dot_q5_K_q8_K` (non-repacked). Unsloth's imatrix Q4_K_M aggressively uses Q6_K for `attn_qkv.weight` and `ffn_down.weight` — the biggest non-expert tensors per layer.
- Q8_0 quant: **77.4% cycles in `ggml_vec_dot_q8_0_q8_0` (non-repacked single-row)**. All Q8 workloads are throttled by this single-row kernel.

Gradient test on 2026-04-24 — flipping the dispatcher to use the existing `*_generic` C implementations for Q5_K/Q6_K produced **−66% to −71% regression** (generic kernels are scalar C with triple-nested loops; they don't auto-vectorize well enough to match the hand-tuned AVX2 `vec_dot_*`). For Q8_0 the generic 4x8 kernel is **neutral** (no sub-block scales → simpler, auto-vectorizes to AVX2-equivalent).

Conclusion: the plumbing is sound but the kernel side is missing. Writing hand-optimized AVX-512BW 8x8 repacked GEMV kernels for Q8_0 (biggest win: 77% cycle share, simplest kernel) and Q6_K (18% on Q4_K_M dense, more complex due to 4+2 bit unpack) is the next real software-level lever after L3aaN. Use AVX-512BW width (`_mm512_maddubs_epi16` + `_mm512_madd_epi16`) — NOT VPDPBUSD — because Zen 5's maddubs has 2/cycle throughput vs VNNI's 1/cycle. Expected gain: +40-70% on Q8 decode, +7-10% on Q4_K_M dense.

Effort: 4-6 hours per kernel. Deferred pending L3aaN reboot (higher ROI, zero code risk).
