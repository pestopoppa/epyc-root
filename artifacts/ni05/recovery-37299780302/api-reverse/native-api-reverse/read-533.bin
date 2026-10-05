from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from scripts.graph_router.observed_irt_feature_ablation import (
    append_observed_irt_features,
    load_observed_split,
    run_observed_ablation,
)


def _write_observed_fixture(base: Path, *, rows: int = 72) -> tuple[Path, Path]:
    rng = np.random.default_rng(13)
    X = rng.normal(size=(rows, 8)).astype(np.float32)
    correctness = np.zeros((rows, 3), dtype=np.float32)
    correctness[:, 0] = (X[:, 0] > -0.3).astype(np.float32)
    correctness[:, 1] = (X[:, 1] > 0.1).astype(np.float32)
    correctness[:, 2] = (X[:, 0] + X[:, 1] > 0.2).astype(np.float32)
    soft = correctness + 0.1
    soft = soft / soft.sum(axis=1, keepdims=True)
    hard = np.argmax(soft, axis=1).astype(np.int64)
    qids = np.asarray([f"qid-{idx:03d}" for idx in range(rows)], dtype=object)
    suites = np.asarray(["suite-a" if idx % 2 else "suite-b" for idx in range(rows)], dtype=object)
    label_map = np.asarray(
        [(0, "frontdoor"), (1, "worker_general"), (2, "architect_general")],
        dtype=object,
    )
    data_path = base / "soft_labels_embedded.npz"
    np.savez(
        data_path,
        X=X,
        soft_labels=soft.astype(np.float32),
        correctness=correctness,
        hard_labels=hard,
        qids=qids,
        suites=suites,
        label_map=label_map,
    )
    labels_path = base / "soft_labels.jsonl"
    with labels_path.open("w") as handle:
        for idx, qid in enumerate(qids):
            roles = ["frontdoor", "worker_general"]
            if idx % 3 == 0:
                roles.append("architect_general")
            handle.write(json.dumps({"qid": str(qid), "roles_seen": roles}) + "\n")
    return data_path, labels_path


def test_load_observed_split_preserves_seen_role_mask(tmp_path: Path) -> None:
    data_path, labels_path = _write_observed_fixture(tmp_path, rows=20)

    split = load_observed_split(data_path, labels_path, val_split=0.25, seed=2)

    assert split["source_rows"] == 20
    assert split["train_rows"] == 15
    assert split["val_rows"] == 5
    assert split["observed_mask_train"].shape == (15, 3)
    assert split["observed_cells"] == 47
    assert split["label_map"] == {0: "frontdoor", 1: "worker_general", 2: "architect_general"}


def test_append_observed_irt_features_adds_two_columns(tmp_path: Path) -> None:
    data_path, labels_path = _write_observed_fixture(tmp_path, rows=36)
    split = load_observed_split(data_path, labels_path, seed=4)

    X_train_aug, X_val_aug, metadata = append_observed_irt_features(
        split,
        embedding_dim=8,
        platt_iterations=5,
    )

    assert X_train_aug.shape[1] == split["X_train"].shape[1] + 2
    assert X_val_aug.shape[1] == split["X_val"].shape[1] + 2
    assert metadata["embedding_dim"] == 8


def test_run_observed_ablation_reports_non_promotion_diagnostic(tmp_path: Path) -> None:
    data_path, labels_path = _write_observed_fixture(tmp_path, rows=80)

    report = run_observed_ablation(
        data_path,
        labels_path,
        val_split=0.2,
        embedding_dim=8,
        epochs=5,
        batch_size=16,
        patience=3,
        seed=3,
    )

    assert report["schema"] == "epyc.graph_router.observed_irt_feature_ablation.v1"
    assert report["response_source"] == "journal_observed_per_role_correctness_cached_embeddings"
    assert report["baseline"]["input_dim"] == 8
    assert report["observed_irt_augmented"]["input_dim"] == 10
    assert "delta_role_success_acc_pp" in report
    assert report["decision_gate"]["promotion_grade"] is False
