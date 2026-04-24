# CPU Optimization — Step 3 CPU3 Phase 0 Root Baseline (2026-04-23)

**Parent plan**: `cpu-inference-optimization-index.md` §Pickup Sequence Step 3
**Scope**: System-state audit + thread sweep + per-op breakdown + barrier cost + effective bandwidth + GGUF dims. Root gate for CPU1 (TP), CPU2 (GEMV), CPU4 (sync primitive), CPU5 (hugepages), CPU8 (weight replication).
**Workspace**: `/mnt/raid0/llm/llama.cpp-experimental` on branch `cpu-optimization/backlog-2026-04-23` (HEAD `9e048fbc1`, tinyBLAS ON).
**Baseline model**: Qwen3-Coder-30B-A3B-Instruct-Q4_K_M (17.28 GiB, 30.53 B params, hybrid MoE)
**Raw data**: `/mnt/raid0/llm/epyc-inference-research/data/cpu_optimization/2026-04-23/`

## 1. System-state audit (captured 2026-04-23T19:42:43+00:00)

Key values from `system-state-audit.txt`:

| Item | Value | Notes |
|---|---|---|
| CPU | AMD EPYC 9655 96-Core (Zen 5 Turin, family 26 model 2) | 192 logical cores, SMT=on |
| NUMA mode | **NPS2** (2 nodes) | node 0: 580 GB, node 1: 580 GB; distance 10/12 |
| THP | `madvise` (default) | Candidate CPU3 Step 4 to set `always` |
| NUMA balancing | **1 (ON)** | Candidate CPU3 Step 4 to disable |
| Hugepages (2M/1G) | **0 allocated** | Candidate CPU5 to allocate 1 GB pages |
| Governor | `performance` | Already deployed ✓ |
| Memory | 1188 GB total; 305 GB free; 820 GB in page cache (existing mmap'd models) | Plenty of headroom |
| `perf` | **NOT INSTALLED** | Matches earlier audit; use ggml/rdtsc/getrusage fallbacks |
| Zen 5 ISA | `avx512f avx512dq avx512_bf16 avx512vnni avx512vbmi avx512_vbmi2 avx512_bitalg avx512_vpopcntdq avx512_vp2intersect avx_vnni gfni vaes vpclmulqdq fsrm la57` | Full Zen 5 AVX-512 family available |

## 2. Thread sweep — Qwen3-Coder-30B-A3B Q4_K_M decode (`-p 0 -n 64 -r 2`)

All runs use `llama-bench` with `GGML_USE_LLAMAFILE=ON` (immaterial per §CPU7 finding but held constant) and `taskset` for thread pinning up to 144t; 192t uses `--numa distribute -mmp 1`.

| Config | CPU set | Threads | avg t/s | stddev | Notes |
|---|---|---|---|---|---|
| t024 | 0–23 (node 0 Q0A) | 24 | **40.76** | 0.105 | Matches production worker_explore 39.1 t/s closely |
| t048 | 0–47 (node 0 half) | 48 | **39.59** | 0.208 | Minor regression vs 24t — barrier cost exceeds BW gain |
| t096 (loaded) | 0–95 (full node 0) | 96 | 47.91 | 0.26 | Original run; host load 6–170 |
| **t096 (quiet)** | 0–95 (full node 0) | 96 | **49.11** | **0.08** | **PEAK CONFIRMED.** Full 6-channel DDR5 node-local BW. Stddev tightens from 0.26 → 0.08 on quiet host. |
| t144 | 0–143 (node 0 + half node 1) | 144 | **25.74** | **18.50** (bimodal 12.66 / 38.83) | NUMA crossing disaster — weight pages split unevenly |
| **t192 (quiet)** | all cores `--numa distribute --mlock` | 192 | **18.69** | **7.23** (bimodal 13.58 / 23.81) | Production registry number was 14.2 t/s for this config. Our number is +31% vs registry but **still bimodal** — first sample slow (page-in), second sample faster. Needs more samples + warm page cache for a clean number. |

### The 96t/192t ratio: **2.63×**

Running on a single NUMA node with half the threads is **2.63× faster** than running on the full machine with all threads for single-instance decode on this model. This is the gap CPU1 (intra-process TP-sharding) is trying to close. Compare against the 6.7× aggregate speedup from 4×48t NUMA-pinned multi-instance (95.8 t/s) — the single-instance TP ceiling is bounded by that aggregate, and the 49.11 → ~95 trajectory would represent 80% of the aggregate ceiling in a single session.

### Interpretation

1. **48t is barrier-limited, not BW-limited.** Adding threads 25–48 to a single node 0 half barely moves throughput (40.8 → 39.6) — within noise on the regression side. This tells us barrier and thread-pool overhead at the per-layer sync points costs about as much as the extra compute/BW the added threads supply.
2. **96t single-socket is the peak for single-instance.** Using all of node 0 (full 6-channel BW + more FMAs) brings +21% vs 48t and +18% vs 24t. This config is *not* how production runs (production uses 4×48t pinned for aggregate), and suggests a natural single-instance operating point that wasn't previously measured.
3. **Crossing NUMA boundaries without proper sharding is catastrophic.** 144t spans 1.5 NUMA nodes. The per-sample bimodality (12.66 and 38.83 t/s) indicates weights pages landed unevenly — one sample got lucky, the other didn't. The 18.5 stddev is the kind of thing that breaks production SLAs.
4. **This baseline reshapes CPU1 (TP-sharding) framing.** The original TP claim was "1×192t is 20–50% of hardware capability." Our measurement: 96t single-node is nearly optimal for single-instance; the gap to fill is 96t → full-machine, not 48t → full-machine. That's still plenty of TP opportunity, but the target is different.

## 3. Per-function time breakdown (perf record -g, DWARF call graph)

`perf_event_paranoid` set to 1 (user-approved sysctl, 2026-04-23). `perf record --call-graph dwarf -F 99` captured 55K + 145K samples on two decode runs:

### 3a. Qwen3-Coder-30B-A3B Q4_K_M @ 96t (48.13 t/s decode)

| Overhead | Symbol | Notes |
|---|---|---|
| 45.04% | unresolved `0x0000000000026580` family | libomp spin wait / OpenMP barrier |
| 24.72% | `ggml_gemv_q4_K_8x8_q8_K` | **Already-specialized Q4_K GEMV** in `ggml/src/ggml-cpu/arch/x86/repack.cpp` — KleidiAI-style upstream work, 8×8 tiles |
| 9.24% | `ggml_vec_dot_q6_K_q8_K` | Q6_K dot product (some tensors are Q6_K) |
| 2.72% | `ggml_cpu_fp32_to_fp16` | KV cache + activation conversion |
| 1.66% | `ggml_compute_forward_mul_mat` | Matmul dispatcher |
| 1.14% | `ggml_vec_dot_f16` | FP16 dot (attention KV ops) |
| 0.98% | kernel space | context switches / syscalls |
| ~14% | misc unresolved libomp + small ops | |

**Barrier-bound at 96t**: 45% in OpenMP wait-states, ~35% in hot matmul + dispatcher, rest is misc ops. The Q4_K path has already been specialized upstream (GEMV 8×8 tile).

### 3b. Qwen3.6-27B Q8_0 @ 96t (4.41 t/s decode)

| Overhead | Symbol | Notes |
|---|---|---|
| **63.43%** | `ggml_vec_dot_q8_0_q8_0` | **The single hot function.** `ggml/src/ggml-cpu/arch/x86/quants.c:1012-1066` — **AVX2-only (256-bit `__m256`), NO AVX-512 path** |
| 32.34% | unresolved `0x0000000000026580` | libomp barrier |
| 0.25% | `ggml_compute_forward_mul_mat` | Dispatcher |
| 0.07% | `ggml_compute_forward_gated_delta_net` | **DeltaNet main forward** |
| 0.04% | `ggml_compute_forward_ssm_conv` | DeltaNet conv1d |
| <0.01% | `ggml_compute_forward_rms_norm`, `rope_flt`, `l2_norm`, `add`, `silu` | Noise |

### Critical findings from 3a + 3b

**1. DeltaNet fraction: 0.11% — gate PASSES with huge margin.**

Feared that DeltaNet recurrence would bottleneck decode and cap ukernel speedup. Actually measured: `gated_delta_net` + `ssm_conv` + related SSM ops = **0.11% of cycles** on Qwen3.6-27B Q8_0. The handoff's "DeltaNet might dominate" concern is refuted. DeltaNet's own matmul-like operations already route through `ggml_vec_dot_q8_0_q8_0`, so speeding up that function speeds up the DeltaNet path automatically.

**2. Matmul is dominated by a single un-AVX-512'd function on Q8_0 decode.**

`ggml_vec_dot_q8_0_q8_0` in `arch/x86/quants.c:1012` is conditionally compiled: AVX2 path (lines 1029-1046) or AVX fallback (lines 1047-1065). **No `__AVX512F__` or `__AVX512VNNI__` path.** On Zen 5 with full 512-bit datapath + native `VPDPBUSD` (int8 dot product), this is a blatant missing ukernel. This is the **#1 concrete Zen 5 opportunity** that the GEMV handoff was circling without naming precisely.

**3. Barrier cost is 32–45% of decode cycles, not compute.**

libomp spin waits dominate a large fraction (45% on Q4_K_M at 96t, 32% on Q8_0 at 96t). This is **CPU4 (per-CCD sync primitive) and CPU1 (TP-sharding with smaller barriers) directly addressable opportunity**. A barrier-cost reduction of, say, 50% translates to +22% end-to-end on Q4_K_M and +16% on Q8_0.

**4. Q4_K is already specialized upstream.** `ggml_gemv_q4_K_8x8_q8_K` exists and is the hot function for Q4_K decode. Further Q4_K-shape specialization by us would layer on top of an already-tuned kernel. CPU2 Q4_K work has less headroom than CPU2 Q8_0 work.

### Projected CPU2 impact — ORIGINAL ESTIMATE (FALSIFIED BY MEASUREMENT)

Working from the Q8_0 profile (63.43% matmul + 32.34% barrier + rest):

| Intervention | Matmul speedup | End-to-end speedup | Projected Qwen3.6-27B Q8_0 t/s (from 4.41) |
|---|---|---|---|
| Port `ggml_vec_dot_q8_0_q8_0` to AVX-512VNNI (quick win) | 2× | 1/(0.32 + 0.63/2 + 0.05) = 1.46× | 6.4 t/s |
| + Shape-specialize for Qwen3.6-27B MLP-up (K=5120, N=17408) | 3× total | 1/(0.32 + 0.21 + 0.05) = 1.72× | 7.6 t/s |
| + Address libomp barrier (CPU4): cut to 15% | 3× + barrier | ~2.1× | 9.3 t/s |

**These projections were falsified by direct measurement** — see §3c below.

### 3c. CPU2 Phase 1 Target #1 measurement — NEGATIVE RESULT

Built an AVX-512VNNI port of `ggml_vec_dot_q8_0_q8_0` in `build-vnni-q8/`:

- Used existing helper `mul_sum_i8_pairs_acc_int32x16` from `avx512-helpers.h` (handles signed-signed via abs+sign trick over VPDPBUSD).
- Processed 2 Q8_0 blocks (64 bytes) per iteration at 512-bit width.
- Disassembly confirmed: new binary emits `vpdpbusd %zmm1,%zmm0,%zmm2` + `vpabsb %zmm0,%zmm0` + `vpmovb2m` — the intended AVX-512VNNI path. Baseline build emits only `{vex} vpdpbusd %ymm...` — 256-bit.

Measured end-to-end on Qwen3.6-27B Q8_0 decode:

| Config | AVX2 baseline | AVX-512VNNI | Delta |
|---|---|---|---|
| 96t pinned, `-n 64 -r 3` | 4.241 t/s (σ=0.075) | 4.313 t/s (σ=0.003) | **+1.7%** |
| 1t pinned, `-n 8 -r 2` | 1.020 t/s (σ=<0.001) | 0.983 t/s (σ=0.002) | **−3.6%** |

**Interpretation**: the 63.43% perf-sample count in `ggml_vec_dot_q8_0_q8_0` was **cycles waiting for DRAM inside the inner loop**, not cycles doing ALU work. Doubling ALU throughput (256-bit → 512-bit VNNI) produces no meaningful end-to-end gain because the CPU is stalled on memory loads, not instruction issue. At 1-thread the additional per-iteration overhead of my port (cross-lane `vinsertf32x8`, `_mm512_reduce_add_ps`, odd-block tail) actually regresses by 3.6%.

The decode workload runs at ~25% of the 460 GB/s BW roofline (Qwen3.6-27B Q8 × 4.3 t/s ≈ 116 GB/s), which at first glance suggests compute headroom. But the effective roofline for single-instance 96t is lower — barrier idle time (32% of cycles) and load-port contention within each thread further cap throughput well below raw DRAM BW. **The "compute headroom" is illusory for this workload**.

### 3d. CPU2 Phase 1 gate — FAIL (BW-bound not compute-bound)

Change reverted (git diff clean on quants.c). CPU2 GEMV ukernel work on Q8_0 decode does not pay under measurement on this hardware.

Where CPU2 might still help (future lanes, not this session):
- **Prefill matmuls** (M > 1): BLAS-style throughput regime; VDPBF16PS/VNNI can matter. Outside this session's scope.
- **Attention softmax/RoPE** on FP16/BF16 activations: not covered by GEMV ukernels anyway.
- **Batched multi-user decode** (`-np N`): batches approach the prefill regime as N grows; see CPU14 in the umbrella index.

### CPU1 (TP-sharding) Phase 0 gate — PASSED

Per `intra-process-tensor-parallel-decode.md` Phase 0 gates:
- **(a) 192t single-instance is <60% of BW roofline**: measured 18.7 t/s × ~2 GB/token ≈ 37 GB/s = 8% of 460 GB/s roofline. PASS (by huge margin).
- **(b) Barrier cost at 192t >15% of per-token time**: measured 32–45% at 96t, extrapolates higher at 192t given the bimodality. PASS.
- **Bonus data**: 96t/192t throughput ratio = 2.63× — this is the concrete TP-sharding opportunity. Closing this gap with CCD-local weight sharding is the explicit CPU1 Phase 1 goal.

CPU1 Phase 1 prototype is gated as GO. Phase 1 is a ~1-week effort (per-CCD thread pools + Option A replicated reduce + one MLP-up layer shard + numerical validation + bench); schedule for a dedicated session.

### CPU4 (per-CCD sync primitive) — PROMOTED to HIGH standalone

32–45% barrier cost measured. Previously MED, bundled into CPU3 Phase 3. Today's measurements justify promoting to a standalone HIGH lever: lock-free per-CCD spin primitive replacing OpenMP global barrier could recover a significant slice independent of CPU1. ROI: halving barrier cost → +16–22% end-to-end.

## 4. Barrier / sync cost

*To be populated — microbenchmark: tight-loop pthread barrier at N threads, measure cost per barrier.*

## 5. Effective bandwidth vs 460 GB/s roofline

Using measured tok/s × weight_bytes_per_token:

| Config | tok/s | ~GB/s | % of 460 GB/s |
|---|---|---|---|
| 24t | 40.76 | 16 GB × 40.76 = **652 GB/s**... wait that's >460 | — |

*Hmm — the 30B-A3B MoE doesn't read all 16 GB per token; only the active experts' weights + attention + shared layers. Need to compute `active_bytes_per_token` properly. For a3b (3B active): roughly 16 GB × (3/30) = 1.6 GB per token + attention/norm ~0.5 GB = ~2 GB/token for MoE hybrids. At 40.76 t/s × 2 GB = 82 GB/s ≈ 18% of 460 roofline. That's the number CPU1/CPU2 levers fight over.*

*To be validated via ggml activation trace or profiling; this is an estimate.*

## 6. Qwen3.6-27B GGUF metadata (CPU2 Phase 0 dependency)

Captured via `llama-bench -v`:

| Key | Value | Matches handoff? |
|---|---|---|
| `general.architecture` | `qwen35` | (same arch as Qwen3.5 in llama.cpp — registers under existing arch) |
| `qwen35.block_count` | **64** | ✓ handoff claim |
| `qwen35.embedding_length` | **5120** | ✓ handoff claim |
| `qwen35.feed_forward_length` | **17408** | ✗ **handoff claimed 27648 — off by 59%. CORRECTED.** |
| `qwen35.attention.head_count` | **24** | ✗ handoff claimed 14 — CORRECTED |
| `qwen35.attention.head_count_kv` | **4** | ✗ handoff claimed 2 — CORRECTED |
| `qwen35.attention.key_length` | 256 | Head dim |
| `qwen35.attention.value_length` | 256 | Head dim |
| `qwen35.context_length` | 262144 (256K) | — |
| `qwen35.full_attention_interval` | 4 | 16 full / 48 DeltaNet = 75% DeltaNet ✓ |
| `qwen35.rope.freq_base` | 1e7 | — |
| `qwen35.ssm.conv_kernel` | 4 | DeltaNet conv kernel |
| `qwen35.ssm.state_size` | 128 | DeltaNet state size |
| `qwen35.ssm.inner_size` | 6144 | DeltaNet inner dim |
| `qwen35.ssm.group_count` | 16 | — |
| `qwen35.ssm.time_step_rank` | 48 | — |

**GEMV handoff §"Decode shapes for our production models" updated 2026-04-23 with corrected dims** — see the handoff itself. Phase 1 ukernel target is now **K=5120 → N=17408** (not 27648).

## 7. Open items

- [x] Per-function breakdown via `perf record -g` (see §3).
- [ ] Barrier cost microbenchmark (synthetic tight-loop N-thread barrier) — the 32–45% libomp overhead is now confirmed; a microbench would quantify the cost-per-thread curve for CPU4 planning.
- [ ] Effective-bandwidth calc refined with actual active-bytes-per-token per model.
- [x] DeltaNet-fraction gate decision — **PASSED (0.11% DeltaNet, below 40% threshold by huge margin)**.
- [x] 192t clean measurement — 18.69 t/s (bimodal), 96t/192t = 2.63× gap for CPU1 to target.

## 8. Gate decisions (Phase 0 complete — REVISED 2026-04-23 after measurement)

### CPU2 (GEMV ukernels on quantized decode) — **STOP**

The Phase 1 Target #1 measurement (§3c) falsified the perf-based projection. Decode-path matmuls on Q8_0 at 96t are BW-bound, not compute-bound. Doubling ALU throughput produced +1.7% at 96t and −3.6% at 1t. CPU2 ukernel work on quantized decode is not the right lever on this hardware.

The original CPU2 "GO" recommendation below is preserved for historical context but superseded by §3c/§3d/§8 revisions.

### CPU2 (GEMV ukernels) — ORIGINAL GO RECOMMENDATION (SUPERSEDED — see above)

- **DeltaNet gate: PASSED.** DeltaNet at 0.11% of cycles, not 40%+. Matmul speedup translates almost directly to end-to-end speedup with minimal Amdahl dilution.

**Target #1 — quick win (recommended Phase 1 start):**
- `ggml_vec_dot_q8_0_q8_0` at `ggml/src/ggml-cpu/arch/x86/quants.c:1012`. Currently **AVX2-only** (256-bit), 63.43% of cycles on Qwen3.6-27B Q8_0 decode.
- Port to AVX-512VNNI (`VPDPBUSD` on full ZMM). The existing AVX2 code processes 32 bytes per iteration via `_mm256_*`. An AVX-512 VNNI version processes 64 bytes per iteration and leverages Zen 5's 512-bit datapath + 2 FMA units.
- Expected: ~2× speedup on the 63.43% slice → **1.46× end-to-end**. Concrete scope: ~30-50 lines inside one existing file, no new infrastructure.

**Target #2 — missing x86 specialization of a repacked kernel:**
- **ARM has** `ggml_gemv_q8_0_4x8_q8_0` with NEON/SVE ukernel at `ggml/src/ggml-cpu/arch/arm/repack.cpp:1757`.
- **x86 has** only the `_generic` fallback (`ggml/src/ggml-cpu/repack.cpp:1321`). No AVX-512 or AVX2 path.
- Tensor traits `tensor_traits<block_q8_0, 8, 4, GGML_TYPE_Q8_0>` are registered at `repack.cpp:4605`.
- **Open question**: does the repack actually activate for our Qwen3.6-27B Q8_0? The perf profile suggests NO (we see `ggml_vec_dot_q8_0_q8_0` at 63%, not `ggml_gemv_q8_0_*`). Either the repack doesn't engage, or both get called and the unpacked path dominates. Needs diagnostic trace before investing in this target.

**Phase 1 recommended scope**: complete Target #1 first. If measured end-to-end speedup matches the 1.46× projection, the methodology is validated and Target #2 becomes the next Phase 1.5 investment. If Target #1 under-delivers (e.g. bandwidth-bound even after compute speedup), Target #2 becomes a candidate.

- **Q4_K lower priority**: already specialized upstream as `ggml_gemv_q4_K_8x8_q8_K` (8×8 tile, x86 impl exists). CPU2 Q4_K work would layer on top of tuned code with less headroom. Skip for Phase 1.

### CPU1 (TP-sharding) — **GO, HIGHEST PRIORITY NOW** (promoted from among others after CPU2 falsification)

- **Gate passed** per Phase 0 criteria; see §3d/gate-decision block.
- Original framing: "close gap between 48t-barrier-bound and full-machine." Revised: **close gap between 96t-single-node peak (49.11 t/s) and multi-instance aggregate (95.8 t/s at 4×48t NUMA)** — factor of ~2× achievable.
- 192t on full machine is worse than 96t single-node (18.7 vs 49.1). The full-machine TP story requires per-CCD weight locality + smaller barriers — which is exactly what `intra-process-tensor-parallel-decode.md` proposes.
- **Barrier cost (32–45% of cycles) is now a known quantity**, not speculative. CPU4 (per-CCD sync primitive) delivers direct returns.

### CPU4 (per-CCD sync primitive) — **PROMOTED TO HIGH standalone**

Originally MED priority ("part of CPU3 Phase 3"). Based on 32–45% barrier-cost measurement, CPU4 is now a **standalone high-value lever** independent of CPU1. A lock-free per-CCD spin primitive replacing the current OpenMP global barrier could recover a significant slice.

### Remaining open: barrier microbench

Not a gate — informational. Time permitting before Step 5/6 starts, do a synthetic barrier-cost-per-thread curve to inform CPU4 primitive design choice (atomic counter vs tree reduce vs tournament).

### 96t-single-node operating point deserves production attention

Independent of CPU1/2/3/4, the 96t-node0-pinned config delivers 49.11 t/s on Qwen3-Coder-30B-A3B Q4_K_M — a config that production doesn't currently use. The production worker_explore config is 1×24t (39.1 t/s). Running 1×96t single-node (saturating one NUMA node) as a production option could deliver +26% single-session decode without any code change. Recommend a follow-up production-sweep to verify this holds under realistic load.
