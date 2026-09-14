# Mutually blocking fences: a provenance stamp reachable only through the write it blocks

**Category**: `benchmark_methodology`
**Confidence**: verified (local code + unit tests, zero inference)
**Date**: 2026-09-14
**Source**: RTG-02, `epyc-orchestrator` `d03218fc`; handoff
`handoffs/active/autopilot-continuous-optimization.md` (boxes at `:1727` and `:1780`)
**Folds into**: [Benchmark Methodology](../benchmark-methodology.md) — era/instrument fencing, as a
companion to the absent-vs-measured-zero defect class

## The mechanism

An instrument-era fence is a pair: a **stamp** on the resident baseline naming the instrument era it
was measured under, and a **hold** that refuses comparisons across a boundary. AutoPilot runs two such
fences — `eval_quality_era` (scorer/question-pool instrument) and `autopilot_speed_era`
(kernel/binary/topology instrument). Both were correct in isolation.

The defect is in where the stamps were written. Both stamps lived at the END of
`SafetyGate.update_baseline()`, i.e. *inside a successful promotion*, while each hold returns EARLY from
that same method. So:

- the quality hold's documented remediation is "reseed a baseline stamped with the active era" — but the
  only in-loop writer of that stamp is the promotion the hold refuses;
- the speed stamp sat ~220 lines BEHIND the quality hold's early return, so while the quality fence was
  held the speed stamp was **unreachable code** — the speed hold could never close either, even though
  the throughput instrument had nothing to do with the eval instrument.

Net live effect: quality promotion dead, and a cross-era throughput violation permanently demoted to a
warning with no in-code path to re-arm it. Neither symptom looks like a bug at the symptom: both fences
report exactly the fail-closed message they were designed to report. Only reachability analysis finds it.

**The general rule: a fence's CLEARING path must not run through the write the fence blocks.** A
fail-closed guard whose only remedy is gated by itself is not fail-closed, it is a latch — and two such
latches on independent axes will latch each other.

## Three rules the repair follows

1. **One instrument, one fence, one clearing path.** Independent instruments have independent eras, so
   neither may be held hostage by the other. The speed axis re-anchors from its own in-era measurement
   (`_reseed_speed_axis_if_held`) on the very path that refuses the quality promotion.
2. **A stamp must not outrun the measurement it describes.** The speed reseed fires only where
   `update_tier()` would itself have rewritten `frontdoor_speed` (frontier tier, positive speed sample,
   eligibility already certified). Stamping an era onto a number nobody re-measured is the provenance
   lie the field exists to prevent — the fix would have reintroduced the original defect one level up.
3. **Stamp the era of the instrument that PRODUCED the number, never the era current at write time.**
   Those two differ across exactly the boundary the fence detects, so reading "now" at write time
   launders a pre-boundary measurement into the current era. The result carries its own era (stamped at
   measurement time from the human-owned registry, with `active` / `unfenced` / `unresolved` as three
   explicit outcomes) and the baseline writer REFUSES an unstamped or unresolved result rather than
   guessing. An unstamped baseline holds the fence forever; an invented stamp is worse — it opens it on
   a claim no measurement supports.

## Evidence

`epyc-orchestrator` `d03218fc`; 23 new unit tests (`tests/unit/test_era_stamp_reachability.py`),
including the deadlock state itself (both eras active, both holds open) and the four negative cases where
no stamp is permitted. `pytest tests -k "safety_gate or era or baseline or calibrat"`: 1674 → 1696
passed, 20 pre-existing failures unchanged. No quality or speed number already on record changes: the
edits affect promotability and provenance only, never a computed metric.
