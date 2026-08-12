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

- [ ] SEQ-B2 — Capture the refutation counterfactual AT STOP TIME: record which axis refuted and the margin on the other. | `safety_gate.py:1528` write-side + `readjudicate_sequential_candidates.py:203` report-side (mainB authorized 2026-08-11 to split quality-refuted / rate-refuted / joint — that fix is the first half) | Deps: none; per CLAUDE.md belief-kernel rule, wire the write side now — a future objective change must at minimum be able to IDENTIFY which stopped candidates deserve re-running, even though their trials must be regenerated.

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
