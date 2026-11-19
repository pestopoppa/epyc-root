"""Offline test of native-envelope contracts, the fixed matrix and the finite environment."""

import json
from copy import deepcopy

import pytest
import runner
from environment import TOOLS, OrderService
from jinja2 import Environment


@pytest.fixture(scope="module")
def sealed():
    return runner.verify()


@pytest.fixture(scope="module")
def template():
    return Environment().from_string(runner.live.TEMPLATE.read_text())


def render(template, request):
    messages = deepcopy(request["messages"])
    for message in messages:
        for call in message.get("tool_calls") or []:
            call["function"]["arguments"] = json.loads(call["function"]["arguments"])
    return template.render(
        messages=messages,
        tools=request["tools"],
        add_generation_prompt=True,
        **request["chat_template_kwargs"],
    )


def test_fixed_paired_matrix(sealed, template):
    _, policies, _, cases, rows = sealed
    assert len(rows) == len({row["unit"] for row in rows}) == 18
    for row in rows:
        case = cases[row["case"]]
        assert case["seed"] == row["seed"]
        original = policies.archive(case)
        selected, receipt = policies.select(original, row["arm"])
        witness = policies.verify_structured(
            case, original, selected, row["arm"], receipt
        )
        request = runner.request_for(selected, row["seed"])
        prompt = render(template, request)
        policies.verify_render(case, selected, prompt, witness)
        assert (case["receipt"] in prompt) == witness["archive_receipt_exposed"]
        assert case["challenge"] not in prompt and case["confirmation"] not in prompt
        assert receipt["pairs_fixed"] == receipt["compaction_model_calls"] == 0
        assert receipt["active"] is (row["arm"] != "A0")
        if row["arm"].startswith("A1-"):
            assert receipt["production_stubbed"] == 6
            assert selected[:4] == original[:4] and selected[-7:] == original[-7:]
        broken = (
            prompt.replace(case["receipt"], "")
            if case["receipt"] in prompt
            else prompt + case["receipt"]
        )
        with pytest.raises(ValueError, match="native receipt exposure"):
            policies.verify_render(case, selected, broken, witness)


def call(name, arguments, call_id):
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(arguments)},
    }


def test_environment_progression_and_oracle(sealed):
    _, _, _, cases, _ = sealed
    case = cases["archive-reasoning"]
    service = OrderService(
        **{
            key: case[key]
            for key in ("order", "desk", "receipt", "challenge", "confirmation")
        }
    )
    correct_args = {"receipt": case["receipt"], "challenge": case["challenge"]}
    final = f"RELEASED {case['confirmation']}"
    assert not service.score(final)["correct"]
    _, events = service.execute([call("release_order", correct_args, "before")])
    assert events[0]["outcome"] == "rejected"
    obs, events = service.execute(
        [call("inspect_order", {"order": case["order"]}, "check")]
    )
    assert events[0]["outcome"] == "inspected"
    assert json.loads(obs[0]["content"]) == {
        "desk": case["desk"],
        "challenge": case["challenge"],
    }
    bad, events = service.execute(
        [call("release_order", {**correct_args, "receipt": "wrong"}, "wrong")]
    )
    assert (
        events[0]["outcome"] == "rejected"
        and case["confirmation"] not in bad[0]["content"]
    )
    obs, events = service.execute([call("release_order", correct_args, "right")])
    assert events[0]["outcome"] == "released"
    assert json.loads(obs[0]["content"]) == {"confirmation": case["confirmation"]}
    assert (
        service.score(final)["correct"]
        and not service.score("RELEASED wrong")["correct"]
    )
    assert service.score("BLOCKED")["status"] == "abstained"


def reply(*, calls=None, content="", finish="stop"):
    message = {"role": "assistant", "content": content}
    if calls:
        message["tool_calls"] = calls
    return {
        "model": runner.live.MODEL.name,
        "choices": [{"finish_reason": finish, "message": message}],
        "usage": {"prompt_tokens": 73, "completion_tokens": 10, "total_tokens": 83},
    }


def wire(template, replies, requests):
    def fake(folder, label, path, payload, key, deadline, task_deadline):
        if label == "template":
            return {"prompt": render(template, payload)}
        if label == "tokenize":
            return {"tokens": list(range(73))}
        assert path == "/v1/chat/completions"
        requests.append(deepcopy(payload))
        return next(replies)

    return fake


def test_live_action_contract_growing_history_and_tokens(
    sealed, template, tmp_path, monkeypatch
):
    _, policies, _, cases, rows = sealed
    row = next(
        row
        for row in rows
        if row["case"] == "archive-reasoning" and row["arm"] == "A1-k12"
    )
    case = cases[row["case"]]
    requests = []
    replies = iter(
        (
            reply(
                calls=[call("inspect_order", {"order": case["order"]}, "inspect")],
                content="Follow the archive trail from ArchiveHead03 and ArchiveThinking04.",
                finish="tool_calls",
            ),
            reply(
                calls=[
                    call(
                        "release_order",
                        {"receipt": case["receipt"], "challenge": case["challenge"]},
                        "release",
                    )
                ],
                finish="tool_calls",
            ),
            reply(content=f"RELEASED {case['confirmation']}"),
        )
    )
    monkeypatch.setattr(runner, "post", wire(template, replies, requests))
    record = runner.trajectory(
        tmp_path / "flow", row, case, policies, "unused", float("inf"), "packet"
    )
    assert (record["status"], record["correct"], record["live_tools_executed"]) == (
        "graded",
        True,
        2,
    )
    assert [request["seed"] for request in requests] == [
        row["seed"] + i for i in range(3)
    ]
    assert [len(request["messages"]) for request in requests] == [23, 25, 27]
    assert record["generation_requests_started"] == 3
    assert record["usage_complete"] is True
    assert record["observed_usage"] == {
        "prompt_tokens": 219,
        "completion_tokens": 30,
        "total_tokens": 249,
    }
    assert all(turn["policy"]["production_stubbed"] >= 6 for turn in record["turns"])
    assert case["challenge"] not in json.dumps(requests[0])
    assert case["challenge"] in requests[1]["messages"][-1]["content"]
    assert render(template, requests[1]).count("ArchiveThinking04") == 2
    assert case["confirmation"] not in json.dumps(requests[1])
    assert case["confirmation"] in requests[2]["messages"][-1]["content"]
    assert len(record["turns"][2]["receipt_occurrences"]) == 2
    assert record["evidence_sha256"]["turn-01/ACTION.json"]


@pytest.mark.parametrize(
    "mode, outcome, finish",
    [
        ("length", "NA", "decode_cap"),
        ("cap", "NA", "turn_cap"),
        ("context", "NA", "context_budget"),
        ("task-wall", "NA", "task_wall_budget"),
        ("empty", "NA", "empty_answer"),
        ("stop", "abstained", "stop"),
        ("incorrect", "graded", "stop"),
        ("invalid", "UNKNOWN", "instrument_failure"),
    ],
)
def test_terminal_outcomes(
    sealed, template, tmp_path, monkeypatch, mode, outcome, finish
):
    _, policies, _, cases, rows = sealed
    row = rows[0]
    case = cases[row["case"]]
    if mode == "cap":
        replies = [
            reply(
                calls=[call("inspect_order", {"order": case["order"]}, f"call-{n}")],
                finish="tool_calls",
            )
            for n in range(runner.MAX_TURNS)
        ]
    elif mode == "invalid":
        replies = [{**reply(), "usage": {"prompt_tokens": 74}}]
    else:
        replies = [
            reply(
                finish="length" if mode == "length" else "stop",
                content={"stop": "BLOCKED", "incorrect": "RELEASED invented"}.get(
                    mode, ""
                ),
            )
        ]
    fake = wire(template, iter(replies), [])

    def send(*args):
        if mode == "task-wall":
            raise runner.TaskDeadline()
        if mode == "context" and args[1] == "tokenize":
            return {"tokens": list(range(runner.CONTEXT_TOKENS))}
        return fake(*args)

    monkeypatch.setattr(runner, "post", send)
    result = runner.trajectory(
        tmp_path / mode, row, case, policies, "unused", float("inf"), "packet"
    )
    assert (result["status"], result["finish_reason"]) == (outcome, finish)
    assert result["correct"] is (None if outcome == "UNKNOWN" else False)
    assert result["non_termination"] == (
        None if outcome == "UNKNOWN" else int(outcome == "NA")
    )
    summary = runner.summarize(rows, [result], policies.ARMS)
    assert summary["completed"] == int(outcome != "UNKNOWN")
    assert (
        summary["paired"][rows[1]["case"]]["arms"][rows[1]["arm"]]["status"]
        == "unattempted"
    )


def test_source_pin_and_row_window_contract(sealed):
    inputs, policies, _, _, rows = sealed
    spec = runner.live.read_json(runner.HERE / "spec.json")
    assert inputs["source"] == runner.BASE
    assert inputs["model_stat"] == runner.live.file_identity(runner.live.MODEL)
    assert spec["id"] == runner.ROW and spec["handoff_task"].endswith(":CF-3c-T1")
    assert spec["estimate_s"] == spec["max_window_s"] == runner.WINDOW_S
    assert spec["max_window_s"] >= spec["min_window_s"] + 300
    assert spec["min_window_s"] >= 90 + 160 + 20 + len(rows) * runner.TASK_S + 12
    assert len(policies.ARMS) == 6 and len(TOOLS) == 2


def test_inflight_timeout_preserves_cost_lower_bound(
    sealed, template, tmp_path, monkeypatch
):
    _, policies, _, cases, rows = sealed
    row = rows[0]
    case = cases[row["case"]]
    first_reply = reply(
        calls=[call("inspect_order", {"order": case["order"]}, "first")],
        finish="tool_calls",
    )
    requests = []
    fake = wire(template, iter((first_reply,)), requests)

    def send(*args):
        if args[1] == "completion" and requests:
            raise runner.TaskDeadline()
        return fake(*args)

    monkeypatch.setattr(runner, "post", send)
    result = runner.trajectory(
        tmp_path / "inflight-timeout",
        row,
        case,
        policies,
        "unused",
        float("inf"),
        "packet",
    )
    assert result["status"] == "NA"
    assert (
        result["generation_requests_started"] == 2 and result["generation_turns"] == 1
    )
    assert result["usage_complete"] is False
    assert result["observed_usage"]["total_tokens"] == 83
    arm = runner.summarize(rows, [result], policies.ARMS)["arms"][row["arm"]]
    assert arm["non_termination"] == arm["incomplete_cost_tasks"] == 1
    assert (
        arm["complete_cost_tasks"] == 0
        and arm["incomplete_token_lower_bound_total"] == 83
    )
    assert arm["mean_live_tokens_per_complete_cost_task"] is None
