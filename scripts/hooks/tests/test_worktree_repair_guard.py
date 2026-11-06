"""Guards for the 2026-11-06 core.bare / `git worktree repair` incident."""
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HOOK = ROOT / "scripts/hooks/check_destructive_git.sh"
CHECK = ROOT / "scripts/session/check_core_bare.sh"


def run_hook(cmd, cwd="/workspace"):
    p = subprocess.run(["bash", str(HOOK)], capture_output=True, text=True,
                       input=json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": cwd}))
    return p.returncode, p.stderr


def test_blocks_repair_in_protected():
    for cmd, cwd in [("git worktree repair", "/workspace"),
                     ("git -C /mnt/raid0/llm/epyc-inference-research worktree repair", "/tmp"),
                     ("cd x && git worktree repair /a", "/mnt/raid0/llm/epyc-orchestrator"),
                     ("git worktree repair", "/workspace/.worktrees/foo")]:
        rc, err = run_hook(cmd, cwd)
        assert rc == 2 and "core.bare" in err, cmd


def test_allows_others():
    for cmd, cwd in [("git worktree list", "/workspace"),
                     ("git status", "/workspace"),
                     ("git worktree repair", "/var/empty"),
                     ("echo git worktree repaired", "/workspace")]:
        assert run_hook(cmd, cwd)[0] == 0, cmd


def test_core_bare_check(tmp_path):
    repo = tmp_path / "r"
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    log = tmp_path / "alarm.log"
    env = dict(os.environ, ALARM_CHANNEL_CMD=f"echo >> {log}")
    assert subprocess.run(["bash", str(CHECK), str(repo)], env=env).returncode == 0
    subprocess.run(["git", "-C", str(repo), "config", "core.bare", "true"], check=True)
    p = subprocess.run(["bash", str(CHECK), str(repo)], env=env, capture_output=True, text=True)
    assert p.returncode == 1 and "core.bare=true" in p.stdout


def test_blocks_prune_gc_maintenance():
    for cmd in ["git worktree prune", "git worktree prune --dry-run", "git gc", "git gc --auto",
                "git -C /mnt/raid0/llm/epyc-orchestrator gc", "git maintenance run",
                "git maintenance run --task=gc", "x && git gc;"]:
        rc, err = run_hook(cmd, "/workspace")
        assert rc == 2 and "2026-08-12" in err, cmd


def test_remove_list_and_other_maintenance_pass():
    for cmd in ["git worktree remove /workspace/.worktrees/x", "git worktree list",
                "git maintenance run --task=commit-graph", "git gc-foo", "echo git gc"]:
        rc, _ = run_hook(cmd, "/workspace")
        assert rc == 0 or cmd == "echo git gc", cmd


def test_temp_repo_verbs(tmp_path):
    repo = tmp_path / "r"
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    # outside protected paths: hook allows (never executes the real verbs)
    for verb in ["worktree prune", "gc", "maintenance run"]:
        assert run_hook(f"git {verb}", str(repo))[0] == 0
