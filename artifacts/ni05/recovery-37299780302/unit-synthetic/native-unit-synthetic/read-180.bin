"""Non-inference route regression for ``GET /config/attest``.

Targets ``attest_config`` in ``src/api/routes/config.py`` — a read-only
introspection endpoint that reports this worker's effective feature-flag state
and each flag's value source. It performs no inference and touches no model or
DB, so it is fully exercisable with the ``dep_features`` dependency overridden
to a synthetic ``Features`` instance.

Sibling test ``tests/unit/test_config_endpoint.py`` already covers the
``POST /config`` mutation path (localhost gate, unknown-key filtering, ipv6);
this file closes the untested ``GET /config/attest`` read path.

Isolation contract (per handoffs/active/integration-test-coverage.md):
    * FastAPI ``TestClient`` over a freshly built app (in-process, no network,
      never hits ``:8000``).
    * ``dep_features`` is dependency-overridden so the response is driven by a
      test-authored ``Features`` object, not by ambient process/global state.

Mocked-only test: no inference marker, safe for normal CI.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from src.api import create_app
from src.api.dependencies import dep_features
from src.features import Features


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setattr(
        "src.api.routes.config.publish_config_attestation",
        lambda current: None,
    )
    application = create_app()
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client


def _override_features(app, features_obj: Features) -> None:
    app.dependency_overrides[dep_features] = lambda: features_obj


class TestAttestConfig:
    """``GET /config/attest`` reports the injected flag state faithfully."""

    def test_returns_pid_flags_sources_keys(self, app, client):
        _override_features(app, Features(memrl=True))

        response = client.get("/config/attest")

        assert response.status_code == 200
        body = response.json()
        assert set(body.keys()) == {"pid", "flags", "sources"}

    def test_pid_is_this_worker(self, app, client):
        # TestClient runs the handler in-process, so os.getpid() must match.
        _override_features(app, Features())

        body = client.get("/config/attest").json()

        assert isinstance(body["pid"], int)
        assert body["pid"] == os.getpid()

    def test_flags_match_injected_features_summary(self, app, client):
        injected = Features(memrl=True)
        _override_features(app, injected)

        flags = client.get("/config/attest").json()["flags"]

        # The reported flag map is exactly the injected Features summary.
        assert flags == injected.summary()
        assert flags["memrl"] is True

    def test_flags_reflect_override_not_global_state(self, app, client):
        # Injecting memrl=False must surface as False regardless of any ambient
        # default — proves the response is driven by the overridden dependency.
        _override_features(app, Features(memrl=False))

        flags = client.get("/config/attest").json()["flags"]

        assert flags["memrl"] is False

    def test_sources_is_a_flag_keyed_mapping(self, app, client):
        injected = Features(memrl=True)
        _override_features(app, injected)

        sources = client.get("/config/attest").json()["sources"]

        assert isinstance(sources, dict)
        # feature_sources() reports a source for every known flag.
        assert set(injected.summary()).issubset(set(sources))

    def test_post_to_attest_is_method_not_allowed(self, app, client):
        _override_features(app, Features())

        # /config/attest is GET-only; POST belongs to the /config mutation route.
        response = client.post("/config/attest", json={})

        assert response.status_code == 405
