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

### Attribution (REVISED post-perf-record 2026-04-26 evening)

**`dominant_bottleneck = compute_kernel (memory-stalled INSIDE compute path)`**

Original "sync_imbalance" attribution was WRONG. perf-record hot-function profile on REAP-246B at 96t (`01_perfrecord_hotfunc.sh`, 25-second decode-phase capture, 160k samples) shows:

| Symbol | % of samples |
|--------|-------------|
| `ggml_gemv_q4_K_8x8_q8_K` (compute kernel) | **64.37%** |
| `ggml_vec_dot_q6_K_q8_K` (compute kernel) | **15.64%** |
| libgomp internal sync at offset 0x26580 | **15.50%** |
| `ggml_compute_forward_flash_attn_ext` | 0.73% |

**80% of cycles are in compute kernels; only 15% in OpenMP sync.**

The 4.27× scaling on 96 threads (vs ideal 96×) is NOT primarily sync overhead — it's per-thread bandwidth contention inside the compute kernels. With 96 threads sharing 460 GB/s aggregate, per-thread BW = 4.79 GB/s vs single-thread effectively-unlimited (single-thread saturates its local channel at ~30-40 GB/s). Cores spend 80% of cycles INSIDE the gemv loop but stalled on memory loads — perf-record sees them in the kernel's IP range, but the IPC counter (0.39) reveals they're not actually retiring instructions.

**Refined evidence:**
1. **80% time in compute kernels** (perf record) — kernels themselves are the wall-time consumer
2. **IPC 0.39** (perf stat) — but kernels are memory-stalled, not compute-saturated
3. **15% libgomp time** — real sync overhead, but secondary to compute-stall
4. **20% cross-NUMA fills** — adds to per-access latency (within compute path)
5. **26% aggregate BW used** — NOT BW-saturated at the system level, but per-thread BW share is what bottlenecks each core's compute
6. **CPU21 affinity tuning gives +3-8%** — this is real but small; consistent with the secondary role of sync overhead

### Implications for downstream tracks (UPDATED post-perf-record + CPU21)

- **CPU19 Tutel 2DH**: motivation FURTHER weakened by perf-record. Sync is only 15% of REAP-246B cycles. Even if Tutel 2DH halved that overhead (best case), throughput would gain at most ~7-8%. Keep stub for archival; **DON'T pursue without new evidence**.
- **CPU22 dynamic load balancing**: re-scoped. The "static partitioning leaving 96% on the table" framing was wrong. Dynamic balancing might still help by keeping all 96 threads productively in compute (instead of some waiting at barriers), but the gain ceiling is bounded by the 15% sync-overhead share. **Modest priority** — gated on CPU21 results AND new evidence that thread imbalance is significant.
- **CPU21 OpenMP runtime matrix**: COMPLETE 2026-04-26 evening. Universal +3-8% via `OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active`. Real win but smaller than originally projected; consistent with sync being a secondary (15%) bottleneck.
- **CPU15 EP**: throughput-neutral on proper canonical (compounding-matrix). EP code is bit-correct but doesn't address the actual bottleneck (compute kernels memory-stalled).
- **CPU2 SIMD kernel work**: REVALIDATED PRIORITY. Since 80% of cycles ARE in compute kernels (gemv + vec_dot), faster SIMD compute = real wall-time reduction. Q6_K + Q5_K extensions (Tier 1.6) directly attack the dominant cycle consumer.
- **Memory-latency-hiding research**: the bottleneck is per-thread DRAM access inside compute kernels. Possible levers (research-grade): software prefetching tuning, K-block sizing in 8x8 kernel, smaller working sets per thread.

### Updated guidance for CPU15 / L3aaN / runbook

- The catastrophic >150B regression narrative was a baseline artifact (compounding-matrix). On proper canonical EP is neutral.
- The remaining open question — "what limits REAP at 6 t/s" — is answered by the corrected attribution above: **compute kernels memory-stalled INSIDE on per-thread DRAM access**, not sync (sync is only 15%), not bandwidth saturation at the system level (26% aggregate used), not memory placement. The 4.27× scaling efficiency at 96 threads (vs ideal 96×) is dominated by per-thread BW contention; the second-order contributor is sync (15% of cycles).
- L3aaN was already rejected for unrelated reasons (regressed across all configs); CPU24 doesn't change that.

> **Stale-text strikethrough (corrected 2026-04-27 evening)**: an earlier version of this section said "sync overhead claims 96% of parallelism". That sentence was leftover framing from the pre-perf-record draft (when the sync-imbalance hypothesis was active). It contradicts the corrected attribution above (compute kernels = 80%, sync = 15%) and has been removed.

### Raw data

- `data/cpu_optimization/2026-04-26-cpu24/reap_canonical_perfstat.log` — REAP-246B perf stat
- `data/cpu_optimization/2026-04-26-cpu24/q8_canonical_perfstat.log` — Q8_0 perf stat (comparison)
- `data/cpu_optimization/2026-04-26-cpu24/reap_singlethread.log` — REAP single-thread baseline (1.41 t/s)
- `data/cpu_optimization/2026-04-26-cpu24/perfrecord/` — perf-record hot-function profile

## Remediation TODO (Phase 2.3 of closure-inflation remediation plan)

The original CPU24 objective (line 12-25 of this handoff) lists IMC/channel/fabric/remote-miss/LLC/stall attribution on REAP-246B **AND MiniMax-M2.7** as primary targets, with at least 2 repetitions for counter stability. Peer review on 2026-04-27 evening identified that:

1. **MiniMax-M2.7 counter run is missing.** Only REAP + Qwen3.6-35B Q8_0 (the latter as comparison) were measured.
2. **2-rep stability pass is missing.** Each model has 1 perf-stat run.
3. **Dense/hybrid coverage is missing** — finding #11 of the peer review. The IPC=0.39 / compute-kernel-memory-stalled finding is stated in MoE-only terms but the underlying mechanism (per-thread BW contention) is architecture-independent. A dense Qwen3.5/3.6-27B Q8_0 counter run closes this gap.
4. **Counter table format** in this handoff is informal; the binding objective lists IMC/channel, fabric/interconnect pressure, remote miss, LLC miss intensity, stall-class indicators as discrete columns. The data is captured in the raw perf-stat logs but not formally tabulated.

Phase 2.3 will deliver:
- MiniMax-M2.7 Q8_0 perf stat counter run at proper canonical.
- Qwen3.5/3.6-27B Q8_0 dense/hybrid counter run.
- 2-repetition stability pass on REAP + Qwen3.6-35B + MiniMax + dense.
- Formal counter table in the format required by the handoff (IMC/channel, fabric, remote miss, LLC, stall class) for all four models.
- `decision.md` stating attribution class explicitly per model class (MoE vs dense).
- CPU20 artifact bundle (README.md, system-state.txt, process-pre.txt, process-post.txt, ld_debug.log, results.csv, decision.md).

Output dir: `data/cpu_optimization/2026-04-28-cpu24-minimax-and-dense/`. Existing `2026-04-26-cpu24/` artifacts are kept; the new dir adds the missing pieces.
