# Agentic Rubrics → the two-turn reviewer (author once, grade cheap)

**Date:** 2026-07-16
**Companion handoffs:** [`reviewer-decision-plane.md`](../../handoffs/active/reviewer-decision-plane.md) (H3 RD-2), [`reviewer-typed-artifacts.md`](../../handoffs/active/reviewer-typed-artifacts.md) (H2 RA-4), [`reviewer-calibration-accounting.md`](../../handoffs/active/reviewer-calibration-accounting.md) (H4)
**Source:** intake-834 — "Agentic Rubrics as Contextual Verifiers for SWE Agents" (arXiv 2601.04171, ACL 2026 long, Scale AI; cred 5/6, adopt_patterns)
**Scope:** why the reviewer is a two-turn system, and which of their numbers seed our design.

---

## The economics that decide the architecture

Rubric **authoring** is agentic and expensive ($0.245, ~23 API calls, 30-turn repo exploration); **grading** against the rubric is near-free ($0.003/patch, one binary pass per item). Authoring-model capability matters a lot (frontier authors ~20 criteria vs ~10 for small models; removing repo access costs up to −4pp); **grading-model capability barely matters (2.4pp across a wide judge range)**.

On a CPU stack where the heavyweight reviewer decodes at ~5-20 t/s, this inverts the naive design: do **not** run GLM-5.2 on every candidate. Instead (H3 RD-2): the heavyweight model **authors a cached rubric once per task-class/domain-template**; a cheap fast model (frontdoor-class) **grades every candidate** against it. Re-review = a cheap grade, not a heavyweight pass. Our domains recur, so caching amortizes even better than in their per-instance setting — this is the structural fix for the measured plan-review latency regression.

## Numbers we seed from (observation-grade)

- Rubric-vs-test alignment ROC-AUC **0.886**; GT-pass scores cluster 0.85-1.0, GT-fail disperse ~0.4-0.5 → decision bands **S≥0.85 approve / S≤0.5 reject / middle → request_changes|request_evidence**.
- Grading flakiness 2% (strong judge) / 9% (weak) → **majority-of-k near band edges**; log flakiness per grading model.
- Tests-pass-but-rubric-low quadrant = **54% real high-utility issues / 46% over-specification false positives** → verifier precedence refined: objective-PASS + rubric-LOW → `request_evidence`, never `reject`.
- Best@16 +3.5-4.6pp over the strongest execution-free baseline — rubric signal is additive to tests, not a substitute.

## Artifact shape (H2 RA-4)

`{text, axis, weight ∈ {1,2,3}}`, aggregated S=Σ(wᵢsᵢ)/Σwᵢ. Their four axes (file-change / spec-alignment / integrity / runtime) port to domain-general variants: QA → {grounding/citations, question-alignment, integrity/no-fabrication, completeness}; math → {answer, method validity, integrity, case coverage}. Both artifacts (rubric + grade) are GBNF-constrainable. Persist **full rubric + per-item grades** in corpus rows — their distillation ablation shows a rubric-*generator* fine-tune beats a binary-classifier fine-tune on identical data; a verdict-only ledger throws away the transferable structure.

## Do NOT adopt / hazards

- **Rubric-as-RL-reward.** The critique literature (Verification Horizon 2606.26300; Reward Hacking in Rubric-Based RL 2605.12474 + reproduction 2606.04923) shows static rubric judges get gamed (length/verbosity exploitation) and "fundamental limitations, not model quirks." We use rubrics for inference-time gating/reranking (safer). The moment any learning loop closes over the ledger: objective-verifier precedence stays, author and grade with **different model families**, never optimize against the rubric score alone.
- Harden the Integrity axis against verbosity/complexity inflation from day one (ties into the judge-bias evidence — see the calibration-evidence dive).
- No code release for the paper; adopt patterns, not components. Non-code generalization is our hypothesis to validate (nearest analog: 2601.15808, rubric-guided deep-research verification — queued follow-up).

## MEASUREMENT note

Their thresholds/AUC seed our bands as priors; the bands become decision-gating only after re-measurement on corpus v1 under P-REV-1.
