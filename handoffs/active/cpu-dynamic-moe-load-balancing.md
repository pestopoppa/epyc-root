# CPU22 — Dynamic MoE Load Balancing

**Status**: ACTIVE — work-stealing prototype upcoming as Phase 3 of closure-inflation remediation plan (corrected 2026-04-27 evening). Earlier "closed by inference" framing was incorrect: CPU22's binding gates (≥10% on 2 sync-bound models, no crash, PPL bit-exact) require a prototype run, not a sync-share argument. CPU24's 15% sync-share finding caps the realistic gain *target*; it does NOT close the track.
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

## Closure-inflation correction (2026-04-27 evening)

A prior progress entry (`progress/2026-04/2026-04-26.md`) marked CPU22 as "✅ closed — gain capped at 15% sync share" based on the CPU24 attribution finding. Peer review on 2026-04-27 evening identified this as closure-by-inference: the 15% sync-share argument bounds the *expected gain ceiling* but does not exercise CPU22's stated empirical gates (≥10% throughput on 2 sync-bound Q4_K_M models, no crash/deadlock in 5-min sustained run, PPL bit-exact). **Status reverts to ACTIVE; closure requires prototype run per the gates above.**

The 15% sync ceiling is preserved as guidance: a successful work-stealing implementation would convert some fraction of the 15% sync time into productive compute, with theoretical upside ≈7-15% on the sync-bound MoE Q4_K_M class. If the prototype hits ≥10%, it's a deployable opt-in. If it lands in the 5-10% band, it's experimental opt-in (NOT v5 cherry-pick). If it lands negative or null, the track closes honestly via measurement.

## Remediation TODO (Phase 3 of closure-inflation remediation plan)

User decision: **full work-stealing implementation** (handoff scope item #1, the most aggressive option).

Phase 3 will deliver:
1. **Design** — read existing static-modulo expert sharding in `ggml/src/ggml-cpu/ggml-ep-shard.cpp` and `ggml_compute_forward_mul_mat_id` path in `ggml/src/ggml-cpu/ggml-cpu.c`. Design shared work queue of expert tiles; threads poll for next tile when local work exhausted; bounded migration; lock-free CAS where feasible, spinlock fallback.
2. **Implementation** — env-gated `GGML_EP_WORK_STEALING=1` (default off). Branch from `feature/cpu-ep-inter-process` HEAD `29a69599a`. Build green with `-DGGML_NUMA_MIRROR` off (default) and on (preserve experimental NUMA_MIRROR build).
3. **Validation** — PPL bit-exact on Coder-30B Q4_K_M wiki.test full 32-chunk under env=on vs env=off. Throughput sweep on 2 sync-bound Q4_K_M proxies (Coder-30B + Next-80B) at proper canonical. Stability: 5-minute sustained run, no crash/deadlock/PPL drift. CPU20 artifact bundle.
4. **Outcome documentation** — three terminal states:
   - **WIN ≥10%**: env-gated default-off, deployable opt-in, cherry-pick candidate for v5.
   - **WIN 5-10%**: experimental opt-in, NOT cherry-pick candidate for v5.
   - **NULL or NEGATIVE**: implementation reverted or kept off; track honestly closed via test (replaces the corrected closure-by-inference).

Output dir: `data/cpu_optimization/<phase3-completion-date>-cpu22-work-stealing/`.

Effort: ~3-5 days focused.
