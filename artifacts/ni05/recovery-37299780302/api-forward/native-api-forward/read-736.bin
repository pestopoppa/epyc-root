"""B8 / SG-0: loud baseline-ratchet freeze.

When _baseline_eligible refuses a write (a stale or unverifiable contention matrix), the
baseline ratchet is FROZEN — nothing can promote until the operator re-measures the matrix.
update_baseline surfaces this as:
  - a log.error (not a quiet warning) carrying the reason + remediation, and
  - BaselineUpdateResult.ineligible_reason (non-empty ONLY on the freeze path, so a caller
    can tell "ratchet frozen, go re-measure" apart from "candidate simply not better").
A pre-expiry countdown warns while the matrix is still fresh but within
PRE_EXPIRY_WARN_DAYS of the staleness wall.

Tests the AUTOPILOT's safety_gate (scripts/autopilot/safety_gate.py).
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

import pytest
import safety_gate as sg  # type: ignore[import-not-found]
from safety_gate import EvalResult, SafetyGate  # type: ignore[import-not-found]

import src.scheduling.contention as contention


def _result() -> EvalResult:
    return EvalResult(
        tier=2, quality=2.9, speed=99.0, cost=0.1, reliability=0.99,
        per_suite_quality={"coder": 2.9}, n_questions=50,
        speed_metric_mode="aggregate_batch_tps",
    )


_STALE_REASON = "matrix not certified-fresh (status=stale)"


def test_ineligible_carries_reason_and_logs_error(tmp_path, monkeypatch, caplog):
    g = SafetyGate(baseline_path=tmp_path / "absent.yaml")
    # Stand in for a stale contention matrix: _baseline_eligible returns ineligible.
    monkeypatch.setattr(
        g, "_baseline_eligible",
        lambda result: (False, _STALE_REASON, {"matrix_status": "stale"}),
    )
    with caplog.at_level(logging.ERROR, logger="autopilot.safety"):
        res = g.update_baseline(_result())

    assert res.updated is False
    assert res.ineligible_reason == _STALE_REASON
    errors = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert errors, "a frozen ratchet must log at ERROR, not warning"
    joined = " ".join(r.getMessage() for r in errors)
    assert _STALE_REASON in joined
    assert "re-measure" in joined and "contention matrix" in joined


def test_eligible_write_has_empty_ineligible_reason(tmp_path, monkeypatch):
    g = SafetyGate(baseline_path=tmp_path / "absent.yaml")
    monkeypatch.setattr(g, "_baseline_eligible", lambda result: (True, "ok", {}))
    monkeypatch.setattr(SafetyGate, "_archive_best_quality", staticmethod(lambda tier=None: None))
    res = g.update_baseline(_result())
    assert res.updated is True
    assert res.ineligible_reason == ""


def test_not_better_skip_has_empty_ineligible_reason(tmp_path, monkeypatch):
    """A non-freeze skip (candidate not a monotonic improvement) must NOT set
    ineligible_reason — the field distinguishes 'ratchet frozen' from 'not better'."""
    g = SafetyGate(baseline_path=tmp_path / "absent.yaml")
    g.baseline.baselines_by_tier[2] = 2.4
    monkeypatch.setattr(g, "_baseline_eligible", lambda result: (True, "ok", {}))
    monkeypatch.setattr(SafetyGate, "_archive_best_quality", staticmethod(lambda tier=None: 2.9))
    lower = _result()
    lower.quality = 2.3
    res = g.update_baseline(lower)
    assert res.updated is False
    assert "monotonic" in res.reason
    assert res.ineligible_reason == ""


# ── pre-expiry countdown ──────────────────────────────────────────────────────

def _write_matrix(tmp_path: Path, age_days: float) -> Path:
    p = tmp_path / "contention_matrix.yaml"
    p.write_text("schema: test\n")
    mtime = os.path.getmtime(p) - age_days * 86400.0
    import time as _t
    now = _t.time()
    os.utime(p, (now, now - age_days * 86400.0))
    return p


def test_pre_expiry_warning_fires_within_window(tmp_path, monkeypatch, caplog):
    p = _write_matrix(tmp_path, age_days=25.0)  # 30-day wall → ~5 days remaining
    monkeypatch.setattr(contention, "DEFAULT_MATRIX_PATH", p)
    monkeypatch.setattr(contention, "MATRIX_STALENESS_DAYS", 30)
    with caplog.at_level(logging.WARNING, logger="autopilot.safety"):
        sg._warn_matrix_pre_expiry()
    assert any("freezes in ~" in r.getMessage() for r in caplog.records)


def test_no_pre_expiry_warning_when_fresh(tmp_path, monkeypatch, caplog):
    p = _write_matrix(tmp_path, age_days=1.0)  # ~29 days remaining, well outside window
    monkeypatch.setattr(contention, "DEFAULT_MATRIX_PATH", p)
    monkeypatch.setattr(contention, "MATRIX_STALENESS_DAYS", 30)
    with caplog.at_level(logging.WARNING, logger="autopilot.safety"):
        sg._warn_matrix_pre_expiry()
    assert not any("freezes in ~" in r.getMessage() for r in caplog.records)


def test_no_pre_expiry_warning_when_already_past_wall(tmp_path, monkeypatch, caplog):
    """Past the wall the matrix is already STALE (handled by the ineligible/log.error path);
    the countdown does not double-warn on a negative remaining."""
    p = _write_matrix(tmp_path, age_days=40.0)  # remaining ~-10 days
    monkeypatch.setattr(contention, "DEFAULT_MATRIX_PATH", p)
    monkeypatch.setattr(contention, "MATRIX_STALENESS_DAYS", 30)
    with caplog.at_level(logging.WARNING, logger="autopilot.safety"):
        sg._warn_matrix_pre_expiry()
    assert not any("freezes in ~" in r.getMessage() for r in caplog.records)


def test_pre_expiry_is_fail_soft_when_matrix_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(contention, "DEFAULT_MATRIX_PATH", tmp_path / "nope.yaml")
    sg._warn_matrix_pre_expiry()  # must not raise
