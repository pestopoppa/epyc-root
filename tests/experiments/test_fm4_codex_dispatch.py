"""Codex rollout identity and lifecycle controls for the FM-4 collector."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import pytest

from scripts.experiments.fm4 import codex_dispatch as dispatch, native_canary


adapter = native_canary.adapter


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


def _write_json(path, record):
    path.write_text(json.dumps(record))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _replay_fixture(tmp_path, *, parent_changes=lambda _: None, child_changes=lambda _: None,
                    receipt_change=lambda _: None, pin_change=lambda _: None):
    private = tmp_path / "private"
    private.mkdir()
    parent, child = _rollouts(private, parent_changes=parent_changes, child_changes=child_changes)
    receipt = dispatch.collect(parent, child)
    receipt["pair_id"] = "example"
    inputs = {}
    for role, path in zip(("parent", "child"), (parent, child)):
        destination = path.with_name(f"example.{path.name}")
        path.rename(destination)
        destination.chmod(0o400)
        sha = receipt["inputs"][role]["sha256"]
        del receipt["inputs"][role]["path"]
        inputs[role] = {"file": f"private/{destination.name}", "bytes": destination.stat().st_size,
                        "sha256": sha}
    pin = {"pair_id": "example", "inputs": inputs, "identity": receipt["identity"],
           "binding_kind": receipt["binding_kind"], "child_agent_path": AGENT_PATH}
    pin_change(pin)
    receipt_change(receipt)
    collector_sha = hashlib.sha256(Path(dispatch.__file__).read_bytes()).hexdigest()
    pin_sha = _write_json(tmp_path / "input-pins.json", {"schema": adapter.DISPATCH_PINS_SCHEMA,
                         "collector_sha256": collector_sha, "pairs": [pin]})
    official = tmp_path / "official"
    official.mkdir()
    result = official / "RESULT.json"
    result_sha = _write_json(result, {"schema": adapter.DISPATCH_CENSUS_SCHEMA, "id": "fixture",
                             "mode": "official", "cpus": [0, 1, 2, 3], "input_pins_sha256": pin_sha,
                             "collector_sha256": collector_sha, "receipts": [receipt],
                             "terminal_receipt_count": 1, "refusal_count": 0,
                             "pair_ids": ["example"], "task_outcome": None})
    replay = tmp_path / "replay.json"
    _write_json(replay, {"schema": adapter.DISPATCH_BUNDLE_SCHEMA, "result": str(result),
                         "result_sha256": result_sha, "snapshot_dir": str(private), "pair_ids": ["example"]})
    replay.chmod(0o400)
    return replay, result, private


@pytest.mark.parametrize("terminal", ["task_complete", "turn_aborted"])
@pytest.mark.parametrize("coordinator_review", [False, True])
def test_dispatch_canary_uses_real_planner_and_terminal_only_authority(
        tmp_path, capsys, terminal, coordinator_review):
    def child_changes(rows):
        rows[-1]["payload"]["type"] = terminal

    replay, result, private = _replay_fixture(tmp_path, child_changes=child_changes)
    state = tmp_path / "state"
    args = ["--dispatch-replay", str(replay), "--state-dir", str(state)]
    if coordinator_review:
        args.append("--coordinator-review")
    assert native_canary.main(args) == 0
    output = capsys.readouterr().out
    canary = json.loads(output)
    (item,) = canary["selected"]
    assert item["receipt"]["child_turn"]["terminal_event"] == terminal
    assert item["receipt"]["child_turn"]["state"] == (
        "completed" if terminal == "task_complete" else "ended_with_error")
    assert item["receipt"]["task_outcome"] is canary["task_outcome"] is None
    assert item["claim"]["locator"].startswith(f"{result}#sha256=")
    assert item["claim"]["not_evidence"] and item["claim"]["grade"] == "Judged/Located"
    assert canary["excluded_consumer"] == "autokernel.planner"
    ledger = (state / "ledger.jsonl").read_text()
    assert str(private) not in (output + ledger) and "private content" not in (output + ledger)
    assert adapter.DISPATCH_AUTHORITY in ledger and adapter.AUTHORITY not in ledger
    assert "fm4_selected_gate_pass" not in ledger and "fm4_codex_terminal_dispatch" in ledger
    assert len((state / "reads.jsonl").read_text().splitlines()) == 2
    if coordinator_review:
        entry = native_canary.ROOT / native_canary.COORDINATOR_ENTRY
        assert canary["entrypoint"] == "scripts/vidya/coordinator_fm4_context.py"
        assert canary["entrypoint_sha256"] == hashlib.sha256(entry.read_bytes()).hexdigest()
        assert canary["reliance_count"] == canary["task_gate_claim_count"] == 0
        config = state / "alarm-config.json"
        assert json.loads(config.read_bytes())["backend"] == "file"


def test_coordinator_review_uses_the_fixed_consumer():
    entry = native_canary.ROOT / native_canary.COORDINATOR_ENTRY
    refused = subprocess.run([sys.executable, "-B", str(entry), "--consumer", "autokernel.planner"],
                             capture_output=True, text=True)
    assert refused.returncode == 2
    assert "unrecognized arguments: --consumer autokernel.planner" in refused.stderr


def test_coordinator_entry_refuses_invalid_index_and_defaults_to_checkout_check(tmp_path):
    entry = native_canary.ROOT / native_canary.COORDINATOR_ENTRY
    index = tmp_path / "index.yaml"
    index.write_text("[\n")
    config = tmp_path / "alarm-config.json"
    config.write_text(json.dumps({"backend": "file", "file": {"path": str(tmp_path / "alarms.jsonl")}}))
    run = subprocess.run([
        sys.executable, "-B", str(entry), "--ledger", str(tmp_path / "ledger.jsonl"),
        "--index", str(index), "--known-good", str(tmp_path / "known-good.json"),
        "--read-log", str(tmp_path / "reads.jsonl"), "--alarm-state", str(tmp_path / "alarm-state.json"),
        "--alarm-config", str(config),
    ], capture_output=True, text=True)
    answer = json.loads(run.stdout)
    assert run.returncode == native_canary.loop_beliefs.EXIT_REFUSED
    assert answer["consumer"] == adapter.PLANNER_CONSUMER and answer["reader_checkout_check"] is True
    assert answer["status"] == "refused" and answer["evidence"] is None


def test_coordinator_canary_preserves_reader_timeout_as_refusal(tmp_path, capsys, monkeypatch):
    def timeout(argv, **kwargs):
        assert argv[3].endswith("/scripts/vidya/coordinator_fm4_context.py")
        assert kwargs["timeout"] == 60
        assert kwargs["env"]["ALARM_BACKEND"] == "file"
        assert kwargs["env"]["ALARM_FILE_PATH"] == str(tmp_path / "state" / "alarms.jsonl")
        raise subprocess.TimeoutExpired(argv, kwargs["timeout"], output=b"private content")

    replay, _, _ = _replay_fixture(tmp_path)
    monkeypatch.setattr(native_canary.subprocess, "run", timeout)
    assert native_canary.main(["--dispatch-replay", str(replay), "--state-dir", str(tmp_path / "state"),
                               "--coordinator-review"]) == 1
    output = capsys.readouterr()
    assert not output.out and output.err == "FM-4 canary refused: FM-4 coordinator reader timed out\n"


@pytest.mark.parametrize(("fixture_change", "refusal"), [
    ({"pin_change": lambda row: row.update(identity={"child_agent_id": "unrelated"})},
     "identity disagrees"),
    ({"receipt_change": lambda row: row.update(task_outcome="success")}, "disagrees with native replay"),
    ({"receipt_change": lambda row: row["child_turn"].update(final_message_present=1)},
     "disagrees with native replay"),
    ({"parent_changes": lambda rows: rows.append(rows[-1])}, "ambiguous_spawn_result"),
    ({"child_changes": lambda rows: rows.append(rows[-1])}, "ambiguous_child_turn"),
    ({"child_changes": lambda rows: rows.pop()}, "launch_only"),
])
def test_dispatch_replay_refuses_resealed_identity_outcome_and_ambiguity(tmp_path, fixture_change, refusal):
    replay, _, _ = _replay_fixture(tmp_path, **fixture_change)
    state = tmp_path / "state"
    with pytest.raises(ValueError, match=refusal):
        native_canary.run_codex_dispatch(replay, state)
    assert not state.exists()


@pytest.mark.parametrize(("artifact", "refusal"), [
    ("result", "RESULT.json digest mismatch"), ("pins", "input-pins.json digest mismatch"),
    ("snapshot", "snapshot digest or path drift"), ("symlink", "snapshot type, mode or size drift"),
    ("writable", "snapshot type, mode or size drift"),
])
def test_dispatch_rechecks_custody_before_projection(tmp_path, artifact, refusal):
    replay, result, private = _replay_fixture(tmp_path)
    (native,) = adapter.native_rows(replay)
    if artifact == "result":
        result.write_bytes(result.read_bytes() + b"\n")
    elif artifact == "pins":
        pins = tmp_path / "input-pins.json"
        pins.write_bytes(pins.read_bytes() + b"\n")
    else:
        child = private / "example.child.jsonl"
        child.chmod(0o600)
        if artifact == "snapshot":
            child.write_bytes(child.read_bytes().replace(b"private content", b"changed content"))
            child.chmod(0o400)
        elif artifact == "symlink":
            relocated = child.with_suffix(".relocated")
            child.rename(relocated)
            relocated.chmod(0o400)
            child.symlink_to(relocated)
    with pytest.raises(ValueError, match=refusal):
        adapter.project(native)
