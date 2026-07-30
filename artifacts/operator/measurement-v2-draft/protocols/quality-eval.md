<!-- ⚠️ DRAFT v2 — NOT RATIFIED. Annex Q of MEASUREMENT.md (same trust boundary, same
     amendment rules). Quality / eval / significance protocol family. -->

# Annex Q — Quality & eval protocols

## P-QUAL-T1 — Autopilot trial-gate quality (the production instrument card)

- **Instrument**: **core_id** (versioned question set; current: `core_v2`, 50 items / 37
  scoreable, era `E4-quality-core-v2` from 2026-07-23T10:39:40Z, `policy_version
  core_v2_designed_e7_v1` — replaced the accidental `legacy_pool_seed_42_n50` draw; dataset
  sha256 in the era entry), n, per-question ledger ON, eval concurrency
  **fixed at 3** (part of the instrument — changing it is a new core version), scoring =
  deterministic methods only, `<think>` stripped.
- **Published constants per core version**: quantum (3/n), single-trial MDE (2 flips),
  per-suite resolution, known-dead items (must be zero after Phase 2.0 repair).
- **Per-suite resolution** = `1 / n_suite`. tool_use n=5 → 0.2; coder n=50 → 0.02. A one-question
  flip on tool_use is −0.2 (a fifth of the scale); on coder −0.02. **Never treat suites as
  having uniform resolution.**
- **Decision rule**: sequential e-process per `fable5-findings-01c` (`policy_version` cited in
  every verdict). Single-trial deltas below the MDE are *never* decisions.
- **Anti-gaming**: question selection, seeds, and n are evaluator-side constants; rotating
  audit-block correlation published with the verdict.
- **Sentinel suites with non-standard execution**: tool_use runs `force_mode: "repl"` with
  substring scoring on tool output. Moderate regressions (−0.2 to −2.9 on the 0–3 scale, 1–4 of
  5 questions missed) are **advisory only**; only catastrophic drops (≤ −3.0, ≥3 of 5 failed)
  are hard violations (`TOOL_USE_CATASTROPHIC_REGRESSION` in `safety_gate.py`). This threshold
  is part of the instrument — changing it is a new core version.

## P-QUAL-PROMO — Promotion / generalization quality

Fresh stratified draw, **n ≥ 200**, qids unseen within 60 days, broken-suite items excluded via
the suite-health table, runs only on `confirmed` candidates; its e-value multiplies the
candidate's running E (combined threshold E ≥ 100 for baseline changes).

## P-AB-1 — Orchestrator A/B (routing, prompts, features)

Paired where possible (same questions both arms); **N ≥ 100/arm for production-role decisions**
(the X-MAS lesson: a 20pp effect at N=25 collapsed to 4pp at N=100); every failure classified by
reason (backend outage / timeout / empty / genuine — `feedback_classify_eval_failures_by_reason`)
with infra-failure rate reported next to the effect; flag-state attestation across all workers
in the run header (the 1-of-6-worker lesson).

## P-SMOKE-1 — Sanity check (non-decision-gating)

A lightweight pass/fail sufficient to **unblock work**, **insufficient to gate any decision**.
Examples: REPL sentinel 4/5 after an infra fix; single-question smoke before a benchmark;
one-shot output-extraction check. Grammar: `4/5 toolrunner sentinel pass [P-SMOKE-1,
2026-07-11]`. Fails → investigate. Passes → proceed, but a protocol-level claim is still
required before any keep/revert/deploy/promote decision.

## P-CAL — Verifier/answer calibration (ECE / AUROC) [added 2026-07-23]

- **Instruments**: eval-tower.math-rebaseline (GSM8K+MATH-500, n=1,819/arm, math_verify,
  seed 42, production sampling; run E7c 2026-07-23) and eval-tower.calibration-baseline.v1
  (Scoring Verifiers HE-R+, n=820/arm, code_execution labels, seed 42; run EV-4c 2026-07-22).
  Era: E7-eval-instrument and later ONLY — pre-E7 calibration rows are void (proxy confidence).
- **ECE** = closed-top-bin stat_tests definition (`ece_instrument_era=ev11b_closed_bin_2026_07_20`),
  10 bins. Confidence = completion-probability geomean; a row gates ONLY with
  `confidence_is_real=True` — proxy or mixed-provenance ECE is an observation FOREVER.
- **Decision-capable uses** (ESC-7 Option A, granted 2026-07-23 — DOMAIN-SCOPED): (a) RLVR
  reward calibration/discrimination components at existing weights (rlvr_tiers) for
  provenance-clean CODE (code_execution-scored) rows only; (b) verifier-model promotion
  (EV-5/EV-7) may gate on code-domain ECE/AUROC vs the same-domain P-CAL baseline. MATH: ECE =
  cross-arm stability check only; math AUROC is an OBSERVATION (anti-discriminative 0.401/0.411
  — geomean length confounding) pending EV-CONF-2 (salient-token/answer-span confidence).
- **Baselines (era anchors)**: code ECE 0.2532/0.3216, AUROC 0.6337/0.5751 (frontdoor/
  worker_general, EV-4c); math ECE 0.2114/0.2199, AUROC 0.4013/0.4114 observation-only
  (worker_general/worker_math, E7c). Ledger rows: EV-4-calibration-baseline,
  EV-11-math-rebaseline (2026-07-23).

## P-PAIRED — Paired A/B significance verdict (McNemar) [STAGED 2026-07-23; operator-apply]

*STATUS: staged for human review — written by the implementation session, NOT applied; the
measurement trust boundary is human-amendment-only. The operator applies this block by hand
after auditing the cited implementation.*

- **Instrument identity.** Verdict surface = epyc-orchestrator
  `scripts/autopilot/paired_stats.py::mcnemar_verdict` (+ `verdict_from_result`,
  `MCNEMAR_EXACT_MAX_DISCORDANT`), driven from `eval_tower.py::screen_paired_arms` (each matched
  pair carries a `verdict` block), threaded per-role by `attach_role_paired_verdicts`. Producing
  instrument: eval-tower.math-rebaseline (GSM8K+MATH-500, n=1,819/arm, math_verify, seed 42,
  production sampling; `result.paired_significance` in each summary.json). Era:
  E7-eval-instrument+ ONLY — pre-E7 paired rows void (proxy-scored arms). Direction: lower
  two-sided p = stronger evidence of difference; the VERDICT, not the raw delta, is the decision
  object.
- **Verdict semantics.** Discordant counts from `mcnemar_from_vectors`: b = a_correct_b_wrong,
  c = a_wrong_b_correct. Verdict block = {verdict, method:"mcnemar", approximation,
  n_discordant, p_value, z, alpha, exact_max_discordant}. Method by n_discordant = b+c:
  ≤25 → EXACT two-sided binomial sign test ("exact_binomial", z null); >25 →
  continuity-corrected NORMAL approximation ("normal_approx", signed z; Edwards correction
  (|b−c|−1), two-sided p = erfc(|z|/√2)). Rationale: normal approx trustworthy only at b+c ≥ 25;
  the exact path's 2^n division overflows float64 past ~1000 discordant pairs — the switch is
  statistical AND numerical. Verdict at α=0.05: "indistinguishable" unless p < α AND b ≠ c; then
  "b_better" when c > b else "a_better". Provenance gate: a pair is scored ONLY when both arms
  declare and agree on {dataset_sha256, test_profile}
  (`paired_stats.require_matched_comparison`); mismatched/one-sided/missing provenance is
  refused to `mismatched_pairs`, never silently verdicted.
- **Decision-capable uses.** A P-PAIRED verdict MAY gate keep/prefer between two arms ONLY when
  the pair appears in `pairs` (identical dataset_sha256 + test_profile). Then: (a)
  "a_better"/"b_better" (p < α) is decision-grade evidence to PREFER the winner for that
  dataset+profile; (b) "indistinguishable" is decision-grade evidence of NO measured preference
  — it does NOT license a swap and MUST NOT be read as equivalence beyond this dataset/profile
  (report n_discordant so an underpowered null is visible). A verdict never gates across
  mismatched provenance, never upgrades a single-arm accuracy delta, never gates outside
  E7-eval-instrument+. Grammar:
  `verdict [P-PAIRED, n_discordant/method, YYYY-MM-DD, attest <summary.json ref>]`.
- **Baseline (era anchor)**: E7c math re-baseline
  (`orchestration/reports/eval_tower_math_rebaseline_E7c/summary.json`), worker_general vs
  worker_math, seed 42: b=61, c=58, n_discordant=119 → normal_approx, p ≈ 0.855 →
  "indistinguishable" (the ~0.2pp delta is inside the noise band). Ledger row:
  EV-11-math-rebaseline (2026-07-23). Tests: `tests/unit/test_paired_stats.py`,
  `tests/unit/test_eval_tower_paired_significance.py`.
