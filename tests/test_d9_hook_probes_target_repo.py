"""D9 must probe the repository the commit targets, not the hook's inherited cwd.

Origin: 2026-09-05. Two independent INF-70 subagents had legitimate commits in
`/mnt/raid0/llm/llama.cpp-cpu-fusion-20260829` worktrees refused by D9, because the hook ran
`git diff` in `$CLAUDE_PROJECT_DIR` (`/workspace`) and saw a PEER's dirty
`scripts/coordination/**`. Neither agent invented an ack to get past it — correctly, since an
invented ack defeats the control. The defect refuses every llama.cpp-worktree commit for as long
as /workspace has dirty coordination files, which is most of the time.
"""
import json
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "scripts" / "hooks" / "check_d9_loop_plane.py"


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True,
                   capture_output=True, text=True)


def _run_hook(cmd, cwd):
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": str(cwd)})
    return subprocess.run([sys.executable, str(HOOK)], input=payload,
                          capture_output=True, text=True)


def _mk_repo(path, files):
    path.mkdir(parents=True, exist_ok=True)
    _git(path, "init", "-q")
    _git(path, "config", "user.email", "t@t"); _git(path, "config", "user.name", "t")
    for rel, body in files.items():
        f = path / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(body)
    _git(path, "add", "-A"); _git(path, "commit", "-qm", "init")
    return path


def test_commit_in_repo_without_loop_plane_is_allowed(tmp_path):
    """The regression: a repo with no scripts/coordination/ cannot carry a loop-plane change."""
    other = _mk_repo(tmp_path / "llama", {"ggml/src/ggml-cpu.c": "int main(){}\n"})
    (other / "ggml/src/ggml-cpu.c").write_text("int main(){return 1;}\n")
    r = _run_hook("git commit -am 'kernel change'", other)
    assert r.returncode == 0, f"D9 refused a commit in a repo with no loop plane:\n{r.stdout}"


def test_commit_touching_loop_plane_is_still_refused(tmp_path):
    """The control must still fire where the loop plane genuinely exists."""
    root = _mk_repo(tmp_path / "root", {"scripts/coordination/session_bus.py": "x = 1\n"})
    (root / "scripts/coordination/session_bus.py").write_text("x = 2\n")
    r = _run_hook("git commit -am 'touch the loop plane'", root)
    assert r.returncode != 0, "D9 failed to refuse a real loop-plane commit"
    assert "D9 REFUSED" in r.stderr        # the hook writes its refusal to stderr


def test_peer_dirt_in_another_repo_does_not_leak(tmp_path):
    """The exact measured failure: peer's dirty loop plane must not refuse OUR clean repo."""
    peer = _mk_repo(tmp_path / "peer", {"scripts/coordination/relay.py": "x = 1\n"})
    (peer / "scripts/coordination/relay.py").write_text("x = 99\n")   # peer's dirt
    mine = _mk_repo(tmp_path / "mine", {"src/kernel.c": "int a;\n"})
    (mine / "src/kernel.c").write_text("int b;\n")
    r = _run_hook("git commit -am 'my unrelated change'", mine)
    assert r.returncode == 0, f"peer dirt leaked into an unrelated repo:\n{r.stdout}"


def test_ack_still_bypasses(tmp_path):
    """The ack path is untouched by this fix."""
    root = _mk_repo(tmp_path / "root2", {"scripts/coordination/x.py": "x = 1\n"})
    (root / "scripts/coordination/x.py").write_text("x = 3\n")
    # ACK_RE anchors at line start, so the ack must be its own line in the message.
    r = _run_hook("git commit -am 'change\n\nD9-ack: operator 2026-09-05'", root)
    assert r.returncode == 0, r.stderr


def test_commit_dash_a_cannot_bypass(tmp_path):
    """`git commit -am` stages tracked files itself, so the index is empty and
    `git diff --cached` saw nothing — the commit passed D9 cleanly.
    Measured 2026-09-05 on a dirty scripts/coordination/ file."""
    root = _mk_repo(tmp_path / "root3", {"scripts/coordination/relay.py": "x = 1\n"})
    (root / "scripts/coordination/relay.py").write_text("x = 2\n")   # dirty, NOT staged
    r = _run_hook("git commit -am 'sneak past'", root)
    assert r.returncode != 0, "git commit -a bypassed D9 — the control has an unguarded path"
    assert "D9 REFUSED" in r.stderr
