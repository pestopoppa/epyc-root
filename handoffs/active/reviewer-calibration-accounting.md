# Reviewer Control Plane — Calibration Accounting: FA/FR Ledger + Near-Miss Corpus + P-REV-1 (H4)

**Status**: active — M2 "measured" milestone; the series centerpiece (every downstream claim is gated on this instrument)
**Created**: 2026-07-16 (Architect→Reviewer control-plane series; see index)
**Categories**: benchmark_methodology, agent_architecture
**Index**: [`reviewer-control-plane-index.md`](reviewer-control-plane-index.md)
**Related**: [`evidence-plane-ledger-and-sequential-verdicts.md`](evidence-plane-ledger-and-sequential-verdicts.md) (ledger conventions), [`eval-tower-verification.md`](eval-tower-verification.md) (EV-tier ECE/AUC — REUSE, do not duplicate), [`reviewer-model-ablations.md`](reviewer-model-ablations.md) (H5 consumes this instrument)
**Gate**: starts after H1 TM-8 coverage + H3 shadow decisions flowing.
**Repo**: `epyc-orchestrator` (ledger/scripts) + `epyc-root` (MEASUREMENT amendment draft)

## Objective

Build reviewer calibration accounting — decision ledger, gold labels from objective verifiers, near-miss decision corpus, calibration metrics, sequential monitoring — and draft MEASUREMENT protocol **P-REV-1** for operator sign-off. Layer A throughout.

## Thesis

Two dive results reshape the report's design. First, **overcorrection dominates** (false-reject ≫ false-accept, 10:1-440:1 — intake-836), so the ledger runs **symmetric FA AND FR tolerance e-processes** (auto-demote a live reviewer to shadow on either breach), with the FA/FR *ratio* as a first-class column. Second, **the corpus is the instrument**: versioned, dual-gold-labeled (executable oracles + reasoning modules), spanning domains (the autopilot journal already holds thousands of scored per-question outcomes across general/hotpotqa/simpleqa/instruction_precision/thinking/code — non-code mining is cheap).

## Prioritized Task List

- [ ] **RC-1 — `review_ledger` table** in the trace DB: `(decision_id, ts, reviewer_model_quant, grading_model, rubric_version, corpus_id, candidate_id, domain, decision, tripwire, confidence, gold_label, gold_source, gold_instrument_version, rationale_cause_match, latency_ms, tokens, family_match_flag, era)` with provenance links to trace events.
- [ ] **RC-2 — Gold-label pipeline**: candidate outcome from gate_runner (format/lint/typecheck/unit) and/or eval-tower tier scorers; human arbitration only for sampled escalations + the ambiguous/unsolvable tail. **Gate-worthy rows need ≥2 oracles or human arbitration** (weak-oracle inflation: 47.9% of SWE-bench "resolved" pass on weak tests — intake-845).
- [ ] **RC-3 — Near-miss decision corpus v1** (versioned: corpus id + hash): (a) autopilot journal approve/reject + scored per-question history across suites; (b) seeded-defect mutations of known-good outputs; (c) known-bad candidates from bug-reports; (d) mined c-CRAB rows + SWE-CARE pool (`/mnt/raid0/llm/datasets/`, acquired 2026-07-16). **Row schema**: dual gold labels (executable-oracle verdict + reasoning-module labels), `defect_origin ∈ {natural, seeded}` + a natural-defect control slice, decontamination metadata (repo/base_commit/created_at — SWE-Bench-Illusion applies to all SWE-bench derivatives), `rationale_vs_gold_cause` (catch right-for-wrong-reason: models detect THAT 95-100% but WHY only 52-75%). Do NOT copy c-CRAB's solvable-only filter — the ambiguous tail routes to human arbitration.
- [ ] **RC-4 — `scripts/analysis/reviewer_calibration_report.py`**: FA rate, FR rate, FA/FR ratio, acceptance rate, request-evidence yield, escalation precision (sampled), Brier, ECE, AUC, **Consistency Rate (test-retest ≥2 runs — bias can inflate CR to 81% at near-random accuracy)**, parse-failure rate — per (reviewer config × grading model × rubric version × corpus version × domain). **Reuse EV-tier ECE/AUC implementations** (`eval-tower-verification.md` T1) — do not duplicate. Metrics: **pass^k for review decisions** (consistency gates deploys), pass@k for candidate generation.
- [ ] **RC-5 — Sequential monitoring**: FA-tolerance AND FR-tolerance e-processes on `src/autopilot_core/sequential_verdict.py` (`EProcessState`, `SequentialPolicy`) — live breach on either side auto-demotes the reviewer to shadow. Enforcement, not new decision theory (Fable5 posture).
- [ ] **RC-6 — Draft MEASUREMENT amendment P-REV-1** (operator PR — MEASUREMENT.md is human-amendment-only): instrument = (corpus id+hash, gold-label source+version, reviewer model+quant+grammar-flag, grading model, rubric version, shadow/live mode, n); changing any = new instrument version; claim grammar `reviewer FA x%, FR y% (n=…, corpus rev-…, gold=…) [P-REV-1, date, attest …]`; directions stated; external judge-of-judge samples cite pinned API model-id+date as part of the instrument. Speed/latency claims stay under existing P-AB-1/P-SPEED-OBJ.
- [ ] **RC-7 — Evidence-plane alignment**: per-decision rows follow per-question-ledger conventions (decision ≈ question); cross-ref both handoffs.
- [ ] **RC-8 — Baseline run**: current self-review (architect alias) in shadow on corpus v1 — the first FA/FR numbers. **Broken-grader guardrail**: read transcripts before trusting a surprising number (CORE-Bench 42→95% was grader repair, not model change).
- [ ] **RC-9 — Rubric persistence**: store full rubric + per-item grades in corpus rows, not just verdicts (rubric-generator distillation > classifier — intake-834); if the instrument changes later, append eras per `instrument_eras.yaml` conventions.

## Dependency Graph

```text
H1 TM-8 + H3 shadow flow → RC-1 → RC-2 → RC-3 corpus v1 → RC-4 report → RC-5 e-processes → RC-8 baseline
RC-6 P-REV-1 draft (parallel after RC-1; operator PR gates all decision-grade claims in H5/H7)
RC-7, RC-9 (parallel)
```

## Cross-Cutting Concerns

1. **Layer A / trust boundary** — reviewer metrics do NOT enter the T0-T3 model-quality axes; they are a separate instrument gating *reviewer-role promotion*. The plane invokes the tower; the tower never depends on the plane.
2. **Anti-reward-hacking** — any learning loop off this ledger must keep objective-verifier precedence, cross-family author/grade separation, and never optimize directly against the rubric score (intake-834 critique lit: length exploitation is the known failure).
3. **Domain generality** — calibration reported per-domain; expect reviewer value highest on planning/reasoning-heavy suites, lowest on saturated factual ones.

## Key Files / Surfaces

- trace DB (H1) — `review_ledger` home; `src/autopilot_core/sequential_verdict.py`
- `scripts/autopilot/eval_tower.py` + `rubric_scoring.py` (EV-9/ECE/AUC reuse)
- `/mnt/raid0/llm/datasets/` (SWE-CARE, c-CRAB, RewardBench 1/2, JudgeBench, LLMBar — see `BENCHMARKS.md`)
- `/workspace/MEASUREMENT.md` (P-REV-1 target; operator PR)
- autopilot journals (`orchestration/autopilot_journal*.jsonl` — read ALL rotated shards)

## Reporting Instructions

Flip checkboxes `✅ YYYY-MM-DD`; corpus versions and first FA/FR numbers recorded here + H0 milestone table; P-REV-1 text goes to the operator decision queue (§A00) — do not self-approve; all pre-P-REV-1 numbers are observations, never decision-gating.

## Evidence Base (intake)

intake-836 FR≫FA asymmetry + rationale-vs-cause · intake-837 Consistency Rate · intake-844 Recall/OverPrediction plan-grading template · intake-845 executable oracles + corpus mining rules · intake-846 pass^k + broken-grader guardrail · intake-834 rubric persistence + decision bands · audit doc 2026-07-16 · dataset manifest B13.
