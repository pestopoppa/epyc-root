"""Tests for J9/HLE observe-only metric computation."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

from hle_metrics import (  # noqa: E402
    compute_hle_observe_payload,
    infer_control_attestation,
    infer_oracle_adequacy,
)
from safety_gate import EvalResult  # noqa: E402


def _result(**overrides) -> EvalResult:
    base = {
        "tier": 1,
        "quality": 2.4,
        "speed": 20.0,
        "cost": 0.2,
        "reliability": 0.9,
        "per_suite_quality": {"hotpotqa": 2.1, "humaneval": 2.7},
        "n_questions": 20,
        "details": {"correct": 16, "total": 20, "errors": 1},
        "partial_count": 1,
        "degraded_count": 0,
    }
    base.update(overrides)
    return EvalResult(**base)


def test_hle_payload_computes_observe_only_axes_from_trial_evidence() -> None:
    payload = compute_hle_observe_payload(
        _result(n_exogenous_recovered=2, n_exogenous_unrecovered=1),
        action={"type": "numeric_trial", "surface": "routing_threshold"},
        verdict=SimpleNamespace(violations=[], warnings=[]),
        failure_analysis="",
        prior_criticism="Next directions: tune routing threshold after quality_floor",
        recent_traces="ROLE frontdoor\nPROMPT x\nRESPONSE y\n",
    )

    metrics = payload["harness_metrics"]
    axes = metrics["axes"]

    assert payload["metric_schema_version"] == 1
    assert metrics["observe_only"] is True
    assert axes["execution_fidelity"]["score"] > 0.7
    assert axes["execution_fidelity"]["evidence_event_ids"] == []
    assert axes["feedback_interpretation"]["missing"] is False
    assert axes["memory_coherence"]["score"] == 1.0
    assert axes["recovery_rate"]["score"] == 0.6667


def test_hle_payload_keeps_missing_axes_explicit() -> None:
    payload = compute_hle_observe_payload(
        _result(details={}, n_questions=0, quality=0.0, reliability=0.0),
        verdict=SimpleNamespace(violations=["quality_floor"], warnings=[]),
        prior_criticism="(first trial -- no prior criticism)",
        recent_traces="",
    )

    axes = payload["harness_metrics"]["axes"]

    assert axes["execution_fidelity"]["missing"] is True
    assert axes["feedback_interpretation"]["missing"] is True
    assert axes["memory_coherence"]["missing"] is True
    assert axes["recovery_rate"]["missing"] is True
    assert "execution_fidelity" in payload["harness_metrics"]["summary"]["missing_axes"]


def test_oracle_adequacy_registers_profiles_for_observed_suites() -> None:
    oracle = infer_oracle_adequacy(_result())

    assert oracle["observe_only"] is True
    assert oracle["suites"]["hotpotqa"]["oracle_type"] == "short_answer_f1_or_exact"
    assert oracle["suites"]["hotpotqa"]["shortcut_risk"] == "high"
    assert oracle["suites"]["humaneval"]["oracle_type"] == "unit_test"
    assert oracle["suites"]["humaneval"]["deterministic"] is True
    assert oracle["control_attestation"]["status"] == "disabled"


def test_control_attestation_default_off(monkeypatch) -> None:
    monkeypatch.delenv("AUTOPILOT_ORACLE_CONTROL_ATTESTATION", raising=False)

    attestation = infer_control_attestation(
        _result(
            details={
                "oracle_control_pairs": {
                    "known_good": [{"suite": "humaneval", "passed": True}],
                    "known_bad": [{"suite": "humaneval", "passed": False}],
                }
            }
        )
    )

    assert attestation["status"] == "disabled"
    assert attestation["observe_only"] is True
    assert attestation["eligible_for_evidence"] is False


def test_control_attestation_reports_passed_pair_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv("AUTOPILOT_ORACLE_CONTROL_ATTESTATION", "1")

    attestation = infer_control_attestation(
        _result(
            details={
                "oracle_control_pairs": {
                    "known_good": [{"suite": "humaneval", "passed": True}],
                    "known_bad": [{"suite": "humaneval", "passed": False}],
                }
            }
        )
    )

    assert attestation["status"] == "passed"
    assert attestation["controls_seen"] == {"known_good": 1, "known_bad": 1}
    assert attestation["suites"] == ["humaneval"]
    assert attestation["failures"] == []


def test_control_attestation_reports_failed_or_incomplete_controls(monkeypatch) -> None:
    monkeypatch.setenv("AUTOPILOT_ORACLE_CONTROL_ATTESTATION", "1")

    failed = infer_control_attestation(
        _result(
            details={
                "oracle_control_pairs": [
                    {"kind": "known_good", "suite": "qa", "passed": True},
                    {"kind": "known_bad", "suite": "qa", "passed": True},
                ]
            }
        )
    )
    incomplete = infer_control_attestation(
        _result(
            details={
                "oracle_control_pairs": {
                    "known_good": [{"suite": "qa", "passed": True}],
                }
            }
        )
    )

    assert failed["status"] == "failed"
    assert failed["failures"][0]["expected_accept"] is False
    assert failed["failures"][0]["observed_accept"] is True
    assert incomplete["status"] == "incomplete"
