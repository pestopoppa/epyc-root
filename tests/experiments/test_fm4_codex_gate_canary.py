"""Generated rollout controls for native Codex selected-gate acceptance."""

import hashlib
import json
import sys

import pytest

from scripts.experiments.fm4 import codex_dispatch as dispatch, native_canary, run_gate


adapter = native_canary.adapter
PARENT = "synthetic-parent"
CHILD = "synthetic-child"
CALL = "synthetic-dispatch"
AGENT_PATH = "/root/synthetic-child"
TASK = "FM4-CODEX-GATE-CONTROL"


def _rollouts(tmp_path, *, child_changes=lambda _: None):
    parent_rows = [
        {"type": "session_meta", "payload": {"id": PARENT}},
        {"type": "response_item", "payload": {"type": "function_call", "namespace": "collaboration",
                                             "name": "spawn_agent", "call_id": CALL}},
        {"type": "response_item", "payload": {"type": "function_call_output", "call_id": CALL,
                                             "output": json.dumps({"task_name": AGENT_PATH})}},
    ]
    child_rows = [
        {"type": "session_meta", "payload": {"id": CHILD, "source": {"subagent": {"thread_spawn": {
            "parent_thread_id": PARENT, "agent_path": AGENT_PATH,
        }}}}},
        {"type": "event_msg", "payload": {"type": "task_started", "turn_id": "first"}},
        {"type": "event_msg", "payload": {"type": "task_complete", "turn_id": "first",
                                         "last_agent_message": "private content"}},
    ]
    child_changes(child_rows)
    parent, child = tmp_path / "parent.jsonl", tmp_path / "child.jsonl"
    for path, rows in ((parent, parent_rows), (child, child_rows)):
        path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    return parent, child


def _gate_bundle(tmp_path, code=0, **overrides):
    acceptance = tmp_path / "acceptance.json"
    identity = dict(parent_session_id=PARENT, child_agent_id=CHILD, dispatch_tool_use_id=CALL, task_id=TASK)
    identity.update(overrides)
    arguments = ["--out", str(acceptance), "--cwd", str(tmp_path), "--timeout-s", "5"]
    for key, value in identity.items():
        arguments.extend([f"--{key.replace('_', '-')}", value])
    assert run_gate.main([*arguments, "--", sys.executable, "-c", f"raise SystemExit({code})"]) == 0
    return acceptance


@pytest.mark.parametrize(("code", "result", "value"), [(0, "pass", 1), (7, "fail", 0)])
def test_codex_gate_selects_exact_claim_without_a_task_outcome(tmp_path, capsys, code, result, value):
    parent, child = _rollouts(tmp_path)
    acceptance = _gate_bundle(tmp_path, code)
    capsys.readouterr()
    state = tmp_path / "state"
    assert native_canary.main(["--codex-gate", "--parent", str(parent), "--child", str(child),
                             "--task-id", TASK, "--acceptance", str(acceptance), "--state-dir", str(state)]) == 0
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["schema"] == "fm4.codex_gate.native_canary.v1"
    assert receipt["consumer"] == adapter.PLANNER_CONSUMER
    assert receipt["excluded_consumer"] == "autokernel.planner"
    assert receipt["dispatch"] == dispatch.collect(parent, child)
    assert receipt["identity"] == dict(receipt["dispatch"]["identity"], task_id=TASK)
    assert receipt["task_id"] == TASK
    assert receipt["gate_result"] == result
    assert receipt["task_outcome"] is None
    for role, path in (("parent", parent), ("child", child), ("acceptance", acceptance)):
        assert receipt["inputs"][role]["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    claim = receipt["claim"]
    assert (claim["grade"], claim["tier"], claim["value"], claim["not_evidence"]) == (
        "Judged/Located", "harness", value, True)
    assert receipt["ledger_state_digest"]
    with pytest.raises(ValueError, match="state directory must be new"):
        native_canary.run_codex_gate(child, parent, TASK, acceptance, state)


@pytest.mark.parametrize("key", ["task_id", "parent_session_id", "child_agent_id", "dispatch_tool_use_id"])
def test_codex_gate_refuses_matching_execution_for_a_different_identity(tmp_path, key):
    parent, child = _rollouts(tmp_path)
    acceptance = _gate_bundle(tmp_path, **{key: "another-id"})
    state = tmp_path / "state"
    with pytest.raises(ValueError, match=f"selected gate identity mismatch: {key}"):
        native_canary.run_codex_gate(child, parent, TASK, acceptance, state)
    assert not state.exists()


@pytest.mark.parametrize(("change", "refusal"), [
    (lambda rows: rows.pop(), "launch_only"),
    (lambda rows: rows.append(rows[-1]), "ambiguous_child_turn"),
    (lambda rows: rows[-1]["payload"].update(type="turn_aborted"), "ended_with_error"),
])
def test_codex_gate_refuses_incomplete_or_ambiguous_lifecycle(tmp_path, change, refusal):
    parent, child = _rollouts(tmp_path, child_changes=change)
    acceptance = _gate_bundle(tmp_path)
    state = tmp_path / "state"
    with pytest.raises(ValueError, match=refusal):
        native_canary.run_codex_gate(child, parent, TASK, acceptance, state)
    assert not state.exists()


def test_codex_gate_refuses_tampered_execution(tmp_path):
    parent, child = _rollouts(tmp_path)
    acceptance = _gate_bundle(tmp_path)
    sidecar = acceptance.with_name(acceptance.name + ".execution.json")
    sidecar.write_bytes(sidecar.read_bytes() + b"\n")
    state = tmp_path / "state"
    with pytest.raises(ValueError, match="adjacent execution JSON disagrees"):
        native_canary.run_codex_gate(child, parent, TASK, acceptance, state)
    assert not state.exists()


def test_codex_gate_refuses_rollout_drift_during_planning(tmp_path, monkeypatch):
    parent, child = _rollouts(tmp_path)
    acceptance = _gate_bundle(tmp_path)
    prepare = native_canary.loop_beliefs.prepare

    def change_rollout(*args, **kwargs):
        answer = prepare(*args, **kwargs)
        child.write_bytes(child.read_bytes().replace(b"private content", b"different content"))
        return answer

    monkeypatch.setattr(native_canary.loop_beliefs, "prepare", change_rollout)
    with pytest.raises(ValueError, match="a Codex rollout changed"):
        native_canary.run_codex_gate(child, parent, TASK, acceptance, tmp_path / "state")
