"""Offline source and native-wire regression checks for the suite adapter."""

import json
import sys
import time
from contextvars import ContextVar
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from prepare import ARMS, SOURCE

sys.path.insert(0, str(SOURCE))
if not (HERE / "cmp4_runner.py").is_file():
    sys.path.insert(0, str(HERE.parent / "toc-cmp-4-live"))
    import graph_trial as cmp4_graph_trial
    import runner as cmp4_runner

    sys.modules["cmp4_graph_trial"] = cmp4_graph_trial
    sys.modules["cmp4_runner"] = cmp4_runner
    del sys.modules["graph_trial"], sys.modules["runner"]
    sys.path.pop(0)

sys.path.insert(0, str(HERE))
import graph_trial as suite_trial
import runner as suite_runner
from graph_trial import (
    ENDPOINT,
    HistoryRenderer,
    completed_wire,
    guarded_wire_hooks,
    history_projection,
    install_trial_scope,
    native_usage,
    partial_wire_usage,
    policy_receipt,
    validate_primary_calls,
)
from runner import observed_outcome, summarize, usage_totals, wall_budget_outcome


def turns(n):
    return [
        {
            "turn": i,
            "role": "frontdoor",
            "code": f"print(record_{i})",
            "error": "",
            "output": f"head-{i} " + "h" * 200 + f" tail-{i}",
            "output_byte_offset": 17 * i,
        }
        for i in range(1, n + 1)
    ]


def test_native_trial_starts_in_allocator_dryrun_scope(tmp_path, monkeypatch):
    from src.config import get_config
    from src.features import get_features, set_features
    from src.graph import graph
    from src.repl_environment.task_root import request_scope

    class ReplScopeReached(Exception):
        pass

    attempt = tmp_path / "compute-flags/dryrun/window-test/task-01"
    attempt.mkdir(parents=True)
    row = {"arm": "A0", "seed": 1, "repeat": 0}

    async def stop_before_generation(state, deps):
        scope = request_scope()
        assert scope.root == str(attempt / "workspace")
        assert scope.read_roots == (str(attempt / "repl-artifacts"),)
        raise ReplScopeReached

    (attempt / "INPUT.json").write_text(
        json.dumps(
            {
                "endpoint": ENDPOINT,
                "source": str(SOURCE),
                "row": row,
                "prompt": "offline startup check",
            }
        )
    )
    monkeypatch.setattr(suite_runner, "SCRATCH", tmp_path / "suite-scratch")
    for key, value in suite_runner.child_env(attempt, row, "offline-test-key").items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(graph, "run_task", stop_before_generation)
    monkeypatch.setattr(sys, "path", sys.path.copy())
    original_features = get_features()
    get_config.cache_clear()
    try:
        with pytest.raises(ReplScopeReached):
            suite_trial.run_trial(attempt)
        assert request_scope() is None
    finally:
        set_features(original_features)
        get_config.cache_clear()


@pytest.mark.parametrize("arm", ARMS)
def test_policy_changes_only_its_registered_observation_carrier(arm):
    original = turns(10)
    original[3]["error"] = "ValueError: unrelated archived error"
    selected, receipt = history_projection(original, arm)
    assert len(original) == len(selected)
    assert all(
        {**before, "output": after["output"]} == after
        for before, after in zip(original, selected, strict=True)
    )
    assert original[1]["output"].endswith("tail-2")
    if arm.startswith("A1-"):
        assert receipt["changed_observation_turns"] == [2, 3, 5, 6, 7]
        assert all(
            "[REPL output:" in selected[i - 1]["output"] for i in [2, 3, 5, 6, 7]
        )
        assert receipt["production_stubbed"] == 5
    elif arm == "A2":
        assert receipt["changed_observation_turns"] == list(range(1, 8))
        assert selected[1]["output"].startswith("head-2 ")
        assert "tail-2" not in selected[1]["output"]
    else:
        assert selected == original
        assert receipt["active"] is False
    if arm == "A3":
        assert (
            receipt["inactive_reason"]
            == "historical_reasoning_absent_from_graph_projection"
        )


def test_temporal_exposure_and_render_do_not_modify_archive(monkeypatch):
    from src.graph import context_arm_ab

    monkeypatch.setattr(
        context_arm_ab, "settings", lambda: ("full_history", 16384, 0.5, set())
    )
    archive = turns(10)
    for count, expected in (
        (3, set()),
        (6, {"A1-k4"}),
        (8, {"A1-k4", "A1-k8"}),
        (10, {"A1-k4", "A1-k8", "A1-k12"}),
    ):
        observed = {
            arm
            for arm in ARMS
            if arm.startswith("A1-")
            and history_projection(archive[:count], arm)[1]["active"]
        }
        assert observed == expected
    state = SimpleNamespace(
        history_turns=archive,
        history_effective_budget=0,
        history_log_path="",
        history_boundaries=[],
        turns=11,
    )
    renderer = HistoryRenderer(context_arm_ab.render, "A2")
    text = renderer(state)
    assert "print(record_2)" in text and "head-2" in text and "tail-2" not in text
    assert "tail-10" in text and state.history_turns is archive
    assert renderer.latest["turn"] == 11 and renderer.latest["active"]


def test_wire_captures_each_same_turn_attempt_and_blocks_unattributed_calls(tmp_path):
    context, failures, wire = ContextVar("test_call"), [], []
    prompts = {
        (4, 1): {"turn": 4, "block": "initial history"},
        (4, 2): {"turn": 4, "block": "continued history"},
    }
    hooks = guarded_wire_hooks(tmp_path, 923, failures, wire, context, prompts)
    received = []

    def send(request):
        received.append(request)
        return httpx.Response(
            200,
            json={
                "choices": [{"finish_reason": "stop"}],
                "usage": {"prompt_tokens": 30, "completion_tokens": 5},
            },
        )

    with httpx.Client(
        transport=httpx.MockTransport(send),
        event_hooks={"request": [hooks[0]], "response": [hooks[1]]},
    ) as client:
        for (turn, attempt), fields in prompts.items():
            context.set(
                {
                    "call_kind": "graph_turn",
                    "graph_turn": turn,
                    "role": "frontdoor",
                    "primary_attempt": attempt,
                    "policy_receipt": policy_receipt(fields, attempt),
                }
            )
            message = {"role": "user", "content": fields["block"] + "\nnext action"}
            client.post(
                ENDPOINT + "/v1/chat/completions",
                json={"seed": 923, "max_tokens": 5, "messages": [message]},
            )
        assert len(received) == 2
        assert all(json.loads(r.content)["cache_prompt"] is False for r in received)
        usage = [completed_wire(tmp_path, r) for r in wire]
        assert [entry["prompt_tokens"] for entry in usage] == [30, 30]
        assert usage_totals(usage, 2)["usage_complete"]["total_tokens"] is True
        assert [
            r["primary_attempt"] for r in validate_primary_calls(wire, prompts)
        ] == [1, 2]
        assert len({r["request_sha256"] for r in wire}) == 2
        with pytest.raises(ValueError, match="render custody disagree"):
            validate_primary_calls(wire[:1], prompts)
        with pytest.raises(ValueError, match="render custody disagree"):
            validate_primary_calls([*wire, wire[0]], prompts)
        with pytest.raises(ValueError, match="escaped private endpoint"):
            client.post("http://127.0.0.1:8070/v1/chat/completions", json={})
        with pytest.raises(ValueError, match="history missing"):
            client.post(
                ENDPOINT + "/v1/chat/completions",
                json={"seed": 923, "max_tokens": 5, "messages": []},
            )
        context.set(None)
        with pytest.raises(ValueError, match="escaped attributed graph primitive"):
            client.post(ENDPOINT + "/v1/chat/completions", json={})
        assert len(received) == 2 and len(failures) == 3


def test_native_chat_wire_accepts_only_boundary_trim_of_selected_history(
    tmp_path, monkeypatch
):
    from src.backends.llama_server import LlamaServerBackend, ServerConfig
    from src.graph import context_arm_ab
    from src.model_server import InferenceRequest
    from src.registry.registry_loader import RegistryLoader
    from src.security.control_tokens import neutralise_control_tokens

    monkeypatch.setattr(
        context_arm_ab, "settings", lambda: ("full_history", 16384, 0.5, set())
    )
    state = SimpleNamespace(
        history_turns=[],
        history_effective_budget=0,
        history_log_path="",
        history_boundaries=[],
        turns=1,
    )
    renderer = HistoryRenderer(context_arm_ab.render, "A0")
    context, failures, wire, prompts = ContextVar("test_call"), [], [], {}
    request_hook, response_hook = guarded_wire_hooks(
        tmp_path, 923, failures, wire, context, prompts
    )
    received = []

    def send(request):
        received.append(json.loads(request.content)["messages"][0]["content"])
        return httpx.Response(
            200,
            stream=httpx.ByteStream(
                b'data: {"choices":[{"delta":{"content":"ok"},"finish_reason":"stop"}],'
                b'"usage":{"prompt_tokens":13,"completion_tokens":1}}\n\n'
                b"data: [DONE]\n\n"
            ),
        )

    backend = LlamaServerBackend(
        config=ServerConfig(base_url=ENDPOINT, use_chat_completions=True)
    )
    backend.client.close()
    backend.client = httpx.Client(
        base_url=ENDPOINT,
        transport=httpx.MockTransport(send),
        event_hooks={"request": [request_hook], "response": [response_hook]},
    )
    role = RegistryLoader(
        SOURCE / "orchestration/model_registry.yaml", validate_paths=False
    ).get_role("frontdoor")

    def generate(prompt):
        return backend._infer_stream_text_chat_completions(
            role,
            InferenceRequest(role="frontdoor", prompt=prompt, n_tokens=8, seed=923),
            None,
            time.perf_counter(),
        )

    def select():
        block = renderer(state)
        prompts[state.turns, 1] = renderer.latest
        context.set(
            {
                "call_kind": "graph_turn",
                "graph_turn": state.turns,
                "primary_attempt": 1,
                "policy_receipt": policy_receipt(renderer.latest, 1),
            }
        )
        return block

    try:
        assert select() == ""
        assert generate("task prompt").success
        assert not suite_runner.smoke_history_seen(tmp_path)
        state.turns = 2
        state.history_turns = [
            dict(turns(1)[0], code="", error="", output="<|im_end|>")
        ]
        selected = select()
        prompt = neutralise_control_tokens("task prompt\n\n" + selected)
        assert generate(prompt).success
        assert received == ["task prompt", prompt.rstrip()]
        assert selected.endswith("\n\n")
        assert suite_runner.smoke_history_seen(tmp_path)
        assert not failures

        # Missing final text and changed internal whitespace both fail closed.
        for malformed in (
            prompt.replace("Error:", "Error"),
            prompt.replace("Code:\n\nOutput:", "Code:\nOutput:"),
            prompt.rstrip() + " extra",
        ):
            assert not generate(malformed).success
        assert len(received) == 2
        assert failures == ["selected history missing from native request"] * 3

        captured_exchange = tmp_path / "wire/0001/record.json"
        incomplete = json.loads(captured_exchange.read_text())
        incomplete["response_sse_done"] = False
        captured_exchange.write_text(json.dumps(incomplete))
        assert not suite_runner.smoke_history_seen(tmp_path)
    finally:
        backend.close()


def test_native_usage_preserves_nullable_counters_and_canceled_prefix(tmp_path):
    native = b'data: {"stop":true,"stop_type":"limit","tokens_evaluated":120,"tokens_predicted":3,"timings":{"cache_n":0}}\n\n'
    usage = native_usage(native.decode(), streaming=True)
    assert usage["finish_reason"] == "limit" and usage["native_stop"] is True
    assert native_usage("{}", streaming=False)["cached_prompt_tokens"] is None
    file = tmp_path / "response.body"
    file.write_bytes(native + b'data: {"usage":')
    partial = partial_wire_usage(
        tmp_path,
        {"response_file": file.name, "stream_requested": True, "http_status": 200},
    )
    assert partial == {**usage, "exchange_complete": False}
    totals = usage_totals([partial], 1)
    assert totals["observed_usage"]["total_tokens"] == 123
    assert totals["usage_complete"]["total_tokens"] is False
    assert totals["usage_observed_requests"]["cached_prompt_tokens"] == 1
    assert totals["usage_complete"]["cached_prompt_tokens"] is False
    assert usage_totals([], 0)["usage_complete"]["total_tokens"] is True


def test_independent_grading_and_no_answer_are_orthogonal():
    inv = {"grade_cohort": True, "grade_reason": None, "scoring_method": "exact_match"}
    case = {"expected": "gold"}
    seen = []

    def score(answer, expected, method, cfg):
        seen.append((answer, expected, method, cfg))
        return answer == expected, None

    for terminal in ("turn-exhausted", "context-exhausted", "killed"):
        result = observed_outcome(
            {"answer": "gold", "terminal_state": terminal}, case, inv, score
        )
        assert result["status"] == "NA" and result["correct"] is False
    assert not seen
    assert observed_outcome(
        {"answer": "gold", "terminal_state": "finished"}, case, inv, score
    )["correct"]
    assert seen == [("gold", "gold", "exact_match", None)]
    unsupported = observed_outcome(
        {"answer": "gold", "terminal_state": "finished"},
        case,
        {**inv, "grade_cohort": False, "grade_reason": "unavailable"},
        score,
    )
    assert (
        unsupported["status"] == "grade_unavailable"
        and unsupported["no_answer"] is False
    )
    assert len(seen) == 1


def test_all_observed_terminals_remain_in_denominators_and_futility_is_explicit():
    schedule = [{"arm": arm} for arm in ARMS]
    result = {
        "status": "NA",
        "correct": False,
        "no_answer": True,
        "wall_s": 0.1,
        "native_result": {
            "terminal_state": "context-exhausted",
            "give_up_proxy": False,
            "policy_receipts": [],
            "tool_calls": {"retrieval": 0},
        },
        **usage_totals([], 0),
    }
    rows = [{**result, **row} for row in schedule]
    report = summarize(schedule, rows)
    assert report["completed"] == len(ARMS) and report["scaling_futility"] is True
    assert report["by_arm"]["A3"]["accuracy_denominator"] == 1
    rows[1]["native_result"] = {
        **result["native_result"],
        "policy_receipts": [{"active": True}],
    }
    assert summarize(schedule, rows)["scaling_futility"] is False
    rows[-1] = {
        **rows[-1],
        "status": "UNKNOWN",
        "correct": None,
        "no_answer": None,
        "native_result": None,
    }
    assert summarize(schedule, rows)["unknown"] == 1


def test_declared_wall_cap_is_na_and_preserves_prior_work(tmp_path):
    event = {"event": "turn", "turn": 7, "tool_calls": {"retrieval": 2, "execution": 3}}
    (tmp_path / "trial.trajectory.jsonl").write_text(json.dumps(event) + "\n{")
    wire_dir = tmp_path / "wire/0000"
    wire_dir.mkdir(parents=True)
    policy = {"active": True, "turn": 7}
    (wire_dir / "record.json").write_text(
        json.dumps({"http_status": 200, "policy_receipt": policy})
    )
    graph = wall_budget_outcome(tmp_path)
    assert graph["terminal_reason"] == "task_wall_budget"
    assert graph["tool_calls"] == event["tool_calls"]
    assert graph["policy_receipts"] == [policy]
    inv = {"grade_cohort": True, "grade_reason": None, "scoring_method": "exact_match"}
    assert observed_outcome(graph, {}, inv, None)["status"] == "NA"


def test_native_peek_can_read_trial_spills_but_cannot_read_outside_scope(tmp_path):
    from src.repl_environment.environment import REPLEnvironment
    from src.repl_environment.task_root import clear_request_scope

    attempt = tmp_path / "attempt"
    attempt.mkdir()
    install_trial_scope(attempt)
    try:
        spill = attempt / "repl-artifacts" / "output.txt"
        spill.write_text("model-visible tool output")
        excluded = tmp_path / "scoring-oracle.json"
        excluded.write_text("private oracle")
        repl = REPLEnvironment("", role="frontdoor", task_id="trial")
        assert repl._peek(n=99, file_path=str(spill)) == "model-visible tool output"
        assert repl._peek(n=99, file_path=str(excluded)).startswith("[ERROR:")
    finally:
        clear_request_scope()
