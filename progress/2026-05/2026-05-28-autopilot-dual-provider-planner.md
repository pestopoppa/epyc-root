# 2026-05-28 — Autopilot Dual-Provider Planner

## Problem

Autopilot's planner was Claude-only. That made planner availability depend on one provider and left no structured way to use the available Codex subscription as an independent critic.

## Changes Made

Implemented provider-coordinated planning in `epyc-orchestrator`:

| Area | Files | Change |
|---|---|---|
| Provider adapters | `scripts/autopilot/planner_providers.py` | Added Claude and Codex planner providers. Codex uses `codex exec --json` in read-only mode, parses assistant-message JSONL, and writes planner tap/archive records. |
| Coordinator | `scripts/autopilot/planner_coordinator.py` | Added primary draft, fallback draft, secondary critique, circuit breaker state, risk-gated critique policy, and canonical action reconciliation. |
| Autopilot loop | `scripts/autopilot/autopilot.py` | Replaced direct controller parsing in the main loop with `plan_with_providers(...)`, while preserving the existing `invoke_controller()` wrapper and public controller helper imports. |
| Tests | `tests/unit/test_autopilot_planner_*.py` | Added unit coverage for Codex JSONL parsing, primary failure fallback, shadow critique, active revision, reject-to-safe-seed fallback, and circuit-open routing. |

## Behavior

- Default primary provider: Claude.
- Default fallback/critic provider: Codex.
- Default mode: `shadow_critique`; fallback is active, but critic revisions are logged rather than applied.
- Active critic reconciliation requires `AUTOPILOT_PLANNER_MODE=draft_critique`.
- Config knobs: `AUTOPILOT_PLANNER_PRIMARY`, `AUTOPILOT_PLANNER_CRITIC`, `AUTOPILOT_PLANNER_MODE`, `AUTOPILOT_PLANNER_CRITIQUE_POLICY`, `AUTOPILOT_PLANNER_CIRCUIT_FAILURES`, `AUTOPILOT_PLANNER_CIRCUIT_COOLDOWN_S`.

## Validation

- `gitnexus status`: PASS after `scripts/gitnexus-analyze.sh` re-index.
- `gitnexus impact invoke_controller --direction upstream --repo epyc-orchestrator --include-tests`: LOW, confined to the Autopilot loop.
- `.venv/bin/python -m pytest tests/unit/test_autopilot_controller_io.py tests/unit/test_autopilot_planner_providers.py tests/unit/test_autopilot_planner_coordinator.py tests/unit/test_autopilot_recovery.py tests/test_gepa_integration.py`: PASS, 52/52.
- `uv tool run ruff check scripts/autopilot/planner_providers.py scripts/autopilot/planner_coordinator.py tests/unit/test_autopilot_planner_providers.py tests/unit/test_autopilot_planner_coordinator.py`: PASS.
- `git diff --check` on touched planner files: PASS.

## Deferred

- Broad wiki synthesis was not run because `compile_sources.py` reported 30 new sources, mostly unrelated parallel handoff edits in the shared worktree.
- Active critic reconciliation should remain opt-in until shadow critique logs show useful corrections without excessive latency or false positives.
