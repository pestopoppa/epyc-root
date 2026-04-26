# CPU23 — Context-Regime Coverage Matrix

**Status**: ACTIVE (created 2026-04-26)
**Priority**: MEDIUM-HIGH
**Categories**: benchmarking_methodology, inference_serving, hardware_optimization
**Workstream**: Inference Acceleration → CPU Optimization
**Parent index**: [`cpu-inference-optimization-index.md`](cpu-inference-optimization-index.md) (CPU23)
**Related**: [`cpu-benchmark-rigor-and-revalidation.md`](cpu-benchmark-rigor-and-revalidation.md) (CPU20 protocol), [`sarathi-serve-cpu-evaluation.md`](sarathi-serve-cpu-evaluation.md) (CPU17 serving path), [`large-moe-expert-parallelism.md`](large-moe-expert-parallelism.md) (CPU15 class conclusions)

## Objective

Prevent decode-only overgeneralization by validating conclusions across context lengths and mixed prefill/decode interference scenarios.

## Required matrix

Per target model class, run:
1. 2K context
2. 8K context
3. 32K context
4. long-prompt-mid-stream interference scenario

Metrics:
- generation t/s
- TTFT
- decode stall fraction
- per-iteration latency variance

## Target model set

- frontdoor class (Q8_0): Qwen3.6-35B-A3B
- sync-heavy class (Q4_K_M): Coder-30B, Qwen3-Next-80B, REAP-246B, gemma-26B

## Protocol

CPU20 is mandatory:
- canonical baseline shape per model
- explicit cache-state labels
- process hygiene proofs

## Gate for class-level conclusions

No track may claim a class-wide closure/deployment rule unless:
1. all 4 regimes above were measured, and
2. conclusion direction is stable across regimes (or explicitly split by regime)

## Deliverables

- `data/cpu_optimization/<date>-cpu23-context-matrix/`
- summary table with per-regime deltas
- explicit update to CPU15/CPU17 guidance reflecting regime split (if any)
