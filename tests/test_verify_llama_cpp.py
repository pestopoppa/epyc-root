from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/session/verify_llama_cpp.sh"


def run_function(command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "-c", f"source {SCRIPT!s}; {command}"],
        check=False,
        capture_output=True,
        text=True,
    )


def init_repo(path: Path) -> str:
    subprocess.run(["git", "init", "-q", "-b", "production-test", path], check=True)
    subprocess.run(["git", "-C", path, "config", "user.email", "test@example.invalid"], check=True)
    subprocess.run(["git", "-C", path, "config", "user.name", "Test"], check=True)
    (path / "tracked").write_text("clean\n", encoding="ascii")
    subprocess.run(["git", "-C", path, "add", "tracked"], check=True)
    subprocess.run(["git", "-C", path, "commit", "-q", "-m", "fixture"], check=True)
    return subprocess.run(
        ["git", "-C", path, "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def test_commit_and_tracked_state_fail_closed(tmp_path: Path) -> None:
    head = init_repo(tmp_path)
    assert run_function(
        f"verify_branch {tmp_path} production-test fixture"
    ).returncode == 0
    assert run_function(
        f"verify_branch {tmp_path} production-wrong fixture"
    ).returncode == 1
    assert run_function(f"verify_commit {tmp_path} {head} fixture").returncode == 0
    assert run_function(f"verify_commit {tmp_path} {'0' * 40} fixture").returncode == 1
    assert run_function(f"verify_tracked_state {tmp_path} fixture").returncode == 0

    (tmp_path / "tracked").write_text("dirty\n", encoding="ascii")
    assert run_function(f"verify_tracked_state {tmp_path} fixture").returncode == 1


def test_server_identity_checks_hash_and_version(tmp_path: Path) -> None:
    server = tmp_path / "llama-server"
    server.write_text("#!/bin/bash\nprintf '%s\\n' 'version: 42 (abcdef123)'\n", encoding="ascii")
    server.chmod(0o755)
    digest = hashlib.sha256(server.read_bytes()).hexdigest()

    good = run_function(
        f"check_server_identity {server} {digest} 'version: 42 (abcdef123)' fixture"
    )
    assert good.returncode == 0, good.stdout + good.stderr
    assert run_function(
        f"check_server_identity {server} {'0' * 64} 'version: 42 (abcdef123)' fixture"
    ).returncode == 1
    assert run_function(
        f"check_server_identity {server} {digest} 'version: 43 (abcdef123)' fixture"
    ).returncode == 1
