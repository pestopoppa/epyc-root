# Reviewer Control Plane — Latency & Sampling Budget (H-LB)

> **Fold destination** (BRF-T1-F25, BRF-T1-1, route 1a, 2026-11-02): absorbs 2 handoff(s) as `## Track:` sections at the end of this file (`reviewer-calibration-accounting.md`, `reviewer-typed-artifacts.md`). The body above the first track is the former `reviewer-latency-and-sampling-budget.md`.

**Status**: active — cross-cutting; **blocks ALL enforce-mode** anywhere in the series
**Created**: 2026-07-16 (Architect→Reviewer control-plane series; see index)
**Categories**: agent_architecture, cost_aware_routing, benchmark_methodology
**Index**: [`reviewer-control-plane-index.md`](reviewer-control-plane-index.md)
**Related**: [`reviewer-decision-plane.md`](../completed/reviewer-decision-plane.md) (RD-12 supplies the baseline), [`autopilot-control-plane-integration.md`](../completed/autopilot-control-plane-integration.md) (tunes these knobs)
**Repo**: `epyc-orchestrator`

## Objective

Make review latency a governed, first-class budget. The 2026-07-16 regression is the motivating fact: plan-review/eval-routing overhead **halved** eval throughput (~68 backend requests + 11-17 architect plan-review prompts per 50-question replay; reroute bug fixed `bc8d3303` but the structural cost remains). Architect↔Reviewer handshakes multiply this; no enforcement until the budget gate passes.

## Thesis

The literature quantifies the tax: multi-role pipelines ~2-3× cost / ~8-10× latency (intake-839 critique lit); multi-agent ~15× tokens with token usage explaining 80% of outcome variance; on a single host, parallel-reviewer latency models as **SUM not MAX** (intake-846). The counter-levers are structural (two-turn rubric, reminders-over-re-review, complexity gating, final-aggregate review, sticky cache — all in H3) plus governed budgets tuned by the autopilot. The standing floor: **the plane must beat a single augmented LLM on the same tasks** (M3 baseline floor) — a control plane that only adds cost gets deleted, per the Fable5 enforcement-not-theory posture.

## Prioritized Task List

- [ ] **LB-1 — Reproduce + attribute the regression**: which calls dominate (plan-review prompt count vs prompt length vs architect queueing) on the RD-12 replay baseline.
- [x] **LB-2 — Budget targets** ✅ 2026-07-17 (targets DEFINED below — see "LB-2 Budget targets (proposed)"; all numbers **PROPOSED/observation-grade**, pending LB-4 paired A/B confirmation + operator ratification): per-decision tokens + latency_ms; per-session review caps (reuse `IterationContext.max_iterations`/`max_total_iterations`); token-multiplier as a governed knob (target multiplier vs single-model baseline).
- [ ] **LB-3 — Sampling policies** — ⏳ PARTIAL 2026-07-17: complexity-gated review (TaskComplexity threshold knob) + reminder-substitution call-site + per-session caps LANDED (orchestrator `30d3232b`); still open: k% sampling, quick_mode tier wiring, fan-out effort-scaling rules.: review only COMPLEX/escalated tasks (reuse `TaskComplexity`); k% sampling; quick_mode tiering (QUICK_REVIEW_PROMPT exists); reminder-instead-of-review substitution rate; fan-out gated by task type + effort-scaling rules (1 agent/3-10 calls simple … 2-4 agents comparisons).
- [ ] **LB-4 — Paired throughput A/B per policy** under P-AB-1 + P-SPEED-OBJ (task-rate axis, e-process — never single-trial); parallel-reviewer wall-clock modeled as SUM on-host (exception: NUMA-split or MI210-offloaded reviewer).
- [x] **LB-5 — Budget-enforcement knobs** ✅ 2026-07-17 (knobs + LB-2 budgets declared in `orchestration/review_plane_knobs.yaml` and enforced at existing seams — IterationContext caps + shadow `check_token_budget` that logs VIOLATIONs, never blocks; apply_params plumbing landed AP-1) in features/delegation config; declared in the guarded numeric-surface manifest (H8 class 1).
- [ ] **LB-6 — THE BUDGET GATE** — ⏳ metric + decision procedure DRAFTED ✅ 2026-07-17 (see "LB-6 Budget-gate metric + decision procedure"); **checkbox stays OPEN — threshold VALUE is an operator decision (OP-5b), not yet picked**: define the (quality gain per throughput cost) threshold that `review_decision_enforce` and H7 policies must satisfy. Threshold VALUE is an operator decision (OP bundle); this task defines the metric and decision procedure.
  - [x] **LB-6a — gate metric + decision procedure drafted** ✅ 2026-07-17 (metric, who-runs-what, re-eval cadence, FA/FR auto-demote linkage, and 2–3 candidate thresholds for the operator recorded below).
  - [ ] **LB-6b — operator picks threshold (OP-5b)**: choose one of the candidate thresholds (or a variant) → operator decision queue §A00; until picked, no enforce-mode flip anywhere in the series.
- [ ] **LB-7 — M3 baseline floor measurement**: full plane (shadow→enforce candidate config) vs single-augmented-LLM baseline (A0/A1 arms) on the same tasks — the go/no-go the whole series answers to.
- [ ] **LB-8 — Publish standing numbers** into the index (H0) cross-cutting section.

## Dependency Graph

```text
H3 RD-12 baseline → LB-1 → LB-2 → LB-3 → LB-4 → LB-6 gate → (unblocks enforce-mode in H3/H7)
LB-5 (with LB-2/3) → H8. LB-7 needs H4 instrument + H5 anchor arms. LB-8 continuous.
```

## Cross-Cutting Concerns

1. **CPU economics** — decode is BW-bound; every review token competes with production traffic; "better reviewer model beats bigger token budget" (intake-846) favors fidelity + caching over volume.
2. **GPU relief valve** — drafter Stage-1 and architect-residency (operator GPU bets 1-2) directly reduce review-turn latency; teleport (bet 4) helps long review turns; cross-ref `mi210-big-model-and-acceleration-roadmap.md`.

## Key Files / Surfaces

- `src/proactive_delegation/` (IterationContext, complexity, QUICK_REVIEW_PROMPT), `src/features.py`
- `scripts/autopilot/eval_tower.py` replay harness; P-AB-1/P-SPEED-OBJ protocols (MEASUREMENT.md)

## Reporting Instructions

Flip checkboxes `✅ YYYY-MM-DD`; LB-6 threshold proposal → operator decision queue (§A00); standing numbers mirrored to H0; any enforce-mode flip anywhere cites LB-6 passage.

## Evidence Base (intake)

2026-07-16 throughput-regression checkpoint (master index) · intake-839 multi-role tax + single-model baseline · intake-846 15×/SUM-not-MAX/effort rules · intake-835 reminders-over-re-review + adaptive gating (2509.03581) · intake-849 P5 guardrail placement · audit doc 2026-07-16.

## Budget Definitions (appended 2026-07-17 — design/spec only; wave-2 agent owns features/config)

Design/spec for LB-2 and LB-6. **No orchestrator code here** — a wave-2 agent implements the features/config knobs (LB-5) and runs the paired A/Bs (LB-4). Every number is **PROPOSED / observation-grade** until confirmed under **P-AB-1** (paired task-rate A/B) + **P-SPEED-OBJ** (task_rate axis); none may gate an enforce-mode flip on its own.

### LB-2 Budget targets (proposed)

**Stack facts used as anchors** (observation-grade decode rates, single-model, 96t canonical unless noted; re-confirm under P-BENCH/P-SPEED before gating): architect ~18–21 t/s CPU, frontdoor 24.3 t/s, worker 44.7 t/s; **rubric grading is cheap-model (worker-tier) work**; on this host parallel-reviewer wall-clock models as **SUM not MAX** (intake-846). Latency budgets below are derived as `tokens ÷ t/s` on the arm that performs that decision, then rounded up for prompt/queue overhead — they are ceilings, not forecasts.

| Decision type | Actor (typical) | Token budget (out) | Latency budget (ms) | Notes |
|---|---|---|---|---|
| **plan-review** | architect (~18–21 t/s) | ≤ 350 | ≤ 22,000 | one pass per plan; reminders-over-re-review (intake-835) preferred to a second pass |
| **candidate-review** | reviewer (CPU GLM low t/s / GPU-resident) | ≤ 300 | ≤ 18,000 (CPU) / ≤ 6,000 (GPU-resident) | GBNF-constrained verdict; SUM-not-MAX if run parallel to production |
| **rubric-authoring** | strong model (architect-tier) | ≤ 800 | ≤ 45,000 | **amortized** — authored once per task-type, sticky-cached (H3); cost divided over all items it grades |
| **rubric-grading** | cheap grader / worker (~44.7 t/s) | ≤ 180 | ≤ 5,000 | high-frequency per-item path; keep it cheap (intake-834 grading-model insensitivity 2.4pp) |

- **Per-session caps** (reuse `IterationContext` semantics): `max_review_iterations` ← reuse `IterationContext.max_iterations` (per-task ceiling on review turns, proposed default **2**); `max_total_review_iterations` ← reuse `IterationContext.max_total_iterations` (per-session ceiling across all tasks, proposed default **scale with session task count, cap the review-token share — see multiplier below**). Review turns count against the same iteration ledger so a runaway Architect↔Reviewer handshake trips the existing budget, not a new one.
- **Token-multiplier knob** (`review_token_multiplier`): the governed ratio of **total tokens with the plane** ÷ **single-augmented-LLM baseline tokens on the same tasks** (LB-7 / A0–A1 arms). Literature tax is ~2–3× cost / ~8–10× latency for multi-role pipelines (intake-839); multi-agent ~15× tokens (intake-846). **Proposed target ≤ 1.5× (stretch 1.3×), hard ceiling 2.0×** — above the ceiling the plane auto-throttles review fan-out (sampling policies, LB-3) rather than spend. The multiplier is the single knob the autopilot (H8) tunes; it composes with, and is bounded by, the LB-6 gate.
- All targets are **PROPOSED**; confirm each under LB-4 (P-AB-1 + P-SPEED-OBJ) before any enforce-mode flip.

### LB-6 Budget-gate metric + decision procedure (proposed; threshold value = operator decision OP-5b)

**Gate metric — quality-gain-per-throughput-cost.** On **paired replays** (same task set, same seeds, plane arm vs single-augmented-LLM baseline arm A0/A1) under **P-AB-1** (N ≥ 100) with the throughput axis under **P-SPEED-OBJ** (task_rate = questions / eval-wall-hour, e-process, never single-trial):

```
G = ΔP(success) / (% throughput reduction)
    ΔP(success)          = P(success | plane) − P(success | single-LLM baseline)   [pp, higher-better]
    % throughput reduction = 100 × (task_rate_baseline − task_rate_plane) / task_rate_baseline   [higher = costlier]
```

Enforce-mode for a reviewer configuration requires **BOTH**: (1) `G ≥ threshold` **and** net `ΔP(success) > 0` measured as above (the budget gate), **and** (2) the config is not in FA/FR breach (the calibration gate — RC-5). The two gates are orthogonal: a config can pass budget yet fail calibration, or vice versa; enforce needs both green. If `task_rate_reduction ≤ 0` (plane is *faster*), the gate reduces to `ΔP(success) > 0` (pure win, no cost to trade).

**Decision procedure.**
- **Who / what**: the H8 autopilot proposes an enforce-candidate config and runs the paired replay (placement via the eval fan-out path, not `/chat`; respects no-concurrent-inference + operator bench window). It computes `G`, `ΔP(success)`, `% throughput reduction`, and the FA/FR e-process state, and writes them in P-AB-1 / P-REV-1 grammar. **The operator ratifies the threshold value (OP-5b)** — agents never self-approve a gate threshold (measurement trust boundary is human-amendment-only).
- **When re-evaluated**: on every enforce-candidate config; on any instrument-era change (P-REV-1 instrument version bump, corpus revision, kernel cutover); and continuously in shadow so a live config that drifts below threshold is caught.
- **Auto-demote linkage**: the budget gate hooks the **same** demotion machinery as FA/FR — a live config whose measured `G` falls below threshold (or `ΔP(success)` goes ≤0) auto-demotes reviewer enforcement to **shadow** via `sequential_verdict.py` (`EProcessState`/`SequentialPolicy`, RC-5), exactly as an FA/FR-tolerance breach does. One demotion path, two trigger families (calibration + budget).

**Candidate thresholds — FOR THE OPERATOR TO PICK (do not self-select):**
| # | Threshold (`G` = pp ΔP(success) per 10% throughput cut) | Guardrails | Rationale |
|---|---|---|---|
| **T-conservative** | `G ≥ 0.5` (≥0.5pp quality per 10% throughput lost) | net ΔP(success) ≥ +2pp **and** throughput reduction ≤ 25% | protects production task-rate; the plane must clearly earn its cost — matches "a control plane that only adds cost gets deleted" (Fable5). Fewest configs pass. |
| **T-moderate** | `G ≥ 0.25` | net ΔP(success) ≥ +1pp **and** throughput reduction ≤ 40% | balances quality lift against the ~2–3× literature tax; expects GPU relief valves (bets 1–2) to absorb some cost. |
| **T-liberal** | `G > 0` | net ΔP(success) > 0 (any real gain) **and** throughput reduction ≤ 50% | maximizes quality capture where correctness matters more than throughput; only viable if spare capacity / off-peak review windows exist. |

Each threshold pairs a **rate** (`G`) with an **absolute floor** (net ΔP) and an **absolute cost ceiling** (max throughput reduction) so a tiny quality gain bought at ruinous cost cannot pass on the ratio alone. The operator picks one (or a variant) → §A00 decision queue (OP-5b). Standing floor cross-ref: whichever threshold is chosen, the plane must still clear **LB-7** (beat a single augmented LLM on the same tasks) — the go/no-go the whole series answers to.

### Refactor wrap-up — 2026-10-31

REV06v2 reduced controls passed and reader proposal prepared; row is explicitly owner-held before arm for logging repair, not runnable READY. No official full50q/122B exposure, July attribution or LB1 completion. [no-belief: preparation only]

## Track: reviewer-calibration-accounting
<!-- gate: none -->

> Folded from `handoffs/active/reviewer-calibration-accounting.md` @ `9ca99cab58e3` on 2026-11-02 (BRF-T1-F25, route 1a, operator D1/D5; retired row REV-03 → REV-06). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Reviewer Control Plane — Calibration Accounting: FA/FR Ledger + Near-Miss Corpus + P-REV-1 (H4)

**Status**: active — M2 "measured" milestone; the series centerpiece (every downstream claim is gated on this instrument)
**Created**: 2026-07-16 (Architect→Reviewer control-plane series; see index)
**Categories**: benchmark_methodology, agent_architecture
**Index**: [`reviewer-control-plane-index.md`](reviewer-control-plane-index.md)
**Related**: [`evidence-plane-ledger-and-sequential-verdicts.md`](autopilot-program.md#track-evidence-plane-ledger-and-sequential-verdicts) (ledger conventions), [`eval-tower-verification.md`](eval-tower-program.md) (EV-tier ECE/AUC — REUSE, do not duplicate), [`reviewer-model-ablations.md`](reviewer-model-ablations.md) (H5 consumes this instrument)
**Gate**: starts after H1 TM-8 coverage + H3 shadow decisions flowing.
**Repo**: `epyc-orchestrator` (ledger/scripts) + `epyc-root` (MEASUREMENT amendment draft)

#### Objective

Build reviewer calibration accounting — decision ledger, gold labels from objective verifiers, near-miss decision corpus, calibration metrics, sequential monitoring — and draft MEASUREMENT protocol **P-REV-1** for operator sign-off. Layer A throughout.

#### Thesis

Two dive results reshape the report's design. First, **overcorrection dominates** (false-reject ≫ false-accept, 10:1-440:1 — intake-836), so the ledger runs **symmetric FA AND FR tolerance e-processes** (auto-demote a live reviewer to shadow on either breach), with the FA/FR *ratio* as a first-class column. Second, **the corpus is the instrument**: versioned, dual-gold-labeled (executable oracles + reasoning modules), spanning domains (the autopilot journal already holds thousands of scored per-question outcomes across general/hotpotqa/simpleqa/instruction_precision/thinking/code — non-code mining is cheap).

#### Prioritized Task List

- [x] **RC-1 — `review_ledger` table** ✅ 2026-07-17 (additive DDL in store.py + append-only writer `src/trace/review_ledger.py`; provenance links via emit:// paths; verified non-disruptive against a copy of the real 10,326-row DB) in the trace DB: `(decision_id, ts, reviewer_model_quant, grading_model, rubric_version, corpus_id, candidate_id, domain, decision, tripwire, confidence, gold_label, gold_source, gold_instrument_version, rationale_cause_match, latency_ms, tokens, family_match_flag, era)` with provenance links to trace events.
- [x] **RC-2 — Gold-label pipeline** ✅ 2026-07-17 (`gold_labels.py`: gate_runner / eval-tower scorer / corpus-row oracle families; ≥2-agree→multi_oracle gate-worthy; disagree→ambiguous-tail arbitration; pure functions): candidate outcome from gate_runner (format/lint/typecheck/unit) and/or eval-tower tier scorers; human arbitration only for sampled escalations + the ambiguous/unsolvable tail. **Gate-worthy rows need ≥2 oracles or human arbitration** (weak-oracle inflation: 47.9% of SWE-bench "resolved" pass on weak tests — intake-845).
- [x] **RC-3 — Near-miss decision corpus v1** ✅ 2026-07-17 (`corpus_id=nearmiss-v1`, content_sha256 1c50c025…, **11,516 rows / 0 invalid / 0 dupes** at `/mnt/raid0/llm/datasets/nearmiss-corpus-v1/`; per-source c-crab 1005 / swe-care 622 / journal 3683 (qid-hash join, 99.32% recovered) / seeded 6202 (29.1% ≤ cap) / bug-report 4; multi_oracle gate-worthy 6687; ambiguous_tail 475; natural-defect control slice 960; builder `scripts/analysis/corpus_v1/`, orchestrator `9958d819`. LATER PASSES: journal rows need candidate-text recovery (non-inference join or eval re-run) + reasoning-module labels (inference); optional Docker-oracle upgrade of single_oracle rows) (versioned: corpus id + hash): (a) autopilot journal approve/reject + scored per-question history across suites; (b) seeded-defect mutations of known-good outputs; (c) known-bad candidates from bug-reports; (d) mined c-CRAB rows + SWE-CARE pool (`/mnt/raid0/llm/datasets/`, acquired 2026-07-16). **Row schema**: dual gold labels (executable-oracle verdict + reasoning-module labels), `defect_origin ∈ {natural, seeded}` + a natural-defect control slice, decontamination metadata (repo/base_commit/created_at — SWE-Bench-Illusion applies to all SWE-bench derivatives), `rationale_vs_gold_cause` (catch right-for-wrong-reason: models detect THAT 95-100% but WHY only 52-75%). Do NOT copy c-CRAB's solvable-only filter — the ambiguous tail routes to human arbitration.
- [x] **RC-4 — `scripts/analysis/reviewer_calibration_report.py`** ✅ 2026-07-17 (full panel FA/FR/ratio/acceptance/yield/esc-precision/Brier/ECE/AUC/CR/pass^k/parse-fail + Wilson CIs per 5-tuple group; FA/FR classifiers imported from review_ledger; ECE/AUC replicated stdlib-only w/ origin comments — eval-tower versions are inline+sklearn-dependent; observation-stamped pre-P-REV-1): FA rate, FR rate, FA/FR ratio, acceptance rate, request-evidence yield, escalation precision (sampled), Brier, ECE, AUC, **Consistency Rate (test-retest ≥2 runs — bias can inflate CR to 81% at near-random accuracy)**, parse-failure rate — per (reviewer config × grading model × rubric version × corpus version × domain). **Reuse EV-tier ECE/AUC implementations** (`eval-tower-verification.md` T1) — do not duplicate. Metrics: **pass^k for review decisions** (consistency gates deploys), pass@k for candidate generation.
- [x] **RC-5 — Sequential monitoring** ✅ 2026-07-17 (symmetric FA+FR e-processes on EProcessState/SequentialPolicy; either-side CONFIRMED (wealth≥20, anytime-valid α≈.05) latches demote-to-shadow; placeholder tolerances fa=.05 / fr=.25 encode the intake-836 FR≫FA prior — pending P-REV-1; library-only, no live wiring): FA-tolerance AND FR-tolerance e-processes on `src/autopilot_core/sequential_verdict.py` (`EProcessState`, `SequentialPolicy`) — live breach on either side auto-demotes the reviewer to shadow. Enforcement, not new decision theory (Fable5 posture).
- [x] **RC-6 — Draft MEASUREMENT amendment P-REV-1** ✅ 2026-07-17 (amendment text DRAFTED — see "P-REV-1 Draft Amendment Text" section below; **operator PR still outstanding** — MEASUREMENT.md is human-amendment-only): instrument = (corpus id+hash, gold-label source+version, reviewer model+quant+grammar-flag, grading model, rubric version, shadow/live mode, n); changing any = new instrument version; claim grammar `reviewer FA x%, FR y% (n=…, corpus rev-…, gold=…) [P-REV-1, date, attest …]`; directions stated; external judge-of-judge samples cite pinned API model-id+date as part of the instrument. Speed/latency claims stay under existing P-AB-1/P-SPEED-OBJ.
  - [ ] **RC-6a — operator PR + sign-off** (human-amendment-only): land the drafted P-REV-1 blocks into `MEASUREMENT.md` §1/§2/§3 via PR-reviewed amendment with a one-line CHANGELOG (append-or-version). Until merged, every reviewer FA/FR/yield/CR number stays an **observation** and MUST NOT gate any keep/revert/deploy/promote decision in H5/H7.
- [x] **RC-7 — Evidence-plane alignment** ✅ 2026-07-17 (docstring alignment note + `to_question_ledger_row()` adapter stub — decision≈question): per-decision rows follow per-question-ledger conventions (decision ≈ question); cross-ref both handoffs.
- [ ] **RC-8 — Baseline run**: current self-review (architect alias) in shadow on corpus v1 — the first FA/FR numbers. **Broken-grader guardrail**: read transcripts before trusting a surprising number (CORE-Bench 42→95% was grader repair, not model change).
- [x] **RC-9 — Rubric persistence** ~~✅ 2026-07-29~~ **REOPENED 2026-09-16** (`review_ledger.v2`; focused validation: 94 passed, 1 expected skip): full rubric and per-item grade snapshots now persist in nullable canonical-JSON `rubric_json` / `per_item_grades_json` columns. The additive migration preserves pre-RC-9 rows; legacy writers remain valid, and readers retain raw forensic columns while exposing decoded `rubric` / `per_item_grades` aliases. This is an accounting schema change only — no reviewer metric or instrument claim was produced. **Staleness audit 2026-07-29:** the prior ledger had `rubric_version` only, with no rubric/grade payload; its append writer has HIGH impact (analysis, tests, Autopilot, and trace modules), so this was implemented as a separately reviewed additive schema + backward-compatible writer/read change.
  ✅ 2026-09-16 RE-IMPLEMENTED and merged: orchestrator `ebfb1cb5` on main (`review_ledger.v2`: `rubric_json` + `per_item_grades_json`, repeat-safe migration, no back-fill; 813 real rows verified before/after). Residual data gaps (per-item grades from live grading, score-token logprobs) are RC-10/SC43, not RC-9.
  - **Reopen note 2026-09-16 (sub-closure-fix):** the 2026-07-29 tick is false. The `review_ledger.v2` schema and the `rubric_json` / `per_item_grades_json` columns **exist on no ref**. They are absent from orchestrator `origin/main` @ `88a2902d` (`src/trace/review_ledger.py`, `src/trace/store.py`) and from every branch tip and the `log --all -S` history of root, orchestrator and research; the only hits are untracked bus state. The tick arrived in root `4762625d` (2026-07-30), the same false cohort as UTM-M7/M8 and E1a. Evidence: `progress/2026-09/2026-09-16-sub-closure-audit.md` (top-10 #2) and `scripts/handoffs/closure_audit.py --strict-idents`. The work is still needed: the ledger carries `rubric_version` only.
  - **Progress 2026-09-16 (sub-rc9): implemented, NOT yet on `origin/main` — box stays open until merge.**
    Orchestrator branch `sub/rc9-20260916` @ `ebfb1cb5` (unpushed) implements the spec above:
    nullable canonical-JSON `rubric_json` / `per_item_grades_json` columns in `src/trace/store.py`;
    an additive, idempotent v1→v2 `ALTER TABLE` migration with no back-fill (read-only ledgers still read);
    `LEDGER_DDL_VERSION = "review_ledger.v2"`; and readers that keep the raw columns and add decoded
    `rubric` / `per_item_grades` aliases (`None` on v1 rows). Legacy writers are unchanged and still
    valid. The writers now populate the columns wherever a producer holds the data:
    - `grade_result_to_ledger_row()` covers the RD-2 `GradeResult`, including its full rubric and
      per-item grades.
    - `review_decision_to_ledger_row` / `record_review_decision` accept the snapshots and map
      `rubric_ref` to `rubric_version`.
    - The `review_plan_rubric` event records a rubric snapshot (id, template sha256, axes). It
      records per-item grades only when the emission parsed, because the axes default to `True`
      otherwise.
    - `reviewer_events_to_ledger` passes both snapshots through.
    - The `reviewer_corpus_ledger_run` field-order arms carry their prompt-rubric snapshot.

    Validation: `tests/test_review_ledger_v2.py` (15 tests); related suites 409 passed, 1 skipped,
    4 xfailed. A migration dry run on a copy of `data/trace/review_ledger.sqlite` read all 813 rows
    before and after the migration, `calibration_summary` was identical, and 0 rows were back-filled.
    No reviewer metric was produced. **Data gaps (need a capture run, i.e. inference, not schema
    work):**
    - The single-token corpus probe has no per-item grades.
    - No live producer calls `grade_candidate` yet, so no captured rubric snapshot exists.
    - Score-token logprobs / K-vector remain uncaptured (RC-10 / SC43).

    Vidya: root `origin/main` has no reviewer adapter (SC43 / SC83 are "none (planned)"), so there
    is nothing to re-wire yet; a future adapter reads the decoded aliases.
    **Tick when `ebfb1cb5` lands on orchestrator `origin/main`** (that merge is the only remaining
    step).
- [ ] **RC-10 — Evaluate a logprob-expectation confidence construction against the existing ledger and
  corpus.** The intake-804 cross-link below (Research Intake Cross-Link — 2026-07-29) has been prose
  only since it was filed; this is its first runnable entry point, and it inherits that block's scope
  boundaries verbatim — **evaluate an alternate confidence construction against the existing
  ledger/corpus and calibration panel; do not replace the typed decision, alter a threshold, or infer a
  reviewer-quality improvement from the paper.** Preserve objective-verifier precedence and cross-family
  separation. [intake-804] [intake-1162] [intake-1168]
  - **What to run.** A/B the current discrete construction against an expectation over the score-token
    distribution on `nearmiss-v1` (11,516 rows, sha `1c50c025…`) via
    `scripts/analysis/reviewer_calibration_report.py`, reporting Brier/ECE/AUC on both arms. Smallest
    implementation site is `repos/epyc-orchestrator/src/pipeline_monitor/model_grader.py:159-168` —
    replace `choice_scores.get(classification)` with `Σ_g p(v_g)·φ(v_g)` over the existing
    `choice_strings`. The read-out spec, the T=1 constraint and the silent-failure guards are specified
    once in `eval-tower-verification.md` EV-15b/EV-15c — reuse them, do not restate them here.
  - **Per-generator normalisation is a prerequisite, not a refinement.** intake-1168 Appendix H finds
    that raw log-likelihood conflates distributional similarity with the *intrinsic predictability* of
    the generator's text — short, conventional output scores higher regardless of correctness. Subtract
    each generator's mean across verifiers before the score means anything, or the construction is
    partly a **style prior** rather than a correctness signal. An un-normalised arm is not a valid
    comparison.
  - **Prompt-framing caveat to record alongside any result.** With unit-test ground truth held fixed, a
    one-word strict-versus-lenient change in the judge prompt swung one model from **−0.106 to +0.722**
    (intake-875 Table 5). Any A/B here must hold framing byte-identical across arms and say so.
  - **Standing constraint (RC-6a):** until the operator PR merges, every number this row produces is an
    **observation** and MUST NOT gate any keep/revert/deploy/promote decision in H5/H7.
  - **Precondition check 2026-09-16 (sub-reviewer): NOT startable offline.** `data/trace/review_ledger.sqlite`
    `review_ledger` stores one scalar `confidence` and no score-token distribution: there are no logprob,
    K-vector or `retained_mass` columns. `scripts/analysis/reviewer_corpus_ledger_run.py` also records that
    the reviewer probe captures no per-decision logprob. The existing ledger cannot supply the expectation
    arm, so RC-10 needs a NEW capture run: inference, with the SC43 write-side fields emitted from the first
    call.
- [x] **RC-11 — report false-accept and false-reject SEPARATELY** (intake-1307; 2026-09-07). A single
  aggregate accuracy does not satisfy this plane's gate. Where one side is not computable — typically
  false-reject, because a rejected item has no ground truth — **say so explicitly and report the cause
  histogram instead; never omit the side silently.** intake-1307 is the citable precedent for the
  omission being the *default* behaviour rather than an oversight: it quantifies false-accept in three
  places (8% wrong-class proved, 0.877 and 0.932 accepted accuracy) and never converts false-reject to
  a rate at all, decomposing it by cause instead. That asymmetry is the finding, not the paper's bug.
  **✅ 2026-09-08 — audited + one residual gap closed.** Audit result: all four FA/FR-reporting
  surfaces were already separate (pii_fixture_eval.py FA 0/21 + FR 0/30 with own denominators and
  cause histograms; reviewer_calibration_report.py per-side columns with Wilson CIs;
  safety_gate.py / review_policy_trials.py / screening_tier_runner.py separate with absent side
  surviving as null). Residual gap — `reviewer_calibration_from_decisions` returned only the
  computable axes and the corpus reader silently dropped observation-gold rows — CLOSED in
  epyc-orchestrator `15d0858f`: every axis key always present, an unmeasured side is `None`
  (never absent, never `0.0`), `n_gate_fail`/`n_gate_pass` ride along, and exclusions are counted by
  cause at both the corpus-read seam (`judgeable_row_cause`: no_candidate_answer /
  non_conclusive_gold_label / observation_gold_confidence / not_a_record) and the gate-None seam
  (`excluded_no_conclusive_gate`). Full audit record: `progress/2026-09/2026-09-08.md`.
- [x] **RC-12 — audit every reviewer/gate threshold for selection-on-the-certification-sample**
  (intake-1307; 2026-09-07). For each threshold, record whether it was chosen on a split independent
  of the one used to certify it. Where it was not, either re-derive on a held-out split or record the
  multiplicity penalty owed. The source makes the size of this concrete: the same data certifies at
  materially different risk levels under a union-bounded grid search versus a threshold picked on an
  independent dev split, and it treats that difference as decisive rather than cosmetic. Maps directly
  onto the standing "eight ways a check passes for the wrong reason" catalogue.
  **✅ 2026-09-08 — 16-threshold audit filed.** The referenced ~110-threshold subagent report is not
  recoverable from the tree (re-enumerated from code instead; every `file:line` verified by direct
  read). Three VIOLATIONS: (1) `rubric_pass_threshold` default 0.60 in `eval_tower.py:4334-4335` —
  unknown derivation, converts rubric aggregates into per-question `correct` feeding the SafetyGate
  quality axis; remedy: derive from a rubric-vs-gold slice or make `scoring_config` name threshold +
  rationale per suite (mirroring gate_verdict's mandatory rationale), until then observation-only.
  (2) PII-hook exemption surface in `pii_precommit.sh` — tuned on observed over-blocks with fixture
  rows added in the same commits that certify it (catalogue face 15: the oracle endorses the defect);
  mitigation present (evaluator prints same-sample provenance; `candidate_eval_gate.sh:26` mislabels
  it "held-out" — relabel to "same-sample PII fixture validation (observation-only)", wording fix
  only). (3) `DEFAULT_BASELINE_QUALITY=1.16` `safety_gate.py:365` — silent fallback default of
  undocumented derivation; prefer fail-closed. Plus: review_ledger FA/FR tolerances are
  self-declared placeholders (stamped `thresholds_are_placeholders`) pending P-REV-1 — re-derive on a
  held-out near miss slice before any live wiring. One previously-filed VIOLATION already fixed
  (impact.py ordinal drift, `ae8ab82b`). OK-class: sequential_verdict e-process policy
  (protocol-derived), SafetyGate tuning constants (incident-derived, continuously gated), gate_verdict
  (design is the anti-VIOLATION), CITATION_THRESHOLD_N=20, vidya policy floors, repo-readiness 80%
  (external rubric). Full findings table: `progress/2026-09/2026-09-08.md`.
  **Follow-on execution 2026-09-08 (all zero-inference):**
  - **(1) mechanism half landed** (epyc-orchestrator `5a9442d3`): every rubric row now carries
    `rubric_threshold_source` — `declared` (threshold + `rubric_threshold_rationale` named in
    `scoring_config`), `declared-no-rationale`, or `undeclared-default-0.60` — serialized into the
    detail row, plus a once-per-suite warning naming the remediation. The defaulted 0.60 is no
    longer silent anywhere. Hard refusal at decision-grade seams is NOT yet enforced: rubric scoring
    is ~0.7% of the quality objective, no suite currently declares the threshold, and RC-6a makes
    the plane observation-only — the refusal half lands with the RC-6a/P-REV-1 operator window
    (same gate as the reviewer tolerances below).
  - **(2) relabel landed** (epyc-root `af4c5c63`): `candidate_eval_gate.sh` usage now reads
    "same-sample PII fixture validation (observation-only)".
  - **(3) loudness landed** (epyc-orchestrator `5a9442d3`): `Baseline.load` warns loudly when a
    persisted baseline file names no quality source (SG-3 already forces strict same-tier reads at
    every decision site, so the legacy 1.16 now only reaches lenient/display reads — but a number
    nobody re-derived must not be silent). Behavior unchanged otherwise.
  - **#1 reviewer tolerances + refusal halves: NOT executed — inference/cadence-gated.** Both need
    the RC-8 near-miss baseline data (shadow reviewer runs) and the RC-6a P-REV-1 operator PR
    (human-amendment-only). Recorded here so they cannot read as lost.

#### Dependency Graph

```text
H1 TM-8 + H3 shadow flow → RC-1 → RC-2 → RC-3 corpus v1 → RC-4 report → RC-5 e-processes → RC-8 baseline
RC-6 P-REV-1 draft (parallel after RC-1; operator PR gates all decision-grade claims in H5/H7)
RC-7, RC-9 (parallel)
```

#### Cross-Cutting Concerns

1. **Layer A / trust boundary** — reviewer metrics do NOT enter the T0-T3 model-quality axes; they are a separate instrument gating *reviewer-role promotion*. The plane invokes the tower; the tower never depends on the plane.
2. **Anti-reward-hacking** — any learning loop off this ledger must keep objective-verifier precedence, cross-family author/grade separation, and never optimize directly against the rubric score (intake-834 critique lit: length exploitation is the known failure).
3. **Domain generality** — calibration reported per-domain; expect reviewer value highest on planning/reasoning-heavy suites, lowest on saturated factual ones.

#### Key Files / Surfaces

- trace DB (H1) — `review_ledger` home; `src/autopilot_core/sequential_verdict.py`
- `scripts/autopilot/eval_tower.py` + `rubric_scoring.py` (EV-9/ECE/AUC reuse)
- `/mnt/raid0/llm/datasets/` (SWE-CARE, c-CRAB, RewardBench 1/2, JudgeBench, LLMBar — see `BENCHMARKS.md`)
- `/workspace/MEASUREMENT.md` (P-REV-1 target; operator PR)
- autopilot journals (`orchestration/autopilot_journal*.jsonl` — read ALL rotated shards)

#### Reporting Instructions

Flip checkboxes `✅ YYYY-MM-DD`; corpus versions and first FA/FR numbers recorded here + H0 milestone table; P-REV-1 text goes to the operator decision queue (§A00) — do not self-approve; all pre-P-REV-1 numbers are observations, never decision-gating.

#### Evidence Base (intake)

intake-836 FR≫FA asymmetry + rationale-vs-cause · intake-837 Consistency Rate · intake-844 Recall/OverPrediction plan-grading template · intake-845 executable oracles + corpus mining rules · intake-846 pass^k + broken-grader guardrail · intake-834 rubric persistence + decision bands · intake-804 continuous verifier confidence source · audit doc 2026-07-16 · dataset manifest B13.

#### P-REV-1 Draft Amendment Text (for operator PR — MEASUREMENT.md is human-amendment-only)

Copy-paste-ready blocks for the operator to land in `MEASUREMENT.md` via a PR-reviewed amendment (append-or-version; one-line CHANGELOG). Grammar matches the existing `P-QUAL-T1` instrument-card style. **This handoff must not edit MEASUREMENT.md — the autopilot/agents may READ it, never write it.** Nothing below is a claim until it is merged AND a measurement citing it exists; all pre-merge reviewer numbers are observations (§5 demote-to-prior default).

##### Block 1 — add to §1 Protocol registry (after P-SPEED-OBJ)

> ### P-REV-1 — Reviewer decision calibration (instrument card)
> The instrument for **reviewer-role promotion** — it gates keep/revert/deploy/promote of a *reviewer configuration*, never a model-quality (T0–T3) axis (Layer A; the plane invokes the tower, the tower never depends on the plane).
> - **Instrument** = (**decision corpus id + content hash**, **gold-label source + version** — objective oracle set and/or eval-tower tier scorer, `gold_instrument_version`, ≥2 oracles or human arbitration for gate-worthy rows), **reviewer model + quant + grammar-flag** (GBNF on/off is part of the instrument), **grading model**, **rubric version**, **shadow/live mode**, **n decisions**. Changing **any** field = a **new instrument version** (append an era row per `instrument_eras.yaml`, `scope: reviewer_plane`; never rescale prior FA/FR in place).
> - **Reps**: paired arms per **P-AB-1** (same decisions/prompts/grammar/stop/verifier budget both arms), **N ≥ 100/arm** for a reviewer-promotion decision; failures classified by reason (backend outage / timeout / empty / genuine) with infra-failure rate reported alongside the effect; flag-state attestation across all workers in the run header. **A single-corpus, single-run number is an observation** (never a decision), same rule as every other protocol here.
> - **Consistency**: `pass^k` for review decisions (test-retest ≥2 runs; CR can inflate to ~81% at near-random accuracy under bias — report accuracy next to CR). `pass@k` is for candidate *generation*, not review.
> - **Directions** (state explicitly; ambiguous-direction errors have burned debugging time): **FA (false-accept) rate — lower-better**; **FR (false-reject) rate — lower-better**; **request-evidence yield — higher-better**; **Consistency Rate (CR) — higher-better**. The **FA/FR ratio** is a first-class reported column (overcorrection dominates: FR≫FA, 10:1–440:1 — intake-836), not a derived footnote.
> - **External judge-of-judge**: any externally-graded sample cites the **pinned API model-id + date** as part of the instrument version (e.g. `judge=<model-id>@YYYY-MM-DD`); a different judge model-id or date = a new instrument version. Bounded/budget-capped per the H5 Ref arm.
> - **Broken-grader guardrail**: read transcripts before trusting a surprising FA/FR flip (CORE-Bench 42→95% was grader repair, not model change — intake-846).
> - **Out of scope for P-REV-1**: latency/throughput/token-cost claims stay under **P-AB-1** (paired task-rate A/B) and **P-SPEED-OBJ** (task_rate axis). P-REV-1 governs *decision quality only*; the budget gate is `reviewer-latency-and-sampling-budget.md` LB-6.

##### Block 2 — add to §2 Claim grammar & examples

> - Reviewer-calibration claim grammar: `reviewer FA x%, FR y%, yield z%, CR c% (n=N/arm, corpus rev-<id>@<hash8>, gold=<source>/v<ver>, reviewer=<model>/<quant>/gbnf=<on|off>, grader=<model>, rubric=v<r>, mode=<shadow|live>) [P-REV-1/<instrument-ver>, YYYY-MM-DD, attest <id>]`. FA/FR are lower-better, yield/CR higher-better; the FA/FR ratio is reported.
> - ✅ Worked example (illustrative — NOT a measurement): `reviewer FA 1.8%, FR 12.4% (ratio 0.15), yield 63%, CR 88% (n=120/arm, corpus rev-nm1@9f3a2c71, gold=gate_runner+evaltower-T1/v2, reviewer=GLM-5.2/UD-IQ2_M/gbnf=on, grader=Qwen3-Coder-30B, rubric=v3, mode=shadow) [P-REV-1/iv-1, 2026-08-xx, attest r7c1]`.
> - ❌ `reviewer catches 95% of bugs` (no instrument, no n, no protocol — and conflates "detects THAT" 95–100% with "detects WHY" 52–75%; intake-836).

##### Block 3 — add to §3 Standing noise & resolution table

> | Reviewer FA/FR resolution | `1/n_arm` per rate; report FA/FR ratio + CR with accuracy | P-REV-1 instrument card |
> | Reviewer CR inflation caveat | CR ≈ 81% reachable at near-random accuracy | intake-837 |

##### Operator sign-off checklist (RC-6a)
1. Land Blocks 1–3 verbatim (adjust cross-ref anchors as needed) with a one-line CHANGELOG entry.
2. Append the `scope: reviewer_plane` era row to `instrument_eras.yaml` when corpus v1 + gold pipeline freeze.
3. Confirm `check_claims_grammar.sh` recognizes the `[P-REV-1/…]` citation form (warn-mode month 1).
4. Until merged: reviewer FA/FR/yield/CR remain observations (RC-6a checkbox stays open).

#### Research Intake Update — 2026-07-21 (P-REV-1 needs a chance-corrected agreement statistic — RC-6a still open)

- **[intake-876] "Agreement Metrics for LLM-as-Judge Evaluation: What to Report and Why"** (arxiv:2606.00093; Delip Rao, Chris Callison-Burch)
  - Relevance: **this arrives in time to amend a DRAFT rather than a ratified protocol.** RC-6a is still an open checkbox, and the P-REV-1 claim grammar currently reports raw FA/FR/yield/CR with **no chance correction, no confusion matrix, and no declared tie/abstention estimand**.
  - Why it bites here specifically: RM-3c's live slice is FR 50.0% / FA 16.7% — a maximally skewed marginal. This handoff already warns in prose that bias can inflate CR to 81% at near-random accuracy. That warning is a **rediscovery of the chance-correction problem**, currently patched with a caveat instead of a statistic.
  - Key claims: on non-degenerate binary data Pearson/Spearman/Kendall/phi/MCC all collapse to the **same number** (reporting several manufactures fake corroboration); Cohen's kappa is the only common coefficient adding information, because its marginal-sensitive normalization exposes judge-vs-human positive-rate drift. Recommended minimal binary report = accuracy + F1 + kappa + exactly one correlation representative + the confusion matrix.
  - Abstention handling is a **choice of estimand, not preprocessing**: exclude / recode-as-negative / retain-as-third-class each estimate a different quantity. This directly bites GC-external-1a, which currently drops malformed/tie rows as data cleaning.
  - **Caveat carried forward:** the paper does not discuss Gwet's AC1. The classical kappa paradox is that kappa collapses toward 0 under highly skewed marginals even at high raw agreement — exactly our deliberately near-miss corpora. Pair kappa with prevalence/bias disclosure (or AC1); do not adopt kappa uncritically.
  - Delta from current approach: cost is low (kappa/Fleiss/Krippendorff are ~30 lines stdlib, alongside the existing stdlib ECE/AUC reimplementation).

- [ ] Operator-review candidate (RC-6a, do BEFORE the PR lands): add a chance-corrected agreement statistic + a declared tie/abstention estimand + confusion-matrix publication to the P-REV-1 claim grammar; pair kappa with marginal/prevalence disclosure per the kappa-paradox caveat. Human-amendment-only — operator PR, not an agent edit. [intake-876]
- [ ] Operator-review candidate (GC-external-1a): declare the tie/abstention estimand explicitly and report its rate, rather than skipping malformed/tie rows as cleaning. [intake-876]

#### Research Intake Cross-Link — 2026-07-29 (intake-804; confidence source, not a re-verdict)

- [`intake-804`](../../research/intake_index.yaml) is the canonical arXiv write-up of LLM-as-a-Verifier (also tracked as intake-362#record / intake-363#record in the eval tower). Its central empirical claim is that a **continuous score formed from scoring-token logit expectations** can rank and calibrate solutions better than discrete judgments. The reviewer plane currently emits discrete typed decisions with scalar `confidence ∈ [0,1]` (RA-1) and reports Brier/ECE (RC-4/RM-2), so this is directly relevant as a **candidate confidence source**.
- Scope boundary: use it to evaluate an alternate confidence construction against the existing ledger/corpus and calibration panel; do not replace the typed decision, alter a threshold, or infer a reviewer-quality improvement from the paper. Any measured comparison remains an observation until the P-REV-1 instrument and its required evidence are satisfied.
- Local-enabler boundary: the 2026-07-21 `completion_probabilities_geomean` path and `confidence_is_real` fail-closed gate make local extraction/evaluation possible; their existence is not evidence that this source is calibrated for reviewer decisions. Preserve objective-verifier precedence and cross-family separation.

#### RC-13 — Autonomous-science judge calibration

**Activation trigger:** materialize RC-13 only when EPYC begins proposal-to-execution scientific experiments whose outcomes require independent trajectory, artifact, or manuscript review. Maintenance jobs, software evaluations, and research-intake summaries do not fire this trigger. `RA-14` and `VB-AISCI-1` must exist before the first such evaluation.

- **RC-13a:** add an autonomous-science shadow-evaluation stratum whose sampling unit is one manifest-bound attempt or adjudicated manuscript, never a framework-task cell inferred from prose. Preserve independent-study clusters, task/version/model/scaffold strata, failures, and committed metric; report per-stratum denominators and refuse pooled rates across incompatible endpoints, budgets, operators, or stopping rules. Sources: intake-1675#record, intake-1704#record, intake-1705#record, intake-1706#record.
- **RC-13b:** validate automated trajectory and log judges on held-out human labels with the full confusion matrix, precision, recall, false-accept, false-reject, disagreement, prevalence, and uncertainty. Keep outputs observation-only until calibration passes; agreement is not accuracy. Source: intake-1707#record.
- **RC-13c:** add blinded independent scientific adjudication over multiple tasks and reviewers independent of the system and original task authors, with any original-author arm disclosed separately. Record blinding, task-selection freedom, artifact-inspection completeness, and separate engineering, manuscript, venue, and scientific-validity judgments. Sources: intake-1653#record, intake-1705#record, intake-1706#record.

#### MAIN-reviewed JEV refinement — 2026-10-06 (RC-10)

Prepare an adapter arm using the shipped `Question`/`DecisionResult` and native candidate readout over the existing score-bin catalogue, rather than building a second typed scorer. Compute the specified expectation in host code; preserve explicit unsupported, missing and unresolved outcomes. Deterministic fixtures can validate mapping, expectation, failure denominators and call-accounting integration without model calls.

Before a live comparison, prove that temperature, masking/conditioning and probability semantics match RC-10's existing EV-15b/EV-15c read-out contract. Native candidate probabilities cannot silently replace the historical score-token instrument. Preserve the same corpus/panel, objective-verifier precedence, cross-family separation and all P-REV-1/inference gates. This refinement supplies an implementation seam; it changes no threshold or reviewer verdict and establishes no accuracy or cost improvement. Use `record_llm_calls` where its actual primitives seam is invoked; missing telemetry stays absent.


- [x] **RC-10-PREP — implement pure supplied-score expectation and synthetic coverage/failure contract.** ✅ 2026-10-06 — [Preparation contract](../../docs/reference/confidence-expectation-preparation.md), APPmainff423d14, original CI37446388954 TRUE26/26 after MAIN original source/API review. Existing three grading φ maps supplied unchanged; no zero-fill/renormalization. Synthetic coverage assertion is not native coverage proof. Historical EV-15b/c parity, same-corpus/panel live comparison and Claude-owned SC43 producer remain open; RC-10 parent remains unchecked.

## Track: reviewer-typed-artifacts
<!-- gate: none -->

> Folded from `handoffs/active/reviewer-typed-artifacts.md` @ `9ca99cab58e3` on 2026-11-02 (BRF-T1-F25, route 1a, operator D1/D5; retired row REV-09 → REV-06). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Reviewer Control Plane — Typed Artifact Schemas (H2)

**Status**: active — M1 "observable" milestone; schemas are the contract everything downstream validates against
**Created**: 2026-07-16 (Architect→Reviewer control-plane series; see index)
**Categories**: agent_architecture, tool_implementation
**Index**: [`reviewer-control-plane-index.md`](reviewer-control-plane-index.md)
**Related**: [`reviewer-trace-materialization.md`](../completed/reviewer-trace-materialization.md) (H1; events carry these artifacts), [`reviewer-decision-plane.md`](../completed/reviewer-decision-plane.md) (H3; emits them), [`tri-role-coordinator-architecture.md`](routing-program.md#track-tri-role-coordinator-architecture) (Verifier semantics)
**Repo**: `epyc-orchestrator`

#### Objective

Author the three missing IR schemas — evidence-linked `ReviewDecision`, `CandidatePackage`, `VerificationReport` — wire them into `orchestration/validate_ir.py` alongside the existing task_ir/architecture_ir/procedure suite, evolve the dormant dataclasses in `src/proactive_delegation/types.py`, and make reviewer output grammar-constrainable. Schemas are **domain-general**: evidence kinds include answer spans, retrieval provenance, and scorer results — not just file_span/test_result.

#### Thesis

Typed artifact contracts are the design center (report thesis + MetaGPT's validated discipline, intake-839). The repo already has the IR convention + validator; what's missing is the review-plane trio plus governance semantics the dive evidence forces: a **tripwire ⟂ advisory split** (blocking boolean orthogonal to score/feedback — `safety_gate.py` has it, `ArchitectReview` doesn't; intake-849 P1), **REJECT-to-empty** as a first-class plan outcome (bad plan < no plan; intake-835), **payload sanitization** (architect self-assessment shifts verdicts ~18-29pp; intake-837/838), and **parse-failure accounting** (an IQ2 reviewer's schema-emission failures are themselves a quality signal).

#### Prioritized Task List

- [x] **RA-1 — `orchestration/review_decision.schema.json`** ✅ 2026-07-17: decision enum `{approve, reject, reject_to_empty, request_changes, request_evidence, escalate}`; `confidence` [0,1]; `tripwire: bool` + `blocking_issues[]` (hard stop) structurally separate from `score`/`non_blocking_issues`/`feedback` (advisory); `evidence[]` with kinds `{file_span, test_result, gate_result, scorer_result, answer_span, retrieval_provenance, trace_event, protocol_claim}`; `verifier_requests[]`; `human_review_required`.
- [x] **RA-2 — `orchestration/candidate_package.schema.json`** ✅ 2026-07-17 (sanitized_view projection w/ additionalProperties:false — leaked self-assessment FAILS validation): task ref, plan ref (task_ir), diff/output refs, declared acceptance checks, provenance (model+quant, role, flag state, instrument era) — **plus a sanitization contract**: the reviewer-visible view MUST exclude architect self-assessment prose, confidence assertions, and "refined/final/expert" labels (intake-837/838). Sanitization is applied at package assembly, not reviewer prompt time.
- [x] **RA-3 — `orchestration/verification_report.schema.json`** ✅ 2026-07-17 (certificate required-on-fail via if/then): normalizes `gate_runner.GateResult` + eval-tower tier outputs; **three-valued outcome per check: `pass | fail | inconclusive`** with a `certificate` field on fail (failing assertion / counterexample / unsat core — the request_evidence payload; intake-842/843) and instrument version.
- [x] **RA-4 — Rubric artifact schema** ✅ 2026-07-17 (`orchestration/review_rubric.schema.json`): items `{text, axis, weight ∈ {1,2,3}}`; axes per domain template (code: file-change/spec-alignment/integrity/runtime; QA: grounding/question-alignment/integrity-no-fabrication/completeness; math: answer/method/integrity/coverage) (intake-834). Rubrics are cacheable, versioned artifacts.
- [x] **RA-5 — Wire all four into `orchestration/validate_ir.py`** ✅ 2026-07-17 (SCHEMA_MAP; non-zero exit on failure); **schema validation gates every role boundary** — a validation failure is a routable bounce-to-author event, never silent (intake-839).
- [x] **RA-6 — Evolve `src/proactive_delegation/types.py`** ✅ 2026-07-17 (+REQUEST_EVIDENCE/+REJECT_TO_EMPTY; ArchitectReview +confidence/tripwire/evidence/verifier_requests, all defaulted; consumers verified — 102 regression tests pass; enum/semantics ratification stays in OP-5f): add `ReviewDecision.REQUEST_EVIDENCE` + `REJECT_TO_EMPTY`; extend `ArchitectReview` with `confidence`, `evidence`, `verifier_requests`, `tripwire` (keep `score` for compat; document score-vs-confidence semantics — operator question in OP bundle).
- [x] **RA-7 — GBNF/json_schema constrained-decoding generation** ✅ 2026-07-17 (`review_grammar.py`: enum sourced from schema file so grammar cannot drift; pure generators + `parse_review_decision` w/ ParseFailure accounting. Grammar EXECUTION on the v7 GPU lane remains K22-blocked) from RA-1/RA-4 for llama.cpp reviewer calls, flag-gated. **Blocked for v7 GPU lane by the grammar-sampler P0 crash** (`common/sampling.cpp:292` — routed to `gemma-challenge-kernel-techniques-v7.md`); CPU production path unaffected pending verification.
- [x] **RA-8 — Field-order A/B design** ✅ 2026-07-17 (full design appended below; EXECUTION inference-gated → H5 RM-6): evidence→confidence→verdict vs verdict-first. Opposing hypotheses on record: verdict-first suppresses self-justification overcorrection (intake-836) vs verdict-first anchors (intake-837). Design the experiment here; run under H5.
- [x] **RA-9 — Round-trip + validator tests; parse-failure accounting** ✅ 2026-07-17 (57 tests) (count schema-invalid emissions per reviewer config; never silently fall back).
- [x] **RA-10 — Schema-versioned artifact emission into the trace store** ✅ 2026-07-17 (ledger rows + emitted artifacts stamp schema_version; REVIEW_DECISION_SCHEMA_VERSION=1.0.0 default w/ override; verification_report versions threaded through gold resolutions).
- [x] **RA-11 — ArchitectureIR/PlanGraph hardening** ✅ 2026-07-17 (optional-but-recommended-for-new-artifacts: interfaces section + typed call_edges; existing docs stay valid) (intake-839): ArchitectureIR mandates an interface-definition/data-structure section; plan steps carry typed call-flow dependency edges, not prose.

#### Dependency Graph

```text
RA-1..RA-4 (schemas, parallel) → RA-5 validator wiring → RA-6 types → RA-9 tests → RA-10 emission
RA-7 GBNF (after RA-1/RA-4; v7-GPU-blocked on kernel P0)     RA-8 design (parallel; executes in H5)
RA-11 (parallel)
```

#### Cross-Cutting Concerns

1. **Domain generality** — every schema field must make sense for non-code candidates (answers, plans, summaries); code-specific fields are optional extensions.
2. **IQ2 strict-IF weakness** (2/11 measured) is why RA-7 grammar constraint + RA-9 parse-failure accounting are load-bearing, not nice-to-have.
3. **Immutable structure, mutable status** (intake-846): artifacts are append/versioned; only status fields mutate.

#### Key Files / Surfaces

- `orchestration/*.schema.json` + `orchestration/validate_ir.py` (existing convention to extend)
- `src/proactive_delegation/types.py` (`ReviewDecision`, `ArchitectReview`, `IterationContext`)
- `src/task_ir.py`, `src/graph/task_ir_helpers.py`

#### Reporting Instructions

Flip checkboxes with `✅ YYYY-MM-DD`; schema versions are instruments — version bumps get changelog lines here. RA-6 enum evolution and score-vs-confidence semantics are operator decisions (OP bundle in master index §A00).

#### Evidence Base (intake)

intake-834 rubric artifact + axes · intake-835 REJECT-to-empty · intake-836 verdict-first/admissibility · intake-837/838 sanitization + field-order anchoring · intake-839 boundary validation-gating + IR hardening · intake-842/843 three-valued outcomes + certificates · intake-849 tripwire⟂advisory (P1) · audit doc 2026-07-16.

#### RA-8 — Field-order A/B experiment design (designed 2026-07-17; executes as H5 RM-6)

**Question**: does ReviewDecision field ORDER in the constrained-decoding schema change reviewer calibration? Two GBNF/json_schema variants generated from the same schema (`review_grammar.py` supports property ordering): **V-first** = decision→confidence→blocking→evidence→feedback; **E-first** = evidence→blocking→confidence→decision→feedback.
**Opposing hypotheses on record**: H1 (intake-836): V-first ↓FR — forcing the verdict before free-text suppresses self-justification-driven overcorrection (their explain-then-fix effect, 35.9→87.9% FR). H2 (intake-837): V-first ↑anchoring — committing to a verdict before enumerating evidence degrades accuracy on near-miss items (their CoT-order effects).
**Protocol**: paired within-item (same corpus-v1 slice graded under both grammars, same reviewer/grader config, seed42 production sampling), stratified to include the ambiguous-tail + natural-defect control slices; N≥100/arm per P-AB-1; primary metrics FA, FR, CR (test-retest ≥2), parse-failure rate; secondary: per-domain splits + confidence calibration (ECE). Analysis: paired flips via `sequential_verdict.quality_trial_statistic`, Holm over {FA, FR, CR}. Decision rule: adopt the variant that is non-inferior on FA and superior on FR (or vice versa with operator weighting); tie → keep E-first (matches evidence-linked design intent). **Execution is inference-gated → H5 RM-6.**

#### RA-9 — dual-gold annotation envelope + a gold-sanity gate (intake-948, intake-983; 2026-08-03)

_Via `/research-intake` Stage-2/2b. Schema-level items, so they belong here rather than in the skill;
the pipeline-ordering half lives in [`security-review-skill.md`](../completed/security-review-skill.md)._

- [x] **Adopt benchmrk's annotation envelope as the dual-gold schema.** ✅ 2026-09-16 Its `status:"invalid"` decoys give us a **negative-control axis we do not have anywhere** — intake-845 records the gap explicitly. Every current gold annotation asserts a true finding; nothing in the corpus asserts a finding that *should* be rejected, so no false-accept rate is measurable from our own data.
  - Evidence: `epyc-orchestrator` branch `sub/reviewer-artifacts-20260916` @ `e242a156`, integrated by orchestrator merge `bdf76ab3` (pushed in `753343f5`, 2026-09-16) — `orchestration/gold_annotation.schema.json` (validate_ir kind `gold_annotation`) + `src/proactive_delegation/gold_annotations.py`. `status: valid|invalid`; `invalid_reason` required iff decoy; dual gold (executable oracle + reasoning label, never both null), a conflict must carry `needs_arbitration`; model annotators force `origin: machine_generated`. `false_accept_rate()` is the negative-control axis: numerator/denominator stated, unscored decoys listed, decoys under arbitration excluded and listed. **This is the ONE dual-gold schema** — `security-review-skill.md` points here. `tests/test_gold_annotations.py` (45 tests, 13/13 mutants killed). Corpus population with real decoys is not done: no decoy rows exist yet.
- [x] **Add a gold-sanity gate to the schema contract for any machine-generated annotation or test.** ✅ 2026-09-16 Procedure, in this order: inject into the real project test file → apply the **gold** solution → run the project's **native** runner → discard and retry at higher temperature on gold-failure → *only then* consult a 3-sample self-consistency judge. **The order is the finding**: the judge reasons about generated test code that may not itself run, and it endorsed **all six** named invalid cases in the source study. Measured per-augmentation defect rate is **61.9% (n=105)** — the author's own nominated headline, and more stable than the 28.5% iterative figure concentrated in 2 of 12 repos.
  - Evidence: `src/proactive_delegation/gold_sanity.py` @ `e242a156`. `run_gate()` runs inject → apply gold → native runner, retries at the next strictly-higher temperature on gold failure, and only after a native pass takes a 3-sample majority judge. The judge is never called on an unrun or gold-failing test, and a crashed stage or an errored judge sample counts as a failure. `validate_record()` re-checks stored records (stage prefix order, judge only on the final attempt, vote/outcome consistency, no un-retried discard). The schema makes `gold_sanity.outcome: admitted` plus an executable oracle mandatory for `origin: machine_generated`. Hooks are caller-owned, so nothing runs a model here; the first live use is inference-gated.
- [x] **Ablation to preserve when implementing the retry:** ✅ 2026-09-16 retry *presence* is load-bearing (3/11 → 9/11); retry *style* is not (a neutral prompt also reaches 9/11). Do not spend design effort on the retry prompt.
  - Evidence: `run_gate` refuses a configuration with fewer than 2 temperatures or with non-increasing temperatures (`GoldSanityConfigError`), so retry presence is mandatory. `generate(temperature)` takes no prompt argument, so retry style is deliberately not a design surface. Both properties are pinned by tests (`test_config_removing_a_load_bearing_property_is_refused`, `test_generate_hook_takes_only_temperature`).
- Source code is *"available upon reasonable request"* — **not open**, so this is a pattern adoption and nothing is vendored.

#### RA-12 — immutable machine-review envelope (intake-1004; 2026-08-05)

- [x] **Bind every machine review to one immutable, version-correct envelope.** ✅ 2026-09-16 The envelope must carry the
  source/candidate content hash and version, reviewer model+quant, prompt bundle hash, pipeline and schema
  versions, output hash, validation status, and supersession link. Any source, candidate, prompt, pipeline,
  or schema change invalidates the prior decision/objections until re-run; retain the old artifact as stale
  history, never splice it into a current page. Machine-generated objections are typed `unverified_lead`
  until a current primary artifact or objective verifier resolves them and are never counted as independent
  corroboration. Add a regression fixture that combines a current source abstract with an old signed review
  body and prove that validation refuses a current binding.
  - Evidence: `epyc-orchestrator` branch `sub/reviewer-artifacts-20260916` @ `afa4e107`, integrated by orchestrator merge `bdf76ab3` (pushed in `753343f5`, 2026-09-16) — `orchestration/machine_review_envelope.schema.json` (validate_ir kind `review_envelope`) + `src/proactive_delegation/review_envelope.py`. The binding covers source/candidate hash+version, reviewer model+quant, prompt bundle hash, pipeline version and review-schema version; locators are not material. The body is SIGNED with the binding digest, so a forged envelope claiming current inputs around an old body is refused. `current_view()` returns at most one current review, keeps the rest as unchanged history and shows only the current envelope's objections; supersession chains are checked for dangling, forked and cyclic links. Objections are emitted as `unverified_lead`, `independent_corroboration` is schema-`const false`, and a primary-artifact resolution must match the CURRENT source or candidate hash. Frozen regression fixture `tests/fixtures/review_envelope/` (old review signed for abstract v1 vs current abstract v2): `tests/test_review_envelope.py`, 37 tests, 5/5 mutants killed. Integrity, not authentication: there is no signing key.

#### RA-13 — blind read-back (intake-1308, intake-1299#record; 2026-09-07)

The countermeasure to a reviewer that confirms what it expected rather than what is there. An
auditing sub-agent is given the **artifact only** and never the intent, so it *cannot* accidentally
agree with the author; it emits a description, and a human compares that description against the
original ask. Adapted from Prove2Me's mission-auditor protocol.

**Three properties are load-bearing, and all three must survive implementation** — remove any one
and this degenerates into the role-based decomposition our doctrine ratified against
(`OPERATING_CONSTRAINTS.md` → *Parallel Subagent Fan-Out*, *When NOT to fan out*): **(i)** no
authority is transferred — the auditor is forbidden to reach a verdict, it describes and a human
adjudicates; **(ii)** the split is an **information whitelist over the same task**, not a skill or
work-stage boundary, which is what makes it information-hiding rather than role decomposition;
**(iii)** blinding is re-established with a **fresh context on every artifact revision**, so the
auditor cannot be progressively contaminated across iterations.

**Citation bound, non-negotiable.** `intake-1308` is citable for **mechanism and rationale only**.
Its source repository contains **no efficacy measurement of any kind** — no hit rate, no caught-error
count, no false-agreement rate, no A/B against unblinded self-review (whole tree grepped at the
pinned commit). RA-13b exists because of that gap, and RA-13b gates RA-13a's citability.

- [ ] **RA-13a — blind read-back pilot.** HARNESS BUILT 2026-09-07 (`scripts/reviewer/blind_readback.py`, 48 tests, 9/9 mutants killed); **the N=20 pilot itself is NOT run** — it needs live model calls and is operator-gated. Row stays open for the pilot. Structural notes: the field whitelist is POSITIVE (a key is refused because it is not named, not because it was recognised as intent), `AuditorBrief` is a frozen 2-field dataclass so there is no attribute to smuggle intent through, and three independent routes to adding a verdict field each fail a test. **Known limit, not fixable structurally:** the whitelist is over field NAMES, so a caller who pastes the task statement into the artifact text still contaminates the brief — the artifact hash makes that visible after the fact, but does not prevent it. The reviewer sub-agent receives the artifact ONLY (a diff,
  a gate script, or a handoff row) plus a read-back spec — never the task statement, the request, or
  the author's intent — and emits a literal description of what the artifact does and asserts. The
  main compares that description against the original ask. Fresh context per revision. Pilot N=20
  completed edits. Authoring rules worth lifting verbatim from the source: account for every binder
  and precondition (omitting one is the worst failure mode); expand non-standard names rather than
  restating them; surface degenerate cases and conditions that could be vacuously satisfied; and if
  the artifact says less than the intent, the read-back must say less.
- [x] **RA-13b — instrument it at WRITE time.** ✅ 2026-09-07 — `scripts/reviewer/blind_readback.py`; the three counts must PARTITION the denominator (an undercounted denominator inflates every rate, so it is refused), `adjudicator` is required because a description nobody compared produced no result, and `citable_summary()` raises below n=20 naming n, the threshold and the bound. `provisional_summary()` is deliberately a different type so the two cannot be duck-typed together. Per run, record caught-discrepancy count,
  false-discrepancy count, and agreement-with-author rate. **No read-back result may be cited as
  evidence until n>=20 with a stated denominator.** Retrofitting this is impossible for the standing
  reason (write-side/read-side asymmetry), and adopting an unmeasured control and then citing it
  would reproduce exactly the warrant inflation this plane exists to prevent.
- [x] **RA-13c — read-back record format.** ✅ 2026-09-07 — missing judge model id, spec version, artifact hash or context manifest RAISES (never warns — a warned record still gets counted). The manifest pins the sha256 of the exact rendered brief, so `verify_brief_binding()` re-derives it: a run whose context carried the task produces a different hash and cannot pass. That closes the source's defect, where model-name-only records are byte-identical whether or not blinding happened. Every record carries: judge model id, spec version or
  commit, a hash of the exact artifact text shown, and a context manifest attesting the blinding
  actually held. A record lacking these is not evidence. This closes a defect in the source, which
  stores only the model name — so a captain who skipped the blinding entirely produces a
  byte-identical record — and which enforces read-back staleness as prose rather than mechanically.

#### RA-14 — Autonomous-science attempt and adjudication artifacts

**Activation trigger:** materialize RA-14 only when EPYC begins proposal-to-execution scientific experiments rather than software evaluation or maintenance work. The first campaign must implement these artifacts prospectively with `VB-AISCI-1`; no historical framework result is backfilled.

- **RA-14a:** define one versioned attempt manifest with attempt and independent-study-cluster IDs, system/model/scaffold and task/dataset revisions, seed and parent, API/compute/elapsed/human budgets, environment/dependency access, interventions, stop and terminal/audit status, and every filter/rerun/promotion decision. Report per-task and per-system denominators and refuse pooled rates over heterogeneous endpoints. Sources: intake-1607#record, intake-1609#record, intake-1610#record, intake-1704#record, intake-1705#record, intake-1706#record.
- **RA-14b:** define an immutable self-hashed scientific-evaluation receipt binding inputs, trajectory, commands and tool I/O, environment/runtime/access, intermediate scientific objects, output/code digests, grader inputs, rubric, automated judge, human decision, and final disposition. Preserve failed, censored, and unaudited attempts; every empirical manuscript claim points to execution and verification evidence. Sources: intake-1653#record, intake-1675#record, intake-1707#record.
- **RA-14c:** define a scientific-adjudication envelope that records engineering completion, executable validity, domain validity, manuscript assessment, and venue decision separately. Bind preregistered task/metric, reviewer expertise and independence/blinding, original-author involvement, task-selection degrees of freedom, interventions, manuscript lifecycle, and artifact availability class. Sources: intake-780#record, intake-1705#record, intake-1706#record.
