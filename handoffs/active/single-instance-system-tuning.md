# Single-Instance System-Level Throughput Tuning

**Status**: stub (investigation not started)
**Created**: 2026-04-23 (user-identified gap — "leave nothing on the table" single-instance throughput)
**Priority**: HIGH — several knobs are zero-code changes with measurable gains, and some are prerequisites for the TP-sharding lever.
**Categories**: hardware_optimization, inference_serving, local_inference
**Workstream**: Inference Acceleration → CPU Optimization
**Parent index**: [`cpu-inference-optimization-index.md`](cpu-inference-optimization-index.md), [`inference-acceleration-index.md`](inference-acceleration-index.md)
**Related**:
- [`intra-process-tensor-parallel-decode.md`](intra-process-tensor-parallel-decode.md) — the big compute-parallelism lever; depends on NPS outcomes here
- [`cpu-shape-specialized-gemv-decode.md`](cpu-shape-specialized-gemv-decode.md) — per-kernel compute lever
- [`dynamic-stack-concurrency.md`](dynamic-stack-concurrency.md) — multi-instance NUMA deployment (existing production config that some of these knobs might affect)

---

## Problem

We're on single-socket EPYC 9655 (96 cores / 192 threads / 12 CCDs) in default system configuration:

- **NPS mode**: NPS2 (2 NUMA nodes, 6 channels each)
- **THP**: `madvise` (not always-on)
- **Explicit hugepages**: 0 allocated
- **Governor**: `performance` ✅
- **SMT**: enabled
- **NUMA balancing**: unknown (default kernel state)
- **IRQ affinity**: default (IRQs can land on compute cores)
- **Thread pool sync**: GGML's pthread barrier (generic OpenMP-style)

Each of these is potentially a free or near-free lever for single-instance decode throughput. None has been systematically measured on our hardware. Several may be **prerequisites** for the TP-sharding work (`intra-process-tensor-parallel-decode.md`) to deliver its full gain.

This handoff groups the system-level knobs into one workstream so they can be audited, measured, and either deployed or ruled out together, rather than as scattered ad-hoc experiments.

## Lever Catalog

Grouped by what they affect, with current state and expected gain.

### Group A — Memory subsystem

| Knob | Current | Candidate | Expected gain | Needs reboot |
|------|---------|-----------|---------------|--------------|
| NPS mode | NPS2 (2 nodes) | NPS4 (4 nodes) or L3-as-NUMA (12 nodes) | 1.5–3× when combined with TP; 0–10% without TP | **Yes** (BIOS) |
| Transparent Huge Pages | `madvise` | `always` | 2–8% on large-weight workloads (fewer TLB misses) | No |
| Explicit hugepages (1 GB) | 0 allocated | Pre-allocate + use for weight mmap | 5–15% on long decode runs | No (kernel boot param) |
| `numa_balancing` | default (probably on) | Explicitly off via `sysctl kernel.numa_balancing=0` | 2–10% (AMD's own guide requires this for MI300X; same principle applies) | No |
| `--numa` llama.cpp flag | `distribute` | Test `isolate` for single-instance | 0–5% | No |
| Weight replication per NUMA node | Shared (mmap + page cache) | Explicit per-node copies via `mbind` | 10–30% in NPS4/L3aaN modes, 0% in NPS2 | No |

### Group B — Thread/sync primitives

| Knob | Current | Candidate | Expected gain |
|------|---------|-----------|---------------|
| Barrier implementation | pthread barrier (GGML default) | Busy-wait spinlock for high-thread count | 5–15% barrier cost reduction |
| SMT (hyperthreading) | On | Off for AVX-512-heavy decode | Unclear: AVX-512 often regresses with SMT, but GGML's work distribution may assume 2× threads |
| Thread pool | Global 192-thread pool | Per-CCD pools (12 × 16 threads) | Baseline for TP-sharding; 10–30% barrier cost reduction alone |
| IRQ affinity | Default (IRQs on any core) | Pin IRQs to NUMA node 0 cores 0–3 only | 2–5% tail-latency improvement |
| Scheduler policy | `SCHED_OTHER` (default) | `SCHED_FIFO` for worker threads with `mlockall` | 1–3% (removes migration jitter) |
| CPU frequency pinning | `performance` governor | Also disable C-states in BIOS | 0.5–2% (removes entry/exit latency) |

### Group C — llama.cpp runtime flags

| Flag | Current | Candidate | Expected gain |
|------|---------|-----------|---------------|
| `--threads` | 192 | Measure 48/96/144/192 sweep per-model | Per-model optimal; not always 192 |
| `--threads-batch` | Same as `--threads` | Decouple: higher for prefill, lower for decode | 3–8% on mixed workloads |
| `--ubatch-size` | Model-dependent | Already partially tuned in `numa_parallel` data; re-verify under NPS changes | — |
| `--numa` | `distribute` | Test all 4 modes: `distribute`, `isolate`, `numactl`, default | Per-mode; interacts with Group A |
| `--mlock` | Enabled | Verify all pages actually pinned with `/proc/<pid>/status` `VmLck` | Already done; sanity-check |
| `--no-mmap` | Not set | Test: copies weights into anonymous pages, may hurt first-load but help residency | Usually worse; verify |
| `--parallel` (N slots) | 1 | N=2,4,8 for concurrent requests within one server | Aggregate, not single-session; covered by separate multi-instance work |

### Group D — Kernel / OS

| Knob | Current | Candidate | Expected gain |
|------|---------|-----------|---------------|
| Kernel version | 6.14 | Unchanged; modern | — |
| `zone_reclaim_mode` | default | 0 (off — for NUMA) | 0–3% under memory pressure |
| `vm.swappiness` | default (60) | 1 or 0 | Negligible if never swapping |
| `vm.watermark_scale_factor` | default | Higher (more free memory buffer) | Reduces reclaim stalls |
| IRQ balancing service | `irqbalance` running? | Stopped, manual pin | Paired with IRQ affinity |

## What Is Already Done vs Missing

**Already done**:
- Governor set to `performance`
- `--mlock` deployed across all production models
- `--numa distribute` on current production
- AMD NUMA balancing: documented as required for MI300X GPU but not verified on our host

**Missing / not audited**:
- NPS mode has never been benchmarked against alternatives
- THP is still at default (`madvise`)
- Explicit hugepages never tried
- Barrier/sync cost never profiled
- IRQ affinity never tuned
- Full `--threads` sweep hasn't been done since the NUMA 4-way deployment (numbers in `numa_parallel/` data are 2-weeks-old at the time of this handoff creation)

## Phased Work Plan

### Phase 0: Audit and baseline (2–3 days)

**Goal**: know what our current state is before changing anything.

- [ ] Capture current BIOS config: NPS mode, C-states, Infinity Fabric frequency, SMT setting. Record in `research/deep-dives/epyc-9655-bios-baseline.md`.
- [ ] Capture current kernel config: sysctls for NUMA balancing, zone_reclaim, THP mode, hugepages count.
- [ ] Run single-instance decode baseline on 30B-A3B Q4_K_M at 192t with `perf stat` recording:
  - `cycles`, `instructions`, `IPC`
  - `dTLB-load-misses`, `iTLB-load-misses`
  - `cache-misses`, `LLC-loads`, `LLC-load-misses`
  - Uncore memory bandwidth counters
  - `sched:sched_wakeup` counts (proxy for barrier frequency)
- [ ] Compute: what % of wall-clock decode time is in barrier/wait states vs active compute?
- [ ] Measure single-instance BW utilization as a fraction of theoretical 460 GB/s.
- [ ] **Gate**: these numbers become the baseline for every subsequent experiment. Do not change anything until baseline is captured.

**Artifacts**: baseline report with all counters and a decode-time breakdown flamegraph.

### Phase 1: Zero-reboot system tuning (1 week)

**Goal**: apply and measure all knobs that don't require BIOS changes.

Apply one at a time, measure delta, keep or revert. Order by expected gain × ease:

1. **NUMA balancing off**: `sysctl -w kernel.numa_balancing=0`. Single-command test. Measure.
2. **THP `always`**: `echo always > /sys/kernel/mm/transparent_hugepage/enabled`. Measure. Then tune defrag: `echo always > .../defrag` or `echo defer+madvise > .../defrag`.
3. **Explicit 1GB hugepages**: reserve via boot param `hugepagesz=1G hugepages=200` (~200 GB for weights). Verify llama-server mmap uses them (may need patch or `libhugetlbfs`).
4. **IRQ affinity**: stop `irqbalance`, pin all IRQs to node 0 cores 0–3: `for irq in /proc/irq/*; do echo 0-3 > $irq/smp_affinity_list; done`. Measure tail latency on production traffic.
5. **`--numa` flag sweep**: test `distribute`, `isolate`, default on same model. Pick best.
6. **`--threads` sweep**: 48, 96, 144, 168, 192. Per model. Update production config if non-192 wins.
7. **`--threads-batch` decoupling**: if prefill-heavy workloads present, set batch=192, decode=128 or lower.

For each: document, benchmark, and retain only if Δ ≥ +2%. Stack the wins.

**Artifacts**: per-knob benchmark matrix; updated `orchestrator_stack.py` launch flags; new defaults in `/etc/sysctl.d/` and `/etc/default/grub`.

### Phase 2: BIOS / reboot changes (1–2 weeks, coordinated)

**Goal**: evaluate NPS4 and L3-as-NUMA modes, possibly disable C-states or SMT.

Requires a maintenance window (reboot, BIOS interaction). Coordinate with user before any reboot.

- [ ] Plan maintenance window. Document rollback procedure.
- [ ] Reboot into **NPS4**. Re-run Phase 0 baseline + current production benchmarks. Record deltas.
- [ ] If BIOS exposes **L3-as-NUMA** (CCDaaN): reboot into that mode. Re-run same battery.
- [ ] Test **SMT off**: reboot with SMT disabled. Measure AVX-512-heavy decode on 30B-A3B and dense 32B.
- [ ] Test **C-states off** (C1E, C6 disabled in BIOS). Measure latency and throughput deltas; check thermal/power implications.
- [ ] Decision matrix: pick optimal BIOS config balancing single-instance gain, multi-instance gain, and operational complexity.

**Gate**: if NPS4 or L3aaN shows no improvement and hurts multi-instance aggregate, revert to NPS2. If one mode strictly dominates, deploy.

**Artifacts**: BIOS config recommendation report; rollback procedure doc; updated production config.

### Phase 3: Sync primitive redesign (2–4 weeks, depends on TP handoff)

**Goal**: replace GGML's default barrier with a per-CCD hierarchical one. Composes with `intra-process-tensor-parallel-decode.md`.

- [ ] Profile GGML barrier in isolation: build a micro-benchmark that runs N threads through K barriers and measures time-per-barrier.
- [ ] Prototype a spinlock-based barrier for high thread counts (>64).
- [ ] Prototype a hierarchical barrier: per-CCD local barrier (16 threads) + cross-CCD global barrier (12 participants).
- [ ] Measure speedup on synthetic + real decode.
- [ ] If win, coordinate integration with `intra-process-tensor-parallel-decode.md` Phase 2 thread-pool work.

**Artifacts**: barrier micro-benchmark; prototype code; integration plan.

### Phase 4: Weight replication per NUMA node (1–2 weeks, conditional on NPS ≥ 4)

**Goal**: when running in NPS4 or L3aaN, replicate small-model weights to each NUMA node to guarantee local reads.

- [ ] Identify which production models fit 4× (NPS4) or 12× (L3aaN) replication in 1.1 TB RAM.
  - 30B-A3B Q4_K_M (16 GB): 4× = 64 GB (fits), 12× = 192 GB (fits).
  - 32B Q4_K_M (18.5 GB): 4× = 74 GB (fits), 12× = 222 GB (fits).
  - 122B Q4_K_M (69 GB): 4× = 276 GB (fits), 12× = 828 GB (tight).
  - 246B REAP Q4_K_M (139 GB): 4× = 556 GB (tight), 12× = 1668 GB (does not fit).
  - 480B Q4_K_M (250 GB): 12× does not fit under any mode.
- [ ] Implement via `mmap` + `mbind(MPOL_BIND)` or `move_pages`. Verify pages land on correct node via `/proc/<pid>/numa_maps`.
- [ ] Benchmark weight-replicated vs shared-page-cache on each model.
- [ ] Decision matrix: which models get replicated, which stay shared.

**Artifacts**: placement strategy per model; updated `orchestrator_stack.py`.

## Falsification Conditions

Skip a lever if its Phase 1 measurement shows:

- No measurable improvement (Δ < +1%) on either single-instance or aggregate benchmarks.
- Regression on any benchmark (hurts more than it helps).
- Complexity far exceeds expected gain (e.g., 2 weeks of work for 2% improvement).

Abandon the whole handoff if Phase 0 shows:

- Single-instance is already within 10% of aggregate throughput (no gap to close).
- All knobs are already at optimal default (nothing to tune).

## Risks

1. **BIOS changes require reboots** and may have unintended effects on other services running on the host. Coordinate with user; document rollback.
2. **NPS4 / L3aaN may hurt multi-instance aggregate** even if it helps single-instance. Need full battery of benchmarks before committing.
3. **Hugepages fragmentation**: large pages can be hard to allocate on a running system. Reserve at boot.
4. **IRQ affinity changes may affect network / disk latency** for the orchestrator's control plane. Test carefully.
5. **SMT off halves logical thread count**: if GGML relies on 192 threads, going to 96 physical may hurt. Benchmark.
6. **THP `always` can cause `khugepaged` CPU spikes** that affect tail latency. Mitigation: `defer+madvise` gives the benefit without the stalls.

## Success Criteria

**Phase 0**: baseline captured, bottleneck identified.

**Phase 1 (zero-reboot)**: cumulative +5–15% single-instance decode on 30B-A3B. No regression on aggregate.

**Phase 2 (BIOS)**: NPS mode recommendation decided. If NPS4 or L3aaN wins, an additional +10–30% unlocked when combined with TP sharding.

**Phase 3 (sync)**: barrier cost reduced by 30–60% on 192t workloads. Prerequisite for TP Phase 2.

**Phase 4 (replication)**: small-model single-instance throughput reaches 80%+ of aggregate. Only meaningful under NPS4/L3aaN.

## Composition

These knobs multiply with the compute-side work but with smaller individual coefficients:

| Lever | Typical multiplier |
|-------|--------------------|
| Full system tuning (all Phase 1 + 2 knobs) | 1.15–1.40× |
| GEMV ukernels alone | 1.5–2.5× |
| TP sharding alone | 2.0–3.5× (NPS2) or 3.5–5× (L3aaN) |
| Combined | Multiplicative, capped by memory BW ceiling (~460 GB/s) |

A model currently at 50% of BW ceiling has 2× headroom. A model at 80% of BW ceiling has only 1.25× headroom. Phase 0 tells us which regime we're in.

## Open Questions

1. **Does our BIOS actually expose L3-as-NUMA** (CCDaaN)? Some server boards hide it behind a "Technician Mode" or similar. Check.
2. **Is the IOD fabric frequency (FCLK) at stock or can it be overclocked?** FCLK scaling can add a few % of cross-CCD BW.
3. **Is there a measurable downside to `sysctl kernel.numa_balancing=0`** for our mixed workload (inference + orchestrator control + occasional training)?
4. **Does `libhugetlbfs` still work cleanly with llama.cpp's mmap path**, or do we need to patch llama.cpp to request hugepages explicitly?
5. **Can we get AMD μProf running on this host** to expose uncore counters the default `perf` doesn't?

## Artifacts to Produce

1. `research/deep-dives/epyc-9655-bios-baseline.md` — Phase 0 report.
2. `research/deep-dives/epyc-9655-system-tuning-matrix.md` — Phase 1–4 results.
3. Updated `orchestrator_stack.py` launch flags.
4. Host-level config: `/etc/sysctl.d/99-epyc-inference.conf`, `/etc/default/grub` hugepage params.
5. BIOS config recommendation document (for future rebuilds).
6. Updated `cpu-inference-optimization-index.md` and `inference-acceleration-index.md` rows.

## References

- AMD "EPYC 9005 Series BIOS & Workload Tuning Guide" — primary reference for NPS modes.
- AMD MI300X inference tuning guide — source for NUMA balancing recommendation.
- Linux kernel docs: `Documentation/admin-guide/mm/transhuge.rst`, `Documentation/admin-guide/mm/hugetlbpage.rst`.
- Phoronix Zen 5 / Turin reviews for NPS mode benchmarks on other workloads.
- llama.cpp `--numa` flag docs: [github.com/ggml-org/llama.cpp/blob/master/tools/main/README.md](https://github.com/ggml-org/llama.cpp/blob/master/tools/main/README.md).

## Pickup Checklist

- [ ] Re-read this handoff end-to-end.
- [ ] Capture Phase 0 baseline **before any change**.
- [ ] Run Phase 1 knob-by-knob, not all at once — isolate effects.
- [ ] Coordinate reboot window with user before Phase 2.
- [ ] Keep every change rollback-able.
- [ ] Update `progress/` daily during active phases.
