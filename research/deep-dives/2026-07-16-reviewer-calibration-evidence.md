# Reviewer calibration evidence: overcorrection, judge bias, and corpus design

**Date:** 2026-07-16
**Companion handoffs:** [`reviewer-calibration-accounting.md`](../../handoffs/active/reviewer-calibration-accounting.md) (H4), [`reviewer-model-ablations.md`](../../handoffs/active/reviewer-model-ablations.md) (H5), [`reviewer-decision-plane.md`](../../handoffs/active/reviewer-decision-plane.md) (H3)
**Sources:** intake-836 (Are LLMs Reliable Code Reviewers?, ASE 2025 + Springer AutoSE, cred 5/6) · intake-837 (Bias in the Loop, preprint, 4/6) · intake-838 (Don't Judge Code by Its Cover, EACL 2026 Findings, 5/6) · intake-844 (RACE-bench, 4/6) · intake-845 (c-CRAB, 5/6)
**Scope:** the empirical basis for the FA/FR ledger design, review-prompt controls, and near-miss corpus schema.

---

## The five load-bearing findings

1. **Overcorrection dominates (FR ≫ FA, 10:1 to 440:1).** Large models push false-accepts toward zero while false-rejecting 26-88% of *correct* code; "explain + propose fix" prompting DOUBLES false-rejects (GPT-4o MBPP 35.9→87.9%); 62% of false-reject rationales are hallucinated requirements or unfounded logic claims. → H4 runs **symmetric FA AND FR tolerance e-processes**; FA/FR ratio is a first-class ledger column; H3 prompts are framing-neutral with fix-suggestions only post-verdict.
2. **Executable counterfactuals fix it.** Requiring the reviewer's proposed fix to objectively pass tests the original fails cut FR ~40pp. → H3's reject-admissibility rule: a `reject` without an objective-verifier hit or passing counterfactual is logged *unverified* and down-weighted.
3. **Pointwise grading dodges position bias (~41pp, the largest axis) but NOT content bias.** Self-declared-correctness/authority still shifts pointwise verdicts ~18pp (and degrades incorrect-code detection 24-29pp); verbosity (−16..−36pp) lives in the weights and cannot be prompted away; illusory complexity +9.6pp. → CandidatePackage **sanitization** (strip architect self-assessment/confidence/"refined" labels) is mandatory (H2); verbosity/complexity are measured tournament covariates.
4. **Reliability ≠ consistency.** Bias can inflate test-retest Consistency Rate to ~81% while accuracy is near-random. → CR is reported *alongside* FA/FR/Brier/ECE, never instead of them (H4 RC-4). Family-preference was measured WEAK (−0.9..+3.5pp) in these sources → cross-family anti-collusion is a **measured covariate, not an assumption** (H5; the stronger prior is Panickssery 2404.13076, unverified locally).
5. **Detection ≠ diagnosis.** Models detect THAT something fails (95-100%) far better than WHY (52-75%), and rationales often contradict verdicts. → corpus rows record `rationale_vs_gold_cause` so right-for-wrong-reason reviewers don't earn calibration credit.

## Corpus design (what the benchmarks contribute)

- **c-CRAB** (mine NOW; CC BY 4.0; base SWE-CARE acquired at `/mnt/raid0/llm/datasets/swe-care/`): executable **fail-then-pass oracles from real human review comments** — one of the two gold-label templates. Its gaps are our lessons: no precision/false-positive axis (we add it); solvable-only filter discards the hardest near-misses (we keep the ambiguous tail for human arbitration); validator/evaluatee circularity (we use ≥2 oracles or arbitration for gate-worthy rows — weak-oracle inflation is real: 47.9% of SWE-bench "resolved" pass on weak tests).
- **RACE-bench** (schema NOW, rows when released): per-module **Recall + OverPrediction** pairs = a ready-made miss/over-flag (FR/FA) instrument for grading *plan* packages, where no diff exists; steps-recall is universally weakest (0.34-0.45) → weight ambiguous items there.
- **Both are 100% natural defects.** Our seeded-mutation slice is a deliberate departure → every row carries `defect_origin ∈ {natural, seeded}` + a natural-defect control slice; decontamination metadata (repo/base_commit/created_at) is mandatory (SWE-Bench-Illusion memorization critique applies to all derivatives).

## Priors for our reviewer arms (hypotheses, not gates)

GLM-5.2-IQ2 and 122B-IQ2 (both large): expect FA≈0 / FR-high, worst under explain-then-fix prompting. IQ2 quant plausibly degrades *why*-diagnosis more than *that*-detection — measure (H6 GC-3), don't assume. Cross-family = better FA coverage + an FR tax from stylistic disagreement. Small judges are MORE bias-fragile — weight the robustness probe heavily in reviewer selection.

## MEASUREMENT note

All numbers above are external-benchmark observations (saturated suites, injected bugs, other domains). Ratios/directions transfer as design priors; **no threshold gates anything until re-measured on our ledger under P-REV-1** (pending operator amendment, OP-5a).
