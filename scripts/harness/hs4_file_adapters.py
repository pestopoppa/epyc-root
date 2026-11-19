"""Synthetic-only adapter controls for the HS-4 file-task driver.

There is deliberately no HTTP or subprocess launcher here. The live grader
isolation boundary has not been proven; these adapters must not be used to
claim an actual run or SC86 measurement.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any


def repl_request(prompt: str, task_root: str, session_id: str, role: str,
                 max_turns: int) -> dict[str, Any]:
    """Build the current /chat forced-REPL request; sending is out of scope."""
    if (not all(isinstance(x, str) and x.strip() for x in (prompt, task_root, session_id, role))
            or not task_root.startswith("/") or type(max_turns) is not int
            or not 1 <= max_turns <= 100):
        raise ValueError("prompt, absolute task root, fresh session, role and turn cap required")
    return {"prompt": prompt, "task_root": task_root, "session_id": session_id,
            "force_role": role, "force_mode": "repl", "allow_delegation": False,
            "mock_mode": False, "real_mode": True, "max_turns": max_turns,
            "quiescent_after": True}


def _count(value: Any) -> int | None:
    return value if type(value) is int and value >= 0 else None


def repl_response(raw: dict[str, Any]) -> dict[str, Any]:
    """Keep native response and only exact whole-request generation counts."""
    if not isinstance(raw, dict) or not isinstance(raw.get("answer"), str):
        raise ValueError("invalid /chat response")
    prompt = _count(raw.get("prompt_tokens"))
    output = _count(raw.get("output_tokens_reported"))
    if raw.get("output_tokens_status") != "reported":
        output = None
    return {"answer": raw["answer"], "raw_response": deepcopy(raw),
            "executed_tools": deepcopy(raw.get("tool_timings")) if isinstance(raw.get("tool_timings"), list) else None,
            "tool_arguments_and_results": None,
            "prompt_tokens": prompt, "output_tokens": output,
            "generation_usage_complete": prompt is not None and output is not None,
            "cost_complete": False}


def opencode_session(session: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    """Retain all exported parts; never turn absent step usage into zero."""
    if not isinstance(session, dict) or not isinstance(session.get("messages"), list) or not isinstance(events, list):
        raise ValueError("invalid OpenCode export")
    parts = []
    last_answer = None
    for message in session["messages"]:
        if not isinstance(message, dict) or not isinstance(message.get("parts"), list):
            raise ValueError("malformed OpenCode message")
        parts.extend(message["parts"])
        info = message.get("info")
        if isinstance(info, dict) and info.get("role") == "assistant":
            texts = [p.get("text") for p in message["parts"]
                     if isinstance(p, dict) and p.get("type") == "text" and isinstance(p.get("text"), str)]
            if texts:
                last_answer = "\n".join(texts)
    if any(not isinstance(p, dict) for p in parts):
        raise ValueError("malformed OpenCode part")
    tools = [deepcopy(p) for p in parts if p.get("type") == "tool"]
    steps = [p for p in parts if p.get("type") == "step-finish"]
    prompt = output = 0
    complete = bool(steps)
    for step in steps:
        t = step.get("tokens")
        cache = t.get("cache") if isinstance(t, dict) else None
        values = ([t.get("input"), t.get("output"), t.get("reasoning"),
                   cache.get("read"), cache.get("write")]
                  if isinstance(t, dict) and isinstance(cache, dict) else [])
        if len(values) != 5 or any(_count(x) is None for x in values):
            complete = False
            continue
        prompt += values[0] + values[3] + values[4]
        output += values[1] + values[2]
    return {"answer": last_answer, "session": deepcopy(session), "events": deepcopy(events),
            "tool_parts": tools, "prompt_tokens": prompt if complete else None,
            "output_tokens": output if complete else None, "cost_complete": False,
            "cost_note": "step totals require tap parity and coverage of all calls before completeness"}


class FakeTransport:
    """In-memory transport for adapter conformance only; cannot send requests."""

    def __init__(self, response: dict[str, Any]):
        self.response = deepcopy(response)
        self.requests: list[dict[str, Any]] = []

    def post(self, body: dict[str, Any]) -> dict[str, Any]:
        self.requests.append(deepcopy(body))
        return deepcopy(self.response)


def exercise_repl(fake: FakeTransport, body: dict[str, Any]) -> dict[str, Any]:
    if type(fake) is not FakeTransport:
        raise TypeError("synthetic-only transport required")
    return repl_response(fake.post(body))
