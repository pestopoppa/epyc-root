"""Tests for the eval_quality instrument-era resolver (defect #1/#3/#4 fence source).

``active_eval_quality_era`` is the QUALITY-axis analogue of the speed axis's era lookup:
it answers "which eval-instrument era is live now, and at what boundary did it open" from
the human-owned registry, fail-closed. Wiring this into the decision path (autopilot
startup migration) is the audit's "guard exists but is unwired" fix.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from src.autopilot_core.instrument_era_guard import (
    E7_EVAL_INSTRUMENT_BOUNDARY,
    E7_EVAL_INSTRUMENT_ERA_ID,
    EVAL_QUALITY_SCOPE,
    active_eval_quality_era,
)

_E7_EPOCH = datetime(2026, 7, 21, 10, 30, tzinfo=timezone.utc).timestamp()
_AFTER = datetime(2026, 7, 22, 0, 0, tzinfo=timezone.utc).timestamp()
_BEFORE = datetime(2026, 7, 20, 0, 0, tzinfo=timezone.utc).timestamp()


def _registry(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "instrument_eras.yaml"
    path.write_text(body)
    return path


_E7_REGISTRY = """
eras:
  - id: E6-autopilot-speed
    from: "2026-07-20T13:30:13Z"
    scope: autopilot_speed
    note: "speed only"
  - id: E7-eval-instrument
    from: "2026-07-21T10:30:00Z"
    scope: eval_quality
    note: "pool rebuild + B7 scorer"
"""


def test_code_constant_matches_registry_row_identity() -> None:
    # The fail-safe fallback constant MUST equal the registry row it stands in for.
    assert E7_EVAL_INSTRUMENT_ERA_ID == "E7-eval-instrument"
    assert E7_EVAL_INSTRUMENT_BOUNDARY == "2026-07-21T10:30:00Z"
    assert EVAL_QUALITY_SCOPE == "eval_quality"


def test_active_era_resolved_after_boundary(tmp_path: Path) -> None:
    guard = active_eval_quality_era(path=_registry(tmp_path, _E7_REGISTRY), now=_AFTER)
    assert guard["ok"] is True
    assert guard["status"] == "active"
    assert guard["era_id"] == "E7-eval-instrument"
    assert guard["boundary_epoch"] == _E7_EPOCH
    assert guard["boundary_iso"] == "2026-07-21T10:30:00Z"


def test_no_active_era_before_boundary_is_fail_closed_unfenced(tmp_path: Path) -> None:
    # Before the boundary the registry reads fine but no eval_quality era is active — the
    # migration must then leave the quality axis unfenced (single-era world), not fabricate one.
    guard = active_eval_quality_era(path=_registry(tmp_path, _E7_REGISTRY), now=_BEFORE)
    assert guard["ok"] is False
    assert guard["status"] == "no_active_era"


def test_missing_registry_fails_closed(tmp_path: Path) -> None:
    guard = active_eval_quality_era(path=tmp_path / "absent.yaml", now=_AFTER)
    assert guard["ok"] is False
    assert guard["status"] == "missing_registry"


def test_invalid_yaml_fails_closed(tmp_path: Path) -> None:
    guard = active_eval_quality_era(path=_registry(tmp_path, "eras: [::::"), now=_AFTER)
    assert guard["ok"] is False
    assert guard["status"] == "invalid_registry"


def test_registry_without_eras_list_fails_closed(tmp_path: Path) -> None:
    guard = active_eval_quality_era(path=_registry(tmp_path, "not_eras: 1\n"), now=_AFTER)
    assert guard["ok"] is False
    assert guard["status"] == "invalid_registry"


def test_invalid_boundary_timestamp_fails_closed(tmp_path: Path) -> None:
    body = """
eras:
  - id: E7-eval-instrument
    from: "not-a-timestamp"
    scope: eval_quality
"""
    guard = active_eval_quality_era(path=_registry(tmp_path, body), now=_AFTER)
    assert guard["ok"] is False
    assert guard["status"] == "invalid_registry"


def test_latest_opened_era_wins_when_two_are_active(tmp_path: Path) -> None:
    body = """
eras:
  - id: E7-eval-instrument
    from: "2026-07-21T10:30:00Z"
    scope: eval_quality
  - id: E8-eval-instrument
    from: "2026-07-21T20:00:00Z"
    scope: eval_quality
"""
    guard = active_eval_quality_era(path=_registry(tmp_path, body), now=_AFTER)
    assert guard["ok"] is True
    assert guard["era_id"] == "E8-eval-instrument"


def test_other_scopes_are_ignored(tmp_path: Path) -> None:
    body = """
eras:
  - id: E6-autopilot-speed
    from: "2026-07-20T13:30:13Z"
    scope: autopilot_speed
  - id: E3a
    from: "2026-06-04T06:41:00Z"
    scope: autopilot_quality
"""
    guard = active_eval_quality_era(path=_registry(tmp_path, body), now=_AFTER)
    assert guard["ok"] is False
    assert guard["status"] == "no_active_era"


def test_resolves_against_the_live_shipped_registry() -> None:
    # No path override => reads orchestration/instrument_eras.yaml. The E7 row IS shipped, so
    # at a post-boundary clock the fence resolves from the real source of truth.
    guard = active_eval_quality_era(now=_AFTER)
    assert guard["ok"] is True
    assert guard["era_id"] == "E7-eval-instrument"
    assert guard["boundary_epoch"] == _E7_EPOCH
