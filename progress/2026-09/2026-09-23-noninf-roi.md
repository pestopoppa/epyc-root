# 2026-09-23 — non-inference ROI session (ad-hoc, operator-spawned; no roster lane)

Operator asked for an overview of high-ROI handoff work that needs no inference, then for all of it to be
executed. Survey: 4 read-only screeners over the six domain indices. Execution: ~14 implementation
subagents (Sonnet by default, Haiku for mechanical tasks), each on its own worktree, every result reviewed
and re-tested on the main thread before landing; several were corrected in review (below).

## Round 1 — operator items, rulings, tier-1 fixes
Survey of every domain index for high-ROI tasks that need no inference, then execution
(4 screeners, then 10 implementation subagents, each reviewed on the main thread before landing).

- **Operator items:** opencode event reaper relaunched from the tracked path (it had been dead
  since the 2026-09-21 reboot); S-15 vision `max_tokens` 512→1024 (orch `8a8e391c`). Rulings:
  NIB2-59 digest inside the boundary, ETR-1 task_failed scores 0, NIB2-75 retire the E8 tests.
- **Landed, epyc-orchestrator** (main `3c6721ef`): NIB2-74 scorer uses `sys.executable`; NIB2-80
  early-abort escalation bounded at all 5 sites; NIB2-75 24 dead E8 tests retired; EPD-1
  episodic `outcome` tracks the running Q; EV-6b cross-family check resolves roles, fails
  closed on the rubric gate, LABELS llm_judge rows (all-Qwen lineup ⇒ every llm_judge row reads
  `same_family`); ETR-1 code; K4 `-ub` declared 2048 (effective value unchanged) + derived
  chain recompiled (the descriptor "drift" was symlink path spelling only).
- **Landed, epyc-root:** KB-WM-5 per-agent session file; NIB2-81(a) `daemon_provenance.sh`
  wired into reaper + both supervisors, NIB2-81a incident + migration note; stale boxes closed
  (OBS-13, NIB2-68, NI-IO, NIB2-81b, PAW-4); index rows INF-64/INF-76/RTG-47/EVL-44 re-seeded.
- **Landed, epyc-inference-research** (`714777e4`): AK-INST-2 audit found no other drift pin,
  but found the v10 folded-lineage defect — `instrument parents == (production,)` was
  unsatisfiable in `live_controls` preflight and `candidate_record` once
  MEASUREMENT_COMMIT == PRODUCTION_COMMIT; fixed via `worktree.instrument_lineage_ok`.
- **Awaiting the operator:** `bash scripts/operator/ratify_trust_boundary_and_etr1_20260923.sh --apply`
  (MEASUREMENT.md §5 + CHANGELOG, era E17 in instrument_eras.yaml).
- **Left open, verified still needed:** SW-7 (general worktree resolution of gitignored
  citations), INF-66 P7.3 (`test_experiments.py` cwd dependency), NIB2-73b (check still red on
  the architect_critic / qwen38_flash_next known gaps), NIB2-81 remedy (b).

## Round 2 — follow-through (operator: reload API, own DS41 impact, handle the four open items)

| Item | Result | Evidence |
|---|---|---|
| API reload for S-15 | uvicorn :8000 restarted (pid 2815541, 20:31Z) on orch `3c6721ef`; health ok; config reads 1024. DS41 had no :8000 sockets and its profile window ended 19:32Z | `orchestrator_stack.py reload orchestrator` |
| DS41 impact of the lineage fix | Campaign CPU candidates record through `campaign.py:5011` with v10 PRODUCTION==MEASUREMENT, so the first one would have raised; `ebb68dc55` descends from v10, so it now records. Shared research clone fast-forwarded; next batch process loads it | DS41-C12 |
| SW-7 | `PRESENT_IN_MAIN_CLONE` (WARN) verdict via `git --git-common-dir`, same durability test as the main clone; explicit cannot-resolve notice | research `3e83ed4f`; 72 tests |
| P7.3 | `scripts/kernel_rnd/conftest.py`; suites location-independent. Surfaced 78 failed / 10 errors in autokernel controller+execution from EITHER cwd (pre-existing) | research `77b75dae` |
| NIB2-73b / SW-8 | Done by the K4 update; check baseline = 4 known-gap errors (architect_critic critic-suite never run — inference-gated) | orch `3c6721ef` |
| NIB2-81 (b) | registry `runtime` field (daemon + scheduled modes), `observer_census.py --live`, alarm via `alarm_channel`, bus_supervisor restarts `restart_on_stale` rows (reaper only) | root `ddb4d0e9`, `938766ab`, `eb05724b` |
| Operator ruling | bus_supervisor + coordinator-daemon stay DOWN (so no reaper auto-restart meanwhile) | root `10b94f09` |
| Ratification | Applied at the operator's written "apply" over remote control (the operator could not run `!` from the remote client): MEASUREMENT.md §5 + CHANGELOG, era E17 boundary 2026-09-23T21:37:09Z; era guard resolves E17 live | root `c6657ab0`, orch `0c9d57b6` |

## Corrections made in main-thread review (agents' first versions)
- EV-6b first version would have made all 3,806 llm_judge pool items `scoring_failed` (all-Qwen lineup) → reworked to label rows.
- EV-6b loaded a 900-line scripts/ module at import time from src/ → replaced with a 6-line registry lookup.
- EPD-1 first version set `outcome` from the LAST reward's sign → now from the running Q (> 0.5).
- ETR-1 left EV-11 per-role `accuracy` disagreeing with `quality` → one shared denominator helper.
- NIB2-75 left 4 unused imports; NIB2-81 refused the hub's read-only view as a launch root; NIB2-81(b) would have raised permanent false CRITICALs for cron-ticked hub_supervisor/fleet_watch (scheduled mode added).

## Known limitations / follow-ups filed
See the new `- [ ]` tasks: P7.3a (78 autokernel test failures), NIB2-80a (early-abort skips role-cycle check),
NIB2-82 (`baseline_authority_seed` uses `pgrep -af`), NIB2-83 (audit task_failed error texts post-E17),
EV-6c (non-Qwen llm_judge), EPD-1b (operator-gated historical backfill), K4a (research master
`server_defaults.ubatch_size: 8192`).
