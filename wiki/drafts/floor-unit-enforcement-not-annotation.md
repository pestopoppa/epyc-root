# A floor's unit is enforced at the writer and the gate, never annotated after the fact

**Category**: `benchmark_methodology`
**Confidence**: verified (local code + targeted tests, zero inference)
**Date**: 2026-09-14
**Source**: INF-66 R23-55 / INF-73 U2; `epyc-inference-research` branch `fix/noninf-floorunit`
(`scripts/kernel_rnd/autokernel/loop/{serving,bench,instruments,serving_gate,run,source_loo}.py`)
**Folds into**: [Benchmark Methodology](../benchmark-methodology.md) — as an implementation annex to
*Compiled Update — 2026-09-08 (pm, INF-70/INF-66): a floor without its UNIT is a 1200-fold error*, which
already carries the measured spreads (arm sd 0.501% vs process-launch sd 2.793%, ~13x) and the refusal rule.

## What the earlier entry leaves open

That entry states the rule — every floor record carries `unit ∈ {arm, session, process}`, and a gate
comparing an effect to a floor of a different unit REFUSES. Turning it into code surfaced three
conventions that are not derivable from the rule itself, and each of them is the difference between a
rule that holds and a field that is merely present.

## 1. The unit is DERIVED from the harness, never passed as an opinion

A caller that can *choose* a unit can mislabel one, and a mislabelled floor is worse than a missing one —
it is a bar nobody will question. So the unit belongs to the code that took the samples:

- `serving.calibrate_floor` relaunches the server for every sample, and `serving.compare` relaunches it
  for every sample of every arm. Both are therefore `process`-unit **by construction**, stated as
  module constants (`CALIBRATION_UNIT`, `COMPARE_EFFECT_UNIT`) rather than parameters.
- The screen instrument alternates across `llama-bench` invocations, so `bench.FLOOR_UNIT` is `process`
  for the floor **and** for the effect, and both appear in every comparison row.

The writer still has to *state* it (`write_floor(..., unit=...)` has no default: a missing unit is the
defect R23-55 names, so it must be a refusal and not a fallback), but what it states is checked against
what the row already says. A row and a caller that disagree is a relabelled measurement, and refuses.

## 2. A legacy record's unit may be derived from its SCHEMA, but never from its silence

Two kinds of unit-less record exist on disk, and they are not the same fact:

- A **serving** floor (`loop-memory/serving-floor.*.json`) has many possible provenances, so silence is
  unresolvable: it loads as `unit=None`, `legacy=True`, and refuses to gate — naming the file and the
  recalibration command. Nothing is rewritten; the refusal is the fix request.
- A **bench** floor (`calibration/<surface>.<model>.json`) has exactly ONE writer, and that writer
  alternates processes. Its schema therefore *pins* the unit, so a pre-rule record is admitted as
  `process` because the code path that produced it is known — not because the field is absent.

The distinction matters operationally: it closed the rule over the whole live store without touching a
single floor file, while keeping the serving path fail-closed where the provenance genuinely is unknown.

## 3. `n` is the same defect class and belongs in the same gate

A floor is an extreme order statistic (p95 of |deviation|), so a record that cannot state its `n` cannot
state its precision either (R23-61: at n=10 the 5th–95th percentile of the estimate spanned
4.200%–7.821%). The writer therefore promotes whichever count the schema recorded (`samples`,
`calibration_pairs`, `pairs_per_condition`) to `n` and refuses a row that has none, and the gate refuses a
floor whose `n` it cannot read. Both fields are checked *before* any launch, at the same admission point —
a unit check paid for after a gate's worth of host time is a post-mortem, not a gate.

## Consequence for a sealed record

A matched (`serving_floor.v2`) floor is sealed by `content_sha256`. `unit` and `n` must therefore be
inside the seal at calibration time; stamping them at write time would place the two fields a gate depends
on outside the digest, where an edit leaves no trace. The writer refuses a sealed row that lacks them
rather than adding them.
