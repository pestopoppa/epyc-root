"""B9 significance/throttle hygiene + B4 anti-ratchet + never-tested gate branches.

Covers (audit B9 / B4 / E3-TEST-2):
  * SG-9  throttle branch: violation→warning DEMOTION, NO host-state side effect,
          and detection-failure surfaced (not silently swallowed).
  * SEQ-3 bridge leg: a REFUTED rate axis blocks confirmation even under the advisory
          P0.2 bridge mode.
  * B4    update_baseline fail-closed when the sequential path is on but no verdict is
          available (seq_confirmed is None).
  * E3/TEST-2 gate-branch coverage: routing_diversity violation and _proxy_check.
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

import pytest
from safety_gate import EvalResult, SafetyGate  # type: ignore[import-not-found]
import scripts.autopilot.host_health as hh
from src.autopilot_core.authority_consent import (
    SEQ_P0_2_BRIDGE_CONSENT,
    SEQ_P0_2_BRIDGE_ENV,
)


def _result(quality=2.5, speed=99.0, tier=2, reliability=0.99, **kw) -> EvalResult:
    return EvalResult(
        tier=tier,
        quality=quality,
        speed=speed,
        cost=0.1,
        reliability=reliability,
        per_suite_quality=kw.pop("per_suite_quality", {"coder": quality}),
        routing_distribution=kw.pop("routing_distribution", {"worker": 1.0}),
        **kw,
    )


def _gate(tmp_path, **kw) -> SafetyGate:
    g = SafetyGate(baseline_path=tmp_path / "absent.yaml", **kw)
    g.baseline.frontdoor_speed = 1.0  # keep the throughput floor out of the way by default
    return g


class _FakeState:
    """Stand-in for HostHealthState.snapshot() with a controllable is_throttled()."""

    def __init__(self, throttled: bool, triggers: list[str]):
        self._t = (throttled, triggers)

    def is_throttled(self):
        return self._t


def _patch_snapshot(monkeypatch, factory):
    """Patch the class the GATE imports (scripts.autopilot.host_health.HostHealthState)."""
    monkeypatch.setattr(hh.HostHealthState, "snapshot", staticmethod(factory))


# ---------------------------------------------------------------------------
# SG-9 throttle branch
# ---------------------------------------------------------------------------
def test_throttle_demotes_violation_to_warning_with_reason(tmp_path, monkeypatch):
    _patch_snapshot(monkeypatch, lambda: _FakeState(True, ["cpu_freq_dip"]))
    g = _gate(tmp_path)
    g.baseline.frontdoor_speed = 100.0  # force result.speed (10) under the 0.8 floor
    verdict = g.check(_result(speed=10.0))

    assert verdict.passed is True, "a host-throttle stall must NOT force-revert a config"
    assert "throughput_throttle_demoted" in verdict.categories
    assert "exogenous_cache_flush" in verdict.categories
    assert "throughput" not in verdict.categories  # not a binding violation
    assert any("throttle_demoted" in w for w in verdict.warnings)


def test_throttle_branch_has_no_host_state_side_effect(tmp_path, monkeypatch):
    # SG-9(i): check() must not mutate host state (bare drop_caches pins NUMA pages).
    calls = {"remediate": 0, "rewarm": 0}
    monkeypatch.setattr(hh, "remediate", lambda *a, **k: calls.__setitem__("remediate", calls["remediate"] + 1) or True)
    monkeypatch.setattr(hh, "_numa_interleave_rewarm", lambda *a, **k: calls.__setitem__("rewarm", calls["rewarm"] + 1))
    _patch_snapshot(monkeypatch, lambda: _FakeState(True, ["cpu_freq_dip"]))
    g = _gate(tmp_path)
    g.baseline.frontdoor_speed = 100.0
    g.check(_result(speed=10.0))
    assert calls == {"remediate": 0, "rewarm": 0}, "gate must not remediate host state"


def test_throttle_detection_failure_is_logged_and_not_demoted(tmp_path, monkeypatch, caplog):
    # SG-9(iii): a broken detection import must surface (log.warning), not silently
    # disable throttle detection forever — the throughput violation stays binding.
    def _boom():
        raise RuntimeError("detector import broke")

    _patch_snapshot(monkeypatch, _boom)
    g = _gate(tmp_path)
    g.baseline.frontdoor_speed = 100.0
    with caplog.at_level(logging.WARNING, logger="autopilot.safety"):
        verdict = g.check(_result(speed=10.0))
    assert verdict.passed is False
    assert "throughput" in verdict.categories  # NOT demoted
    assert "throughput_throttle_demoted" not in verdict.categories
    assert any("detection failed" in r.getMessage() for r in caplog.records)


def test_no_throttle_keeps_binding_throughput_violation(tmp_path, monkeypatch):
    _patch_snapshot(monkeypatch, lambda: _FakeState(False, []))
    g = _gate(tmp_path)
    g.baseline.frontdoor_speed = 100.0
    verdict = g.check(_result(speed=10.0))
    assert verdict.passed is False
    assert "throughput" in verdict.categories
    assert "throughput_throttle_demoted" not in verdict.categories


# ---------------------------------------------------------------------------
# E3 / TEST-2 — never-tested gate branches
# ---------------------------------------------------------------------------
def test_routing_diversity_violation(tmp_path):
    g = _gate(tmp_path)
    verdict = g.check(_result(routing_distribution={"architect": 0.9}))
    assert verdict.passed is False
    assert "routing_diversity" in verdict.categories
    assert any("Routing diversity" in v for v in verdict.violations)


def test_proxy_only_improvement_is_flagged_as_warning(tmp_path):
    g = _gate(tmp_path)
    # _proxy_check reads the FLAT baseline.per_suite_quality (not the per-tier map).
    g.baseline.per_suite_quality = {"easy": 1.0, "hard": 2.0}
    verdict = g.check(_result(per_suite_quality={"easy": 1.3, "hard": 1.9}))
    assert verdict.passed is True  # proxy is advisory, never a violation
    assert any("Proxy-only improvement" in w for w in verdict.warnings)


# ---------------------------------------------------------------------------
# SEQ-3 — advisory bridge mode still blocks on a REFUTED rate axis
# ---------------------------------------------------------------------------
def _enable_bridge(tmp_path, monkeypatch):
    grant = tmp_path / "consent.json"
    grant.write_text(json.dumps({SEQ_P0_2_BRIDGE_CONSENT: "allow"}), encoding="utf-8")
    monkeypatch.setenv("AUTOPILOT_AUTHORITY_CONSENT_PATH", str(grant))
    monkeypatch.setenv(SEQ_P0_2_BRIDGE_ENV, "1")


def test_bridge_refuted_rate_axis_blocks_confirmation(tmp_path, monkeypatch):
    _enable_bridge(tmp_path, monkeypatch)
    g = SafetyGate(baseline_path=tmp_path / "absent.yaml", use_sequential=True)
    g.baseline.frontdoor_speed = 1.0
    verdict = g.check(
        _result(quality=2.5, speed=12.7, n_questions=2, question_results={"q1": True}),
        question_results={"q1": True},
        baseline_profile={"q1": 0.0},
        task_rate=0.1,  # << baseline → non-inferiority refuted
        baseline_task_rate=1.0,
        # z within the SEQ-3a validity domain (quality [-1, 1]); enough strong-positive
        # observations that the quality axis on its own would confirm.
        prior_quality_obs=[(i, 1.0) for i in range(20)],
        prior_rate_obs=[(i, -0.9) for i in range(8)],  # rate wealth stuck below budget
    )
    seq = verdict.seq
    assert seq is not None
    assert seq["rate_axis_binding"] is False, "bridge/advisory mode must be active"
    assert seq["E_quality"] >= 20.0, "quality axis on its own would confirm"
    # SEQ-3: a REFUTED rate axis blocks confirmation even though it is advisory.
    assert seq["state"] == "refuted"
    assert seq["confirmed"] is False
    assert "seq_refuted" in verdict.categories


# ---------------------------------------------------------------------------
# B4 / SEQ-2 — fail-closed when the sequential path is on but no verdict exists
# ---------------------------------------------------------------------------
def _promotion(**kw) -> EvalResult:
    d = dict(
        tier=2,
        quality=2.9,
        speed=99.0,
        cost=0.1,
        reliability=0.99,
        per_suite_quality={"coder": 2.9},
        n_questions=50,
        speed_metric_mode="aggregate_batch_tps",
    )
    d.update(kw)
    return EvalResult(**d)


def _bootstrap_eligible(g, monkeypatch):
    monkeypatch.setattr(g, "_baseline_eligible", lambda result: (True, "test-eligible", {"x": 1}))
    monkeypatch.setattr(SafetyGate, "_archive_best_quality", staticmethod(lambda tier=None: None))


def test_update_baseline_fails_closed_when_seq_inputs_unavailable(tmp_path, monkeypatch, caplog):
    g = SafetyGate(baseline_path=tmp_path / "absent.yaml", use_sequential=True)
    _bootstrap_eligible(g, monkeypatch)
    before = g.baseline.quality_for_tier(2)
    with caplog.at_level(logging.WARNING, logger="autopilot.safety"):
        res = g.update_baseline(_promotion(), seq_confirmed=None)  # inputs unavailable
    assert res.updated is False
    assert res.seq_refused_reason == "seq_inputs_unavailable"
    assert "REFUSED" in res.reason or "refused" in res.reason.lower()
    assert g.baseline.quality_for_tier(2) == before, "must not ratchet on unverifiable evidence"
    assert any("accumulate" in r.getMessage().lower() for r in caplog.records)


def test_update_baseline_seq_not_confirmed_tags_reason(tmp_path, monkeypatch):
    g = SafetyGate(baseline_path=tmp_path / "absent.yaml", use_sequential=True)
    _bootstrap_eligible(g, monkeypatch)
    res = g.update_baseline(_promotion(), seq_confirmed=False)
    assert res.updated is False
    assert res.seq_refused_reason == "seq_not_confirmed"


def test_update_baseline_flag_off_ignores_missing_seq(tmp_path, monkeypatch):
    # With the flag OFF, a None seq_confirmed must NOT block the legacy promotion path.
    g = SafetyGate(baseline_path=tmp_path / "absent.yaml")  # flag off
    _bootstrap_eligible(g, monkeypatch)
    res = g.update_baseline(_promotion(), seq_confirmed=None)
    assert res.updated is True
    assert res.seq_refused_reason == ""
