# A guard computed, documented and never consulted (`quality_measured`)

**Category**: `benchmark_methodology`
**Confidence**: verified (local code + unit tests, zero inference)
**Date**: 2026-09-14
**Source**: EVL-13 ETR-2/ETR-3, `epyc-orchestrator` `250a5d13`; handoff
`handoffs/active/eval-tower-loop-robustness-audit-2026-07-20.md`
**Folds into**: [Benchmark Methodology](../benchmark-methodology.md) — the absence-read-as-a-value
defect class, as the WRITE-side companion to
[`absent-vs-measured-zero-on-objective-axes.md`](absent-vs-measured-zero-on-objective-axes.md) (RTG-23,
the read side)

## The mechanism

`EvalResult.quality` is a plain float on the Pareto/SafetyGate contract, so it cannot be `None`. The
2026-08-03 incident (a T1 calibration reporting `0% correct` purely because the orchestrator API was
down) was answered by carrying the honesty in a companion flag: `quality_measured=False` means *the 0.0
next to me is a placeholder, not a measurement*. Each placeholder construction even carried the comment
saying so.

The flag was then read by nobody. Neither `SafetyGate.check()` nor `update_baseline()` consulted it, so a
placeholder entered the promotion gate as a literal `0.0` candidate score. What actually stopped those
trials was an **independent** guard — the REL-1 reliability floor — which fires because the same infra
failure also craters `reliability`. Two consequences:

1. The protection was **incidental**. Any placeholder path that leaves reliability intact (a partition
   filter that empties the decision subset; a loader/config abort that never asks a question) had no
   guard at all.
2. Where REL-1 did fire, the trial was charged a **quality-floor / regression violation** — a fabricated
   regression written into planner-visible `failure_analysis` out of a measurement that never happened.

**A guard is not deployed until something reads it.** "Computed, documented, never consulted" is the
symmetric twin of `feedback_fail_open_defaults_conceal_their_own_corruption`: the comment asserts the
invariant, the code never enforces it, and a reader auditing the source concludes the system is safe.

## Two halves, and only one of them can be retrofitted

- **Read side** (cheap to add, what this change did): fail closed on the flag, with its own
  distinguishable reason (`quality_not_measured`), and *suppress* rather than charge the quality legs —
  the absence of a measurement is not evidence of a regression, so it blocks promotion without arming
  the auto-rollback counter. A **measured** 0.0 keeps `quality_measured=True` and is still gated as a
  measurement. Never conflate the two.
- **Write side** (impossible to retrofit): eleven early-return placeholders in `eval_tower.py` built
  `EvalResult(quality=0)` and left the flag at its `True` default, i.e. they asserted a measurement they
  had never made. A flag that defaults to the *safe-looking* value silently lies for every producer that
  forgets it. The structural remedy used here is an AST test over the producer module: every
  `EvalResult(quality=0)` construction must carry `quality_measured=False` **and** a named reason, so a
  new placeholder cannot reintroduce the defect by omission.

## The narrow silent-scoring hole, and the structural signal that closes it

The disposition taxonomy already excluded an *empty* zero-token reply (`empty_response`). The hole was
one step away: a **non-blank** answer with no error field and no structural signal returned `None` from
`infra_failure_reason` and was scored as an ordinary wrong answer.

The decisive fact was already on the wire and unread — the response reports **zero generated tokens**.
Text with no decode behind it (a templated/echoed/stub body) is the absence of a measurement, in exactly
the class of `empty_response`, whose blank-answer requirement is why this shape slipped past. New reason:
`answer_without_generation`.

Two scoping rules make it safe, and both generalize:

- **Name the residue instead of widening the heuristic.** A non-blank answer *with* a real token count is
  a genuine generation, so garbage there is the model's own failure and stays scored WRONG. "Garbage" is
  not detectable; "did not come from a decode" is.
- **A measurement guard is not automatically a reward guard.** The leg is opt-in
  (`require_generation_evidence`) and set only on measurement paths (eval tower, seeding calibration).
  The live-serving reward path deliberately leaves it off: excluding a row from a quality denominator is
  fail-closed, but withholding a *negative reward* from a genuinely wrong answer is the opposite — it
  teaches the router that a bad answer never happened.

## Evidence

`epyc-orchestrator` `250a5d13`; 26 new unit tests
(`tests/unit/test_safety_gate_quality_measured.py`, `tests/unit/test_quality_measured_producers.py`,
`tests/unit/test_answer_without_generation.py`). No quality number already on record changes: the edits
affect promotability and disposition only, never a computed quality.
