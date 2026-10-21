"""Unit tests for scripts/hooks/handoff_mass_deletion_warn.py (warn-only guard)."""
import importlib.util
import pathlib

_p = pathlib.Path(__file__).resolve().parents[1] / "handoff_mass_deletion_warn.py"
_s = importlib.util.spec_from_file_location("hmd", _p)
hmd = importlib.util.module_from_spec(_s)
_s.loader.exec_module(hmd)


def test_465954bc0_shape_warns():
    # 1234-line file, 892 deleted, nothing moved
    assert "892 of 1234" in hmd.evaluate(1234, 892, 0)


def test_small_edit_is_silent():
    assert hmd.evaluate(1234, 30, 0) is None


def test_below_threshold_is_silent():
    assert hmd.evaluate(1000, 200, 0) is None


def test_move_to_completed_is_silent():
    assert hmd.evaluate(1000, 600, 590) is None


def test_partial_move_still_warns():
    assert hmd.evaluate(1000, 600, 100) is not None


def test_empty_file_is_silent():
    assert hmd.evaluate(0, 0, 0) is None
