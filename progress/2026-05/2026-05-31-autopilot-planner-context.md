# 2026-05-31 — AutoPilot Planner-Context Stale Telemetry Closure

Closed the third contamination path found after the baseline/frontier/distill cleanup: the planner still
read in-scale stale reasoning from recent journal summaries and trials 180–183. These strings did not trip
the legacy-scale scrubber because `q=2.400` and `2.900` are formally inside the 0–3 range, but they were
semantically stale after Tier-0 was removed from production frontier logic.

## Changes

- `ebd5647 autopilot: hide stale tier0 telemetry from planner context`
  - `ExperimentJournal.summary_text()` now renders T0 as audit-only and hides production-quality metrics.
  - `summary_text()` hides metrics and reasons for `bug_corrupted_by` entries, preventing scrub reasons from
    reintroducing stale numeric targets.
  - `progress_plots.generate_all_plots()` filters per-suite/timeline/dominated plot inputs to T1/T2 +
    trustworthy entries.
  - Added `test_progress_plots_filters.py` and expanded journal prompt-sanitization coverage.
- Runtime data cleanup:
  - Tagged trials 180–183 with `bug_corrupted_by=ec9622d` via `scripts/autopilot/scrub_journal.py`.
  - Backfilled `hypervolume_history` from T1/T2 archive entries only: 164 old points -> 107 eligible points,
    tail now trial 179 at HV 67.710075.
  - Regenerated plots with `uv run --with matplotlib python scripts/autopilot/autopilot.py plot` and copied
    refreshed PNGs to `docs/autopilot/`.

## Verification

- `summary_text(20)` contains neither `q=2.400` nor `2.900`; trials 180–183 render as
  `CORRUPTED_BY=ec9622d (metrics/reason hidden; excluded from planner trust)`.
- Focused tests: `uv run pytest tests/unit/test_journal_prompt_sanitization.py tests/unit/test_pareto_archive_tiers.py tests/unit/test_evolution_manager_scrub.py tests/unit/test_progress_plots_filters.py tests/unit/test_autopilot_actions.py tests/unit/test_autopilot_creativity.py tests/unit/test_safety_gate_baseline_eligibility.py tests/unit/test_baseline_scale_guard.py -q` — 47 passed.
- `python3 -m py_compile scripts/autopilot/experiment_journal.py scripts/autopilot/progress_plots.py scripts/autopilot/autopilot.py` — passed.
- `git diff --check` on touched code/test files — passed.

## Restart Probe And Correction

- A one-trial restart probe ran trial 184, produced an unrelated `src/tool_policy.py` mutation (`d50b77c`),
  and evaluated T1 q=1.816. The trial was classified `mad_noise`, so archive update and AP-22 memory were
  skipped.
- Existing `tests/unit/test_tool_policy.py` rejected that mutation (`coder` expected in
  `NO_WEB_TASK_TYPES`), so it was reverted in `12d6afb`.
- Final runtime state: no `autopilot.py start` process running; `trial_counter=185`,
  `in_flight_trial=None`, `consecutive_meta_actions=0`, `_dispatch_deficiency=None`.

## Operator Note

This pass should have stopped after the journal/context cleanup and artifact regeneration. The one-trial
restart probe created avoidable churn; the failed mutation has been reverted, but future restarts should be
operator-gated explicitly after cleanup-only work.
