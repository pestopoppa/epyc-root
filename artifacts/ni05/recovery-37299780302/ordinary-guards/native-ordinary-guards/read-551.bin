"""Tests for offline reward verifier model-family diagnostics."""

from __future__ import annotations

import pytest

from scripts.graph_router import evaluate_offline_reward_verifier_model_families as mod


def _run(family: str, method: str, passed: bool, ece: float = 0.04) -> dict:
    return {
        "family": family,
        "method": method,
        "metrics": {"brier": 0.18, "auc": 0.82, "ece": ece, "acc": 0.72},
        "brier_delta_vs_best_softmax_baseline": 0.08,
        "gates": {"pass": passed},
        "source_family_metrics": {
            "orchestrator_live_seed": {
                "rows": 12,
                "positive_rows": 4,
                "negative_rows": 8,
                "metrics": {"brier": 0.11, "auc": 0.9, "ece": 0.07, "acc": 0.83},
            },
            "seeding_eval": {
                "rows": 3,
                "positive_rows": 0,
                "negative_rows": 3,
                "metrics": None,
            },
        },
    }


def test_source_family_from_benchmark_paths() -> None:
    assert (
        mod._source_family(
            "/mnt/raid0/llm/epyc-inference-research/benchmarks/results/orchestrator/seeding_live_seed42.json"
        )
        == "orchestrator_live_seed"
    )
    assert (
        mod._source_family(
            "/mnt/raid0/llm/epyc-inference-research/benchmarks/results/eval/seeding_20260305_203724.jsonl"
        )
        == "seeding_eval"
    )
    assert (
        mod._source_family(
            "/mnt/raid0/llm/epyc-inference-research/benchmarks/results/eval/3way_20260303_025953.jsonl"
        )
        == "three_way_eval"
    )
    assert mod._source_family("/tmp/custom.jsonl") == "other"


def test_split_indices_are_disjoint_and_cover_requested_sizes() -> None:
    train_idx, cal_idx, test_idx = mod._split_indices(
        100,
        seed=42,
        calibration_split=0.2,
        test_split=0.2,
    )

    assert len(train_idx) == 60
    assert len(cal_idx) == 20
    assert len(test_idx) == 20
    assert not (set(train_idx) & set(cal_idx))
    assert not (set(train_idx) & set(test_idx))
    assert not (set(cal_idx) & set(test_idx))


def test_aggregate_runs_flags_non_promotion_methods() -> None:
    summary = mod.aggregate_runs(
        [
            _run("logistic_l2", "raw", True),
            _run("logistic_l2", "raw", False, ece=0.12),
            _run("random_forest", "isotonic", False, ece=0.2),
        ],
        min_calibrated_pass_rate=1.0,
    )

    assert summary["decision"]["status"] == "not_promotion_grade"
    assert "logistic_l2_raw_pass_rate_below_threshold" in summary["decision"]["blockers"]
    assert "random_forest_isotonic_pass_rate_below_threshold" in summary["decision"]["blockers"]
    assert summary["families"]["logistic_l2"]["methods"]["raw"]["pass_count"] == 1
    assert summary["families"]["logistic_l2"]["methods"]["raw"]["pass_rate"] == 0.5
    source_summary = summary["source_families"]["orchestrator_live_seed"]["methods"]
    assert source_summary["logistic_l2:raw"]["metric_runs"] == 2
    assert source_summary["logistic_l2:raw"]["ece"]["mean"] == pytest.approx(0.07)
    sparse_summary = summary["source_families"]["seeding_eval"]["methods"]
    assert sparse_summary["logistic_l2:raw"]["metric_runs"] == 0
    assert sparse_summary["logistic_l2:raw"]["rows"]["mean"] == pytest.approx(3.0)


def test_parse_rejects_unknown_family() -> None:
    with pytest.raises(argparse_error()):
        mod._parse_csv("logistic_l2,unknown", allowed=mod.MODEL_FAMILIES)


def argparse_error() -> type[Exception]:
    import argparse

    return argparse.ArgumentTypeError
