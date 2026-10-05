"""SafetyGate.update_baseline HARD eligibility gate (operator audit #3, 2026-05-27).

The autopilot's production baseline must not be written on a stale/wrong topology or with unknown
concurrent-speed semantics — the poisoning guard. Tests the AUTOPILOT's safety_gate
(scripts/autopilot/safety_gate.py — the module the autopilot imports), NOT src/safety_gate.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))
sys.path.insert(0, str(REPO_ROOT))  # for `import src.scheduling.contention` in the C5 test

import pytest
from safety_gate import EvalResult, SafetyGate  # type: ignore[import-not-found]


def _result(speed_metric_mode: str = "aggregate_batch_tps") -> EvalResult:
    # quality/per-suite must stay within the 0-3 scale; the loader + update_baseline
    # now reject out-of-scale values (see test_baseline_scale_guard.py).
    return EvalResult(tier=2, quality=2.9, speed=99.0, cost=0.1, reliability=0.99,
                      per_suite_quality={"coder": 2.9}, n_questions=50,
                      speed_metric_mode=speed_metric_mode)


def _repro_entry(
    quality: float = 2.9,
    speed: float = 88.0,
    cost: float = 0.2,
    reliability: float = 0.98,
    n_reproductions: int = 3,
) -> dict:
    return {
        "trial_id": 123,
        "objectives": (quality, speed, -cost, reliability),
        "n_reproductions": n_reproductions,
        "config_fingerprint": "fp-test",
    }


def test_baseline_refused_on_unrecognized_speed_mode(tmp_path):
    g = SafetyGate(baseline_path=tmp_path / "absent.yaml")  # default Baseline (quality=2.0)
    before = g.baseline.quality
    g.update_baseline(_result(speed_metric_mode="bogus_mode"))
    assert g.baseline.quality == before, "baseline must NOT update with an unrecognized speed mode"
    elig, reason, proof = g._baseline_eligible(_result(speed_metric_mode="bogus_mode"))
    assert not elig and "speed_metric_mode" in reason


def test_baseline_written_when_eligible(tmp_path, monkeypatch):
    g = SafetyGate(baseline_path=tmp_path / "absent.yaml")
    monkeypatch.setattr(g, "_baseline_eligible", lambda result: (True, "test-eligible", {"x": 1}))
    # Isolate from the live Pareto archive — bootstrap case where the archive-max guard is skipped.
    monkeypatch.setattr(SafetyGate, "_archive_best_quality", staticmethod(lambda tier=None: None))
    result = g.update_baseline(_result())
    assert result.updated
    assert g.baseline.quality_for_tier(2, strict=True) == pytest.approx(2.9), (
        "eligible result must write the same-tier baseline"
    )
    assert not (tmp_path / "absent.yaml").exists(), "baseline promotion is state-only, not YAML"


def test_baseline_refused_when_quality_exceeds_archive_max(tmp_path, monkeypatch):
    """A promotion whose quality exceeds the Pareto frontier max is a phantom/contaminated
    measurement (it was never archived) and must be refused — the 2026-05-31 gate-lock guard."""
    g = SafetyGate(baseline_path=tmp_path / "absent.yaml")
    before = g.baseline.quality
    monkeypatch.setattr(g, "_baseline_eligible", lambda result: (True, "test-eligible", {"x": 1}))
    # Archive max 2.400; the result claims 2.9 — never achieved, must be refused.
    monkeypatch.setattr(SafetyGate, "_archive_best_quality", staticmethod(lambda tier=None: 2.4))
    g.update_baseline(_result())  # quality=2.9
    assert g.baseline.quality == before, "baseline must NOT update above the archive max"


def test_baseline_written_when_reproduced_quality_within_archive_max(tmp_path, monkeypatch):
    """A promotion at/under the frontier max still needs reproduced representative evidence."""
    g = SafetyGate(baseline_path=tmp_path / "absent.yaml")
    monkeypatch.setattr(g, "_baseline_eligible", lambda result: (True, "test-eligible", {"x": 1}))
    monkeypatch.setattr(SafetyGate, "_archive_best_quality", staticmethod(lambda tier=None: 2.9))
    monkeypatch.setattr(
        SafetyGate, "_archive_frontier_entry", staticmethod(lambda source_trial_id, tier=None: _repro_entry())
    )
    result = g.update_baseline(_result(), source_trial_id=123)  # archive max 2.9 + n=3 evidence
    assert result.updated
    assert g.baseline.quality_for_tier(2, strict=True) == pytest.approx(2.9), (
        "reproduced result at the same-tier archive max must write"
    )


def test_baseline_refused_without_reproduced_frontier_evidence(tmp_path, monkeypatch):
    """A single frontier trial is not enough to ratchet the production baseline."""
    g = SafetyGate(baseline_path=tmp_path / "absent.yaml")
    monkeypatch.setattr(g, "_baseline_eligible", lambda result: (True, "test-eligible", {"x": 1}))
    monkeypatch.setattr(SafetyGate, "_archive_best_quality", staticmethod(lambda tier=None: 2.9))
    monkeypatch.setattr(
        SafetyGate,
        "_archive_frontier_entry",
        staticmethod(lambda source_trial_id, tier=None: _repro_entry(n_reproductions=1)),
    )
    result = g.update_baseline(_result(), source_trial_id=123)
    assert not result.updated
    assert "reproductions" in result.reason
    assert g.baseline.quality_for_tier(2, strict=True) is None


def test_baseline_update_is_monotonic_within_tier(tmp_path, monkeypatch):
    """A lower/equal same-tier quality must not replace the current state baseline."""
    g = SafetyGate(baseline_path=tmp_path / "absent.yaml")
    g.baseline.baselines_by_tier[2] = 2.4
    monkeypatch.setattr(g, "_baseline_eligible", lambda result: (True, "test-eligible", {"x": 1}))
    monkeypatch.setattr(SafetyGate, "_archive_best_quality", staticmethod(lambda tier=None: 2.9))
    lower = _result()
    lower.quality = 2.3
    result = g.update_baseline(lower)
    assert not result.updated
    assert "monotonic" in result.reason
    assert g.baseline.quality_for_tier(2, strict=True) == pytest.approx(2.4)


def test_archive_guard_is_same_tier(tmp_path, monkeypatch):
    """A T2 promotion checks the T2 frontier max, not an easier tier's max."""
    g = SafetyGate(baseline_path=tmp_path / "absent.yaml")
    monkeypatch.setattr(g, "_baseline_eligible", lambda result: (True, "test-eligible", {"x": 1}))
    monkeypatch.setattr(
        SafetyGate,
        "_archive_best_quality",
        staticmethod(lambda tier=None: 1.8 if tier == 2 else 2.9),
    )
    result = g.update_baseline(_result())
    assert not result.updated
    assert "same-tier archive max" in result.reason
    assert g.baseline.quality_for_tier(2, strict=True) is None


def test_baseline_state_round_trips_per_tier(tmp_path, monkeypatch):
    import safety_gate as sg  # type: ignore[import-not-found]

    g = SafetyGate(baseline_path=tmp_path / "absent.yaml")
    monkeypatch.setattr(g, "_baseline_eligible", lambda result: (True, "test-eligible", {"x": 1}))
    monkeypatch.setattr(SafetyGate, "_archive_best_quality", staticmethod(lambda tier=None: 2.9))
    # SG-4 (audit B3c): apply_state now applies load()'s above-archive-max guard to
    # state-sourced tier baselines too, reading the module-level Pareto frontier. Pin it
    # consistent with the archive max above so the round-tripped T2=2.9 baseline is NOT
    # dropped as over-max during restore (the guard reads the LIVE archive otherwise).
    monkeypatch.setattr(sg, "_pareto_frontier_best_quality", lambda tier=None: 2.9)
    monkeypatch.setattr(
        SafetyGate, "_archive_frontier_entry", staticmethod(lambda source_trial_id, tier=None: _repro_entry())
    )
    result = g.update_baseline(_result(), source_trial_id=123)
    assert result.updated

    restored = SafetyGate(
        baseline_path=tmp_path / "absent.yaml",
        baseline_state=g.baseline.to_state_dict(),
    )
    assert restored.baseline.quality_for_tier(2, strict=True) == pytest.approx(2.9)
    assert restored.baseline.per_suite_for_tier(2, strict=True)["coder"] == pytest.approx(2.9)


def test_baseline_state_overrides_all_live_scalar_authority(tmp_path, monkeypatch):
    """A complete state reseed must not retain stale scalars from frozen YAML."""
    import safety_gate as sg  # type: ignore[import-not-found]

    baseline_path = tmp_path / "baseline.yaml"
    baseline_path.write_text(
        "quality: 1.0\n"
        "speed: 10.0\n"
        "cost: 0.5\n"
        "reliability: 0.9\n"
        "frontdoor_speed: 9.0\n"
        "per_suite_quality: {old: 1.0}\n"
    )
    monkeypatch.setattr(sg, "_pareto_frontier_best_quality", lambda tier=None: None)
    state = {
        "quality": 1.75,
        "speed": 42.0,
        "cost": 0.25,
        "reliability": 0.98,
        "frontdoor_speed": 42.0,
        "per_suite_quality": {"new": 2.25},
        "baselines_by_tier": {"1": 1.75},
        "per_suite_quality_by_tier": {"1": {"new": 2.25}},
        "per_suite_counts_by_tier": {"1": {"new": 4}},
        "eval_quality_era": "E9-quality",
        "autopilot_speed_era": "E9-speed",
    }

    loaded = sg.Baseline.load(baseline_path, state=state)

    assert loaded.quality == 1.75
    assert loaded.speed == 42.0
    assert loaded.cost == 0.25
    assert loaded.reliability == 0.98
    assert loaded.frontdoor_speed == 42.0
    assert loaded.per_suite_quality == {"new": 2.25}
    assert loaded.to_state_dict() == state


def test_reproduced_promotion_uses_representative_median_and_refreshes_frontdoor_speed(
    tmp_path, monkeypatch
):
    """Accepted production-tier promotions use the representative median objectives."""
    g = SafetyGate(baseline_path=tmp_path / "absent.yaml")
    before_frontdoor = g.baseline.frontdoor_speed
    result = _result()
    result.tier = 1
    result.quality = 2.95
    result.speed = 99.0
    result.cost = 0.05
    result.reliability = 0.99
    monkeypatch.setattr(g, "_baseline_eligible", lambda r: (True, "test-eligible", {"x": 1}))
    monkeypatch.setattr(SafetyGate, "_archive_best_quality", staticmethod(lambda tier=None: 2.8))
    monkeypatch.setattr(
        SafetyGate, "_archive_frontier_trial_ids", staticmethod(lambda tier=None: frozenset({123}))
    )
    monkeypatch.setattr(
        SafetyGate,
        "_archive_frontier_entry",
        staticmethod(
            lambda source_trial_id, tier=None: _repro_entry(
                quality=2.8, speed=77.0, cost=0.25, reliability=0.96
            )
        ),
    )
    update = g.update_baseline(result, source_trial_id=123)
    assert update.updated
    assert update.new_quality == pytest.approx(2.8)
    assert g.baseline.quality_for_tier(1, strict=True) == pytest.approx(2.8)
    assert g.baseline.speed == pytest.approx(77.0)
    assert g.baseline.cost == pytest.approx(0.25)
    assert g.baseline.reliability == pytest.approx(0.96)
    assert g.baseline.frontdoor_speed != pytest.approx(before_frontdoor)
    assert g.baseline.frontdoor_speed == pytest.approx(77.0)


def test_baseline_refused_above_max_when_source_not_on_frontier(tmp_path, monkeypatch):
    """Archive-first ordering: an above-max promotion whose source trial is NOT yet on the
    frontier is refused even with a source_trial_id — the caller must archive.update() first."""
    g = SafetyGate(baseline_path=tmp_path / "absent.yaml")
    before = g.baseline.quality
    monkeypatch.setattr(g, "_baseline_eligible", lambda result: (True, "test-eligible", {"x": 1}))
    monkeypatch.setattr(SafetyGate, "_archive_best_quality", staticmethod(lambda tier=None: 2.4))
    monkeypatch.setattr(
        SafetyGate, "_archive_frontier_trial_ids", staticmethod(lambda tier=None: frozenset())
    )
    g.update_baseline(_result(), source_trial_id=999)  # quality 2.9, trial 999 not archived
    assert g.baseline.quality == before, "above-max promotion with unarchived source must be refused"


def test_loader_rejects_above_archive_baseline(tmp_path, monkeypatch):
    """Baseline.load() falls back to the default floor when the persisted quality exceeds the
    Pareto archive max — defense-in-depth, since the scale guard alone passes a 2.9 stub."""
    import safety_gate as sg  # type: ignore[import-not-found]
    p = tmp_path / "baseline.yaml"
    p.write_text("quality: 2.9\nspeed: 99.0\ncost: 0.1\nreliability: 0.99\n")
    monkeypatch.setattr(sg, "_pareto_frontier_best_quality", lambda tier=None: 2.4)
    b = sg.Baseline.load(p)
    assert b.quality == pytest.approx(sg.Baseline().quality), "above-archive baseline must fall back"


def test_loader_accepts_within_archive_baseline(tmp_path, monkeypatch):
    """An honest baseline below the archive max loads unchanged."""
    import safety_gate as sg  # type: ignore[import-not-found]
    p = tmp_path / "baseline.yaml"
    p.write_text("quality: 1.16\nspeed: 18.0\ncost: 0.5\nreliability: 0.86\n")
    monkeypatch.setattr(sg, "_pareto_frontier_best_quality", lambda tier=None: 2.4)
    b = sg.Baseline.load(p)
    assert b.quality == pytest.approx(1.16), "within-archive baseline must load unchanged"


def test_baseline_eligible_accepts_partition_filtered_speed_mode(tmp_path, monkeypatch):
    """C5 (commit 9204d6b7): when audit-shadow / tool_sentinel partitions are excluded from
    the decision subset, eval_tower stamps `median_request_tps_partition_filtered` — a
    provenance marker on the SAME metric (median request TPS over the decision subset), not a
    new instrument. _baseline_eligible must accept it; otherwise the documented-default regime
    (audit blocks active) refuses EVERY baseline write — an unintended total ratchet freeze."""
    import src.scheduling.contention as contention  # type: ignore[import-not-found]

    g = SafetyGate(baseline_path=tmp_path / "absent.yaml")
    # Force a certified-fresh matrix against the live topology so eligibility hinges on the mode.
    monkeypatch.setattr(contention, "load_contention_matrix", lambda *a, **k: object())
    monkeypatch.setattr(contention, "topology_fingerprint_for_matrix", lambda *a, **k: "live-hash")
    monkeypatch.setattr(contention, "matrix_status", lambda *a, **k: contention.MatrixStatus.OK)

    elig, reason, proof = g._baseline_eligible(
        _result(speed_metric_mode="median_request_tps_partition_filtered")
    )
    assert elig, f"partition-filtered mode must be eligible with a healthy matrix: {reason}"
    assert proof["speed_metric_mode"] == "median_request_tps_partition_filtered"
    assert proof.get("matrix_status") == "ok"

    # A genuinely unknown mode still refuses at the mode gate (suffix strip is exact).
    elig2, reason2, _ = g._baseline_eligible(_result(speed_metric_mode="totally_bogus"))
    assert not elig2 and "speed_metric_mode" in reason2


def test_baseline_eligibility_is_explicit_decision_with_proof(tmp_path):
    """Eligibility must be a deliberate bool decision carrying topology/matrix proof (or an error
    reason) — never eligible-by-default. Fail-closed when the live topology/matrix is unverifiable."""
    g = SafetyGate(baseline_path=tmp_path / "absent.yaml")
    elig, reason, proof = g._baseline_eligible(_result(speed_metric_mode="aggregate_batch_tps"))
    assert isinstance(elig, bool)
    assert proof.get("speed_metric_mode") == "aggregate_batch_tps"
    assert ("matrix_status" in proof) or ("error" in proof), "must record topology/matrix proof or error"
