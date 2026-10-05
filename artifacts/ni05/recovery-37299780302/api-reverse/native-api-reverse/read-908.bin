"""Tests for verifier calibration robustness aggregation."""

from __future__ import annotations

import pytest

from scripts.graph_router import evaluate_verifier_calibration_robustness as mod


def _run(method: str, passed: bool, ece: float = 0.04) -> dict:
    return {
        "method": method,
        "action_counts": {"0": 50, "1": 10, "2": 40},
        "gates": {"pass": False},
        "calibration": {
            "gates": {"pass": passed},
            "calibrated_verifier": {
                "brier": 0.18,
                "auc": 0.82,
                "ece": ece,
                "acc": 0.72,
            },
        },
    }


def test_parse_methods_rejects_unknown_method() -> None:
    with pytest.raises(argparse_error()):
        mod._parse_csv_strings("quantile_histogram,unknown")


def test_parse_methods_accepts_ece_temperature_bias() -> None:
    assert mod._parse_csv_strings("temperature_bias,ece_temperature_bias") == [
        "temperature_bias",
        "ece_temperature_bias",
    ]


def test_aggregate_runs_flags_sparse_actions_and_unstable_pass_rate() -> None:
    summary = mod.aggregate_runs(
        [
            _run("quantile_histogram", True, ece=0.04),
            _run("quantile_histogram", False, ece=0.12),
            _run("temperature_bias", False, ece=0.18),
        ],
        min_calibrated_pass_rate=1.0,
        min_action_rows=30,
    )

    assert summary["decision"]["status"] == "not_promotion_grade"
    assert "sparse_action_coverage" in summary["decision"]["blockers"]
    assert "quantile_histogram_calibrated_pass_rate_below_threshold" in summary["decision"]["blockers"]
    assert summary["sparse_actions"] == {"1": 10}
    assert summary["methods"]["quantile_histogram"]["calibrated_pass_count"] == 1
    assert summary["methods"]["quantile_histogram"]["calibrated_pass_rate"] == 0.5


def argparse_error() -> type[Exception]:
    import argparse

    return argparse.ArgumentTypeError
