"""Regression tests for the local-reference guard on governance documents."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
GUARD = REPO_ROOT / "scripts" / "hooks" / "agents_reference_guard.sh"


def _run_guard(
    project_dir: Path,
    file_path: Path,
    *,
    tool_name: str = "Edit",
    content: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Invoke the hook exactly as its Edit/Write integration does."""
    tool_input: dict[str, str] = {"file_path": str(file_path)}
    if content is not None:
        tool_input["content"] = content
    return subprocess.run(
        ["bash", str(GUARD)],
        input=json.dumps({"tool_name": tool_name, "tool_input": tool_input}),
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


def _init_git_repo(path: Path) -> None:
    path.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)


def test_checks_new_claude_md_write_with_mismatched_project_dir(tmp_path: Path) -> None:
    """New governance writes resolve references from the edited file's repo."""
    launch_repo = tmp_path / "launch-repo"
    edited_repo = tmp_path / "edited-repo"
    _init_git_repo(launch_repo)
    _init_git_repo(edited_repo)
    (launch_repo / "only-in-launch-repo.md").write_text("launch\n", encoding="utf-8")
    (edited_repo / "repo-root-reference.md").write_text("edited repo\n", encoding="utf-8")
    claude_file = edited_repo / "CLAUDE.md"  # Write target intentionally does not exist yet.

    result = _run_guard(
        launch_repo,
        claude_file,
        tool_name="Write",
        content="Read `repo-root-reference.md`.\n",
    )

    assert result.returncode == 0, result.stderr

    result = _run_guard(
        launch_repo,
        claude_file,
        tool_name="Write",
        content="Read `missing-governance.md`.\n",
    )

    assert result.returncode == 2
    assert "missing-governance.md" in result.stderr

    result = _run_guard(
        launch_repo,
        claude_file,
        tool_name="Write",
        content="Read `only-in-launch-repo.md`.\n",
    )

    assert result.returncode == 2
    assert "only-in-launch-repo.md" in result.stderr


def test_resolves_references_in_edited_files_own_repo_with_mismatched_project_dir(
    tmp_path: Path,
) -> None:
    """The harness project root may differ from the edited file's worktree."""
    launch_repo = tmp_path / "launch-repo"
    edited_repo = tmp_path / "edited-repo"
    _init_git_repo(launch_repo)
    _init_git_repo(edited_repo)

    (launch_repo / "only-in-launch-repo.md").write_text("launch\n", encoding="utf-8")
    (edited_repo / "repo-root-reference.md").write_text("edited repo\n", encoding="utf-8")
    agent_file = edited_repo / "agents" / "author.md"
    agent_file.parent.mkdir()
    agent_file.write_text("Read `repo-root-reference.md`.\n", encoding="utf-8")

    result = _run_guard(launch_repo, agent_file)

    assert result.returncode == 0, result.stderr

    # A file present only in the fixed harness root must not make an unresolved
    # reference in the edited worktree pass.
    agent_file.write_text("Read `only-in-launch-repo.md`.\n", encoding="utf-8")
    result = _run_guard(launch_repo, agent_file)

    assert result.returncode == 2
    assert "only-in-launch-repo.md" in result.stderr
