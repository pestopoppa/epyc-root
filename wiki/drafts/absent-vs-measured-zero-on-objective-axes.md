# Absent vs measured zero on objective axes

**Category**: `benchmark_methodology`
**Confidence**: verified (local code + full journal replay, zero inference)
**Date**: 2026-09-14
**Source**: RTG-23, `epyc-orchestrator` `fb16d860`; handoff `handoffs/active/objective-task-rate-goodput.md` (W3d)
**Folds into**: [Benchmark Methodology](../benchmark-methodology.md) — the absence-read-as-a-value defect class
(alongside RC-11 `None`-not-`0.0`, the three-valued gate verdicts, and CJ-8/9/11/12)

## The mechanism

`float(x or 0.0)` is not a numeric coercion, it is a **claim**: it asserts that a value the run never
produced equals the worst possible measurement. On a Pareto objective that assertion is unremovable, not
merely wrong:

- A max-objective frontier admits any point nothing dominates, and domination requires being at least
  equal on **every** axis. A point holding the maximum on one axis is unbeatable on that axis, so nothing
  dominates it however bad its other axes are.
- Therefore a zero on a *quality* axis cannot be corrected by dominance. Only an admission floor or a
  scaled axis can exclude such a point — and neither existed in `src/autopilot_core/`.
- So an unmeasured axis read as `0.0` does not merely add noise: it manufactures a permanent frontier
  point out of a trial that measured nothing.

The rate axis had already been fixed this way (`seq_task_rate_qph` returns `None`, never `0.0`, because a
missing measurement fed to the sequential z-test scored y = −1 and pinned the clip floor). The lesson did
not propagate to the other three axes of the same tuple, which kept `or 0.0`.

## The companion defect: a gate that checks less than its name

`objectives_measurable`'s docstring read *"True when this result carries every axis the live dominance
vector needs"*; its body was `return seq_task_rate_qph_from(result) is not None` — one of four axes. A
result with no quality, cost or reliability passed a gate whose name and docstring both said it had
checked them. **Remedy pattern**: a measurability gate should not re-implement the check — it should call
the *builder* it gates and report whether the builder refused (`UnmeasuredObjectiveError`). Gate and
construction then cannot diverge by construction.

## The measured facts (AutoPilot journal, both shards, 2026-09-14)

Instrument: `orchestration/autopilot_journal.jsonl` + `autopilot_journal_1.jsonl`, 1,390 rows / 1,372 trial
rows, read-only offline replay through `reconstruct_archive_from_journal_rows` (zero inference).

| Fact | Count |
|---|---|
| Trial rows with falsy quality | 231 (16.8%) |
| …of those, rows whose eval NEVER RAN (`eval_details == {}`, no question count, no wall clock) | 225 |
| …of those 225: T0 sentinel lane / bug-corrupted T1 | 224 / 1 |
| …of the 231, rows with a real eval behind a genuine **measured** 0.0 quality | 6 |
| Rows the policy-aware objective builder refused, before → after | 0 → 225 |
| T0 audit entries reconstructed, before → after | 318 → 233 |
| Frontier sizes, before → after (legacy T1/T2/T3; rate T1/T2) | 11/4/1 and 13/8 — unchanged |
| Zero-quality points **on** a reconstructed frontier, before → after | 0 → 0 |

Two things follow, and the second corrects a prior record:

1. **The placeholder is identifiable on the read side.** The substituted value IS `0.0`, so a zero on a row
   that ran no eval never measured anything, while a NON-zero value cannot have come from that path and is
   always a measurement. This distinguishes absence from a measured zero *without* rewriting any journal
   row (replay is retire-view; rows are immutable).
2. **The realised blast radius was smaller than recorded.** The W3d record (2026-08-12) read the 231 falsy
   rows as "admitted to the frontier as zero-quality points". Replay shows every one of the 225
   never-evaluated rows is either T0 (a sentinel lane below `MIN_FRONTIER_EVAL_TIER`, which no frontier
   admits) or already bug-excluded — so zero-quality frontier points were 0 before the fix and 0 after.
   The *defect* was real and now closed in the objective plane; the *frontier corruption* it was believed
   to have caused had not occurred. A count of rows carrying a bad value is not a count of decisions that
   value reached.

## Reusable rules

- On any axis that gates a decision, absence has its own state: `None` (row/result side) or a refusal
  (`UnmeasuredObjectiveError`) on the construction side. Never a number.
- A measurability gate calls its builder; it never re-implements the axis checks.
- Quality-derived display metrics inherit the distinction — an unmeasured quality yields a **null**
  goodput, not `0.0`, or the same rows re-enter under a quality-scaled axis scored as zero goodput.
- When a record says N rows carry a defective value, replay to find how many reached a decision before
  sizing the remedy.
