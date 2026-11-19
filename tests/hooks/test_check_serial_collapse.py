import json
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parents[2] / "scripts" / "hooks" / "check_serial_collapse.py"


def run(log, payload, raw=None):
    env = {"AGENT_DISPATCH_AUDIT_LOG": str(log), "PATH": "/usr/bin:/bin"}
    p = subprocess.run([sys.executable, str(HOOK)], input=raw if raw is not None else json.dumps(payload),
                       capture_output=True, text=True, env=env)
    assert p.returncode == 0
    return p.stderr


def boundary(task, sid="s1", agent_id=None):
    d = {"tool_name": "Bash", "session_id": sid, "tool_input": {"command":
         f"python3 scripts/coordination/session_bus.py append --agent mainA --target heartbeat "
         f"--json '{{\"state\":\"working\",\"task_id\":\"{task}\"}}'"}}
    if agent_id:
        d["agent_id"] = agent_id
    return d


def dispatch(log, sid="s1"):
    with open(log, "a") as fh:
        fh.write(json.dumps({"hook": "check_agent_dispatch", "session_id": sid}) + "\n")


def rows(log):
    return [json.loads(l) for l in open(log) if '"check_serial_collapse"' in l]


def test_three_serial_tasks_flag(tmp_path):
    log = tmp_path / "a.jsonl"
    for t in ("t1", "t2"):
        assert "serial_collapse" not in run(log, boundary(t))
    assert "serial_collapse" in run(log, boundary("t3"))
    assert rows(log)[-1]["zero_streak"] == 3


def test_dispatch_breaks_streak(tmp_path):  # paired mutation of the above
    log = tmp_path / "a.jsonl"
    run(log, boundary("t1")); run(log, boundary("t2"))
    dispatch(log)
    assert "serial_collapse" not in run(log, boundary("t3"))
    assert rows(log)[-1]["width"] == 1


def test_other_session_dispatch_does_not_count(tmp_path):
    log = tmp_path / "a.jsonl"
    run(log, boundary("t1")); run(log, boundary("t2"))
    dispatch(log, sid="other")
    assert "serial_collapse" in run(log, boundary("t3"))


def test_subagent_and_non_boundary_ignored(tmp_path):
    log = tmp_path / "a.jsonl"
    run(log, boundary("t1", agent_id="sub"))
    run(log, {"tool_name": "Bash", "session_id": "s1", "tool_input": {"command": "ls"}})
    assert not log.exists()


def test_malformed_input_allows(tmp_path):
    log = tmp_path / "a.jsonl"
    assert "internal error allowed" in run(log, None, raw="{not json")
