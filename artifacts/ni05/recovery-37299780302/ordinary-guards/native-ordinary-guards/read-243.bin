"""CME-1: the llm_judge transport as a reusable text call, and the per-nugget refusal.

Behaviour pinned here:

* a ``per_nugget`` item (BEAM) is refused LOUDLY by the boolean judge, before any
  HTTP call, because one boolean would binarise its 0/0.5/1 nugget scale;
* the boolean judge's wire payload is unchanged by the refactor (max_tokens 8,
  boolean output schema, one request);
* ``request_llm_judge_text`` returns the raw verdict with its case preserved,
  forwards the caller's max_tokens and output schema, and keeps the fail-closed
  error taxonomy (empty or error answers raise and are never returned as text).

Every HTTP call is mocked. Nothing here opens a socket.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import httpx
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "benchmark"))

import debug_scorer  # noqa: E402
from debug_scorer import (  # noqa: E402
    ScoringUnavailableError,
    request_llm_judge_text,
    score_answer,
)

NUGGET_SCHEMA = {
    "type": "object",
    "properties": {"score": {"type": "number"}, "reason": {"type": "string"}},
    "required": ["score"],
}


class _Resp:
    def __init__(self, body: dict[str, Any]) -> None:
        self._body = body

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._body


@pytest.fixture
def recorder(monkeypatch):
    calls: list[dict[str, Any]] = []
    replies: list[dict[str, Any]] = []

    def fake_post(url, json=None, timeout=None):  # noqa: A002 - mirrors httpx
        calls.append({"url": url, "json": json, "timeout": timeout})
        return _Resp(replies.pop(0))

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.delenv("ORCHESTRATOR_API_URL", raising=False)
    return calls, replies


def test_per_nugget_item_is_refused_before_any_request(recorder):
    calls, _ = recorder
    with pytest.raises(ScoringUnavailableError, match="llm_judge_per_nugget_item"):
        score_answer(
            answer="The user prefers tea.",
            expected="tea",  # would even hit the substring fast path
            scoring_method="llm_judge",
            scoring_config={"per_nugget": True, "nuggets": ["mentions tea"]},
        )
    assert calls == []


def test_boolean_judge_wire_payload_is_unchanged(recorder):
    calls, replies = recorder
    replies.append({"answer": "True"})
    assert score_answer("an unrelated long answer", "reference", "llm_judge", {}) is True
    assert len(calls) == 1
    payload = calls[0]["json"]
    assert calls[0]["url"] == "http://localhost:8000/chat"
    assert payload["max_tokens"] == 8
    assert payload["output_schema"] == {"type": "boolean"}
    assert payload["force_mode"] == "direct"
    assert "REFERENCE ANSWER:\nreference" in payload["prompt"]

    replies.append({"answer": "false"})
    assert score_answer("an unrelated long answer", "reference", "llm_judge", {}) is False


def test_text_call_preserves_case_and_forwards_contract(recorder):
    calls, replies = recorder
    replies.append({"answer": '  {"score": 0.5, "Reason": "Partial"}  '})
    text = request_llm_judge_text(
        "PROMPT", {"timeout": 12}, max_tokens=256, output_schema=NUGGET_SCHEMA)
    assert text == '{"score": 0.5, "Reason": "Partial"}'
    payload = calls[0]["json"]
    assert payload["prompt"] == "PROMPT"
    assert payload["max_tokens"] == 256
    assert payload["output_schema"] == NUGGET_SCHEMA
    assert payload["timeout_s"] == 12


def test_text_call_direct_override_speaks_openai_protocol(recorder):
    calls, replies = recorder
    replies.append({"choices": [{"message": {"content": '{"score": 1.0}'}}]})
    text = request_llm_judge_text(
        "P", {"judge_host": "127.0.0.1", "judge_port": 8082},
        max_tokens=128, output_schema=None)
    assert text == '{"score": 1.0}'
    assert calls[0]["url"] == "http://127.0.0.1:8082/v1/chat/completions"
    assert calls[0]["json"]["max_tokens"] == 128


@pytest.mark.parametrize("body, category", [
    ({"answer": ""}, "llm_judge_empty_answer"),
    ({"answer": "x", "error": "backend down"}, "llm_judge_backend_error"),
])
def test_text_call_fails_closed(recorder, body, category):
    _, replies = recorder
    replies.append(body)
    with pytest.raises(ScoringUnavailableError, match=category):
        request_llm_judge_text("P", {}, max_tokens=64, output_schema=None)


def test_text_call_is_public_api():
    assert "request_llm_judge_text" in dir(debug_scorer)
    assert not request_llm_judge_text.__name__.startswith("_")
