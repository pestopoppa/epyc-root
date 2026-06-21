from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "hooks" / "posttool_kb_rag_update.sh"


def _run_hook(project_dir: Path, log_path: Path, command: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    env["KB_RAG_HOOK_LOG"] = str(log_path)
    return subprocess.run(
        ["bash", str(SCRIPT)],
        input=json.dumps({"tool_input": {"command": command}}),
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )


def _wait_for(path: Path, timeout_s: float = 2.0) -> str:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if path.exists():
            return path.read_text(encoding="utf-8")
        time.sleep(0.05)
    raise AssertionError(f"timed out waiting for {path}")


def test_posttool_dispatches_head_moving_git_command_and_logs(tmp_path: Path) -> None:
    hook = tmp_path / ".claude" / "hooks" / "post_commit_kb_rag_update.sh"
    marker = tmp_path / "marker.txt"
    log_path = tmp_path / "logs" / "kb_rag_update.log"
    hook.parent.mkdir(parents=True)
    hook.write_text(
        "#!/bin/bash\n"
        "set -euo pipefail\n"
        f"echo background-ran > {marker}\n"
        "echo hook-output\n",
        encoding="utf-8",
    )
    hook.chmod(0o755)

    result = _run_hook(tmp_path, log_path, "git commit -m test")

    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""
    assert _wait_for(marker).strip() == "background-ran"
    log_text = _wait_for(log_path)
    assert "posttool dispatch: git commit -m test" in log_text
    assert "hook-output" in log_text


def test_posttool_ignores_non_head_moving_commands(tmp_path: Path) -> None:
    hook = tmp_path / ".claude" / "hooks" / "post_commit_kb_rag_update.sh"
    marker = tmp_path / "marker.txt"
    log_path = tmp_path / "logs" / "kb_rag_update.log"
    hook.parent.mkdir(parents=True)
    hook.write_text(
        "#!/bin/bash\n"
        f"echo background-ran > {marker}\n",
        encoding="utf-8",
    )
    hook.chmod(0o755)

    result = _run_hook(tmp_path, log_path, "git status --short")

    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""
    assert not marker.exists()
    assert not log_path.exists()
