"""Regression test for KB-WM-5: agent_log.sh's session file must be sharded

per-AGENT_ID, the same way AGENT_LOG_FILE already is, instead of one
".current_session" shared by every concurrent agent.

Before the fix: two concurrent agents (different AGENT_ID) sourced
agent_log.sh in the same LOG_DIR and both read/wrote the SAME
"logs/.current_session" file -- whichever one wrote last "won" the session id
for both, and agent_session_end() from either agent deleted it for both.

This test drives the real scripts/utils/agent_log.sh via `bash -c` (it is
meant to be SOURCED, not executed, and asserts set -euo pipefail compatible
behavior under sourcing) with two different AGENT_ID values sharing one tmp
LOG_DIR, and checks:

  1. starting a session for agent A and agent B produces two DISTINCT session
     files, each holding only that agent's own session id;
  2. ending A's session removes ONLY A's file -- B's file and its content are
     untouched;
  3. a log line B writes after A's session end still carries B's own session
     id (not clobbered by A's end, not merged with A's).

Uses ORCHESTRATOR_PATHS_LOG_DIR (the same override scripts/lib/env.sh honors,
and the same one scripts/utils/tests/test_agent_log_merge_format.sh uses) to
redirect LOG_DIR to a pytest tmp_path -- this must NEVER touch the real
/workspace/logs or /mnt/raid0/llm/epyc-root/logs.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENT_LOG_SH = REPO_ROOT / "scripts" / "utils" / "agent_log.sh"


def _run_bash(script: str, log_dir: Path, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    env = {
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "HOME": str(log_dir),  # harmless; keeps any $HOME-reading tool from touching the real home
        "ORCHESTRATOR_PATHS_LOG_DIR": str(log_dir),
    }
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", "-c", script],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


def _session_files(log_dir: Path) -> list[Path]:
    return sorted(log_dir.glob(".current_session*"))


@pytest.fixture()
def log_dir(tmp_path: Path) -> Path:
    d = tmp_path / "logs"
    d.mkdir()
    return d


def test_agent_log_sh_syntax_ok():
    result = subprocess.run(["bash", "-n", str(AGENT_LOG_SH)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_two_agents_get_distinct_session_files(log_dir: Path):
    result = _run_bash(
        f'set -euo pipefail; AGENT_ID=mainA source "{AGENT_LOG_SH}"; echo "SID_A=$AGENT_SESSION_ID"',
        log_dir,
    )
    assert result.returncode == 0, result.stderr
    sid_a = _extract(result.stdout, "SID_A")

    result = _run_bash(
        f'set -euo pipefail; AGENT_ID=mainB source "{AGENT_LOG_SH}"; echo "SID_B=$AGENT_SESSION_ID"',
        log_dir,
    )
    assert result.returncode == 0, result.stderr
    sid_b = _extract(result.stdout, "SID_B")

    assert sid_a != sid_b

    files = _session_files(log_dir)
    names = {f.name for f in files}
    assert ".current_session.mainA" in names
    assert ".current_session.mainB" in names
    # No shared legacy file was written by either agent.
    assert ".current_session" not in names

    assert (log_dir / ".current_session.mainA").read_text().strip() == sid_a
    assert (log_dir / ".current_session.mainB").read_text().strip() == sid_b


def test_agent_end_removes_only_its_own_file(log_dir: Path):
    # Both agents start a session first (persists their session files).
    _run_bash(f'set -euo pipefail; AGENT_ID=mainA source "{AGENT_LOG_SH}"', log_dir)
    r_b = _run_bash(
        f'set -euo pipefail; AGENT_ID=mainB source "{AGENT_LOG_SH}"; echo "SID_B=$AGENT_SESSION_ID"',
        log_dir,
    )
    sid_b_before = _extract(r_b.stdout, "SID_B")
    b_file = log_dir / ".current_session.mainB"
    b_content_before = b_file.read_text()

    # Agent A ends its session.
    result = _run_bash(
        f'set -euo pipefail; AGENT_ID=mainA source "{AGENT_LOG_SH}"; agent_session_end "done"',
        log_dir,
    )
    assert result.returncode == 0, result.stderr

    a_file = log_dir / ".current_session.mainA"
    assert not a_file.exists(), "agent A's own session file must be removed by agent_session_end"
    assert b_file.exists(), "agent B's session file must survive agent A's session_end"
    assert b_file.read_text() == b_content_before, "agent B's session file content must be untouched"

    # A subsequent log line written by B still carries B's own (unchanged) session id.
    r_b2 = _run_bash(
        f'set -euo pipefail; AGENT_ID=mainB source "{AGENT_LOG_SH}"; '
        f'agent_task_start "post-A-end task" "verify B unaffected" >/dev/null; '
        f'echo "SID_B2=$AGENT_SESSION_ID"',
        log_dir,
    )
    assert r_b2.returncode == 0, r_b2.stderr
    sid_b_after = _extract(r_b2.stdout, "SID_B2")
    assert sid_b_after == sid_b_before

    shard_log = log_dir / "agent_audit-mainB.log"
    assert shard_log.exists()
    lines = [line for line in shard_log.read_text().splitlines() if line.strip()]
    assert lines, "expected at least one log line from agent B"
    last_entry = json.loads(lines[-1])
    assert last_entry["session"] == sid_b_before
    assert last_entry["cat"] == "TASK_START"

    # Agent A's audit shard must be untouched by B's post-end activity.
    a_shard_log = log_dir / "agent_audit-mainA.log"
    assert a_shard_log.exists()


def test_unattributed_fallback_shard_used_when_agent_id_unset(log_dir: Path):
    result = _run_bash(
        f'set -euo pipefail; unset AGENT_ID; source "{AGENT_LOG_SH}"; echo "SID=$AGENT_SESSION_ID"',
        log_dir,
    )
    assert result.returncode == 0, result.stderr
    assert (log_dir / ".current_session.unattributed").exists()


def _extract(stdout: str, key: str) -> str:
    for line in stdout.splitlines():
        if line.startswith(f"{key}="):
            return line[len(key) + 1 :]
    raise AssertionError(f"{key}= not found in stdout:\n{stdout}")
