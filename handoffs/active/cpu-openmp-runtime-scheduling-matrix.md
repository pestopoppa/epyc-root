# CPU21 — OpenMP Runtime And Scheduling Matrix

**Status**: ACTIVE (created 2026-04-26)
**Priority**: HIGH
**Categories**: hardware_optimization, inference_serving, runtime_tuning
**Workstream**: Inference Acceleration → CPU Optimization
**Parent index**: [`cpu-inference-optimization-index.md`](cpu-inference-optimization-index.md) (CPU21)
**Related**: [`cpu-benchmark-rigor-and-revalidation.md`](cpu-benchmark-rigor-and-revalidation.md) (CPU20 gate), [`cpu-hierarchical-barrier.md`](cpu-hierarchical-barrier.md) (single variant falsified), [`cpu-dynamic-moe-load-balancing.md`](cpu-dynamic-moe-load-balancing.md) (CPU22 follow-on)

## Objective

Test whether sync-heavy Q4_K_M regressions are recoverable by OpenMP runtime/scheduling choices before doing deeper kernel surgery.

## Why this exists

CPU4 showed one hierarchical barrier variant is net-negative. That does **not** close the sync-class. The remaining low-cost branch is runtime-level tuning:
- `libgomp` vs `libomp`
- schedule policy/chunking
- affinity/bind permutations
- spin/yield behaviors

## Scope

Target models:
- Qwen3-Coder-30B-A3B Q4_K_M
- Qwen3-Next-80B-A3B Q4_K_M
- REAP-246B-A35B Q4_K_M
- gemma-4-26B-A4B-it Q4_K_M

Out of scope:
- algorithmic load balancing (CPU22)
- >150B root-cause attribution counters (CPU24)

## Matrix

1. Runtime: `libgomp`, `libomp`
2. Schedule: `static`, `dynamic`, `guided`
3. Chunk: `1`, `4`, `8`, `16`
4. Affinity: `OMP_PROC_BIND={false,close,spread}`, `OMP_PLACES={cores,threads}`
5. Wait policy: runtime defaults + explicit spin/yield knobs when available

## Protocol requirements

All runs must follow CPU20 protocol:
- canonical baseline rerun first
- process hygiene snapshots
- LD path identity proof
- replicated measurements (`r >= 3` for >2% claims)

## Gates

1. If any config yields >=5% gain on at least 2 of 4 sync-bound models with no quality drift:
   keep runtime profile as deployable tune and feed CPU22 with updated bottleneck shape.
2. If all configs are <=2% or regress:
   mark runtime branch exhausted and move to CPU22 directly.

## Deliverables

- `data/cpu_optimization/<date>-cpu21-openmp-matrix/` artifacts
- table of top 5 configurations by model
- recommended default runtime profile (or explicit "no deployable profile")
