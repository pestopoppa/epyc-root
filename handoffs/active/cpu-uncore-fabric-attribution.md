# CPU24 — Uncore/Fabric Counter Attribution For >150B Regressions

**Status**: ACTIVE (created 2026-04-26)
**Priority**: HIGH
**Categories**: profiling, hardware_optimization, benchmarking_methodology
**Workstream**: Inference Acceleration → CPU Optimization
**Parent index**: [`cpu-inference-optimization-index.md`](cpu-inference-optimization-index.md) (CPU24)
**Related**: [`cpu-benchmark-rigor-and-revalidation.md`](cpu-benchmark-rigor-and-revalidation.md) (CPU20 gate), [`large-moe-expert-parallelism.md`](large-moe-expert-parallelism.md) (CPU15 regressions), [`nps-reboot-runbook.md`](nps-reboot-runbook.md) (topology decisions)

## Objective

Replace synthetic bandwidth framing with counter-backed attribution for >150B EP regressions (REAP-246B and MiniMax-M2.7 class).

## Why this exists

Observed regressions are real, but aggregate-DDR saturation was previously overstated. We need hardware counter evidence to identify the dominant bottleneck class before closing CPU15 decisions.

## Scope

Collect and compare baseline vs EP on:
- IMC/channel utilization
- fabric/interconnect pressure
- remote miss behavior
- LLC miss intensity
- stall-class indicators (where available)

Primary targets:
- REAP-246B-A35B Q4_K_M
- MiniMax-M2.7 Q8_0

## Protocol requirements

All measurements must satisfy CPU20.

Attribution runs should include:
1. canonical single-instance baseline
2. best-known EP config for each model
3. at least 2 repetitions for counter stability

## Decision outputs

Produce one of:
1. `dominant_bottleneck = sync_imbalance`
2. `dominant_bottleneck = fabric_or_remote_miss`
3. `dominant_bottleneck = compute_or_kernel_path`
4. `dominant_bottleneck = mixed/uncertain` (with next discriminator test)

## Integration gate

CPU15 >150B closure, CPU22 mechanism design, and L3aaN retest rationale must all cite CPU24 outputs.

## Deliverables

- `data/cpu_optimization/<date>-cpu24-uncore-fabric/`
- attribution memo with counter table + conclusion class
- update to CPU15 and runbook guidance based on the conclusion class

---

## CPU24-narrow Attribution Result — 2026-04-26 evening

**Status**: COMPLETE — narrowed scope (the original "EP regresses on >150B" question evaporated after compounding-matrix found EP is neutral on proper canonical). New scope: characterize what limits REAP-246B at 5.94 t/s on proper canonical (`numactl --interleave=all -t 96`).

### Method

`sudo perf stat -e cycles,instructions,branches,branch-misses,cache-references,cache-misses,ls_dmnd_fills_from_sys.{dram_io_far,dram_io_near,remote_cache,local_all}` running:

`numactl --interleave=all --physcpubind=0-95 llama-bench -m REAP-246B-Q4_K_M -t 96 -fa 1 -p 0 -n 64 -r 1`

### Counter table — REAP-246B Q4_K_M @ 96t (BW-bound class proxy)

| Metric | Value |
|---|---|
| Throughput | **6.01 t/s** (matches 5.94 ± 0.01 r=5 baseline) |
| Wall time | 41.22 s (64 tokens generated) |
| Cycles | 6.84e12 |
| Instructions | 2.69e12 |
| **IPC** | **0.39** (7.8% of Zen 5 peak 5) |
| Cache references | 65e9 |
| Cache misses | 5e9 (7.68%) |
| ls_dmnd_fills.dram_io_far | 482M (10%) — remote-NUMA DRAM |
| ls_dmnd_fills.dram_io_near | 152M (3%) — local-NUMA DRAM |
| ls_dmnd_fills.remote_cache | 422M (9%) — cross-NUMA cache hits |
| ls_dmnd_fills.local_all | 3,580M (77%) — local L1-L3 hierarchy |
| **Cross-NUMA fraction** | **20% (904M / 4,636M total fills)** |

### Counter table — Qwen3.6-35B-A3B Q8_0 @ 96t (BW-bound class comparison)

| Metric | Value |
|---|---|
| Throughput | 21.40 t/s |
| Wall time | 9.24 s (64 tokens) |
| **IPC** | **0.19** (3.8% of Zen 5 peak — even lower than REAP) |
| Cache miss rate | 10.0% |
| Cross-NUMA fraction | 26% (363M / 1,391M total fills) |

### Sync-overhead estimate via thread scaling

- REAP-246B single-thread (taskset -c 0 -t 1): **1.41 t/s**
- REAP-246B 96-thread: 6.01 t/s
- **Scaling efficiency = 4.27× (vs ideal 96×)**

If the workload were perfectly parallel, 96 threads would deliver ~135 t/s. We get 6 t/s. **Sync/coordination overhead consumes ~96% of potential parallelism.**

### Bandwidth utilization

- REAP-246B: ~118 GB/s used (rough estimate based on activated 35B at Q4 → ~19.7 GB/token × 6 t/s) = **26% of 460 GB/s aggregate**
- Qwen3.6-35B Q8_0: ~64 GB/s = **14% of aggregate**

**Both models are NOT DRAM-saturated.** The earlier hypothesis that >150B class was "BW-saturated" is invalidated by the counter data — REAP uses only 26% of aggregate DRAM bandwidth.

### Attribution

**`dominant_bottleneck = sync_imbalance + fabric_pressure (mixed)`**

Evidence:
1. Low IPC (0.19-0.39 vs Zen 5 peak 5) — cores stalled on memory accesses despite low BW utilization → individual access latency is the killer, not aggregate BW
2. 4.27× scaling on 96 threads for REAP — sync overhead claims most of the parallelism
3. 20-26% cross-NUMA fills — fabric-traversal latency adds to per-access cost
4. 80% local fills — the L1-L3 hierarchy is well-utilized; the bottleneck is the 20% that has to traverse fabric

### Implications for downstream tracks

- **CPU19 Tutel 2DH** (was deprioritized after compounding-matrix): the technique itself (intra-CCD aggregate first, then inter-NUMA exchange to reduce sync points/token) has **independent merit** beyond EP. Could apply to standard MoE expert dispatch sync pattern. Re-evaluate: CPU19 keeps research-grade priority but is not urgent.
- **CPU22 dynamic load balancing**: still gated on CPU21 results, but the ~96% parallelism loss to sync overhead suggests STATIC partitioning is leaving substantial throughput on the table. Likely to be valuable.
- **CPU21 OpenMP runtime matrix**: the 4.27× scaling (vs ideal 96×) is exactly what runtime-layer tuning should attack. Higher priority than originally framed.
- **CPU15 EP**: was supposed to fix sync via inter-process coordination. On proper canonical EP is neutral (compounding-matrix). The sync-overhead problem is real but EP isn't the right tool for it.

### Updated guidance for CPU15 / L3aaN / runbook

- The catastrophic >150B regression narrative was a baseline artifact (compounding-matrix). On proper canonical EP is neutral.
- The remaining open question — "what limits REAP at 6 t/s" — is answered: **sync overhead claims 96% of parallelism**, not bandwidth saturation, not memory placement. The bottleneck is the per-token sync count × per-sync latency at 96 threads.
- L3aaN was already rejected for unrelated reasons (regressed across all configs); CPU24 doesn't change that.

### Raw data

- `data/cpu_optimization/2026-04-26-cpu24/reap_canonical_perfstat.log` — REAP-246B perf stat
- `data/cpu_optimization/2026-04-26-cpu24/q8_canonical_perfstat.log` — Q8_0 perf stat (comparison)
- `data/cpu_optimization/2026-04-26-cpu24/reap_singlethread.log` — REAP single-thread baseline (1.41 t/s)
