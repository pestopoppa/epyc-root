"""Tests for the factual-risk calibration report aggregator."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.analysis import factual_risk_calibration_report as report


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_build_report_summarizes_dataset_and_splits(tmp_path: Path) -> None:
    dataset = tmp_path / "factual_risk_calibration_v2.jsonl"
    _write_jsonl(
        dataset,
        [
            {
                "domain": "gpqa",
                "label_4class": "CORRECT",
                "label_source": "v1_regex",
                "prompt": "p1",
                "prompt_hash": "h1",
                "risk_band_v1": "high",
                "tier": 1,
            },
            {
                "domain": "usaco",
                "label_4class": "INCORRECT",
                "label_source": "aa_omniscience",
                "prompt": "p2",
                "prompt_hash": "h2",
                "risk_band_v1": "low",
                "tier": 2,
            },
            {
                "domain": "gpqa",
                "label_4class": "PARTIAL",
                "label_source": "seeding_diagnostics",
                "prompt": "p3",
                "prompt_hash": "h3",
                "risk_band_v1": "high",
                "tier": 2,
            },
            {
                "domain": "math",
                "label_4class": "NOT_ATTEMPTED",
                "label_source": "seeding_diagnostics",
                "prompt": "p4",
                "prompt_hash": "h4",
                "risk_band_v1": "low",
            },
        ],
    )
    _write_jsonl(dataset.with_name("factual_risk_calibration_v2_train.jsonl"), [{"id": 1}, {"id": 2}])
    _write_jsonl(dataset.with_name("factual_risk_calibration_v2_val.jsonl"), [{"id": 3}])
    _write_jsonl(dataset.with_name("factual_risk_calibration_v2_test.jsonl"), [{"id": 4}, {"id": 5}])

    summary = report.build_report(dataset, auto_discover_results=False)

    assert summary["dataset"]["row_count"] == 4
    assert summary["dataset"]["source_counts"] == {
        "aa_omniscience": 1,
        "seeding_diagnostics": 2,
        "v1_regex": 1,
    }
    assert summary["dataset"]["risk_label_counts"] == {
        "CORRECT": 1,
        "INCORRECT": 1,
        "NOT_ATTEMPTED": 1,
        "PARTIAL": 1,
    }
    assert summary["dataset"]["tier_counts"] == {"1": 1, "2": 2}
    assert summary["dataset"]["tier_source_crosstab"] == {
        "1": {"v1_regex": 1},
        "2": {"aa_omniscience": 1, "seeding_diagnostics": 1},
    }
    assert summary["splits"]["train"]["row_count"] == 2
    assert summary["splits"]["val"]["row_count"] == 1
    assert summary["splits"]["test"]["row_count"] == 2
    assert summary["results"]["enabled"] is False


def test_build_report_aggregates_result_directories(tmp_path: Path, monkeypatch) -> None:
    orch = tmp_path / "orchestration"
    monkeypatch.setattr(report, "ORCH_ROOT", tmp_path)

    dataset = orch / "factual_risk_calibration_v2.jsonl"
    _write_jsonl(dataset, [{"label_4class": "CORRECT", "label_source": "v1_regex", "prompt": "p", "prompt_hash": "h", "risk_band_v1": "low"}])

    g10_dir = orch / "g10_results"
    _write_jsonl(
        g10_dir / "run_a.jsonl",
        [
            {"role": "architect", "model": "m1", "outcome": "passed", "source": "g10"},
            {"role": "architect", "model": "m1", "outcome": "failed", "source": "g10"},
        ],
    )
    _write_jsonl(
        g10_dir / "run_b.jsonl",
        [
            {"role": "coder", "model": "m2", "passed": True, "source": "g11"},
        ],
    )

    summary = report.build_report(dataset, auto_discover_results=True)

    assert summary["results"]["enabled"] is True
    assert summary["results"]["files"] == [
        {"path": str(g10_dir / "run_a.jsonl"), "row_count": 2},
        {"path": str(g10_dir / "run_b.jsonl"), "row_count": 1},
    ]
    assert summary["results"]["by_role"]["architect"]["total"] == 2
    assert summary["results"]["by_role"]["architect"]["outcomes"] == {"failed": 1, "passed": 1}
    assert summary["results"]["by_role"]["architect"]["source_counts"] == {"g10": 2}
    assert summary["results"]["by_model"]["m2"]["outcomes"] == {"passed": 1}
    assert summary["results"]["by_role_model"]["architect::m1"]["outcomes"] == {"failed": 1, "passed": 1}
    assert summary["results"]["by_role_model"]["coder::m2"]["outcomes"] == {"passed": 1}


def test_build_report_ignores_missing_result_paths(tmp_path: Path, monkeypatch) -> None:
    orch = tmp_path / "orchestration"
    monkeypatch.setattr(report, "ORCH_ROOT", tmp_path)

    dataset = orch / "factual_risk_calibration_v2.jsonl"
    _write_jsonl(dataset, [{"label_4class": "CORRECT", "label_source": "v1_regex", "prompt": "p", "prompt_hash": "h", "risk_band_v1": "low"}])

    summary = report.build_report(dataset, result_paths=[tmp_path / "missing.jsonl"], auto_discover_results=False)

    assert summary["results"]["enabled"] is False
    assert summary["results"]["files"] == []


def test_tier_calibration_readiness_blocks_until_expected_roles_present(tmp_path: Path) -> None:
    dataset = tmp_path / "factual_risk_calibration_v2.jsonl"
    _write_jsonl(dataset, [{"label_4class": "CORRECT", "label_source": "v1_regex", "risk_band_v1": "low"}])
    results = tmp_path / "aa_results.jsonl"
    _write_jsonl(
        results,
        [
            {"role": "frontdoor", "outcome": "CORRECT", "source": "aa_omniscience"},
            {"role": "frontdoor", "outcome": "PARTIAL_ANSWER", "source": "aa_omniscience"},
            {"role": "worker_general", "outcome": "INCORRECT", "source": "aa_omniscience"},
            {"role": "worker_general", "outcome": "PARTIAL_ANSWER", "source": "aa_omniscience"},
            {"role": "worker_general", "outcome": "NOT_ATTEMPTED", "source": "aa_omniscience"},
        ],
    )

    summary = report.build_report(
        dataset,
        result_paths=[results],
        auto_discover_results=False,
        expected_roles=("architect_general", "frontdoor", "worker_general"),
    )

    readiness = summary["tier_calibration_readiness"]
    assert readiness["complete"] is False
    assert readiness["status"] == "blocked_missing_roles"
    assert readiness["missing_roles"] == ["architect_general"]
    assert readiness["scoring_policy"] == {
        "basis": "deterministic_aa_omniscience_4class",
        "decided_at": "2026-06-20",
        "decision": "accepted_for_role_tier_recalibration",
        "scope": "factual_risk_role_adjustments_only",
    }
    assert readiness["role_metrics"]["frontdoor"]["accuracy"] == 0.5
    assert readiness["role_metrics"]["worker_general"]["hallucination_rate"] == 0.333333
    assert readiness["role_multiplier_preview_vs_worst"]["worker_general"] == 1.0
    assert readiness["tier_multiplier_preview_vs_worst"] == {}


def test_tier_calibration_readiness_reports_complete_preview(tmp_path: Path) -> None:
    dataset = tmp_path / "factual_risk_calibration_v2.jsonl"
    _write_jsonl(dataset, [{"label_4class": "CORRECT", "label_source": "v1_regex", "risk_band_v1": "low"}])
    results = tmp_path / "aa_results.jsonl"
    _write_jsonl(
        results,
        [
            {"role": "architect_general", "outcome": "PARTIAL_ANSWER", "source": "aa_omniscience"},
            {"role": "architect_general", "outcome": "CORRECT", "source": "aa_omniscience"},
            {"role": "frontdoor", "outcome": "CORRECT", "source": "aa_omniscience"},
            {"role": "frontdoor", "outcome": "INCORRECT", "source": "aa_omniscience"},
            {"role": "worker_general", "outcome": "INCORRECT", "source": "aa_omniscience"},
            {"role": "worker_general", "outcome": "INCORRECT", "source": "aa_omniscience"},
        ],
    )

    summary = report.build_report(
        dataset,
        result_paths=[results],
        auto_discover_results=False,
        expected_roles=("architect_general", "frontdoor", "worker_general"),
    )

    readiness = summary["tier_calibration_readiness"]
    assert readiness["complete"] is True
    assert readiness["status"] == "ready_for_tier_update"
    assert readiness["scoring_policy"]["decision"] == "accepted_for_role_tier_recalibration"
    assert readiness["missing_roles"] == []
    assert readiness["tier_multiplier_preview_vs_worst"] == {
        "tier_1": 0.0,
        "tier_2": 1.0,
        "tier_3": 1.0,
    }
