"""B2 context compression on /v1 is fail-open; the fallback must be VISIBLE.

House rule: a fail-open default conceals its own corruption. The route keeps
falling back to the unfolded history when the compressor raises (policy, not
changed here), but the fallback is now counted on
``openai_compat.CONTEXT_COMPRESSION_FALLBACK_COUNTS`` and logged as a
``context_compression_fallback exc_type=...`` WARNING. These tests use a
raising fake compressor and a MagicMock LLM backend -- zero inference.
"""

from __future__ import annotations

import json
import logging
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

import src.context_compression as context_compression_module
from src.api import app
from src.api.models import OpenAIMessage
from src.api.routes import openai_compat
from src.api.state import get_state, reset_state
from src.features import reset_features


class _BoomError(RuntimeError):
    pass


class _RaisingCompressor:
    def __init__(self, *_a, **_kw):
        pass

    def compress(self, messages):
        # Mutate the input first: the fallback must still serve clean history.
        for m in messages:
            m["content"] = "CORRUPTED"
        raise _BoomError("compressor exploded")


def _long_history(n: int = 10) -> list[dict[str, object]]:
    turns: list[dict[str, object]] = [{"role": "system", "content": "You are helpful."}]
    for i in range(n):
        turns.append({"role": "user", "content": f"q{i}"})
        turns.append({"role": "assistant", "content": f"a{i}"})
    turns.append({"role": "user", "content": "final question"})
    return turns


@pytest.fixture
def raising_compressor(monkeypatch):
    monkeypatch.setenv("ORCHESTRATOR_FEATURE_CONTEXT_COMPRESSION", "1")
    reset_features()
    monkeypatch.setattr(context_compression_module, "ContextCompressor", _RaisingCompressor)
    monkeypatch.setattr(
        openai_compat, "CONTEXT_COMPRESSION_FALLBACK_COUNTS", {"total": 0}, raising=False
    )
    yield
    reset_features()


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("ORCHESTRATOR_MOCK_MODE", "false")
    reset_state()
    get_state()
    with TestClient(app, raise_server_exceptions=False) as c:
        state = get_state()
        if state.registry is None:
            state.registry = MagicMock()
        yield c


def _install_fake_backend(monkeypatch, answer: str = "the answer") -> MagicMock:
    primitives = MagicMock()
    primitives.llm_call.return_value = answer
    primitives.total_tokens_generated = 7
    import src.llm_primitives as llm_primitives_module

    monkeypatch.setattr(llm_primitives_module, "LLMPrimitives", lambda **_kw: primitives)
    return primitives


def test_helper_counts_logs_and_returns_unfolded_history(raising_compressor, caplog):
    history = [OpenAIMessage(**m) for m in _long_history()[:-1]]
    assert len(history) > 8

    with caplog.at_level(logging.WARNING, logger="src.api.routes.openai_compat"):
        out = openai_compat._compressed_history_dicts(history)

    # Unfolded history is still served, untouched by the compressor's mutation.
    assert out == [openai_compat._history_message_dict(m) for m in history]
    assert all(d["content"] != "CORRUPTED" for d in out)

    counts = openai_compat.CONTEXT_COMPRESSION_FALLBACK_COUNTS
    assert counts["total"] == 1
    assert counts["_BoomError"] == 1

    records = [r for r in caplog.records if "context_compression_fallback" in r.getMessage()]
    assert len(records) == 1
    assert records[0].levelno == logging.WARNING
    assert "exc_type=_BoomError" in records[0].getMessage()


def test_helper_is_a_no_op_when_history_is_short(raising_compressor):
    history = [OpenAIMessage(**m) for m in _long_history(2)[:-1]]
    assert len(history) <= 8
    out = openai_compat._compressed_history_dicts(history)
    assert out == [openai_compat._history_message_dict(m) for m in history]
    assert openai_compat.CONTEXT_COMPRESSION_FALLBACK_COUNTS == {"total": 0}


@pytest.mark.parametrize("stream", [False, True], ids=["nonstream", "stream"])
def test_route_fallback_is_visible_and_request_still_succeeds(
    client, monkeypatch, raising_compressor, caplog, stream
):
    primitives = _install_fake_backend(monkeypatch)
    body = {
        "model": "frontdoor",
        "messages": _long_history(),
        "x_disable_repl": True,
        "stream": stream,
    }
    with caplog.at_level(logging.WARNING, logger="src.api.routes.openai_compat"):
        r = client.post("/v1/chat/completions", json=body)

    assert r.status_code == 200
    if stream:
        # SSE streams one character per delta; reassemble before asserting.
        deltas = []
        for line in r.text.splitlines():
            if line.startswith("data: ") and line != "data: [DONE]":
                for choice in json.loads(line[6:]).get("choices", []):
                    deltas.append(choice.get("delta", {}).get("content") or "")
        assert "".join(deltas) == "the answer"
    else:
        assert r.json()["choices"][0]["message"]["content"] == "the answer"

    # The fallback fired exactly once and is observable.
    assert openai_compat.CONTEXT_COMPRESSION_FALLBACK_COUNTS["total"] == 1
    assert openai_compat.CONTEXT_COMPRESSION_FALLBACK_COUNTS["_BoomError"] == 1
    assert any(
        "context_compression_fallback exc_type=_BoomError" in rec.getMessage()
        for rec in caplog.records
    )

    # The unfolded (not corrupted) history reached the backend.
    assert primitives.llm_call.called
    joined = " ".join(
        str(a) for c in primitives.llm_call.call_args_list for a in (*c.args, *c.kwargs.values())
    )
    assert "CORRUPTED" not in joined
    assert "q9" in joined
