"""Fixture tests for scripts/hooks/check_agent_dispatch.py (FM-8, warn mode).

Every positive case is paired with a mutation that flips exactly one input and
must flip the verdict, so a hook that always warns (or never warns) fails.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / "scripts" / "hooks" / "check_agent_dispatch.py"
AGENTS = ROOT / ".claude" / "agents"


@pytest.fixture()
def proj(tmp_path: Path) -> Path:
    agents = tmp_path / ".claude" / "agents"
    agents.mkdir(parents=True)
    (agents / "explorer.md").write_text("---\nname: explorer\nmodel: haiku\n---\nbody\n")
    (agents / "nomodel.md").write_text("---\nname: nomodel\ndescription: x\n---\nbody\n")
    return tmp_path


def run(proj: Path, stdin: str):
    log = proj / "logs" / "agent_dispatch_audit.jsonl"
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(proj), "AGENT_DISPATCH_AUDIT_LOG": str(log)}
    res = subprocess.run([sys.executable, str(HOOK)], input=stdin, text=True,
                         capture_output=True, env=env, check=False)
    lines = [json.loads(x) for x in log.read_text().splitlines()] if log.exists() else []
    return res, lines


def dispatch(tool_input: dict, **extra) -> str:
    return json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Agent",
                       "tool_input": tool_input, **extra})


def test_no_model_untyped_warns_and_logs(proj):
    res, lines = run(proj, dispatch({"subagent_type": "general-purpose", "prompt": "SECRET"}))
    assert res.returncode == 0
    assert "no_model_non_project_type" in res.stderr
    assert [l["findings"] for l in lines] == [["no_model_non_project_type"]]
    assert lines[0]["verdict"] == "warn" and lines[0]["mode"] == "warn"
    assert "SECRET" not in json.dumps(lines)  # prompt never logged


def test_mutation_explicit_model_is_clean(proj):
    res, lines = run(proj, dispatch({"subagent_type": "general-purpose", "model": "haiku"}))
    assert res.returncode == 0 and res.stderr == ""
    assert lines[0]["verdict"] == "ok" and lines[0]["findings"] == []


def test_no_model_omitted_subagent_type_warns(proj):
    res, lines = run(proj, dispatch({"prompt": "p"}))
    assert "no_model_non_project_type" in res.stderr and lines[0]["verdict"] == "warn"


def test_project_type_with_model_frontmatter_is_clean(proj):
    res, lines = run(proj, dispatch({"subagent_type": "explorer", "prompt": "p"}))
    assert res.returncode == 0 and res.stderr == ""
    assert lines[0]["verdict"] == "ok"


def test_mutation_project_type_without_model_frontmatter_warns(proj):
    res, lines = run(proj, dispatch({"subagent_type": "nomodel", "prompt": "p"}))
    assert "no_model_non_project_type" in res.stderr and lines[0]["verdict"] == "warn"


def test_mutation_unknown_type_warns(proj):
    res, lines = run(proj, dispatch({"subagent_type": "explorer2", "prompt": "p"}))
    assert "no_model_non_project_type" in res.stderr


def test_fork_with_cheaper_model_warns(proj):
    res, lines = run(proj, dispatch({"subagent_type": "fork", "model": "haiku"}))
    assert res.returncode == 0
    assert "fork_cheaper_model" in res.stderr
    assert lines[0]["findings"] == ["fork_cheaper_model"]


def test_mutation_fork_without_model_is_clean(proj):
    res, lines = run(proj, dispatch({"subagent_type": "fork", "prompt": "p"}))
    assert res.stderr == "" and lines[0]["verdict"] == "ok"


def test_mutation_non_fork_with_cheaper_model_is_clean(proj):
    res, lines = run(proj, dispatch({"subagent_type": "general-purpose", "model": "haiku"}))
    assert res.stderr == "" and lines[0]["verdict"] == "ok"


def test_mutation_fork_with_opus_is_clean(proj):
    res, lines = run(proj, dispatch({"subagent_type": "fork", "model": "opus"}))
    assert res.stderr == "" and lines[0]["verdict"] == "ok"


def test_subagent_context_is_skipped_silently(proj):
    res, lines = run(proj, dispatch({"subagent_type": "general-purpose"}, agent_id="a123"))
    assert res.returncode == 0 and res.stderr == "" and lines == []


def test_mutation_same_input_main_thread_warns(proj):
    res, lines = run(proj, dispatch({"subagent_type": "general-purpose"}))
    assert "no_model_non_project_type" in res.stderr and len(lines) == 1


def test_task_tool_name_is_handled(proj):
    stdin = json.dumps({"tool_name": "Task", "tool_input": {"subagent_type": "general-purpose"}})
    res, lines = run(proj, stdin)
    assert lines[0]["tool_name"] == "Task" and lines[0]["verdict"] == "warn"


def test_mutation_other_tool_name_is_ignored(proj):
    stdin = json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls"}})
    res, lines = run(proj, stdin)
    assert res.returncode == 0 and lines == []


@pytest.mark.parametrize("stdin", ["", "not json", "[1,2]", '{"tool_name":"Agent"}',
                                   '{"tool_name":"Agent","tool_input":"str"}'])
def test_malformed_input_allows_and_logs(proj, stdin):
    res, lines = run(proj, stdin)
    assert res.returncode == 0
    assert len(lines) == 1 and lines[0]["verdict"] == "malformed"
    assert lines[0]["findings"] == ["malformed_input"]


def test_mutation_wellformed_input_is_not_malformed(proj):
    res, lines = run(proj, dispatch({"subagent_type": "explorer"}))
    assert lines[0]["verdict"] != "malformed"


def test_unhashable_subagent_type_does_not_crash(proj):
    res, lines = run(proj, dispatch({"subagent_type": ["x"]}))
    assert res.returncode == 0 and lines[0]["verdict"] == "warn"


def test_audit_line_carries_hook_sha(proj):
    res, lines = run(proj, dispatch({"subagent_type": "general-purpose"}))
    assert lines[0]["hook_sha"] == hashlib.sha256(HOOK.read_bytes()).hexdigest()


def test_mutation_modified_hook_changes_sha(proj, tmp_path):
    copy = tmp_path / "hook_copy.py"
    copy.write_text(HOOK.read_text() + "\n# mutation\n")
    log = proj / "logs" / "agent_dispatch_audit.jsonl"
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(proj), "AGENT_DISPATCH_AUDIT_LOG": str(log)}
    subprocess.run([sys.executable, str(copy)], input=dispatch({}), text=True,
                   capture_output=True, env=env, check=True)
    assert json.loads(log.read_text().splitlines()[0])["hook_sha"] != hashlib.sha256(HOOK.read_bytes()).hexdigest()


def test_unwritable_log_still_allows(proj, tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(proj),
           "AGENT_DISPATCH_AUDIT_LOG": str(blocker / "sub" / "a.jsonl")}
    res = subprocess.run([sys.executable, str(HOOK)], input=dispatch({}), text=True,
                         capture_output=True, env=env, check=False)
    assert res.returncode == 0 and "internal error allowed" in res.stderr


def test_shipped_project_types_all_declare_models():
    """The three shipped types must be recognised as project types by the hook."""
    sys.path.insert(0, str(HOOK.parent))
    try:
        import check_agent_dispatch as mod
    finally:
        sys.path.pop(0)
    os.environ["CLAUDE_PROJECT_DIR"] = str(ROOT)
    try:
        types = mod.project_types()
    finally:
        del os.environ["CLAUDE_PROJECT_DIR"]
    assert types == {"explorer": "haiku", "runner": "sonnet", "clerk": "haiku"}
