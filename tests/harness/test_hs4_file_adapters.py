import pytest

from scripts.harness.hs4_file_adapters import (
    FakeTransport, exercise_repl, opencode_session, repl_request,
)


def test_repl_fake_transport_retains_response_and_exact_usage():
    body = repl_request("Find the file", "/tmp/public", "fresh-1", "frontdoor", 5)
    raw = {"answer": "value", "prompt_tokens": 10, "output_tokens_reported": 3,
           "output_tokens_status": "reported", "tool_timings": [{"tool_name": "read", "success": True}]}
    fake = FakeTransport(raw)
    out = exercise_repl(fake, body)
    assert fake.requests[0]["force_mode"] == "repl"
    assert fake.requests[0]["allow_delegation"] is False
    assert out["raw_response"] == raw and out["answer"] == "value"
    assert out["prompt_tokens"] == 10 and out["output_tokens"] == 3
    assert out["tool_arguments_and_results"] is None
    assert out["generation_usage_complete"] is True
    assert out["cost_complete"] is False


def test_repl_refuses_transport_substitution_and_missing_usage():
    body = repl_request("Find", "/tmp/public", "fresh", "frontdoor", 5)
    with pytest.raises(TypeError):
        exercise_repl(object(), body)
    out = exercise_repl(FakeTransport({"answer": "x", "prompt_tokens": None,
                                       "output_tokens_reported": 4,
                                       "output_tokens_status": "unknown"}), body)
    assert out["prompt_tokens"] is None and out["output_tokens"] is None
    assert not out["cost_complete"]
    with pytest.raises(ValueError):
        repl_request("x", "relative", "s", "frontdoor", True)


def test_opencode_retains_all_parts_and_refuses_missing_step_usage():
    session = {"messages": [{"info": {"role": "assistant"}, "parts": [
        {"type": "tool", "tool": "read", "state": {"status": "completed", "input": {"path": "a"}, "output": "one"}},
        {"type": "step-finish", "tokens": {"input": 2, "output": 3, "reasoning": 1, "cache": {"read": 4, "write": 5}}},
        {"type": "text", "text": "final"},
    ]}]}
    events = [{"type": "tool_use", "sessionID": "synthetic"}]
    out = opencode_session(session, events)
    assert out["answer"] == "final" and out["session"] == session and out["events"] == events
    assert out["tool_parts"][0]["state"]["output"] == "one"
    assert out["prompt_tokens"] == 11 and out["output_tokens"] == 4
    assert out["cost_complete"] is False
    session["messages"][0]["parts"].append({"type": "step-finish", "tokens": {}})
    out = opencode_session(session, events)
    assert out["prompt_tokens"] is None and out["output_tokens"] is None
