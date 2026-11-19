"""Synthetic controls for the native entry point with the proposed D9 API shape."""

import hashlib
import inspect
import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.experiments.fm4 import native_canary as canary


TASK = "FM4-SYNTHETIC-NATIVE-CANARY"
SESSION = "synthetic-parent"
CHILD = "synthetic-child"
DISPATCH = "synthetic-dispatch"
GATE = Path(canary.__file__).with_name("run_gate.py")


def _case(root, code):
    child = root / f"agent-{CHILD}.jsonl"
    parent = root / f"{SESSION}.jsonl"
    child.write_text(json.dumps({"type": "assistant", "sessionId": SESSION,
                                 "agentId": CHILD, "isSidechain": True, "message": {"content": [
                                     {"type": "tool_use", "name": "SubagentHandback", "id": "h",
                                      "input": {"message": "synthetic delivery"}}]}}) + "\n")
    parent.write_text("\n".join(json.dumps(line) for line in (
        {"type": "assistant", "sessionId": SESSION, "message": {"content": [
            {"type": "tool_use", "name": "Agent", "id": DISPATCH, "input": {}}]}},
        {"type": "user", "sessionId": SESSION, "toolUseResult": {"agentId": CHILD, "status": "completed"},
         "message": {"content": [{"type": "tool_result", "tool_use_id": DISPATCH,
                                  "is_error": False, "content": []}]}},
    )) + "\n")
    receipt = root / "acceptance.json"
    subprocess.run([sys.executable, "-B", str(GATE), "--out", str(receipt), "--cwd", str(root),
                    "--timeout-s", "5", "--parent-session-id", SESSION, "--child-agent-id", CHILD,
                    "--dispatch-tool-use-id", DISPATCH, "--task-id", TASK, "--",
                    sys.executable, "-c", f"raise SystemExit({code})"], check=True, capture_output=True)
    return child, parent, receipt, root / "state"


def _double(monkeypatch, case, mutation=None):
    child, parent, receipt, _ = case

    def assess(path, *, parent_path, task_id, acceptance_paths):
        assert (path, parent_path, acceptance_paths) == (child, parent, [receipt])
        record = json.loads(receipt.read_bytes())
        signal = {
            "caller_task_id": task_id, "disposition": "applied",
            "identity": {"parent_session_id": SESSION, "dispatch_tool_use_id": DISPATCH,
                         "child_agent_id": CHILD, "task_id": TASK},
            "sources": [{"path": str(receipt), "sha256": hashlib.sha256(receipt.read_bytes()).hexdigest(),
                         "record": record, "disposition": "verified"}],
        }
        row = {"harness": "claude", "path": str(child), "session_id": SESSION,
               "verdict": "success" if record["gate_result"] == "pass" else "failure",
               "signals": {"parent_join": "matched", "task_acceptance": signal,
                           "parent_result": {"path": str(parent), "session_id": SESSION,
                                             "tool_use_id": DISPATCH, "agent_id": CHILD}}}
        if mutation:
            mutation(row, signal)
        return row

    monkeypatch.setattr(canary.session_oracle, "assess", assess)


def _run(case, task=TASK):
    child, parent, receipt, state = case
    return canary.run(child, parent, task, receipt, state)


@pytest.mark.parametrize(("code", "verdict", "value"), [(0, "success", 1), (7, "failure", 0)])
def test_synthetic_dispatch_through_real_d9_oracle_and_planner(tmp_path, code, verdict, value):
    if not {"acceptance_paths", "task_id"} <= inspect.signature(canary.session_oracle.assess).parameters.keys():
        pytest.skip("D9 oracle acceptance API is pending")

    case = _case(tmp_path, code)
    with pytest.raises(ValueError, match="identity_mismatch"):
        _run(case, task="FM4-DIFFERENT-TASK")
    assert not case[-1].exists()

    result = _run(case)
    assert result["identity"]["task_id"] == TASK
    assert result["oracle_disposition"] == "applied"
    assert result["oracle_verdict"] == verdict
    assert result["selected_claim"]["value"] == value


@pytest.mark.parametrize(("code", "verdict", "value"), [(0, "success", 1), (7, "failure", 0)])
def test_exact_gate_claim_selected_with_real_isolated_vidya(tmp_path, monkeypatch, capsys, code, verdict, value):
    case = _case(tmp_path, code)
    _double(monkeypatch, case)
    child, parent, record, state = case
    assert canary.main(["--child", str(child), "--parent", str(parent), "--task-id", TASK,
                        "--acceptance", str(record), "--state-dir", str(state)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["oracle_verdict"] == verdict
    assert result["identity"]["task_id"] == TASK
    for label, path in zip(("child", "parent", "acceptance"), case):
        assert result["inputs"][label]["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    claim = result["selected_claim"]
    assert (claim["grade"], claim["tier"], claim["value"], claim["not_evidence"]) == (
        "Judged/Located", "harness", value, True)
    assert (case[-1] / "ledger.jsonl.sync.json").is_file()
    assert (case[-1] / "reads.jsonl").is_file()
    with pytest.raises(ValueError, match="state directory must be new"):
        _run(case)


@pytest.mark.parametrize(("mutation", "message"), [
    (lambda row, signal: signal.update(disposition="corroborates_parent"), "corroborates_parent"),
    (lambda row, signal: signal.update(disposition="nonterminal_parent"), "nonterminal_parent"),
    (lambda row, signal: row["signals"].update(parent_join="ambiguous"), "matched dispatch"),
    (lambda row, signal: signal["identity"].update(child_agent_id="another-agent"), "matched dispatch"),
    (lambda row, signal: signal["sources"][0].update(sha256="0" * 64), "record and digest"),
    (lambda row, signal: row.update(verdict="failure"), "disagrees with the verified gate result"),
])
def test_disagreed_oracle_assessment_refuses_before_ingest(tmp_path, monkeypatch, mutation, message):
    case = _case(tmp_path, 0)
    _double(monkeypatch, case, mutation)
    with pytest.raises(ValueError, match=message):
        _run(case)
    assert not case[-1].exists()


def test_independent_task_mismatch_and_transcript_mutation_refuse(tmp_path, monkeypatch):
    case = _case(tmp_path, 0)
    _double(monkeypatch, case)
    with pytest.raises(ValueError, match="independent task ID"):
        _run(case, task="FM4-DIFFERENT-TASK")
    child = case[0]
    _double(monkeypatch, case, lambda row, signal: child.write_text(child.read_text() + "\n"))
    with pytest.raises(ValueError, match="transcript changed during oracle assessment"):
        _run(case)
    assert not case[-1].exists()


def test_planner_must_select_the_claim_and_bundle_must_stay_stable(tmp_path, monkeypatch):
    prepare = canary.loop_beliefs.prepare
    first = tmp_path / "unselected"
    first.mkdir()
    case = _case(first, 0)
    _double(monkeypatch, case)

    def unselected(*args, **kwargs):
        answer = prepare(*args, **kwargs)
        answer["evidence"]["claims"] = []
        return answer

    monkeypatch.setattr(canary.loop_beliefs, "prepare", unselected)
    with pytest.raises(ValueError, match="did not select the exact gate observation"):
        _run(case)

    second = tmp_path / "mutated"
    second.mkdir()
    case = _case(second, 0)
    _double(monkeypatch, case)
    record = case[2]

    def mutate_record(*args, **kwargs):
        answer = prepare(*args, **kwargs)
        record.chmod(0o644)
        record.write_bytes(record.read_bytes() + b"\n")
        record.chmod(0o444)
        return answer

    monkeypatch.setattr(canary.loop_beliefs, "prepare", mutate_record)
    with pytest.raises(ValueError, match="acceptance bundle changed during Vidya ingest or retrieval"):
        _run(case)


def test_missing_oracle_api_is_a_clear_refusal(tmp_path, monkeypatch, capsys):
    def baseline(path, *, parent_path=None):
        pytest.fail("unpatched oracle must not run")

    monkeypatch.setattr(canary.session_oracle, "assess", baseline)
    state = tmp_path / "state"
    status = canary.main(["--child", "missing", "--parent", "missing", "--task-id", TASK,
                          "--acceptance", "missing", "--state-dir", str(state)])
    assert status == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert "the D9 oracle acceptance API is required" in output.err
    assert not state.exists()
