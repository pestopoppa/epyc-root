# Reviewer Control Plane — Registry-Driven Model-Role Ablation Tournament (H5)

**Status**: active — M3 "compared" milestone; GATED on H4 instrument (P-REV-1) + H6 arms + operator bench windows
**Created**: 2026-07-16 (Architect→Reviewer control-plane series; see index)
**Categories**: benchmark_methodology, agent_architecture, routing_intelligence
**Index**: [`reviewer-control-plane-index.md`](reviewer-control-plane-index.md)
**Related**: [`reviewer-calibration-accounting.md`](reviewer-calibration-accounting.md) (the instrument), [`glm52-reviewer-capability-gates.md`](glm52-reviewer-capability-gates.md) (A4 arm gates), [`autopilot-control-plane-integration.md`](autopilot-control-plane-integration.md) (screening-tier driver), [`mi210-big-model-and-acceleration-roadmap.md`](mi210-big-model-and-acceleration-roadmap.md) (GPU arms)
**Repo**: `epyc-orchestrator` + `epyc-inference-research`

## Objective

Answer the model-role question empirically — which (architect, reviewer, grading-model) assignment maximizes calibrated review value per token — via a **registry-driven staged tournament** over the ~240-model registry, not a fixed condition table (operator 2026-07-16: the report's 7-row matrix is an example only).

## Thesis

Three stages: (1) **pool generation** — architect × reviewer × grader pools drawn from `model_registry.yaml` by capability/speed tier with pruning rules (RAM/VRAM fit, t/s floor, quality floor from existing benches, cross-family preference; staged candidates included: Hy3-295B-IQ1M, MiniMax-M2.7, DeepSeek-V4-Flash, Qwen3-Next-80B, gemma-4-31B, Qwen3.6-27B, Bonsai tier-C); (2) **screening** — cheap small-n sweeps over many pairings, autopilot-driven (H8) on a corpus-v1 subset via eval-tower T0/T1; (3) **confirmation** — full paired N≥100 P-REV-1 runs only for Pareto-promising pairs. Family-preference/collusion is **measured as a covariate, not assumed** (direct measurements found it weak, −0.9..+3.5pp — intake-837; the stronger prior lives in Panickssery 2404.13076, unverified locally).

## Prioritized Task List

- [x] **RM-1 — Pool-generation script** ✅ 2026-07-17 (`scripts/analysis/reviewer_pool_gen.py`; live run: 157 roles → pools 68/77/65 → 5,236 pairings; anchors A0/A1/A3/A4 forced-present, A4 cross-family-flagged; deterministic w/ registry+config sha256 provenance; 19 tests) with pruning rules + provenance (registry rev, pruning config hash); emit the candidate pairing list.
- [x] **RM-1a — Bonsai Q1 default-staging stop**: `epyc-orchestrator` commit `d30593a2` removes Bonsai Q1_0 from `reviewer_pool_gen` `DEFAULT_STAGED_KEYS`; Bonsai remains opt-in/reopen-only until a named quality/protocol fix clears the strict-output blocker. ✅ 2026-07-19
- [ ] **RM-2 — Anchor arms (guaranteed confirmation-tier)**: A0 gates-only (objective-verifier floor); A1 self-review (status quo alias); A3 same-family GPU heavyweight (122B-IQ2 resident, 43.7 t/s, grammar mandatory); A4 cross-family GLM-5.2-IQ2 CPU (target); A4g +hot-expert offload (skew-profile-gated); Ref external judge-of-judge (approved bounded: pinned model-id+date, ~100 sampled decisions, budget-capped).
- [ ] **RM-3 — Screening-tier protocol**: small-n, per-pairing FA/FR/CR estimates with wide CIs; promotion rule to confirmation tier (Pareto on quality-vs-cost); driven by the H8 autopilot action, respecting no-concurrent-inference + placement-queue-not-/chat discipline.
- [ ] **RM-4 — Confirmation-tier protocol**: fully paired (same tasks/prompts/grammar/stop/verifier budget), N≥100/arm, paired flips via `sequential_verdict.quality_trial_statistic`, Holm across metric families; per-domain reporting.
- [ ] **RM-5 — Bias-robustness probe set**: the 6 content-bias injections (authority, self-declared correctness, renaming, reverse-authority, misleading-task, illusory complexity) as a held-out probe → per-reviewer **robustness rate** as a selection axis (small judges more fragile); blinding/randomization controls baked into the harness (sanitized packages, no reference-comparison mode without swap-augmentation).
- [ ] **RM-6 — RA-8 field-order A/B** (evidence-first vs verdict-first GBNF) on the leading arm — opposing hypotheses on record (intake-836 vs intake-837).
- [ ] **RM-7 — With-vs-without verifier-request access** ablation on the winning pair (isolates contextual verification vs second-opinion effect).
- [ ] **RM-8 — Report + registry annotation**: winners' calibration profiles into model registry `measured:` fields; publish claims in P-REV-1 grammar only.
- [ ] **RM-9 — (deferred, LOW) A5 reviewer-as-architect** (GLM-5.2 solo) — only after A4 results justify it.

## Dependency Graph

```text
H4 P-REV-1 + corpus v1 → RM-1 → RM-3 screening (needs H8 driver) → RM-4 confirmation → RM-7 → RM-8
RM-2 anchors: A3 needs GPU-residency lane; A4/A4g need H6 + glm51-reap gates; Ref needs operator budget window
RM-5, RM-6 fold into RM-4 protocol. Operator bench windows gate all inference-heavy runs.
```

## Cross-Cutting Concerns

1. **Single-card contention** — A3/A4g arms use the MI210; sequence behind the parallel session's admission smokes + the operator's GPU bets 1→4 ordering.
2. **Latency accounting** — parallel-reviewer wall-clock models as SUM not MAX on this host; per-arm cost reported alongside quality (keeps "stronger" arms honest).
3. **Saturated-suite hazard** — screening on journal-derived items must include near-miss/ambiguous rows, or arms will tie at ceiling (the corpus exists precisely to avoid this).

## Key Files / Surfaces

- `epyc-inference-research/orchestration/model_registry.yaml` (pool source; `measured:` target)
- H4 ledger + `reviewer_calibration_report.py`; `src/autopilot_core/sequential_verdict.py`
- eval tower T0/T1 (screening); H8 autopilot action (driver)

## Reporting Instructions

Flip checkboxes `✅ YYYY-MM-DD`; screening leaderboards + confirmation results recorded here; winners update H0 + registry; NO claim leaves this handoff without P-REV-1 citation; bench windows requested via OP bundle.

## Evidence Base (intake)

intake-837/838 bias probes + family-preference-as-covariate · intake-836 big-model FR priors + IQ2 quant caveat · intake-834 grading-model insensitivity (2.4pp) · intake-846 fidelity-over-fan-out · audit doc 2026-07-16 · IQ2==Q4 parity (n=212, Δ0.0pp; workspace-root iq2_parity_results.jsonl).
