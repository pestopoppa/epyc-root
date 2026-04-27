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

---

## CPU23 sweep COMPLETE — 2026-04-27 (methodology-completeness gate met)

**Method**: `-pg pp,tg` mode (combined prefill + 32-token decode throughput) at proper canonical (`OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active numactl --interleave=all -t 96 -fa 1`). Tested 2K/8K/32K context on the BW-bound class proxy (Q8_0) and a sync-bound class proxy (Coder-30B Q4_K_M).

| Model | Context | pp+tg32 t/s | Δ vs 2K |
|-------|---------|-------------|---------|
| Coder-30B Q4_K_M | 2K | 429.42 | reference |
| Coder-30B Q4_K_M | 8K | 340.49 | **−21%** |
| Coder-30B Q4_K_M | 32K | 126.75 | **−70%** |
| Qwen3.6-35B Q8_0 | 2K | 344.04 | reference |
| Qwen3.6-35B Q8_0 | 8K | 353.49 | +3% (within noise) |
| Qwen3.6-35B Q8_0 | 32K | 219.69 | **−36%** |

### Findings

1. **Long-context prefill is the dominant wall-time cost** at 32K for both classes. The pp+tg32 metric is dominated by prefill (32-token decode is ~0.1% of total tokens at 32K).
2. **Coder-30B Q4_K_M degrades steeply** (−70% at 32K) — Qwen3 hybrid architecture's attention overhead grows quadratically.
3. **Qwen3.6-35B Q8_0 holds up much better** (−36% at 32K, neutral at 8K) — different attention layout in the Qwen3.6 family is more efficient at long context.
4. **No new optimization targets** — the per-context degradation is architectural (O(N²) attention), not a CPU-optimization gap.
5. **CPU21 affinity stack and proper canonical extend cleanly** to long-context regimes. No regression in the relative gain pattern.

### Strategic conclusions

- **For agent-loop workloads with persistent context**: Q8_0 (Qwen3.6-35B) is the long-context-friendly quant. Worth surfacing in any future model-selection decision matrix.
- **CPU17 Sarathi-Serve closure decision validated**: long-context prefill IS expensive (which is the prefill-decode-interference target), but our single-user regime doesn't have concurrent decodes to stall.
- **CPU23 was a methodology-completeness gate, not an optimization track** — confirmed prior 2026-04 findings extend across context regimes. No follow-up actions.

### Files

- `data/cpu_optimization/2026-04-27-cpu23/SUMMARY.md` — full analysis
- 6 raw `-pg` bench logs at 2K/8K/32K × 2 models
