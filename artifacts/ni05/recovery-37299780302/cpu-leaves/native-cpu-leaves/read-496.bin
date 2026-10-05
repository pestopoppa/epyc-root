"""Tests for the offline memory-store growth curve instrument."""

import importlib.util
from pathlib import Path


_PATH = Path(__file__).parents[2] / "scripts" / "analysis" / "memory_store_growth_curve.py"
_SPEC = importlib.util.spec_from_file_location("memory_store_growth_curve", _PATH)
assert _SPEC and _SPEC.loader
curve = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(curve)


def test_per_window_rate_is_not_cumulative():
    report = curve.summarize_rows(
        [("1", "success"), ("2", "success"), ("3", "failure"), ("4", "failure")],
        2,
    )
    assert [window["success_rate"] for window in report["windows"]] == [1.0, 0.0]
    assert [window["cumulative_store_size"] for window in report["windows"]] == [2, 4]


def test_unknown_outcomes_are_not_scored():
    report = curve.summarize_rows([("1", "success"), ("2", None)], 2)
    window = report["windows"][0]
    assert window["scored_records"] == 1
    assert window["unknown_outcomes"] == 1
    assert window["success_rate"] == 1.0
