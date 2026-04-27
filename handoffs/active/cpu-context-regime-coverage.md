# CPU23 — Context-Regime Coverage Matrix

**Status**: ACTIVE — partial methodology probe complete; gate NOT met. Closure-inflation correction applied 2026-04-27 evening (peer review).
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

## Remediation TODO (Phase 2.2 of closure-inflation remediation plan)

User decision: **minimum-to-meet-gate**.

Phase 2.2 will add:
1. Long-prompt-mid-stream interference scenario on Coder-30B Q4_K_M + Qwen3.6-35B Q8_0 (2K decode + concurrent 32K prefill via `llama-server --parallel 2`).
2. TTFT, decode-stall fraction, per-iteration latency variance metrics for the 2K/8K/32K runs already collected.
3. Qwen3.5/3.6-27B (dense/hybrid) added as a 3rd proxy across the same regimes (closes finding #11 of the peer review — the MoE-only test gap).

After Phase 2.2 lands, conclusion will be explicitly scoped: "3-class proxy validated (BW-bound MoE Q8 + sync-bound MoE Q4 + dense/hybrid); full 5-model coverage deferred to a future session, NOT implicitly closed."

Items NOT in Phase 2.2 (deferred, not closed):
- Next-80B, REAP-246B, gemma-26B coverage at 4 regimes × 4 metrics.
- Class-wide deployment-rule conclusions (would require the deferred coverage).

## Files

- `data/cpu_optimization/2026-04-27-cpu23/SUMMARY.md` — partial-probe analysis (existing)
- 6 raw `-pg` bench logs at 2K/8K/32K × 2 models (existing)
- `data/cpu_optimization/2026-04-28-cpu23-interference-metrics/` — Phase 2.2 deliverable (forthcoming)
