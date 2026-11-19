"""AUD-10: the re-landed single-branch `git clean` guard (scan + PreToolUse hook).

Each blocking case is paired with a mutation of the TREE (same command, nothing
untracked -> allow) and the suite varies the shell FRAMING around the clean, which is
the dimension the reverted 03e17111 suite never mutated (54889ea33).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parents[1]
REPO_ROOT = HOOKS.parents[1]
sys.path.insert(0, str(HOOKS))
import git_clean_scan as scan  # noqa: E402

HOOK = HOOKS / "check_git_clean.sh"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "tree"
    r.mkdir()
    _git(r, "init", "-q")
    (r / ".gitignore").write_text("*.log\n")
    _git(r, "add", ".gitignore")
    _git(r, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "base")
    return r


def _dirty(repo: Path) -> None:
    (repo / "work.txt").write_text("someone's in-flight file\n")
    (repo / "sub").mkdir(exist_ok=True)
    (repo / "sub" / "notes.md").write_text("x\n")


def _hook(command: str, cwd: Path) -> subprocess.CompletedProcess:
    payload = json.dumps({"tool_name": "Bash", "cwd": str(cwd),
                          "tool_input": {"command": command}})
    return subprocess.run(["bash", str(HOOK)], input=payload, capture_output=True, text=True)


def test_forced_clean_with_untracked_files_blocks_and_clean_tree_passes(repo: Path) -> None:
    assert scan.classify("git clean -fd", str(repo)) == "allow"      # nothing to remove
    _dirty(repo)
    v = scan.classify("git clean -fd", str(repo))
    assert v.startswith("block:clean-untracked:"), v
    assert ":2:" in v and "work.txt" in v
    # the scanner only ever dry-runs: the files are still there
    assert (repo / "work.txt").exists() and (repo / "sub" / "notes.md").exists()


@pytest.mark.parametrize("framing", [
    "cd {r}; git clean -fd",
    "cd {r} && git clean -fd",
    "echo cleanup; cd {r}; git clean -f",
    "(cd {r} && git clean -f)",
    "for i in 1; do cd {r}; git clean -f; done",
    "git -C {r} clean -f",
    "sudo -n git -C {r} clean -f",
    "env FOO=1 git -C {r} clean -fdx",
    "timeout 30 git -C {r} clean -f",
    "bash -c 'cd {r} && git clean -fd'",
    "sh -c \"git -C {r} clean -f\"",
    "eval git -C {r} clean -f",
    "echo $(git -C {r} clean -f)",
    "git -C {r} clean -f | tee /dev/null",
    "git -c clean.requireForce=false -C {r} clean -d",
])
def test_shell_framing_cannot_hide_the_clean(repo: Path, framing: str) -> None:
    _dirty(repo)
    cmd = framing.format(r=repo)
    v = scan.classify(cmd, "/")
    assert v.startswith("block:clean-untracked:"), (cmd, v)


@pytest.mark.parametrize("command", [
    "git clean -n -fd",
    "git clean --dry-run -f",
    "git clean -nfd",
    "git clean -d",                       # requireForce default: git refuses on its own
    "git clean -i",
    "git clean -fd -- does-not-exist",
    "git clean -f -e work.txt",           # no -d: sub/ stays, work.txt excluded
    "echo 'git clean -fd'",
    "grep -n 'git clean -f' README.md",
    "git status --short",
    "REVERT_VERIFIED=1 git clean -fd",
    "cat <<'EOF'\ngit clean -fd\nEOF",
])
def test_harmless_or_overridden_forms_pass(repo: Path, command: str) -> None:
    _dirty(repo)
    assert scan.classify(command, str(repo)) == "allow", command


def test_ignored_files_count_with_x_and_X(repo: Path) -> None:
    (repo / "run.log").write_text("ignored but real\n")
    assert scan.classify("git clean -f", str(repo)) == "allow"        # -f alone keeps ignored
    assert scan.classify("git clean -fX", str(repo)).startswith("block:clean-untracked:")
    assert scan.classify("git clean -fx", str(repo)).startswith("block:clean-untracked:")


def test_unresolvable_tree_fails_closed_only_when_forcing() -> None:
    assert scan.classify("cd $SOMEWHERE; git clean -f", "/").startswith("block:clean-unresolvable:")
    assert scan.classify("cd $SOMEWHERE; git clean -n -f", "/") == "allow"


def test_override_is_per_command_not_per_line(repo: Path) -> None:
    _dirty(repo)
    v = scan.classify(f"REVERT_VERIFIED=1 true; git -C {repo} clean -f", "/")
    assert v.startswith("block:clean-untracked:"), v


def test_hook_end_to_end_blocks_then_passes_same_command(repo: Path) -> None:
    _dirty(repo)
    r = _hook("git clean -fd", repo)
    assert r.returncode == 2, r.stdout + r.stderr
    assert "would DELETE 2 untracked" in r.stderr and "REVERT_VERIFIED=1" in r.stderr
    assert (repo / "work.txt").exists()
    (repo / "work.txt").unlink()
    (repo / "sub" / "notes.md").unlink()
    (repo / "sub").rmdir()
    r = _hook("git clean -fd", repo)
    assert r.returncode == 0, r.stdout + r.stderr


def test_hook_ignores_other_tools_and_empty_commands(repo: Path) -> None:
    _dirty(repo)
    payload = json.dumps({"tool_name": "Write", "cwd": str(repo),
                          "tool_input": {"command": "git clean -fd"}})
    r = subprocess.run(["bash", str(HOOK)], input=payload, capture_output=True, text=True)
    assert r.returncode == 0
    assert _hook("", repo).returncode == 0


def test_registered_as_a_bash_pretooluse_hook() -> None:
    settings = json.loads((REPO_ROOT / ".claude" / "settings.json").read_text())
    cmds = [h["command"] for m in settings["hooks"]["PreToolUse"] if m.get("matcher") == "Bash"
            for h in m["hooks"]]
    assert any("check_git_clean.sh" in c for c in cmds), cmds
