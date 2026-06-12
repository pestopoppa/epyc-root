# Objective: task_rate Axis + Goodput Frontier Rebuild

**Status**: SPEC'D, not started (from the Fable 5 architecture review)
**Created**: 2026-06-12
**Priority**: HIGH — master-index N6; the replay is NOW-class (zero inference: both inputs already journaled)
**Spec**: [fable5-findings-05-objective-design.md](fable5-findings-05-objective-design.md) — read before claiming any waypoint. Slots into [fable5-findings-01-impl-plan.md](fable5-findings-01-impl-plan.md) as Phase 1.6.
**Related**: [evidence-plane-instrument-repair.md](evidence-plane-instrument-repair.md) (noise/admission rules the new axis inherits), [autopilot-continuous-optimization.md](autopilot-continuous-optimization.md) (live consumer), [MEASUREMENT.md](../../MEASUREMENT.md) §P-SPEED-OBJ (already names task_rate as the speed axis) + §5 era table (E3→E4 retire-view)

## Why

The current Pareto vector is fully blind to token bloat: quality, t/s, and
reliability are all bloat-invariant, and the "cost" axis is a routing-tier
average, not a token count — so a verbose and a terse config at equal
correctness are Pareto-indistinguishable while differing 30% in wall-per-task
(spec §verdict). An entire manual research domain (TrimR, brevity limits,
enable_thinking=False, tool-output compression) exists as corrective work the
optimizer could not discover natively. `task_rate` = n / eval-wall-hours; both
inputs are journaled, so the axis replays over FULL journal history at zero inference.

## Waypoints

- [ ] **W1 — axis + shadow journal** (~half day): add `task_rate` to `objectives_from` (`src/autopilot_core/tier_specs.py`, epyc-orchestrator) computed from `eval_wall_s`; journal old+new vectors side-by-side for one shadow period. Acceptance: both vectors present in every new journal row.
- [ ] **W2 — historical replay + bloat-artifact diff report** (~half day, ZERO inference): replay the full journal under (quality, task_rate, reliability) via the existing `pareto_epoch` machinery; one-page diff report naming which historical "wins" were bloat artifacts. Decisive observation per spec: ≥2 of the 5 current frontier points fall off under goodput ⇒ case proven on own data.
- [ ] **W3 — flip the vector** (~half day): archive/gate/baseline move to the 3-D vector behind a policy-version bump; retire t/s AND the tier-cost axis from dominance (tier-mix stays telemetry for capacity planning); record the E3→E4 retire-view per MEASUREMENT.md §5 (frontier restarts fresh; old view archived read-only). Acceptance: dominance runs on the new vector only; era table updated.
- [ ] **W4 — telemetry + doc truth** (~half day): keep t/s as host-throttle diagnostic; add `tokens_per_solved_task` (planner-visible bloat diagnostic — makes compression/brevity experiments self-motivating); fix `scripts/autopilot/program.md:123` + system-card goal-metric text (it describes a wall-occupancy cost proxy the instrument does not compute). Acceptance: program/system-card match the running objective.

## Gates & pitfalls

- Wall time carries the same ~9% host-noise CV as t/s (spec caveat 1) — findings-01 Phase 1.4 sequential/median-cluster admission rules apply to the new axis unchanged; never single-trial rate claims.
- `task_rate` depends on question mix AND eval concurrency — both are instrument: fix per core-version, bump policy version on any change; per-suite wall telemetry attributes which suites pay the bloat.
- Degenerate-terseness is bounded (quality is a co-equal axis); if a long-form role emerges, add a suite-level format-adequacy check — never re-reward tokens globally.
- Tool tokens stay excluded from the rate (already correct); tool use is priced by downstream correctness + wall cost.
- Replay is retire-view, not rewrite: journal rows are immutable; quality is NOT rescaled across eras (MEASUREMENT.md §5).

## Reporting

Tick waypoints here + one-line progress entry; delete master-index row N6 on completion; all rate numbers via the MEASUREMENT.md §2 claim grammar.
