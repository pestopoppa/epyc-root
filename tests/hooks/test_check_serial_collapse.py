import json
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parents[2] / "scripts" / "hooks" / "check_serial_collapse.py"


def run(log, payload, raw=None, threshold=None):
    env = {"AGENT_DISPATCH_AUDIT_LOG": str(log), "PATH": "/usr/bin:/bin"}
    if threshold is not None:
        env["SERIAL_COLLAPSE_THRESHOLD"] = threshold
    p = subprocess.run([sys.executable, str(HOOK)], input=raw if raw is not None else json.dumps(payload),
                       capture_output=True, text=True, env=env)
    assert p.returncode == 0
    return p.stderr


def boundary(task, sid="s1", agent_id=None):
    d = {"tool_name": "Bash", "hook_event_name": "PostToolUse", "session_id": sid, "tool_response": {"stdout": "", "stderr": "", "interrupted": False, "isImage": False}, "tool_input": {"command":
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


def test_repeated_task_not_counted_and_distinct_task_counts(tmp_path):
    log = tmp_path / "a.jsonl"
    run(log, boundary("t1")); run(log, boundary("t1")); run(log, boundary("t2"))
    assert len(rows(log)) == 2
    assert "serial_collapse" in run(log, boundary("t3"))
    assert len(rows(log)) == 3


def test_failed_or_unverified_response_refused_success_accepted(tmp_path):
    log = tmp_path / "a.jsonl"
    failure = boundary("t1"); failure["hook_event_name"] = "PostToolUseFailure"
    failed = boundary("t1"); failed["tool_response"]["exit_code"] = 1
    interrupted = boundary("t1"); interrupted["tool_response"]["interrupted"] = True
    missing = boundary("t1"); missing.pop("tool_response")
    unknown = boundary("t1"); unknown["tool_response"].pop("interrupted")
    no_event = boundary("t1"); no_event.pop("hook_event_name")
    invalid_status = boundary("t1"); invalid_status["tool_response"]["exit_code"] = None
    for payload in (failure, failed, interrupted, missing, unknown, no_event, invalid_status):
        run(log, payload)
    assert not log.exists()
    run(log, boundary("t1"))  # documented Bash response, without exit_code
    explicit = boundary("t2"); explicit["tool_response"]["exit_code"] = 0
    run(log, explicit)
    assert len(rows(log)) == 2


def test_echo_and_composed_commands_refused_direct_accepted(tmp_path):
    log = tmp_path / "a.jsonl"
    good = boundary("t1")
    command = good["tool_input"]["command"]
    for text in ("echo " + command, "echo prefix; " + command,
                 command + " || true", "python3 evil_session_bus.py append --target heartbeat --json '{}'"):
        bad = boundary("t1"); bad["tool_input"]["command"] = text
        run(log, bad)
    assert not log.exists()
    run(log, good)
    assert len(rows(log)) == 1


def test_invalid_threshold_warn_only_and_valid_threshold_flags(tmp_path):
    log = tmp_path / "a.jsonl"
    for value in ("bad", "0", "-1"):
        assert "internal error allowed" in run(log, boundary("t1"), threshold=value)
        assert not log.exists()
    assert "serial_collapse" in run(log, boundary("t1"), threshold="1")


def test_duplicate_preserves_dispatch_and_task_ids_are_session_local(tmp_path):
    log = tmp_path / "a.jsonl"
    run(log, boundary("t1")); dispatch(log)
    run(log, boundary("t1")); run(log, boundary("t2"))
    run(log, boundary("t1", sid="other"))
    records = rows(log)
    assert [(r["session_id"], r["task_id"], r["width"]) for r in records] == [
        ("s1", "t1", 0), ("s1", "t2", 1), ("other", "t1", 0)]


def test_legacy_duplicate_boundaries_do_not_inflate_streak(tmp_path):
    log = tmp_path / "a.jsonl"
    legacy = {"hook": "check_serial_collapse", "session_id": "s1", "task_id": "t1", "width": 0}
    log.write_text((json.dumps(legacy) + "\n") * 2)
    assert "serial_collapse" not in run(log, boundary("t2"))
    assert rows(log)[-1]["zero_streak"] == 2
    assert "serial_collapse" in run(log, boundary("t3"))
    assert rows(log)[-1]["zero_streak"] == 3
