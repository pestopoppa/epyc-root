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
  - [x] **SEQ-A0 — the mechanism, built NEUTRAL so SEQ-A1 is a one-line switch** ✅ 2026-08-11
        (`mainB`, orchestrator `43108014`). `SequentialPolicy.sticky_refuted`, **default `False`** —
        seq-v1 semantics reproduced byte-for-byte, the 3 candidates below still flip exactly as
        before, 75 passed across every sequential-verdict consumer. Plus `EProcessState
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
        true: the FUNCTION is non-sticky (`state_name()` has no memory), the PERSISTED LABEL is
        sticky (never recomputed). So "make it sticky" is not a bug fix — it is SEQ-A1 horn 2, and
        deciding it silently would settle a human-amendment-only question on a phrasing.
  - [ ] SEQ-A1 — **OPERATOR DECISION**: recompute the verdict label per trial from `state_name()`
        (restoring the policy's own pure-function semantics), or keep stickiness and document it as
        "a stop decision is final". Either is defensible — a stopped e-process arguably *should*
        stay stopped — but the current state is neither: the label is sticky while allocation is
        not, so candidates keep burning trials whose evidence is then discarded. This changes which
        candidates are promotable, so it is **human-amendment-only** per MEASUREMENT.md.
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

- [ ] **Rate-axis comparator has no era fence of its own.** The incumbent pool is the 120 most recent
      same-tier trials; `quality_exclude_before_ts` is scoped `eval_quality` only. Post-fix median
      measured lift is **+4%, inside the 5% margin**, so "candidates really are faster" cannot be
      distinguished from "the comparator lags a host that got faster". Main residual anti-conservative
      risk.

- [ ] SEQ-A — Sticky `refuted` label (above).
- [ ] SEQ-B — Frozen baseline-promotion gate (above).
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
