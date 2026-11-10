import json
import sys
from pathlib import Path

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
    assert v(tmp_path, [("ls", "a", False)])["verdict"] == "unknown"


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
