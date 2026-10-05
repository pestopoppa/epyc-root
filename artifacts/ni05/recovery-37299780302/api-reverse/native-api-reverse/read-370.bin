#!/usr/bin/env python3
"""E8-PANELS-a — the three rerun-progress surfaces must agree.

`completed_numeric_trials` used to be written onto the frontier-rerun marker only
by `_clear_frontier_rerun_marker`, i.e. once the gate was already satisfied. While
the marker was OPEN it kept the value it was created with — 0 — even though the
live count was recomputed every decision cycle and reached only the rationale.

Result: three surfaces, three answers. The system-card banner carried no count,
the operator brief rendered `pending <era> numeric rerun (0/16)`, and the gate
itself knew 15/16.

These tests pin that the reporting surfaces read the marker's counters, and — the
part that matters for safety — that the hold does NOT depend on them, so a
missing or stale count can never release a fail-closed gate.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]


def _load(relpath: str, name: str):
    spec = importlib.util.spec_from_file_location(name, _ROOT / relpath)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def brief():
    return _load("scripts/autopilot/optimization_brief.py", "_opt_brief_e8panels")


@pytest.fixture(scope="module")
def card():
    return _load("scripts/autopilot/gen_system_card.py", "_card_e8panels")


def _open_marker(**over):
    marker = {
        "required": True,
        "reason": "era fence",
        "min_numeric_trials": 16,
        "opened_at": "2026-08-01T00:00:00+00:00",
    }
    marker.update(over)
    return marker


def test_brief_reports_live_progress(brief):
    """The 15/16 the operator should see, where they used to see 0/16."""
    state = {
        "frontier_rerun_required": _open_marker(
            completed_numeric_trials=15, min_numeric_trials=16
        )
    }
    out = brief._live_era_holds(state)
    assert out["frontier_rerun_required"] is True
    assert "15/16" in out["speed_authority"], out["speed_authority"]
    assert out["speed_hold_detail"]["completed_numeric_trials"] == 15
    assert out["speed_hold_detail"]["min_numeric_trials"] == 16


def test_hold_does_not_depend_on_the_count(brief):
    """A missing counter must never release a fail-closed gate.

    The hold keys off `required`, not the count. Pinned because this change
    touches the field the operator-facing string is built from, and a regression
    that wired the hold to the count would silently unblock the gate.
    """
    out = brief._live_era_holds({"frontier_rerun_required": _open_marker()})
    assert out["frontier_rerun_required"] is True, "hold must survive a missing count"
    assert out["any_hold_active"] is True
    # And 0/16 must still read as held, not as satisfied.
    out0 = brief._live_era_holds(
        {"frontier_rerun_required": _open_marker(completed_numeric_trials=0)}
    )
    assert out0["frontier_rerun_required"] is True


def test_cleared_marker_releases_the_hold(brief):
    """The compliant path: `required: False` is what actually clears it."""
    out = brief._live_era_holds(
        {
            "frontier_rerun_required": _open_marker(
                required=False, completed_numeric_trials=16
            )
        }
    )
    assert out["frontier_rerun_required"] is False
    assert "no frontier rerun marker open" in out["speed_authority"]


def test_banner_renders_progress_when_present(card):
    state = {
        "frontier_rerun_required": _open_marker(
            completed_numeric_trials=15, min_numeric_trials=16
        )
    }
    joined = "\n".join(card._runtime_state_lines(state))
    assert "frontier_rerun_required: true" in joined
    assert "[15/16]" in joined


def test_banner_omits_progress_rather_than_printing_a_fake_zero(card):
    """No minimum recorded => print no counter at all.

    `[0/0]` would read as "nothing done, nothing required" — a third wrong
    answer rather than an absent one.
    """
    state = {"frontier_rerun_required": {"required": True, "reason": "era fence"}}
    joined = "\n".join(card._runtime_state_lines(state))
    assert "frontier_rerun_required: true" in joined
    assert "[" not in joined.split("frontier_rerun_required: true")[1].split("(")[0]
