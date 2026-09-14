# Draw Completeness and the Baseline Pin

**Category**: `benchmark_methodology`
**Confidence**: verified (code-resident contract; `epyc-orchestrator` `4555677e`, 28 unit tests, zero inference)
**Drafted**: 2026-09-14
**Target page**: `wiki/benchmark-methodology.md`
**Provenance**: EVL-14 EV-14d + EV-14e, `handoffs/active/eval-tower-verification.md`

Two defect classes closed in the same commit, both instances of the same failure: **a report that
records a derived number but not the fact the number depends on.** One is about the denominator, the
other about the comparator.

## 1. A report must state what it ASKED for, not only what it got

`EvalTower._eval_batch` collects results into a pre-sized list and returns
`[r for r in results if r is not None]`. Holes are reachable by design — the pipelined path leaves
one when a lane is abandoned or a future is cancelled, and the serial path `break`s out of its loop
on the wall-budget timeout. So the batch can come back SHORT of what it was handed.

Four per-role report writers (calibration, math re-baseline, question subset, resume-incomplete)
defined `n_questions = len(results)`. That single choice **renames the shortfall as the
denominator**: 40 of 50 questions scored is byte-identical in the report to a complete draw of 40,
and every accuracy, reliability and task-rate computed from it reads as a whole-suite number. The
draw is the one thing that got smaller and the one thing nothing recorded.

**The contract.** A per-role report block carries, together:

| field | meaning |
|---|---|
| `n_questions` | the REQUESTED count — what the run asked the batch for |
| `n_questions_requested` | the same, named explicitly |
| `n_questions_completed` | what actually came back |
| `n_questions_missing` | `requested − completed` |
| `completeness_ratio` | `completed / requested` |
| `draw_complete` | `requested > 0 and completed >= requested` |

`n_questions` is the requested count rather than the delivered one for a specific reason: every
pre-existing downstream guard of the form `n_questions < expected_n` keeps its meaning. Had
`n_questions` stayed as delivered, tightening the fields would have *weakened* those guards, because
a short draw would report a smaller number that still "matched" a smaller expectation. The mode
report also carries a top-level fold — `draw_complete` plus `incomplete_roles` — so a consumer never
has to walk the per-role map to learn that one role drew short.

### Two predicates, deliberately asymmetric

This is the reusable part. A completeness check has two callers with opposite correct defaults, and
collapsing them into one function is wrong either way:

- **`draw_is_complete(payload)` — FAIL-CLOSED.** Returns False when the requested/completed pair is
  absent. Absence of counts is not evidence of completeness; the only safe answer for a payload that
  never counted is "unknown, therefore not complete." This is the predicate a *writer of a new
  decision* uses.
- **`draw_shortfall(payload)` — SILENT ON ABSENCE.** Returns `(requested, completed)` only when both
  fields are present AND disagree; returns `None` both for a complete draw and for a payload with no
  counts at all. This is the predicate a *reader of old evidence* uses.

The asymmetry exists because the fail-closed predicate applied to a gate would have retroactively
failed every artifact written before the fields existed — a correctness fix that invalidates the
archive is not deployable. So the gate consumer (the eval-batch serving window runner's arm and
verifier blockers) blocks on a *recorded* gap, while anything asserting completeness forward uses the
strict form. **Generalization: when a new provenance field lets you detect a defect, the detector
that gates NEW writes and the detector that reads OLD artifacts are different functions.**

## 2. A comparison must record its comparator, not narrate it

AutoPilot's safety gate compares a trial's quality against a per-tier baseline. Before this change,
the baseline value reached the journal **only as prose** — the gate's regression string
(`"Quality regression: 1.744 vs baseline 1.884 …"`) landed in `failure_analysis`, and a regex
(`_BASELINE_QUALITY_RE`) parsed it back out. `JournalEntry` had no baseline, delta, or
previous-quality field at all.

Three independent failures follow, and only the first is obvious:

1. A regex over a sentence recovers a NUMBER but never the comparison's **identity** — not which
   tier reference was used, not that reference's monotonic revision (EV-14c), not the
   `eval_quality_era` it was captured under. Two rows quoting "baseline 1.884" may be comparing
   against different references.
2. The prose is written **only on a regression.** Every trial that PASSED the gate recorded no
   baseline whatsoever, so the archive's clean rows are exactly the ones with no comparator.
3. **Ordering.** `update_baseline()` runs between the gate check and the journal write. Anything
   reconstructed at write time is therefore the POST-promotion reference — the candidate's own
   number standing in as its own incumbent. A pin must be captured *before the write that can move
   it*, which means at compare time, by the caller.

**The `baseline_pin` schema** (`JournalEntry.baseline_pin`, `schema_version: 1`):

| field | meaning |
|---|---|
| `source` | `structured` \| `legacy_failure_analysis_regex` \| `absent` \| `capture_error` |
| `tier` | the tier whose reference was compared |
| `baseline_quality` | the reference value, or `None` when there was none |
| `baseline_revision` | the EV-14c per-tier monotonic revision — makes a reference that moved AFTER the compare detectable from the row alone |
| `eval_quality_era` / `autopilot_speed_era` | the instrument eras the reference was captured under |
| `per_suite_baseline_quality` / `per_suite_baseline_counts` | the per-suite reference map and the sampling resolution it was measured at |
| `baseline_path` | which baseline file it came from |
| `candidate_quality`, `delta`, `relative_delta` | the comparison as made, stored not recomputed |
| `suppressed_by` | why there was NO usable reference (`quality_rebaseline_hold`, `no_same_tier_baseline`) |
| `captured_at` | capture timestamp |

Two conventions worth carrying:

- **An absent reference is recorded as absent, never as `0.0`.** `baseline_quality: None` plus
  `suppressed_by` naming the reason is a different fact from a baseline of zero, and the difference
  decides whether a delta is meaningful.
- **The legacy fallback announces itself.** The reader prefers the structured field and falls back to
  the regex ONLY for rows written before the field existed, stamping
  `source="legacy_failure_analysis_regex"` and logging once per trial that the comparison identity
  "was never recorded and cannot be recovered." A prose baseline above the possible 0-3 quality scale
  (a known corrupt-era artifact) is returned as suspect with `baseline_quality: None` rather than
  handed back as a number — so a scrubbed corrupt baseline cannot re-enter a comparison through the
  fallback.

The migration is additive: the field defaults to `{}`, legacy shards load unchanged, and **no journal
file on disk is rewritten or back-filled** — a pin invented at load time would claim a comparison
identity the original trial never captured.

## Source references

- `epyc-orchestrator` `4555677e` — `scripts/autopilot/experiment_journal.py`,
  `scripts/autopilot/eval_tower.py`, `scripts/autopilot/autopilot.py`,
  `scripts/benchmark/eval_batch_serving_evaltower_window.py`
- Tests: `tests/unit/test_ev14d_short_draw_completeness.py`,
  `tests/unit/test_ev14e_baseline_pin_record.py`
- `handoffs/active/eval-tower-verification.md` — EV-14d, EV-14e (and EV-14c for the revision pin the
  baseline pin reuses)
- External framing only, gates nothing locally: `intake-1141#record` (a half-vendored suite that
  "passes config validation and then scores a subset of the benchmark without saying so", and the
  write-the-pin-into-the-run's-own-result pattern).
