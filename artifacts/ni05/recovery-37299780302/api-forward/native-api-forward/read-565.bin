#!/usr/bin/env python3
"""HS-OD-1 — body fields the API does not honour must not be accepted silently.

`OpenAIChatRequest` declared no extra-field policy, so pydantic v2's default
`extra='ignore'` silently discarded standard OpenAI fields. A JSON-mode client
got prose where it asked for schema-constrained JSON — with a 200 and no
diagnostic. The fix refuses any unhonoured field whose value would have changed
the output, and implements `max_completion_tokens` as the alias it is.

Both directions are pinned, per the standing lens: the refusal must fire on
semantic values, AND the compliant path must still pass — explicit no-op values
(n=1, penalty 0.0, response_format {"type":"text"}), benign non-semantic extras
(user, metadata), and plain requests must all be accepted. A refusal tested only
on its refusal path is indistinguishable from one that refuses everything.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.api.models.openai import OpenAIChatRequest

_MSGS = [{"role": "user", "content": "hi"}]


def _req(**extra):
    return OpenAIChatRequest.model_validate({"messages": _MSGS, **extra})


# -- refusal direction: semantic values are rejected, naming the field --------

@pytest.mark.parametrize(
    "field,value",
    [
        ("response_format", {"type": "json_object"}),
        ("response_format", {"type": "json_schema", "json_schema": {"name": "x"}}),
        ("n", 2),
        ("stop", ["\n\n"]),
        ("stop", "END"),
        ("logprobs", True),
        ("top_logprobs", 5),
        ("logit_bias", {"50256": -100}),
        ("presence_penalty", 0.5),
        ("frequency_penalty", -0.2),
        ("functions", [{"name": "f"}]),
        ("function_call", "auto"),
    ],
)
def test_semantic_value_is_refused_and_named(field, value):
    with pytest.raises(ValidationError) as exc:
        _req(**{field: value})
    text = str(exc.value)
    assert f"'{field}'" in text, "the 4xx must NAME the refused field"
    assert "HS-OD-1" in text


# -- compliant direction: no-ops and benign extras still pass -----------------

@pytest.mark.parametrize(
    "field,value",
    [
        ("response_format", {"type": "text"}),   # explicit default = current behaviour
        ("response_format", None),
        ("n", 1),
        ("stop", []),
        ("stop", None),
        ("logprobs", False),
        ("logit_bias", {}),
        ("presence_penalty", 0.0),
        ("frequency_penalty", 0),
        ("functions", []),
        ("function_call", None),
    ],
)
def test_explicit_noop_value_is_accepted(field, value):
    req = _req(**{field: value})
    assert req.messages[0].content == "hi"


def test_plain_request_unaffected():
    assert _req(temperature=0.7, max_tokens=64).max_tokens == 64


def test_benign_non_semantic_extras_still_ignored():
    # user/metadata/stream_options carry no output semantics; refusing them
    # would break well-behaved SDK clients for nothing.
    req = _req(user="abc", metadata={"k": "v"}, stream_options={"include_usage": True})
    assert req.messages[0].content == "hi"


# -- max_completion_tokens: implemented, not refused --------------------------

def test_max_completion_tokens_is_honoured_as_alias():
    assert _req(max_completion_tokens=512).max_tokens == 512


def test_max_completion_tokens_inherits_bounds():
    with pytest.raises(ValidationError):
        _req(max_completion_tokens=0)


def test_both_token_caps_refused():
    with pytest.raises(ValidationError) as exc:
        _req(max_tokens=64, max_completion_tokens=128)
    assert "max_completion_tokens" in str(exc.value)


def test_max_tokens_alone_still_works():
    assert _req(max_tokens=64).max_tokens == 64


# -- the seam itself returns a 4xx, not a 200 --------------------------------

def test_route_returns_422_not_prose():
    # Validation runs before the route body, so this needs no primitives/mock
    # plumbing: the seam must answer 4xx-naming-the-field, never 200-with-prose.
    from fastapi.testclient import TestClient

    from src.api import app

    with TestClient(app, raise_server_exceptions=False) as client:
        r = client.post(
            "/v1/chat/completions",
            json={
                "messages": _MSGS,
                "response_format": {"type": "json_object"},
            },
        )
    assert r.status_code == 422
    assert "response_format" in r.text
