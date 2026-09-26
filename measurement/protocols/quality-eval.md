<!-- RATIFIED 20260730T103218Z. Annex Q of MEASUREMENT.md (same trust boundary, same
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

## P-CAL — Verifier/answer calibration (ECE / AUROC) [added 2026-07-23; decision uses SUSPENDED 2026-09-16]

- **SUSPENDED 2026-09-16 — speculative-decoding contamination** (amendment block; it deletes and
  edits no historical number). Every baseline in this block was captured on `draft-mtp` servers:
  E7c on worker_general/worker_math (gemma-4-26B-A4B MTP, `draft_max=2`); EV-4c on frontdoor
  (Qwen3.6-35B-A3B-MTP, `draft_max=4`) and worker_general (gemma-4-26B-A4B MTP). For every
  draft-accepted token, llama.cpp (v7 and v9) reports `prob=1.0` with an empty top-k. The
  completion-probability geomean therefore averages placeholder values, not model probabilities,
  over an unmeasured share of every answer. `confidence_is_real=True` does not clear this, because
  the flag certifies the confidence SOURCE, not the absence of placeholders. Status by value:
  - **E7c math** ECE 0.2114/0.2199, AUROC 0.4013/0.4114 (SUSPENDED): **CONTAMINATED, INVALID**
    as a calibration measurement, kept as history. The rows are saturated: 1528/1684 and
    1485/1628 carry confidence ≥ 0.999999 (observation, a recount of
    `question_results.ev11-*.jsonl` on 2026-09-16). As the primary explanation of the
    anti-discrimination, "geomean length confounding" (below) is superseded by the placeholder
    artifact (observation, not a claim; EV-CONF-2 decides).
  - **EV-4c code** ECE 0.2532/0.3216, AUROC 0.6337/0.5751 (SUSPENDED): **CONTAMINATED, size
    unmeasured**, demoted-to-prior. The rows are not saturated: 0/820 and 2/817 sit at ≥ 0.999999
    (observation). The placeholder share is diluted, not absent, and no row is known to be
    placeholder-free.
  - **Suspended decision uses, until EV-CONF-2 reports**: (a) the rlvr_tiers RLVR code-reward
    calibration/discrimination components, and (b) the EV-5/EV-7 verifier-promotion gate, may not
    gate on any P-CAL ECE or AUROC value; the math cross-arm ECE stability check is suspended
    likewise. P-PAIRED verdicts on E7c are correctness-scored and are NOT affected.
  - **Re-baseline rule (standing)**: a confidence metric (ECE, AUROC, or anything computed from
    token probabilities) is admissible under P-CAL only from (i) a spec-off run (no draft model,
    no MTP head, no n-gram/lookup drafting; serving identity recorded in the row), or (ii) a run
    whose per-token trace marks draft-accepted placeholder tokens and excludes them, reporting the
    excluded share. A row that meets neither condition is an observation, permanently.
  - **Lift condition**: EV-CONF-2 (the spec-off GPU probe; spec in the EV-CONF-2 box of
    `handoffs/active/autopilot-decision-plane-audit-2026-07-22.md`) reports. Restoring the
    decision uses, or appending replacement baselines, is a further human amendment. The values
    in the Baselines bullet below are never edited.
  - **Evidence**: epyc-orchestrator `b98dee18` (per-token trace; placeholder tokens stored as a
    sentinel and counted) and `f2e9ee07` (EV-CONF-2 probe driver; the spec-off arm fails closed
    when a draft is present). Both were merged 2026-09-16 via d8b915ee/88a2902d (epyc-orchestrator
    origin/main). Sidecars:
    `orchestration/reports/eval_tower_math_rebaseline_E7c/` and
    `orchestration/reports/eval_tower_calibration_baseline_HE-R+/*_ev4c/`. Operator decision
    2026-09-16, option (a): caveat now rather than wait for the probe.
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

## P-SERVE-SEL-1 — Text-LLM serving-selection load-sweep A/B (RATIFIED 2026-09-26)

*Ratified by the operator on 2026-09-26 in the orchestrator-design session (operator queue OP-62) and
applied through `scripts/operator/ratify_p_serve_sel_1_20260926.sh`. Prospective only: it governs
windows opened after this block landed, and no earlier run may be retro-certified under it. First
consumer: `handoffs/active/decision-aware-routing.md` DAR-LAT-3.*

**Scope.** Decision-gating claims that a change to the orchestrator's **selection policy** (a latency
or load term, a saturation guard, a live queue or progress term, or the weight of any of them)
improves, or does not degrade, TTFT-bound service on a text-LLM tier with the orchestrator in the
loop. The regime is a **single-instance tier** (the registered `-np`, unchanged) that saturates under
offered load and has a registered divert target. Not for: kernel or throughput claims (P-BENCH-\*,
P-GPU-1), speech (Annex S), a routing A/B with no load axis (P-AB-1), or displacement of batched work
across devices (P-SHED-1). This protocol specialises P-AB-1 for load: P-AB-1's failure-by-reason
classification and flag-state attestation apply unchanged, and its N ≥ 100/arm rule is replaced by
the block design below, because the decision unit here is the block.

**Instrument class.** `instrument_class=serving` is required: production servers on their registered
recipes, the orchestrator's streaming `/v1/chat/completions` in the loop. A `bench`-class number
cannot enter a P-SERVE-SEL-1 row (INSTRUMENT-CLASS-1).

**Metric.** Primary: **S = TTFT-SLO attainment per block**, the fraction of scheduled arrivals whose
first byte arrives within that item's TTFT budget (higher-better). Secondary, reported beside S and
never substituted for it: realized quality per suite (higher-better; a failed request scores 0, the
E17 rule), TTFT p50/p95 per block (lower-better), completions per minute (higher-better).

**Arms.**
- **A0** is the production incumbent, `category=OPTIMUM` (§3). Candidate arms (A1, A2, …) are
  `category=CANDIDATE`.
- Every candidate weight is predeclared on the scale of the existing selection cost term and is never
  tuned on the evaluation half.
- Arms switch per block inside ONE experiment API process (own port, captured PID, no relaunch), so
  every arm-to-arm comparison and the floor below have **unit = arm** (FLOOR-UNIT-1). A design that
  relaunches between arms has unit = process launch and must calibrate its own floor at that unit.
- The candidate set of each request is predeclared and restricted to {tier under test, its
  registered divert target}.

### Six rigor controls

1. **Frozen input manifest.** Frozen in `FROZEN-AT-LAUNCH.sha256` before the first arm block:
   - prompt items (seeded sample of an existing graded item set, item ids + sha256), a predeclared
     `max_tokens` cap and the live reasoning setting, so the workload is TTFT-bound;
   - the candidate pair, and a dry route-explain filter (no generation) that keeps only items the
     incumbent AND the candidate at zero load both route to the tier under test; the kept fraction is
     reported;
   - every frozen selection input with its digest: prior tables (keyed by role, device and
     topology_hash, with the live topology_hash at freeze), a read-only episodic snapshot, and any
     online learning (Q-updates) OFF for the window;
   - the live argv and environment of every server in the candidate set, the `kv_unified =` log line,
     and the kernel-store digests;
   - **TTFT budget per item** = 2 × the unloaded p50 TTFT of the tier under test for that item's
     prompt-length bucket, measured on the calibration half. The factor 2 is part of the instrument;
   - **load points** ρ ∈ {0.5, 0.8, 1.0, 1.25, 1.6, 2.0} × μ̂, where μ̂ is the tier's measured
     unloaded service rate on the calibration half. Saturating points are ρ ≥ 1.0;
   - open-loop, seeded Poisson arrivals; **one block = 40 arrivals**; ABBA arm order per ρ.
2. **Incumbent baseline.** A0 runs at every load point, in the same window as the candidates.
3. **Per-item raw outputs.** One durable directory per run (§5 durability: a `SHA256SUMS` and a
   README) holding `manifest.json`, `requests.jsonl`, `blocks.jsonl`, `summary.json` and `env/`
   (argv, environment, kernel digests, host health, region-claim witness). Every `requests.jsonl`
   row carries arm, block, ρ, arrival/send/first-byte/done timestamps, HTTP status and error class,
   the per-decision selection receipt, the admission snapshot, the live-state snapshot where an arm
   reads one, selection-time and final role, output text and hash, token counts and grader verdict.
4. **Holdout.** Items split 50/50 by seeded hash. The calibration half is used only for μ̂, the TTFT
   budgets and a sanity check on the frozen priors; every arm block runs on the evaluation half.
   **Time holdout:** a later window **W2, ≥ 24 h after W1**, repeats ρ = 1.25 with all arms in ABBA
   order and fresh arrival seeds.
5. **Complete denominator.** Every scheduled arrival counts. A late completion, a 503 (contention
   denial), a 429, an admission-queue-full error, a 413 or context overflow, the client hard deadline
   (predeclared as max(10 × budget, 600 s)) and a connection error are all TTFT-SLO misses, reported
   by class. The driver never retries.
6. **Predeclared decision rule** (below), frozen with the manifest.

### Floor

**F** = the 95% upper bound of |ΔS| over **24 A/A block pairs of the reference candidate arm at
ρ = 1.25**, run in the same window, with **unit = arm**, recorded with n and an interval
(FLOOR-UNIT-1). n = 24 is a minimum and is never reduced to fit a window.

### Decision rule

Candidate X beats comparator Y (a candidate over the reference candidate, or a candidate over A0)
only if ALL of the following hold:
- mean(S_X − S_Y) > F at **≥ 2 saturating ρ** in W1;
- the same sign and a gap > F at ρ = 1.25 in W2;
- realized quality is non-inferior: X ≥ Y − one per-suite quantum (§4);
- no ρ < 1 point degrades by more than F.

Otherwise Y is kept, and the result is written as a **BOUNDED-NULL-1** statement: the power bound
(which gaps the design excludes, at what number of blocks) plus the positive controls below.

**Intervals.** PAIRED-CI-1 with the small-K correction, computed **within a window only**. W1 and W2
are never pooled; W2 is a replication, not extra sample.

### Positive controls (BOUNDED-NULL-1, both directions)

- Per-request selection receipts show exactly-zero candidate terms in A0 and non-zero terms in every
  candidate arm that declares them.
- Every diversion carries an admission snapshot with `in_flight ≥ limit`, and no non-saturated
  snapshot diverts.
- An arm that declares a live-state term carries a fresh live-state timestamp on every request; every
  other arm carries null.

A run whose controls do not fire in both directions is recorded as `untested`, not as a negative.

### Preconditions (decision-grade requires ALL)

- A compute window granted through the session bus covering every device the candidate set touches;
  a CPU region claim **acquired** by wrapping the driver in `region-lock run`, plus a GPU lease when a
  GPU server is in the candidate set.
- AutoPilot quiesced by its owning session. The experiment session owns every API action in the
  window; the production API is not reloaded.
- Host-health preflight and the quiet-window preconditions of P-BENCH-1. Zombie checks use
  region-lock holders and captured PIDs, never process-name patterns.
- All other production servers show zero in-flight, **sampled during** each block.
- The live argv and environment of every server in the candidate set match the registered recipe,
  including the OMP environment stack.
- The write-side belief-kernel wiring for the run's records is in place before the first block.

Missing any precondition makes the run observation-grade. A precondition that fails during a block
stops the run; that block is re-queued, never dropped.

**Sizing and stop rules.** After calibration the session computes the projected window length. If it
exceeds the granted window, load points are dropped in the predeclared order 1.6 → 0.8 → 2.0. The
floor's n = 24 is never reduced.

**Scope limits.** Couplings that exist in the production topology (for example a GPU lane's host
threads sharing physical cores with the CPU region) are in scope and recorded, not removed. Traffic
from clients other than the orchestrator is out of scope and is stated as a limit. Raising `-np` is a
different experiment.

**Grammar.** `ΔS <X>−<Y> = <value> (<interval>) at ρ=<ρ>, W<n>, category=CANDIDATE,
instrument_class=serving [P-SERVE-SEL-1, blocks=<n>, YYYY-MM-DD, attest <run directory>]`.

**Provenance.** Designed in the 2026-09-26 orchestration prior-art research intake (Stage-3 plan,
item DAR-LAT-3), for the single-instance, TTFT-bound, saturated-tier regime that the static-prior
versus live-estimate literature leaves open.
