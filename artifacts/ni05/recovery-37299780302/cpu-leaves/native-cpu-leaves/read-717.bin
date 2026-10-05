"""Tests for routing model bootstrap helpers."""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import patch

from src.api.services.routing_models import (
    RoutingModelBundle,
    load_frontdoor_verifier,
    load_routing_classifier,
)


class _Features:
    def __init__(self, routing_classifier: bool = False) -> None:
        self.routing_classifier = routing_classifier


class _Classifier:
    param_count = 3
    n_actions = 2

    @classmethod
    def load(cls, _path: Path):
        return cls()


class _Verifier:
    param_count = 4

    @classmethod
    def load(cls, _path: Path):
        return cls()


def test_routing_model_bundle_router_kwargs() -> None:
    bundle = RoutingModelBundle(
        graph_router="graph",
        routing_classifier="classifier",
        frontdoor_verifier="verifier",
    )

    assert bundle.hybrid_router_kwargs() == {
        "graph_router": "graph",
        "routing_classifier": "classifier",
        "frontdoor_verifier": "verifier",
    }


def test_load_routing_classifier_disabled() -> None:
    assert load_routing_classifier(_Features(False), logging.getLogger(__name__)) is None


def test_load_routing_classifier_missing_weights(tmp_path) -> None:
    logger = logging.getLogger(__name__)

    assert load_routing_classifier(
        _Features(True),
        logger,
        {"ROUTING_CLASSIFIER_WEIGHTS": str(tmp_path / "missing.npz")},
    ) is None


def test_load_routing_classifier_loads_existing_weights(tmp_path) -> None:
    weights = tmp_path / "routing.npz"
    weights.write_bytes(b"weights")
    module = type(
        "module",
        (),
        {
            "DEFAULT_WEIGHTS_PATH": weights,
            "RoutingClassifier": _Classifier,
        },
    )

    with patch.dict("sys.modules", {"orchestration.repl_memory.routing_classifier": module}):
        loaded = load_routing_classifier(
            _Features(True),
            logging.getLogger(__name__),
            {"ROUTING_CLASSIFIER_WEIGHTS": str(weights)},
        )

    assert isinstance(loaded, _Classifier)


def test_load_frontdoor_verifier_default_off() -> None:
    assert load_frontdoor_verifier(logging.getLogger(__name__), {}) is None


def test_load_frontdoor_verifier_loads_when_gated(tmp_path) -> None:
    weights = tmp_path / "verifier.npz"
    weights.write_bytes(b"weights")
    module = type(
        "module",
        (),
        {
            "DEFAULT_WEIGHTS_PATH": weights,
            "VerifierHead": _Verifier,
        },
    )

    with patch.dict("sys.modules", {"orchestration.repl_memory.verifier_head": module}):
        loaded = load_frontdoor_verifier(
            logging.getLogger(__name__),
            {
                "ORCHESTRATOR_FRONTDOOR_VERIFIER_GATE": "1",
                "FRONTDOOR_VERIFIER_WEIGHTS": str(weights),
            },
        )

    assert isinstance(loaded, _Verifier)
