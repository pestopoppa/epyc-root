from __future__ import annotations

from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from scripts.autopilot import collect_e9_operational_baseline as collector
from scripts.autopilot import run_operational_baseline_diagnostic as diagnostic


REPO_ROOT = Path(__file__).resolve().parents[2]


def _result(**overrides):
    values = {
        "tier": 1,
        "quality": 1.8,
        "speed": 55.0,
        "cost": 0.25,
        "reliability": 0.99,
        "per_suite_quality": {"general": 2.0},
        "per_suite_counts": {"general": 4},
        "n_questions": collector.EVAL_T1_SPEC_N,
        "eval_concurrency": 6,
        "speed_metric_mode": "aggregate_batch_tps",
        "question_results": [],
        "details": {
            "eval_execution_instrument_id": collector.EVAL_EXECUTION_INSTRUMENT_ID,
            "eval_scoring_schedule_id": collector.EVAL_SCORING_SCHEDULE_ID,
            "task_rate_qph": 120.0,
            "eval_contaminated_by_abandoned_requests": False,
        },
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_candidate_is_fresh_t1_only_and_stamps_both_eras():
    candidate = collector.candidate_baseline_state(_result())

    assert candidate["baselines_by_tier"] == {"1": 1.8}
    assert candidate["per_suite_quality_by_tier"] == {"1": {"general": 2.0}}
    assert candidate["per_suite_counts_by_tier"] == {"1": {"general": 4}}
    assert candidate["frontdoor_speed"] == 55.0
    assert candidate["eval_quality_era"] == collector.QUALITY_ERA
    assert candidate["autopilot_speed_era"] == collector.SPEED_ERA


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"eval_concurrency": 1}, "resource lanes inactive"),
        ({"speed_metric_mode": "median_request_tps"}, "speed_metric_mode"),
        ({"reliability": 0.79}, "reliability"),
        ({"n_questions": 50}, "n_questions"),
    ],
)
def test_result_gate_fails_closed(overrides, message):
    with pytest.raises(RuntimeError, match=message):
        collector._validate_result(_result(**overrides))


def test_instrument_state_requires_ratified_e9_ids():
    state = {
        "pareto_objective_policy": collector.POLICY,
        "eval_execution_instrument_id": collector.EVAL_EXECUTION_INSTRUMENT_ID,
        "eval_scoring_schedule_id": collector.EVAL_SCORING_SCHEDULE_ID,
        "active_instrument_eras": {
            "eval_quality": collector.QUALITY_ERA,
            "autopilot_speed": collector.SPEED_ERA,
        },
    }
    collector._validate_instrument_state(state)

    state["eval_execution_instrument_id"] = "old"
    with pytest.raises(RuntimeError, match="execution_instrument"):
        collector._validate_instrument_state(state)


def test_source_hashes_bind_files_not_repository_head(monkeypatch, tmp_path: Path):
    source = tmp_path / "instrument.py"
    source.write_text("stable\n", encoding="utf-8")
    monkeypatch.setattr(collector, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(collector, "SOURCE_PATHS", (source,))

    before = collector._source_hashes()
    # An unrelated file (and therefore an unrelated commit) is outside the
    # measurement trust boundary.
    (tmp_path / "dashboard.py").write_text("changed\n", encoding="utf-8")
    assert collector._source_hashes() == before

    source.write_text("drifted\n", encoding="utf-8")
    assert collector._source_hashes() != before


def test_generation_probe_requires_explicit_real_inference_attestation():
    assert (
        collector._validate_generation_probe_response(
            {"answer": "4", "mock_mode": False, "real_mode": True}
        )
        == "4"
    )

    with pytest.raises(RuntimeError, match="did not attest real inference"):
        collector._validate_generation_probe_response(
            {"answer": "4", "mock_mode": True, "real_mode": False}
        )

    with pytest.raises(RuntimeError, match="mock content"):
        collector._validate_generation_probe_response(
            {"answer": "[MOCK] 4", "mock_mode": False, "real_mode": True}
        )


def test_result_gate_rejects_scorer_infrastructure_errors_at_reliability_floor():
    result = _result(
        reliability=0.80,
        question_results=[
            {
                "error": True,
                "error_detail": "scoring_unavailable: llm_judge_transport_timeout",
            }
        ],
    )

    with pytest.raises(RuntimeError, match="scorer-infrastructure"):
        collector._validate_result(result)


def test_diagnostic_gate_rejects_any_error_even_when_canonical_gate_allows_it():
    result = _result(
        reliability=0.99,
        details={
            **_result().details,
            "errors": 1,
            "scoring_errors": 1,
            "eval_client_transport_timeout_count": 1,
        },
    )

    collector._validate_result(result)
    with pytest.raises(RuntimeError, match="diagnostic is not clean"):
        diagnostic._validate_clean_result(result)


def test_diagnostic_gate_accepts_only_error_free_full_reliability():
    result = _result(
        reliability=1.0,
        details={
            **_result().details,
            "errors": 0,
            "scoring_errors": 0,
            "eval_client_transport_timeout_count": 0,
            "eval_backend_drain_failure_count": 0,
            "eval_orphan_contamination_count": 0,
        },
    )

    diagnostic._validate_clean_result(result)


def test_diagnostic_source_hashes_include_admission_runner():
    hashes = diagnostic._diagnostic_source_hashes()
    assert "scripts/autopilot/run_operational_baseline_diagnostic.py" in hashes


def test_e13_ratifier_help_is_a_real_cli_surface():
    script = (
        REPO_ROOT
        / "scripts"
        / "autopilot"
        / "operator_candidates"
        / "ratify_and_apply_e14_operational_baseline.py"
    )

    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "EVIDENCE.json" in result.stdout
    assert "Traceback" not in result.stderr
