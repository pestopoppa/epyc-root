import base64
from datetime import datetime, timezone
import json
from pathlib import Path
import signal
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "scripts/experiments/fm4/run_gate.py"
sys.path.insert(0, str(RUNNER.parent))
import run_gate
import task_acceptance


IDENTITIES = dict(parent_session_id="session-1", dispatch_tool_use_id="toolu_123",
                  child_agent_id="agent-a", task_id="FM4-GATE")


def options(path, *, cwd=None, timeout="5", identities=IDENTITIES):
    args = ["--out", str(path / "record.json"),
            "--cwd", str(path.resolve() if cwd is None else cwd), "--timeout-s", timeout]
    for name, value in identities.items():
        args.extend(["--" + name.replace("_", "-"), value])
    return args


def execution_path(path):
    return path / "record.json.execution.json"


@pytest.mark.parametrize(("returncode", "gate_result"), [(0, "pass"), (7, "fail")])
def test_run_records_gate_result_and_raw_output(tmp_path, capsys, returncode, gate_result):
    gate = [sys.executable, "-c", "import os, sys; "
            "os.write(1, b'\\x00\\xffstdout\\n' * 6000); "
            "os.write(2, b'\\x80stderr\\r\\n'); sys.exit(int(sys.argv[1]))", str(returncode)]
    before = datetime.now(timezone.utc)
    assert run_gate.main([*options(tmp_path), "--", *gate]) == 0
    after = datetime.now(timezone.utc)
    output = capsys.readouterr()
    assert not output.err
    record = json.loads(output.out)
    assert task_acceptance.validate_record(record) == record
    assert record == json.loads((tmp_path / "record.json").read_text())
    assert record["gate_result"] == gate_result
    assert {name: record[name] for name in IDENTITIES} == IDENTITIES

    source = execution_path(tmp_path).read_bytes()
    assert Path(record["evidence"]["path"]).read_bytes() == source
    evidence = json.loads(source)
    assert evidence["schema"] == "fm4.gate_execution.v1"
    assert evidence["argv"] == gate
    assert evidence["cwd"] == str(tmp_path.resolve())
    assert evidence["timeout_s"] == 5
    assert evidence["returncode"] == returncode
    assert evidence["timed_out"] is False
    assert evidence["launch_error"] is None
    assert {name: evidence[name] for name in IDENTITIES} == IDENTITIES
    started = datetime.fromisoformat(evidence["started_at"])
    ended = datetime.fromisoformat(evidence["ended_at"])
    assert started.tzinfo == ended.tzinfo == timezone.utc
    assert before <= started <= ended <= after
    assert base64.b64decode(evidence["stdout_base64"], validate=True) == b"\x00\xffstdout\n" * 6000
    assert base64.b64decode(evidence["stderr_base64"], validate=True) == b"\x80stderr\r\n"


@pytest.mark.parametrize("timed_out", [True, False])
def test_incomplete_attempt_preserves_execution_without_acceptance(tmp_path, capsys, timed_out):
    if timed_out:
        gate = [sys.executable, "-c", "import os, time; os.write(1, b'partial'); time.sleep(10)"]
    else:
        gate = [str(tmp_path / "missing-executable")]
    assert run_gate.main([*options(tmp_path, timeout="0.5"), "--", *gate]) == 1
    output = capsys.readouterr()
    assert not output.out
    assert ("gate timed out" if timed_out else "gate launch failed") in output.err
    assert not (tmp_path / "record.json").exists()
    assert not (tmp_path / "evidence").exists()
    evidence = json.loads(execution_path(tmp_path).read_text())
    assert evidence["timed_out"] is timed_out
    assert evidence["returncode"] is None
    assert (evidence["launch_error"] is None) is timed_out
    assert base64.b64decode(evidence["stdout_base64"], validate=True) == (b"partial" if timed_out else b"")


def test_signal_termination_preserves_execution_without_acceptance(tmp_path, capsys):
    gate = [sys.executable, "-c", "import os, signal; os.kill(os.getpid(), signal.SIGTERM)"]
    assert run_gate.main([*options(tmp_path), "--", *gate]) == 1
    assert f"gate terminated by signal {signal.SIGTERM.value}" in capsys.readouterr().err
    assert not (tmp_path / "record.json").exists()
    evidence = json.loads(execution_path(tmp_path).read_text())
    assert evidence["returncode"] == -signal.SIGTERM
    assert evidence["timed_out"] is False
    assert evidence["launch_error"] is None


@pytest.mark.parametrize("identity", IDENTITIES)
def test_invalid_identity_does_not_run_gate(tmp_path, capsys, identity):
    identities = {**IDENTITIES, identity: "agent/../invalid"}
    gate = [sys.executable, "-c", "from pathlib import Path; Path('marker').touch()"]
    assert run_gate.main([*options(tmp_path, identities=identities), "--", *gate]) == 1
    assert f"invalid {identity}" in capsys.readouterr().err
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("occupied", ["record.json", "record.json.execution.json", "evidence"])
@pytest.mark.parametrize("kind", ["file", "dangling symlink"])
def test_invalid_output_does_not_run_gate(tmp_path, occupied, kind):
    existing = tmp_path / occupied
    if kind == "file":
        existing.write_text("prior artifact\n")
    else:
        existing.symlink_to(tmp_path / "missing")
    gate = [sys.executable, "-c", "from pathlib import Path; Path('marker').touch()"]
    assert run_gate.main([*options(tmp_path), "--", *gate]) == 1
    assert list(tmp_path.iterdir()) == [existing]
    if kind == "file":
        assert existing.read_text() == "prior artifact\n"
    else:
        assert existing.is_symlink()


@pytest.mark.parametrize("timeout", ["nan", "inf", "0", "-1"])
def test_invalid_timeout_does_not_run_gate(tmp_path, timeout):
    gate = [sys.executable, "-c", "from pathlib import Path; Path('marker').touch()"]
    assert run_gate.main([*options(tmp_path, timeout=timeout), "--", *gate]) == 1
    assert not list(tmp_path.iterdir())


def test_noncanonical_cwd_does_not_run_gate(tmp_path):
    link = tmp_path / "cwd-link"
    link.symlink_to(tmp_path, target_is_directory=True)
    gate = [sys.executable, "-c", "from pathlib import Path; Path('marker').touch()"]
    assert run_gate.main([*options(tmp_path, cwd=link), "--", *gate]) == 1
    assert list(tmp_path.iterdir()) == [link]


def test_gate_requires_separator(tmp_path):
    with pytest.raises(SystemExit) as exc:
        run_gate.main([*options(tmp_path), sys.executable])
    assert exc.value.code == 2
    assert not list(tmp_path.iterdir())


def test_gate_receives_literal_arguments(tmp_path, capsys):
    literal = ["; touch marker", "$(touch marker)", "'quoted'", "*", "--", ""]
    gate = [sys.executable, "-c", "import json, sys; print(json.dumps(sys.argv[1:]))", *literal]
    assert run_gate.main([*options(tmp_path), "--", *gate]) == 0
    assert not (tmp_path / "marker").exists()
    evidence = json.loads(execution_path(tmp_path).read_text())
    assert json.loads(base64.b64decode(evidence["stdout_base64"], validate=True)) == literal
    assert json.loads(capsys.readouterr().out)["gate_result"] == "pass"


def test_isolated_script_help_uses_sibling_writer(tmp_path):
    result = subprocess.run([sys.executable, "-I", "-B", str(RUNNER), "--help"],
                            cwd=tmp_path, capture_output=True, text=True, timeout=5)
    assert result.returncode == 0, result.stderr
    assert "OUT.execution.json" in result.stdout


def test_module_invocation_records_acceptance(tmp_path):
    result = subprocess.run([sys.executable, "-B", "-m", "scripts.experiments.fm4.run_gate",
                             *options(tmp_path), "--", sys.executable, "-c", "pass"],
                            cwd=ROOT, capture_output=True, text=True, timeout=5)
    assert result.returncode == 0, result.stderr
    assert task_acceptance.validate_record(json.loads(result.stdout))["gate_result"] == "pass"
