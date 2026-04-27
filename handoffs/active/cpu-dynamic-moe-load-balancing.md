# CPU22 — Dynamic MoE Load Balancing

**Status**: CLOSED via test 2026-04-28 (Phase 3 of remediation) **for the global-tile-queue work-stealing design only**. The handoff's original candidate list (Scope section below) has three designs: (1) global work-stealing queue, (2) token-to-expert runtime rebalance with bounded migration, (3) hybrid coarse-static + dynamic spillover. **Only design #1 was implemented and tested.** Work-stealing prototype implemented (`GGML_EP_WORK_STEALING=1`, env-gated default-off in `ggml/src/ggml-cpu/ggml-cpu.c`). PPL bit-exact at 12 chunks. Throughput gate (≥10% on 2 sync-bound Q4_K_M models) **NOT MET for design #1**: -2.3% Coder-30B, -0.3% Next-80B (noise), -0.8% REAP-246B (noise) at 5-rep proper canonical. Single-atomic contention overhead at 96 threads dominates over the limited (CPU24's 15% sync ceiling) imbalance-recovery gain. Track closes honestly via empirical measurement for design #1; replaces prior closure-by-inference. **Designs #2 and #3 remain untested** and are not closed by this evidence — they are deprioritized for current single-user NPS4 MoE decode given the 15% sync ceiling, but a future workload (multi-tenant batched, hardware change, or different MoE topology) could re-promote them.
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

## Phase 3 RESULTS — DONE 2026-04-28

Bundle: `data/cpu_optimization/2026-04-28-cpu22-work-stealing/`. Full CPU20 artifact bundle.

### Implementation

Single env-gated path added to `ggml_compute_forward_mul_mat_id` in `ggml/src/ggml-cpu/ggml-cpu.c` (will commit on `feature/cpu-ep-inter-process`). When `GGML_EP_WORK_STEALING=1`:
- ith==0 builds a global tile array (one tile per chunk × per non-empty expert), encoded as int64.
- After existing barrier, all threads pull tiles via single atomic counter (`atomic_fetch_add`).
- 512 KB static tile buffer (256 experts × 256 chunks max, generous for any production model).
- Excluded paths (falls through to existing): EP master/worker drone, per-CCD sharding, master-parker mode.

### Validation results

**PPL bit-exact**: Coder-30B Q4_K_M wiki.test chunks 1-12: PPL = 11.1146 ± 0.62405 in both env=0 and env=1 (byte-identical).

**Throughput gate (5-rep, proper canonical)**:

| Model | env=0 | env=1 | Δ | Verdict |
|---|---|---|---|---|
| Coder-30B Q4_K_M | 53.12 ± 0.10 | 51.89 ± 0.07 | -2.3% | regression |
| Next-80B Q4_K_M | 23.36 ± 0.03 | 23.29 ± 0.07 | -0.3% | within noise |
| REAP-246B Q4_K_M | 6.64 ± 0.01 | 6.59 ± 0.02 | -0.8% | within noise |

**Gate threshold (≥10% on at least 2 of 3 sync-bound models): NOT MET.**

3-rep vs 5-rep gotcha noted: initial 3-rep Next-80B showed +6.3% (artifact); 5-rep converged to neutral. Lesson: ≥5 reps required for sub-5% deltas on this hardware.

### Why it doesn't deliver

- CPU24's 15% sync share bounds the gain ceiling.
- Existing per-expert chunked path **already has chunk-level work-stealing** (atomic_fetch_add per expert; threads progress through experts independently with no per-expert barrier).
- Single-atomic contention overhead at 96 threads (~30 ns × ~12K tiles per op = ~360 µs/op × ~100 ops/token = ~36 ms wall added) dominates over the limited imbalance-recovery gain.
- Tile-decode + per-tile dimension recompute adds further per-tile overhead.

### Code disposition

Env-gated default-OFF in the codebase, preserved as documented dead-code-by-default for future hardware where atomic-contention overhead is lower OR a workload emerges with severe expert imbalance >7-15% sync share (would require new CPU24 attribution).

**Reopen criteria**:
- New CPU24 attribution shows sync share >25% on a workload.
- Algorithmic change (e.g., MoE-Spec budgeted-expert verification) introduces compounding imbalance the global queue could fix.
- Hardware change reduces atomic-contention overhead (different topology, different barrier mechanics).
