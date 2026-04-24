# CPU1 Phase 1.0 — Per-CCD 2-level Barrier in ggml (Negative Result, 2026-04-24)

**Parent handoff**: `handoffs/active/intra-process-tensor-parallel-decode.md` (CPU1)
**Scope**: Restructure ggml's flat atomic barrier into a 2-level per-CCD barrier in the **no-OpenMP** compile path. Env-var gated (`GGML_CCD_POOLS=1`). Leaves OpenMP production path untouched.
**Result**: **Net neutral** end-to-end (−2% vs noOMP flat atomic barrier, still 17% behind OMP production). Barrier-restructuring alone is NOT the right lever for CPU1 on this hardware. Phase 1.1 (CCD-aware work distribution) needed for real gain.

## What was implemented

Changes to `/mnt/raid0/llm/llama.cpp-experimental/ggml/src/ggml-cpu/ggml-cpu.c`:

1. **New types**:
   - `struct ggml_ccd_sync { atomic_int n_arrived; atomic_int sense; char _pad[...]; }` — cacheline-aligned per-CCD sync state
   - Array `ccd[GGML_TP_MAX_CCD=16]` on `ggml_threadpool` + global `ccd_global_arrived` / `ccd_global_sense` atomics
   - New fields on `ggml_compute_state`: `ccd_id`, `ccd_local_id`, `local_sense`, `global_sense`

2. **2-level sense-reversing barrier in `ggml_barrier`** (noOMP path only):
   - Each thread flips its own `local_sense` and `global_sense` every barrier (leader-turnover tolerant — found and fixed a bug where only the leader flipped global sense, causing deadlock/early-pass when leader changed across barriers)
   - Non-leaders spin on their CCD's local `sense` atomic (cacheline stays in CCD's local L3)
   - Last thread on each CCD promotes to global counter; last CCD globally flips the global sense and unblocks the other 11 CCD-leaders; each CCD-leader then publishes the local sense to release its 15 neighbors

3. **Env-var gate**: `GGML_CCD_POOLS=1` enables the path; defaults off. Auto-detects CCD count from thread count (prefers 12 for 96/192, falls back to 6/4/3/2)

4. **Thread-local state pointer** (`__thread struct ggml_compute_state * ggml_tls_state`) set at `ggml_graph_compute_thread` entry — O(1) access to the calling thread's state from inside `ggml_barrier`, replacing an initial O(N) `pthread_equal` scan that caused catastrophic slowdown

All changes are under `#ifndef GGML_USE_OPENMP`. Production OMP build is zero-impact.

## Measured performance

Test setup: `Qwen3-Coder-30B-A3B-Instruct-Q4_K_M` (17.28 GiB MoE-hybrid), 96t, `-p 0 -n 64 -r 3`, quiet host. Pinned via `taskset -c 0-95` for un-pinned variants (Phase 1.0 and bases).

| Build | Config | tok/s | Notes |
|---|---|---|---|
| build-llamafile-on (OMP) | Flat OMP barrier | **45.92** (σ 0.18) | Production baseline |
| build-noomp (no-OMP, CCD disabled) | Flat atomic barrier (ggml default) | 38.90 (σ 0.09) | noOMP's own baseline; 15% behind OMP |
| build-noomp (no-OMP, `GGML_CCD_POOLS=1`), Phase 1.0 only | Per-CCD 2-level barrier, no CCD pinning | 38.22 (σ 0.02) | **−1.7% vs noOMP flat; −17% vs OMP** |
| build-noomp (no-OMP, `GGML_CCD_POOLS=1`), **Phase 1.0 + 1.1** | Per-CCD barrier **+ CCD-aware cpumask pinning** | **39.07** (σ 0.04) | **+2.2% vs Phase 1.0, +0.4% vs noOMP flat; still −15% vs OMP** |

Phase 1.1 (adding CCD-aware per-worker cpumask so worker j pins to physical core `ccd_id*8 + local_id` — one core per worker within its CCD) recovers +2% over Phase 1.0. But the combined result is still neutral vs the baseline noOMP flat barrier, and 15% behind OMP.

Also tested on Qwen3.6-27B Q8_0 at 96t — same pattern (4.30 with CCD vs 4.43 flat noOMP; −3%).

## Correctness

- Tokens produced, benchmark completes, no crashes
- Initial implementation had a **leader-turnover deadlock** (different CCDs' leaders flipped `global_sense` independently, ending up at inconsistent target values). Fixed by having every thread unconditionally flip both local AND global sense on every barrier call regardless of whether it ends up being the leader.
- Bit-exact output not verified (would need a deterministic prompt + checksum comparison against OMP output — not done this session).

## Why the expected gain didn't materialize

The 32-45% barrier cost measured yesterday via `perf record` on the OMP build is **libomp-specific**. The unresolved `0x0000000000026580` family of hot addresses in perf is libgomp's spin-wait / futex-based barrier implementation. That barrier has a specific cost profile on 192 threads.

**ggml's own noOMP atomic barrier**:
```c
int n_barrier = atomic_fetch_add(&tp->n_barrier, 1);
if (n_barrier == n_threads - 1) { ... }
while (atomic_load(&tp->n_barrier_passed) == n_passed) cpu_relax();
```
Is a single cacheline-bouncing counter plus a spin loop on a single sense-like value. For 96 threads this is apparently already efficient enough that further splitting doesn't help.

Splitting into 12 per-CCD barriers replaces:
- 96-way atomic contention on `n_barrier` → 8-way contention on each of 12 `ccd[c].n_arrived`
- 96-way spin on `n_barrier_passed` → 7 per CCD spinning on local `ccd[c].sense`, plus 12 leaders spinning on global

In principle: less cacheline ping-ponging, local L3 hits for spin loads. In practice: no measurable end-to-end delta on this workload.

**Hypothesis**: the ggml atomic barrier at 96 threads completes in microseconds, and the TOTAL time in barriers is a small fraction of the noOMP decode cycle. Splitting the small-fraction-cost into two levels adds fixed overhead (the 2-level dispatch logic, TLS load) that roughly offsets the savings.

## What this tells us about CPU1 Phase 1 scope

Original handoff hypothesis was that restructuring the thread pool into per-CCD sub-pools would deliver 2-5× single-instance decode. That hypothesis depended on:

1. ✗ **Barrier cost reduction** — measured as neutral (this session)
2. ⚠ **CCD-local work distribution** — NOT implemented in Phase 1.0; still the most promising remaining lever
3. ⚠ **Cache-friendly weight access within a CCD** — requires both work distribution AND first-touch memory affinity

For the gain to materialize, ggml's `ith/nth` strided work distribution in `ggml_compute_forward_mul_mat` must become CCD-block-aware. Thread i working on rows `[i*N/nth, (i+1)*N/nth)` keeps sequential memory access within that thread. But if CCD-0 threads (ith 0-7) work on adjacent rows 0-7, CCD-1 threads (ith 8-15) on rows 8-15, etc. — that's already the natural behavior for `schedule(static)`. The CCD partition would then map contiguous output chunks to contiguous CCDs. That's not new work; it's what happens by default.

The gain must come from **memory placement**: if weight tensor rows are allocated so rows `[c*N/12, (c+1)*N/12)` are physically on the same NUMA node / close to CCD c, the GEMV reads are local. That requires:
- Weight allocation with `mbind` / first-touch discipline per CCD
- Thread pinning via cpumask so CCD c threads run on CCD c physical cores

ggml already has `cpumask` in `ggml_compute_state` and applies it via `ggml_thread_apply_affinity`. So thread pinning is already available.

**Phase 1.1 — CCD-aware thread pinning — IMPLEMENTED, +2%**: added a branch in `ggml_threadpool_new_impl` that, when `ccd_pool_enabled`, sets each worker's `cpumask` to a single specific core on its CCD (physical first, HT siblings for local_id ≥ 8 when ccd_threads==16). Measured +2% over Phase 1.0 alone but still neutral vs un-CCD baseline. So thread-pinning helps a bit but is not the missing multiplier either.

**What's STILL missing for real CPU1 gain** (not tried this session):
- **Per-CCD NUMA-bound weight allocation**: explicit `mbind(MPOL_BIND)` at model-load time so tensor row ranges land on each CCD's physically-nearest NUMA node. Without this, 96 threads still pull weights from the same flat DRAM pool (first-touch happened before CCD pinning existed). CCD-pinned cpumask alone doesn't relocate already-touched pages.
- **Matching OMP's barrier efficiency in noOMP**: OMP wins by 15% specifically on the barrier itself. ggml's atomic barrier is not a 2-level issue — it's a constant-factor gap against libomp.

## 2026-04-24 late — 2-way NUMA-local microbench confirms NPS2 is the real limiter

Extended the standalone GEMV microbench at `/mnt/raid0/llm/cpu-tp-prototype/tp_gemv_numa_bench.cpp` to measure the best-case 2-way NUMA TP under current NPS2 BIOS. Two modes on a 7.6 GB weight matrix (K=5120, N=400000, F32):

- **Mode A — flat 96t across both nodes (no NUMA awareness)**: 246.3 GB/s
- **Mode B — 2×48t, each half first-touched + mbind'd to its own NUMA node, threads pinned to that node**: 250.0 GB/s → **+1.5%, within noise**

`move_pages` confirmed WA's first page is on node 0 and WB's first page is on node 1 — NUMA placement IS happening. It just doesn't help end-to-end on this hardware.

**Why**: on NPS2 the node-distance ratio is 10/12 per `numactl --hardware` — cross-node access is only 20% slower than local. The 12 DDR5 channels are essentially "shared" across both NUMA nodes for random workloads. The 20% per-access penalty, applied to maybe 50% of accesses (random allocation gives half-local), = 10% average overhead. CPU1's TP design hoped to turn that 10% into 0%, but that 10% is small compared to barrier + coordination overhead when the split into N-way TP is introduced.

**Implication**: on current NPS2 BIOS, CPU1 TP-sharding cannot deliver the projected 2-5× because the memory subsystem is too close-to-uniform. The individual levers sum to at most a few percent:

| Lever | Measured NPS2 benefit |
|---|---|
| Per-CCD 2-level barrier (Phase 1.0) | neutral / −2% |
| CCD-aware per-worker cpumask (Phase 1.1) | +2% |
| 2-way NUMA-local mbind+first-touch | +1.5% |
| **NPS2 ceiling combining all CPU1 levers** | **~2-5%** total |

### What unlocks real CPU1 gains: NPS4 or L3-as-NUMA BIOS change

EPYC 9655 has 12 CCDs, each with its own L3 slice + nearest memory controllers. In **NPS4** mode, the BIOS exposes 4 NUMA nodes (3 CCDs each). In **L3-as-NUMA** mode, it exposes all 12 CCDs as individual NUMA nodes. Both require a reboot + BIOS setting change.

In those modes:
- Node-distance ratio is larger (more asymmetric) → NUMA-local access has real benefit
- 12-way or 4-way CCD-local sharding becomes physically meaningful
- CPU1 TP projections (2-5× single-instance) may actually materialize

This matches the `cpu-inference-optimization-index.md` plan: **CPU3 Phase 2 BIOS window** is the gate for CPU1's full potential, and CPU1 Phase 1 without the BIOS change yields diminishing returns. Today's session confirms empirically: under NPS2, CPU1 cannot outperform OMP's well-tuned flat pool.

### NPS mode tradeoff summary (for future BIOS window discussion)

| Mode | NUMA nodes | CCDs per node | Cross-node cost | Best for |
|---|---|---|---|---|
| NPS1 | 1 | 12 | N/A (all same) | Single-instance, no locality work |
| **NPS2** (current) | 2 | 6 | 20% (10/12) | Current production — good enough for flat workloads |
| NPS4 | 4 | 3 | larger | 4-way NUMA TP (CPU1 Phase 1 friendly) |
| L3-as-NUMA | 12 | 1 | largest (per-CCD) | Full 12-way CCD-TP (CPU1 Phase 2 full potential) |

Side effects to consider before changing NPS:
- Multi-instance 4×48t current production deployment may re-benchmark differently — the 4-way NUMA pinning currently maps to node halves under NPS2; under NPS4 each quarter would be its own node
- memory interleaving behavior changes — `--numa distribute` and `--numa interleave=all` take on different meanings
- `mlock` behavior may change with more NUMA nodes
- Applications that don't use NUMA API at all may see slight performance shifts (mostly positive for NUMA-aware work, mostly neutral for naive code)

## Recommendation

**Keep the CCD barrier infrastructure** (it's correct, env-var gated, zero impact when off) as the foundation for Phase 1.1. Next session's Phase 1.1 work:

1. Apply CCD-aware `cpumask` in `ggml_threadpool_new_impl` when `ccd_pool_enabled` — pin each worker to its CCD's 8 physical cores (+ optional HT siblings).
2. Add a per-CCD NUMA-bound weight allocation path for large tensors (possibly gated via `GGML_CCD_WEIGHT_NUMA=1`).
3. Measure end-to-end again. If still neutral, investigate profile-guided: where IS the time going at 96t on noOMP? Target that specifically.

A Phase 1 WITHOUT memory/affinity placement is equivalent to what OpenMP already does (flat team, no NUMA awareness), so matching OMP performance is the best we could hope for from barrier-only changes — which is exactly what we measured (neutral vs noOMP flat).

## Artifacts

- Modified source: `/mnt/raid0/llm/llama.cpp-experimental/ggml/src/ggml-cpu/ggml-cpu.c`
- Build: `/mnt/raid0/llm/llama.cpp-experimental/build-noomp/` (with `-DGGML_OPENMP=OFF`)
- Enable: `GGML_CCD_POOLS=1 LD_LIBRARY_PATH=.../build-noomp/bin .../llama-bench -t 96 ...`
- Raw logs: `/mnt/raid0/llm/epyc-inference-research/data/cpu_optimization/2026-04-24/ccd-pools/`
- Microbench (independent validation of pattern): `/mnt/raid0/llm/cpu-tp-prototype/`
