# 2026-05-28 — Pareto dashboard freshness fix

## Scope

Affected repo: `epyc-orchestrator`; dashboard panel `GEPA + Pareto Frontier`; autopilot Pareto persistence.

## Problem

The dashboard's Pareto frontier and hypervolume plots looked unchanged for days. Initial live checks showed the panel was polling `/dashboard/api/pareto`, but that endpoint exposed stale data from `orchestration/autopilot_state.json`: frontier trials `8` and `164`, hypervolume flat at `72.071`, and trial ids through `231`. The live journal and log disagreed: recent trials `70` and `71` were marked frontier in `orchestration/autopilot_journal.jsonl`, and the log reported `HV=57.9114` for trial `72`.

## Root Cause

- `ParetoArchive.save(state)` wrote the updated archive to disk, then the caller immediately ran `save_state(state)` with the older in-memory `state["pareto_archive"]`, overwriting the fresh archive.
- `/dashboard/api/pareto` trusted the cached `pareto_archive` subdocument in `autopilot_state.json`, so the dashboard could not show current plots when that cache was stale. It also unnecessarily coupled plot freshness to the live autopilot process state.

## Changes

| Repo | Commit | Files | What |
|---|---:|---|---|
| `epyc-orchestrator` | `11e3e40` | `scripts/autopilot/pareto_archive.py`, `tests/unit/test_atomic_state_persistence.py` | After a successful atomic archive write, synchronize the caller's `state["pareto_archive"]` so follow-up `save_state(state)` cannot reintroduce stale archive data. Added a regression test for the exact archive-save-then-state-save overwrite pattern. |
| `epyc-orchestrator` | `ffff854` | `src/api/routes/dashboard.py`, `src/api/routes/dashboard.html`, `tests/unit/test_dashboard_helpers.py` | Reconstruct `/dashboard/api/pareto` from the append-only `autopilot_journal.jsonl` for the current autopilot session (`autopilot_fleet_started_at`), filtering `bug_corrupted_by` rows. Fallback to cached state only when journal data is unavailable. The accordion summary now shows `journal` vs `state` as the plot source. |

## Verification

- `pytest tests/unit/test_atomic_state_persistence.py tests/unit/test_autopilot_recovery.py tests/unit/test_autopilot_bt_tiebreak.py -q` -> 29 passed.
- `pytest tests/unit/test_dashboard_helpers.py tests/unit/test_dashboard_route_html.py tests/unit/test_atomic_state_persistence.py tests/unit/test_autopilot_recovery.py tests/unit/test_autopilot_bt_tiebreak.py -q` -> 85 passed.
- Extracted dashboard JavaScript passed `node --check`; `python3 -m py_compile src/api/routes/dashboard.py` passed; `git diff --check` passed.
- `ruff` remains unavailable in the local/uv environment (`Failed to spawn: ruff`); accidental `uv.lock` churn from the failed command was restored before commit.

## Deployment

The orchestrator API was reloaded only, not autopilot: `python3 scripts/server/orchestrator_stack.py reload orchestrator` started uvicorn PID `3495860` on 2026-05-28 09:26 UTC and `/dashboard/api/pareto` served the new journal-backed payload.

Live endpoint after reload:

```text
source: journal_current_session
frontier_size: 3
all_entries: 22
hv_points: 22
frontier trial ids: 67, 70, 71
last hypervolume point: [72, 57.9114]
```

Autopilot was already down before the API reload; no autopilot restart was performed.

## Deferred

- The current wiki source manifest still includes unrelated 2026-05-28 research-intake handoff edits from another dirty working-tree stream. They were not compiled or marked complete in this scoped dashboard wrap-up.
