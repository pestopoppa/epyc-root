# A stopping rule destroys its own evidence — capture the counterfactual at stop time

**Category**: `benchmark_methodology`
**Confidence**: verified (local code + unit tests, zero inference)
**Date**: 2026-09-14
**Source**: EVL-04 SEQ-B2, `epyc-orchestrator` `4c220b11`; handoff
`handoffs/active/autopilot-sequential-allocation.md` (finding F2)
**Folds into**: [Benchmark Methodology](../benchmark-methodology.md) — as the *stopping-decision*
case of the belief-kernel write-side rule in `CLAUDE.md`, alongside
[`computed-guard-never-consulted.md`](computed-guard-never-consulted.md)

## The mechanism

The AutoPilot sequential gate does not merely score candidates; it decides which ones keep
GENERATING data. `safety_gate.py::_sequential_verdict` stamps `state="refuted"` when EITHER
evidence axis refutes (quality, or rate-non-inferiority), and a refuted candidate stops
accumulating trials.

That makes it categorically different from a scoring rule. **A future objective can rescore every
trial that exists; it can never recover a trial that was never run.** So a stopping rule is a
data-generating decision wearing the costume of a scoring decision, and it is the one thing a later
metric change cannot undo.

The journal recorded only the JOINT `state`. WHICH axis refuted, and the surviving margin on the
OTHER axis at the moment of the stop, existed only post hoc, in
`scripts/analysis/readjudicate_sequential_candidates.py`. That reconstruction works only where the
row happens to carry both wealths, and only under today's policy constants — and it cannot answer
the question the record is for: *which stopped candidates would a changed objective want re-run?*

## The rule

**When a decision destroys its own inputs, its rationale must be written at decision time or never.**
The general belief-kernel rule ("the write side is cheap and permanent; the read side cannot be
retrofitted") has a strict subcase here: for a *reversible* decision, post-hoc reconstruction is
merely inconvenient; for a *stopping* decision it is impossible in principle, because the missing
trials are missing.

The concrete record (`seq-refutation-v1`, written on the refuted branch only, additive): the refuting
axis, its margin, the OTHER axis and ITS margin, the trial count at stop, the policy thresholds in
force, and a capture timestamp.

## Two definitions of one rule is the drift defect

The attribution predicate existed twice: once implicitly in `EProcessState._meets_refutation`, and
once as an independent copy in the analysis script. A live writer plus an independent post-hoc reader
of the SAME rule is a drift hazard whose failure mode is silent: a policy edit moves one copy, and
the live record and the reconstruction then disagree about a candidate that can never be re-run to
settle the question.

The remedy is one canonical function (`sequential_verdict.axis_refutation`) with the reader reduced
to a thin delegation, plus a test asserting live-vs-reconstructed AGREEMENT on a synthetic candidate
— the property that would break first if the two ever diverged.

Three conventions worth stating once, because attribution is otherwise ambiguous:

- **The binding threshold depends on `k`.** `futility_e` (0.05) sits far below `budget_min_e` (2.0),
  so once `k >= budget` the budget clause dominates and IS the bar; before that, futility is. The
  record names which (`rule`).
- **Sign convention: margin = `wealth - threshold`, negative means refuted.** The magnitude is the
  wealth distance to the bar. The one boundary asymmetry (futility is inclusive, budget is strict) is
  inherited from the policy, not invented by the record — so `refuted` is the predicate and `margin`
  is only the distance.
- **Both axes refuting is not "joint".** Precedence is quality-first (mirroring the reader's
  `if/elif`), with `both_axes_refuted` carried separately so the case stays distinguishable, and each
  axis's own verdict retained regardless. An unmeasured axis yields `margin=None` and never refutes:
  an absent measurement is not evidence against.

## Evidence

`epyc-orchestrator` `4c220b11`; 17 new unit tests
(`tests/unit/test_seq_refutation_capture.py`). No recorded verdict changes: the field is additive and
written only on stops, so legacy rows load unchanged and no journal file on disk was modified.
