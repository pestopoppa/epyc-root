# 2026-07-06 — CoT accuracy↔token-tradeoff study: COMPLETE (scaffold + verifier characterized across 3 beneficiary archs)

## Summary

Closed the operator-driven CoT / accuracy-vs-token-efficiency study. The reframe (2026-07 arc): evaluate accuracy-vs-token features (scaffold sidecar, own-reasoning, verifier/selector) by **rescue-rate on tasks the cheap path FAILS** and by **blended CPU/GPU wall-clock cost** — not token-efficiency. All experiments GPU-only on the MI210 (35B generator/beneficiary, Qwable-4B reasoner, dense 27B/31B beneficiaries), seed 42, production sampling.

## Final result — three beneficiary archs × three levers

**GPQA reasoning diagnostic (wide caps; the cheap-path-FAILS distribution):**

| lever | 35B-A3B (sparse MoE) | Qwen3.6-27B (dense-FFN-GDN) | gemma-4-31B (pure dense) |
|---|---|---|---|
| scaffold **quality** | +25pp (48→73%) | **+3/10 (6→9)** | neutral (8=8, saturated) |
| scaffold **CPU-tok** | ~180 (+2073 GPU) | **176** vs 9041 ownthink | **98** vs 3049 ownthink |
| own-reasoning (ownthink) | +19pp | none (6=6) | none (8=8) |

- **Scaffold as capability-transplant on CODE → FALSIFIED** (literature-consistent: amplifier-not-substitute, arXiv:2605.28913). Reasoning is elicited, not installed.
- **Scaffold as a COST lever → ROBUST, architecture-independent.** Caps CPU tokens at ~100–175 vs the beneficiary's own 3,000–9,000 = **20–50× fewer expensive-device tokens**, reasoning offloaded to the GPU. Holds across sparse-MoE / dense-GDN / pure-dense.
- **Scaffold as a QUALITY lever → HEADROOM-CONDITIONAL.** Rescues the overthinking-and-weak 27B (6→9); no-ops the already-saturated gemma-31B (8=8). Lifts quality only where the beneficiary is weak-and-overthinking.
- **Both dense models: ownthink ≈ nothink** (own reasoning = wasted CPU cost, no quality gain); the sparse-MoE 35B differed (+19pp) — suggestive that sparse-MoE reasons more productively on GPQA (n=10 caveat).

**Verifier / selector (reasoner grades N candidates, best-of-N) — 3 benches:**

| bench | pass@1 | oracle best-of-N | verifier-sel | gap → recovered |
|---|---|---|---|---|
| cruxeval | — | — | — | no candidate divergence |
| GSM8K (n=40) | 39/40 (97%) | 39/40 | 39/40 | saturated, no gap |
| **GPQA (n=40)** | 25/40 (62%) | 28/40 (70%) | **26/40 (65%)** | +8pp ceiling → **+2pp captured** |

- **MARGINAL on this stack.** Even in the competence band (GPQA 62%), candidate divergence is small: n_passing dist {0:12, 1:2, 3:1, 4:1, 5:24} — **36/40 questions are per-question bimodal** (systematic error, not stochastic). Best-of-N only fixes *stochastic* errors; ceiling is structurally low (+8pp), verifier captured +2pp.
- Verifier **judgment is sound** (selection-acc 93–100% with the corrected correctness-first prompt) but inert without a gap. Needs BOTH genuine candidate diversity AND a verifier more competent than the generator on the contested items — both limited on a GPU-constrained small-reasoner stack.

## Related closed items (this arc)
- Self-debug reason↔execute loop (GPU-only), generator>beneficiary (Qwable→gemma-26B), Qwable-standalone GPQA control — all tested; scaffold benefit dominated by standalone routing where the reasoner is itself strong.
- MTP temperature convergence (~neutral at production temp 0.2; three-way flip-flop root-caused to temp-0 measurement) — see `feedback_production_sampling_seed_not_temp0`.
- gemma-IQ4 NO-GO, stream-K already-live, KV-quant DEFER, 122B/80B IQ2 residency VIABLE + eval-parity PASS.

## Deployment implication (for autopilot / episodic memory)
The scaffold is a **deployable CPU-cost lever** for a RAM+CPU-hosted large beneficiary: offload reasoning to the cheap GPU reasoner, cap the expensive CPU-decode tokens. Its quality payoff is conditional — episodic memory should gate it to the *weak-and-overthinking* per-task-class regime (where nothink fails and the beneficiary over-reasons), matching the blended-cost objective autopilot already optimizes (quality, speed, −cost, reliability). The verifier/selector is **not** worth deploying as-is (marginal, needs stochastic-error workloads).

## Handoff / next
`handoffs/active/gpu-cot-scaffold-sidecar.md` — full arc persisted (commits through `60ac3817`). CoT study is COMPLETE. Remaining open campaign levers are GPU *throughput* benchmarks in `fable5-window2-findings-05c-mi210-lever-category-matrix.md` §4 (MTP-fp16, tree-draft pure-dense, FA-decode MoE frontdoor) — each needs a per-run speed-bench go-ahead (benchmarking discipline: no autonomous llama-bench).
