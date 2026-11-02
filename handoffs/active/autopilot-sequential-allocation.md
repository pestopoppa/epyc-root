# Autopilot Sequential Verdicts — the allocation rule, not the effect, was the binding constraint

> **Fold destination** (BRF-T1-F21, BRF-T1-1, route 1a, 2026-11-02): absorbs 1 handoff(s) as `## Track:` sections at the end of this file (`promptforge-mutation-safety-contract.md`). The body above the first track is the former `autopilot-sequential-allocation.md`.

**Status**: active — offline re-adjudication COMPLETE 2026-07-28 (zero inference). Two candidates sit
within ~10 trials of a confirm **inside `core_v1`** — but `core_v1` is closed and E8 is under a
fail-closed rebaseline hold, so SEQ-3 is gated on an operator era ruling (SEQ-3a) or a ~49-trial
clean re-run (SEQ-3b).
**Created**: 2026-07-28
**Priority**: HIGH — this determines whether the benchmark-Autopilot program was ever tested
**Categories**: benchmark_methodology, autonomous_research, routing_intelligence
**Parent index**: [research-evaluation-index.md](research-evaluation-index.md)
**Related**: [episodic-memory-integrity.md](episodic-memory-integrity.md) (separate store — the reseed
did not touch the journal)

## The finding

Measured over **393 sequential trials / 141 candidates** in `orchestration/autopilot_journal*.jsonl`:

- **Median 1.0 trial per candidate** (mean 2.79, max 41). **90 of 141** candidate×era groups received
  exactly one trial.
- **0 of 121** refuted trials were killed by futility (`E <= futility_e = 0.05`). Every refutation
  came from the *budget* rule.
- The strongest candidate `70902e4b665474e7` trips `k>=8 and E<2.0` at k=8 with **E=1.68**, then
  climbs to **E_quality 11.55 by k=40 — while still labelled `refuted` the whole way.**

`confirm_e = 20.0` is the Ville bound for α=0.05 and is untouchable. **`budget = 8` and
`budget_min_e = 2.0` (`src/autopilot_core/sequential_verdict.py:44-57`) are a compute-allocation
heuristic with no bearing on anytime-validity.** Relaxing them is statistically free.

## Re-adjudication result (2026-07-28, zero inference)

`scripts/analysis/readjudicate_sequential_candidates.py` re-folds the recorded per-trial `z` values
through the project's own `rebuild_candidate_view`, era-fenced by `core_id`, with `budget` and
`budget_min_e` relaxed and every other policy parameter untouched.

```
candidates CONFIRMED under the relaxed budget:              0
recorded 'refuted' that are NOT refuted once budget drops:  9
candidates still RISING when the run ended:                58

candidate           core      k          E     grow   need  recorded
70902e4b665474e7    core_v1  40    11.5507   1.0631      9  refuted
dd793a6ee43ce718    core_v1  24     8.7048   1.0943     10  refuted
85c3dcf25823c537    core_v1  15     2.7448   1.0696     30  refuted
db866b4a9fa37e03    core_v1  10     1.5856   1.0472     55  refuted
45129cc6ee5bac29    core_v1  12     1.5609   1.0378     69  refuted
```

**Verdict: the benchmark-Autopilot hypothesis is NOT falsified — it was never funded to a verdict.**
No candidate crosses `confirm_e` on evidence already purchased, but two are close and were still
rising steeply when cut.

**Caveat, stated plainly**: `need` is an *extrapolation* from the observed per-trial growth factor. It
assumes the effect persists at the same rate, which the data cannot guarantee — an e-process can
plateau or reverse. Treat it as a cost estimate for the next experiment, never as a predicted
outcome.

## Two defects in the verdict machinery

- [x] **SEQ-A — DISSOLVED, not fixed** ✅ 2026-08-12 (`mainB` subagent). Closing the parent to match its
      children: SEQ-A0 landed the neutral mechanism (`43108014`) and SEQ-A1 is VOID, so this box was the
      last thing still presenting a refuted premise as open work. Re-derived rather than inherited:
      `f2ad030e` is an ancestor of orchestrator HEAD, its axis attribution is live in
      `scripts/analysis/readjudicate_sequential_candidates.py`, and `pytest -k "readjudicate or
      sequential_verdict"` → **54 passed, 5 skipped**. **Residual defect found and fixed while
      verifying**: that script's MODULE DOCSTRING still asserted *"56 of 393 … The label is STICKY"* as
      fact — `f2ad030e` corrected the code and the inline comment and left the docstring, which is the
      first thing a reader sees and the source every later citation of "56 of 393" came from. Retracted
      in place (not deleted, so the still-true `70902e4b665474e7` bullet above it cannot be re-read as
      evidence for staleness). Live question remains **SEQ-B1**, with the operator.

      **Original filing preserved verbatim below — read it only together with the ⚠ premise correction
      that follows it; the two are one record and the claim does not survive without the correction.**

      **SEQ-A (as originally filed) — the `refuted` label is STICKY.** `state_name()`
      (`sequential_verdict.py:131-138`) is a pure function of current state, so a candidate that
      outgrows the kill condition should read `accumulating` again. It does not: **56 of 393 trials
      carry `state="refuted"` while `E >= budget_min_e` and `k >= budget`** — the persisted label
      contradicts what the policy's own function returns for that very trial. `70902e4b665474e7`
      crosses E=2.0 at k=10 and stays labelled refuted to k=40 at E=11.55.

      **What it actually costs, measured 2026-07-28**: the label does NOT stop allocation — that
      candidate kept receiving trials to k=40. What `seq_refuted` does is exclude a candidate from
      **promotion and positive strategy distillation** (`learning_exclusions.py:111-119`). So **3
      candidates are permanently excluded by a condition they no longer meet**:

      | candidate | k | E_quality |
      |---|---|---|
      | `70902e4b665474e7` | 40 | **11.5507** |
      | `dd793a6ee43ce718` | 24 | **8.7048** |
      | `85c3dcf25823c537` | 15 | **2.7448** |

      Reported by `readjudicate_sequential_candidates.py` under *SEQ-A: STICKY REFUTED LABELS*.

      > ### ⚠ SEQ-A's PREMISE IS FALSE — measured, not argued (2026-08-11, `mainB`)
      >
      > **There is no stale label. There never was.** The heading above, the "56 of 393", and the
      > 3-candidate table are all artifacts of the detector that produced them.
      >
      > `readjudicate_sequential_candidates.py:203` tested `state == "refuted" AND E_quality >=
      > budget_min_e` — a **JOINT** verdict against a **SINGLE** axis. `safety_gate.py:1529` stamps
      > `state` refuted when **either** axis refutes (`q_name == REFUTED or rate_name == REFUTED`)
      > and **recomputes it on every trial**. So a healthy quality axis beside a refuted RATE axis
      > read as a label that had failed to update.
      >
      > It manufactured the entire population: per SEQ-B below, `E_rate_noninf` never exceeds 2.0
      > anywhere in the corpus (max **1.1100**) against `budget_min_e = 2.0`, so essentially every
      > candidate's rate axis refutes once `k >= budget`.
      >
      > Detector fixed at orchestrator **`f2ad030e`** (reporting only, zero semantic change). It now
      > attributes each `refuted` label to an axis. Measured against the real journal:
      >
      > | bucket | n |
      > |---|---|
      > | refuted on the QUALITY axis | 6 |
      > | refuted on the RATE axis ONLY (quality healthy) | **3** |
      > | **UNEXPLAINED — joint refuted, NEITHER axis** | **0** |
      >
      > The 3 are exactly `70902e4b665474e7`, `dd793a6ee43ce718`, `85c3dcf25823c537`. They are
      > **correctly labelled** by the joint rule. The empty third bucket is the finding: it is the
      > only thing that would be a genuinely stale label, and it does not exist.
      >
      > **Consequence for SEQ-A1 (below): the question it poses is not real.** Nothing needs
      > recomputing. The live question is **SEQ-B1** — joint gate vs quality-primary — because those
      > 3 candidates are precisely the case SEQ-B1 names: *"a candidate that buys quality with
      > throughput can never be promoted — which may be exactly what you want."* `coordinator-agent`
      > withdrew a Horn A instruction on this basis and is taking SEQ-B1 to the operator.
  - [x] **SEQ-A0 — the mechanism, built NEUTRAL so SEQ-A1 is a one-line switch** ✅ 2026-08-11
        (`mainB`, orchestrator `43108014`). `SequentialPolicy.sticky_refuted`, **default `False`** —
        seq-v1 semantics reproduced byte-for-byte, the 3 candidates below still flip exactly as
        before, **75 passed** across the sequential-verdict consumer set. **The set, named so the
        number is checkable** (`auditor` 2026-08-11: the original citation said "every
        sequential-verdict consumer", which is not reconstructable — their two reasonable guesses
        gave 41 and 131):
        `tests/unit/` × {`test_restart_readiness_report.py`, `test_seq_rate_axis_paired_measurement.py`,
        `test_seq_readiness_report.py`, `test_sequential_verdict.py`,
        `test_sequential_verdict_sticky_refuted.py`} — 5 files, selected by
        `grep -rln 'sequential_verdict\|EProcessState\|seq_readiness\|review_ledger' tests/unit/`.
        Re-run 2026-08-11 after the note: 75 passed, unchanged. Plus `EProcessState
        .first_refuted_k`, recorded unconditionally as the process folds forward: **observing that a
        stop happened is free, and is not the same as deciding it is permanent** — capturing it now
        is what lets SEQ-A1 be settled from data rather than by re-running `core_v1`, which is over
        (era E8). Persisted trial state untouched; the field defaults to `None` so a state rebuilt
        from an older record behaves identically (pinned by test).
        **Numbers re-derived, not inherited**: against `readjudicate_sequential_20260728.json`,
        exactly 3 candidates flip `refuted`→`accumulating` — `70902e4b665474e7` (k=40),
        `dd793a6ee43ce718` (k=24), `85c3dcf25823c537` (k=15). Confirms the figures above.
        **Deliberately takes no side.** A lane brief phrased SEQ-A as "the function silently
        un-refutes — make it sticky", i.e. the inverse of this handoff's framing. Both readings are
        true: the FUNCTION is non-sticky (`state_name()` has no memory), the PERSISTED LABEL reads
        `refuted` where the function would not. So "make it sticky" is not a bug fix — it is SEQ-A1
        horn 2, and deciding it silently would settle a human-amendment-only question on a phrasing.
        **CORRECTION 2026-08-11 (`mainB`), to my own sentence above:** I wrote that the persisted
        label is "sticky (never recomputed)". **That is false and I checked it only later.** It is
        recomputed on EVERY trial — `safety_gate.py:1529` stamps it from a JOINT rule
        (`q_name == REFUTED or rate_name == REFUTED`). The divergence is joint-vs-quality-only, not
        staleness. See the SEQ-A premise correction under SEQ-A1 below; it changes what SEQ-A1 is.
  - [x] **SEQ-A1 — VOID, superseded by the premise correction above** ✅ 2026-08-11 (`mainB`).
        Not "decided" — **dissolved**. Horn 1 ("recompute the verdict label per trial") is already
        what the code does; horn 2 ("keep stickiness") preserves a stickiness that does not exist.
        Recomputing from quality-only `state_name()` would not restore pure-function semantics, it
        would **drop the rate axis out of the verdict** — which is SEQ-B1, a different
        human-amendment-only question. Routed there; do not re-open this row.
        ~~SEQ-A1 — **OPERATOR DECISION**: recompute the verdict label per trial from `state_name()`
        (restoring the policy's own pure-function semantics), or keep stickiness and document it as
        "a stop decision is final". Either is defensible — a stopped e-process arguably *should*
        stay stopped — but the current state is neither: the label is sticky while allocation is
        not, so candidates keep burning trials whose evidence is then discarded. This changes which
        candidates are promotable, so it is **human-amendment-only** per MEASUREMENT.md.~~
- [ ] **SEQ-B — the promotion gate is unreachable, but NOT because anything is broken.**
      **CORRECTED 2026-07-28** — I first wrote that "the rate e-process is frozen". **It is not.**
      Measured: `E_rate_noninf` takes **82 distinct values** (min 0.5213, median 0.9100, max 1.1100)
      and `z_rate` takes 179 distinct values with median **−0.8979** and only **7.9% positive**. The
      axis computes fine; it is reporting that candidates **genuinely do not improve throughput**.

      The gate is `combined_E = min(E_quality, E_rate_noninf)` (`autopilot.py:1953-1966`,
      `binding_joint` mode) against `required_E = 100.0`. For the top candidate that is
      `min(11.55, 0.556) = 0.556` — real quality evidence entirely masked by a real negative rate
      result. **18 of 393** trials ever exceed `E_rate 1.0`; **0** ever exceed 2.0.

      So this is a **policy question, not a defect**: do you want a JOINT gate (quality AND
      throughput, current `binding_joint`) or quality-primary with rate advisory? The advisory mode
      already exists — `quality_only_rate_advisory` — and was exercised in 35 trials under an
      operator bridge (`rate_axis_mode = operator_p0_2_rate_alpha_bridge`).
  - [ ] SEQ-B1 — **OPERATOR DECISION**: keep the joint gate, or move the rate axis to advisory. This
        changes what counts as a promotion, so it is a measurement-trust-boundary change and is
        **human-amendment-only** per MEASUREMENT.md. Note that under a joint gate, a candidate that
        buys quality with throughput can never be promoted — which may be exactly what you want.

## Tasks

- [x] SEQ-1 — Verify the k=8/allocation claims directly against the journal. ✅ 2026-07-28
- [x] SEQ-2 — Build and run the offline re-adjudication (zero inference). ✅ 2026-07-28
      Report: `orchestration/reports/readjudicate_sequential_20260728.json`
- [ ] SEQ-3 — **Resume the top candidate to a verdict. GATED — read the era problem first.**

    **The "~9 more trials" figure is only valid inside `core_v1`, and `core_v1` is over.**
    All 393 sequential trials carry `core_id: core_v1`, spanning 2026-06-18 → 2026-07-16. The
    current era is **E8** (`instrument_eras.yaml:166`, from 2026-07-25T18:38:43Z, scope
    `eval_quality`), which explicitly opens *"a fail-closed E8 AutoPilot rebaseline hold: pre-v8/E7
    baseline and MAD observations are historical priors until an operator-ratified E8
    quality-baseline reseed writes fresh values and windows."* `core_v1` has no era row at all —
    the only `core_id` the registry declares is `core_v2` (E4).

    Folding E8-instrument z's into a `core_v1` e-process would mix non-comparable evidence, which is
    the exact defect the era registry exists to prevent. So there are two honest paths:

  - [x] ~~SEQ-3a — **Bridge (cheap, needs an operator ruling).** If an operator judges the E8~~ (closed 2026-10-29 audit: SUPERSEDED → ruling_op19_e8_chain_20260827.json / 1ee8bd7cc: E8 chain retired, eval_quality left E8 on 2026-08-05 (now E16) so an E8-vs-core_v1 comparability era row is moot)
        instrument comparable to `core_v1` for this candidate's axis and records an era row saying
        so, then ~9-10 further trials (≈2.6 eval-hours at the historical ~935 s/trial) settle it.
        **This is a measurement-trust-boundary decision and is human-amendment-only** per
        MEASUREMENT.md — an agent must not make it.
  - [ ] SEQ-3b — **Re-run clean under E8 (expensive, no ruling needed).** Restart the candidate at
        k=0 under the E8 instrument. At the observed growth of 1.0631×/trial it needs **~49 trials**
        to reach `confirm_e=20.0` — roughly **12.7 eval-hours**, not 2.6. Also gated on the E8
        quality-baseline reseed completing and being operator-ratified, since the hold is
        fail-closed.

    **Candidate identity for whoever runs it**: `70902e4b665474e7`, species `seeder`, tier 1,
    `core_id core_v1`, last trial `1067` (2026-07-03, git tag `autopilot/trial-1067`), config_diff
    `{n_questions: 18 → 16, suites: [...] → null}`, hypothesis "Seed 16 questions across all",
    last state `k=40 E_quality=11.5507 lambda=0.5 r_eff=11`.
- [x] **SEQ-B ROOT-CAUSED AND FIXED** ✅ 2026-08-04 (epyc-orchestrator `f1a6b23b`). **The prior
      SEQ-B text in this handoff was WRONG** — it read "the axis computes fine; it is reporting that
      candidates genuinely do not improve throughput". It did not compute fine, and the same
      candidates measure **+13% to +27% faster** once the measurement is paired.

      Root cause: a mis-paired measurement, not a mis-specified alternative.
      `EvalTower._aggregate_decision_partitions` returns an `EvalResult` whose `n_questions` counts
      only the DECISION partition (55) while `eval_wall_s` is the FULL batch's wall clock (65), and
      the incumbent comparator counted the full 65. Candidate rate = 55/wall vs incumbent 65/wall
      **on the same trial** — so an unchanged config measured 0.846x its own throughput, giving
      `z_rate = -0.208` every trial. `next_lambda` clipped the negative running mean to 0, the
      wealth factor became exactly 1.0, and it froze. Evidence: `E_rate_noninf == 0.9100` in
      **192 of 396 rows** — precisely `1 x (1 + 0.1 x -0.9)`, one update then frozen; `z_rate` at
      the clip floor in **199/396 (50%)**.

      Second defect, the same absence-vs-zero class as the reliability floor and
      `throughput_unmeasured`: `task_rate_qph_from` returns `0.0` as its "unavailable" sentinel
      while the guard tested `is not None`, so an UNMEASURABLE trial was consumed as a MEASURED
      zero questions/hour. Now returns `None` and the axis is skipped.

      Third: `rate_noninferiority_z` clipped `y` two-sided, which truncates the null-side lower
      tail, lifts `E[z]` above 0 under H0, and makes the wealth a **submartingale** — Ville does not
      apply. Fixed by lowering the clip to `-1.0` (never binds, since `y >= -1` identically).

      Replay over all 396: `z_rate` at clip floor 50% -> 0%, positive evidence 8% -> 69%, three
      candidates cross `E_rate = 20`, one reaches 222, **zero false confirms**. NO THRESHOLD CHANGED.

- [ ] **Decide whether to re-arm the sequential gate.** Currently `AUTOPILOT_SEQ_VERDICT=0`
      (operator unblock, 2026-08-04) because an unreachable gate meant AutoPilot could not ratchet at
      all. Re-arming changes what counts as a promotion -> human-amendment-only. **On current
      evidence re-arming would RE-BLOCK the ratchet rather than restore it**: post-fix the binding
      constraint is the QUALITY axis (max `E_quality` 11.55 vs bar 20). Coupled switch:
      `AUTOPILOT_SEQ_P0_2_BRIDGE` `1 -> 0` makes the rate axis binding again (advisory today).

- [ ] **The real reason `E_quality` never cleared 20 is trial starvation, not calibration.**
      Measured over the journal: **89 of 141 candidates got exactly ONE trial** (median k = 1). An
      e-process accumulates multiplicatively; at k=1 it cannot clear any bar. The two leading
      candidates were close — `70902e4b665474e7` at k=40 reached E=11.55, **~9 trials short** at its
      observed growth, and `dd793a6ee43ce718` at k=24 reached 8.71, ~10 short. This is the same
      finding as the 2026-07-28 re-adjudication (`budget=8` / `budget_min_e=2.0` killed 121 of 121
      refutations, a compute heuristic with no bearing on anytime-validity). **Fix the allocation
      before concluding anything about `confirm_e = 20`.**

- [x] ✅ 2026-11-01 — APP `b336f50b7efb77644a492c707d4ffc503d69d744` plus `ddb6391714483740ac1c87e6fca7d3b797ef491c`; [49 focused controls and baseline proof](https://github.com/pestopoppa/epyc-orchestrator/blob/f55ad5d9cd3ce708b1704ba874d0605473feebeb/artifacts/engineering/seq-rate-era-fence-20261101/README.md). [belief: cc] **Rate-axis comparator has no era fence of its own.** The incumbent pool is the 120 most recent
      same-tier trials; `quality_exclude_before_ts` is scoped `eval_quality` only. Post-fix median
      measured lift is **+4%, inside the 5% margin**, so "candidates really are faster" cannot be
      distinguished from "the comparator lags a host that got faster". Main residual anti-conservative
      risk.

  - 2026-11-01 codex3 acceptance: The comparator and prior rate statistics now use the existing ratified speed-era cutoff, including the indirect action gate. Prior rate z requires an original strictly typed witness of both speed and quality cutoffs; missing, malformed and mismatched history is not retrofitted. Cached verdicts use the existing side-effect-safe upgrade path, so an unfenced cached statistic is never stamped as new evidence, failed caches do not become passes, and MAD/counters are not duplicated. The focused controls passed 49; a broader failure was independently reproduced on the original source bytes. This closes the engineering fence, not the historical host-drift question: no new speed boundary, threshold, activation or scientific comparison is claimed. [belief: cc]

- [x] SEQ-B3 — Delete the unused `_axis_refuted_factory`. ✅ 2026-10-29
      Orchestrator main `7678711d5b4aa4431abcd089a429b0561180aa29` removes the factory;
      source and test searches found no callers or tests binding it. The existing attribution
      and refutation suites passed all 23 tests after integration. Canonical `axis_refuted`
      and report logic remain unchanged. [no-belief: unused-code removal; no measurement claim]
- [x] ✅ 2026-10-31 SEQ-B4 — Decide explicitly whether the refutation record should carry `k_rate` alongside the QUALITY axis. Evidence: orch `bd2f7105a6b04fc9f9cffba0dff861c6e79c1c8d`; `tests/unit/test_seq_refutation_capture.py`; `/mnt/raid0/llm/tmp/refactor-seq-b4-20261031/TESTS.log` (36 pass). [no-belief: journal capture/reconstruction correction; policy thresholds unchanged]
      New live records and reconstruction use observed `k_rate`; legacy absent counts retain the prior fallback without invented history. Original gap: the QUALITY
      axis's `k`, which it currently reuses for both axes (matching the journal's single `k` and the reader)
      even though the two can differ when the rate axis was skipped on earlier trials
      (`scripts/autopilot/safety_gate.py:1780`) (found 2026-09-14, noninf sweep).

*Declined 2026-09-14: "the rate-axis comparator still has no era fence of its own" (`handoffs/active/autopilot-sequential-allocation.md:265`)
— not filed because it IS the open **Rate-axis comparator has no era fence of its own** box at that line.*

*Declined 2026-09-14: "no live journal row will carry a `refutation` record while the sequential path stays
default-off (`AUTOPILOT_SEQ_VERDICT=0`)" — not filed because re-arming is the open **Decide whether to re-arm the
sequential gate** box at `:249`, an operator decision, and the observation adds no separate action.*

- [x] SEQ-A — Sticky `refuted` label (above). ✅ 2026-10-29 (audit: handoffs/active/autopilot-sequential-allocation.md SEQ-A0 [x] (43108014, 2026-08-11) and SEQ-A1 [x] VOID 2026-08-11: question dissolved, routed to SEQ-B1; all children closed) [no-belief: audit-reconciliation]
- [x] ~~SEQ-B — Frozen baseline-promotion gate (above).~~ (closed 2026-10-29 audit: DUPLICATE → handoffs/active/autopilot-sequential-allocation.md:169 (canonical SEQ-B box); :287 is a pointer copy)
- [x] SEQ-4 — Re-examine the 9 candidates whose refutation does not survive the relaxed budget. ✅ 2026-07-29 — deterministic re-adjudication in [`readjudicate_sequential_20260728.json`](../../epyc-orchestrator/orchestration/reports/readjudicate_sequential_20260728.json) confirms all nine under the same era-fenced `core_v1` evidence; none reaches `confirm_e=20.0`.

      **Disposition:** `70902e4b665474e7` (E=11.5507, ~9 trials estimated) and
      `dd793a6ee43ce718` (E=8.7048, ~10 estimated) are the only credible continuation
      candidates, and are already represented by the SEQ-3 era-gated paths above. The
      remaining seven do not create an independent retry: `85c3dcf25823c537` needs an
      estimated ~30 trials; `db866b4a9fa37e03` ~55; `45129cc6ee5bac29` ~69;
      `4b6b454ea4f884fd` ~263; `3055f1e32fac0316` ~1699; and
      `b738287be98c3372` / `80aa44d93a242af5` were falling (growth <1). Those estimates
      are not forecasts; all are historical-`core_v1` priors and cannot be continued
      without the SEQ-3a bridge ruling or the clean SEQ-3b E8 restart.

- [ ] **SEQ-4 — zero-inference allocation replay: would a bandit allocator have reached confirm_e on the stored pool?** Re-fold the 141 stored candidates / 393 trials under (a) BaSE-style UCB/Thompson routing (intake-1456) and (b) fluid-style portfolio AUC objective (intake-1457); compare against the fixed budget=8 heuristic; report AUC-frontier vs endpoint. Offline only — does not touch the human-amendment-only SEQ-3/SEQ-B1 decision or re-arm any gate.

## Rider — retroactive objective change: what survives it, what does not (2026-08-11)

**Operator position, 2026-08-11, ACCEPTED**: as long as results and progress are tracked diligently,
the to-be-optimized metric may be changed later, and whatever is needed to keep optimizing in the new
direction can be recomputed from that moment forward.

**Operator context**: the Pareto frontier is sparse today (models being swapped, infra bugs still
landing), so deliberately choosing throughput-penalized / quality-favoured configs is premature. The
operator may authoritatively choose them later. AutoPilot's hypervolume is quality × tasks-per-hour;
unless the tradeoff is exactly inversely proportional there should be a non-trivial interior optimum,
plausibly near the frontier's highest-curvature (knee) point.

### F1 — the claim holds, CONDITIONALLY: re-aiming runs over stored COMPONENTS, never over stored SCALARIZATIONS

Verified in code, not taken on report:

- `experiment_journal.py:191-265` — `JournalEntry` persists the raw axes as top-level fields
  (`quality`, `speed`, `cost`, `reliability`), plus `eval_details`, `harness_metrics`, `seq`.
- `experiment_journal.py:336` — the direction comment is exactly as cited: the optimizer declares
  `directions=["maximize"]*4`, the third objective is NEGATED cost, so the raw `cost` field on the
  row is `lower_better`. The row stores raw cost; the sign lives in the reader.
- `experiment_journal.py:289` — `eval_details["objective_policy_live"]` is read per row, as cited.
- The objective vector is **derived at read time**, not stored:
  `tier_specs.py:344-366` `_policy_aware_objectives_from_row` dispatches on the row's own recorded
  policy; `tier_specs.py:328-341` `_rate_objectives_from_row` rebuilds `(quality, qph, -cost,
  reliability)` on demand; `tier_specs.py:220-230` `seq_task_rate_qph_from_row` recomputes
  tasks-per-hour from `question_results` + `eval_wall_s`. This is the mechanism that makes the
  operator's claim true — and it has already been exercised once, on the tokens/s → qph axis flip.

**The picture is more partial than the two cited lines alone suggest — state it plainly.** Measured
over `orchestration/autopilot_journal*.jsonl`, 1372 trial rows:

| write-side field | rows carrying it |
|---|---|
| 4 raw components (`quality`/`speed`/`cost`/`reliability`) | 1372 / 1372 |
| `eval_details.eval_wall_s` | 1147 / 1372 |
| `eval_details.question_results` (rate-axis numerator) | 523 / 1372 |
| `eval_details.objective_policy_live` | 534 / 1372 |
| `measurement` claim tuple (added 2026-08-10) | **0 / 1372** |

So: the 4-axis re-aim is fully retroactive; a re-aim needing the question ledger is retroactive over
~38% of history; and the era label is *inferred from absence* on the other ~61% —
`tier_specs.py:352-360` says so outright ("pre-flip rows … have no question ledger at all"). The
claim-tuple hook exists in code but has zero rows behind it yet.

This is the belief-kernel rule in CLAUDE.md, restated on a second store: the write side is cheap and
permanent, the read side cannot be retrofitted, and `benchmarks/results` (4,562 files, no write-side
hook, 0/200 sampled with a usable claim tuple) is the standing counterexample.

**A metric change is structurally an ERA BOUNDARY, and the machinery already exists.**
`epyc-orchestrator/orchestration/instrument_eras.yaml` was amended four times on 2026-08-11 under
operator signature (`53fc3250`, "4 rows, none struck"). **Recommendation: any future objective change
is recorded as an era row, never as an edit.**

### F2 — the exception that matters: rescoring is retroactive, STOPPING is not

The sequential gate does not merely score candidates — it decides which ones keep GENERATING data
(`safety_gate.py:1528-1529`: `if q_name == STATE_REFUTED or rate_name == STATE_REFUTED: state =
"refuted"`). A candidate refuted under today's joint rule stops accumulating trials. Under a future
objective you can rescore every trial that exists; you cannot recover trials never run. **A stopping
rule is a data-generating decision wearing the costume of a scoring decision, and it is the one thing
a future metric change cannot undo.**

Concretely, and exactly the configuration class the operator says they may later want:
`70902e4b665474e7` (k=40), `dd793a6ee43ce718` (k=24), `85c3dcf25823c537` (k=15) stopped under the
joint gate because they buy quality with throughput.

- [x] SEQ-B2 — Capture the refutation counterfactual AT STOP TIME: record which axis refuted and the margin on the other. ✅ 2026-09-14 (`seqb2`, `epyc-orchestrator` `4c220b11`, branch `fix/noninf-seqb2`). Write side landed: `safety_gate.py::_sequential_verdict` now writes `block["refutation"]` (`seq-refutation-v1`: `refuting_axis`, `refuting_margin`, `other_axis`, `other_axis_margin`, `both_axes_refuted`, `n_trials_at_stop`, per-axis `{wealth,k,refuted,margin,threshold,rule}`, policy `thresholds`, `captured_at`) on the refuted branch ONLY — additive, legacy and non-stop rows load unchanged, no journal file on disk touched. The predicate is now ONE canonical definition (`sequential_verdict.axis_refutation` / `refutation_record`), and `readjudicate_sequential_candidates.py` was reduced to a thin delegation that PREFERS the live field (`refutation_of`) and falls back to reconstruction for pre-SEQ-B2 rows, tagging every reported row and JSON record with its provenance. Attribution mirrors the script's own `if/elif` exactly: quality first then rate, `both_axes_refuted` carried separately, `null` = the UNEXPLAINED bucket, an unmeasured axis never refutes. Sign convention documented: `margin = wealth - threshold`, negative = refuted, futility inclusive / budget strict. 17 new tests (`tests/unit/test_seq_refutation_capture.py`), including `test_live_and_reconstructed_agree_on_a_synthetic_candidate`; `pytest tests -k "sequential or safety_gate or readjudicat"` 268 → 271 passed, 0 failed. Clean against `fix/noninf-etr` (`merge-tree` exit 0). SEQ-B1 (joint-gate vs quality-primary) remains the operator's, untouched.

### F3 — knee / max-curvature is not scale-invariant

Curvature of a Pareto frontier changes under rescaling of the axes. Quality is roughly [0,1] while
tasks-per-hour is order [0,600] (`tier_specs.py:203` returns `n / (wall/3600)`), so "the
highest-curvature point" is **undefined until a normalization is fixed — and the normalization
silently does the real work.** Hypervolume is also scale-dependent, but it forces the reference point
to be stated explicitly, which is why it is the more honest default.

**Recommendation**: if knee-selection is ever adopted, the normalization is a declared and ratified
quantity (an era row), not an implementation detail.

The operator's accompanying observation is correct and worth recording: a strictly inversely
proportional (hyperbolic) tradeoff makes every frontier point equivalent under a product objective, so
a genuine interior optimum requires curvature away from that.

### Background, not an open question — SEQ-B1 posture

SEQ-B1 (joint gate vs quality-primary with rate advisory) remains human-amendment-only and
**UNDECIDED**. On 2026-08-11 the operator stated the current joint-gate behaviour **"is fine for
now"** and explicitly deferred the change to a future in which the frontier is well populated.
Recorded here as a dated operator position so nobody re-opens it as a defect: **the gate is working as
designed; nothing is broken.**

## Why this is independent of the episodic-memory work

The candidate evidence lives in `orchestration/autopilot_journal*.jsonl`, a different store from
`orchestration/repl_memory/sessions/`. Journal mtimes (2026-06-27, 2026-07-27T08:23) predate the
2026-07-27T22:07 reseed, and `rebuild_candidate_view` folds *journal-derived* z sequences. **Scrubbing
and reseeding episodic memory cost this analysis nothing.**

## Reporting

Record SEQ-3's outcome here with the trial count actually spent and the final E. If the candidate
crosses 20.0, the program has its first genuine confirm and the allocation rule should be
re-specified. If it plateaus, that is equally decision-grade — and far cheaper than the ~347
eval-hours already spent without a verdict.

## Research Intake Update — 2026-09-25 (Shinka parent-selection replay)

- [ ] **SEQ-SHINKA-1 — Run the first policy screen over the shared selector-replay package.** Consume the immutable journal/candidate graph, incumbent policy, outcome bytes, task order, holdout, and digests frozen by `AP-DGM-PROV`; do not generate a second candidate campaign. Compare the incumbent with rank power-law and weighted score-times-inverse-offspring selection under the same eligible decisions, evaluator calls, proposer tokens/cost, and wall budget. Write per-decision choices and held-out continuation through `VB-DGM-1`, retaining invalid, failed, and abstained decisions in the denominator. Report choice agreement separately from outcome change and test time-split or bootstrap stability where the 393-trial / 141-candidate record permits it. Stop if policies select the same parent on at least 95% of eligible decisions, if differences do not improve held-out continuation over the incumbent and score-only controls, or if gains reverse across holdouts. A stable gain permits one bounded live paired follow-up and release of the ALE trigger; it does not authorize a selector change. Sources: intake-779#record, intake-1595#record, intake-1596#record.
  - **Implementation checkpoint 2026-09-26:** root commits `37e74b28`, `f434bad5`, and `e8ca0811` implement separate seeded rank-power-law and weighted score-times-inverse-offspring screens over one immutable package. `replay-both` seals two five-arm receipts plus one aggregate digest; fixtures prove denominator retention, paired continuation checks, chronological blocks, cluster bootstrap stability, and all stop rules. The real 393-row record cannot support the screen without inventing eligible menus, holdout assignment, model/decoding identity, or unchosen-parent outcomes, so the historical task remains open and inference-gated by prospective capture rather than being reported as a null result.

**Dormant follow-on:** a full ShinkaEvolve or ALE campaign becomes active only if this replay beats matched simple controls on held-out continuation, or a live long-horizon engineering campaign requires ALE-style evaluation. Until then, reuse this replay and its receipt rather than launching iterative candidate generation.

## Research Intake Update — 2026-10-20 (harness cluster)

Operator-approved 2026-10-20 via research intake (plan sha256 1dc83054706ca0bae002602307b0d9ba6435b010be4d6ffd8a495a04605f3967). Monitor and knowledge records below are prose: no checkbox, no index next action.

- [x] **SEQ-5 — Lifetime promotion-attempt ledger and screening-channel diagnostics in `seq_readiness_report` (read-only; no gate change; zero inference).** Verified 2026-10-20: the `alpha_wealth` block (`scripts/autopilot/seq_readiness_report.py:395-428 @5d4ad2c0`) has no K_opened, union-bound or lifetime field; it counts every fingerprint with any journaled `seq.candidate`; and an attempt opened but interrupted before its fresh-eval row exists is not recoverable from the journal. Add (proposed names; keep existing keys untouched): `promotion_attempts_opened`, `promotion_attempts_finalized`, `promotion_attempts_failed_or_interrupted`, `promotion_alpha_per_attempt` (1/`SEQ_PROMOTION_FINAL_CONFIRM_E`, 0.01), `lifetime_false_promotion_bound` (per-attempt alpha x K_opened, the union bound), `promotion_alpha_per_attempt_for_declared_delta_life` (delta_life / K), `fingerprints_confirmed` (R), `est_false_confirm_fraction` (expected_false_confirms / max(R,1), a conservative all-null heuristic), `cumulative_rate_drift_bound` (promotions x `rate_noninferiority_margin` 0.05) and `rate_reference_is_latest_only` (true by construction: the rate and quality nulls are rolling medians and profiles over the 120 most recent incumbent-representative trials, `autopilot.py:3873-3938`). K_opened from the journal alone is a lower bound unless the pending-promotion state transition is also journaled; decide between reporting a lower bound and adding an append-only 'opened' journal event (a write-side change, still no gate change). Declare in the report what an instrument-era boundary does to charged alpha: today it resets the charged set (`quality_exclude_before_ts`, `autopilot.py:3847-3851`). The ledger is a derived fold of the already-ingested journal, not a new measurement source (descriptive-census stance); if it is ever cited to gate a promotion it needs a ClaimTuple first. Follow-up triggers: K_opened above about 5 per quarter reopens decision package DP-A option (b); fingerprint confirmations still binding after the era and rate-axis faults are fixed reopens DP-C option (b) (`intake-2174#01`, `intake-2188#00`, `intake-2187#02`). ✅ 2026-10-21
  - 2026-10-21 (noninf-gates) result. `promotion_attempt_ledger` in `src/autopilot_core/sequential_replay.py`; `seq_readiness_report.py` merges its keys into the `alpha_wealth` block (existing keys untouched) and prints a ledger line (epyc-orchestrator `ea8c7338`). Frozen input: journal snapshot sha256 `6bb790ba837c9ea23f9e6ebd1a8ff00e354baf196ec7fe830d02dd54fc8c5b4a` (autopilot_journal.jsonl 18257825 B + autopilot_journal_1.jsonl 19801823 B; 1372 rows).
  - Result: `promotion_attempts_opened` 0 (a LOWER BOUND, flag `promotion_attempts_opened_is_lower_bound` true), finalized 0, `promotion_alpha_per_attempt` 0.01, `lifetime_false_promotion_bound` 0.0, `fingerprints_confirmed` 0, `est_false_confirm_fraction` 0.0, `cumulative_rate_drift_bound` 0.0, `rate_reference_is_latest_only` true. The journal holds 141 tested fingerprints and zero rows with `seq.confirmed` or a fresh-eval promotion block, so K_opened is 0 and the DP-A (about 5 per quarter) and DP-C triggers are not met. Era boundary: `quality_exclude_before_ts` leaves 0 rows at or after the boundary, so the live charged set is empty; the report states that an instrument-era boundary resets charged alpha. The task's choice (report a lower bound vs add a write-side 'opened' event) is taken as lower bound; adding an event is a write-side change not made here.
- [x] **SEQ-6 — Counterfactual replay of the sequential gate under one frozen null per candidate (zero inference; no gate change).** Verified 2026-10-20: `ref_snapshot` does not exist in code; `_seq_inputs_for_trial` (`scripts/autopilot/autopilot.py:3812 @5d4ad2c0`) rebuilds the null from the 120 most recent incumbent-representative rows on every trial, so a kept candidate enters later nulls and each stored z was computed against the null as it stood then. Recompute each trial's quality z from stored `eval_details.question_results` under ONE frozen null per candidate (the profile as of its first trial) and report how many verdicts and E values change relative to the live rolling null. Anytime-validity needs the reference fixed before observation (`intake-2173#01`, `intake-2174#01`). Frozen input: the journal snapshot digest; denominator: all candidates with at least the live minimum of 3 baseline rows, the rest counted as not replayable; decision rule predeclared: report only. Changing the live null changes what counts as a promotion and belongs to the operator (human-amendment boundary). ✅ 2026-10-21
  - 2026-10-21 (noninf-gates) result. `frozen_null_replay` in `src/autopilot_core/sequential_replay.py` (epyc-orchestrator `ea8c7338`). Frozen input: journal snapshot sha256 `6bb790ba837c9ea23f9e6ebd1a8ff00e354baf196ec7fe830d02dd54fc8c5b4a` (autopilot_journal.jsonl 18257825 B + autopilot_journal_1.jsonl 19801823 B; 1372 rows). 119 (candidate, tier) groups with seq rows and vectors; 118 replayable; 1 not replayable (fewer than 3 baseline rows at its first trial).
  - 2026-10-21 (noninf-gates) mismatch characterization (epyc-orchestrator `c7abc05e`). Of the 97 trials whose journaled z the rebuilt null did not reproduce (all tier 1, trials 1050-1282: 60 revert, 37 excluded), 79 are explained by one cause: bug tag `backend_connectivity_pollution_20260708` (26 rows, trials 1049-1263) was applied retroactively, so the live null still contained those rows when the later trials ran. Treating it as present below trial 1225 (a cutoff FITTED on this journal, not a recorded fact) lifts matches from 236 to 315 of 333. 18 remain unexplained, clustered at trials 1225-1282 right after the cutoff (a single cutoff is an approximation of staged tagging). Ruled out by trying each: window 30/60/100/119/121/240/unbounded fixes 0 or 1 of 97 and breaks 137-222 matching trials, so 120 is right; dropping the tier filter, dropping the learning-exclusion rows and the incumbent-only rule all fix 0; the instrument-era fence is not a cause (no row is at or after the boundary); 1 trial (tier 2) has no rebuildable null. Rerun on the matching subset (112 of 118 groups, 294 steps; 6 groups with an unreproduced z dropped): the conclusion is unchanged: 2 groups change final verdict, 19 steps change, both groups cross confirm_e only under the frozen null, journal and rebuilt rolling cross in 0. With the cutoff rule on all groups: also 2 and 19. Ticked with the caveat that the 18 residual trials are unexplained.
  - Harness validation first: the journaled z is reproduced by rebuilding the rolling null from all usable same-tier rows in 236 of 333 trials; the current-code rule (incumbent-representative rows only) reproduces 0 of 323, so the journal predates that filter. Counterfactual figures are therefore frozen vs the REBUILT rolling null and carry that infidelity. Result: 2 of 118 groups change final verdict (both accumulating to confirmed under the frozen null), 19 of 323 steps change verdict, 23 groups have E moved by over 1 percent, median |log10 E ratio| 0.0, max 1.148. Groups crossing confirm_e: journal 0, rebuilt rolling 0, frozen 2 (candidates 70902e4b665474e7 E 11.55 to 162.33 and dd793a6ee43ce718 E 8.70 to 27.26). Report only; changing the live null is the operator's.
- [x] **SEQ-7 — Paired-z replay over accepted mutations: false-elite rate and rounds a stop rule would have saved (read-only, zero inference).** For each journal row with `keep_revert_decision == "keep"`, compute the paired discordant-pair statistic against its predecessor incumbent's per-question outcomes (`eval_details.question_results`; `paired_stats.mcnemar_from_vectors` and `compare_fingerprints` already exist) and report the share of accepted mutations whose paired statistic is below the 1.96 equivalent (false-elite rate) and the number of rounds a paired-z stop rule would have saved; without the paired screen the source loop showed phantom progress and never terminated (`intake-2176#03`). State the unit caveat in the result: an AutoPilot trial is one pass over about 37 scoreable questions (P-QUAL-T1), not three attempts per question, so the published screen cannot be copied verbatim and the available paired unit is the McNemar form. Frozen input: the journal snapshot digest; denominator: every keep row, rows lacking question_results counted separately; the result feeds HIL-2 item 11 and changes no gate. ✅ 2026-10-21
  - 2026-10-21 (noninf-gates) result. `paired_keep_replay` in `src/autopilot_core/sequential_replay.py` (epyc-orchestrator `ea8c7338`). Frozen input: journal snapshot sha256 `6bb790ba837c9ea23f9e6ebd1a8ff00e354baf196ec7fe830d02dd54fc8c5b4a` (autopilot_journal.jsonl 18257825 B + autopilot_journal_1.jsonl 19801823 B; 1372 rows). Statistic: z = (gained - lost) / sqrt(gained + lost) over shared qids against the previous keep row of the same tier that has a vector; significant means z >= 1.96.
  - 229 keep rows: 146 without `question_results` (counted), 1 without a predecessor vector, 82 with a paired statistic; 81 of 82 are below 1.96 (false-elite share 0.9878). By action type: numeric_trial 46 of 47, seed_batch 34 of 34, structural_experiment 1 of 1. Predeclared stop rule (stop a tier after 3 consecutive non-significant keeps): tier 1 triggers at trial 803, after which the journal holds 487 later tier-1 trials, 79 of them keep rows. Unit caveat per the task text: one trial is one pass over about 37 questions, so the McNemar form is the available unit. Most keep rows are seeding or numeric trials, not mutations, so the false-elite share describes ships as recorded, not mutation quality. Feeds HIL-2 item 11; no gate change.
- **M1 (monitor, 2026-10-20) — DP-A pending: lifetime promotion error budget.** Trigger: The operator decides, or the SEQ-5 report shows K_opened above about 5 per quarter. First step when it fires: Re-open DP-A option (b) with the measured K_opened. No immediate step remains: The only useful step (the ledger) is SEQ-5; an amendment is human-only.
- **M3 (monitor, 2026-10-20) — DP-C pending: rolling-window alpha budget.** Trigger: The operator decides, or the SEQ-5 report shows fingerprint confirmations binding after the era and rate-axis faults are fixed. First step when it fires: Re-open DP-C option (b). No immediate step remains: The budget is not the binding gate today (2026-07-11 audit); reporting is SEQ-5.
- **M11 (monitor, 2026-10-20) — Alpha and certificate follow-ons (earn-back on promotion, online e-BH, e-GAI, decaying-memory online FDR, Biometrics rejoinder, Safe Harness).** Trigger: DP-C option (b) adopted, or the HIL gate design needs a generation-versus-certification argument. First step when it fires: Read the listed sources before choosing a scheme. No immediate step remains: e-LOND was declined; the successors are unread at the wave cap.


### Discovered quality-provenance defect — codex3, 2026-11-01

- [x] **SEQ-QUALITY-ERA-PROVENANCE — require original native evidence of the active quality-era fence for stored quality z and mismatched cached verdicts; never retrofit historical witnesses.** ✅ 2026-11-01 — APP implementation `59934bfa18913d5379984d9d61fb23129b42ea97`; [source-bound controls and original baseline failures](https://github.com/pestopoppa/epyc-orchestrator/blob/fb2036d93203eb4e5a87918ecf0572c29ba73fd3/artifacts/engineering/seq-quality-era-witness-20261101/README.md). [belief: cc]
  - Review of the rate fix exposed a separate quality path: a post-boundary timestamp did not prove that stored z used the quality-era comparator. The native writer now records the actual quality cutoff only after a finite quality statistic is computed. An active quality cutoff requires its matching typed witness; absent, mismatched or malformed historical values remain unqualified, while no-era behavior and the original raw baseline/alpha folds remain unchanged. Quality-only cache changes use the existing native upgrade without inventing a witness or resurrecting a failed verdict. The seven-file selection recorded 285 passes and two failures reproduced on the pre-change source bytes; after refreshing the nine unrelated peer paths, all 49 focused controls passed again against the refreshed checkout. The proof distinguishes both runs. The fixture index now reflects its HEAD and only protected DAR work remains dirty. No live journal, new cutoff, statistical rule, model call or gate activation. This is a newly discovered repair outside the standing WORK code queue and is not included in the two queue closures in this checkpoint. [belief: cc]

## Track: promptforge-mutation-safety-contract
<!-- gate: RTG-02 -->

> Folded from `handoffs/active/promptforge-mutation-safety-contract.md` @ `b1bf3f3f7ade` on 2026-11-02 (BRF-T1-F21, route 1a, operator D1/D5; retired row RTG-55 → EVL-04). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### PromptForge mutation safety contract (RTG-55)

**Status**: stub
**Created**: 2026-09-07 (research intake, operator-approved plan; successor of ../completed/meta-harness-optimization.md whose active pointer was retired 2026-08-23)
**Categories**: meta_harness, autopilot, safety
**Related**: [autopilot-continuous-optimization.md](autopilot-program.md) (RTG-02) · [eval-tower-verification.md](eval-tower-program.md) (EVL-14) · [agent-collab-rnd-harness.md](agent-collab-rnd-harness.md)

#### Objective

Constrain what a PromptForge mutation may DO — not merely which files it may touch — so that mutation
safety is a compile-time property of the harness rather than a promise made in prompt text. The
lineage's active pointer was retired 2026-08-23 and the completed ledger forbids new task checkboxes,
so this is a **new active stub, not a reopen**.

#### Research Context

| Entry | State | What it contributes |
|---|---|---|
| `intake-1323#record` | dive-verified | Harness-R1's typed return-effect contract, AST denylist, forbidden-text patterns, the ANTI-OVERRIDE prior, and the `examples/heldout_generalization/` corpus |
| `intake-1317#record` | dive-verified | Optimizer budget shape (constant in training-set size, large constant) |
| `intake-1320#record` | stage-1 / bearing | JIT admission-rule comparison context (the archive/admission half lives in AP-51) |

#### Tasks

- [x] **MHS-1 — Typed return-effect contract.** Constrain what a mutation may DO (a closed per-site
      effect enum, host-normalized and truncated), not only which FILES it may touch. Reference
      implementation: Harness-R1 `code_runner.py:31-34` + `_normalize_hook_result`, ~50 lines.
      *Highest value, cheapest.* `intake-1323#record` (dive actionable D0). Zero compute. ✅ 2026-09-14 — `MutationEffect`
      (`inert|constrain|expand|replace|unsafe|unknown`) with total `normalize()` (aliases in, unrecognised ⇒
      `UNKNOWN`, tokens truncated at 32 chars, reasons at 240); `CodeMutation.effect`/`.effect_reason`; both
      `apply_code_mutation*()` refuse `UNSAFE` and report `effect`. CONSTRAIN/REPLACE derived mechanically
      (answers Open Question 3 — no separate label needed). epyc-orchestrator `7d4b40a8`, tests
      `test_effect_enum_is_closed`, `test_effect_normalization`, `test_unrecognized_effects_normalize_to_unknown`,
      `test_classify_*`, `test_apply_rejects_unsafe_effect`, `test_apply_in_context_reports_effect`.
- [x] **MHS-2 — Close the MH-9 inertness hole.** The AutoMem `schema_evolution` `new_file` lane
      requires "default-inert" modules as **prompt text only** (`prompt_forge.py:1261-1277`) while
      `_validate_code_mutation`'s importlib step (`:1147`) executes the module top level
      **unsandboxed in the live repo**. Add an AST node denylist
      (`Import/ImportFrom/With/While/Lambda/ClassDef/Raise/Global/Delete/Yield/Await`) plus
      dunder/underscore `Name` + `Attribute` rejection over `new_file` proposals, modelled on
      `code_runner.py:64-103` and `:170-176`, so inertness is **compile-time, not a promise**. MH-9's
      own row already anticipated this ("keep edit-only allowlist until a stronger isolation story
      exists") — this IS that story. `intake-1323#record` (dive actionable D1). Zero compute. **Depends on MHS-1** (the effect
      enum is the denylist's contract). ✅ 2026-09-14 — the repo-write + in-process `importlib` step
      (`origin/main` `prompt_forge.py:1149`/`:1157`) is GONE; validation is static-only
      (`screen_static_safety`), with the ratified strict node denylist + underscore/dunder rejection for
      `new_file`, a capability denylist with original-file grandfathering, and the MH-9 prompt rewritten to
      the shape the screen admits (`MEMORY_SCHEMA_SHAPE_EXAMPLE` screened in CI, so prompt/denylist drift
      cannot recur). epyc-orchestrator `7d4b40a8` + `c27eec6c`; 100 tests incl.
      `test_validation_never_writes_the_target_file`, `test_validation_does_not_import_the_candidate_module`,
      `test_strict_profile_rejects_denylisted_nodes` (11 cases),
      `test_noop_mutation_of_every_allowlisted_file_passes`, `test_prompt_shape_example_passes_the_strict_screen`,
      `test_old_class_shaped_proposal_is_rejected_by_the_strict_screen`. Selection 40 → 140 passed.
- [x] **MHS-3 — Missing half of the transfer guard.** ✅ 2026-09-17 (landed with the AutoPilot merge train, orchestrator `a1a0251a` on main, which contains `6df6f0d8`; the notes below that say "not yet on main" predate the landing). `_UNIVERSAL_TRANSFER_RE`
      (`prompt_forge.py:83-88`) rejects OVER-generalization (`always|never|all tasks`); Harness-R1's
      `FORBIDDEN_TEXT_PATTERNS` (`harness_r1_patch.py:233-238`) rejects **UNDER**-generalization (a
      patch naming a specific eval task id / sample index / item id). We have **no** guard against a
      mutation memorising the eval set by naming its instances. Add an anti-leakage pattern set over
      accepted mutation text keyed to our suite/task identifiers. `intake-1323#record` (dive actionable D2). Zero compute.
      **Structural form (2026-09-15):** the refusal lives in _transfer_safety_verdict and returns
      valid=False when a mutation's added text — prompt mutations AND code_mutation mutated_content
      (string literals, comparisons) — shares a verbatim ≥8-token n-gram with, or an exact expected
      answer from, the current draw, sentinel_questions.yaml, tool_sentinels.yaml or the contrastive
      trace bank. Record the matched source id. It also refuses in-suite special-casing, which the
      current check allows (it refuses only suites absent from the source context).
      **Source-identity key:** it ALSO refuses a mutation whose few-shot or example content was
      derived from a trace of a question in the current draw. The key is the question id or sentinel
      id carried in the contrastive trace-bank records (actions.py trace context; eval_tower.py
      fixed 20-trial draw), not only a verbatim n-gram, because paraphrase bypasses n-gram matching.
      BAITBENCH entity-overlap and near-duplicate shortcuts had take-rates of 82.5% and 72.5%
      (intake-1395#record). One leakage checker serves prompt and code mutations. Instruction text
      ("don't overfit") is not the fix (intake-1379#record; intake-1395#record, where validity
      prompting moved -6.2 pp). EvilGenie partial-hardcoding class (intake-1387#record).
      ⏳ PARTIAL 2026-09-16 (`sub-autopilot-safety`, orchestrator `8219d8e8` on branch
      `sub/autopilot-safety-20260916`, NOT yet merged; box stays open: structural form completed on `sub/mhs3-complete-20260916`, see below): `EvalIdVocabulary` + `eval_leakage_reason()`
      in `prompt_forge.py`, applied to the ADDED text of prompt, code and GEPA mutations. The vocabulary
      comes from eval data, not a hand list: research `question_pool.jsonl` (required), `core_*.jsonl`
      and the sentinel YAMLs → 153,450 ids (pool ids, nested core qids, prompt-hash qids), 295 id
      families derived from them, and suite/id-stem anchored references, plus a qualified generic
      pattern (`sample #12`, `task_id == 17`). **Fail-closed**: a missing or unreadable pool rejects
      every mutation (`eval_leakage_vocabulary_unavailable`). Measured false positives: 0 over all 33
      current prompt + allowlisted code targets (a regression test pins this), and 1 file of 444
      docs/src files, where both hits were real instance references. Open Question 2: keyed on ids plus
      prompt-hash qids (content hashes of text); image-bound qids are not included.
      `tests/unit/test_prompt_forge_leakage_and_risk.py` (73 tests).
      Operability (loud fail-closed state: startup preflight, alarm after 3 consecutive
      `eval_leakage_vocabulary_unavailable` rejections, runbook `docs/guides/meta-harness-operator-guide.md` § 7)
      built on branch `sub/gate-frontier-20260916`, under review, unmerged (2026-09-16, `sub-gate-frontier`).
      **Structural form built 2026-09-16 (`sub-mhs3b`, orchestrator `6df6f0d8` on branch
      `sub/mhs3-complete-20260916`, built on `sub/gate-frontier-20260916`; carried by the AutoPilot merge train
      `sub/autopilot-train-20260916`, not yet on main; flip the box when it lands):** `_transfer_safety_verdict`
      and the GEPA path now also refuse, over the ADDED text: `eval_content_ngram_overlap` (verbatim >=8-token
      overlap with the pool/cores/sentinels or the rendered trace bank; hashed shingles packed with row id,
      ~1.3e-7 FP per shingle, template df >=32 dropped, anchor-or-15-token-run rule),
      `eval_expected_answer_leakage` (name-shaped 1-7 token answers), `eval_source_identity_leakage` (trace
      blocks resolved to question/sentinel ids; >=3 shared rare tokens, paraphrase-proof) and
      `eval_suite_special_casing` (keyed/phrase/mention, in-suite included). Matched source id in every reason.
      Same pass, cache and fail-closed state as the id vocabulary; harness text (prompts, src/, original) is never
      blamed. Real pool: 16 s cold, +590 MB RSS (index 173 MB, 1.37 GB transient peak), ~9 ms per edit. FP: 0/33
      live targets; content 0/91 historical mutations (special-casing 2/91 borderline); 2.4% of 467 whole
      src/docs files. Coverage 1998/2000 verbatim pool prompts. Runbook § 7 extended.
      `tests/unit/test_prompt_forge_content_leakage.py` (51 tests). Detail:
      `progress/2026-09/2026-09-16-sub-mhs3b.md`.
  - [x] **MHS-3a — remove the pool leak MHS-3 found in live harness text** ✅ 2026-09-16 (orchestrator
        `09bdb998` on main). Pool row `simpleqa_general_00912` (Aschoff / Bonn) was a worked example in
        `orchestration/prompts/rules.md` Example 4b and `DEFAULT_ROOT_LM_RULES`; both now use a synthetic
        example, and a dormant HumanEval/55 copy in `src/prompts/coder_system.txt` was replaced too. Takes
        effect at the next API reload (owned by the session that owns inference).
        Detail: `progress/2026-09/2026-09-16-sub-leak00912.md`.
  - [x] **MHS-3b — close the rewind hole: operator RATIFY of the checkpoint prompt re-pin.** ✅ 2026-09-17 RATIFIED by the operator (root `b8379d42`): all 10 checkpoint copies re-pinned to `18f8ea01`, originals in `/mnt/raid0/llm/backups/ckpt-leak-20260916/`. Operator chose
        option A (2026-09-16). Ten AutoPilot checkpoints, including production_best (multitier_v10), still
        carry the leaked `rules.md` (`b250c227…`), and `restore_checkpoint()` copies it back. Script landed on
        root main (`0e2bbc33`); the operator runs
        `bash -c 'bash <(git -C /mnt/raid0/llm/epyc-root show origin/main:scripts/operator/run_ckpt_leak_ratify_20260916.sh) --operator pestopoppa'`
        and types RATIFY (refuses while AutoPilot holds its lock). Detail: `progress/2026-09/2026-09-16-sub-ckpt-leak.md`.
  - [x] **MHS-3c — clean the out-of-scope leak copies** ✅ 2026-09-17 (all three scopes purged; `--verify` PASS on each) that MHS-3b leaves: 4 HumanEval/55 task memories in
        `episodic.db` (in every checkpoint and the live store) and Aschoff in `autopilot_state*.bak*`
        `last_traces`. Purge tool: orchestrator `41baad2b` (`scripts/maintenance/purge_eval_leak_memories_20260917.sh`),
        backups and receipt in `/mnt/raid0/llm/backups/episodic-leak-20260917/`.
    - [x] Offline stores and state backups purged ✅ 2026-09-17: 11 checkpoint/backup `episodic.db` copies
          (4 rows + FAISS entries each, health OK) and 15 state backups redacted. `--verify` PASS. The first run
          was cut off by a caller timeout at item 19 with no damage (the original was intact); the re-run finished.
    - [x] Live store purged ✅ 2026-09-17 during the API stop window (API down, verified): 4 memories removed,
          health OK, `--verify --include-live` PASS. The reloaded API reported 64,204 entries (was 64,208).
    - [x] Pinned production_best (multitier_v10) store ✅ 2026-09-17: purged with operator approval, 4 rows + FAISS, health OK, verify PASS incl. live+pinned.
          The new hashes are in `pinned_repin_proposal.json`. The v10 pins still name the pre-purge
          bytes until MHS-3d is ratified.
  - [x] **MHS-3d — operator RATIFY of the v10 episodic re-pin** (`RATIFY-V10-EPISODIC-REPIN-20260917`). From a host terminal: ✅ 2026-10-29 (audit: ratified: artifacts/operator/ratify_v10_episodic_repin_20260917.json + .receipt.json (emitted 2026-09-17), commit 810a6a829 'RATIFIED: v10 production checkpoint re-pinned after the HumanEval/55 eval-leak memory purge') [no-belief: audit-reconciliation]
        `docker exec -it -u node epyc-root bash -c 'bash <(git -C /mnt/raid0/llm/epyc-root show origin/main:scripts/operator/run_v10_episodic_repin_ratify_20260917.sh) --operator pestopoppa'`
        and type RATIFY. It re-pins `checkpoint_meta.json` (the three episodic file hashes and
        memory_count 63925 -> 63921; checkpoint_sha256 `a604276f` -> `3b457d98`) and the v10 receipt
        mirror, adds the amendments entries, and refuses while AutoPilot holds its lock. The dry-run
        preflight is clean against the real checkpoint. Its `--verify` supersedes the MHS-3b script's
        `--verify`, which the purge broke. Detail: `progress/2026-09/2026-09-17-sub-v10-repin.md`.
- [x] **MHS-4 — ANTI-OVERRIDE risk prior.** ✅ 2026-09-17 (landed with the AutoPilot merge train: orchestrator `8219d8e8` and `4f28e6c3` are on main via `a1a0251a`; the "pending merge" and "NOT YET ON MAIN" notes below predate that). Rank/gate mutations by CONSTRAIN (add a check, block a bad
      path, re-prompt) vs REPLACE (rewrite/force an action, hard-code an answer). In the released
      corpus the REPLACE-before-CONSTRAIN ordering holds on all 23 valid patches (REPLACE 4/4 negative,
      mean −8.4 pp; CONSTRAIN n=19, mean +3.9 pp), but the worst single patch is CONSTRAIN (−16.9 pp,
      hint-only), so the prior ranks risk and does not certify safety (MHS-5, orchestrator `4f28e6c3`);
      the trained editor converged constrain-only across all 9 patches and all 3 seeds. Encode as a
      mutation-type risk weight. `intake-1323#record` (dive actionable D4; the 2026-09-07 wording
      "every catastrophic regression came from an override" was refuted by MHS-5).
      Orchestrator `4f28e6c3` is on branch `sub/autopilot-safety-20260916`, pending merge. Zero compute. Consumer: AP-52 in
      [autopilot-continuous-optimization.md](autopilot-program.md).
      **IMPLEMENTED 2026-09-16, NOT YET ON MAIN — flip on merge** (`sub-autopilot-safety`, orchestrator `8219d8e8`, branch `sub/autopilot-safety-20260916`, unmerged): `MUTATION_EFFECT_RISK`
      (inert 0.05 < constrain 0.25 < expand 0.50 < replace 0.90 < unknown 1.0 < unsafe ∞), carried as
      `effect_risk` on both `CodeMutation` and `PromptMutation`. Prompt text is now classified too
      (`classify_prompt_effect`). `rank_mutations_by_risk()` orders candidates safest-first. The gate
      `AUTOPILOT_MUTATION_RISK_GATE` (default 1.0 refuses only unclassified effects; 0.9 means
      constrain/expand-only; it can only be tightened) runs at propose time and again at both code
      apply paths, and the proposer prompt now carries the anti-override rule. **Weights are an ordinal
      prior, uncalibrated**. MHS-5 below supports the ordering but shows CONSTRAIN is not
      regression-free. Same test file.
- [x] **MHS-5 — Mine `examples/heldout_generalization/` as a labelled contrastive corpus.** ✅ 2026-09-17 (orchestrator `4f28e6c3` on main via the train merge `a1a0251a`; the "unmerged" notes below predate that). 23
      patches, 3 editors, identical 10-failure evidence, 3 seeds, per-patch sha256, hook sets,
      validation errors, rescued/regressed counts over 1,270 held-out tasks; Apache-2.0.
      Discriminating features already extracted by the dive: effect kind, hook-set stability,
      benchmark-scaled length, rescue:regression ratio. MH-7's contrastive-trace capture is the
      existing consumer. Feeds MHS-4. `intake-1323#record` (dive actionable D7). Zero compute.
      **IMPLEMENTED 2026-09-16, NOT YET ON MAIN — flip on merge** (`sub-autopilot-safety`, orchestrator `4f28e6c3`, branch `sub/autopilot-safety-20260916`, unmerged): sparse-fetched
      Harness-R1 @ `411bb548` (the dive-verified revision). `scripts/autopilot/species/heldout_effect_corpus.py`
      derives `orchestration/datasets/harness_r1_heldout_effect_corpus.json` with labels only, no patch
      code: 27 cells, sha256-verified, effect kinds read by AST and mapped onto `MutationEffect`, plus
      hooks, code length, delta, and rescued/regressed counts. **Result (23 valid patches):** the MHS-4
      ORDERING holds. All 4 REPLACE patches regressed (mean −8.4 pp, rescue:regression 0.21); the 19
      CONSTRAIN patches averaged +3.9 pp (1.65). **But the claim "every catastrophic held-out
      regression came from an override patch" does NOT hold on this corpus.** The single worst valid
      patch (DeepSeek-V4-Pro alfworld seed 20260721, −83 on 490 = −16.9 pp, 130 regressed) is
      hint-only (`inject_hint`). A block-only patch also lost 34 (−6.9 pp). 4 of 19 CONSTRAIN patches
      regressed. Confound: 9 of the 19 CONSTRAIN patches come from the trained Harness-R1 editor.
      Consequence: the MHS-4 weights stay ordinal; the gate ranks risk, it does not certify safety
      (code comment and operator guide updated). **Belief-kernel note — APPLIED 2026-09-16 (`sub-own`):** the refuted text was
      the MHS-4 row's own rationale, not key claim 04 of the entry (the handoff's `#NN` numbers indexed
      the dive actionables ledger, so `#04` was a mis-anchor; claim 04 is the true transductive-scope
      claim). Recorded in `research/intake_index.yaml` (`intake-1323#record`) as `dive_corrections` item (13) and
      a `dive_entry_corrections` row (effect `narrowed` on dive item (6)); claim 04's `claim_corrections`
      note re-examined, still `unaffected`. Evidence cited as orchestrator `4f28e6c3` on
      `sub/autopilot-safety-20260916` (pending merge), corpus sha256 `09ae7365…efbc71`. The MHS-4 row now
      cites `intake-1323#record` with the qualified wording. `tests/unit/test_heldout_effect_corpus.py` (15 tests) pins
      both the ordering and the refutation. MH-7 wiring was not done (out of scope for this row).
- [ ] **MHS-6 (record, no work) — Optimizer budget shape.** Record it as **"constant in training-set
      size, LARGE constant"**: 1 + T_ReAct calls/iteration, T_ReAct 10–20 at B = N_train ⇒ 11–21
      metered calls, vs EvoSkill 2N/B and SkillOpt K_opt·N/B (K_opt 6–8). At our split sizes this is
      **more** absolute calls. The completed file's pointer to
      `handoffs/active/meta-harness-optimization.md` is DANGLING — that file does not exist — which is
      why this stub, not a reopen, is the right shape. `intake-1317#03`. Zero compute.
- [x] **MHS-7 — force the isolated mutation path.** `apply_code_mutation` writes the live tree directly ✅ 2026-10-31 — implementation APP `c91884ee5a38f7b4a2168c76fee1394a867e2e33`; `tests/unit/test_worktree_manager.py` and action controls; Git-retained proof `artifacts/audit/mhs7-isolated-mutation-20261031/` in APP main `a3c00d206a75044a2c01d67498f7bb633084eb0c` (433 focused tests, 162 correction controls). Existing transaction overlays main for evaluation; ordinary rejection/exception restores the preimage. [no-belief: deterministic mutation/commit safety controls; no measurement]
      (git-checkpointed) and the isolated `apply_code_mutation_in_context` exists but nothing requires its use
      (`scripts/autopilot/species/prompt_forge.py:~1440`) (found 2026-09-14, noninf sweep).
- [ ] **MHS-8 — tighten the apply gate to "only screened effects apply"**, since only `MutationEffect.UNSAFE`
      is refused today so `UNKNOWN` — the default on a hand-constructed `CodeMutation` — still applies; needs
      an audit of every construction site (`scripts/autopilot/species/prompt_forge.py`, apply gate)
      (found 2026-09-14, noninf sweep).
- [x] **MHS-9 — narrow `revert_code_mutation`'s new-file revert from `git add -A <path>` to an explicit ✅ 2026-10-29 (audit: orch 25c8e913 (2026-09-16, 'no commit sweep'): revert_code_mutation new-file path now calls _git_commit_paths([abs_path]) = git add -A -- <explicit pathspec> + commit --only (prompt_forge.py:1152,1466)) [no-belief: audit-reconciliation]
      pathspec**, the idiom the project's hygiene rules warn about
      (`scripts/autopilot/species/prompt_forge.py:~1478`) (found 2026-09-14, noninf sweep).
- [x] ✅ 2026-10-31 **MHS-10 — land a standalone formatting commit for `prompt_forge.py`**. Evidence: orch `86f9985e97f010c3a9702b5f923a6d793159ef3c`; `/mnt/raid0/llm/tmp/refactor-01a16fc3/mhs10-format-20261031/QUALIFY-R3.log` and `PROMOTION.json` in that directory. [no-belief: formatting-only change; identical type-comment AST, Ruff checks and 260 existing tests pass]
      Resolved the prior formatting dirt on
      `origin/main` (`ruff format --check` fails on a pristine clone), so future diffs stay readable
      (`scripts/autopilot/species/prompt_forge.py`) (found 2026-09-14, noninf sweep).
- [x] ✅ 2026-11-01 **MHS-11 — replace the operator guide's `prompt_forge.py` line-number citations with symbol names**,
      since `line 575` / `line 594` / `line 509` are already stale by hundreds of lines
      (`docs/guides/meta-harness-operator-guide.md`) (found 2026-09-14, noninf sweep). APP implementation `25d4bc71351437b45d400c36e986b502d94c3c5c`; artifact `artifacts/engineering/mhs11-promptforge-guide-20261101/VALIDATION.txt`; [no-belief: documentation-only]
- [x] **MHS-12 — eval-identity screen for code_mutation.** Refuse (MutationEffect.UNSAFE with reason) any mutation whose ADDED code reads workload_class, scoring_method, batch_id, request-metadata suite/tier keys or the literal "eval_batch", or removes/overrides force_role handling, in any allowlisted file. Grandfather existing references the way MHS-2 grandfathers imports. Fixtures: a chat.py mutation branching on workload_class == "eval_batch" is refused; a no-op chat.py mutation passes. Partly answers Open Question 2 (key on eval-identity fields, not only suite/task names). intake-1387#record. ✅ 2026-10-31 — APP implements `f579bcf92f2b11904176f662f6f6d06ed96947fe`; test `tests/unit/test_prompt_forge_eval_identity.py`; Git proof `artifacts/audit/mhs12-eval-identity-20261031/verification.md`. [no-belief: source implementation and native regression controls]
      ✅ 2026-10-31 — Implemented in epyc-orchestrator `f579bcf92f2b11904176f662f6f6d06ed96947fe`
      (`src/autopilot_core/mutation_guards.py`, `scripts/autopilot/species/prompt_forge.py`). Static AST
      delta screening flags added eval-identity reads and force-role removal/override while
      grandfathering existing references by expression, context and multiplicity; comments, docs and
      write-only matches are excluded. Scope-local forced-role handling covers early exits, false
      wrappers, selected receivers, setattr/delattr and grandfathered guarded calls. Native PromptForge
      screening emits `MutationEffect.UNSAFE` with reason before generic shrink/missing-name REPLACE handling;
      prior precedence for other cases is preserved and the screen is cached once. Native propose,
      action and apply paths reject before evaluation or writes. The final suite has 163 controls,
      including 57 new, with zero touched-file lint findings. The earlier broad run (272 passed, one
      documented baseline failure) was tied to the pre-delta hash and is not the final full-suite claim.
      `make` gates used fixture context and are not a full-repository failure. Evidence:
      `artifacts/audit/mhs12-eval-identity-20261031/verification.md`. Scope limits: no dynamic-alias or
      whole-program security proof; conservative benign changes may be refused. No live activation,
      threshold change or grade is claimed. [no-belief: source implementation and native regression controls]
- [x] **MHS-13 — Scoped-propose plus KEEP_BASE composer for PromptForge: design addendum (spec only; no run; HIL P0.4 ordering applies).** Two scoped candidates per mutation (a process lens and a domain lens, each told not to touch the other's dimension) and a composer that may merge, revise, adopt one or return KEEP_BASE, writing decision lines 'kept/revised/dropped -> edit -> evidence(count)' in which every kept edit names the trajectory moment that motivated it; an invalid proposal is retried once and then the stage inherits the parent. Include a structural pre-flight validator row (valid candidate or inherit; trigger line present; no template braces; referenced scripts exist) and compare each rule with the existing guards first (`mutation_extraction_failed`, `_UNIVERSAL_TRANSFER_RE`, `_prompt_integrity_reason`, MHS-2, MHS-3, MHS-4), dropping what they already cover. State which AP-54 and AP-55 helpers each stage reuses. Adoption is decided only by the PromptForge promotion gate and P-AB-1, never by the contrast between candidates; agreement among candidates is support, not independent proof (`intake-1995#01`, `intake-2148#00`, `intake-2148#06`); the published ablation is a single configuration (`intake-1995#record`). ✅ 2026-10-20
- [x] **MHS-14 — Mutation-record falsifiability fields and activation beacon for PromptForge (spec only; no run).** One optional annotation on the `PromptMutation` record (`scripts/autopilot/species/prompt_forge.py:296-310 @5d4ad2c0`): the trigger condition under which the edit fires; predicted fixed tasks and predicted at-risk tasks; an attribution signature (the trace feature that must appear if the edit fired); a no-trigger control slice on which output must be byte-identical or within a declared noise floor; `evidence_used` and `verification_checks` (how to confirm next iteration); and a deterministic activation beacon with a per-task fire count, where zero fires means uncredited, not harmless; the no-trigger control slice is what bounds a presence effect and it is required for any edit that stays resident in the prompt (`intake-1321#record`). Log observed versus predicted in the journal row of an accepted mutation (AP-53 holds rejected mutations only, `rejected_mutation_ledger.py:91-131`) and in the AP-53 record of a rejected one; the default-off `mutation_author_capture` hashes are the existing hash-level `evidence_used`. Compared first with MHS-3 (leakage in added text), MHS-4 (edit-class risk prior) and AP-55 (regime comparability): none records a predicted effect, a trigger, a locality control or fire counts. Protocol-bearing wording is a MEASUREMENT.md section 5 candidate, not applied (`intake-2145#04`, `intake-2165#00`, `intake-2166#00`, `intake-2146#05`, `intake-2176#03`). ✅ 2026-10-20
- [x] **MHS-15 — Warn-only, delta-only prompt interference lint for PromptForge mutations (pure function; never a reject).** Add `prompt_interference_lint(original, mutated)` in `prompt_forge.py` next to `_prompt_integrity_reason` (`:907 @5d4ad2c0`; the HIL-3 import-safe guard module does not exist yet, so the later extraction moves it with its siblings), reporting findings present in the mutated text and absent in the original: (a) verbatim duplicate lines or blocks, (b) MUST or ALWAYS versus NEVER or DO NOT sharing a scope noun, (c) conflicting priority markers, (d) the count of in-context examples the mutation adds (a deterministic bloat check; an LLM leakage judge is not adopted, an LLM judge is not a measurement). Findings go to `PromptMutation.safety_warnings` (`:306`; nothing reads that field today) and must also be surfaced in the journal `eval_details` or the AP-53 record, otherwise the lint is write-only. Acceptance: original equal to mutated yields zero findings on every file in `orchestration/prompts`; a fixture appending 'NEVER use X' beside an existing 'ALWAYS use X' is flagged; a fixture adding six examples is flagged. Then run the lint once in whole-file read-only mode over `orchestration/prompts` and record per-rule counts as the calibration baseline (13 of the 21 headline findings in the source were minor scope overlaps, so the false-positive rate must be known before the lint is trusted), filing any genuine contradiction as a prompt fix (`intake-2155#00`, `intake-2155#04`). How our served models resolve ALWAYS-versus-NEVER is unknown and is a monitor (M8), not part of this task. ✅ 2026-10-21
  - 2026-10-21 (noninf-gates) result. `prompt_interference_lint(original, mutated)` added beside `_prompt_integrity_reason` in `scripts/autopilot/species/prompt_forge.py` (epyc-orchestrator `29d66c27`, on origin/main). Rules: `duplicate`, `directive_conflict` (MUST/ALWAYS vs NEVER/DO NOT sharing a content word), `priority_conflict`, `examples_added` (threshold 3). Warn-only; appended to `PromptMutation.safety_warnings` after the verdict so it cannot change validity. Surfaced in AP-53 records (`interference_warnings`, additive) and in journal `eval_details.prompt_interference_warnings` via a new ctx.state key. GEPA proposals do not run `_attach_transfer_safety`, so they are not linted (open gap).
  - 2026-10-21 (noninf-gates) GEPA gap closed (epyc-orchestrator `ea820af8`): `_propose_via_gepa` now runs the same warn-only lint on valid proposals and the GEPA handler stashes the findings for `eval_details`; test `test_gepa_proposal_gets_the_warn_only_lint`; 272 prompt-forge tests and 163 actions tests pass.
  - Acceptance: `tests/unit/test_mhs15_prompt_interference_lint.py` (7 pass): original==mutated gives zero findings on every `orchestration/prompts/**/*.md` file; the NEVER-beside-ALWAYS fixture and the six-example fixture are flagged; pre-existing conflicts are not re-reported. 50 related unit tests pass.
  - Calibration (`scripts/autopilot/prompt_interference_calibration.py`, whole-file read-only, each file vs an empty original, 26 files): duplicate 2, directive_conflict 1, examples_added 1. Samples: duplicates are a template line in deep_search_agent.md and a code line in rules.md; the one directive_conflict (report_agent.md, shared word `report`) is a scope overlap, not a contradiction; examples_added is rules.md (13 example headings, legitimately example-heavy). No genuine contradiction found, so no prompt fix filed. Rule (b) matches on a single shared word, which is the false-positive source the task text warned about.
- [x] **MHS-16 — Cumulative-drift report over accepted ships (read-only; no gate change).** Verified 2026-10-20: `safety_gate.py` judges each ship against its predecessor (the tier baseline is overwritten at every promotion by `update_tier`, `scripts/autopilot/safety_gate.py:1533-1576 @5d4ad2c0`), checks only the aggregate (-5 percent) and per-suite deltas, and has no per-question passed-to-failed flip count and no same-bucket edit-concentration check. Build a report that replays journal rows with `keep_revert_decision == "keep"` (per-question vector in `eval_details.question_results`) together with the `baseline_promotion` events (`src/autopilot_core/baseline_ledger.py`) and reports, against the era's SEED baseline profile rather than the predecessor: per-question passed-to-failed flips, the cumulative per-suite delta, and the length of runs of consecutive promotions sharing one (mutation_type, target) bucket; add a warn-only same-bucket concentration flag. AP-53 holds rejected mutations only, so it may be annotated for rejects only. Changing what counts as a ship is human-amendment territory and out of scope (`intake-2166#02`, `intake-2166#03`, `intake-2164#00`). Frozen input: the journal snapshot digest; denominator: every keep row, rows lacking question_results counted separately and not dropped; decision rule: report only. ✅ 2026-10-21
  - 2026-10-21 (noninf-gates) result. `cumulative_drift_report` in `src/autopilot_core/sequential_replay.py`, run by `scripts/autopilot/gate_replay_reports.py` (epyc-orchestrator `ea8c7338`). Frozen input: journal snapshot sha256 `6bb790ba837c9ea23f9e6ebd1a8ff00e354baf196ec7fe830d02dd54fc8c5b4a` (autopilot_journal.jsonl 18257825 B + autopilot_journal_1.jsonl 19801823 B; 1372 rows). 229 keep rows; 146 have no `question_results` (counted, not dropped). Seed = first 3 vector-bearing keep rows per tier (no per-question seed profile is journaled; stated in the report).
  - Tier 1 (105 keep rows, 22 without vectors): seed trials 790, 791, 802; 80 rows compared; 63 rows with at least one passed-to-failed flip against the seed; max 2 flips in one row; 2 distinct questions ever flipped; longest same-bucket run 19, 15 runs of length 3 or more (warn flag set). Tier 0: 123 keep rows, none with vectors, longest run 36. Tier 2: 1 keep row. The journal ends 2026-08-09, before the quality-era boundary (1786378983.88 = 2026-08-10), so there is one era. Bucket here is (action_type, file/target) and most keep rows are `seed_batch`/`numeric_trial`, not mutations; only 5 are `prompt_mutation`. Per-suite cumulative deltas are in the report JSON. Report only; no gate change.
- [x] **MHS-17 — Predicted-effect calibration readout and the zero-fires wording fix (extends MHS-14).** (a) Read-only scoring function over journal and AP-53 predicted-versus-observed rows: deterministic per-mutation verdict by set intersection of predicted_fixed and predicted_at_risk with the observed fail-to-pass and pass-to-fail sets (no LLM); per-round precision and recall for fixes and for regressions, each beside a random-prediction baseline computed from panel size and observed flip rate; an explicit `unattributed regressions` list (intake-1132#record: at-risk prediction was near random, so it cannot be the regression screen). (b) Amend the MHS-14 sentence to read: zero fires means uncredited, not harmless; the no-trigger control slice is what bounds a presence effect and it is required for any edit that stays resident in the prompt (intake-1321#record). Acceptance: the scorer has fixture tests on a synthetic ledger and the MHS-14 sentence is replaced. Estimate: 1.5 days. ✅ 2026-10-21
  - 2026-10-21 (dpf-gates) result. (a) `scripts/autopilot/predicted_effect_calibration.py` (epyc-orchestrator `44d63a0b`): per-mutation verdict by set intersection of predicted_fixed and predicted_at_risk against observed fail-to-pass and pass-to-fail; per-round precision and recall for fixes and regressions beside a random baseline (k*F/n expected hits from panel size and observed flip count); explicit `unattributed regressions` list; unannotated rows counted not dropped. Fixture tests on a synthetic ledger: `tests/unit/test_mhs17_predicted_effect_calibration.py` (7 pass). No real readout exists: MHS-14 fields are not yet journaled. (b) The MHS-14 sentence is replaced (MHS-14 now reads: zero fires means uncredited, not harmless; the no-trigger control slice is required for any resident edit).

*Declined 2026-09-14: repoint the dangling pointer at `handoffs/completed/meta-harness-optimization.md:3` —
not filed because it is already recorded as the **Housekeeping rider (E0, owned elsewhere)** in this file's
Notes and named inside the open **MHS-6** box.*

**Cost yardstick (DERIVED-FROM-CONFIG, never a measurement)**: *"one engineer update ≈ one full sweep
of your eval suite"* — a reusable rule of thumb for pricing ANY outcome-grounded editor loop. It kills
this class of proposal on this host before anyone builds a design doc. `intake-1323#record` (dive actionable D9; handoff half;
the wiki half is queued for the compilation sweep).

#### Open Questions

1. Does the effect enum (MHS-1) need a per-mutation-site vocabulary, or is one closed host-wide enum
   sufficient for PromptForge's mutation sites as they exist today?
2. Does the anti-leakage pattern set (MHS-3) key on suite/task identifiers only, or also on fixture
   content hashes — and does the latter create its own maintenance surface?
3. Is the CONSTRAIN/REPLACE classification (MHS-4) derivable mechanically from the MHS-1 effect enum,
   or does it need a separate label?

#### Notes

- All six rows are **zero compute**. Nothing here requires inference, a model load, or an eval run.
- Dependency order: **MHS-1 → MHS-2**; **MHS-5 → MHS-4**.
- Index: this stub needs a new row in `routing-and-optimization-index.md` at the next free ID
  **RTG-55** — verify against `handoffs/archived/routing-and-optimization-index-history-*` before
  assigning, since retired IDs are never reused. **Row is PREPARED here; the owning session APPLIES.**
- Housekeeping rider (E0, owned elsewhere): the dangling pointer at
  `handoffs/completed/meta-harness-optimization.md:3` should be repointed at this stub or the clause
  deleted.

The [five execution-alignment triage labels](../../docs/reference/agent-run-failure-triage.md) provide descriptive failure-trajectory vocabulary for MHS-5 consumers. They are metadata, not held-out outcome grades or patch-safety predictions.

#### Research Intake Update — 2026-10-20 (harness cluster)

Operator-approved 2026-10-20 via research intake (plan sha256 1dc83054706ca0bae002602307b0d9ba6435b010be4d6ffd8a495a04605f3967). Monitor and knowledge records below are prose: no checkbox, no index next action.

- **M8 (monitor, 2026-10-20) — PromptForge guard follow-ons (additive-selection retest, LLM neutral reader, ALWAYS/NEVER severity probe, CONSTRAIN risk weight, gene-bank archive, cross-framework skills, unresolved-gaps list, saturated-suite skip, parent-in-pool selection, back-translation, proposer-spend review, red-team of our proposer).** Trigger: The named condition in each bullet (for example: the lint fires on a promoted CONSTRAIN mutation; MHS-7, MHS-8 and MHS-12 closed plus an idle window; AutoPilot runs several live configurations in one window). First step when it fires: Do the named step. No immediate step remains: Each is gated on an event that has not happened; MHS-15 covers the part that needs no event.
- **K4 (knowledge, 2026-10-20) — Gate-design confirmations and checks already done (guards fail closed; PACE subsumed by seq-v1; Two-Gate vacuous at our n; MHS-3 covers the literal-leak guard; REPL-EMB-2.1/2.2 already hold the lexical baseline; AU3 similarity floor exists; AP-54 scope; EGL not implemented; parallel_dispatch compared).** Retained use: Prevents re-filing the same checks.
