"""Regression tests for the local-reference guard on governance documents."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
GUARD = REPO_ROOT / "scripts" / "hooks" / "agents_reference_guard.sh"


def _run_guard(project_dir: Path, file_path: Path) -> subprocess.CompletedProcess[str]:
    """Invoke the hook exactly as its Edit/Write integration does."""
    return subprocess.run(
        ["bash", str(GUARD)],
        input=json.dumps({"tool_name": "Edit", "tool_input": {"file_path": str(file_path)}}),
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(project_dir)},
        check=False,
    )


def test_allows_the_compliant_coordinator_agent_role_file() -> None:
    """A compliant production role file must never be blocked by its own guard."""
    result = _run_guard(REPO_ROOT, Path("agents/coordinator-agent.md"))

    assert result.returncode == 0, result.stderr


def test_resolves_bare_session_bus_protocol_and_token_references(tmp_path: Path) -> None:
    """Nested session-bus docs are explicit standard resolution roots."""
    agent_file = tmp_path / "agents" / "coordinator-agent.md"
    protocol = tmp_path / "coordination" / "session-bus" / "BUS_PROTOCOL.md"
    tokens = tmp_path / "coordination" / "session-bus" / "tokens" / "token-queue.md"
    agent_file.parent.mkdir(parents=True)
    protocol.parent.mkdir(parents=True)
    tokens.parent.mkdir(parents=True)
    agent_file.write_text(
        "Read `BUS_PROTOCOL.md` and `tokens/token-queue.md` before acting.\n",
        encoding="utf-8",
    )
    protocol.write_text("# protocol\n", encoding="utf-8")
    tokens.write_text("# tokens\n", encoding="utf-8")

    result = _run_guard(tmp_path, agent_file)

    assert result.returncode == 0, result.stderr


def test_still_blocks_missing_nested_session_bus_reference(tmp_path: Path) -> None:
    """The explicit fallback does not turn unresolved references into allows."""
    agent_file = tmp_path / "agents" / "coordinator-agent.md"
    agent_file.parent.mkdir(parents=True)
    agent_file.write_text("Read `tokens/missing.md` before acting.\n", encoding="utf-8")

    result = _run_guard(tmp_path, agent_file)

    assert result.returncode == 2
    assert "BLOCKED: unresolved local markdown references" in result.stderr
    assert "tokens/missing.md" in result.stderr


def test_resolves_lane_ahead_reference_in_edited_files_own_git_root(tmp_path: Path) -> None:
    env_lane = tmp_path / "env-lane"
    edit_lane = tmp_path / "edit-lane"
    for lane in (env_lane, edit_lane):
        lane.mkdir()
        subprocess.run(["git", "init", "--quiet", str(lane)], check=True)
    agent = edit_lane / "agents" / "lane.md"
    agent.parent.mkdir()
    (edit_lane / "docs").mkdir()
    (edit_lane / "docs" / "ahead.md").write_text("# Lane ahead\n", encoding="utf-8")
    agent.write_text("Read `docs/ahead.md`.\n", encoding="utf-8")
    result = _run_guard(env_lane, agent)
    assert result.returncode == 0, result.stderr


def test_cannot_borrow_missing_reference_from_environment_git_lane(tmp_path: Path) -> None:
    env_lane = tmp_path / "env-lane"
    edit_lane = tmp_path / "edit-lane"
    for lane in (env_lane, edit_lane):
        lane.mkdir()
        subprocess.run(["git", "init", "--quiet", str(lane)], check=True)
    (env_lane / "docs").mkdir()
    (env_lane / "docs" / "env-only.md").write_text("# Other lane\n", encoding="utf-8")
    agent = edit_lane / "agents" / "lane.md"
    agent.parent.mkdir()
    agent.write_text("Read `docs/env-only.md`.\n", encoding="utf-8")
    result = _run_guard(env_lane, agent)
    assert result.returncode == 2
    assert "docs/env-only.md" in result.stderr
