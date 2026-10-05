from __future__ import annotations

from pathlib import Path

import numpy as np

from scripts.graph_router.irt_scorer import (
    estimate_irt_scores,
    load_response_dataset,
    predict_irt_from_embeddings,
    score_file,
)


def test_estimate_irt_scores_orders_difficulty_and_discrimination() -> None:
    responses = np.array(
        [
            [1, 1, 1, 1],  # easy but low-discrimination
            [0, 0, 1, 1],  # separates weak from strong actions
            [0, 0, 0, 0],  # hard but low-discrimination
        ],
        dtype=np.float32,
    )

    scores = estimate_irt_scores(responses, platt_iterations=20)

    assert scores.latent_difficulty[0] < scores.latent_difficulty[1]
    assert scores.latent_difficulty[1] < scores.latent_difficulty[2]
    assert scores.latent_discrimination[1] > scores.latent_discrimination[0]
    assert scores.latent_discrimination[1] > scores.latent_discrimination[2]
    assert np.isfinite(scores.calibrated_success).all()
    assert np.isfinite(scores.action_abilities).all()


def test_load_response_dataset_uses_observed_response_matrix(tmp_path: Path) -> None:
    path = tmp_path / "responses.npz"
    responses = np.array([[1, np.nan, 0], [0, 1, 1]], dtype=np.float32)
    np.savez(path, responses=responses, label_map=np.array([(0, "a"), (1, "b"), (2, "c")], dtype=object))

    dataset = load_response_dataset(path)

    assert dataset["response_source"] == "observed_matrix"
    assert dataset["responses"].shape == (2, 3)
    assert dataset["mask"].tolist() == [[True, False, True], [True, True, True]]
    assert dataset["label_map"] == {0: "a", 1: "b", 2: "c"}


def test_load_response_dataset_builds_label_proxy_from_training_npz(tmp_path: Path) -> None:
    path = tmp_path / "training_data.npz"
    np.savez(
        path,
        X=np.zeros((3, 1031), dtype=np.float32),
        y=np.array([0, 2, 1], dtype=np.int64),
        q_weights=np.array([0.5, 0.75, 1.0], dtype=np.float32),
        label_map=np.array([(0, "frontdoor"), (1, "worker_general"), (2, "architect")], dtype=object),
    )

    dataset = load_response_dataset(path)

    assert dataset["response_source"] == "label_proxy"
    assert dataset["responses"].tolist() == [[1.0, 0.0, 0.0], [0.0, 0.0, 1.0], [0.0, 1.0, 0.0]]
    assert dataset["sample_weights"].shape == (3, 3)
    assert dataset["feature_rows"] == 3


def test_load_response_dataset_canonicalizes_legacy_label_map(tmp_path: Path) -> None:
    path = tmp_path / "training_data.npz"
    np.savez(
        path,
        X=np.zeros((2, 1031), dtype=np.float32),
        y=np.array([0, 1], dtype=np.int64),
        label_map=np.array([(0, "SELF"), (1, "WORKER")], dtype=object),
    )

    dataset = load_response_dataset(path)

    assert dataset["label_map"] == {0: "frontdoor", 1: "worker_general"}


def test_score_file_writes_prompt_score_schema(tmp_path: Path) -> None:
    data_path = tmp_path / "training_data.npz"
    output_path = tmp_path / "irt_scores.npz"
    np.savez(
        data_path,
        X=np.zeros((4, 1031), dtype=np.float32),
        y=np.array([0, 1, 1, 0], dtype=np.int64),
        q_weights=np.ones(4, dtype=np.float32),
        label_map=np.array([(0, "frontdoor"), (1, "worker_general")], dtype=object),
    )

    metadata = score_file(data_path, output_path, platt_iterations=20)
    saved = np.load(output_path, allow_pickle=True)

    assert metadata["schema"] == "epyc.graph_router.irt_prompt_scores.v1"
    assert metadata["response_source"] == "label_proxy"
    assert saved["latent_difficulty"].shape == (4,)
    assert saved["latent_discrimination"].shape == (4,)
    assert saved["calibrated_success"].shape == (4,)
    assert saved["action_abilities"].shape == (2,)
    assert saved["projector_weights"].shape == (1025, 2)
    assert saved["metadata"].item()["items"] == 4

    difficulty, discrimination = predict_irt_from_embeddings(
        np.zeros((1, 1031), dtype=np.float32),
        embedding_dim=int(saved["embedding_dim"]),
        feature_mean=saved["projector_feature_mean"],
        feature_scale=saved["projector_feature_scale"],
        weights=saved["projector_weights"],
        target_mean=saved["projector_target_mean"],
        target_scale=saved["projector_target_scale"],
    )
    assert difficulty.shape == (1,)
    assert discrimination.shape == (1,)
