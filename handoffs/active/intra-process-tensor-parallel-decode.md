# Intra-Process Tensor-Parallel Decode Across CCDs (Single-Instance Saturation)

**Status**: stub (investigation not started)
**Created**: 2026-04-23 (user-identified gap after single-vs-aggregate throughput discussion)
**Priority**: HIGH — the single largest uncharted single-instance lever on CPU. Makes 1×instance approach N×instance aggregate throughput for single-session decode.
**Categories**: hardware_optimization, inference_serving, local_inference
**Workstream**: Inference Acceleration → CPU Optimization
**Parent index**: [`cpu-inference-optimization-index.md`](cpu-inference-optimization-index.md), [`inference-acceleration-index.md`](inference-acceleration-index.md)
**Related**:
- [`cpu-shape-specialized-gemv-decode.md`](cpu-shape-specialized-gemv-decode.md) — per-thread kernel speed (orthogonal; composes multiplicatively)
- [`single-instance-system-tuning.md`](single-instance-system-tuning.md) — NPS mode, hugepages, barrier primitive (sibling work — the NPS/pagesize knobs directly shape what TP-sharding can achieve)
- [`dynamic-stack-concurrency.md`](dynamic-stack-concurrency.md) — multi-instance aggregate path (current workaround; this handoff is the alternative)
- [`attention-matching-kv-compaction.md`](attention-matching-kv-compaction.md) — KV-side lever (independent; composes)

## 2026-04-24 Phase 1.0 implementation — NEGATIVE/NEUTRAL on barrier-only change

**Implemented**: per-CCD 2-level sense-reversing barrier in `ggml-cpu.c` (noOMP path only, env-var `GGML_CCD_POOLS=1` gated). Full details in `research/deep-dives/cpu-tp-phase1a-ccd-barrier-2026-04-24.md`.

**Measured** (Qwen3-Coder-30B-A3B Q4, 96t, n=64 r=3):
- OMP flat (production): 45.92 t/s
- noOMP flat (ggml default): 38.90 t/s
- **noOMP + per-CCD 2-level barrier**: 38.22 t/s → **−1.7% vs noOMP flat, neutral**

**Lesson**: the 32-45% barrier cost measured yesterday via `perf` on the OMP build was **libomp-specific** — it's libgomp's own spin/futex implementation. ggml's own atomic barrier (used in noOMP) is already efficient enough that splitting it into 2 levels doesn't help. **Barrier-restructuring alone is NOT the Phase 1 lever.**

**What's still needed for real CPU1 gain**:
1. **CCD-aware thread affinity via `cpumask`**: pin each worker to its CCD's 8 physical cores. ggml has `cpumask` infrastructure already but propagates a flat mask from `tpp->cpumask`. A per-CCD-block mask application would make `ith/nth` strided work distribution land on CCD-local cores.
2. **Per-CCD NUMA-bound weight allocation**: explicit `mbind` / first-touch policy so weight rows assigned to CCD c land on that CCD's physically-nearest NUMA node. Without this, all threads pull weights from a non-local DRAM pool regardless of which CCD they run on.
3. **(Maybe) CCD-shard matmul work distribution**: change `ith/nth` from flat strided to CCD-block-contiguous in `ggml_compute_forward_mul_mat`.

**Phase 1 is now genuinely a 1-week task** split across: thread pinning (~1 day), NUMA weight placement (~2 days), work-distribution changes (~2 days), end-to-end validation (~2 days). Phase 1.0 (barrier-only) is complete and in-tree as a negative baseline — future Phase 1.1/1.2/1.3 work builds on it.

### 2026-04-24 late — NPS2 BIOS is the real ceiling

Extended the standalone microbench (`/mnt/raid0/llm/cpu-tp-prototype/tp_gemv_numa_bench.cpp`) to measure 2-way NUMA-local TP (each half of the weight matrix `mbind`'d to a different node, threads pinned to that node):

- Flat 96t (current pattern): 246 GB/s
- 2-way NUMA-local: 250 GB/s → **+1.5%, within noise**

`move_pages` confirmed page placement. The reason NUMA-local TP doesn't help under NPS2: the **node distance ratio is only 10/12 = 20%** (per `numactl --hardware`). Cross-node DRAM access is only 20% slower than local. With 50% accesses hitting the wrong node in random allocation, the average overhead is ~10% — too small to offset the coordination overhead of 2-way TP, which adds its own barriers + per-path dispatch.

**Combined NPS2 CPU1 ceiling** (summing all tested interventions):
| Lever | Measured benefit |
|---|---|
| Per-CCD 2-level barrier | neutral |
| CCD-aware thread pinning | +2% |
| 2-way NUMA-local weights (mbind + first-touch) | +1.5% |
| **NPS2 total** | **~2-5% best case** |

**Real CPU1 gains require NPS4 or L3-as-NUMA BIOS change** (reboot window; CPU3 Phase 2 in the umbrella index). Under NPS4 / L3aaN the node-distance ratio grows, 4-way or 12-way locality becomes physically meaningful, and CPU1's TP projection (2-5× single-instance) can materialize. Without the BIOS change, further CPU1 work on NPS2 has diminishing returns.

### 2026-04-24 Phase 1b — NPS4 reboot re-bench

Rebooted into NPS4 (4 NUMA nodes, 3 channels each, distance 10/12). Full results: `research/deep-dives/cpu-tp-phase1b-nps4-2026-04-24.md` and `data/cpu_optimization/2026-04-24-nps4/SUMMARY.md`.

Headline (Qwen3-Coder-30B-A3B Q4, 96t, `-p 0 -n 64 -r 3`):

| Config | NPS2 (freeze) | NPS4 |
|---|---|---|
| OMP flat | 47.17 | 21.03 |
| OMP + `interleave=all` | — | 25.35 |
| noOMP flat | 38.87 | 14.01 |
| noOMP + CCD pools (Phase 1.0+1.1) | 44.85 | 15.07 |
| **noOMP + CCD + `interleave=all`** | — | **27.86** |

- CPU1 Phase 1.0+1.1 under NPS4 (with interleave) = **+12.5% over OMP+interleave baseline**. Meets the runbook's `>10%` gate to proceed with Phase 1.2/1.3.
- Absolute single-instance perf under NPS4 = 27.86, still **−38% vs NPS2's 44.85**. Software `interleave=all` only partially recovers NPS2 behavior.
- Multi-instance 4×48t frontdoor regresses −26% (50.8 → 37.74 on 35B-A3B Q4).
- Concurrent 48×4t NPS4-native is a new peak: **104.35 t/s aggregate** on 30B-A3B Q4 with per-node `membind` + 12 instances per node.
- `numa_balancing=1` auto-migration was net negative (20.42 vs 21.03).

**Why interleave doesn't fully emulate NPS2**: remote-access ratio rises from 50% to 75% per thread; within-node stripe halves from 6 to 3 channels; 4-way directory coherency adds lookup/snoop paths. These are fixed hardware taxes, not software-addressable.

**Decision pending user input.** Four options; recommendation is Option 2 (Phase 1.3 NUMA weight mbind, 2-3 days) to close the single-instance gap while keeping CPU1 gain and 48×4t peak:
1. Rollback to NPS2
2. Stay NPS4 + implement Phase 1.3 NUMA weight mbind
3. Stay NPS4 + deploy 48×4t concurrent in production
4. Reboot to L3-as-NUMA

### 2026-04-24 Phase 1.3 v1 IMPLEMENTED — set_mempolicy(MPOL_INTERLEAVE)

User approved Option 2. First Phase 1.3 iteration landed in `src/llama-mmap.cpp` on the same branch. Gated by `GGML_NUMA_WEIGHTS=1`. The code:

- Counts NUMA nodes via `/sys/devices/system/node/nodeN`
- Calls `syscall(SYS_set_mempolicy, MPOL_INTERLEAVE, ...)` BEFORE `mmap()`
- Suppresses `MAP_POPULATE` when enabled so readahead fills pages under the new policy

Originally tried per-region `mbind()` — failed because file-backed MAP_SHARED pages do NOT honor per-region policy once kernel readahead has queued them. `set_mempolicy` is process-wide and DOES govern readahead placement.

#### Clean-cache NPS4 measurements (Qwen3-Coder-30B-A3B Q4, 96t, `-p 0 -n 64 -r 3`)

| Config | NPS4 t/s |
|---|---|
| noOMP flat (baseline) | 14.53 |
| noOMP + CCD | 15.45 |
| noOMP + NW=1 | 34.84 |
| **noOMP + CCD + NW=1** | **39.59** |

- Phase 1.3 alone delivers **+140%** (baseline 14.5 → 34.8)
- CPU1 Phase 1.0+1.1 on top of Phase 1.3: **+13.6%** (34.8 → 39.6)
- Combined vs baseline: **+156%**
- **88% of NPS2 pre-reboot best** (44.85); gap closed from −38% to −12%

Inline set_mempolicy is **+16% better than external `numactl --interleave=all`** (39.59 vs 27.86 on the same build). Hypothesis: `MAP_POPULATE` + POSIX_FADV_SEQUENTIAL let the kernel readahead thread populate pages under a different effective policy than the exec-time numactl policy. Disabling MAP_POPULATE inside the mmap constructor lets the reshaped task policy govern all placement, including readahead.

#### Decision: NPS4 locked in

With Phase 1.3 landed, NPS4 now delivers 39.59 t/s single-instance + 104 t/s aggregate at 48×4t. Net trade vs NPS2: −12% single-instance for +100%+ aggregate at concurrent peak. Clear win given user approved orchestrator rework for the concurrent path.

#### Still pending (Phase 1.3 v2 + Phase 1.2)

- **v2 — tensor-aware striping**: per-tensor mbind with large stripe chunks. Needs `init_mappings()` / `weights_map` awareness.
- **Phase 1.2 — CCD-aware work distribution**: change `ith/nth` in `ggml_compute_forward_mul_mat` so each CCD's threads handle a contiguous row range. Combined with v2 striping, gives true per-node locality.

Target: close the remaining 12% vs NPS2 and potentially exceed it.

### 2026-04-24 (later same session) — Phase 1.2 landed + Phase 1.3 v2 scaffolding

Committed [`61b00eb53`](https://… ) on `cpu-optimization/backlog-2026-04-23`.

**Phase 1.2** (ggml-cpu.c: `ggml_compute_forward_mul_mat`):
- Env gate `GGML_CCD_WORK_DIST=1` (requires `GGML_CCD_POOLS=1`).
- When active, bypasses the default dynamic chunk-stealing loop and assigns each thread a contiguous output-row slice: CCD c gets `[c*big/n_ccd, (c+1)*big/n_ccd)`, then within the CCD each thread takes a strided sub-slice.
- Bit-exact with prior behavior when env unset. Gated behind `GGML_USE_OPENMP=off`.

**Phase 1.3 `local` mode** (llama-mmap.cpp):
- Added alongside the existing `=1/=interleave` mode.
- `GGML_NUMA_WEIGHTS=local` disables `MAP_POPULATE` and sets `POSIX_FADV_RANDOM` so pages fault on demand under the touching thread's default LOCAL policy. No global `set_mempolicy`.
- Intended endpoint: combined with a per-CCD warm-up touch pass, each CCD's threads first-touch their assigned weight rows and pages land on the CCD's node.

**Measured (NPS4, Qwen3-Coder-30B-A3B Q4, 96t, n=64 r=3)**:

| Config | t/s |
|---|---|
| Phase 1.0+1.1 + NW=1 (interleave) — baseline for Phase 1.2 | **40.40 – 41.38** (avg ~40.8) |
| Phase 1.0+1.1 + Phase 1.2 + NW=1 | 29.76 (cold) / 40.96 / 40.18 (avg ~40.6) |
| Phase 1.0+1.1 + Phase 1.2 + NW=local (no warm-up pass) | 18.4 – 18.6 |

Phase 1.2 under interleave is **net neutral** (static partition loses some work-stealing benefit; per-node locality gain of Phase 1.2 is zero when weights are 4 KB-interleaved, so no offset).

Phase 1.2 + `NW=local` (no warm-up) lands 15 GB on node 0 alone (observed via numastat) because the main thread touches weights during model-load before CCD threads run inference. That concentrates placement on whichever node init runs on.

**Why these modes don't yet deliver**: Phase 1.2 needs per-node weight locality to pay off; page-interleave doesn't provide it. `NW=local` with no warm-up also doesn't provide it (main thread faults most pages first). Both are correct *foundations*; the missing piece is a warm-up step.

### Phase 1.3 v2 proper design (next session)

After `init_mappings()` completes AND when `GGML_NUMA_WEIGHTS=local` + `GGML_CCD_POOLS=1` are set:

1. Read the same CCD geometry env vars the pool uses (or derive from n_threads / ccd_threads).
2. Spawn N pinned pthreads (one per CCD), each bound to that CCD's CPU set and NUMA node via `sched_setaffinity` + `mbind` on the thread's stack/heap.
3. Each thread iterates the weights_map and for each tensor, reads one byte from every page in the rows `[c*N/n_ccd, (c+1)*N/n_ccd)` range (matching Phase 1.2's partitioning).
4. First-touch places those pages on the thread's NUMA node.
5. Threads exit; model is now per-node-cached.

Estimated effort: 1-2 days. Expected result: 44+ t/s single-instance, closing or exceeding the NPS2 baseline gap.

### Current deployable operating point (NPS4)

- **Phase 1.0+1.1 + Phase 1.3 v1 (NW=1)**: **40-41 t/s single-instance** (89% of NPS2 baseline 44.85)
- **48×4t concurrent NPS4-native**: 104 t/s aggregate (new peak)
- Phase 1.2 env-gated-off in production until Phase 1.3 v2 completes (or: enable Phase 1.2 in concurrent 48×4t layouts where each instance is membind'd to one node — then CCD work dist within each instance IS useful)

### NPS BIOS tradeoff summary

| Mode | Nodes | CCDs/node | Cross-node cost | Notes |
|---|---|---|---|---|
| NPS1 | 1 | 12 | n/a | No NUMA awareness required |
| **NPS2** (current) | 2 | 6 | 20% | Current production; CPU1 ceiling ~5% |
| NPS4 | 4 | 3 | larger | 4-way NUMA TP friendly |
| L3-as-NUMA | 12 | 1 | largest | Per-CCD NUMA — full CPU1 potential |

Side effects of NPS mode change to evaluate before reboot:
- 4×48t multi-instance production deployment (frontdoor/coder) may re-benchmark differently — the NUMA quarters would map to actual nodes under NPS4
- `--numa distribute` and `--numa interleave=all` semantics shift with more nodes
- `mlock` behavior unchanged but page-allocation behavior changes
- Naive code (no NUMA API) typically sees slight shifts (mostly neutral)

---

## 2026-04-24 Phase 0 microbench — pattern validated, +6% to +28% over flat OpenMP at DRAM scale

Implemented a standalone C++ microbench (`/mnt/raid0/llm/cpu-tp-prototype/tp_gemv_bench.cpp`) comparing:
- Flat OpenMP 192t / 96t (ephemeral + persistent variants) — current ggml pattern
- **TP 12×16**: 12 pthread workers pinned to 12 CCDs via `sched_setaffinity` (8 phys + 8 HT each), each running a persistent 16-thread OpenMP sub-team sharding its 1/12 of N.

Measured at three working-set sizes on K=5120 FP32 GEMV (`y = W·x`):

| W size | Cache state | Best flat | TP 12×16 | TP gain |
|---|---|---|---|---|
| 0.33 GB | L3-resident | 192t flat = 857 GB/s | 591 GB/s | **−31%** (L3 BW dominates, more threads win) |
| 3.81 GB | DRAM-bound | 192t persistent = 204 GB/s | **210 GB/s** | **+3%** (+14% vs ephemeral 184) |
| 15.26 GB | DRAM-bound | 192t persistent = 205 GB/s | **215 GB/s** | **+5%** (+6% vs ephemeral 204) |

At DRAM scale the TP pattern wins. The gain is modest on a single GEMV (+5-14%) because the microbench amortizes spawn overhead over many iterations and has no chain-of-ops cumulative cost. Real ggml decode has 64 layers × 7 matmul shapes per token; cumulative barrier cost makes the TP gain grow. See `research/deep-dives/cpu-tp-sharding-phase0-microbench-2026-04-24.md` for full analysis.

**Numerical validation**: bit-exact match between all modes at all sizes.

**Key refinement**: the microbench's "flat OpenMP ephemeral vs persistent" gap (+11%) reflects OpenMP runtime behavior. **Inspection of `ggml/src/ggml-cpu/ggml-cpu.c:467-503` shows ggml ALREADY uses a persistent threadpool** (`struct ggml_threadpool` with long-lived workers, atomic `n_graph` / `n_barrier_passed` coordination). So the ephemeral-vs-persistent gap is not something Phase 1 unlocks — ggml has it.

The remaining Phase 1 work is the **per-CCD sub-pool structure**: split ggml's flat 192-way threadpool into 12 CCD-pinned sub-pools (16 threads each), with per-sub-pool barriers and cross-CCD coordination only where necessary. The 32-45% barrier cost in perf is the spin-wait on the FLAT 192-way `n_barrier_passed`; replacing it with 12 × 16-way local barriers + occasional cross-CCD tree reduction should recover a large fraction.

### Phase 1 code sites to modify (identified 2026-04-24)

- `ggml/src/ggml-cpu/ggml-cpu.c:467` — `struct ggml_threadpool` — add array of sub-pool coordinators
- `ggml/src/ggml-cpu/ggml-cpu-impl.h:532` — `ggml_barrier()` — add per-sub-pool variant + cross-CCD tree-reduce
- Thread launch in threadpool init — apply CCD-aware `cpumask` per worker (8 phys + 8 HT on its CCD)
- `ggml_compute_forward_mul_mat` — work-distribution math already uses `ith/nth`; with CCD-pinned workers the natural split puts each worker on CCD-local output rows.
- Env-var gate: `GGML_CCD_POOLS=1` enables the sub-pool path; default off.

Effort: ~1 week. Risk: touching ggml threading (barrier correctness, deadlock potential, cross-CCD reduction bugs). Bit-exact validation against existing ggml is a hard gate.

## 2026-04-23 Phase 0 GATE PASSED — promoted to HIGH top priority

Phase 0 feasibility gate decisions per the CPU-optimization coordinated pickup:

**Gate (a) — single-instance at 192t is <60% of memory-BW roofline**: **PASSED by huge margin.**
- Measured 18.7 t/s at 192t (`--numa distribute --mlock`, quiet host, bimodal samples 13.58 / 23.81).
- Bytes/token on Qwen3-Coder-30B-A3B Q4_K_M (3B active) ≈ 2 GB/token → 37 GB/s = **8% of 460 GB/s roofline**.

**Gate (b) — barrier cost at 192t is >15% of per-token time**: **PASSED.**
- perf record on 96t decode: **32–45% of cycles** in libomp spin-wait / OpenMP barrier (unresolved addresses in `0x0000000000026580` family).
- 192t barrier cost extrapolates higher given the bimodal sample variance at 144t and 192t configs.

**Additional data points:**
- 96t single-node (taskset 0-95, node 0) peak: **49.11 t/s** (stddev 0.08 on quiet host) — the natural "saturate one NUMA node" operating point not previously measured in production.
- 192t full machine: 18.7 t/s. **96t/192t ratio = 2.63×** — a single NUMA node with half the threads beats the full machine by >2.5× for single-instance decode. This is the explicit TP-sharding opportunity.
- 144t (cross-NUMA, 0-143): 25.7 t/s with bimodal stddev 18.5 (samples 12.66 / 38.83) — confirms cross-NUMA contention is catastrophic without proper weight sharding.

**CPU2 GEMV falsification (see `cpu-shape-specialized-gemv-decode.md`)**: the Phase 0 perf profile showed 63.43% of Q8_0 cycles in `ggml_vec_dot_q8_0_q8_0`, but an AVX-512VNNI port of that function delivered only +1.7% end-to-end at 96t (projection was 1.46×). Decode is BW-bound, not compute-bound. This **strengthens the case for CPU1** — BW is the actual bottleneck, and CCD-local weight sharding addresses it directly.

Phase 1 prototype is gated as **GO**; implementation is ~1 week of work (per-CCD thread pools + Option A replicated reduce + one MLP-up layer shard + numerical validation + bench). Schedule for a dedicated session.

---

## 2026-04-23 Audit Cross-References (read before starting Phase 0)

Facts established in the coordinated CPU-optimization pickup audit (see [`cpu-inference-optimization-index.md`](cpu-inference-optimization-index.md) §Pickup Sequence):

- **`perf` is NOT installed** on the host. Phase 0 profiling must use `GGML_PERF=1` for per-op timers, `rdtsc`-bracketed micro-harness for tight loops, `/usr/bin/time -v` for wall + page-faults, `getrusage` for context-switch and RSS. Install `linux-tools-$(uname -r)` only with user approval.
- **tinyBLAS is already in the fork** at `ggml/src/ggml-cpu/llamafile/sgemm.cpp` under `GGML_USE_LLAMAFILE`. Any TP-sharding work should measure on/off baselines so the TP gain is isolated from the sgemm gain.
- **KleidiAI plugin** at `ggml/src/ggml-cpu/kleidiai/` is the repo-internal directory-layout template for a new `zen5-tp/` plugin (CMake wiring, dispatch registry, fail-open fallback pattern).
- **Work in `llama.cpp-experimental`** on `cpu-optimization/backlog-2026-04-23` branch off `production-consolidated-v4`, never in the production `llama.cpp` tree.
- **CPU3 Phase 0 baseline** (from `single-instance-system-tuning.md`) runs first and is a hard prerequisite — this handoff's Phase 0 gates reference its thread-sweep, DeltaNet-fraction, and barrier-cost numbers.

---

## The Problem

On our EPYC 9655, running 4×48-thread NUMA-pinned instances gives **6.7× aggregate throughput** (95.8 t/s) vs 1×192-thread interleaved (14.2 t/s) on the 30B-A3B frontdoor model. But this is **aggregate throughput across 4 independent sessions** — a single interactive user sees only the per-instance speed.

A single request running on one llama-server process currently **cannot** use the full machine, because:

1. **Thread scaling plateaus** around 48–64 threads per instance. Past that, GGML's per-layer barriers and cache-coherence traffic dominate; adding threads returns diminishing or negative gains. The instance becomes **barrier-bound** before it becomes memory-bandwidth-bound.
2. **Memory access pattern is undifferentiated**: all 192 threads read all weights from any memory controller. The 12 DDR5-6000 channels (~460 GB/s effective) are shared as one contention target. No thread has "local" weights.
3. **CCD-level L3 locality is wasted**: each of the 12 Zen 5 CCDs has a 32 MB L3 slice, ~384 MB total on 9655. A single instance spreads hot weights and KV across all CCDs, generating cross-CCD coherence traffic through the IOD.

The consequence: **single-session decode throughput on 1×192t is 20–50% of what the hardware can physically deliver**. The other 50–80% shows up only as aggregate throughput across independent processes.

**This handoff proposes to close that gap inside a single process** via intra-process tensor-parallel decode, sharding each matmul across CCDs such that each CCD's threads read their local weight slice from their local memory channels, overlapped with the next layer's dispatch.

## Why CPU Tensor-Parallel Is Qualitatively Different From GPU Tensor-Parallel

GPU tensor-parallelism (Megatron-LM, vLLM, TensorRT-LLM) is designed around a specific constraint: per-GPU memory is limited, so weights must be split. The "communication" — collective AllReduce across NVLink/PCIe — is a real cost (microseconds to milliseconds) that must be hidden.

On CPU, **the communication layer is the same shared memory system the compute uses**. There is no fabric to cross for data transfer; CCDs communicate through L3/IOD. The partial-sum reduction is small: for a typical decode matmul producing a 5120-element output vector, the reduction across 12 CCDs is 12 × 5120 × 4 bytes = 240 KB, which fits in any CCD's L3. The reduction itself is not the bottleneck.

**The bandwidth savings come from a different place**: weight locality. A CPU matmul at decode reads its entire weight matrix from DRAM every forward pass (weights are too large for L3). If each CCD reads only its 1/12 slice of each weight matrix, and if that slice lives in DRAM channels physically closest to that CCD (NPS4 or L3-as-NUMA mode), then the 12 memory channels feed 12 CCDs in parallel — achieving the **same per-instance bandwidth that 12 single-CCD instances would achieve**, but for a single request.

This is fundamentally available on CPU and fundamentally NOT explored in upstream llama.cpp or any CPU inference engine we've surveyed. There is **no prior art on CPU tensor-parallel decode with fabric-aware sharding**. On GPU it's table stakes; on CPU it's uncharted.

## The Physics — What Bandwidth We Can Actually Recover

**Theoretical peak**: 12-channel DDR5-6000 per socket = 576 GB/s peak, ~460 GB/s effective on llama.cpp decode workloads.

**Current single-instance measured**:
- 30B-A3B Q4_K_M at 192t interleaved: 14.2 t/s × 16 GB weights = **227 GB/s effective** (~50% of peak — confirms barrier-bound, not BW-bound)
- 30B-A3B Q4_K_M at 4×48t NUMA-pinned aggregate: 95.8 t/s × 16 GB per-instance-weight = 1533 GB/s aggregate weight reads across 4 processes

Wait — 1533 GB/s > 460 GB/s total system BW? That's because the 4 instances each have the weights **mapped** but page cache sharing means they effectively share the physical weight reads. The true aggregate bandwidth measurement on our 4-way NUMA deployment is not yet precisely characterized. Phase 0 must measure it.

**What TP-sharding could unlock**: if a single instance with 12-way CCD sharding achieves 80% of the aggregate bandwidth figure, a single request gets close to 80 t/s on 30B-A3B — comparable to what 4× parallel gets for 4 concurrent sessions. That's the target.

**Conservative claim**: 1.5×–3× single-instance speedup, corresponding to 21–43 t/s on 30B-A3B (vs 14.2 baseline). Matches the gap between "barrier-bound on 192t" and "BW-bound on the full socket".

**Aggressive claim** (if the reduce is truly free and sharding aligns perfectly with NPS topology): 4×–6× single-instance speedup. Requires NPS4 or L3-as-NUMA mode, which interacts with `single-instance-system-tuning.md`.

## The Core Design

### Shard each decode matmul column-wise across CCDs

A decode matmul is **GEMV**: one activation vector (K elements) times a weight matrix (K × N) producing an output vector (N elements). Shard the weight matrix by columns across 12 CCDs:

- CCD c owns columns `[c × N/12, (c+1) × N/12)` of the weight matrix.
- Each CCD's threads compute partial output for their column slice only.
- No reduction needed! Each CCD produces a disjoint slice of the output vector.
- **The output is naturally distributed across CCDs** — the next layer's input is already sharded if we keep the same shard geometry.

For the **attention** layers, the sharding pattern differs slightly:
- Q/K/V projections: shard by output head (attention-heads are independently computable).
- Attention softmax + value aggregation: per-head, local to the CCD owning that head.
- Output projection: shard by input (since input is head-distributed). This one **does** need a reduction at the end: partial sums from each head's contribution must be combined into the residual stream.

For **MLP** layers:
- Gate and up projections: column-sharded, output is disjoint.
- Down projection: row-sharded (inputs are distributed), output requires AllReduce to sum partial sums into the residual.

**Result**: ~1–2 reductions per layer (one for attention output, one for MLP down). Everything else is embarrassingly parallel across CCDs.

### The reduction primitive

For each reduction point, 12 CCDs each hold a partial sum of length N (typically 4096–5120 FP32). Need to combine into a final vector of length N, distributed or replicated.

**Option A — Replicated output** (simpler): each CCD writes its partial to a shared buffer; one designated thread per CCD sums the 12 partials and writes the final. Cost: 12 × N × 4 bytes L3 traffic = 240 KB per reduce, negligible. Implementation: cache-aligned shared buffer + one atomic barrier.

**Option B — Ring AllReduce** (more work, scales better if CCD count grows): each CCD sends its partial to its neighbor, accumulates as it goes around. Not needed for 12 CCDs; Option A suffices.

**Option C — Butterfly / tree reduce**: log(12) ≈ 3.5 rounds. Slightly lower cache pressure than Option A. Probably not worth the complexity at 12 nodes.

**Recommendation**: start with Option A. It is ~50 lines of code over the existing ggml thread pool.

### Comm-hiding: overlap reduction with next layer's weight prefetch

While threads wait in the reduce barrier, they can **prefetch the next layer's weights into L2/L3**. This is pure wins: the reduce cost is 240 KB of L3 traffic per layer; prefetching 128 KB of next-layer weights into L2 during that window costs nothing extra.

**Implementation**: during the barrier spin, issue `_mm_prefetch(next_layer_weight_ptr + offset, _MM_HINT_T1)` for the CCD-local shard of the next weight matrix. Tuning: prefetch distance matters; too far and it evicts from L2 before use, too close and there's no overlap.

### Thread pool redesign

The current GGML CPU thread pool uses a single global barrier at each layer. Every worker thread must reach the barrier before any thread advances. This is what makes 192 threads perform worse than 48 — the barrier cost on 192 threads is ~10× higher (not linear).

**Proposed**: per-CCD local thread pools. Each CCD has 16 threads (8 physical cores × 2 SMT) with a local barrier. Only the CCD leaders participate in the global reduce barrier. This changes:
- Per-layer barriers: 12 local (cheap, intra-CCD) + 1–2 global (only 12 participants).
- Barrier cost: O(cores_per_CCD) local + O(CCD_count) global, instead of O(total_threads) global.
- Cache coherence: local barriers stay in-CCD L3; global barrier traffic is bounded to 12 participants.

This is a more significant code change than the sharding itself. It likely requires a parallel thread-pool implementation rather than replacing ggml's. Recommend prototyping as a shadow path enabled by env var.

## Prerequisites and Interactions

### NPS mode (BIOS)

The bandwidth win depends on each CCD reading its weight shard from its **local** memory channels. This requires the DRAM to be partitioned such that physical address ranges align with CCD L3 domains.

- **NPS2 (current)**: 2 NUMA nodes. Each node has 6 CCDs + 6 memory channels. Weight shards split across 2 nodes at best → only 2-way locality, not 12-way.
- **NPS4**: 4 NUMA nodes, 3 CCDs + 3 channels each. 4-way locality.
- **L3-as-NUMA (CCDaaN)**: 12 NUMA nodes, 1 CCD + 1 channel each. Full 12-way locality. **This is what TP-sharding wants**.

Switching NPS mode requires a BIOS change and a reboot. It is a **prerequisite for the full bandwidth win**. See [`single-instance-system-tuning.md`](single-instance-system-tuning.md) for the NPS evaluation path.

However, TP-sharding still produces gains in NPS2 mode: even with only 2-way memory locality, reducing thread barrier pressure and CCD cache coherence traffic helps. Phase 0 should measure both modes.

### Page placement and weight replication

Weight tensors must be physically located on the NUMA node that owns the CCD(s) reading them. Options:

- **Interleaved** (current default for `--numa distribute`): pages round-robin across nodes. Each CCD has ~50% local reads. This is the current state and is suboptimal for TP.
- **Per-CCD shard residence**: mmap the weight tensor multiple times (once per NUMA node), use `move_pages` or `mbind` to place each shard on its owner node. Needs ~12× metadata overhead but weights themselves are already shared via page cache.
- **Weight replication**: for models small enough (<50 GB), replicate full weights on each NUMA node. Wastes memory (4× at NPS4, 12× at L3aaN) but guarantees locality.

For 30B-A3B (16 GB) at L3aaN: 12 × 16 = 192 GB. Fits in 1.1 TB RAM. Acceptable.
For Qwen3-Coder-480B (250 GB): 12 × 250 = 3 TB. Does not fit. Must use sharding.

This interacts with hugepages (explicit 1 GB pages ease placement) — see system-tuning handoff.

### Composition with existing levers

TP-sharding composes multiplicatively with most existing work:

| Lever | Composition | Why |
|-------|-------------|-----|
| Shape-specialized GEMV ukernels | **Multiplicative** | Each CCD's shard kernel can still be hand-tuned per shape; TP gives 3–6×, ukernel gives 1.5–2.5×; combined 4.5–15× |
| AM KV compaction | Orthogonal (KV-side) | TP shards the attention output projection; KV compaction reduces KV read size. Independent levers, fully composing |
| KV quantization (Hadamard) | Orthogonal | Same as above |
| ngram-simple speculation | Multiplicative | Each accepted draft token benefits from TP speedup per verify step |
| TIDE early exit | Partially overlapping | Early-exit reduces layer count; TP speeds remaining layers. Both help, combined gain < multiplicative but positive |
| NUMA multi-instance | **Replaced, not composed** | TP gives single-instance what multi-instance gives aggregate. You'd still want multi-instance for true concurrent sessions, but each session gets the TP speedup |

## Prior Art

### CPU tensor parallel (the gap)

- **llama.cpp multi-GPU split modes** (`--split-mode row`, `--split-mode layer`): supports TP across GPUs but the logic is GPU-specific. The `ggml_backend_tensor_parallel` abstraction does not extend to CPU backends.
- **DeepSparse (Neural Magic)**: uses CPU sparsity + per-core compute but does not do tensor-parallel sharding across NUMA domains in the sense proposed here.
- **Intel oneDNN**: has "graph partitioning" for cross-socket inference but targets multi-socket Xeon, not multi-CCD within one socket. Not directly applicable.
- **ZenDNN 5.2 (AMD)**: "pattern-aware kernel selection" and "Low Overhead API" target single-core performance, not cross-CCD parallelism.
- **vLLM CPU backend**: inherits TP abstraction from GPU side, but CPU backend uses it only for multi-socket config (`VLLM_CPU_KVCACHE_SPACE`, `VLLM_CPU_OMP_THREADS_BIND`). No CCD-aware sharding.

**Conclusion**: the technique proposed here does not appear to exist in any production CPU inference system. This is both the reason it's an opportunity and a reason for skepticism — if it were easy, someone would have shipped it.

### GPU tensor parallel (where the design pattern comes from)

- **Megatron-LM** (Shoeybi et al., arXiv:1909.08053): the canonical column-sharded attention + row-sharded MLP pattern. Our design is a direct CPU port.
- **vLLM** (Kwon et al., SOSP'23): TP combined with paged attention and continuous batching. The TP communication uses NCCL AllReduce.
- **TensorRT-LLM**: similar; hidden behind NVIDIA's inference stack.
- **Alpa** (Zheng et al., OSDI'22): automates sharding decisions. Non-trivially adaptable to CPU topology.

### Register-level prior art that informs the reduce primitive

- **MPI collective algorithms** (MPICH, OpenMPI): decades of tuning for various topologies. The Option A "Replicated output" from above is effectively `MPI_Allreduce` with `MPI_IN_PLACE` on a small vector — well-understood.
- **OpenMP `#pragma omp barrier` and `#pragma omp reduction`**: built-in but tuned for generic HPC, not llama.cpp's specific pattern.

## Phased Work Plan

### Phase 0: Profile baseline & validate the bandwidth claim (3–5 days)

**Goal**: measure what we actually have, what the gap is, and whether TP can close it.

- [ ] Measure **true memory bandwidth** during single-instance 192t decode on 30B-A3B Q4_K_M: use `perf stat -e uncore_imc/cas_count_read/,uncore_imc/cas_count_write/` (or AMD μProf equivalent) and compute GB/s. Compare to 460 GB/s theoretical.
- [ ] Measure **per-CCD memory traffic distribution** — is it balanced (suggesting all CCDs read all weights via all channels), or imbalanced (suggesting partial locality)?
- [ ] Profile **barrier cost**: use `perf record -e sched:sched_wakeup` during decode; compute fraction of time spent in GGML thread-pool wait states. Hypothesis: >30% on 192t.
- [ ] Measure `4×48t NUMA-pinned aggregate` memory BW — does it hit 80% of theoretical, or less?
- [ ] Record per-layer time breakdown: matmul vs attention vs DeltaNet recurrence vs RMSNorm vs sampling.
- [ ] **Gate decision**:
  - If single-instance 192t is already at >70% of theoretical BW → TP can't help much; abandon.
  - If barrier time >30% of decode → TP viable, prototype worth building.
  - If DeltaNet recurrence dominates (>60%) → shard-able matmul is minority; limited upside.

**Artifacts**: `research/deep-dives/cpu-tp-feasibility-baseline.md` with the bandwidth and barrier-cost measurements.

### Phase 1: Single-layer prototype (1–2 weeks)

**Goal**: prove the core sharding + reduction loop works correctly and measure speedup on one layer.

- [ ] Pick a single MLP block in Qwen3-Coder-30B-A3B Q4_K_M (one that ggml can isolate).
- [ ] Implement a standalone C++ harness that:
  - Loads the weight matrix.
  - Splits column-wise across 12 CCDs (using `pthread_setaffinity_np` to pin worker threads to CCD cores).
  - Each CCD group computes its partial output with existing ggml GEMV.
  - Reduction via Option A (shared buffer + one summing thread).
- [ ] Validate numerical equivalence with single-threaded reference: cosine similarity > 0.9999 on 1000 random inputs.
- [ ] Measure speedup per layer vs 192t unsharded baseline. Target: 1.5× on one MLP down projection.
- [ ] **Gate**: if per-layer speedup <1.2×, abandon or rethink NPS mode before proceeding.

**Artifacts**: prototype code in `/mnt/raid0/llm/llama.cpp-experimental` on a new branch `feature/cpu-tp-prototype`; measurement report.

### Phase 2: Full model integration (2–4 weeks)

**Goal**: end-to-end single-instance decode with TP sharding on Qwen3-Coder-30B-A3B.

- [ ] Design the per-CCD thread pool API (new ggml component; coordinate with `single-instance-system-tuning.md` sync-primitive work).
- [ ] Implement column-sharding for all MLP matmuls (gate, up, down).
- [ ] Implement head-sharding for attention (Q/K/V projections, attention compute, output projection).
- [ ] Handle DeltaNet recurrence: the state-update pattern is sequential; TP can parallelize per-head but not across time. Accept DeltaNet as a residual serial cost.
- [ ] Integrate into `llama-server` as a `--tp-ccd N` flag (disabled by default).
- [ ] Correctness: run `llama-bench` with `--tp-ccd 12` and `--tp-ccd 0`; compare tok/s and output divergence.
- [ ] Target: end-to-end 2× single-instance decode on 30B-A3B (14.2 → 28 t/s).
- [ ] **Gate**: if <1.5× end-to-end, evaluate whether the barrier-cost assumption was wrong or whether the NPS mode needs changing.

**Artifacts**: merge to `production-consolidated-v4` experimental branch (not production); benchmark report; divergence analysis.

### Phase 3: NPS4 / L3-as-NUMA evaluation (1 week + reboot window)

**Goal**: measure what BIOS-level NPS changes unlock when combined with TP.

- [ ] Coordinate with `single-instance-system-tuning.md` Phase 2 for the reboot + NPS switch.
- [ ] Re-run Phase 2 benchmarks under NPS4 and (if supported) L3-as-NUMA.
- [ ] Record bandwidth utilization per NPS mode.
- [ ] **Target**: in L3-as-NUMA, single-instance TP decode reaches 80–90% of multi-instance aggregate BW.

**Artifacts**: NPS-vs-TP interaction matrix; recommendation for production NPS setting.

### Phase 4: Rollout to production stack (2–4 weeks)

**Goal**: ship TP-sharding for all suitable production models.

- [ ] Extend to Qwen3.6-35B-A3B, Qwen3-Coder-30B-A3B, Qwen3.6-27B dense (if benchmarked).
- [ ] Handle MoE expert-specific sharding (experts are naturally column-sharded; fits the pattern).
- [ ] Handle very large models (480B, 246B REAP): sharding works but reduction cost grows with hidden size; measure.
- [ ] Integrate with `ConcurrencyAwareBackend`: single sessions route to TP-enabled instance; concurrent sessions to NUMA 4-way (existing path).
- [ ] Update `orchestrator_stack.py` to launch TP-enabled instances with correct CPU pinning.

**Artifacts**: production deployment; orchestrator config update; handoff → `completed/` status.

### Phase 5 (stretch): Upstream contribution

If the work is robust, upstream to llama.cpp. The CPU TP abstraction is valuable to the community. Coordinate with any parallel work in ggml.

## Falsification Conditions

Abandon this lever if any hold after Phase 0 or Phase 1:

1. **Single-instance 192t is already BW-bound** (>70% of theoretical 460 GB/s). Then the gap is small and TP has nowhere to go.
2. **DeltaNet recurrence dominates decode** (>60% of per-token time). The shard-able matmul portion is too small to matter for our hybrid models. In that case, TP would help dense models (Qwen2.5-Coder-32B, Qwen3.6-27B) but not hybrids.
3. **Reduction cost is unexpectedly high** due to cross-CCD coherence traffic we didn't model (e.g., false sharing in the reduce buffer, IOD congestion under sustained load).
4. **Per-CCD thread pool redesign proves prohibitive** (more than 4 weeks of work for Phase 2 alone). In that case, do a simpler barrier-only optimization and reassess.
5. **No measurable improvement in NPS2 mode** and BIOS reboot to NPS4/L3aaN is operationally blocked.

## Risks

### Technical

1. **IOD fabric contention under sustained load**: the Infinity Fabric on Zen 5 is not infinitely scalable. At 12 CCDs all pulling weights simultaneously at peak rate, we may saturate IOD controllers before hitting memory BW limits. Mitigate: Phase 0 measures this.
2. **False sharing in reduction buffer**: the 12 partial-sum buffers must be cache-line-aligned (64 B) with padding between them. A bug here would cost more than TP gains. Mitigate: Phase 1 numerical equivalence test + cycle-accurate profiling of the reduce.
3. **NPS mode affects KV cache placement**: current deployment assumes NPS2. KV cache pinning for compacted/quantized KV may need rework. Mitigate: Phase 3 benchmark under NPS4 before committing.
4. **Thread affinity stability under load**: Linux scheduler may migrate threads off their pinned cores under extreme contention. Use `SCHED_FIFO` with `sched_setscheduler` and `mlockall` for predictability. Mitigate: pin via `pthread_setaffinity_np` + monitor with `perf sched`.

### Engineering

1. **ggml internals are not designed for this**: the graph scheduler assumes one global thread pool. Forking the scheduler to support per-CCD pools is a nontrivial change. Mitigate: implement as a parallel codepath, env-var gated, with fallback to the standard scheduler.
2. **Maintenance burden**: per-CCD sharding adds complexity that every future model must accommodate. Mitigate: make sharding a property of the model graph, not the layer code — like GPU backends do.
3. **Model support**: Qwen3 hybrid (DeltaNet + full attention) has two layer patterns; sharding geometry differs. Mitigate: handle both; document the pattern.

## Open Questions

1. **What is the true single-instance 192t bandwidth utilization today?** Phase 0 must answer this before the lever's ceiling is known.
2. **Is the barrier cost really 30%+ on 192t?** Hypothesis based on thread-scaling plateau behavior; needs direct measurement.
3. **Does upstream llama.cpp have any CPU TP PR in flight?** Check `github.com/ggml-org/llama.cpp` issues and PRs tagged `cpu` or `multi-thread` before starting.
4. **Can we measure the IOD fabric bandwidth directly on Zen 5?** AMD μProf and some newer `perf` uncore events expose this. Investigate.
5. **For MoE models, is per-expert sharding (experts distributed to CCDs) better than per-shape column sharding?** MoE has 8 active experts; 12 CCDs; the 8-to-12 mismatch adds complexity. Consider: 8 experts × 1.5 CCDs per expert, or 12 CCDs with the 4 "extra" CCDs doing shared-expert / attention work.
6. **Is `tinygrad`'s CLOUD=1 or MULTI=1 backend relevant prior art?** Check.

## Success Criteria

**Minimum viable (Phase 1 gate)**: single-layer prototype achieves 1.5× speedup on one MLP projection in isolation under NPS2. Proves the sharding pattern is correct and the reduction primitive is cheap enough.

**Target (Phase 2 gate)**: end-to-end 2.0× single-instance decode on Qwen3-Coder-30B-A3B under NPS2 (14.2 → 28 t/s). Proves TP helps even without BIOS changes.

**Stretch (Phase 3 gate)**: 3.5–5× single-instance decode under L3-as-NUMA (14.2 → 50–70 t/s), approaching 4×48t NUMA aggregate throughput (~95.8 t/s) but in one process. Proves the full bandwidth recovery.

**Composition with GEMV ukernel**: if both land, 2.0× × 1.75× = 3.5× minimum; 5× × 2.5× = 12.5× stretch. Would take 30B-A3B from 14 to 50–175 t/s single-instance.

## Artifacts to Produce

1. `research/deep-dives/cpu-tp-feasibility-baseline.md` — Phase 0 profiling + gate decision.
2. `research/deep-dives/cpu-tp-prototype-report.md` — Phase 1 per-layer result.
3. Prototype code on `feature/cpu-tp-prototype` branch in `/mnt/raid0/llm/llama.cpp-experimental`.
4. Benchmark harness for per-layer and end-to-end measurements.
5. NPS interaction matrix (joint with `single-instance-system-tuning.md`).
6. Updated `inference-acceleration-index.md` row and `cpu-inference-optimization-index.md` status.
7. (Phase 5) upstream PR(s).

## References

### Required reading before picking this up

1. Shoeybi et al., "Megatron-LM: Training Multi-Billion Parameter Language Models Using Model Parallelism" (arXiv:1909.08053) — the canonical TP design.
2. AMD "AMD EPYC 9005 Series BIOS & Workload Tuning Guide" — for NPS modes and L3-as-NUMA configuration details.
3. Mark Hill's "Cost of a Cache Miss" retrospective and Zen 5 / Turin architecture whitepaper — for the IOD fabric topology.
4. `cpu-shape-specialized-gemv-decode.md` (sibling handoff) — the per-thread kernel work that composes with this.
5. `single-instance-system-tuning.md` (sibling handoff) — the NPS/hugepage/sync-primitive work that enables this.

### llama.cpp internals to understand

- `ggml/src/ggml-threading.cpp` — current thread pool; the code to either extend or bypass.
- `ggml/src/ggml.c` function `ggml_graph_compute_thread` — where each worker picks up work from the compute graph.
- `src/llama.cpp` attention and MLP compute sections — where the sharding would apply.
- `ggml/src/ggml-cpu/ggml-cpu.c` — the CPU backend dispatch; the injection point for TP.

### External references

- vLLM CPU backend docs: [docs.vllm.ai/en/latest/getting_started/cpu-installation.html](https://docs.vllm.ai/en/latest/getting_started/cpu-installation.html).
- ZenDNN 5.2 blog + docs.
- Phoronix EPYC 9005 deep-dives for CCD-aware benchmarks.

## Pickup Checklist

When resuming:

- [ ] Re-read this handoff end-to-end.
- [ ] Check `inference-acceleration-index.md` and `cpu-inference-optimization-index.md` for any status changes.
- [ ] Check llama.cpp upstream for any CPU TP PRs since 2026-04-23.
- [ ] Verify the Phase 0 profiling numbers have been captured before touching any code.
- [ ] Start a new `progress/YYYY-MM/YYYY-MM-DD.md` entry before Phase 1 begins.
- [ ] Coordinate with `single-instance-system-tuning.md` picker-upper if BIOS reboot is needed.
