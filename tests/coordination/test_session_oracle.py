import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "coordination"))
import session_oracle as so  # noqa: E402


def _build(tmp_path, calls, name="s.jsonl", extra_lines=()):
    """calls: list of (command, output, is_error)."""
    lines = []
    for i, (cmd, out, err) in enumerate(calls):
        tid = f"t{i}"
        lines.append({"sessionId": "sid1", "type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": tid, "name": "Bash", "input": {"command": cmd}}]}})
        lines.append({"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": tid, "content": out, "is_error": err}]}})
    p = tmp_path / name
    p.write_text("\n".join(json.dumps(x) for x in lines) + "\n" + "\n".join(extra_lines))
    return p


PASS = ("python3 -m pytest -q t.py", "3 passed in 0.1s", False)
FAIL = ("python3 -m pytest -q t.py", "1 failed, 2 passed in 0.1s", True)
COMMIT = ("git commit -m x", "[main abc1234] x\n 1 file changed", False)
PUSH_OK = ("git push origin main", "   abc1234..def5678  main -> main", False)
PUSH_REJ = ("git push origin main", " ! [rejected] main -> main (non-fast-forward)", True)


def v(tmp_path, calls):
    return so.assess(_build(tmp_path, calls))


def test_no_signals_unknown(tmp_path):
    # no outcome signal; the transcript ends on a tool result with no final report
    r = v(tmp_path, [("ls", "a", False)])
    assert r["verdict"] == "aborted" and r["signals"]["commits"] == 0


def test_success_and_pytest_mutation(tmp_path):
    assert v(tmp_path, [PASS, COMMIT])["verdict"] == "success"
    assert v(tmp_path, [FAIL, COMMIT[:3]])["verdict"] == "partial"  # commit after fail
    assert v(tmp_path, [COMMIT, FAIL])["verdict"] == "failure"


def test_later_pass_supersedes_fail(tmp_path):
    assert v(tmp_path, [FAIL, PASS, COMMIT])["verdict"] == "success"
    assert v(tmp_path, [PASS, FAIL])["verdict"] == "failure"


def test_check_exit_code_flips(tmp_path):
    ok = ("python3 scripts/x.py --check", "ok", False)
    bad = ("python3 scripts/x.py --check", "Exit code 1\nbroken", True)
    assert v(tmp_path, [ok, COMMIT])["verdict"] == "success"
    assert v(tmp_path, [bad, COMMIT, bad])["verdict"] == "failure"


def test_commit_sha_signal(tmp_path):
    r = v(tmp_path, [PASS, COMMIT])
    assert r["last_commit_sha"] == "abc1234" and r["signals"]["commits"] == 1
    nosha = ("git commit -m x", "nothing to commit", True)
    r = v(tmp_path, [PASS, nosha])
    assert r["last_commit_sha"] is None and r["verdict"] == "partial"


def test_push_outcomes(tmp_path):
    r = v(tmp_path, [PASS, COMMIT, PUSH_OK])
    assert r["pushed"] is True and r["verdict"] == "success"
    r = v(tmp_path, [PASS, COMMIT, PUSH_REJ])
    assert r["pushed"] is False and r["verdict"] == "partial"
    assert r["signals"]["push_rejected"] == 1


def test_serialized_push(tmp_path):
    ok = ("python3 scripts/serialized_push.py", "   a1b2c3d..e4f5a6b  main -> main", False)
    bad = ("python3 scripts/serialized_push.py", "Exit code 1\nfailed to push", True)
    assert v(tmp_path, [ok])["pushed"] is True
    assert v(tmp_path, [bad])["pushed"] is False


def test_dry_run_commit_ignored(tmp_path):
    r = v(tmp_path, [PASS, ("git commit --dry-run", "[main abc1234] x", False)])
    assert r["signals"]["commits"] == 0


def test_malformed_lines_counted(tmp_path):
    p = _build(tmp_path, [PASS, COMMIT], extra_lines=["{not json", "[1,2]"])
    r = so.assess(p)
    assert r["signals"]["malformed_lines"] == 2 and r["verdict"] == "success"


def test_codex_rollout(tmp_path):
    def rec(i, payload):
        return json.dumps({"ordinal": i, "type": "response_item", "payload": payload})
    meta = json.dumps({"ordinal": 0, "type": "session_meta", "payload": {"id": "cx1"}})
    def run(out):
        return [meta,
                rec(1, {"type": "custom_tool_call", "call_id": "c", "input": "exec_command({cmd:\"pytest -q\"})"}),
                rec(2, {"type": "custom_tool_call_output", "call_id": "c",
                        "output": [{"type": "input_text", "text": json.dumps({"exit_code": 0, "output": out})}]}),
                rec(3, {"type": "custom_tool_call", "call_id": "d", "input": "git commit -m x"}),
                rec(4, {"type": "custom_tool_call_output", "call_id": "d",
                        "output": [{"type": "input_text", "text": json.dumps({"exit_code": 0, "output": "[main 1234567] x"})}]})]
    p = tmp_path / "r.jsonl"
    p.write_text("\n".join(run("2 passed in 1s")))
    r = so.assess(p)
    assert r["harness"] == "codex" and r["session_id"] == "cx1" and r["verdict"] == "success"
    p.write_text("\n".join(run("1 failed in 1s")))
    assert so.assess(p)["verdict"] == "partial"


def test_cli(tmp_path, capsys):
    p = _build(tmp_path, [PASS, COMMIT])
    assert so.main(["--files", str(p)]) == 0
    row = json.loads(capsys.readouterr().out)
    assert row["schema"] == "session_oracle.v1" and row["session_id"] == "sid1"
    out = tmp_path / "o.jsonl"
    assert so.main(["--root", str(tmp_path), "--limit", "1", "--out", str(out)]) == 0
    assert len(out.read_text().splitlines()) == 1


def _raw(tmp_path, lines):
    p = tmp_path / "r.jsonl"
    p.write_text("\n".join(json.dumps(x) for x in lines) + "\n")
    return so.assess(p)


def _asst(*blocks):
    return {"sessionId": "s", "type": "assistant", "message": {"role": "assistant", "content": list(blocks)}}


TU = {"type": "tool_use", "id": "a", "name": "Read", "input": {}}
TR = {"type": "user", "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "a", "content": "x"}]}}
HB = {"type": "tool_use", "id": "h", "name": "SubagentHandback", "input": {"message": "r"}}


def test_handback_is_delivered_not_success(tmp_path):
    r = _raw(tmp_path, [_asst(TU), TR, _asst(HB)])
    assert r["verdict"] == "delivered_no_outcome" and r["signals"]["end"] == "handback"


def test_ending_on_tool_is_aborted(tmp_path):  # paired mutation: drop the handback
    assert _raw(tmp_path, [_asst(TU), TR])["verdict"] == "aborted"


def test_final_text_delivered_vs_api_error(tmp_path):
    txt = _asst({"type": "text", "text": "done"})
    assert _raw(tmp_path, [_asst(TU), TR, txt])["verdict"] == "delivered_no_outcome"
    assert _raw(tmp_path, [_asst(TU), TR, txt, {"isApiErrorMessage": True}])["verdict"] == "aborted"


def test_no_work_and_empty(tmp_path):
    assert _raw(tmp_path, [{"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": "hi"}]}}])["verdict"] == "no_work"


def test_refinement_never_overrides_signal_verdicts(tmp_path):
    p = _build(tmp_path, [PASS, COMMIT])
    with p.open("a") as fh:
        fh.write(json.dumps(_asst(HB)) + "\n")
    assert so.assess(p)["verdict"] == "success"


def _write_session(path, lines):
    path.write_text("\n".join(json.dumps(line) for line in lines) + "\n")
    return path


def _delegation(tool="Agent", *, status="completed", error=False, tool_id="dispatch", agent_id="child"):
    call = _asst({"type": "tool_use", "name": tool, "id": tool_id, "input": {}})
    result = {"sessionId": "s", "type": "user", "toolUseResult": {"agentId": agent_id, "status": status},
              "message": {"content": [{"type": "tool_result", "tool_use_id": tool_id, "is_error": error,
                                       "content": [{"type": "text", "text": "Success. All tests passed."}]}]}}
    return call, result


def _child(tmp_path):
    child = tmp_path / "s" / "subagents" / "agent-child.jsonl"
    child.parent.mkdir(parents=True)
    _write_session(child, [dict(_asst(HB), agentId="child", isSidechain=True)])
    return child, tmp_path / "s.jsonl"


@pytest.mark.parametrize(("status", "error", "outcome", "verdict"), [
    ("async_launched", False, None, "delivered_no_outcome"),
    ("running", False, None, "delivered_no_outcome"),
    ("completed", False, None, "delivered_no_outcome"),
    ("success", False, "success", "success"),
    ("success", True, "failure", "failure"),
    ("failed", False, "failure", "failure"),
])
def test_parent_status_and_tool_error(tmp_path, status, error, outcome, verdict):
    child, parent = _child(tmp_path)
    _write_session(parent, _delegation(status=status, error=error))
    row = so.assess(child)
    assert row["verdict"] == verdict
    assert row["signals"]["local_verdict"] == "delivered_no_outcome"
    assert row["signals"]["end"] == "handback"
    assert row["signals"]["parent_join"] == "matched"
    assert row["signals"]["parent_result"] == {
        "path": str(parent), "session_id": "s", "agent_id": "child", "tool_use_id": "dispatch",
        "status": status, "is_error": error, "outcome": outcome,
    }


def test_async_launch_cannot_claim_success(tmp_path):
    child, parent = _child(tmp_path)
    call, result = _delegation(status="async_launched")
    result["toolUseResult"]["outcome"] = "success"
    _write_session(parent, [call, result])
    assert so.assess(child)["verdict"] == "delivered_no_outcome"


def test_malformed_parent_labels_remain_without_outcome(tmp_path):
    child, parent = _child(tmp_path)
    call, result = _delegation(status=["success"])
    result["toolUseResult"]["outcome"] = {"success": True}
    _write_session(parent, [call, result])
    row = so.assess(child)
    assert row["verdict"] == "delivered_no_outcome"
    assert row["signals"]["parent_result"]["status"] is None


@pytest.mark.parametrize("mutation", ["session", "call_session", "tool_id", "agent_id", "name", "multiple_blocks",
                                      "no_metadata", "sidechain"])
def test_parent_result_must_match_structured_identity(tmp_path, mutation):
    child, parent = _child(tmp_path)
    call, result = _delegation(status="success")
    if mutation == "session":
        call["sessionId"] = result["sessionId"] = "unrelated"
    elif mutation == "call_session":
        call["sessionId"] = "unrelated"
    elif mutation == "tool_id":
        result["message"]["content"][0]["tool_use_id"] = "other-dispatch"
    elif mutation == "agent_id":
        result["toolUseResult"]["agentId"] = "other-child"
    elif mutation == "name":
        call["message"]["content"][0]["name"] = "Read"
    elif mutation == "multiple_blocks":
        result["message"]["content"].append({"type": "tool_result", "tool_use_id": "other-dispatch"})
    elif mutation == "no_metadata":
        result.pop("toolUseResult")
        result["message"]["content"][0]["is_error"] = True
    elif mutation == "sidechain":
        call["isSidechain"] = result["isSidechain"] = True
    _write_session(parent, [call, result])
    row = so.assess(child)
    assert row["verdict"] == "delivered_no_outcome"
    assert row["signals"]["parent_join"] == "missing"
    assert "parent_result" not in row["signals"]


def test_missing_parent_and_conflicting_results(tmp_path):
    child, parent = _child(tmp_path)
    assert so.assess(child)["signals"]["parent_join"] == "missing"
    delegation = _delegation(tool="Task", status="success")
    _write_session(parent, [*delegation, *delegation])
    assert so.assess(child)["verdict"] == "success"  # Duplicate logs carry identical evidence.
    _write_session(parent, [*delegation, *_delegation(status="failed", tool_id="resume")])
    row = so.assess(child)
    assert row["verdict"] == "delivered_no_outcome"
    assert row["signals"]["parent_join"] == "ambiguous"
    assert "parent_result" not in row["signals"]


@pytest.mark.parametrize(("calls", "expected"), [
    ([PASS, COMMIT], "success"), ([FAIL], "failure"), ([COMMIT], "partial"),
])
def test_parent_result_preserves_local_outcome(tmp_path, calls, expected):
    child, parent = _child(tmp_path)
    records = [json.loads(line) for line in _build(tmp_path, calls).read_text().splitlines()]
    _write_session(child, [dict(record, sessionId="s", agentId="child") for record in records])
    _write_session(parent, _delegation(status="failed" if expected == "success" else "success"))
    joined = so.assess(child)
    assert joined["verdict"] == expected
    assert joined == so.assess(child, join_parent=False)


def test_local_only_replay_preserves_launch_verdict(tmp_path):
    child, parent = _child(tmp_path)
    _write_session(parent, _delegation(status="async_launched"))
    parent_cache = {}
    baseline = so.assess(child, parent_cache=parent_cache, join_parent=False)
    assert parent_cache == {}
    assert baseline["verdict"] == "delivered_no_outcome"
    assert baseline["signals"]["end"] == "handback"

    joined = so.assess(child, parent_cache=parent_cache)
    assert joined["signals"].pop("parent_join") == "matched"
    assert joined["signals"].pop("parent_result")["outcome"] is None
    assert joined == baseline


def test_cli_explicit_parent(tmp_path, capsys):
    child, parent = _child(tmp_path)
    parent = parent.with_name("relocated.jsonl")
    _write_session(parent, _delegation(status="success"))
    assert so.main(["--parent", str(parent), "--files", str(child)]) == 0
    row = json.loads(capsys.readouterr().out)
    assert row["verdict"] == "success"
    assert row["signals"]["parent_result"]["path"] == str(parent)


def _acceptance(tmp_path, *, result="pass", name="acceptance.json", **overrides):
    gate = tmp_path / "gate.log"
    gate.write_bytes(b"explicit gate evidence")
    identity = {"parent_session_id": "s", "dispatch_tool_use_id": "dispatch",
                "child_agent_id": "child", "task_id": "FM4-example"}
    identity.update(overrides)
    path = tmp_path / name
    record = so.task_acceptance.write_record(
        path, **identity, gate_result=result, evidence_path=gate,
        evidence_sha256=hashlib.sha256(gate.read_bytes()).hexdigest())
    return path, record


@pytest.mark.parametrize(("gate", "verdict"), [("pass", "success"), ("fail", "failure")])
def test_task_acceptance_applies_only_when_opted_in(tmp_path, gate, verdict):
    child, parent = _child(tmp_path)
    _write_session(parent, _delegation())
    path, record = _acceptance(tmp_path, result=gate)
    baseline = so.assess(child)
    assert baseline["verdict"] == "delivered_no_outcome"
    assert "task_acceptance" not in baseline["signals"]

    row = so.assess(child, task_id="FM4-example", acceptance_paths=[path, path])
    assert row["verdict"] == verdict
    assert row["signals"]["local_verdict"] == "delivered_no_outcome"
    signal = row["signals"]["task_acceptance"]
    assert signal["disposition"] == "applied"
    assert signal["caller_task_id"] == "FM4-example"
    assert signal["identity"] == {identity: record[identity] for identity in so.task_acceptance.IDENTITIES}
    assert signal["sources"] == [{"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                                  "disposition": "verified", "record": record}] * 2


def test_task_acceptance_v11_transcript_snapshot_record_is_consumed(tmp_path):
    child, parent = _child(tmp_path)
    _write_session(parent, _delegation())
    gate = tmp_path / "gate.log"
    gate.write_bytes(b"explicit gate evidence")
    path = tmp_path / "acceptance-v11.json"
    record = so.task_acceptance.write_record(
        path, parent_session_id="s", dispatch_tool_use_id="dispatch", child_agent_id="child",
        task_id="FM4-example", gate_result="fail", evidence_path=gate,
        evidence_sha256=hashlib.sha256(gate.read_bytes()).hexdigest(),
        child_transcript=child, parent_transcript=parent)
    assert record["schema"] == so.task_acceptance.SCHEMA_V11
    row = so.assess(child, task_id="FM4-example", acceptance_paths=[path])
    assert row["verdict"] == "failure"
    assert row["signals"]["task_acceptance"]["disposition"] == "applied"
    # Paired mutation: a tampered transcript snapshot declines the join.
    snap = Path(record["transcripts"]["parent"]["path"])
    snap.chmod(0o644)
    snap.write_bytes(b"rotated and replaced")
    snap.chmod(0o444)
    row = so.assess(child, task_id="FM4-example", acceptance_paths=[path])
    assert row["verdict"] == "delivered_no_outcome"
    assert row["signals"]["task_acceptance"]["disposition"] != "applied"


@pytest.mark.parametrize("identity", ["parent_session_id", "dispatch_tool_use_id", "child_agent_id", "task_id"])
def test_task_acceptance_requires_every_identity(tmp_path, identity):
    child, parent = _child(tmp_path)
    _write_session(parent, _delegation())
    path, _ = _acceptance(tmp_path, **{identity: "unrelated"})
    row = so.assess(child, task_id="FM4-example", acceptance_paths=[path])
    assert row["verdict"] == "delivered_no_outcome"
    signal = row["signals"]["task_acceptance"]
    assert signal["disposition"] == "identity_mismatch"
    assert signal["sources"][0]["disposition"] == "identity_mismatch"


@pytest.mark.parametrize(("mutation", "disposition"), [
    ("no-task-id", "missing_task_identity"),
    ("no-parent", "missing_parent_identity"),
    ("without-join", "missing_parent_identity"),
    ("ambiguous-parent", "ambiguous_parent"),
    ("ambiguous-child", "ambiguous_child"),
    ("reused-dispatch", "ambiguous_parent"),
    ("async_launched", "nonterminal_parent"),
    ("running", "nonterminal_parent"),
])
def test_task_acceptance_requires_terminal_unambiguous_join(tmp_path, mutation, disposition):
    child, parent = _child(tmp_path)
    delegation = _delegation(status=mutation if mutation in ("async_launched", "running") else "completed")
    if mutation != "no-parent":
        _write_session(parent, delegation)
    if mutation == "ambiguous-parent":
        _write_session(parent, [*delegation, *_delegation(tool_id="other-dispatch")])
    if mutation == "reused-dispatch":
        _, another_result = _delegation(agent_id="unrelated")
        _write_session(parent, [*delegation, another_result])
    if mutation == "ambiguous-child":
        _write_session(child, [dict(_asst(HB), agentId="child"), dict(_asst(HB), agentId="other")])
    path, _ = _acceptance(tmp_path)
    baseline = so.assess(child, join_parent=mutation != "without-join")
    row = so.assess(child, task_id=None if mutation == "no-task-id" else "FM4-example",
                    join_parent=mutation != "without-join", acceptance_paths=[path])
    assert row["verdict"] == "delivered_no_outcome"
    assert row["signals"].pop("task_acceptance")["disposition"] == disposition
    assert row == baseline
    if mutation == "reused-dispatch":
        assert baseline["signals"]["parent_join"] == "matched"


def test_task_acceptance_rechecks_cached_parent_attribution(tmp_path):
    child, parent = _child(tmp_path)
    delegation = _delegation()
    _write_session(parent, delegation)
    parent_cache = {}
    assert so.assess(child, parent_cache=parent_cache)["signals"]["parent_join"] == "matched"
    _, another_result = _delegation(agent_id="unrelated")
    _write_session(parent, [*delegation, another_result])
    path, _ = _acceptance(tmp_path)
    row = so.assess(child, task_id="FM4-example", acceptance_paths=[path], parent_cache=parent_cache)
    assert row["verdict"] == "delivered_no_outcome"
    assert row["signals"]["task_acceptance"]["disposition"] == "ambiguous_parent"


@pytest.mark.parametrize("mutation", ["missing", "malformed", "duplicate-field", "extra-field", "mutated-evidence"])
def test_task_acceptance_rejects_unverified_evidence(tmp_path, mutation):
    child, parent = _child(tmp_path)
    _write_session(parent, _delegation())
    path, record = _acceptance(tmp_path)
    if mutation == "missing":
        path.unlink()
    elif mutation == "mutated-evidence":
        evidence = Path(record["evidence"]["path"])
        evidence.chmod(0o644)
        evidence.write_bytes(b"changed gate evidence")
        evidence.chmod(0o444)
    else:
        if mutation == "malformed":
            raw = "{"
        elif mutation == "duplicate-field":
            raw = json.dumps(record)[:-1] + ', "task_id": "FM4-example"}'
        else:
            raw = json.dumps(dict(record, unrecognized=True))
        path.chmod(0o644)
        path.write_text(raw)
    row = so.assess(child, task_id="FM4-example", acceptance_paths=[path])
    assert row["verdict"] == "delivered_no_outcome"
    signal = row["signals"]["task_acceptance"]
    assert signal["disposition"] == "invalid_record"
    assert "record" not in signal["sources"][0]


@pytest.mark.parametrize(("second", "disposition"), [
    ("fail", "conflicting_records"),
    ("mismatch", "identity_mismatch"),
    ("missing", "invalid_record"),
])
def test_task_acceptance_fails_closed_when_supplied_set_disagrees(tmp_path, second, disposition):
    child, parent = _child(tmp_path)
    _write_session(parent, _delegation())
    passing, _ = _acceptance(tmp_path)
    if second == "missing":
        additional = tmp_path / "missing.json"
    elif second == "mismatch":
        additional, _ = _acceptance(tmp_path, name="other.json", task_id="unrelated")
    else:
        additional, _ = _acceptance(tmp_path, name="failure.json", result=second)
    for inputs in ([passing, additional], [additional, passing]):
        row = so.assess(child, task_id="FM4-example", acceptance_paths=inputs)
        assert row["verdict"] == "delivered_no_outcome"
        assert row["signals"]["task_acceptance"]["disposition"] == disposition


@pytest.mark.parametrize(("calls", "result", "expected"), [
    ([PASS, COMMIT], "fail", "success"),
    ([FAIL], "pass", "failure"),
    ([COMMIT], "pass", "partial"),
])
def test_task_acceptance_preserves_local_outcome(tmp_path, calls, result, expected):
    child, parent = _child(tmp_path)
    records = [json.loads(line) for line in _build(tmp_path, calls).read_text().splitlines()]
    _write_session(child, [dict(record, sessionId="s", agentId="child") for record in records])
    _write_session(parent, _delegation())
    path, _ = _acceptance(tmp_path, result=result)
    row = so.assess(child, task_id="FM4-example", acceptance_paths=[path])
    assert row["verdict"] == expected
    assert row["signals"].pop("task_acceptance")["disposition"] == "local_outcome"
    assert row == so.assess(child)


@pytest.mark.parametrize(("result", "disposition"), [
    ("pass", "corroborates_parent"), ("fail", "conflicting_parent_outcome"),
])
def test_task_acceptance_preserves_explicit_parent_outcome(tmp_path, result, disposition):
    child, parent = _child(tmp_path)
    _write_session(parent, _delegation(status="success"))
    path, _ = _acceptance(tmp_path, result=result)
    row = so.assess(child, task_id="FM4-example", acceptance_paths=[path])
    assert row["verdict"] == "success"
    assert row["signals"]["task_acceptance"]["disposition"] == disposition


def test_cli_task_acceptance(tmp_path, capsys):
    child, parent = _child(tmp_path)
    _write_session(parent, _delegation())
    path, _ = _acceptance(tmp_path)
    files = ["--files", str(child)]
    accepted = ["--task-acceptance", str(path)]
    caller_identity = ["--task-id", "FM4-example"]
    assert so.main(files + accepted + caller_identity) == 0
    row = json.loads(capsys.readouterr().out)
    assert row["verdict"] == "success"

    for args in (files + accepted, accepted + caller_identity,
                 files + [str(child)] + accepted + caller_identity, files + caller_identity):
        with pytest.raises(SystemExit) as exc:
            so.main(args)
        assert exc.value.code == 2
