# CPU22 — Dynamic MoE Load Balancing

**Status**: ACTIVE (created 2026-04-26)
**Priority**: HIGH
**Categories**: hardware_optimization, moe_optimization, inference_serving
**Workstream**: Inference Acceleration → CPU Optimization
**Parent index**: [`cpu-inference-optimization-index.md`](cpu-inference-optimization-index.md) (CPU22)
**Related**: [`cpu-openmp-runtime-scheduling-matrix.md`](cpu-openmp-runtime-scheduling-matrix.md) (CPU21 prerequisite), [`cpu-uncore-fabric-attribution.md`](cpu-uncore-fabric-attribution.md) (CPU24 prerequisite), [`large-moe-expert-parallelism.md`](large-moe-expert-parallelism.md) (CPU15 root mechanism context)

## Objective

Replace static expert partitioning assumptions with runtime-aware balancing so idle CCDs/threads can absorb overloaded expert work.

## Why this exists

Static modulo expert assignment repeatedly produced structural imbalance:
- some workers/CCDs idle while others gate wall-time
- barrier improvements alone cannot recover this class of loss

CPU22 is the first mechanism track after attribution confirms imbalance is dominant.

## Scope

Candidate mechanisms:
1. Work-stealing queue for expert tiles inside `mul_mat_id`
2. Token-to-expert runtime rebalance with bounded migration
3. Hybrid strategy: static coarse partition + dynamic spillover

## Prerequisites

1. CPU20 protocol artifacts for baseline + comparison set
2. CPU21 runtime matrix complete (to avoid conflating runtime and mechanism effects)
3. CPU24 attribution complete (to confirm imbalance vs fabric/uncore bottleneck dominance)

## Measurement gates

1. Throughput: >=10% win on at least 2 sync-bound Q4_K_M models
2. Stability: no crash/deadlock in 5-minute sustained run
3. Quality: no material PPL drift vs baseline

If gates fail, keep scaffolding off by default and document failure mode.

## Deliverables

- design note for chosen balancing strategy
- env-gated prototype implementation plan
- artifact bundle under `data/cpu_optimization/<date>-cpu22-dynamic-balance/`
