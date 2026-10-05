"""EV-14c: the baseline last-write-wins collapse is a defect, and it is closed.

Pre-fix, ``Baseline.update_tier()`` wrote with ``dict.update`` semantics: a re-score
of the same suite silently overwrote the prior baseline with no record that one
existed — the collapse point that gates decisions, and the corruption path for
EV-14a the moment repeat scoring exists. Post-fix:

  * every write that changes the T<tier> reference identity (tier quality, a
    per-suite entry, a per-suite count) bumps a per-tier monotonic REVISION and
    logs an explicit BASELINE MOVED line naming prior -> new — never silent;
  * a measurement window pins the reference BEFORE it starts (``pin_tier``) and
    detects a move afterwards (``pin_moved``) — a band measured against a
    reference that moved mid-window is INVALID, never "no change";
  * ``update_tier`` names the registered windows it invalidates at write time;
  * ``update_baseline`` refuses to write when its own compare-to-write span saw
    the reference move — the promotion verdict cannot be a compare-to-ghost;
  * revisions persist through load/save/apply_state/to_state_dict, so a restart
    cannot hide a move, and a legacy baseline's state payload stays byte-identical.

Tests the AUTOPILOT's safety_gate (scripts/autopilot/safety_gate.py).
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

import pytest
from safety_gate import (  # type: ignore[import-not-found]
    Baseline,
    BaselinePin,
    EvalResult,
    SafetyGate,
)


def _gate(tmp_path) -> SafetyGate:
    g = SafetyGate(baseline_path=tmp_path / "absent.yaml")
    g.baseline.frontdoor_speed = 1.0
    return g


def _result(quality: float, tier: int = 2, reliability: float = 0.99) -> EvalResult:
    return EvalResult(
        tier=tier,
        quality=quality,
        speed=99.0,
        cost=0.1,
        reliability=reliability,
        speed_metric_mode="aggregate_batch_tps",
        n_questions=50,
        per_suite_quality={"math": quality},
        per_suite_counts={"math": 50},
        routing_distribution={"worker": 1.0},
    )


# ── the move is explicit, never silent ────────────────────────────────────────

def test_update_tier_overwrite_bumps_revision_and_logs_moved(tmp_path, caplog):
    g = _gate(tmp_path)
    g.baseline.update_tier(_result(1.5, tier=2))
    assert g.baseline.tier_revision(2) == 1
    caplog.clear()
    g.baseline.update_tier(_result(1.7, tier=2))
    assert g.baseline.tier_revision(2) == 2, "a re-score must bump the revision"
    assert any("BASELINE MOVED T2" in rec.message for rec in caplog.records), \
        "the overwrite must be recorded, not silent"
    moved = next(rec.message for rec in caplog.records if "BASELINE MOVED T2" in rec.message)
    assert "1.500" in moved and "1.700" in moved, "the log must name prior -> new"


def test_per_suite_overwrite_bumps_revision_even_when_tier_quality_unchanged(tmp_path, caplog):
    g = _gate(tmp_path)
    g.baseline.update_tier(_result(1.5, tier=2))
    assert g.baseline.tier_revision(2) == 1
    caplog.clear()
    same_quality = _result(1.5, tier=2)
    same_quality.per_suite_quality = {"math": 1.2}  # same tier scalar, moved suite entry
    g.baseline.update_tier(same_quality)
    assert g.baseline.tier_revision(2) == 2, "a per-suite move is a reference move too"
    assert any("suite 'math'" in rec.message and "1.500" in rec.message and "1.200" in rec.message
               for rec in caplog.records)


def test_noop_write_does_not_bump_revision(tmp_path):
    g = _gate(tmp_path)
    g.baseline.update_tier(_result(1.5, tier=2))
    g.baseline.update_tier(_result(1.5, tier=2))
    assert g.baseline.tier_revision(2) == 1, "an identical re-score is not a move"


# ── the pin: a moved reference is detected, never silently read as stable ──────

def test_pin_detects_a_reference_moved_after_pinning(tmp_path):
    g = _gate(tmp_path)
    g.baseline.update_tier(_result(1.5, tier=2))
    pin = g.baseline.pin_tier(2)
    assert not g.baseline.pin_moved(pin), "no writes after pin -> reference stable"
    g.baseline.update_tier(_result(1.7, tier=2))
    assert g.baseline.pin_moved(pin), "a re-score mid-window must register as moved"


def test_pin_captures_the_full_reference_identity(tmp_path):
    g = _gate(tmp_path)
    g.baseline.update_tier(_result(1.5, tier=2))
    pin = g.baseline.pin_tier(2)
    assert pin.tier == 2
    assert pin.quality == pytest.approx(1.5)
    assert pin.per_suite_quality == {"math": 1.5}
    assert pin.per_suite_counts == {"math": 50}
    assert pin.revision == 1
    assert pin.eval_quality_era == ""


def test_update_tier_names_the_live_pin_it_invalidates(tmp_path, caplog):
    g = _gate(tmp_path)
    g.baseline.update_tier(_result(1.5, tier=2))
    g.baseline.pin_tier(2, pin_id="band-math-window")
    caplog.clear()
    g.baseline.update_tier(_result(1.7, tier=2))
    moved = next(rec.message for rec in caplog.records if "BASELINE MOVED T2" in rec.message)
    assert "band-math-window" in moved, "the write must name the window it invalidates"


# ── update_baseline refuses a compare-to-ghost write ─────────────────────────

def test_update_baseline_refuses_when_reference_moved_mid_promotion(tmp_path, monkeypatch):
    """If the tier reference moved between promotion start and write, the verdict
    compared against a reference that no longer exists — refuse, don't write."""
    g = _gate(tmp_path)
    g.baseline.update_tier(_result(1.5, tier=2))
    g.baseline.tier_revisions[2] = 7  # a move happened just before this promotion
    monkeypatch.setattr(g, "_baseline_eligible", lambda result: (True, "test-eligible", {}))
    monkeypatch.setattr(SafetyGate, "_archive_best_quality", staticmethod(lambda tier=None: None))
    # Entry pin carries the STALE revision, as if captured before the interleaved move.
    monkeypatch.setattr(
        g.baseline,
        "pin_tier",
        lambda tier, pin_id=None, *, register=True: BaselinePin(
            tier=tier,
            quality=1.5,
            per_suite_quality={"math": 1.5},
            per_suite_counts={"math": 50},
            revision=6,
            eval_quality_era="",
        ),
    )
    res = g.update_baseline(_result(1.9, tier=2))
    assert not res.updated
    assert "moved" in res.reason and "revision" in res.reason
    assert g.baseline.quality_for_tier(2, strict=True) == pytest.approx(1.5), \
        "the refusal must leave the baseline untouched"


def test_update_baseline_normal_promotion_still_writes(tmp_path, monkeypatch):
    g = _gate(tmp_path)
    g.baseline.update_tier(_result(1.5, tier=2))
    monkeypatch.setattr(g, "_baseline_eligible", lambda result: (True, "test-eligible", {}))
    monkeypatch.setattr(SafetyGate, "_archive_best_quality", staticmethod(lambda tier=None: None))
    res = g.update_baseline(_result(1.9, tier=2))
    assert res.updated
    assert g.baseline.quality_for_tier(2, strict=True) == pytest.approx(1.9)
    assert g.baseline.tier_revision(2) == 2, "the promotion itself is a recorded move"


# ── persistence: a restart cannot hide a move, legacy payloads stay identical ──

def test_state_round_trip_preserves_tier_revisions(tmp_path):
    g = _gate(tmp_path)
    g.baseline.update_tier(_result(1.5, tier=2))
    g.baseline.update_tier(_result(1.7, tier=2))
    state = g.baseline.to_state_dict()
    assert state["tier_revisions"] == {"2": 2}
    loaded = Baseline(source_path=tmp_path / "absent.yaml")
    loaded.apply_state(state)
    assert loaded.tier_revision(2) == 2, "a restart must not reset the move counter"


def test_legacy_baseline_state_payload_has_no_revision_key(tmp_path):
    b = Baseline(source_path=tmp_path / "absent.yaml")
    assert "tier_revisions" not in b.to_state_dict(), \
        "a legacy (pre-EV-14c) payload must stay byte-identical"


def test_revisions_survive_a_file_save_and_load(tmp_path):
    g = _gate(tmp_path)
    g.baseline.update_tier(_result(1.5, tier=2))
    path = tmp_path / "baseline.yaml"
    g.baseline.save(path)
    loaded = Baseline.load(path)
    assert loaded.tier_revision(2) == 1
