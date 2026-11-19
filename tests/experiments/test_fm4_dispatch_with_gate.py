import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/experiments/fm4"))
import dispatch_with_gate as dwg
import task_acceptance


def argv(tmp_path, *gate, task_id="FM4/demo", dispatch="toolu_1", extra=()):
    return ["--root", str(tmp_path / "records"), "--cwd", str(tmp_path.resolve()), "--timeout-s", "10",
            "--parent-session-id", "sid-1", "--dispatch-tool-use-id", dispatch,
            "--child-agent-id", "agent-a", "--task-id", task_id, *extra, "--", *gate]


@pytest.mark.parametrize(("code", "result"), [(0, "pass"), (3, "fail")])
def test_writes_valid_record_at_deterministic_path(tmp_path, capsys, code, result):
    child = tmp_path / "child.jsonl"
    child.write_text("{}\n")
    rc = dwg.main(argv(tmp_path, sys.executable, "-c", f"raise SystemExit({code})",
                       extra=("--child-transcript", str(child))))
    assert rc == 0
    out = capsys.readouterr().out.strip().splitlines()
    expected = tmp_path / "records" / "FM4__demo" / "toolu_1.json"
    assert out == [str(expected)]  # stdout carries only the record path
    record = task_acceptance.validate_record(json.loads(expected.read_text()))
    assert record["gate_result"] == result and record["task_id"] == "FM4/demo"
    assert record["schema"] == task_acceptance.SCHEMA_V11


def test_second_run_for_same_dispatch_refuses_without_executing(tmp_path, capsys):
    assert dwg.main(argv(tmp_path, sys.executable, "-c", "pass")) == 0
    capsys.readouterr()
    marker = tmp_path / "ran"
    assert dwg.main(argv(tmp_path, sys.executable, "-c", f"open({str(marker)!r}, 'w')")) == 1
    assert "already exists" in capsys.readouterr().err
    assert not marker.exists()


@pytest.mark.parametrize(("task_id", "dispatch"), [("../x", "toolu_1"), ("ok", "a/b"), ("a b", "toolu_1"), ("ok", "")])
def test_bad_identity_creates_nothing(tmp_path, capsys, task_id, dispatch):
    assert dwg.main(argv(tmp_path, sys.executable, "-c", "pass", task_id=task_id, dispatch=dispatch)) == 1
    assert not (tmp_path / "records").exists()
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("gate", [["/nonexistent/gate"], [sys.executable, "-c", "import os,signal; os.kill(os.getpid(), signal.SIGTERM)"]])
def test_launch_error_or_signal_yields_no_record(tmp_path, capsys, gate):
    assert dwg.main(argv(tmp_path, *gate)) == 1
    assert not (tmp_path / "records" / "FM4__demo" / "toolu_1.json").exists()
    assert capsys.readouterr().out == ""


def test_post_write_validation_failure_is_reported(tmp_path, capsys, monkeypatch):
    def broken(_record):
        raise ValueError("evidence digest mismatch")
    monkeypatch.setattr(dwg, "validate_record", broken)
    assert dwg.main(argv(tmp_path, sys.executable, "-c", "pass")) == 1
    captured = capsys.readouterr()
    assert "failed validation" in captured.err and captured.out == ""


def test_missing_gate_is_a_usage_error(tmp_path):
    with pytest.raises(SystemExit):
        dwg.main(argv(tmp_path)[:-1])
