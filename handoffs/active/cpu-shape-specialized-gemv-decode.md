# CPU Shape-Specialized GEMV Microkernel for Zen 5 Decode

**Status**: **Phase 1 AVX-512BW 8x8 Q8_0 kernel LANDED + NUMA fix LANDED 2026-04-24 — production-viable without env vars.** Kernel correctly emits `vpmaddubsw`+`vpmaddwd` on Zen 5, +31.8% at 1 thread, +1.6% at 96 threads (BW-saturated ceiling ~4.5 t/s on 27B Q8_0). The root cause of the initial 2.8× regression was NUMA first-touch of the CPU_REPACK buffer pinning 26 GB to node 0 — fixed by auto-mbind(MPOL_INTERLEAVE) inside the buffer allocator. PPL preserved. See §Session 15 below.
**Created**: 2026-04-23 (via session discussion of CPU fusion viability)
**Priority**: ~~MEDIUM~~ DEPRIORITIZED — revisit only for prefill/batched-decode regime where the compute/BW ratio shifts.
**Categories**: hardware_optimization, inference_serving, local_inference
**Workstream**: Inference Acceleration
**Parent index**: [`inference-acceleration-index.md`](inference-acceleration-index.md)
**Related**:
- [`llama-cpp-kernel-push-rebase.md`](llama-cpp-kernel-push-rebase.md) — current kernel-level work on the fork
- [`attention-matching-kv-compaction.md`](attention-matching-kv-compaction.md) — orthogonal throughput lever (KV-side)
- [`gpu-acceleration-path.md`](gpu-acceleration-path.md) — where TensileLite shape-specialization discussion originated
- [`llama-cpp-v3-upstream-rebuild.md`](../completed/llama-cpp-v3-upstream-rebuild.md) — paged attention / OpenMP repack / MoE expert reduction context

## Status as of 2026-04-24

### Session 15 — AVX-512BW 8x8 GEMV kernel LANDED, scaffold validated, multi-thread regression identified

A fresh child branch `cpu-optimization/q8-8x8-avx512bw` off `cpu-optimization/backlog-2026-04-23` (HEAD `138b26cd4`) contains:

- **New `block_q8_0x8` repack** — `make_block_q8_0x8` + `repack_q8_0_to_q8_0_8_bl` + `template <> int repack<block_q8_0, 8, 8>` specialization in `ggml/src/ggml-cpu/repack.cpp`. Layout: 8 fp16 scales + 256 bytes of i8 weights arranged so that each 64-byte sub-chunk of `.qs` is [R0[0..7], R1[0..7], …, R7[0..7]] — exactly one ZMM load per K-sub-chunk.
- **Generic reference GEMV + GEMM** — `ggml_gemv_q8_0_8x8_q8_0_generic` + `ggml_gemm_q8_0_8x8_q8_0_generic` mirroring the 4x8 generics with `ncols_interleaved=8`. Used as the correctness anchor.
- **AVX-512BW SIMD GEMV** — `gemv_q8_0_8x8_q8_0_avx512bw` in `arch/x86/repack.cpp`. Per K-block, 4 ZMM-wide subchunk iterations of `{vpabsb, vpmovb2m, masked vpsubb, vpmaddubsw, vpmaddwd, vpaddd}` to fold signed×signed i8 dots into a 16-lane i32 accumulator; the 16 lanes are reduced pairwise (`vpsrlq 32` + `vpaddd` + `vpmovqd`) to 8 per-row i32 sums, scaled by `d_B × d_A` and FMA'd into an fp32 accumulator across K-blocks. The helper `mul_sum_i8_pairs_acc_int32x16` from `avx512-helpers.h` was deliberately **not** used — it auto-selects VPDPBUSD (VNNI) under `__AVX512VNNI__` and Sessions 13/14 already falsified VNNI on Zen 5 (VPMADDUBSW runs 2/cycle vs VPDPBUSD 1/cycle).
- **Dispatcher branch** for x86 in `ggml_repack_get_optimal_repack_type` under the `GGML_TYPE_Q8_0` arm, gated on `GGML_Q8_0_8X8=1` env var + `cur->ne[1] % 8 == 0`.
- **Runtime A/B switch** `GGML_Q8_0_8X8_AVX ∈ {0,1}` inside the `ggml_gemv_q8_0_8x8_q8_0` entry to select SIMD vs portable-C without rebuilding.
- **ARM + generic arch-fallback.h aliases** for `ggml_gemv_q8_0_8x8_q8_0` and `ggml_gemm_q8_0_8x8_q8_0` so cross-arch builds keep linking.

**Correctness**: PPL on Wikitext-2 (3 chunks, ctx=512) = **6.6985 ± 0.708** with AVX-512BW path active — sensible baseline for this quant, no NaN, no divergence. Disassembly verified: loop emits `vpmaddubsw %zmm, vpmaddwd %zmm`, not `vpdpbusd`.

**Initial measurement showed a 2.8× regression at 96 threads despite winning +25% at 1 thread.** Root cause was NOT the kernel: the CPU_REPACK buffer was being first-touched on NUMA node 0 (26 GB pinned to one node, 96 threads × 4 nodes saturated that node's memory controllers). Plus a secondary serialization in `forward_mul_mat` for ne11 < 4 activation quantization. Both fixed in-session (commits `1d18efce3` + `e84a5c82f`):

1. **Auto-mbind the CPU_REPACK buffer** to `MPOL_INTERLEAVE` across all NUMA nodes inside `ggml_backend_cpu_repack_buffer_type_alloc_buffer`, gated on `ggml_is_numa()`. Scoped to this buffer, not process-wide. Log line `cpu-repack: mbind(MPOL_INTERLEAVE) on 25.4 GiB across 4 NUMA nodes` confirms at load time.
2. **K-parallel activation quant** for ne11 < 4 in tensor_traits `forward_mul_mat`, mirroring the standard-path pattern (ggml-cpu.c:1466-1475). Minor effect alone (NUMA dominated) but corrects an unrelated serialization.

**Final performance on Qwen3.6-27B-Q8_0** (`-fa 1 --numa distribute`, NO env vars — auto-mbind kicks in automatically):

| Threads | Baseline (non-repacked) | Repack 8x8 + AVX-512BW | Δ |
|---------|-------------------------|-------------------------|---|
| 1 | 0.85 t/s | **1.12 t/s** | **+31.8%** |
| 12 | 4.41 | 4.54 | +2.9% |
| 24 | 4.50 | 4.54 | +0.9% |
| 48 | 4.51 | 4.56 | +1.1% |
| 96 | 4.32 | 4.39 | +1.6% |

PPL on Wikitext-2 (3 chunks, ctx=512) = **6.6985 ± 0.708** with the AVX-512BW path + auto-mbind active. Unchanged from pre-mbind run. Disassembly still confirms `vpmaddubsw`+`vpmaddwd` in the hot loop, not `vpdpbusd`.

Q8_0 decode is BW-saturated at ~4.5 t/s on this hardware (12t+), so the +1-3% at high thread count is the real kernel edge over the baseline single-row path — both hit the ~26% of roofline ceiling together. The +31.8% at 1 thread is where the 8-row amortization win survives because DRAM isn't saturated. Consistent with `feedback_cpu_decode_bw_bound.md`: **don't write compute-focused ukernels for quantized decode without a BW roofline check** — the realistic CPU2 gain is 1t-specific, not the projected +40-70% at high thread count.

**Before-vs-after comparison of the NUMA fix:**

| Threads | Baseline | Repack+BW w/o NUMA fix | Repack+BW w/ auto-mbind |
|---------|----------|------------------------|-------------------------|
| 1 | 0.84 | 1.05 | 1.12 |
| 24 | 4.46 | 1.60 | 4.54 |
| 96 | 4.38 | 1.58 | 4.39 |

Without the NUMA fix, the repack path capped at ~1.6 t/s regardless of thread count because all 26 GB of weights lived on node 0.

**Status: production-viable at parity-plus without env vars.** Gates remain `GGML_Q8_0_8X8=1` + `GGML_Q8_0_8X8_AVX=1`, both default OFF. Safe to flip default ON in a follow-up once Q6_K and Q5_K get the same 8x8 SIMD treatment so a blanket Q{5,6,8}_K x86 repack enable-flip makes sense holistically.

**Recommended follow-ups:**
- **Q6_K 8x8 AVX-512BW** — Session 14 flagged Q6_K at 18.2% of Q4_K_M decode cycles; same dispatcher-NEON-only gap. Complexity ~2× Q8_0 due to 4+2 bit-split unpack. Expected: +2-5% on Q4_K_M decode.
- **Q5_K 8x8 AVX-512BW** — smaller cycle share (4.6%), same complexity profile as Q6_K. Lower priority but trivial follow-on once Q6_K is done.
- **Cross-check Q4_K_M at 1t** to confirm the +30% single-thread win extends there too — validates the tensor_traits path across all types.
- **Upstream the NUMA fix** — `mbind(MPOL_INTERLEAVE)` on CPU_REPACK buffer is a real bug-fix affecting every multi-NUMA host running any repacked quant. Worth a PR to ggml-org/llama.cpp independent of the Q8_0 kernel.
- **Flip default ON** — once Q6_K/Q5_K land, remove the `GGML_Q8_0_8X8` env gate and make x86 Q8_0/Q{5,6}_K repack the default.

---

**Archived initial-measurement table (pre-NUMA-fix, for history):**

| Threads | Baseline (no repack) | Repack 8x8 + AVX-512BW | Δ |
|---------|----------------------|-------------------------|---|
| 1 | 0.84 t/s | **1.05 t/s** | **+25.0%** |
| 4 | 2.95 | 1.29 | −56.3% |
| 12 | 4.35 | 1.27 | −70.8% |
| 24 | 4.46 | 1.60 | −64.1% |
| 48 | 4.11 | 1.12 | −72.7% |
| 96 | 4.38 | 1.58 | −63.9% |

The **kernel itself is both correct and faster** (+25% single-thread). What caps the multi-thread number is the tensor_traits `forward_mul_mat` plumbing — absolute throughput *peaks* at 24t (1.60) and *regresses* at 48/96t, the opposite of the baseline path which scales cleanly to 12t then BW-saturates at ~4.4 t/s. Raw data + detailed analysis: `/mnt/raid0/llm/epyc-inference-research/data/cpu_optimization/2026-04-24-q8-8x8-kernel/thread-scaling-summary.md`.

**Bottleneck candidates** (unprobed, ranked by likelihood):
1. **Serialized `from_float` activation quant at ne11=1** — only thread 0 runs, the other 95 hit `ggml_barrier`, which is 28% of decode cycles at 96t per CPU1 Phase 1.3 handoff.
2. **`disable_chunking = ggml_is_numa()`** kills dynamic work-stealing; each thread gets one static chunk, and any thread slower than average stalls the per-matmul barrier.
3. **CPU_REPACK buffer may not be THP-backed** (vs baseline's mmap'd GGUF pages, which are 2 MiB under `THP=always`).
4. **No SW prefetch** in the 8x8 BW kernel — working set per thread is 8× larger than the non-repacked single-row path, so L1 hit rate is likely worse.

These are **tensor_traits plumbing issues that affect every repack-backed ggml type, not a Zen-5 kernel issue**. Q4_K_M via the same path hits 6.84 t/s (Session 14 baseline), which suggests its higher compute-per-byte ratio hides the plumbing cost — Q8_0's simpler 1-byte dot exposes it.

**Recommended follow-up** (on a fresh handoff, out of CPU2 scope):
- Instrument `forward_mul_mat` with `GGML_PERF=1`-style per-phase timing (activation quant vs barrier vs GEMV) at 1/24/96 threads to isolate which of #1–#4 dominates.
- If #1 dominates: parallelize `from_float` quant for ne11=1 by striping K-blocks across threads instead of rows. This is a repack-infra fix that would lift *every* repacked quant at ne11=1.
- If #4 dominates: add `_mm_prefetch(b_ptr[l+1].qs, _MM_HINT_T0)` inside the K-block loop.
- Cross-check Q4_K_M via `ggml_gemv_q4_K_8x8_q8_K` at 1t vs 24t vs 96t to see whether it shows a muted version of the same scaling pattern.

Kernel is landed behind env gates (`GGML_Q8_0_8X8=1`, `GGML_Q8_0_8X8_AVX=1`) — default OFF, no impact on production paths. Flipping default requires the multi-thread bottleneck to be fixed first.

### 2026-04-23 Phase 1 Target #1 — NEGATIVE RESULT (VNNI falsification, preserved for history)

Implemented the "quick win" Phase 1 Target #1 identified by the Phase 0 audit: ported `ggml_vec_dot_q8_0_q8_0` from AVX2 (256-bit) to AVX-512VNNI (512-bit) inside `ggml/src/ggml-cpu/arch/x86/quants.c`, using the existing `mul_sum_i8_pairs_acc_int32x16` helper in `avx512-helpers.h`. Disassembly verified — `vpdpbusd %zmm,%zmm,%zmm` + `vpabsb %zmm,%zmm` + `vpmovb2m` in the new path vs `{vex} vpdpbusd %ymm,%ymm,%ymm` in the baseline.

Measured on **Qwen3.6-27B Q8_0** (the canonical CPU2 target, where perf had shown 63.43% of cycles in this function):

| Config | AVX2 baseline | AVX-512VNNI | Delta |
|---|---|---|---|
| 96t pinned, `-n 64 -r 3` | 4.241 t/s (σ=0.075) | 4.313 t/s (σ=0.003) | **+1.7%** |
| 1t pinned, `-n 8 -r 2` | 1.020 t/s | 0.983 t/s | **−3.6%** (port overhead regressed) |

**Projection was 1.46× end-to-end; measured 1.017×**. Falsified by a factor of 30×.

Root cause: the 63.43% perf sample count inside `ggml_vec_dot_q8_0_q8_0` was **cycles waiting for DRAM loads inside the inner loop**, not cycles doing ALU work. Doubling the ALU throughput (256-bit → 512-bit VNNI) can't help when the CPU is stalled on memory. At 1-thread, the per-iteration port overhead (cross-lane `vinsertf32x8`, `_mm512_reduce_add_ps`, odd-block tail) actively regresses.

Change reverted (`git diff ggml/src/ggml-cpu/arch/x86/quants.c` is clean). Build artifact at `build-vnni-q8/` preserved for reference until next session cleanup.

**Where CPU2 might still help** (future lanes, not pursued in current session):
- Prefill matmuls (M > 1) where compute/BW ratio is better.
- Attention softmax/RoPE on FP16/BF16 activations (would benefit from VDPBF16PS, not VNNI).
- Batched multi-user decode (`-np N`) as N grows toward prefill regime — tracked under CPU14.

**Work redirected to CPU1 (TP-sharding) and CPU4 (per-CCD sync primitive)** — memory-bandwidth-addressing levers rather than compute-addressing. See [`cpu-inference-optimization-index.md`](cpu-inference-optimization-index.md) for updated priorities.

### 2026-04-23 audit update (pre-Phase-0)

Joined the coordinated pickup sequence under [`cpu-inference-optimization-index.md`](cpu-inference-optimization-index.md) as **CPU2**. Pre-Phase-0 audit resolved several open items and adjusted gates. Key changes from the original draft:

- **tinyBLAS IS already in the fork** (answers Open Question 1). See updated Prior Art §5 and Phase 0 § below.
- **KleidiAI plugin is repo-internal prior art** for how a Zen 5 ukernel plugin directory should be laid out. See updated Prior Art §2.
- **`perf` is not installed** on the host. Phase 0 profiling must use `GGML_PERF=1` + `rdtsc` micro-harness + `getrusage` + `/usr/bin/time -v` fallbacks.
- **Phase 0 DeltaNet gate tightened from >60% to >40%** — Amdahl's bound on matmul speedup vs the 1.5× Phase 2 target.
- **TIDE date-collision note**: latest fork commits dated 2026-04-23 (`143ded626`, `c4e06b01e`, `59d2012b2`) are TIDE-related, same day as TIDE's deprecation. Phase 0 baseline runs should confirm TIDE code paths are dormant or compiled out.
- **Path fix**: `kv-cache-quantization.md` reference updated to `../completed/kv-cache-quantization.md`.
- **Phase 3 roster items (Coder-480B, SG4, M2.7)**: deferred per user directive until Phase 3 is actually scoped. Do not edit roster yet.

Original handoff rationale is preserved below. All Phase 0 code/profiling work happens in `/mnt/raid0/llm/llama.cpp-experimental` on a fresh branch off `production-consolidated-v4` — never in the production `llama.cpp` tree.

Motivation: after the TIDE calibration-router early-exit track was deprecated 2026-04-23 (projection quality could not be solved with either linear or bottleneck-adapter approaches), the set of remaining CPU throughput levers is narrow. Weight-reduction strategies (MoE expert pruning, AM KV compaction, KV quantization, ngram-simple spec) are mature or in production. Operator-level fusion was found not viable on CPU (Hadamard + unfused `q4_0` beat TurboQuant + fused by 2.2×; see [`../completed/kv-cache-quantization.md`](../completed/kv-cache-quantization.md) and session discussion 2026-04-23). The one significant unexplored CPU lever remaining is **shape-specialized GEMV microkernels for the M=1 decode regime** on the EPYC 9655's AVX-512 datapath.

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

**Qwen3.6-27B (dense hybrid, 64 layers)** — **dims corrected 2026-04-23 from GGUF metadata of `/mnt/raid0/llm/models/Qwen3.6-27B-Q8_0.gguf` (arch `qwen35`)**:

| Op | Shape (K → N) | Per-token calls | Notes |
|---|---|---|---|
| Attention Q projection | **5120 → 6144** (24 heads × 256 head_dim) | 16 (full-attention layers only, every 4th) | GQA: 24 Q heads, 4 KV heads, head_dim=256 |
| Attention K projection | **5120 → 1024** (4 heads × 256 head_dim) | 16 | Small shape — may not benefit from ukernel |
| Attention V projection | **5120 → 1024** | 16 | Small shape — may not benefit from ukernel |
| Attention output projection | **6144 → 5120** | 16 | Input size differs from other projections |
| MLP gate | **5120 → 17408** | 64 | All layers have MLP |
| MLP up | **5120 → 17408** | 64 | Paired with gate |
| MLP down | **17408 → 5120** | 64 | |
| DeltaNet (qwen35.ssm.*): inner_size=6144, conv_kernel=4, state_size=128, group_count=16, time_step_rank=48 | model-specific | 48 (75% of layers) | Requires separate analysis |

Total: ~7 distinct non-DeltaNet shapes, MLP shapes dominate (64 calls/layer × 3 shapes vs 16 × 4 for attention). Specialize each → ukernel count ≈ 7 × quant_types (Q4_K_M, Q8_0) = 14 ukernels for this model.

**Context length: 262144 (256K)**. `full_attention_interval = 4` (every 4th layer is full attention, others are DeltaNet → 16 full + 48 DeltaNet = 75% DeltaNet, matches handoff assumption).

**Original draft had MLP=27648 (+59% vs actual 17408) and GQA=14Q/2KV (vs actual 24Q/4KV); corrected from authoritative GGUF metadata 2026-04-23 audit.** The smaller MLP dim is significant: it narrows the Phase 1 ukernel target and reduces the per-layer GEMV work. At 5120×17408 Q8_0, the MLP-up weight matrix is 89 MB (vs 141 MB for the originally-claimed 27648), which changes the L3 resident-working-set calculation.

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
- **Integration status for us (resolved 2026-04-23 audit)**: **tinyBLAS IS ALREADY integrated into our fork** at `ggml/src/ggml-cpu/llamafile/sgemm.cpp` + `sgemm.h` (MPL-2.0), gated by the `GGML_USE_LLAMAFILE` macro. Compiles clean across all build targets. Open Question 1 is answered: no license/merge issue. The Phase 0 measurement we need is sgemm-enabled vs sgemm-disabled on Zen 5, not "can we integrate it."

### 2. ARM KleidiAI

- **Hardware**: ARM Neoverse (Graviton 3/4).
- **Decode speedup**: 2.0× on LLaMA-3-8B 4-bit decode, reaching 45.5 tok/s at batch=1 on Graviton 3.
- **Technique**: Shape-specialized GEMV + GEMM, distinct paths; per-group fine-grained codebook quantization with **codebooks resident in the register file**; weight-column reuse during GEMV to amortize activation-vector loads.
- **Data types**: 4-bit weights, 8-bit activations.
- **Effort**: Medium-high; requires ARM ISA expertise (DOT product, SME2).
- **Primary source**: [Gope et al., arXiv:2501.00032](https://arxiv.org/abs/2501.00032) — most directly relevant paper for our setup. Required reading.
- **Integration**: KleidiAI is integrated into llama.cpp upstream via a plugin with separate GEMV/GEMM dispatchers (ARM only). The x86 analog is what this handoff proposes.
- **Repo-internal template (resolved 2026-04-23 audit)**: the KleidiAI plugin sits at `ggml/src/ggml-cpu/kleidiai/` in our fork — ARM-only dispatcher with its own CMake wiring, kernel registry, and fallback-to-ggml-default pattern. **This is the directly-reusable directory layout for our proposed `ggml/src/ggml-cpu/zen5-ukernels/` plugin.** New ukernels should follow this structure rather than reinvent it.

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
- [ ] Profile a baseline Qwen3.6-27B Q8_0 decode. **Note (2026-04-23 audit): `perf` is NOT installed on the host** (`which perf` empty; `linux-tools-$(uname -r)` absent). Use fallbacks: (a) rebuild with `GGML_PERF=1` for per-op timings; (b) `rdtsc`-bracketed micro-harness for tight loops; (c) `/usr/bin/time -v` for wall-clock and page-fault counts; (d) `getrusage` for context-switch and RSS. If sudo is available and the user approves, install `linux-tools-$(uname -r)` for proper `perf stat -e cycles,instructions,cache-references,cache-misses,dTLB-load-misses,l2_rqsts.demand_data_rd_hit` + `perf record -g` flamegraph.
- [ ] **Measure tinyBLAS on/off first** (new Phase 0 step per 2026-04-23 audit): `ggml/src/ggml-cpu/llamafile/sgemm.cpp` is already compiled under `GGML_USE_LLAMAFILE`. Rebuild twice (macro on/off), record end-to-end tok/s delta. This single datum quantifies how much M=1 gain is already "free" and informs the remaining headroom a custom Zen 5 ukernel could recover.
- [ ] Measure: (a) time in matmul ops vs time in DeltaNet recurrence vs time in RMSNorm/RoPE/sampling. (b) IPC and L1/L2 hit rates in the matmul functions (via `GGML_PERF` + any installed counters). (c) fraction of decode time in `ggml_compute_forward_mul_mat` and its callees.
- [ ] **Gate (tightened 2026-04-23 from >60% to >40%)**: if >40% of decode time is in DeltaNet recurrence (not matmul), abandon and document why. Reason: by Amdahl's law, with ≥40% DeltaNet time, max end-to-end speedup from matmul acceleration cannot reach the Phase 2 target of 1.5× even with an infinitely-fast ukernel. Otherwise proceed.

**Artifacts:** a short markdown writeup (`research/deep-dives/cpu-gemv-feasibility-baseline.md`) with the profiling numbers and the gate decision.

### Phase 1: Single-shape prototype — prove the lever (3–5 days)

**Goal:** implement **one** ukernel for **one** shape on **one** model and measure end-to-end speedup.

Target: **Qwen3.6-27B Q8_0 MLP-up matmul**, shape **K=5120 → N=17408** (corrected 2026-04-23 from GGUF metadata; original draft said N=27648 in error).

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

1. ~~**Is llamafile's tinyBLAS already usable on our fork?**~~ **RESOLVED 2026-04-23**: YES. `ggml/src/ggml-cpu/llamafile/sgemm.cpp` + `sgemm.h` (MPL-2.0) compiled under `GGML_USE_LLAMAFILE` macro. Phase 0 measures sgemm on/off delta as a first step; the residual headroom above that is what a custom Zen 5 ukernel would target.
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
- [`../completed/kv-cache-quantization.md`](../completed/kv-cache-quantization.md) — TurboQuant vs Hadamard result that shows fusion isn't automatically a win.
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

- [ ] Re-read this doc end-to-end including the 2026-04-23 audit update block.
- [ ] Check `master-handoff-index.md` and `cpu-inference-optimization-index.md` for any status changes since 2026-04-23.
- [ ] Check llama.cpp upstream for any new CPU ukernel PRs (this handoff may be partially obsoleted).
- [ ] Check for any new Justine Tunney / tinyBLAS Zen 5 benchmarks.
- [ ] **Work in `/mnt/raid0/llm/llama.cpp-experimental`, never the production `llama.cpp` tree.** Ensure the experimental worktree is anchored on `production-consolidated-v4` (or successor) before starting.
- [ ] **Measure tinyBLAS on/off as first Phase 0 step** (`GGML_USE_LLAMAFILE` macro); that delta changes the remaining headroom calculation.
- [ ] **Confirm TIDE code paths are dormant** — fork commits `143ded626`, `c4e06b01e`, `59d2012b2` are TIDE-related and dated 2026-04-23 (same day as TIDE's deprecation). Baseline must not run with early-exit enabled.
- [ ] Run Phase 0 baseline measurements — do not skip the profiling gate (DeltaNet >40% abandon threshold).
- [ ] Start a new `progress/YYYY-MM/YYYY-MM-DD.md` entry before Phase 1 work begins.
- [ ] Update this handoff's Status field as phases close.
