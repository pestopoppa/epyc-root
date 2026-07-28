# Autopilot Sequential Verdicts — the allocation rule, not the effect, was the binding constraint

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

- [ ] **SEQ-A — the `refuted` label is STICKY.** `state_name()`
      (`sequential_verdict.py:131-138`) is a pure function of current state, so a candidate that
      outgrows the kill condition should read `accumulating` again. It does not: **56 of 393 trials
      carry `state="refuted"` while `E >= budget_min_e` and `k >= budget`** — the persisted label
      contradicts what the policy's own function returns for that very trial. `70902e4b665474e7`
      crosses E=2.0 at k=10 and stays labelled refuted to k=40 at E=11.55. Decide: recompute the
      label per trial, or make stickiness explicit and documented.
- [ ] **SEQ-B — the baseline-promotion gate is unreachable.** Max `baseline_promotion_combined_E`
      ever observed is **1.0795** against `required_E = 100.0`, and `combined_E == E_rate_noninf`
      exactly in **307 of 391** trials — the rate e-process dominates and is effectively frozen. No
      candidate can be promoted through this gate regardless of quality evidence. Fix before any new
      campaign, or the compute burns into a gate that cannot open.

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

  - [ ] SEQ-3a — **Bridge (cheap, needs an operator ruling).** If an operator judges the E8
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
- [ ] SEQ-A — Sticky `refuted` label (above).
- [ ] SEQ-B — Frozen baseline-promotion gate (above).
- [ ] SEQ-4 — Re-examine the 9 candidates whose refutation does not survive the relaxed budget.
      They were removed from consideration by an allocation heuristic, not by evidence.

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
