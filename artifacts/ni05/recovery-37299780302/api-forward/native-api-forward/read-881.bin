"""Tests for offline verifier-head evaluation helpers."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from scripts.graph_router import train_verifier_head as mod
from orchestration.repl_memory.verifier_head import VerifierHead


def test_load_classifier_features_falls_back_to_verifier_prefix(tmp_path: Path) -> None:
    data_path = tmp_path / "verifier.npz"
    Z = np.arange(12, dtype=np.float32).reshape(2, 6)
    np.savez_compressed(data_path, Z=Z, feature_dim=np.int64(4))

    with np.load(data_path, allow_pickle=True) as data:
        X, source = mod._load_classifier_features(
            data_path,
            data,
            Z,
            feature_dim=4,
            expected_rows=2,
        )

    np.testing.assert_array_equal(X, Z[:, :4])
    assert source == f"{data_path}:Z_feature_prefix[4]"


def test_load_classifier_features_uses_npz_classifier_prefix(tmp_path: Path) -> None:
    data_path = tmp_path / "verifier.npz"
    Z = np.arange(14, dtype=np.float32).reshape(2, 7)
    np.savez_compressed(
        data_path,
        Z=Z,
        feature_dim=np.int64(5),
        classifier_feature_dim=np.int64(4),
    )

    with np.load(data_path, allow_pickle=True) as data:
        X, source = mod._load_classifier_features(
            data_path,
            data,
            Z,
            feature_dim=5,
            expected_rows=2,
        )

    np.testing.assert_array_equal(X, Z[:, :4])
    assert source == f"{data_path}:Z_feature_prefix[4]"


def test_summary_markdown_records_null_promotion_metrics() -> None:
    markdown = mod._summary_markdown(
        {
            "data_path": "data.npz",
            "output_path": "weights.npz",
            "classifier_feature_source": "verifier_npz:Z_feature_prefix",
            "rows": 4,
            "positive_rows": 2,
            "negative_rows": 2,
            "val_rows": 1,
            "hidden1": 64,
            "hidden2": 32,
            "normalize_features": False,
            "action_counts": {"0": 2, "1": 2},
            "verifier": {"brier": 0.2, "auc": 0.8, "ece": 0.1, "acc": 0.75},
            "brier_delta_vs_best_softmax_baseline": 0.03,
            "brier_delta_vs_constant_baseline": -0.01,
            "gates": {"pass": False},
            "calibration": {
                "method": "temperature_bias_grid",
                "calibrated_verifier": {
                    "brier": 0.18,
                    "auc": 0.8,
                    "ece": 0.04,
                    "acc": 0.75,
                },
                "brier_delta_vs_best_softmax_baseline": 0.05,
                "brier_delta_vs_constant_baseline": 0.02,
                "gates": {"pass": False},
            },
        }
    )

    assert "Offline Multi-Action Verifier Evaluation" in markdown
    assert "Delta Brier vs constant base-rate baseline: `-0.0100`" in markdown
    assert "Calibration method: `temperature_bias_grid`" in markdown
    assert "Calibrated ECE: `0.0400`" in markdown
    assert "Calibrated gates passed: `False`" in markdown
    assert "Gates passed: `False`" in markdown


def test_temperature_bias_calibrator_improves_shifted_probabilities() -> None:
    labels = np.array([0, 0, 0, 1, 1, 1], dtype=np.float32)
    probs = np.array([0.30, 0.35, 0.40, 0.45, 0.50, 0.55], dtype=np.float32)

    calibrator = mod._fit_temperature_bias_calibrator(probs, labels)
    calibrated = mod._apply_temperature_bias_calibrator(probs, calibrator)

    assert calibrator["temperature"] > 0.0
    assert mod._brier(calibrated, labels) < mod._brier(probs, labels)


def test_temperature_bias_calibrator_can_optimize_ece_objective() -> None:
    labels = np.array([0, 0, 0, 1, 1, 1], dtype=np.float32)
    probs = np.array([0.30, 0.35, 0.40, 0.45, 0.50, 0.55], dtype=np.float32)

    calibrator = mod._fit_temperature_bias_calibrator(
        probs,
        labels,
        objective="ece",
    )
    calibrated = mod._apply_temperature_bias_calibrator(probs, calibrator)

    assert calibrator["objective"] == "ece"
    assert calibrator["temperature"] > 0.0
    assert mod._ece(calibrated, labels) <= mod._ece(probs, labels)


def test_quantile_histogram_calibrator_maps_bins_to_empirical_rates() -> None:
    labels = np.array([0, 0, 1, 1, 1, 1], dtype=np.float32)
    probs = np.array([0.10, 0.20, 0.30, 0.70, 0.80, 0.90], dtype=np.float32)

    calibrator = mod._fit_quantile_histogram_calibrator(
        probs,
        labels,
        n_bins=2,
        smoothing_alpha=0.0,
    )
    calibrated = mod._apply_quantile_histogram_calibrator(probs, calibrator)

    assert calibrator["method"] == "quantile_histogram"
    assert calibrator["bin_counts"] == [3, 3]
    assert calibrator["bin_positives"] == [1, 3]
    np.testing.assert_allclose(calibrated[:3], np.full(3, 1.0 / 3.0))
    np.testing.assert_allclose(calibrated[3:], np.ones(3))


def test_isotonic_calibrator_is_monotone() -> None:
    labels = np.array([0, 1, 0, 1, 1, 1], dtype=np.float32)
    probs = np.array([0.10, 0.20, 0.30, 0.70, 0.80, 0.90], dtype=np.float32)

    calibrator = mod._fit_isotonic_calibrator(probs, labels)
    calibrated = mod._apply_isotonic_calibrator(probs, calibrator)

    assert calibrator["method"] == "isotonic_regression"
    assert calibrator["block_count"] < len(probs)
    assert np.all(np.diff(calibrated) >= 0.0)


def test_verifier_feature_normalizer_persists_with_weights(tmp_path: Path) -> None:
    verifier = VerifierHead(feature_dim=3, n_actions=2, hidden1=4, hidden2=3)
    mean = np.array([1.0, 2.0, 3.0], dtype=np.float32)
    scale = np.array([2.0, 4.0, 8.0], dtype=np.float32)
    verifier.set_feature_normalizer(mean, scale)
    path = tmp_path / "verifier.npz"

    verifier.save(path)
    loaded = VerifierHead.load(path)

    assert loaded is not None
    assert loaded.has_feature_normalizer
    np.testing.assert_allclose(loaded.feature_mean, mean)
    np.testing.assert_allclose(loaded.feature_scale, scale)
    np.testing.assert_allclose(
        loaded.normalize_features(np.array([3.0, 10.0, 19.0], dtype=np.float32)),
        np.array([1.0, 2.0, 2.0], dtype=np.float32),
    )
