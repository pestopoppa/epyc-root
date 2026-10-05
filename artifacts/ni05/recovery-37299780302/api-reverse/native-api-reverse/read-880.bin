import numpy as np
import pytest

from scripts.graph_router.train_routing_classifier_kl import _apply_role_dropout_targets


def test_role_dropout_drops_secondary_positive_roles_and_renormalizes() -> None:
    targets = np.asarray([[0.6, 0.3, 0.1], [0.5, 0.5, 0.0]], dtype=np.float32)
    rng = np.random.default_rng(7)

    dropped = _apply_role_dropout_targets(
        targets,
        rng=rng,
        rate=1.0,
        min_roles=1,
        max_roles=1,
    )

    assert np.allclose(targets.sum(axis=1), 1.0)
    assert np.allclose(dropped.sum(axis=1), 1.0)
    assert dropped[0, 0] > 0.0
    assert np.count_nonzero(dropped[0] == 0.0) == 1
    assert dropped[1, 0] > 0.0
    assert np.count_nonzero(dropped[1] == 0.0) == 2
    assert not np.shares_memory(targets, dropped)


def test_role_dropout_leaves_one_hot_and_disabled_targets_unchanged() -> None:
    targets = np.asarray([[1.0, 0.0, 0.0], [0.0, 0.25, 0.75]], dtype=np.float32)

    disabled = _apply_role_dropout_targets(
        targets,
        rng=np.random.default_rng(1),
        rate=0.0,
    )
    active = _apply_role_dropout_targets(
        targets,
        rng=np.random.default_rng(1),
        rate=1.0,
        min_roles=1,
        max_roles=1,
    )

    assert disabled is targets
    assert np.allclose(active[0], targets[0])
    assert np.allclose(active[1].sum(), 1.0)
    assert active[1, 2] > 0.0


@pytest.mark.parametrize(
    "kwargs",
    [
        {"rate": -0.1},
        {"rate": 1.1},
        {"rate": 0.5, "min_roles": 0},
        {"rate": 0.5, "min_roles": 2, "max_roles": 1},
    ],
)
def test_role_dropout_rejects_invalid_parameters(kwargs) -> None:
    targets = np.asarray([[0.5, 0.5]], dtype=np.float32)

    with pytest.raises(ValueError):
        _apply_role_dropout_targets(
            targets,
            rng=np.random.default_rng(1),
            **kwargs,
        )
