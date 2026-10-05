#!/usr/bin/env python3
"""Tests for the consolidated clean-room statistics module.

Covers ``src.llm_primitives.stat_tests`` (Wilson interval, ECE, ROC-AUC) against
published values, hand-computed fixtures, and — where importable — sklearn; plus
the additive ``scripts.autopilot.paired_stats`` dataset/profile equality gate.

Hermetic, stdlib + optional sklearn only. NO inference.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.llm_primitives.stat_tests import (  # noqa: E402
    CALIBRATION_METRIC_KEYS,
    DEFAULT_WILSON_Z,
    compute_calibration_metrics,
    expected_calibration_error,
    roc_auc,
    wilson_interval,
)

try:
    from sklearn.metrics import roc_auc_score as _sk_auc

    _HAVE_SKLEARN = True
except Exception:  # pragma: no cover - environment-dependent
    _HAVE_SKLEARN = False


# --------------------------------------------------------------------------- #
# Wilson score interval
# --------------------------------------------------------------------------- #
def test_wilson_degenerate_denominator():
    # Empty denominator -> maximally uninformative, matching every prior copy.
    assert wilson_interval(0, 0) == (0.0, 1.0)
    assert wilson_interval(5, 0) == (0.0, 1.0)
    assert wilson_interval(0, -3) == (0.0, 1.0)


def test_wilson_published_values():
    # Textbook Wilson 95% (z=1.96) intervals.
    lo, hi = wilson_interval(0, 10, z=1.96)
    assert lo == 0.0
    assert math.isclose(hi, 0.2775401687666165, rel_tol=1e-12)
    # Symmetric complement.
    lo2, hi2 = wilson_interval(10, 10, z=1.96)
    assert hi2 == 1.0
    assert math.isclose(lo2, 1.0 - 0.2775401687666165, rel_tol=1e-12)
    # p_hat = 0.5, n = 100 -> ~(0.404, 0.596).
    lo3, hi3 = wilson_interval(50, 100, z=1.96)
    assert math.isclose(lo3, 0.40382982859014716, rel_tol=1e-12)
    assert math.isclose(hi3, 0.5961701714098528, rel_tol=1e-12)


def test_wilson_brackets_point_estimate_and_clamps():
    lo, hi = wilson_interval(2, 10)
    assert 0.0 <= lo < 0.2 < hi <= 1.0
    # Interval always stays inside [0, 1].
    for k in range(0, 21):
        lo, hi = wilson_interval(k, 20)
        assert 0.0 <= lo <= hi <= 1.0


def test_wilson_default_z_is_sharp_1p96():
    # Default z is the sharper 1.959964 quantile; very close to the rounded 1.96
    # but not identical, so callers reproducing history must pass z=1.96.
    assert DEFAULT_WILSON_Z == 1.959964
    sharp = wilson_interval(2, 10)
    rounded = wilson_interval(2, 10, z=1.96)
    assert sharp != rounded
    assert math.isclose(sharp[0], rounded[0], abs_tol=1e-4)
    assert math.isclose(sharp[1], rounded[1], abs_tol=1e-4)


# --------------------------------------------------------------------------- #
# Expected Calibration Error (hand-computed fixtures)
# --------------------------------------------------------------------------- #
def test_ece_empty_is_none():
    assert expected_calibration_error([], []) is None


def test_ece_perfectly_calibrated_is_zero():
    assert expected_calibration_error([0.0, 0.0, 1.0, 1.0], [0.0, 0.0, 1.0, 1.0]) == 0.0


def test_ece_two_bins_hand_computed():
    # 0.2 -> bin [0.2,0.3): conf 0.2, acc 0 -> gap 0.2, weight 1/2 -> 0.1
    # 0.8 -> bin [0.8,0.9): conf 0.8, acc 1 -> gap 0.2, weight 1/2 -> 0.1
    # ECE = 0.2
    assert math.isclose(
        expected_calibration_error([0.2, 0.8], [0, 1]), 0.2, abs_tol=1e-12
    )


def test_ece_overconfident_single_bin_hand_computed():
    # Four preds of 0.9 (all in the final bin), one positive -> acc 0.25.
    # |0.25 - 0.9| = 0.65, weight 1.0 -> ECE = 0.65
    assert math.isclose(
        expected_calibration_error([0.9, 0.9, 0.9, 0.9], [1, 0, 0, 0]),
        0.65,
        abs_tol=1e-12,
    )


def test_ece_last_bin_closed_on_right():
    # confidence == 1.0 must land in the final bin (closed right).
    assert expected_calibration_error([1.0], [1]) == 0.0
    assert math.isclose(expected_calibration_error([1.0], [0]), 1.0, abs_tol=1e-12)


def test_ece_length_mismatch_raises():
    with pytest.raises(ValueError):
        expected_calibration_error([0.1, 0.2], [1])


# --------------------------------------------------------------------------- #
# ROC-AUC
# --------------------------------------------------------------------------- #
def test_roc_auc_perfect_separation():
    assert roc_auc([0.0, 0.0, 1.0, 1.0], [0, 0, 1, 1]) == 1.0


def test_roc_auc_known_075_worked_example():
    # One positive (0.35) ranks below a negative (0.4) -> AUC 0.75.
    assert math.isclose(roc_auc([0.1, 0.4, 0.35, 0.8], [0, 0, 1, 1]), 0.75)


def test_roc_auc_ties_are_averaged():
    # Two tied scores split across classes -> 0.5 (== sklearn tie handling).
    assert math.isclose(roc_auc([0.5, 0.5], [0, 1]), 0.5)


def test_roc_auc_single_class_is_none():
    assert roc_auc([0.2, 0.3], [1, 1]) is None
    assert roc_auc([0.2, 0.3], [0, 0]) is None


def test_roc_auc_length_mismatch_raises():
    with pytest.raises(ValueError):
        roc_auc([0.1, 0.2, 0.3], [1, 0])


@pytest.mark.skipif(not _HAVE_SKLEARN, reason="sklearn not importable")
def test_roc_auc_matches_sklearn():
    import random

    for seed in (0, 1, 2, 7, 42, 2026):
        rng = random.Random(seed)
        n = rng.randint(20, 150)
        scores = [rng.random() for _ in range(n)]
        labels = [rng.randint(0, 1) for _ in range(n)]
        if 0 < sum(labels) < n:
            assert math.isclose(
                roc_auc(scores, labels), _sk_auc(labels, scores), rel_tol=1e-9, abs_tol=1e-12
            )
    # Tie-heavy case: consolidated tie averaging must equal sklearn exactly.
    scores = [0.5, 0.5, 0.5, 0.9, 0.1, 0.5]
    labels = [0, 1, 0, 1, 0, 1]
    assert math.isclose(roc_auc(scores, labels), _sk_auc(labels, scores), rel_tol=1e-9)


# --------------------------------------------------------------------------- #
# Eval calibration metric bundle
# --------------------------------------------------------------------------- #
def test_calibration_metric_bundle_keys_are_stable():
    assert CALIBRATION_METRIC_KEYS == (
        "ece",
        "auroc",
        "top1_accuracy",
        "bottom1_accuracy",
        "spearman_rho",
        "mae",
    )


def test_calibration_metric_bundle_concrete_values():
    metrics = compute_calibration_metrics([0.2, 0.4, 0.6, 0.8], [0, 0, 1, 1])
    assert metrics["n"] == 4
    assert metrics["ece"] == pytest.approx(0.3, abs=1e-12)
    assert metrics["auroc"] == pytest.approx(1.0, abs=1e-12)
    assert metrics["top1_accuracy"] == pytest.approx(1.0, abs=1e-12)
    assert metrics["bottom1_accuracy"] == pytest.approx(0.0, abs=1e-12)
    assert metrics["spearman_rho"] == pytest.approx(0.8944271909999159, abs=1e-9)
    assert metrics["mae"] == pytest.approx(0.3, abs=1e-12)


def test_calibration_metric_bundle_averages_extreme_ties():
    metrics = compute_calibration_metrics([0.9, 0.9, 0.1, 0.1], [1, 0, 0, 1])
    assert metrics["top1_accuracy"] == pytest.approx(0.5, abs=1e-12)
    assert metrics["bottom1_accuracy"] == pytest.approx(0.5, abs=1e-12)


def test_calibration_metric_bundle_handles_degenerate_inputs():
    empty = compute_calibration_metrics([], [])
    assert empty["n"] == 0
    for key in CALIBRATION_METRIC_KEYS:
        assert empty[key] is None

    constant_conf = compute_calibration_metrics([0.5, 0.5, 0.5, 0.5], [1, 0, 1, 0])
    assert constant_conf["auroc"] is None
    assert constant_conf["spearman_rho"] is None
    assert constant_conf["top1_accuracy"] == pytest.approx(0.5, abs=1e-12)

    single_class = compute_calibration_metrics([0.1, 0.4, 0.9], [1, 1, 1])
    assert single_class["auroc"] is None


def test_calibration_metric_bundle_length_mismatch_raises():
    with pytest.raises(ValueError):
        compute_calibration_metrics([0.1, 0.2], [1])


# --------------------------------------------------------------------------- #
# Paired-comparison dataset/profile equality gate (additive paired_stats helper)
# --------------------------------------------------------------------------- #
from scripts.autopilot.paired_stats import (  # noqa: E402
    ComparisonProfile,
    PairedComparisonMismatchError,
    require_matched_comparison,
)


def test_gate_accepts_matched_arms_and_returns_profile():
    a = {"dataset_sha256": "abc123", "test_profile": "greedy-seed42"}
    b = ComparisonProfile(dataset_sha256="abc123", test_profile="greedy-seed42")
    shared = require_matched_comparison(a, b)
    assert shared.dataset_sha256 == "abc123"
    assert shared.test_profile == "greedy-seed42"


def test_gate_refuses_dataset_mismatch():
    a = {"dataset_sha256": "abc123", "test_profile": "p"}
    b = {"dataset_sha256": "def456", "test_profile": "p"}
    with pytest.raises(PairedComparisonMismatchError, match="dataset_sha256"):
        require_matched_comparison(a, b)


def test_gate_refuses_profile_mismatch():
    a = {"dataset_sha256": "abc123", "test_profile": "greedy"}
    b = {"dataset_sha256": "abc123", "test_profile": "sampled"}
    with pytest.raises(PairedComparisonMismatchError, match="test_profile"):
        require_matched_comparison(a, b)


def test_gate_refuses_empty_identity():
    # Two arms that both lack a dataset hash must NOT be treated as comparable.
    a = {"dataset_sha256": "", "test_profile": "p"}
    b = {"dataset_sha256": "", "test_profile": "p"}
    with pytest.raises(PairedComparisonMismatchError, match="empty"):
        require_matched_comparison(a, b)


def test_gate_refuses_missing_key():
    with pytest.raises(PairedComparisonMismatchError, match="missing"):
        require_matched_comparison({"dataset_sha256": "x"}, {"dataset_sha256": "x", "test_profile": "p"})
