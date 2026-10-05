#!/usr/bin/env python3
"""A one-word answer the model emits unquoted must not be dropped by /v1.

Live repro (2026-09-24, orchestrator 8a0c0944): POST /v1/chat/completions
``{"model":"frontdoor","messages":[{"role":"user","content":"Reply with the
single word OK."}],"max_tokens":1024}`` returned ``content ""`` with
``finish_reason "stop"``. The inference tap showed the frontdoor emitting
``FINAL(yes)`` / ``FINAL(OK)`` — unquoted — which executes as
``NameError: name 'OK' is not defined``. The /v1 REPL loop never feeds
``last_error`` back, so every turn replayed the same NameError and the route
returned the empty ``response_text``. "hello" survived only because the model
happened to quote it.

These tests pin the exact repro shape through the real route and the real
REPLEnvironment, with only the backend replaced.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.api import app
from src.api.state import get_state, reset_state
from src.features import reset_features


def _install_primitives(monkeypatch, *, llm_call):
    primitives = MagicMock()
    primitives.llm_call.side_effect = llm_call
    primitives.total_tokens_generated = 6

    import src.llm_primitives as llm_primitives_module

    monkeypatch.setattr(
        llm_primitives_module, "LLMPrimitives", lambda **_kwargs: primitives
    )
    return primitives


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("ORCHESTRATOR_MOCK_MODE", "false")
    reset_features()
    reset_state()
    get_state()
    with TestClient(app, raise_server_exceptions=False) as c:
        state = get_state()
        if state.registry is None:
            state.registry = MagicMock()
        yield c
    reset_features()


def _repro_body(word: str = "OK", **overrides):
    body = {
        "model": "frontdoor",
        "messages": [
            {"role": "user", "content": f"Reply with the single word {word}."}
        ],
        "max_tokens": 1024,
    }
    body.update(overrides)
    return body


def _stream_text(r) -> str:
    events = [
        json.loads(line[6:])
        for line in r.text.splitlines()
        if line.startswith("data: ") and line[6:].strip() not in ("", "[DONE]")
    ]
    assert not any("error" in e for e in events), events
    return "".join(
        c.get("delta", {}).get("content", "")
        for e in events
        for c in e.get("choices", [])
    )


@pytest.mark.parametrize(
    "word,raw",
    [
        ("OK", "FINAL(OK)"),  # the live repro
        ("yes", "FINAL(yes)"),  # verbatim from the inference tap
        ("Done", "FINAL(Done)"),
        ("OK", "OK"),  # bare reply -> auto_wrap_final -> FINAL(OK)
    ],
)
def test_unquoted_one_word_final_is_returned_not_dropped(client, monkeypatch, word, raw):
    primitives = _install_primitives(monkeypatch, llm_call=lambda *a, **k: raw)

    r = client.post("/v1/chat/completions", json=_repro_body(word))

    assert r.status_code == 200
    choice = r.json()["choices"][0]
    assert choice["message"]["content"] == word, (
        f"{raw!r} was dropped: the route returned {choice['message']['content']!r}"
    )
    assert choice["finish_reason"] == "stop"
    # Rescued on the first turn — not by burning the remaining turns.
    assert primitives.llm_call.call_count == 1


def test_unquoted_one_word_final_streaming(client, monkeypatch):
    _install_primitives(monkeypatch, llm_call=lambda *a, **k: "FINAL(OK)")

    r = client.post("/v1/chat/completions", json=_repro_body(stream=True))

    assert r.status_code == 200
    assert _stream_text(r) == "OK"


def test_quoted_final_is_unchanged(client, monkeypatch):
    """The already-working shape ("hello" through the orchestrator)."""
    _install_primitives(monkeypatch, llm_call=lambda *a, **k: 'FINAL("hello")')

    r = client.post("/v1/chat/completions", json=_repro_body("hello"))

    assert r.json()["choices"][0]["message"]["content"] == "hello"


def test_placeholder_name_is_not_turned_into_a_literal(client, monkeypatch):
    """``FINAL(answer)`` with nothing assigned is a forgotten assignment, not a
    one-word reply: it must NOT come back as the literal text "answer"."""
    _install_primitives(monkeypatch, llm_call=lambda *a, **k: "FINAL(answer)")

    r = client.post("/v1/chat/completions", json=_repro_body("OK"))

    assert r.status_code == 200
    assert r.json()["choices"][0]["message"]["content"] != "answer"
