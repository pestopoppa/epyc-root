# CPU4 — Hierarchical Barrier in OpenMP Path

**Status**: COMPLETE (single-variant test) — **NEGATIVE RESULT** (2026-04-26)
**Goal**: Reclaim the ~30% of decode cycles currently spent in `#pragma omp barrier` (libgomp wait paths) on Q4_K_M sync-bound models.
**Outcome**: Implementation works, measurements show consistent **net-negative** (-2 to -4%) across configs. libgomp's omp barrier is competitive with or better than this custom 2-level CCD-aware barrier on this hardware. Reverted; design preserved here as one falsified variant, not full sync-track closure.
**Owner**: 2026-04-26 session.

## Background — why CPU4 matters

Phase D (2026-04-26) `perf stat` on REAP-246B canonical decode showed:
- IPC = 0.50, only 49.3 / 96 CPUs utilized average
- Cycles distribute as ~57% productive compute (`ggml_gemv_q4_K_8x8_q8_K`, `ggml_vec_dot_q6_K_q8_K`) and **~30% in libgomp scheduler/barrier**

The 30% gap is the lever. Q4_K_M models (4 of 5 production: Coder-30B, Qwen3-Next-80B, REAP-246B, gemma-4-26B-A4B) are sync-bound — half the threads sit idle in barrier wait at any moment. Q8_0 (Qwen3.6-35B-A3B frontdoor) is bandwidth-bound and not the target of this work; EP and L3aaN are the levers there.

## Why the existing CPU1 hierarchical barrier doesn't fix this

CPU1 Phase 1.0 added a 2-level hierarchical barrier (per-CCD arrival + cross-CCD aggregation, sense-flip protocol) at `ggml-cpu.c:633`. The implementation is correct and stable. **It is wrapped in `#ifndef GGML_USE_OPENMP / #else #pragma omp barrier #endif`**, so production OpenMP builds compile to a plain `omp barrier` and never touch the hierarchical primitive.

Why this happened: CPU1 was originally implemented for the `GGML_OPENMP=OFF` path (where the threadpool is pthread-based and the codebase has full control). The OpenMP path was left alone because the OpenMP threadpool init runs in libgomp, not under our control.

Building with `GGML_OPENMP=OFF` doesn't fix the issue either:
- Coder-30B Q4_K_M: 28.47 t/s noomp vs 43.57 t/s OpenMP = **-35%**
- REAP-246B: 3.01 t/s noomp vs 6.85 t/s OpenMP = **-56%**

The OpenMP threadpool's parallelism advantage outweighs the hierarchical barrier savings. CPU4 must keep OpenMP and add the hierarchical barrier *inside* it.

## Design

### Approach: optional hierarchical barrier in the OpenMP path

`ggml_barrier()` becomes a runtime branch:
- Default: `#pragma omp barrier` (existing behavior)
- `GGML_HIERARCHICAL_BARRIER=1` + CCD state initialized: 2-level CCD-local + cross-CCD sense-flip barrier (the same primitive CPU1 already implemented for the non-OpenMP path)

### Per-OMP-thread CCD state

Existing CPU1 code uses `__thread struct ggml_compute_state * ggml_tls_state` to identify the thread's CCD. For OpenMP threads, we use:
- An array `tp->omp_states[]` of length `n_threads`, allocated once
- Each OMP thread looks up its state via `omp_get_thread_num()`
- State initialization happens lazily on first barrier call within a parallel region (cheap one-time path)

Each per-thread state holds:
- `ccd_id` — 0..ccd_count-1, computed as `omp_get_thread_num() / ccd_threads`
- `local_sense`, `global_sense` — the existing barrier protocol's flip bits

### Barrier protocol (unchanged from existing non-OMP version)

```
arrive locally → if leader: arrive globally → if last globally: flip global sense
                                            else: spin on global sense → flip local sense
                else: spin on local sense
```

CCD-leader: thread 0 within each CCD (the (n_arrived == ccd_threads-1)th arrival, by sense-flip protocol the LAST one).

### Topology assumptions

- EPYC 9655: 12 CCDs × 8 cores = 96 physical cores
- `taskset -c 0-95 -t 96` pins one OMP thread per physical core
- Cores 0-7 = CCD 0, cores 8-15 = CCD 1, ..., cores 88-95 = CCD 11
- OMP_PROC_BIND=close (or =true) ensures the omp thread number → core mapping is stable, so omp_get_thread_num()/8 → CCD ID is correct
- Falls back to plain `omp barrier` if state isn't initialized or thread count doesn't divide cleanly into CCDs

### Env knobs

- `GGML_HIERARCHICAL_BARRIER=1` — opt-in (default 0)
- `GGML_HIERARCHICAL_BARRIER_CCD=12` — override CCD count (default 12 for EPYC 9655)
- `GGML_HIERARCHICAL_BARRIER_THREADS_PER_CCD=8` — override (default 8)

### Correctness

Same sense-flip protocol as the non-OpenMP path → same memory ordering guarantees. PPL bit-identical gate must pass on the production lineup.

## Implementation steps

1. **State structures**
   - Add `omp_states` array + `omp_states_initialized` flag to `struct ggml_threadpool`
   - Reuse existing `ccd[]`, `ccd_global_arrived`, `ccd_global_sense` fields

2. **Init helper**
   - `ggml_init_omp_ccd_state(tp)` — called lazily from first barrier call inside parallel region
   - Allocates `omp_states` array, fills `ccd_id` per thread, allocates `ccd[]` if not already, sets `ccd_pool_enabled = true`

3. **Modified `ggml_barrier`**
   - In `GGML_USE_OPENMP` path, check `GGML_HIERARCHICAL_BARRIER`
   - If enabled: call new helper that uses `omp_states[tid]` for per-thread state
   - Else: `#pragma omp barrier`

4. **Validation**
   - Build, smoke-test on Coder-30B Q4_K_M (~5 min)
   - Sweep production lineup: Coder-30B, Qwen3-Next-80B, REAP-246B, gemma-4-26B-A4B (~20 min)
   - PPL gate on Coder-30B Q4_K_M and REAP-246B Q4_K_M (~30 min)

5. **Decision**
   - If +5% or more on REAP-246B + Qwen3-Next-80B with PPL bit-identical → **ship in v5 default-off** (production opt-in)
   - If +1-4% only → keep gated, document as marginal
   - If neutral or worse → revert; document as evidence that this barrier variant is not the dominant lever

## Out of scope (future iterations)

- Lock-free expert dispatch (within `mul_mat_id`, instead of barriered loop)
- Cross-CCD compute migration (move work from idle CCDs to overloaded ones)
- Coalesce barriers across consecutive ops (Lever B ext.)

## Measurement results — 2026-04-26 (negative)

Implemented per design. Built and tested at HEAD `8cb04da9d` + CPU4 patch.

| Model | Config | t/s ± std | vs canonical |
|-------|--------|-----------|--------------|
| Coder-30B Q4_K_M | canonical (no flags) -r 3 | 42.04 ± 0.06 | reference |
| Coder-30B Q4_K_M | + `GGML_CCD_POOLS=1` (hier. barrier active) -r 3 | 40.25 ± 0.12 | **-4.3%** |
| Coder-30B Q4_K_M | + `GGML_CCD_POOLS=1` + `OMP_PROC_BIND=close` `OMP_PLACES=cores` -r 3 | 39.60 ± 0.50 | **-5.8%** |
| Coder-30B Q4_K_M | canonical + `OMP_PROC_BIND=close` (control) -r 3 | 39.09 ± 0.09 | **-7.0%** (binding alone hurts) |
| Coder-30B Q4_K_M | + `GGML_CCD_POOLS=1` -t 48 -r 3 | 37.20 ± 0.15 | -2.1% vs t48 canonical 38.00 |
| REAP-246B Q4_K_M | canonical -r 2 | 6.76 ± 0.03 | reference |
| REAP-246B Q4_K_M | + `GGML_CCD_POOLS=1` -r 2 | 6.70 ± 0.00 | -0.9% |
| REAP-246B Q4_K_M | + `GGML_CCD_POOLS=1` + `OMP_PROC_BIND=close` -r 2 | 5.06 ± 0.00 | **-25%** (binding catastrophic) |

CCD init logged: `[GGML_CCD_POOLS] enabled: 12 CCDs x 8 threads/CCD (total 96, core_base=0)` — code path active.

## Why it doesn't win

Hypotheses, in order of likelihood:

1. **libgomp's `#pragma omp barrier` is highly optimized.** The 30% cycles in libgomp.so observed in Phase D's `perf record` are NOT pure dumb spinning — much is productive scheduler/coordination work that the OMP runtime does correctly. A naive 2-level sense-flip barrier doesn't capture all the work libgomp does.
2. **Cache locality assumption broken without strict pinning.** Without `OMP_PROC_BIND=close`, libgomp can re-balance threads across cores between barrier calls. The hierarchical barrier assumes thread N lives on CCD N/8 (per `omp_get_thread_num()`/8), but the physical core may be elsewhere → spinning on remote-L3 cachelines, slower than libgomp's NUMA-aware spinning.
3. **`OMP_PROC_BIND=close` itself is a regression on this hardware** (-7% on canonical). Whatever libgomp does internally with un-pinned threads on EPYC NPS4 is faster than a static 1:1 thread-to-core pin. Pinning interferes with libgomp's own NUMA-aware scheduling.
4. **The 30% libgomp slice is decode-time reality, not waste.** Half the threads idle at any given moment is a STRUCTURAL property of the workload (top-K MoE expert sparsity creates uneven work), not a barrier-implementation defect. CPU4 cannot fix structural imbalance.

## Implications

This is a strong **negative result** for software-level sync optimization on the Q4_K_M sync-bound class:

- The sync bottleneck on REAP-246B / Qwen3-Next-80B / Coder-30B / gemma-4-26B-A4B is structural (MoE top-K imbalance) and **cannot be alleviated by a faster barrier alone**.
- Future avenues that COULD help (now deprioritized but not falsified):
  1. **Lock-free expert-loop dispatch** — let CCDs grab the next available expert dynamically instead of static partitioning. Out of scope for this round; would require redesigning `mul_mat_id` work distribution.
  2. **Cross-CCD work migration** — move work from idle CCDs to busy ones. Complex, requires runtime profiling.
  3. **Different MoE quantization layouts** — pre-shuffle experts so each CCD's assigned slice has balanced compute. Requires offline tooling.
- L3aaN should not be justified by this barrier test alone; topology decisions should rely on CPU21/CPU24 evidence.
- The +1.8% from CPU1's `CCD_POOLS + CCD_WORK_DIST + BARRIER_LOCAL_BETWEEN_OPS` (without NUMA_WEIGHTS) on Coder-30B remains valid as a small substrate gain in non-OpenMP builds. **This does not extend to OpenMP builds** per CPU4's measurements above.
- Next constructive path is Wave 1/2: CPU21 OpenMP runtime/scheduling matrix first, then CPU22 dynamic load balancing for structural expert-imbalance.

## Disposition

- Code reverted (no changes shipped to llama.cpp-experimental).
- Design preserved in this handoff for future-session reference.
- P4 task marked complete for this implementation variant.
- Treat broader sync-track closure as **pending CPU21/CPU22 evidence**, not closed.

## Cross-references

- Current barrier: `llama.cpp-experimental/ggml/src/ggml-cpu/ggml-cpu.c:633` (`ggml_barrier`)
- CPU1 hierarchical primitive (existing, OMP=OFF only): same file `:650-708`
- Phase D evidence: `progress/2026-04/2026-04-26.md` REAP-246B perf stat
- P2 evidence (sync-bound class): `progress/2026-04/2026-04-26.md` cross-model perf stat
- Env-flag inventory: `cpu-kernel-env-flags-inventory.md`
- Wave dependencies: `cpu-openmp-runtime-scheduling-matrix.md` (CPU21), `cpu-dynamic-moe-load-balancing.md` (CPU22)
