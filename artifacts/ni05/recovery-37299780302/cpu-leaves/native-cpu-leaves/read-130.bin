from __future__ import annotations

import numpy as np

from scripts.graph_router.block_separability_diagnostic import (
    _class_distribution,
    connectivity_masks,
    train_variant,
)


def test_block10_masks_keep_dense_action_head() -> None:
    masks = connectivity_masks(
        input_dim=20,
        hidden1=10,
        hidden2=5,
        n_actions=3,
        variant="block10",
        blocks=5,
    )

    assert masks["W1"].shape == (20, 10)
    assert masks["W2"].shape == (10, 5)
    assert masks["W3"].shape == (5, 3)
    assert 0.0 < float(masks["W1"].mean()) < 1.0
    assert 0.0 < float(masks["W2"].mean()) < 1.0
    assert np.all(masks["W3"] == 1.0)


def test_diagonal_mask_is_more_restrictive_than_block_mask() -> None:
    block = connectivity_masks(
        input_dim=40,
        hidden1=20,
        hidden2=10,
        n_actions=4,
        variant="block10",
        blocks=5,
    )
    diagonal = connectivity_masks(
        input_dim=40,
        hidden1=20,
        hidden2=10,
        n_actions=4,
        variant="diagonal",
        blocks=10,
    )

    assert float(diagonal["W1"].mean()) < float(block["W1"].mean())
    assert float(diagonal["W2"].mean()) < float(block["W2"].mean())


def test_train_variant_reports_synthetic_accuracy() -> None:
    rng = np.random.default_rng(3)
    X = rng.normal(size=(72, 12)).astype(np.float32)
    y = (X[:, 0] + X[:, 1] > X[:, 6]).astype(np.int64)
    q = np.ones(72, dtype=np.float32)
    label_map = {0: "frontdoor", 1: "worker_general"}

    result = train_variant(
        X[:48],
        y[:48],
        q[:48],
        X[48:],
        y[48:],
        q[48:],
        label_map=label_map,
        variant="full",
        hidden1=12,
        hidden2=6,
        epochs=10,
        batch_size=16,
        patience=5,
        seed=7,
    )

    assert result["variant"] == "full"
    assert 0.0 <= result["val_acc"] <= 1.0
    assert result["epochs_run"] >= 1
    assert result["active_weight_fraction"]["W1"] == 1.0


def test_class_distribution_uses_label_names() -> None:
    counts = _class_distribution(
        np.asarray([0, 1, 1, 2], dtype=np.int64),
        {0: "frontdoor", 1: "worker_general", 2: "architect_general"},
    )

    assert counts == {
        "frontdoor": 1,
        "worker_general": 2,
        "architect_general": 1,
    }
