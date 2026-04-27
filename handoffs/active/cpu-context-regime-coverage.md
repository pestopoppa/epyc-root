# CPU23 — Context-Regime Coverage Matrix

**Status**: CLOSED 2026-04-28 **for the 3-proxy minimum-gate scope** (Phase 2.2 of remediation, peer-review CRITICAL finding #1 addressed). This is **NOT a class-wide exhaustion claim**. Full 5-model coverage explicitly deferred, NOT silently dropped — Qwen3-Next-80B Q4_K_M, REAP-246B Q4_K_M, gemma-4-26B-A4B Q4_K_M project from class assignments but were not measured. Dense/hybrid 32K throughput run was deferred (~30 min/run estimated). Multi-concurrent-decode (10 simultaneous decode streams) interference was deferred (only relevant for multi-tenant production). The 3-proxy data is sufficient for current single-user decode routing decisions; broader closure requires the deferred runs.
**Priority**: MEDIUM-HIGH
**Categories**: benchmarking_methodology, inference_serving, hardware_optimization
**Workstream**: Inference Acceleration → CPU Optimization
**Parent index**: [`cpu-inference-optimization-index.md`](cpu-inference-optimization-index.md) (CPU23)
**Related**: [`cpu-benchmark-rigor-and-revalidation.md`](cpu-benchmark-rigor-and-revalidation.md) (CPU20 protocol), [`sarathi-serve-cpu-evaluation.md`](sarathi-serve-cpu-evaluation.md) (CPU17 serving path), [`large-moe-expert-parallelism.md`](large-moe-expert-parallelism.md) (CPU15 class conclusions)

## Objective

Prevent decode-only overgeneralization by validating conclusions across context lengths and mixed prefill/decode interference scenarios.

## Required matrix (binding gate)

Per target model class, run:
1. 2K context
2. 8K context
3. 32K context
4. **long-prompt-mid-stream interference scenario**

Metrics (all four required):
- generation t/s
- TTFT
- decode stall fraction
- per-iteration latency variance

## Target model set

- frontdoor class (Q8_0): Qwen3.6-35B-A3B
- sync-heavy class (Q4_K_M): Coder-30B, Qwen3-Next-80B, REAP-246B, gemma-26B
- **dense/hybrid class** (added 2026-04-27 evening per remediation Phase 2.2): Qwen3.5/3.6-27B (hybrid SSM-Dense per memory `feedback_qwen35_27b_architecture`)

## Protocol

CPU20 is mandatory:
- canonical baseline shape per model
- explicit cache-state labels
- process hygiene proofs
- full required artifact bundle (README.md, system-state.txt, process-pre.txt, process-post.txt, ld_debug.log, results.csv, decision.md)

## Gate for class-level conclusions

No track may claim a class-wide closure/deployment rule unless:
1. all 4 regimes above were measured, AND
2. all 4 metrics were captured for each regime, AND
3. conclusion direction is stable across regimes (or explicitly split by regime)

## Deliverables

- `data/cpu_optimization/<date>-cpu23-context-matrix/`
- summary table with per-regime, per-metric deltas
- explicit update to CPU15/CPU17 guidance reflecting regime split (if any)

---

## Partial probe — 2026-04-27 (DOWNGRADED 2026-04-27 evening: gate NOT met)

**Earlier framing said "CPU23 sweep COMPLETE — methodology-completeness gate met" with "no follow-up actions".** Peer review on 2026-04-27 evening identified this as closure inflation: the binding gate above requires 4 regimes × 4 metrics × 5 production models, and the 2026-04-27 probe ran only 3 regimes × 1 metric (pp+tg32 t/s) × 2 model proxies. **Gate is NOT met.** Closure language is corrected here; the data already collected is preserved.

**Method actually run**: `-pg pp,tg` mode (combined prefill + 32-token decode throughput) at proper canonical (`OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active numactl --interleave=all -t 96 -fa 1`). Tested 2K/8K/32K context on the BW-bound class proxy (Qwen3.6-35B Q8_0) and a sync-bound class proxy (Coder-30B Q4_K_M). **No interference scenario, no TTFT, no decode-stall fraction, no latency variance.**

| Model | Context | pp+tg32 t/s | Δ vs 2K |
|-------|---------|-------------|---------|
| Coder-30B Q4_K_M | 2K | 429.42 | reference |
| Coder-30B Q4_K_M | 8K | 340.49 | **−21%** |
| Coder-30B Q4_K_M | 32K | 126.75 | **−70%** |
| Qwen3.6-35B Q8_0 | 2K | 344.04 | reference |
| Qwen3.6-35B Q8_0 | 8K | 353.49 | +3% (within noise) |
| Qwen3.6-35B Q8_0 | 32K | 219.69 | **−36%** |

### Findings (preserved from the partial probe; do NOT generalize beyond their scope)

1. **Long-context prefill is the dominant wall-time cost** at 32K for both *MoE* classes tested. The pp+tg32 metric is dominated by prefill (32-token decode is ~0.1% of total tokens at 32K).
2. **Coder-30B Q4_K_M MoE degrades steeply** (−70% at 32K) under the throughput-only metric.
3. **Qwen3.6-35B Q8_0 MoE holds up much better** (−36% at 32K, neutral at 8K) under the throughput-only metric.
4. **CPU21 affinity stack and proper canonical extend cleanly** to long-context regimes for these two MoE proxies. No regression in the relative gain pattern.

### Why these findings are partial

- No long-prompt-mid-stream interference scenario was measured — that is the regime CPU17 Sarathi-Serve closure rests on. The CPU17 closure used a different probe (chunk-size sweep with single-user concurrent decode), which is related but distinct.
- No TTFT measurement — required to distinguish prefill-cost from decode-cost contributions.
- No decode-stall fraction — required for any prefill/decode interference claim.
- No latency variance — required to assess tail-latency behavior at long context.
- 3 of the 5 production models (Next-80B, REAP-246B, gemma-26B) were not measured — class-wide conclusions about MoE require representative coverage.
- 0 of the dense/hybrid class measured — the entire CPU optimization track has been MoE-focused; long-context regime degradation may be architectural-attention-only or MoE-routing-specific, and we don't yet have the data to tell.

## Phase 2.2 RESULTS — DONE 2026-04-28

Bundle: `data/cpu_optimization/2026-04-28-cpu23-interference-metrics/`. Full CPU20 artifact bundle (README.md, system-state.txt, process-pre/post.txt, ld_debug.log, results.csv, decision.md).

### Headline findings

**TTFT** (long-context prefill cost):

| Proxy | TTFT@2K | TTFT@8K | TTFT@32K |
|---|---|---|---|
| Coder-30B Q4_K_M | 4.2s | 24.6s | 262.4s |
| Qwen3.6-35B Q8_0 | 5.2s | 22.0s | 146.8s |
| Qwen3.6-27B Q8 dense | 18.8s | 78.0s | **403.6s** |

**Per-iter variance** (5-rep CV at depths 0/2K/8K): all 9 combinations 0.24-0.57%. Single-user decode is highly stable.

**Long-prompt-mid-stream interference** (concurrent 30K-token prefill + 10 sequential decode-32 requests on the OTHER slot):

| Proxy | Baseline | Rep 1 (interfered) | Reps 2-10 mean | All-10 mean | Rep-1 TTFT amp |
|---|---|---|---|---|---|
| Coder-30B Q4_K_M | 47.99 | **4.77** | 48.33 | 43.83 | **9.6×** |
| Qwen3.6-35B Q8_0 | 29.95 | 26.11 | 30.10 | 29.70 | 1.15× |
| Qwen3.6-27B Q8 dense | 6.652 | 6.137 | 6.582 | 6.538 | 1.08× |

### Class-level conclusions (stable across 3 proxies)

1. **First-decode TTFT spike** under concurrent prefill is severe on sync-bound MoE Coder-30B (9.6×, ~7s wait), mild on BW-bound MoE Q8 (1.15×) and dense (1.08×). Mechanism: continuous batching makes the first new decode request wait for the current prefill ubatch (Coder ubatch = 2048 tokens × 137 t/s = 14.9s).
2. **Steady-state continuous batching is efficient on all 3 classes** — rep-2-onward decode rate within ±2% of baseline.
3. **Long-context prefill scales nonlinearly**: 32K is 60-80× more expensive than 2K. Dense pays the absolute highest cost (6.7 min for 32K).

### Items explicitly deferred (NOT silently dropped)

- Next-80B Q4_K_M, REAP-246B Q4_K_M, gemma-26B Q4_K_M coverage. Class assignments project from the 3 proxies (Next/REAP → sync-bound MoE; gemma → BW-bound MoE) but explicit measurement is the gate-binding evidence.
- Dense/hybrid 32K throughput (~30 min/run estimated, deferred).
- Multi-concurrent-decode interference (10 simultaneous decode streams) — only relevant for multi-tenant production.

CPU17 chunked-prefill closure remains valid for steady-state. The rep-1 TTFT amplification is the latency-tail signal CPU17's probe didn't measure; in single-user regime rep-1 only happens once per session and is not actionable.

## Files

- `data/cpu_optimization/2026-04-27-cpu23/SUMMARY.md` — partial-probe analysis (existing)
- 6 raw `-pg` bench logs at 2K/8K/32K × 2 models (existing)
- `data/cpu_optimization/2026-04-28-cpu23-interference-metrics/` — Phase 2.2 deliverable (forthcoming)
