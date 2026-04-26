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
