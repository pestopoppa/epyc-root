from __future__ import annotations

from pathlib import Path

import numpy as np

from scripts.graph_router.irt_feature_ablation import (
    append_projected_irt_features,
    load_training_split,
    run_ablation,
)


def _write_training_npz(path: Path, *, rows: int = 80) -> None:
    rng = np.random.default_rng(7)
    base = rng.normal(size=(rows, 6)).astype(np.float32)
    y = (base[:, 0] + base[:, 1] * 0.5 > 0).astype(np.int64)
    np.savez(
        path,
        X=base,
        y=y,
        q_weights=np.ones(rows, dtype=np.float32),
        label_map=np.array([(0, "frontdoor"), (1, "worker_general")], dtype=object),
    )


def test_load_training_split_is_seeded_and_bounded(tmp_path: Path) -> None:
    data_path = tmp_path / "training_data.npz"
    _write_training_npz(data_path, rows=20)

    split = load_training_split(data_path, max_samples=10, val_fraction=0.3, seed=1)

    assert split["source_rows"] == 20
    assert split["sampled_rows"] == 10
    assert split["train_rows"] == 7
    assert split["val_rows"] == 3
    assert split["X_train"].shape == (7, 6)
    assert split["label_map"] == {0: "frontdoor", 1: "worker_general"}


def test_append_projected_irt_features_adds_two_standardized_columns() -> None:
    rng = np.random.default_rng(11)
    X_train = rng.normal(size=(16, 8)).astype(np.float32)
    y_train = np.array([0, 1] * 8, dtype=np.int64)
    q_train = np.ones(16, dtype=np.float32)
    X_val = rng.normal(size=(5, 8)).astype(np.float32)

    train_aug, val_aug, metadata = append_projected_irt_features(
        X_train,
        y_train,
        q_train,
        X_val,
        n_actions=2,
        embedding_dim=8,
        platt_iterations=5,
    )

    assert train_aug.shape == (16, 10)
    assert val_aug.shape == (5, 10)
    assert metadata["embedding_dim"] == 8
    assert np.allclose(train_aug[:, -2:].mean(axis=0), 0.0, atol=1e-5)


def test_run_ablation_writes_label_proxy_decision_report(tmp_path: Path) -> None:
    data_path = tmp_path / "training_data.npz"
    _write_training_npz(data_path, rows=120)

    report = run_ablation(
        data_path,
        max_samples=80,
        embedding_dim=6,
        epochs=5,
        batch_size=16,
        patience=3,
        seed=2,
    )

    assert report["schema"] == "epyc.graph_router.irt_feature_ablation.v1"
    assert report["response_source"] == "label_proxy_train_split_only"
    assert report["baseline"]["input_dim"] == 6
    assert report["irt_augmented"]["input_dim"] == 8
    assert "delta_val_acc_pp" in report
    assert report["decision_gate"]["promotion_grade"] is False
