#!/usr/bin/env python3
"""Tests for autopilot_precondition_gate.py (C2).

Pure — no live probing, no model. Feeds hand-built entry + load-signal dicts to
``check_autopilot_precondition`` and asserts the consistency verdict.

Run:
    /mnt/raid0/llm/epyc-orchestrator/.venv/bin/python -m pytest \
        scripts/coordination/tests/test_autopilot_precondition_gate.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import autopilot_precondition_gate as gate  # noqa: E402


def _entry(autopilot):
    return {"task_id": "t1", "preconditions": {"autopilot": autopilot}}


def _signals(running):
    # Shape of inference_load_check.collect_signals(): top-level 'autopilot'.
    return {"autopilot": {"running": running}}


# --------------------------------------------------------------------------- #
# stopped vs running consistency
# --------------------------------------------------------------------------- #
def test_c2_stopped_requirement_ok_when_stopped():
    ok, reason = gate.check_autopilot_precondition(_entry("stopped"), _signals(False))
    assert ok is True
    assert "stopped" in reason


def test_c2_stopped_requirement_fails_when_running():
    ok, reason = gate.check_autopilot_precondition(_entry("stopped"), _signals(True))
    assert ok is False
    assert "requires autopilot stopped" in reason


def test_c2_running_requirement_ok_when_running():
    ok, _ = gate.check_autopilot_precondition(_entry("running"), _signals(True))
    assert ok is True


def test_c2_running_requirement_fails_when_stopped():
    ok, reason = gate.check_autopilot_precondition(_entry("running"), _signals(False))
    assert ok is False
    assert "requires autopilot running" in reason


# --------------------------------------------------------------------------- #
# 'any' passthrough + unconfirmed conservatism
# --------------------------------------------------------------------------- #
def test_c2_any_passthrough_regardless_of_signal():
    for running in (True, False, None):
        ok, _ = gate.check_autopilot_precondition(_entry("any"), _signals(running))
        assert ok is True


def test_c2_absent_precondition_defaults_to_any():
    ok, _ = gate.check_autopilot_precondition({"task_id": "t"}, _signals(True))
    assert ok is True


def test_c2_unconfirmed_signal_fails_stopped_and_running():
    for req in ("stopped", "running"):
        ok, reason = gate.check_autopilot_precondition(_entry(req), _signals(None))
        assert ok is False
        assert "unconfirmed" in reason


def test_c2_unknown_precondition_value_rejected():
    ok, reason = gate.check_autopilot_precondition(_entry("maybe"), _signals(True))
    assert ok is False
    assert "not one of" in reason


def test_c2_accepts_full_classify_load_shape():
    # classify_load() nests signals under a 'signals' key — the helper must dig in.
    full = {"state": "busy", "signals": {"autopilot": {"running": True}}}
    ok, _ = gate.check_autopilot_precondition(_entry("running"), full)
    assert ok is True


def test_c2_missing_autopilot_signal_is_unconfirmed():
    ok, reason = gate.check_autopilot_precondition(_entry("stopped"), {})
    assert ok is False
    assert "unconfirmed" in reason
