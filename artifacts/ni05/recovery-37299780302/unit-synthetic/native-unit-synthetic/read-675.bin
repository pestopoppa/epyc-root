"""recall() on the /v1 path, and the legacy fallback's failure contract.

Regression for the 2026-09-16 finding: `/v1/chat/completions` built its REPL
without a retriever, so `recall()` fell into `_recall_legacy`, which called a
non-existent `EpisodicStore.search_similar` (and `TaskEmbedder.embed`) and
swallowed the AttributeError into a bare `{"results": []}` — "recall broken"
looked like "no memories" for every /v1 client.

All tests are hermetic: a tmp-path EpisodicStore and a deterministic embedder
double. No embedding server, no production store.
"""

from __future__ import annotations

import json
import logging
from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np
import pytest

from src.repl_environment import REPLEnvironment

DIM = 8


class _FixtureEmbedder:
    """Deterministic TaskEmbedder double exposing only the real method names."""

    def __init__(self, *args, **kwargs):
        pass

    def embed_exploration(self, query: str, context_preview: str) -> np.ndarray:
        vec = np.zeros(DIM, dtype=np.float32)
        vec[0] = 1.0
        return vec

    def close(self) -> None:
        pass


def _unwrap(output: str) -> dict:
    if "<<<TOOL_OUTPUT>>>" in output:
        start = output.find("<<<TOOL_OUTPUT>>>") + len("<<<TOOL_OUTPUT>>>")
        output = output[start : output.find("<<<END_TOOL_OUTPUT>>>")]
    return json.loads(output)


@pytest.fixture
def fixture_store_cls(tmp_path):
    """A real EpisodicStore in tmp_path, seeded with one exploration memory."""
    from orchestration.repl_memory.episodic_store import EpisodicStore

    seed = EpisodicStore(db_path=tmp_path, embedding_dim=DIM)
    vec = np.zeros(DIM, dtype=np.float32)
    vec[0] = 1.0
    seed.store(
        embedding=vec,
        action="grep -n 'def main' src/",
        action_type="exploration",
        context={"objective": "find the entrypoint", "role": "worker_general"},
        outcome="success",
        initial_q=0.8,
    )
    seed.close()

    def _factory(*args, **kwargs):
        return EpisodicStore(db_path=tmp_path, embedding_dim=DIM)

    # The real store has no search_similar — the method the old fallback called.
    assert not hasattr(EpisodicStore, "search_similar")
    return _factory


@pytest.fixture
def legacy_backend(monkeypatch, fixture_store_cls):
    import orchestration.repl_memory.embedder as embedder_mod
    import orchestration.repl_memory.episodic_store as store_mod

    monkeypatch.setattr(store_mod, "EpisodicStore", fixture_store_cls)
    monkeypatch.setattr(embedder_mod, "TaskEmbedder", _FixtureEmbedder)


def test_legacy_fallback_uses_real_store_api(legacy_backend):
    repl = REPLEnvironment(context="some code")
    data = _unwrap(repl._recall("where is main?"))

    assert data["status"] == "ok"
    assert len(data["results"]) == 1
    hit = data["results"][0]
    assert hit["task"] == "find the entrypoint"
    assert hit["role_used"] == "worker_general"
    assert hit["q_value"] == pytest.approx(0.8)
    assert hit["similarity"] > 0.9


def test_legacy_fallback_failure_is_loud_and_explicit(monkeypatch, caplog):
    """A store lacking the search API must not look like 'no memories'."""
    import orchestration.repl_memory.embedder as embedder_mod
    import orchestration.repl_memory.episodic_store as store_mod

    class _StoreWithoutSearch:  # has neither search_similar nor retrieve_by_similarity
        def __init__(self, *a, **k):
            pass

        def close(self):
            pass

    monkeypatch.setattr(store_mod, "EpisodicStore", _StoreWithoutSearch)
    monkeypatch.setattr(embedder_mod, "TaskEmbedder", _FixtureEmbedder)

    repl = REPLEnvironment(context="x")
    with caplog.at_level(logging.ERROR, logger="src.repl_environment.routing"):
        data = _unwrap(repl._recall("anything"))

    assert data["status"] == "unavailable"
    assert data["results"] == []
    assert "AttributeError" in data["error"]
    assert any(
        r.levelno == logging.ERROR and "recall() legacy fallback FAILED" in r.getMessage()
        for r in caplog.records
    )


def test_retriever_failure_is_loud_and_explicit(caplog):
    retriever = MagicMock()
    retriever.retrieve_for_exploration.side_effect = RuntimeError("faiss desync")
    repl = REPLEnvironment(context="x", retriever=retriever)
    with caplog.at_level(logging.ERROR, logger="src.repl_environment.routing"):
        data = _unwrap(repl._recall("anything"))

    assert data["status"] == "unavailable"
    assert "faiss desync" in data["error"]
    assert any(r.levelno == logging.ERROR for r in caplog.records)


def test_repl_memrl_kwargs_passes_shared_retriever(monkeypatch):
    import src.api.services.memrl as memrl_mod
    from src.api.routes.openai_compat import _repl_memrl_kwargs

    calls = []
    monkeypatch.setattr(memrl_mod, "ensure_memrl_initialized", lambda s: calls.append(s) or True)
    router = SimpleNamespace(retriever=object())
    state = SimpleNamespace(hybrid_router=router)

    kwargs = _repl_memrl_kwargs(state)

    assert calls == [state]
    assert kwargs == {"retriever": router.retriever, "hybrid_router": router}

    off = _repl_memrl_kwargs(SimpleNamespace(hybrid_router=None))
    assert off == {"retriever": None, "hybrid_router": None}


def test_v1_route_repl_recall_returns_fixture_memories(monkeypatch, fixture_store_cls):
    """End to end through /v1/chat/completions: the REPL the route builds gets
    the shared retriever, and recall() on it returns the fixture store's rows."""
    from fastapi.testclient import TestClient

    import src.api.routes.openai_compat as compat
    import src.api.services.memrl as memrl_mod
    import src.llm_primitives as llm_primitives_module
    from orchestration.repl_memory.retriever import TwoPhaseRetriever
    from src.api import app
    from src.api.state import get_state, reset_state
    from src.features import reset_features

    retriever = TwoPhaseRetriever(store=fixture_store_cls(), embedder=_FixtureEmbedder())
    fake_router = SimpleNamespace(retriever=retriever)

    monkeypatch.setenv("ORCHESTRATOR_MOCK_MODE", "false")
    monkeypatch.setenv("ORCHESTRATOR_MEMRL", "false")  # keep startup off the real store
    reset_features()
    reset_state()

    captured = []
    real_repl = compat.REPLEnvironment

    def _capturing_repl(*args, **kwargs):
        repl = real_repl(*args, **kwargs)
        captured.append(repl)
        return repl

    monkeypatch.setattr(compat, "REPLEnvironment", _capturing_repl)
    monkeypatch.setattr(memrl_mod, "ensure_memrl_initialized", lambda s: True)

    primitives = MagicMock()
    primitives.llm_call.side_effect = lambda *a, **k: 'FINAL("done")'
    primitives.total_tokens_generated = 3
    monkeypatch.setattr(llm_primitives_module, "LLMPrimitives", lambda **_k: primitives)

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            state = get_state()
            if state.registry is None:
                state.registry = MagicMock()
            state.hybrid_router = fake_router
            r = client.post(
                "/v1/chat/completions",
                json={
                    "model": "frontdoor",
                    "messages": [{"role": "user", "content": "hello"}],
                    "x_disable_repl": False,
                },
            )
    finally:
        reset_features()

    assert r.status_code == 200, r.text
    assert captured, "route did not build a REPL"
    repl = captured[0]
    assert repl._retriever is retriever
    assert repl._hybrid_router is fake_router

    data = _unwrap(repl._recall("where is main?"))
    assert data["status"] == "ok"
    assert [h["task"] for h in data["results"]] == ["find the entrypoint"]
