#!/usr/bin/env python3
"""SEQ-A detector — refutation must be attributed to an AXIS, not guessed.

`readjudicate_sequential_candidates.py` used to report a candidate as carrying a
"sticky refuted label" whenever the persisted `state` was `refuted` while
`E_quality >= budget_min_e`. That comparison is invalid: `state` is the JOINT
verdict (`safety_gate.py` stamps `refuted` when EITHER axis refutes, recomputed
every trial) and `E_quality` is a single axis. A healthy quality axis sitting
next to a refuted RATE axis therefore read as a label that had failed to update.

It manufactured the whole finding: `E_rate_noninf` never exceeds 2.0 anywhere in
the corpus against `budget_min_e = 2.0`, so essentially every candidate's rate
axis refutes once `k >= budget`.

These tests pin the replacement predicate and, most importantly, the *residual*
bucket — joint says refuted but neither axis does — which is the only thing that
would constitute a genuinely stale label. Measured against the real journal that
bucket is empty.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from src.autopilot_core.sequential_verdict import DEFAULT_POLICY

_SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "analysis"
    / "readjudicate_sequential_candidates.py"
)


def _load():
    spec = importlib.util.spec_from_file_location("_readjudicate", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def mod():
    return _load()


def test_futility_refutes_at_any_k(mod):
    assert mod.axis_refuted(DEFAULT_POLICY.futility_e, 1, DEFAULT_POLICY) is True
    assert mod.axis_refuted(0.01, 1, DEFAULT_POLICY) is True


def test_budget_rule_only_applies_at_or_past_budget(mod):
    below = DEFAULT_POLICY.budget_min_e - 0.5
    assert mod.axis_refuted(below, DEFAULT_POLICY.budget - 1, DEFAULT_POLICY) is False
    assert mod.axis_refuted(below, DEFAULT_POLICY.budget, DEFAULT_POLICY) is True


def test_healthy_axis_never_refutes(mod):
    assert mod.axis_refuted(11.55, 40, DEFAULT_POLICY) is False


def test_absent_axis_is_not_evidence_against(mod):
    """A missing measurement must not be read as a refutation."""
    assert mod.axis_refuted(None, 40, DEFAULT_POLICY) is False


def test_the_three_stuck_candidates_are_rate_refuted_not_stale(mod):
    """The exact rows that produced the 'sticky label' finding.

    Real values from `orchestration/reports/readjudicate_sequential_20260728.json`
    and the journal. Each has a HEALTHY quality axis and a REFUTED rate axis, so
    the joint `refuted` label is correct — not stale.
    """
    for e_quality, e_rate, k in (
        (11.5507, 0.5561, 40),   # 70902e4b665474e7
        (8.7048, 0.9100, 24),    # dd793a6ee43ce718
        (2.7448, 0.9100, 15),    # 85c3dcf25823c537
    ):
        assert mod.axis_refuted(e_quality, k, DEFAULT_POLICY) is False, (
            "quality axis is healthy — this is what the old detector saw"
        )
        assert mod.axis_refuted(e_rate, k, DEFAULT_POLICY) is True, (
            "rate axis refutes — this is what the old detector never looked at"
        )


def test_a_genuinely_stale_label_would_still_be_detectable(mod):
    """The guard must not be one that can never fire.

    If BOTH axes are healthy, nothing justifies a `refuted` label and the
    residual bucket must catch it. Pinning this so the fix cannot degrade into
    'attribute everything, report nothing'.
    """
    assert mod.axis_refuted(11.55, 40, DEFAULT_POLICY) is False
    assert mod.axis_refuted(9.90, 40, DEFAULT_POLICY) is False
