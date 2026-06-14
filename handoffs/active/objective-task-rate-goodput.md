# Objective: task_rate Axis + Goodput Frontier Rebuild

**Status**: HOLD/SHADOW — W1-W2 + W4 landed 2026-06-12; W3 live vector flip held by 2026-06-13 policy decision; replay reports fold supersession events as of `d21bbee`
**Created**: 2026-06-12
**Priority**: GATED — N6 policy decision closed 2026-06-13; W3 reopens only after the evidence-plane and quality-eligibility gates below
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

- [x] **W1 — axis + shadow journal** (~half day): added task-rate helpers and policy constants in `src/autopilot_core/tier_specs.py`; `eval_tower._aggregate()` records `task_rate_qph`, `goodput_qph`, and `tokens_per_solved_task`; new journal rows include live legacy vector + shadow task-rate vector under policy labels.
- [x] **W2 — historical replay + bloat-artifact diff report** (~half day, ZERO inference): replay implemented via `scripts/analysis/task_rate_goodput_replay.py` and `journal_reconstruction` objective-policy replay. Full-journal report: `epyc-orchestrator/orchestration/reports/task_rate_goodput_replay_2026-06-12.md`. Follow-up `d21bbee` folds append-only supersession events before rendering report rows, so replay tables match supersession-aware archive/dashboard state.
- [ ] **W3 — flip the vector** (~half day): archive/gate/baseline move to the 3-D vector behind a policy-version bump; retire t/s AND the tier-cost axis from dominance (tier-mix stays telemetry for capacity planning); record the E3→E4 retire-view per MEASUREMENT.md §5 (frontier restarts fresh; old view archived read-only). **Hold as of 2026-06-13**: W2 replay found 1/5 legacy T1 frontier points fall off under `task_rate_3d_v1`, not the spec's >=2/5 proof threshold, and raw `task_rate` admits a zero-quality high-rate frontier point. Do not flip live dominance yet.
- [x] **W4 — telemetry + doc truth** (~half day): `task_rate_qph`, `goodput_qph`, and `tokens_per_solved_task` are journaled; `scripts/autopilot/program.md` now states that EvalTower `speed` remains the current Pareto speed axis/host-throttle diagnostic, task-rate fields are shadow policy telemetry, and `tokens_per_solved_task` is the bloat diagnostic. The stale wall-occupancy `sum(tokens_generated[role] / throughput_tps[role])` proxy is explicitly marked as not computed/not live. `rg` found no other live system-card copy of that stale text.
- [x] **W5 — policy decision** (2026-06-13, zero inference): keep `task_rate_qph`, `goodput_qph`, and `tokens_per_solved_task` as shadow telemetry; leave live Pareto dominance on the current objective until preconditions below are met.

## 2026-06-13 Policy Decision

**Verdict: HOLD the live vector flip; continue shadow telemetry.**

Rationale:

- The replay did not meet the Fable proof gate: only 1/5 legacy canonical T1 frontier points fell off under `task_rate_3d_v1`; the proposed gate was >=2/5.
- Raw `task_rate` creates an obviously unsafe frontier point: trial 75 enters the task-rate frontier with quality 0.000 and goodput 0.00 because it completed quickly. Quality remains an axis, but the replay proves raw rate alone can preserve junk candidates as non-dominated noise.
- Findings-01 dependencies are not fully in place: per-question ledger, sequential verdicts, core_v2 repair, and E4 retire-view bootstrap are still pending, so flipping now would create another objective-era boundary before the evidence plane can certify effects.

Reopen W3 only after all of these are true:

- N2 per-question ledger + sequential e-process verdict path is live for the restart bundle.
- Instrument repair/core_v2 or equivalent E4 boundary is in force, with frontier/baseline retire-view mechanics ready.
- A replay of the chosen policy (`task_rate` with explicit quality eligibility, or a goodput-shaped variant) no longer admits zero-quality high-rate frontier entries.
- The replay either meets the original >=2/5 historical-frontier proof threshold or a documented shadow-period result shows task-rate/goodput changes live decisions without degrading quality/reliability.

## Gates & pitfalls

- Wall time carries the same ~9% host-noise CV as t/s (spec caveat 1) — findings-01 Phase 1.4 sequential/median-cluster admission rules apply to the new axis unchanged; never single-trial rate claims.
- `task_rate` depends on question mix AND eval concurrency — both are instrument: fix per core-version, bump policy version on any change; per-suite wall telemetry attributes which suites pay the bloat.
- Degenerate-terseness is bounded (quality is a co-equal axis); if a long-form role emerges, add a suite-level format-adequacy check — never re-reward tokens globally.
- Tool tokens stay excluded from the rate (already correct); tool use is priced by downstream correctness + wall cost.
- Replay is retire-view, not rewrite: journal rows are immutable; quality is NOT rescaled across eras (MEASUREMENT.md §5).

## Reporting

Tick waypoints here + one-line progress entry; all rate numbers via the MEASUREMENT.md §2 claim grammar. The master-index N6 row was removed on 2026-06-13 after the hold decision; future W3 work belongs in the gated cluster until reopen criteria are met.

## Checkpoints

- 2026-06-12 W2 replay result: 656 journal rows parsed, 0 malformed skipped; legacy canonical T1 frontier = 5 points, task-rate replay frontier = 8 points, admitted entries = 247 in both views. Dropped legacy point: trial 776 (quality 1.884, wall 804.5s, task_rate 192.42 q/h, goodput 120.82 q/h) dominated by trial 775 under task-rate. Fable proof criterion (`>=2 of 5`) was **not met**.
- Verification: `uv run pytest tests/unit/test_autopilot_core_contracts.py tests/unit/test_eval_tower_concurrency_metrics.py tests/unit/test_eval_tower_hybrid_eval.py tests/unit/test_autopilot_controller_io.py tests/unit/test_evolution_manager_scrub.py tests/unit/test_safety_gate_baseline_eligibility.py tests/unit/test_per_suite_regression_resolution.py tests/unit/test_self_criticism_resolution.py` → 81 passed; `git diff --check` clean.
- 2026-06-12 W4 doc-truth verification: `gitnexus impact File:scripts/autopilot/program.md --direction upstream` LOW; `rg` confirms the only remaining stale wall-occupancy phrase is the negated warning in the updated text; `git diff --check -- scripts/autopilot/program.md` clean. Landed in `epyc-orchestrator` `9bc4c3a`.
- 2026-06-13 W5 policy checkpoint: live dominance flip held. Shadow telemetry remains useful, but the NOW-class decision is closed as "do not flip yet"; W3 remains gated on N2/E4 and a quality-eligible replay.
- 2026-06-14 replay read-path follow-up: `epyc-orchestrator` `d21bbee` makes `scripts/analysis/task_rate_goodput_replay.py` fold append-only supersession events before rendered report rows. Regression coverage in `tests/unit/test_task_rate_goodput_replay.py` verifies folded values replace raw superseded metrics; combined analytics validation passed (`15 passed`) with focused ruff and diff-check clean.
