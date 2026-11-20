"""AK audit C2: hand-back sweep lists background tasks left alive; silent otherwise; never blocks."""
import json
import os
import subprocess
import sys

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts", "hooks", "posttool_handback_sweep.py")


def bg(uid, cmd):
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": uid, "name": "Bash",
                                                          "input": {"command": cmd, "run_in_background": True}}]}}


def res(uid, tid):
    return {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": uid,
            "content": f"Command running in background with ID: {tid}. Output is being written to: /x (ID: {tid})"}]}}


def write(tmp_path, recs):
    p = tmp_path / "agent.jsonl"
    p.write_text("".join(json.dumps(r) + "\n" for r in recs))
    return str(p)


def run(payload):
    return subprocess.run([sys.executable, HOOK], input=json.dumps(payload) if not isinstance(payload, str) else payload,
                          capture_output=True, text=True)


def test_alive_task_is_listed_on_posttool(tmp_path):
    p = write(tmp_path, [bg("u1", "watch.sh"), res("u1", "b1"), bg("u2", "build.sh"), res("u2", "b2"),
                         {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "u3", "name": "TaskStop", "input": {"task_id": "b2"}}]}}])
    r = run({"hook_event_name": "PostToolUse", "tool_name": "Agent", "agent_transcript_path": p})
    assert r.returncode == 0
    ctx = json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "b1 (watch.sh)" in ctx and "b2" not in ctx


def test_subagent_stop_uses_system_message(tmp_path):
    p = write(tmp_path, [bg("u1", "watch.sh"), res("u1", "b1")])
    r = run({"hook_event_name": "SubagentStop", "transcript_path": p})
    assert r.returncode == 0 and "b1" in json.loads(r.stdout)["systemMessage"]


def test_finished_stopped_or_foreground_tasks_are_silent(tmp_path):
    note = "<task-notification><task-id>b1</task-id><status>completed</status></task-notification>"
    p = write(tmp_path, [bg("u1", "x"), res("u1", "b1"), {"type": "user", "message": {"content": note}},
                         {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "u2", "name": "Bash", "input": {"command": "ls"}}]}}])
    r = run({"hook_event_name": "PostToolUse", "tool_name": "Agent", "agent_transcript_path": p})
    assert r.returncode == 0 and r.stdout == ""


def test_never_blocks_on_bad_input(tmp_path):
    for payload in ("not json", {"hook_event_name": "PostToolUse", "tool_name": "Agent"},
                    {"hook_event_name": "PostToolUse", "tool_name": "Agent", "agent_transcript_path": "/nonexistent"},
                    {"hook_event_name": "PostToolUse", "tool_name": "Bash", "agent_transcript_path": write(tmp_path, [bg("u", "x"), res("u", "b")])},
                    {"hook_event_name": "PostToolUse", "tool_name": "Agent", "transcript_path": write(tmp_path, [bg("u", "x"), res("u", "b")])}):
        r = run(payload)
        assert r.returncode == 0 and r.stdout == ""
