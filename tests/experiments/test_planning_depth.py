"""Software controls only; no endpoint or model is exercised."""
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


episode = load("planning_depth_episode", "scripts/experiments/planning_depth/episode.py")
orders = load("planning_depth_orders", "scripts/experiments/cf3c-task-level/environment.py")


def response(name=None, args=None, *, call_id="c1", text="RELEASED confirmation", reason=None):
    message = {"role": "assistant", "content": text if name is None else None}
    if name:
        message["tool_calls"] = [{"id": call_id, "type": "function",
                                  "function": {"name": name, "arguments": json.dumps(args)}}]
    return {"choices": [{"index": 0, "message": message,
                          "finish_reason": reason or ("tool_calls" if name else "stop")}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}}


def setup():
    service = orders.OrderService("order", 7, "receipt", "challenge", "confirmation")
    return service, SimpleNamespace(tools=orders.TOOLS, execute=service.execute, score=service.score)


def run(replies, **kwargs):
    service, environment = setup()
    captures, requests = [], []
    iterator = iter(replies)

    def complete(request, timeout):
        assert 0 < timeout <= 120
        requests.append(request)
        value = next(iterator)
        if isinstance(value, Exception):
            raise value
        return value

    result = episode.run_episode(complete, environment, [{"role": "user", "content": "release order"}],
                                 captures.append, model="pinned-model", seed=42, **kwargs)
    return result, service, captures, requests


def success():
    return [response("inspect_order", {"order": "order"}),
            response("release_order", {"receipt": "receipt", "challenge": "challenge"}, call_id="c2"),
            response()]


def test_stateful_success_retains_every_native_step():
    result, service, captures, requests = run(success())
    assert result["status"] == "GRADED" and result["score"]["correct"] is True
    assert service.released and result["total_completion_tokens"] == 15
    assert len(captures) == 8  # 3 requests/replies, 2 executed tools
    assert requests[1]["messages"][-1]["role"] == "tool"
    assert json.loads(requests[1]["messages"][-1]["content"])["challenge"] == "challenge"
    assert "observations" not in captures[1]  # snapshots cannot mutate after capture


def test_claiming_success_without_state_change_is_wrong():
    result, service, *_ = run([response()])
    assert result["status"] == "GRADED" and result["score"]["correct"] is False
    assert not service.released


def test_schema_error_can_be_repaired_without_mutation():
    bad = response("release_order", {"receipt": "receipt", "challenge": "challenge", "extra": "x"})
    replies = [bad, *success()]
    replies[1]["choices"][0]["message"]["tool_calls"][0]["id"] = "repair"
    result, service, *_ = run(replies)
    assert result["schema_rejections"] == result["repairs"] == 1
    assert result["score"]["correct"] and service.released


@pytest.mark.parametrize("kind", ["length", "filter", "wrong_role", "multi_choice", "bad_calls", "null_reply"])
def test_unknown_protocol_and_caps_never_grade_or_execute(kind):
    reply = response("inspect_order", {"order": "order"})
    if kind == "length":
        reply["choices"][0]["finish_reason"] = "length"
    elif kind == "filter":
        reply["choices"][0]["finish_reason"] = "content_filter"
    elif kind == "wrong_role":
        reply["choices"][0]["message"]["role"] = "tool"
    elif kind == "multi_choice":
        reply["choices"].append(reply["choices"][0].copy())
    elif kind == "bad_calls":
        reply["choices"][0]["message"]["tool_calls"] = {"bad": True}
    else:
        reply = None
    result, service, *_ = run([reply])
    assert result["status"] == "UNKNOWN" and result["score"] is None
    assert not service.inspected


def test_reused_call_id_cannot_repeat_effect():
    replies = success()
    replies[1]["choices"][0]["message"]["tool_calls"][0]["id"] = "c1"
    result, service, *_ = run(replies)
    assert result["reason"] == "invalid_native_response" and not service.released


def test_transport_failure_preserves_partial_usage_and_state():
    result, service, captures, _ = run([success()[0], OSError("connection lost")])
    assert result["status"] == "UNKNOWN" and not result["usage_complete"]
    assert result["observed_usage"]["completion_tokens"] == 5
    assert result["total_completion_tokens"] is None and service.inspected
    assert captures[-1]["event"] == "transport_error"


def test_turn_cap_is_unknown_even_after_successful_action():
    result, service, *_ = run(success(), max_turns=2)
    assert service.released and result["reason"] == "turn_cap" and result["score"] is None


def test_missing_usage_does_not_invent_zero_token_cost():
    replies = success()
    replies[0].pop("usage")
    result, *_ = run(replies)
    assert result["score"]["correct"] and result["total_completion_tokens"] is None
    assert result["observed_usage"]["completion_tokens"] == 10


def test_deadline_after_reply_prevents_tool_execution():
    times = iter([0, 0, 121, 121])
    result, service, *_ = run([success()[0]], clock=lambda: next(times))
    assert result["reason"] == "deadline" and not service.inspected


def test_capture_failure_prevents_execution():
    service, environment = setup()

    def capture(record):
        if record["event"] == "response":
            raise OSError("disk full")

    with pytest.raises(OSError, match="disk full"):
        episode.run_episode(lambda *_: success()[0], environment, [], capture, model="x", seed=42)
    assert not service.inspected


@pytest.mark.parametrize("kwargs", [{"max_turns": True}, {"max_tokens": 0}, {"timeout_s": float("nan")}])
def test_invalid_bounds_fail_before_request(kwargs):
    with pytest.raises(ValueError):
        run([], **kwargs)


def test_multiple_tools_do_not_speculate_state_changes():
    reply = success()[0]
    reply["choices"][0]["message"]["tool_calls"].extend(success()[1]["choices"][0]["message"]["tool_calls"])
    result, service, *_ = run([reply], max_turns=1)
    assert not service.inspected and not service.released and result["schema_rejections"] == 1


def test_duplicate_argument_is_rejected_before_execution():
    reply = success()[0]
    reply["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"] = '{"order":"other","order":"order"}'
    result, service, *_ = run([reply], max_turns=1)
    assert result["schema_rejections"] == 1 and not service.inspected


def test_empty_stopped_answer_is_unknown():
    result, *_ = run([response(text="  ")])
    assert result["status"] == "UNKNOWN" and result["reason"] == "empty_answer"
