# CPU Shape-Specialized GEMV Microkernel for Zen 5 Decode

**Status**: stub (investigation not started)
**Created**: 2026-04-23 (via session discussion of CPU fusion viability)
**Priority**: MEDIUM — speculative lever, but one of few remaining uncharted CPU throughput paths post-TIDE deprecation
**Categories**: hardware_optimization, inference_serving, local_inference
**Workstream**: Inference Acceleration
**Parent index**: [`inference-acceleration-index.md`](inference-acceleration-index.md)
**Related**:
- [`llama-cpp-kernel-push-rebase.md`](llama-cpp-kernel-push-rebase.md) — current kernel-level work on the fork
- [`attention-matching-kv-compaction.md`](attention-matching-kv-compaction.md) — orthogonal throughput lever (KV-side)
- [`gpu-acceleration-path.md`](gpu-acceleration-path.md) — where TensileLite shape-specialization discussion originated
- [`llama-cpp-v3-upstream-rebuild.md`](../completed/llama-cpp-v3-upstream-rebuild.md) — paged attention / OpenMP repack / MoE expert reduction context

## Status as of 2026-04-23

**Investigation not started. This handoff documents the rationale, prior art, and work plan for a future pickup.**

Motivation: after the TIDE calibration-router early-exit track was deprecated 2026-04-23 (projection quality could not be solved with either linear or bottleneck-adapter approaches), the set of remaining CPU throughput levers is narrow. Weight-reduction strategies (MoE expert pruning, AM KV compaction, KV quantization, ngram-simple spec) are mature or in production. Operator-level fusion was found not viable on CPU (Hadamard + unfused `q4_0` beat TurboQuant + fused by 2.2×; see `kv-cache-quantization.md` and session discussion 2026-04-23). The one significant unexplored CPU lever remaining is **shape-specialized GEMV microkernels for the M=1 decode regime** on the EPYC 9655's AVX-512 datapath.

This handoff is a research/implementation stub. No work has been started. The expected effort is medium (hundreds of lines of templated C++ intrinsics, no assembly), the expected gain is 1.5–2.5× decode throughput on our production models based on prior-art extrapolation, and the payoff scenario is significant — 1.5–2× on Qwen3.6-27B (4.8 t/s → 7–10 t/s) and multiplicative composition with existing gains (NUMA 4-way, ngram spec, KV compaction).

## Objective

Implement shape-specialized AVX-512 microkernels for the matmul operations that dominate single-user decode (M=1) on our production model stack. The target is to replace the generic ggml CPU GEMM fallback with hand-tuned kernels whose dimensions (K, N) are fixed at compile time, whose register blocking is tuned for Zen 5's 512-bit datapath + VDPBF16PS + VNNI throughput, and whose dequant-from-`q4_K_m` (or `q8_0`) stage is fused into the matmul inner loop.

Concretely: prove or disprove that 1.5–2.5× decode speedup is achievable on Qwen3.6-27B Q8_0 using this approach. If proven, roll out to the other production models (Qwen3.6-35B-A3B MoE, Qwen3-Coder-30B-A3B, Qwen3-Coder-480B, SG4, M2.7). If disproven, archive the handoff with the specific measurements that show why the lever is dry on this hardware.

## Why This Is a Credible Lever (and What Would Falsify It)

### The case for

**Prior art on adjacent hardware achieves 2–3× on the same workload.**

| System | Hardware | Workload | Speedup | Technique |
|--------|---------|---------|---------|-----------|
| Justine Tunney / tinyBLAS (llamafile) | Zen 4 (Threadripper PRO) | LLM prefill+decode | 2.8× overall; 10× prefill; decode fraction not broken out | Templated C++ with compiler intrinsics; per-dtype specialization (BF16/FP16/FP32/Q8_0); iterative disassembly-driven tuning |
| ARM KleidiAI | Graviton 3 (Neoverse V1) | LLaMA-3-8B 4-bit decode | **2.0× decode**, 3× prefill; 45.5 tok/s batch=1 | Specialized GEMV + GEMM; per-group fine-grained codebook with register-resident codebooks; weight-column reuse |
| Intel oneDNN | Xeon AVX-512 | Generic GEMM | 1.0–1.5× | Runtime shape dispatch + 5-loop blocking; M=1 not primary target |
| Microsoft MLAS (ONNXRuntime) | x86 AVX-512 VNNI | Generic GEMM | 1.0–1.3× | Shape-dispatched kernel pool |

The two directly-relevant data points are llamafile on Zen 4 (same CPU family as our Zen 5, 2.8× overall) and KleidiAI on Graviton 3 (direct M=1 decode measurement, 2.0×). Both use a similar pattern: template the ukernel on (K, N, dtype), keep weights in packed column-major cache-friendly layout, fuse dequant into the inner product, register-block the output tile.

**Zen 5 has architectural improvements over Zen 4 that favor this lever.** Zen 5 / Turin has a **full 512-bit AVX-512 datapath** (Zen 4 was a 256-bit datapath executing AVX-512 in 2 cycles). This doubles peak AVX-512 throughput per core. Zen 5 also has native VDPBF16PS (AVX-512 BF16 dot-product) and VNNI (AVX-512 VNNI for int8 dot-products). Every llamafile result from Zen 4 is a lower bound for what should be achievable on Zen 5.

**ggml has no M=1 ukernel specialization for Zen 5 today.** The current CPU path (confirmed by inspection of `/mnt/raid0/llm/llama.cpp/ggml/src/ggml-cpu/`):
- AMX path exists but is Intel-only (Sapphire Rapids+), inapplicable to Zen 5.
- AVX-512 VNNI path has M=1 fast path in `mmq.cpp:2436–2463` using templated `tinygemm_kernel_vnni<BLOCK_M, BLOCK_N>` with NB ∈ {32, 64, 96, 128}, but this is int8 × int4 multi-tile prefill-style code; not a true M=1 GEMV ukernel.
- TILE constants in `amx/common.h:16–18` (TILE_M=16, TILE_N=16, TILE_K=32) are hardcoded and not model-aware.
- Dispatch via runtime switch on `(MB_SIZE << 4 | NB_SIZE)` — pays dispatch cost on every decode step.

There is no shape-specialized single-row GEMV ukernel for Zen 5 in upstream ggml. Nor is there vendor work (ZenDNN 5.2 targets Zen generally via "Low Overhead API" and "pattern-aware kernel selection," but no published M=1 GEMV ukernel).

**No fundamental blocker identified.** Zen 5's core throughput, memory hierarchy (32 KB L1D, 1 MB L2 per core, ~384 MB L3 total on 9655), and 12-channel DDR5-6000 are all compatible with the register-blocked GEMV pattern that KleidiAI and llamafile use.

### The case against (and how to falsify the lever)

**1. Decode is memory-bandwidth bound, not compute bound, on large models.** If this is the dominant constraint, ukernel tuning can only close the gap between current utilization and roofline. For Qwen3.6-27B Q8 (26.6 GB model / 460 GB/s effective BW = 17 t/s roofline), we're at 4.8 t/s → 28% of roofline. Getting to 50% of roofline via ukernel work → 8.5 t/s, i.e., 1.77×. Getting to 80% → 13.6 t/s, i.e., 2.83×. That's the upper-bound envelope. Exceeding 80% of roofline with a CPU ukernel is implausible.

**2. DeltaNet sequential recurrence caps the effective compute.** Our hybrid models have ~75% DeltaNet linear-attention layers; each requires a sequential state update per token. If the recurrence update time dominates, ukernel speedup on the other 25% (full attention + MLP) is diluted. Falsification test: profile decode on a single token and measure the time fraction in DeltaNet recurrence. If >60%, the ceiling is lower than the roofline calc suggests.

**3. Dequant overhead from Q4_K_M may be inherent.** Q4_K_M's block structure (32 weights per block, 6-bit superblock scales) requires gather/broadcast operations in the inner loop. If the dequant can't be fused efficiently into the AVX-512 FMA, the ukernel may lose to `q8_0` unfused — same lesson as TurboQuant vs Hadamard. Falsification test: measure a `q8_0` ukernel first (simpler path), then try `Q4_K_M`, and compare.

**4. Zen 5 AVX-512 thermal downclocking.** If heavy AVX-512 code triggers non-trivial frequency drops on our specific CPU under sustained load, ukernel gains get clawed back. Zen 5 reportedly does not have the Skylake-X-era AVX-512 downclock penalty, but this needs to be verified on our hardware at our thermal profile (EPYC 9655 in our chassis with our cooling).

**5. Ukernel maintenance burden.** If each new model (Qwen3.7, Qwen4, etc.) requires hand-written ukernels for its specific shapes, this becomes a treadmill. Mitigation: template on (K, N) as non-type template parameters; ship a registry of ukernels for the ~dozen shapes we actually use; document the code-gen pattern so regenerating for a new model is a `sed` exercise, not a research project.

**Falsification conditions (abandon this lever if any hold after Phase 1):**
- End-to-end decode speedup on Qwen3.6-27B Q8 < 1.3× vs baseline.
- Profiling shows DeltaNet recurrence > 70% of decode time (ukernel can't help there).
- Q4_K_M ukernel is slower than a plain q8_0 ukernel despite the BW savings (dequant-into-FMA fusion doesn't amortize on Zen 5).
- Thermal downclocking costs > 15% of peak throughput under sustained load.

## Technical Background

### Decode shapes for our production models

Decode at batch=1 is a sequence of GEMV operations (matrix × vector), not GEMM. The shapes depend on the model's hidden size, head count/dim, MLP intermediate size, and (for MoE) expert size.

**Qwen3.6-27B (dense hybrid, 64 layers):**
| Op | Shape (K → N) | Per-token calls | Notes |
|---|---|---|---|
| Attention QKV projection | 5120 → ~6400 (GQA: Q=5120, K=640, V=640 with 14Q/2KV heads) | 64 (1 per layer) | For the ~25% full-attention layers; DeltaNet layers have different shapes |
| Attention output projection | 5120 → 5120 | 64 | |
| MLP up | 5120 → 27648 | 64 | Largest shape |
| MLP gate | 5120 → 27648 | 64 | Largest shape (pair with up) |
| MLP down | 27648 → 5120 | 64 | |
| DeltaNet QKV+state | model-specific | 48 (75% of layers) | Requires separate analysis; state-update shape differs from standard matmul |

Total: ~5 distinct non-DeltaNet shapes, each called 64 times per token. Specialize each → ukernel count ≈ 5 × quant_types (Q4_K_M, Q8_0) = 10 ukernels for this model.

**Qwen3.5/3.6-35B-A3B (hybrid MoE, 3B active):**
| Op | Shape (K → N) | Per-token calls |
|---|---|---|
| Attention QKV (~25% of layers) | ~4096 → smaller GQA | ~layer_count × 0.25 |
| Attention output | ~4096 → 4096 | ~layer_count × 0.25 |
| Expert up (per active expert) | ~4096 → ~1408 (smaller than dense) | 8 experts × ~layer_count |
| Expert gate | ~4096 → ~1408 | 8 × ~layer_count |
| Expert down | ~1408 → 4096 | 8 × ~layer_count |

MoE shapes are smaller (intermediate dim ~1408 per expert) but there are many more matmul calls per token. The shape-specialization approach still applies; the shapes to specialize on are different.

**Qwen3-Coder-30B-A3B:** similar to 35B-A3B but different dims. Separate ukernel set needed.

**Rough ukernel count to cover production stack:** 5 shapes per model × 5 models × 2 quants = **~50 specialized ukernels**. This is the maintenance-surface upper bound.

### Why shape-specialization wins (when it wins)

A generic GEMM inner loop pays for:
1. **Loop-bound checks** at every iteration (modern CPUs mostly hide these, but not fully).
2. **Indirect addressing** for strided access patterns that the compiler can't prove are contiguous.
3. **Register under-utilization**: a generic kernel picks blocking constants conservatively for arbitrary (M, N, K). A specialized kernel picks constants tuned for the exact shape.
4. **Dispatch overhead** at the matmul-call level (the `(MB_SIZE << 4 | NB_SIZE)` switch in `mmq.cpp`).
5. **Dequant redundancy**: if dequant is done as a separate pass producing an FP16/FP32 buffer, the buffer is written to DRAM and then re-read; a fused ukernel avoids the round-trip.

A shape-specialized ukernel with compile-time constants lets the compiler:
- **Fully unroll** the inner loop (N and K known at compile time).
- **Pre-compute register pressure** (output tile sized for exactly the available AVX-512 registers, 32 ZMM regs on Zen 5).
- **Pipeline dequant into FMA**: load packed weights, unpack to BF16 via VDPBF16PS, multiply-accumulate with the activation broadcast, discard — no intermediate buffer.
- **Eliminate branches** on block boundaries when K is a known multiple of the tile.

The technique is bog-standard HPC — there's nothing novel about it. The novelty in LLM-inference context is specifically **having a small enough shape catalog (~50 ukernels) that hand-specializing them is cheaper than the generic path's overhead**. Justine Tunney's llamafile and ARM KleidiAI both demonstrated this catalog is small enough in practice.

### Register blocking target for Zen 5

Zen 5 per core:
- 32 × 512-bit ZMM registers (`zmm0`–`zmm31`), full 512-bit datapath (unlike Zen 4's 2-cycle issue)
- 2× FMA units capable of 2× AVX-512 FMAs per cycle (peak 16 FLOPs/cycle FP32, 32 FLOPs/cycle BF16 via VDPBF16PS, 128 ops/cycle int8 via VNNI)
- L1D: 32 KB, 48-cycle hit latency, 2 loads + 1 store per cycle
- L2: 1 MB per core, ~14-cycle hit
- L3: ~384 MB total on 9655 (shared across CCDs)

Plausible register blocking for a Q8_0 GEMV ukernel:
- Output tile: 1×8 (M=1, N=8 FP32 accumulators in 8 ZMM regs — but wait, ZMM is 16×FP32, so 1×16 is more natural; use 1×32 with two ZMM per output column)
- Weight prefetch: 4 K-block lookahead into L1 via software prefetch
- Activation: broadcast single FP32 into ZMM, reused across output tile
- Inner loop: load 16 weights → VDPBF16PS with activation → accumulate; unroll K loop 4×

The exact constants need measurement; these are starting points.

### Dequant-in-matmul fusion for Q4_K_M

Q4_K_M layout (per block of 32 weights):
- 16 bytes of 4-bit weights (128 nibbles → 32 weight pairs)
- 1 byte super-scale factor (6-bit format with 2-bit correction)
- Plus block-level shared scale

A fused ukernel:
1. Load 16 bytes of quantized weights (4-bit packed).
2. Unpack to int8 (32 weights per ZMM) via shift+mask — 2 instructions.
3. Multiply by scale (broadcast from block header) — 1 VPMULLD.
4. Convert int8 → BF16 — 1 VCVTQQ2PS (or similar).
5. Dot-product with activation via VDPBF16PS.

Total per 32-weight block: ~6 instructions of dequant + 1 FMA. Compare to the generic dequant-to-buffer path, which writes 32 FP32 values (128 bytes) to DRAM then re-reads them, blowing L1 cache on large matrices.

## Prior Art — Detailed

### 1. Justine Tunney's llamafile / tinyBLAS

- **Hardware tested**: Zen 4 (Threadripper PRO 7995WX), Intel Alder Lake, ARM v8.2+.
- **Overall result**: 2.8× end-to-end on Zen 4; 10× prefill (485 → 557 tok/s on Mistral 7B BF16 is cited, but the 10× is a different workload — verify specific number before citing).
- **Technique**: C++ with compiler intrinsics (not hand-written assembly); per-dtype template specialization for BF16, FP16, FP32, Q8_0; iterative tuning driven by disassembly inspection to confirm the compiler was emitting the intended instructions.
- **Catalog size**: 84 ukernels shipped across platforms as of llamafile 0.7.
- **Maintenance**: Entirely C++; no assembly. Shipped in llamafile 0.7+, integrated into some ggml builds.
- **Primary source**: [justine.lol/matmul/](https://justine.lol/matmul/) — required reading before starting this work.
- **Integration question for us**: Can we pull tinyBLAS into our llama.cpp fork, or is it license-incompatible / too intrusive? Needs checking.

### 2. ARM KleidiAI

- **Hardware**: ARM Neoverse (Graviton 3/4).
- **Decode speedup**: 2.0× on LLaMA-3-8B 4-bit decode, reaching 45.5 tok/s at batch=1 on Graviton 3.
- **Technique**: Shape-specialized GEMV + GEMM, distinct paths; per-group fine-grained codebook quantization with **codebooks resident in the register file**; weight-column reuse during GEMV to amortize activation-vector loads.
- **Data types**: 4-bit weights, 8-bit activations.
- **Effort**: Medium-high; requires ARM ISA expertise (DOT product, SME2).
- **Primary source**: [Gope et al., arXiv:2501.00032](https://arxiv.org/abs/2501.00032) — most directly relevant paper for our setup. Required reading.
- **Integration**: KleidiAI is integrated into llama.cpp upstream via a plugin with separate GEMV/GEMM dispatchers (ARM only). The x86 analog is what this handoff proposes.

### 3. Intel oneDNN / MKL

- **Hardware**: Intel AVX-512 Xeon; some Zen support via AOCC.
- **M=1 speedup**: Not quantified as a primary benchmark (oneDNN is general-purpose). Experimentally 1.0–1.5× over vanilla BLAS, shape-dependent.
- **Technique**: Runtime shape dispatch + cache-aware 5-loop blocking; tiles specialized at op-creation time (not every call).
- **Relevance**: Proves the general design pattern scales, but oneDNN is a large dependency and not llama.cpp-native.

### 4. Microsoft MLAS (ONNXRuntime CPU EP)

- **Hardware**: Multi-platform (ARM NEON, x86 AVX/AVX2/AVX-512 VNNI, WebAssembly).
- **Technique**: Kernel pool with platform dispatch; BFMMLA/SMMLA for int8.
- **Relevance**: Similar to oneDNN — proves the pattern, provides code-gen reference, but too heavy as a direct dependency.

### 5. Current ggml (baseline)

- `mmq.cpp:2436–2463`: `tinygemm_kernel_vnni<BLOCK_M, BLOCK_N>` with NB ∈ {32, 64, 96, 128} — templated on block size but not model-specific shapes.
- AMX path: Intel-only (16×16×32 tiles), inapplicable.
- No decode-specific (M=1) optimization in the AVX-512 codepath.

## Hardware Context: EPYC 9655 / Zen 5 Turin

- **Cores**: 96 (192 threads with SMT).
- **ISA**: AVX-512F, AVX-512BW, AVX-512DQ, AVX-512VNNI, AVX-512BF16 (VDPBF16PS), AVX-512VBMI, AVX-512VPOPCNTDQ.
- **AVX-512 datapath**: **Full 512-bit** (vs Zen 4's 256-bit executing AVX-512 over 2 cycles). 2× peak throughput per core over Zen 4.
- **FMA units**: 2 per core (AVX-512 capable).
- **Registers**: 32 × ZMM (512-bit).
- **No AMX**: Intel-only ISA; irrelevant.
- **Cache**: 32 KB L1D, 1 MB L2 per core, ~384 MB L3 shared across 12 CCDs (wave-level cache split matters for NUMA).
- **Memory**: 12-channel DDR5-6000 per socket; aggregate ~460 GB/s effective per NUMA node on llama.cpp decode workloads (not the theoretical 576 GB/s peak).
- **Thermal**: Zen 5 reportedly does not have significant AVX-512 downclocking under sustained load (unlike Skylake-X generation). Needs verification on our chassis.

Relevant compiler flags (GCC/Clang): `-mavx512f -mavx512bf16 -mavx512vnni -mavx512vbmi -mtune=znver5`.

## Phased Work Plan

### Phase 0: Feasibility — read prior art & profile baseline (1–2 days)

**Goal:** confirm the lever is worth pursuing before writing any code.

- [ ] Read [justine.lol/matmul](https://justine.lol/matmul/) end-to-end. Extract the exact Zen 4 ukernel pattern for Q8_0.
- [ ] Read [Gope et al., arXiv:2501.00032](https://arxiv.org/abs/2501.00032). Extract the GEMV register-blocking and codebook-resident technique.
- [ ] Profile a baseline Qwen3.6-27B Q8_0 decode with `perf stat -e cycles,instructions,cache-references,cache-misses,dTLB-load-misses,l2_rqsts.demand_data_rd_hit`. Also run `perf record -g` and flamegraph the hot functions.
- [ ] Measure: (a) time in matmul ops vs time in DeltaNet recurrence vs time in RMSNorm/RoPE/sampling. (b) IPC and L1/L2 hit rates in the matmul functions. (c) fraction of decode time in `ggml_compute_forward_mul_mat` and its callees.
- [ ] **Gate**: if >60% of decode time is in DeltaNet recurrence (not matmul), abandon and document why. Otherwise proceed.

**Artifacts:** a short markdown writeup (`research/deep-dives/cpu-gemv-feasibility-baseline.md`) with the profiling numbers and the gate decision.

### Phase 1: Single-shape prototype — prove the lever (3–5 days)

**Goal:** implement **one** ukernel for **one** shape on **one** model and measure end-to-end speedup.

Target: **Qwen3.6-27B Q8_0 MLP-up matmul**, shape K=5120 → N=27648.

- [ ] Write a standalone benchmark harness that calls just this matmul (not the full model), with the same activation layout ggml uses. Measure baseline perf.
- [ ] Implement the ukernel as a single C++ file with compile-time template parameters `<K, N>`. Use AVX-512 + VDPBF16PS intrinsics. Register-block the output tile (1×32 or 1×16 — measure both).
- [ ] Validate numerical equivalence: bit-exact comparison with ggml reference on 1000 random inputs, then cosine similarity on the full layer on real activations.
- [ ] Integrate via a custom ggml op override, conditionally enabled with an env var like `EPYC_UKERNEL_MLP_UP=1`.
- [ ] Run full decode with the env var on/off; compare tok/s on Qwen3.6-27B Q8_0, 192 threads single instance.
- [ ] **Gate**: if end-to-end speedup is ≥1.15× from this single ukernel (representing ~1/5 of matmul ops per token), extrapolate to full coverage and proceed. If <1.10×, abandon.

**Artifacts:** the ukernel source, the benchmark data, and a decision writeup.

### Phase 2: Full Qwen3.6-27B coverage — prove end-to-end gain (1–2 weeks)

**Goal:** cover all matmul shapes on Qwen3.6-27B for both Q8_0 and Q4_K_M, measure end-to-end decode speedup.

- [ ] Write ukernels for the remaining 4 shapes on Qwen3.6-27B (Q/K/V projections, attention output, MLP gate, MLP down).
- [ ] Write the Q4_K_M variant of each (dequant-into-FMA fusion). Compare per-shape against Q8_0 ukernel perf.
- [ ] Integrate via a shape-dispatch table keyed on (K, N, quant_type) + model ID. Fall back to ggml default for unmatched shapes.
- [ ] Benchmark end-to-end decode with full coverage vs baseline. Target: 1.5×.
- [ ] Run correctness battery: PPL delta on WikiText-2, full MMLU subset, SWE-bench-verified mini-subset (the usual coder-correctness suite).
- [ ] Verify no thermal downclocking regression under sustained load (ensemble benchmark ≥30 min continuous).
- [ ] Verify NUMA interaction: run under production NUMA 4-way config and confirm aggregate throughput also scales.
- [ ] **Gate**: if end-to-end decode ≥1.5× AND correctness within tolerance (PPL Δ < 0.01, MMLU Δ < 1 pt, thermal loss <5%), proceed to Phase 3. Otherwise decide: partial rollout vs abandon.

**Artifacts:** full ukernel set for Qwen3.6-27B; benchmark report; correctness battery results.

### Phase 3: Rollout to production stack (2–3 weeks)

**Goal:** cover all production models.

- [ ] Write ukernels for Qwen3.5/3.6-35B-A3B (MoE variant; different shapes, same pattern).
- [ ] Write ukernels for Qwen3-Coder-30B-A3B.
- [ ] Write ukernels for Qwen3-Coder-480B (large target, may gate by storage; verify ROI first).
- [ ] Write ukernels for SG4 and M2.7 if in production.
- [ ] Integrate into `production-consolidated-v4` branch of our fork.
- [ ] Update `orchestrator_stack.py` if any quant-format changes needed.
- [ ] Full regression sweep across all production models.
- [ ] Document the ukernel catalog and code-gen pattern for future model additions.

**Artifacts:** merged fork branch; updated orchestrator config; documentation of how to add ukernels for a new model.

### Phase 4 (optional): Contribute upstream

**Goal:** if the wins are real, push the work upstream to llama.cpp / ggml so it doesn't rot on our fork.

- [ ] Open discussion on [ggml-org/llama.cpp discussions](https://github.com/ggml-org/llama.cpp/discussions) with our benchmark data.
- [ ] PR the ukernel infrastructure (registry + dispatch) independent of model-specific shapes.
- [ ] PR model-specific shape kernels as a separate body of work.
- [ ] Coordinate with Justine Tunney / tinyBLAS if her work is upstream-blocked.

**Why bother:** avoids a long-term fork divergence, and the community benefits from Zen 5 attention.

## Benchmark Plan

### Baseline establishment (pre-work)

Run these on `production-consolidated-v4` (current fork tip) before starting any ukernel work:

```bash
# Single-user decode baseline, Qwen3.6-27B Q8_0, 192 threads, single instance
./llama-bench -m Qwen3.6-27B-Q8_0.gguf -t 192 -p 0 -n 256 -b 1 \
  --numa isolate --mlock \
  -r 5 -o json > baseline-27b-q8.json

# Same for Q4_K_M
./llama-bench -m Qwen3.6-27B-Q4_K_M.gguf -t 192 -p 0 -n 256 -b 1 \
  --numa isolate --mlock \
  -r 5 -o json > baseline-27b-q4.json

# Same for Qwen3.6-35B-A3B Q8_0
./llama-bench -m Qwen3.6-35B-A3B-Q8_0.gguf -t 192 -p 0 -n 256 -b 1 \
  --numa isolate --mlock \
  -r 5 -o json > baseline-35b-a3b-q8.json
```

Record median + 95% CI for each.

### Micro-benchmark per ukernel

Standalone C++ benchmark harness that calls the ukernel in a tight loop, compared to ggml's reference path. Measure:
- Cycles / op
- L1 hit rate
- L2 hit rate
- Effective GFLOPS

Target: ≥70% of Zen 5 peak throughput for the ukernel's working set fitting in L2.

### End-to-end speedup

After each phase gate:
- Run the full `llama-bench` suite above with ukernels enabled.
- Compare tok/s at p50, p95.
- Run 30-minute sustained decode to catch thermal regression.
- Diff NUMA 4-way aggregate throughput (`orchestrator_stack.py` production config).

### Correctness battery

Every phase must pass:
- PPL delta on WikiText-2, C4 (en), CodeParrot (for coder models): |Δ| < 0.01.
- MMLU 5-shot: |Δ| < 1.0 pt.
- HumanEval / SWE-bench-verified mini: |Δ| < 2.0 pt.
- Bit-exact comparison on 1000 randomized inputs for each ukernel.

## Risks and Gotchas

### Technical

1. **Q4_K_M dequant may not fuse efficiently.** The 6-bit super-scale format requires bit-manipulation that may not map cleanly to AVX-512. Mitigation: Phase 1 measures Q8_0 first; Phase 2 measures Q4_K_M separately. If Q4_K_M loses, ship Q8_0 only.
2. **DeltaNet recurrence may dominate decode time.** The ukernel approach only helps the dense matmul layers. If DeltaNet is >50% of per-token time, ukernel speedup is diluted. Mitigation: Phase 0 profiling gate.
3. **AVX-512 thermal downclocking.** Zen 5 reportedly doesn't downclock heavily, but our chassis cooling may differ. Mitigation: 30-min sustained benchmark in Phase 2.
4. **Numerical drift.** BF16 FMAs have different rounding than FP32 FMAs. Cumulative drift over 64 layers may cross a threshold. Mitigation: PPL gate + cosine-similarity gate per ukernel.
5. **Interaction with AM KV compaction.** KV compaction modifies the attention-softmax-V matmul. Our ukernels must be compatible with compacted KV layout or we lose the compaction gain. Verify in Phase 2.

### Engineering

1. **Maintenance burden**. ~50 ukernels for the production stack. Mitigate by: (a) code-gen from a small template, (b) per-shape ukernels tested in CI, (c) fallback to ggml default for unmatched shapes (fails open).
2. **Upstream divergence risk**. If we write this on our fork and upstream adds similar work, we'll have a merge conflict. Mitigation: Phase 4 upstream push; monitor ggml-org/llama.cpp for any CPU GEMV ukernel PRs (flag this handoff on the master index as a tracking item).
3. **CI cost**. Correctness battery across 5 models × 2 quants × full test suite is expensive. Mitigate with a fast path (PPL + bit-exact on small sample) for PRs and full sweep for merges.
4. **Rollback safety**. Feature-flag every ukernel with env-var override. If production shows a quality regression, disable via env var without redeploying.

### Organizational

1. **TIDE deprecation just happened.** Don't over-promise on another "unlock" until we have Phase 1 data. Phase 0–1 is 1–2 weeks of work before any commitment.
2. **Competing priorities.** Non-inference backlog (autopilot, routing intelligence, research intake) and v4 llama.cpp kernel-push are in-flight. This handoff is MEDIUM priority; not a drop-everything item.
3. **Expertise requirement.** The work is "HPC kernel engineer" type. If the picker-up isn't comfortable with AVX-512 intrinsics + compiler disassembly workflow, ramp-up is ~2–3 days on top of the Phase 0 reading.

## Open Questions

1. **Is llamafile's tinyBLAS already usable on our fork?** If so, much of Phase 1–3 is a pull + test, not a write. Check `llama.cpp` tip for the LLAMAFILE macro and the `sgemm.cpp` it gates.
2. **Does ZenDNN 5.2 actually help?** AMD claims "200% improvement" over prior versions via the Low Overhead API, but we haven't evaluated it on our stack. Worth a 1-day test before committing to ukernel work.
3. **What about Q4_0 instead of Q4_K_M?** Our production uses Q4_K_M but some benchmarks have shown Q4_0 is simpler to ukernel-ize (see `kv-cache-quantization.md` TurboQuant experience). If Q4_0 ukernel is 2× faster than Q4_K_M at similar PPL, re-quant is a cheaper win than ukernel work on Q4_K_M.
4. **Does Justine Tunney have Zen 5 benchmarks we could cite?** Her llamafile results are on Zen 4. Zen 5 numbers would firm up the prior-art case.
5. **Is there a community benchmark of `mul_mat` throughput on Zen 5 EPYC 9005-series specifically?** Phoronix has Zen 5 AVX-512 reviews but not LLM-decode-specific.
6. **Does the upstream llama.cpp ukernel work in `mmq.cpp` already cover our shapes adequately?** Re-read the VNNI templated code and measure before deciding the gap is real.
7. **MoE expert shapes are small (d_intermediate ~1408).** Do ukernels still help when the matmul fits entirely in L2? (L1 is 32 KB = 8K FP32; 1408 × FP32 = 5.6 KB, fits easily. May be a different story.)

## Success Criteria

**Minimum viable success (Phase 1 gate):** 1.15× end-to-end decode speedup from a single ukernel covering ~1/5 of per-token matmul work. Extrapolates to ~1.75× full coverage.

**Target success (Phase 2 gate):** 1.5× end-to-end decode speedup on Qwen3.6-27B Q8_0 with full shape coverage, correctness within tolerance, no thermal regression. For 27B dense this takes 4.8 t/s → 7.2 t/s, meaningful for interactive use.

**Stretch success:** 2.0–2.5× matching the KleidiAI / llamafile reference points. 4.8 → 9.6–12.0 t/s on 27B dense.

**Composition target (if rolled out):** Ukernel speedup × current NUMA 4-way aggregate × ngram-simple spec × AM KV compaction = multiplicative. Single-user latency improves by ukernel factor; multi-user aggregate scales similarly.

## Artifacts to Produce

1. `research/deep-dives/cpu-gemv-feasibility-baseline.md` — Phase 0 profiling report + gate decision.
2. `research/deep-dives/cpu-gemv-ukernel-prototype.md` — Phase 1 single-ukernel writeup.
3. Ukernel source in the fork under `ggml/src/ggml-cpu/zen5-ukernels/` (new directory; keeps the blast radius contained).
4. Benchmark harness in `tools/bench-ukernel/`.
5. CI hook in fork's test suite — bit-exact + PPL gate per ukernel.
6. Updated inference-acceleration-index row reflecting status.
7. (Phase 4 only) upstream PRs.

## References

### Required reading before picking this up

1. [Justine Tunney, "LLaMA Now Goes Faster on CPUs" (justine.lol/matmul)](https://justine.lol/matmul/) — the primary-source reference for the Zen 4 result that motivates this.
2. [Gope et al., "Highly Optimized Kernels and Fine-Grained Codebooks for LLM Inference on Arm CPUs" (arXiv:2501.00032)](https://arxiv.org/abs/2501.00032) — the ARM KleidiAI paper; the most directly relevant technique.
3. Our own `research/deep-dives/dflash-dart-diffusion-speculation.md` — for context on what we've ruled out on the speculative-decoding side.

### Related handoffs

- [`llama-cpp-kernel-push-rebase.md`](llama-cpp-kernel-push-rebase.md) — current kernel-level work on v4.
- [`attention-matching-kv-compaction.md`](attention-matching-kv-compaction.md) — orthogonal lever; composes with ukernel speedup.
- [`kv-cache-quantization.md`](kv-cache-quantization.md) — TurboQuant vs Hadamard result that shows fusion isn't automatically a win.
- [`gpu-acceleration-path.md`](gpu-acceleration-path.md) — TensileLite reference; cross-reference for shape-specialization context.

### Upstream code to inspect

- `llama.cpp/ggml/src/ggml-cpu/amx/mmq.cpp` — current VNNI templated GEMM, especially lines 2436–2463.
- `llama.cpp/ggml/src/ggml-cpu/ggml-cpu.c` — matmul dispatch.
- `llama.cpp/ggml/src/ggml-quants.c` — Q4_K_M and Q8_0 dequant reference.

### External libraries worth reading

- [llamafile tinyBLAS source](https://github.com/Mozilla-Ocho/llamafile) — specifically `llamafile/sgemm.cpp`.
- [KleidiAI source](https://github.com/ARM-software/kleidiai) — for the register-blocking patterns.
- [Intel oneDNN ukernel interface](https://github.com/oneapi-src/oneDNN/blob/master/src/cpu/gemm/gemm.hpp) — design reference.
- [Microsoft MLAS](https://github.com/microsoft/onnxruntime/tree/main/onnxruntime/core/mlas) — dispatch-table pattern reference.

### Hardware references

- [AMD EPYC 9655 specs / AVX-512 on Zen 5](https://www.amd.com/en/blogs/2025/unlocking-optimal-llm-performance-on-amd-epyc--cpus-with-vllm.html)
- [Phoronix EPYC Turin AVX-512 review](https://www.phoronix.com/review/amd-epyc-turin-avx512) — for the 512-bit datapath measurement.

## Pickup Checklist

When resuming this handoff:

- [ ] Re-read this doc end-to-end.
- [ ] Check `master-handoff-index.md` for any status changes since 2026-04-23.
- [ ] Check llama.cpp upstream for any new CPU ukernel PRs (this handoff may be partially obsoleted).
- [ ] Check for any new Justine Tunney / tinyBLAS Zen 5 benchmarks.
- [ ] Run Phase 0 baseline measurements first — do not skip the profiling gate.
- [ ] Start a new `progress/YYYY-MM/YYYY-MM-DD.md` entry before Phase 1 work begins.
- [ ] Update this handoff's Status field as phases close.
