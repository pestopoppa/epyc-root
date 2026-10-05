"""Non-inference route regressions for the OpenAI-compat model-discovery API.

Targets ``GET /v1/models`` (``list_models``) and ``GET /v1/models/{model_id}``
(``get_model``) in ``src/api/routes/openai_compat.py``. These endpoints serve
model/role *discovery* only — no LLM is invoked — so their status codes,
response schema, alias/dedup/ordering transformation, and the 404 error path
are fully exercisable with the model-served boundary faked out.

Isolation contract (per handoffs/active/integration-test-coverage.md):
    * FastAPI ``TestClient`` over a freshly built app (in-process, no network,
      never hits ``:8000``).
    * The one boundary these handlers touch — ``available_roles`` and its
      ``live_stack_role_records`` stack-priors artifact reader — is
      monkeypatched, so no deployment artifact, DB, model, or filesystem
      truth-source is consulted. Tests are deterministic regardless of what is
      actually deployed on the host.

These are mocked-only tests: no inference marker, safe for normal CI.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api import create_app
import src.api.routes.openai_compat as oc


@pytest.fixture
def app():
    """A fresh app instance; dependency overrides cleared after each test."""
    application = create_app()
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client


# ── GET /v1/models — schema + transformation (available_roles faked) ────────


class TestListModels:
    """``list_models`` faithfully maps ``available_roles()`` into OpenAI shape."""

    def test_returns_openai_list_envelope(self, client, monkeypatch):
        monkeypatch.setattr(
            oc, "available_roles", lambda: ["orchestrator", "architect", "worker", "frontdoor"]
        )

        response = client.get("/v1/models")

        assert response.status_code == 200
        data = response.json()
        assert data["object"] == "list"
        assert [entry["id"] for entry in data["data"]] == [
            "orchestrator",
            "architect",
            "worker",
            "frontdoor",
        ]

    def test_each_entry_has_model_metadata(self, client, monkeypatch):
        monkeypatch.setattr(oc, "available_roles", lambda: ["frontdoor"])

        entry = client.get("/v1/models").json()["data"][0]

        assert entry["id"] == "frontdoor"
        assert entry["object"] == "model"
        assert entry["owned_by"] == "orchestrator"
        assert isinstance(entry["created"], int)
        assert entry["created"] > 0

    def test_empty_role_set_yields_empty_data(self, client, monkeypatch):
        monkeypatch.setattr(oc, "available_roles", lambda: [])

        data = client.get("/v1/models").json()

        assert data["object"] == "list"
        assert data["data"] == []

    def test_preserves_order_from_available_roles(self, client, monkeypatch):
        ordered = ["frontdoor", "worker_general", "architect", "orchestrator"]
        monkeypatch.setattr(oc, "available_roles", lambda: ordered)

        ids = [entry["id"] for entry in client.get("/v1/models").json()["data"]]

        assert ids == ordered


# ── GET /v1/models/{model_id} — known/unknown handling ──────────────────────


class TestGetModel:
    """``get_model`` returns info for known roles and 404 for unknown ones."""

    def test_known_model_returns_info(self, client, monkeypatch):
        monkeypatch.setattr(oc, "available_roles", lambda: ["orchestrator", "frontdoor"])

        response = client.get("/v1/models/frontdoor")

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == "frontdoor"
        assert body["object"] == "model"
        assert body["owned_by"] == "orchestrator"

    def test_unknown_model_returns_404(self, client, monkeypatch):
        monkeypatch.setattr(oc, "available_roles", lambda: ["orchestrator"])

        response = client.get("/v1/models/does-not-exist")

        assert response.status_code == 404

    def test_404_detail_names_the_missing_model(self, client, monkeypatch):
        monkeypatch.setattr(oc, "available_roles", lambda: ["orchestrator"])

        detail = client.get("/v1/models/ghost-role").json()["detail"]

        assert "ghost-role" in detail
        assert "not found" in detail.lower()

    def test_alias_is_resolvable(self, client, monkeypatch):
        # The compatibility aliases must always be addressable by /v1/models/{id}.
        monkeypatch.setattr(
            oc, "available_roles", lambda: list(oc.COMPATIBILITY_MODEL_ALIASES)
        )

        for alias in oc.COMPATIBILITY_MODEL_ALIASES:
            assert client.get(f"/v1/models/{alias}").status_code == 200


# ── Real available_roles() logic (stack-priors boundary faked) ──────────────


class TestAvailableRolesLogic:
    """Exercise the real alias/dedup/fallback logic in ``available_roles``.

    Only the stack-priors artifact reader (``live_stack_role_records``) or the
    ``_live_stack_role_ids`` boundary is patched, so the merge, dedup, and
    degraded-fallback code paths run for real — surfaced through /v1/models.
    """

    def test_degraded_fallback_lists_only_compat_aliases(self, client, monkeypatch):
        # When the stack-priors artifact can't be read, _live_stack_role_ids
        # swallows the error and returns []; available_roles then degrades to
        # exactly the compatibility aliases.
        def _boom(*_args, **_kwargs):
            raise RuntimeError("stack priors artifact unavailable")

        monkeypatch.setattr(oc, "live_stack_role_records", _boom)

        ids = [entry["id"] for entry in client.get("/v1/models").json()["data"]]

        assert ids == list(oc.COMPATIBILITY_MODEL_ALIASES)

    def test_live_roles_appended_after_aliases(self, client, monkeypatch):
        monkeypatch.setattr(oc, "_live_stack_role_ids", lambda: ["zzz_live_role"])

        ids = [entry["id"] for entry in client.get("/v1/models").json()["data"]]

        # Aliases lead, live role follows.
        assert ids[: len(oc.COMPATIBILITY_MODEL_ALIASES)] == list(
            oc.COMPATIBILITY_MODEL_ALIASES
        )
        assert "zzz_live_role" in ids

    def test_duplicate_live_roles_are_deduped(self, client, monkeypatch):
        monkeypatch.setattr(
            oc, "_live_stack_role_ids", lambda: ["zzz_live_role", "zzz_live_role"]
        )

        ids = [entry["id"] for entry in client.get("/v1/models").json()["data"]]

        assert ids.count("zzz_live_role") == 1
        # No id is duplicated overall.
        assert len(ids) == len(set(ids))

    def test_get_model_resolves_a_live_role(self, client, monkeypatch):
        monkeypatch.setattr(oc, "_live_stack_role_ids", lambda: ["zzz_live_role"])

        assert client.get("/v1/models/zzz_live_role").status_code == 200
