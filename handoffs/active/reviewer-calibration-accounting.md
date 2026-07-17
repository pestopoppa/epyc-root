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

- [x] **RC-1 — `review_ledger` table** ✅ 2026-07-17 (additive DDL in store.py + append-only writer `src/trace/review_ledger.py`; provenance links via emit:// paths; verified non-disruptive against a copy of the real 10,326-row DB) in the trace DB: `(decision_id, ts, reviewer_model_quant, grading_model, rubric_version, corpus_id, candidate_id, domain, decision, tripwire, confidence, gold_label, gold_source, gold_instrument_version, rationale_cause_match, latency_ms, tokens, family_match_flag, era)` with provenance links to trace events.
- [x] **RC-2 — Gold-label pipeline** ✅ 2026-07-17 (`gold_labels.py`: gate_runner / eval-tower scorer / corpus-row oracle families; ≥2-agree→multi_oracle gate-worthy; disagree→ambiguous-tail arbitration; pure functions): candidate outcome from gate_runner (format/lint/typecheck/unit) and/or eval-tower tier scorers; human arbitration only for sampled escalations + the ambiguous/unsolvable tail. **Gate-worthy rows need ≥2 oracles or human arbitration** (weak-oracle inflation: 47.9% of SWE-bench "resolved" pass on weak tests — intake-845).
- [x] **RC-3 — Near-miss decision corpus v1** ✅ 2026-07-17 (`corpus_id=nearmiss-v1`, content_sha256 1c50c025…, **11,516 rows / 0 invalid / 0 dupes** at `/mnt/raid0/llm/datasets/nearmiss-corpus-v1/`; per-source c-crab 1005 / swe-care 622 / journal 3683 (qid-hash join, 99.32% recovered) / seeded 6202 (29.1% ≤ cap) / bug-report 4; multi_oracle gate-worthy 6687; ambiguous_tail 475; natural-defect control slice 960; builder `scripts/analysis/corpus_v1/`, orchestrator `9958d819`. LATER PASSES: journal rows need candidate-text recovery (non-inference join or eval re-run) + reasoning-module labels (inference); optional Docker-oracle upgrade of single_oracle rows) (versioned: corpus id + hash): (a) autopilot journal approve/reject + scored per-question history across suites; (b) seeded-defect mutations of known-good outputs; (c) known-bad candidates from bug-reports; (d) mined c-CRAB rows + SWE-CARE pool (`/mnt/raid0/llm/datasets/`, acquired 2026-07-16). **Row schema**: dual gold labels (executable-oracle verdict + reasoning-module labels), `defect_origin ∈ {natural, seeded}` + a natural-defect control slice, decontamination metadata (repo/base_commit/created_at — SWE-Bench-Illusion applies to all SWE-bench derivatives), `rationale_vs_gold_cause` (catch right-for-wrong-reason: models detect THAT 95-100% but WHY only 52-75%). Do NOT copy c-CRAB's solvable-only filter — the ambiguous tail routes to human arbitration.
- [x] **RC-4 — `scripts/analysis/reviewer_calibration_report.py`** ✅ 2026-07-17 (full panel FA/FR/ratio/acceptance/yield/esc-precision/Brier/ECE/AUC/CR/pass^k/parse-fail + Wilson CIs per 5-tuple group; FA/FR classifiers imported from review_ledger; ECE/AUC replicated stdlib-only w/ origin comments — eval-tower versions are inline+sklearn-dependent; observation-stamped pre-P-REV-1): FA rate, FR rate, FA/FR ratio, acceptance rate, request-evidence yield, escalation precision (sampled), Brier, ECE, AUC, **Consistency Rate (test-retest ≥2 runs — bias can inflate CR to 81% at near-random accuracy)**, parse-failure rate — per (reviewer config × grading model × rubric version × corpus version × domain). **Reuse EV-tier ECE/AUC implementations** (`eval-tower-verification.md` T1) — do not duplicate. Metrics: **pass^k for review decisions** (consistency gates deploys), pass@k for candidate generation.
- [x] **RC-5 — Sequential monitoring** ✅ 2026-07-17 (symmetric FA+FR e-processes on EProcessState/SequentialPolicy; either-side CONFIRMED (wealth≥20, anytime-valid α≈.05) latches demote-to-shadow; placeholder tolerances fa=.05 / fr=.25 encode the intake-836 FR≫FA prior — pending P-REV-1; library-only, no live wiring): FA-tolerance AND FR-tolerance e-processes on `src/autopilot_core/sequential_verdict.py` (`EProcessState`, `SequentialPolicy`) — live breach on either side auto-demotes the reviewer to shadow. Enforcement, not new decision theory (Fable5 posture).
- [x] **RC-6 — Draft MEASUREMENT amendment P-REV-1** ✅ 2026-07-17 (amendment text DRAFTED — see "P-REV-1 Draft Amendment Text" section below; **operator PR still outstanding** — MEASUREMENT.md is human-amendment-only): instrument = (corpus id+hash, gold-label source+version, reviewer model+quant+grammar-flag, grading model, rubric version, shadow/live mode, n); changing any = new instrument version; claim grammar `reviewer FA x%, FR y% (n=…, corpus rev-…, gold=…) [P-REV-1, date, attest …]`; directions stated; external judge-of-judge samples cite pinned API model-id+date as part of the instrument. Speed/latency claims stay under existing P-AB-1/P-SPEED-OBJ.
  - [ ] **RC-6a — operator PR + sign-off** (human-amendment-only): land the drafted P-REV-1 blocks into `MEASUREMENT.md` §1/§2/§3 via PR-reviewed amendment with a one-line CHANGELOG (append-or-version). Until merged, every reviewer FA/FR/yield/CR number stays an **observation** and MUST NOT gate any keep/revert/deploy/promote decision in H5/H7.
- [x] **RC-7 — Evidence-plane alignment** ✅ 2026-07-17 (docstring alignment note + `to_question_ledger_row()` adapter stub — decision≈question): per-decision rows follow per-question-ledger conventions (decision ≈ question); cross-ref both handoffs.
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

## P-REV-1 Draft Amendment Text (for operator PR — MEASUREMENT.md is human-amendment-only)

Copy-paste-ready blocks for the operator to land in `MEASUREMENT.md` via a PR-reviewed amendment (append-or-version; one-line CHANGELOG). Grammar matches the existing `P-QUAL-T1` instrument-card style. **This handoff must not edit MEASUREMENT.md — the autopilot/agents may READ it, never write it.** Nothing below is a claim until it is merged AND a measurement citing it exists; all pre-merge reviewer numbers are observations (§5 demote-to-prior default).

### Block 1 — add to §1 Protocol registry (after P-SPEED-OBJ)

> ### P-REV-1 — Reviewer decision calibration (instrument card)
> The instrument for **reviewer-role promotion** — it gates keep/revert/deploy/promote of a *reviewer configuration*, never a model-quality (T0–T3) axis (Layer A; the plane invokes the tower, the tower never depends on the plane).
> - **Instrument** = (**decision corpus id + content hash**, **gold-label source + version** — objective oracle set and/or eval-tower tier scorer, `gold_instrument_version`, ≥2 oracles or human arbitration for gate-worthy rows), **reviewer model + quant + grammar-flag** (GBNF on/off is part of the instrument), **grading model**, **rubric version**, **shadow/live mode**, **n decisions**. Changing **any** field = a **new instrument version** (append an era row per `instrument_eras.yaml`, `scope: reviewer_plane`; never rescale prior FA/FR in place).
> - **Reps**: paired arms per **P-AB-1** (same decisions/prompts/grammar/stop/verifier budget both arms), **N ≥ 100/arm** for a reviewer-promotion decision; failures classified by reason (backend outage / timeout / empty / genuine) with infra-failure rate reported alongside the effect; flag-state attestation across all workers in the run header. **A single-corpus, single-run number is an observation** (never a decision), same rule as every other protocol here.
> - **Consistency**: `pass^k` for review decisions (test-retest ≥2 runs; CR can inflate to ~81% at near-random accuracy under bias — report accuracy next to CR). `pass@k` is for candidate *generation*, not review.
> - **Directions** (state explicitly; ambiguous-direction errors have burned debugging time): **FA (false-accept) rate — lower-better**; **FR (false-reject) rate — lower-better**; **request-evidence yield — higher-better**; **Consistency Rate (CR) — higher-better**. The **FA/FR ratio** is a first-class reported column (overcorrection dominates: FR≫FA, 10:1–440:1 — intake-836), not a derived footnote.
> - **External judge-of-judge**: any externally-graded sample cites the **pinned API model-id + date** as part of the instrument version (e.g. `judge=<model-id>@YYYY-MM-DD`); a different judge model-id or date = a new instrument version. Bounded/budget-capped per the H5 Ref arm.
> - **Broken-grader guardrail**: read transcripts before trusting a surprising FA/FR flip (CORE-Bench 42→95% was grader repair, not model change — intake-846).
> - **Out of scope for P-REV-1**: latency/throughput/token-cost claims stay under **P-AB-1** (paired task-rate A/B) and **P-SPEED-OBJ** (task_rate axis). P-REV-1 governs *decision quality only*; the budget gate is `reviewer-latency-and-sampling-budget.md` LB-6.

### Block 2 — add to §2 Claim grammar & examples

> - Reviewer-calibration claim grammar: `reviewer FA x%, FR y%, yield z%, CR c% (n=N/arm, corpus rev-<id>@<hash8>, gold=<source>/v<ver>, reviewer=<model>/<quant>/gbnf=<on|off>, grader=<model>, rubric=v<r>, mode=<shadow|live>) [P-REV-1/<instrument-ver>, YYYY-MM-DD, attest <id>]`. FA/FR are lower-better, yield/CR higher-better; the FA/FR ratio is reported.
> - ✅ Worked example (illustrative — NOT a measurement): `reviewer FA 1.8%, FR 12.4% (ratio 0.15), yield 63%, CR 88% (n=120/arm, corpus rev-nm1@9f3a2c71, gold=gate_runner+evaltower-T1/v2, reviewer=GLM-5.2/UD-IQ2_M/gbnf=on, grader=Qwen3-Coder-30B, rubric=v3, mode=shadow) [P-REV-1/iv-1, 2026-08-xx, attest r7c1]`.
> - ❌ `reviewer catches 95% of bugs` (no instrument, no n, no protocol — and conflates "detects THAT" 95–100% with "detects WHY" 52–75%; intake-836).

### Block 3 — add to §3 Standing noise & resolution table

> | Reviewer FA/FR resolution | `1/n_arm` per rate; report FA/FR ratio + CR with accuracy | P-REV-1 instrument card |
> | Reviewer CR inflation caveat | CR ≈ 81% reachable at near-random accuracy | intake-837 |

### Operator sign-off checklist (RC-6a)
1. Land Blocks 1–3 verbatim (adjust cross-ref anchors as needed) with a one-line CHANGELOG entry.
2. Append the `scope: reviewer_plane` era row to `instrument_eras.yaml` when corpus v1 + gold pipeline freeze.
3. Confirm `check_claims_grammar.sh` recognizes the `[P-REV-1/…]` citation form (warn-mode month 1).
4. Until merged: reviewer FA/FR/yield/CR remain observations (RC-6a checkbox stays open).
