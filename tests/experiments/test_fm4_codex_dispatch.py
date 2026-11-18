"""Codex rollout identity and lifecycle controls for the FM-4 collector."""

import hashlib
import json
import pytest

from scripts.experiments.fm4 import codex_dispatch as dispatch


PARENT = "01a1eeed-335d-7812-b888-306f9fa8a828"
CHILD = "01a1eeef-c28a-76d1-a869-f37f3b624754"
CALL = "call_1df762adc54847a587e455ad5d94656c"
AGENT_PATH = "/root/example"


def _event(kind, event, **fields):
    return {"type": kind, "payload": {"type": event, **fields}}


def _spawn(call_id=CALL):
    return _event("response_item", "function_call", namespace="collaboration", name="spawn_agent",
                  arguments='{"task_name":"example"}', call_id=call_id)


def _result(call_id=CALL, **output):
    return _event("response_item", "function_call_output", call_id=call_id, output=json.dumps(output))


def _rollouts(tmp_path, *, parent_changes=lambda _: None, child_changes=lambda _: None):
    parent_rows = [{"type": "session_meta", "payload": {"id": PARENT, "source": "cli"}},
                   _spawn(), _result(task_name=AGENT_PATH)]
    child_rows = [
        {"type": "session_meta", "payload": {"id": CHILD, "source": {"subagent": {"thread_spawn": {
            "parent_thread_id": PARENT, "agent_path": AGENT_PATH,
        }}}}},
        _event("event_msg", "task_started", turn_id="first"),
        _event("event_msg", "task_complete", turn_id="first", last_agent_message="private content"),
    ]
    parent_changes(parent_rows)
    child_changes(child_rows)
    paths = [tmp_path / "parent.jsonl", tmp_path / "child.jsonl"]
    for path, rows in zip(paths, (parent_rows, child_rows)):
        path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    return paths


@pytest.mark.parametrize("direct", [False, True])
def test_terminal_binding_keeps_lifecycle_and_task_outcome_separate(tmp_path, capsys, direct):
    def change(rows):
        if direct:
            rows[-1] = _result(agent_id=CHILD)

    parent, child = _rollouts(tmp_path, parent_changes=change)
    assert dispatch.main(["--parent", str(parent), "--child", str(child)]) == 0
    raw = capsys.readouterr().out
    receipt = json.loads(raw)
    assert receipt["disposition"] == "terminal_child"
    assert receipt["binding_kind"] == ("direct_agent_id" if direct else "native_agent_path")
    assert receipt["identity"] == {"parent_session_id": PARENT, "child_agent_id": CHILD,
                                   "dispatch_tool_use_id": CALL}
    assert receipt["task_outcome"] is None
    assert receipt["child_turn"] == {"state": "completed", "turn_id": "first", "start_line": 2,
                                     "terminal_line": 3, "terminal_event": "task_complete",
                                     "final_message_present": True}
    assert "private content" not in raw
    for role, path in (("parent", parent), ("child", child)):
        assert receipt["inputs"][role] == {"path": str(path),
                                           "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


@pytest.mark.parametrize(("change", "disposition"), [
    (lambda rows: rows.pop(), "missing_spawn_result"),
    (lambda rows: rows.insert(1, rows[-1]), "ambiguous_spawn_result"),
    (lambda rows: rows.append(_spawn()), "ambiguous_spawn_result"),
    (lambda rows: rows[1]["payload"].update(namespace="other"), "missing_spawn_result"),
    (lambda rows: rows.__setitem__(2, _result(task_name=AGENT_PATH, error="failed")),
     "spawn_result_error"),
    (lambda rows: rows[2]["payload"].update(is_error=True), "spawn_result_error"),
    (lambda rows: rows.__setitem__(2, _result(task_name=AGENT_PATH, isError=True)),
     "spawn_result_error"),
    (lambda rows: rows.extend([_spawn("another"), _result("another", task_name=AGENT_PATH)]),
     "ambiguous_spawn_result"),
    (lambda rows: rows.append(_result(agent_id="another-id")), "ambiguous_spawn_result"),
    (lambda rows: rows.__setitem__(2, _result(agent_id="another-id", task_name=AGENT_PATH)),
     "spawn_child_identity_mismatch"),
    (lambda rows: rows.__setitem__(2, _result(agent_id=CHILD, task_name="/root/another")),
     "spawn_child_identity_mismatch"),
    (lambda rows: rows.__setitem__(2, _result("another", task_name=AGENT_PATH)), "missing_spawn_result"),
])
def test_spawn_must_establish_unique_matching_identity(tmp_path, change, disposition):
    receipt = dispatch.collect(*_rollouts(tmp_path, parent_changes=change))
    assert receipt["disposition"] == disposition
    assert receipt["identity"] is None
    assert receipt["task_outcome"] is None


@pytest.mark.parametrize(("change", "disposition"), [
    (lambda rows: rows[0]["payload"].update(source={}), "missing_session_identity"),
    (lambda rows: rows[0]["payload"]["source"]["subagent"]["thread_spawn"].update(
        parent_thread_id="wrong-parent"), "parent_child_identity_mismatch"),
    (lambda rows: rows.append(rows[0]), "invalid_session_metadata"),
    (lambda rows: rows[0]["payload"]["source"]["subagent"]["thread_spawn"].update(
        agent_path="/root/../example"), "invalid_child_agent_path"),
    (lambda rows: rows.append(rows[-1]), "ambiguous_child_turn"),
])
def test_conflicting_or_missing_child_metadata_refuses(tmp_path, change, disposition):
    receipt = dispatch.collect(*_rollouts(tmp_path, child_changes=change))
    assert receipt["disposition"] == disposition
    assert receipt["identity"] is None


def test_launch_and_later_turn_cannot_satisfy_terminal_check(tmp_path, capsys):
    def change(rows):
        rows.pop()
        rows.extend([_event("event_msg", "task_started", turn_id="later"),
                     _event("event_msg", "task_complete", turn_id="later")])

    parent, child = _rollouts(tmp_path, child_changes=change)
    assert dispatch.main(["--parent", str(parent), "--child", str(child)]) == 1
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["disposition"] == "launch_only"
    assert receipt["identity"]["dispatch_tool_use_id"] == CALL
    assert receipt["task_outcome"] is None


@pytest.mark.parametrize("terminal", ["task_complete", "turn_aborted"])
def test_transport_error_is_terminal_without_a_task_outcome(tmp_path, terminal):
    def change(rows):
        rows[2] = _event("event_msg", terminal, turn_id="first", error={"message": "transport failure"})

    receipt = dispatch.collect(*_rollouts(tmp_path, child_changes=change))
    assert receipt["disposition"] == "terminal_child"
    assert receipt["child_turn"]["state"] == "ended_with_error"
    assert receipt["task_outcome"] is None


def test_incomplete_line_refuses(tmp_path):
    parent, child = _rollouts(tmp_path)
    child.write_bytes(child.read_bytes().rstrip(b"\n"))
    with pytest.raises(ValueError, match="invalid_rollout:.*incomplete JSONL line"):
        dispatch.collect(parent, child)


def test_rollout_change_after_parse_refuses(tmp_path, monkeypatch):
    parent, child = _rollouts(tmp_path)
    read = dispatch._read

    def change(path, digest, *, parent):
        result = read(path, digest, parent=parent)
        if not parent:
            path.write_bytes(path.read_bytes() + b"\n")
        return result

    monkeypatch.setattr(dispatch, "_read", change)
    with pytest.raises(ValueError, match="changed_input"):
        dispatch.collect(parent, child)
