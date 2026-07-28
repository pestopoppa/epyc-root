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
