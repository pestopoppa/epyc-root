"""INC-20260812-destructive-revert: the guard blocks reverts that would destroy
uncommitted work, and ONLY those.

Both directions per the fleet's standing lens: the block must fire on a dirty
target AND the compliant paths must pass — a clean-path revert, the audited
override, index-only restore, and quoted mentions of the commands (a guard must
not forbid its own documentation). Mutation direction is the dirty/clean flip on
an otherwise identical command.
"""
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from destructive_revert_scan import classify  # noqa: E402


def _repo(tmp_path):
    r = tmp_path / "r"
    r.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=r, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=r, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=r, check=True)
    (r / "f.txt").write_text("committed\n")
    subprocess.run(["git", "add", "f.txt"], cwd=r, check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=r, check=True)
    return r


def test_dirty_checkout_blocked(tmp_path):
    r = _repo(tmp_path)
    (r / "f.txt").write_text("someone's uncommitted fix\n")
    v = classify("git checkout -- f.txt", cwd=str(r))
    assert v.startswith("block:revert-dirty:"), v


def test_clean_checkout_allowed(tmp_path):
    r = _repo(tmp_path)
    assert classify("git checkout -- f.txt", cwd=str(r)) == "allow"


def test_mutation_is_the_dirty_flip(tmp_path):
    # Identical command; only the tree state differs. The verdict MUST differ —
    # a guard whose answer is constant across the mutation is decoration.
    r = _repo(tmp_path)
    cmd = "git checkout -- f.txt"
    clean = classify(cmd, cwd=str(r))
    (r / "f.txt").write_text("mutated\n")
    dirty = classify(cmd, cwd=str(r))
    assert clean == "allow" and dirty != "allow"


def test_override_token_allows(tmp_path):
    r = _repo(tmp_path)
    (r / "f.txt").write_text("mine, verified\n")
    assert classify("REVERT_VERIFIED=1 git checkout -- f.txt", cwd=str(r)) == "allow"


def test_restore_worktree_blocked_staged_allowed(tmp_path):
    r = _repo(tmp_path)
    (r / "f.txt").write_text("dirty\n")
    assert classify("git restore f.txt", cwd=str(r)).startswith("block:")
    subprocess.run(["git", "add", "f.txt"], cwd=r, check=True)
    # --staged edits the index only; the worktree content survives.
    assert classify("git restore --staged f.txt", cwd=str(r)) == "allow"


def test_reset_hard_blocked_only_when_dirty(tmp_path):
    r = _repo(tmp_path)
    assert classify("git reset --hard", cwd=str(r)) == "allow"
    (r / "f.txt").write_text("dirty\n")
    assert classify("git reset --hard", cwd=str(r)).startswith("block:repo-destructive:")


def test_clean_f_blocked_when_untracked_exist(tmp_path):
    r = _repo(tmp_path)
    assert classify("git clean -fd", cwd=str(r)) == "allow"
    (r / "orphan.md").write_text("untracked fix\n")
    assert classify("git clean -fd", cwd=str(r)).startswith("block:clean-untracked:")


def test_dash_C_repo_resolution(tmp_path):
    r = _repo(tmp_path)
    (r / "f.txt").write_text("dirty\n")
    v = classify(f"git -C {r} checkout -- f.txt", cwd=str(tmp_path))
    assert v.startswith("block:revert-dirty:"), v


def test_checkout_without_dashdash_path_form(tmp_path):
    r = _repo(tmp_path)
    (r / "f.txt").write_text("dirty\n")
    assert classify("git checkout f.txt", cwd=str(r)).startswith("block:")


def test_quoted_mention_is_documentation_not_command(tmp_path):
    r = _repo(tmp_path)
    (r / "f.txt").write_text("dirty\n")
    v = classify('echo "never run git checkout -- f.txt blind"', cwd=str(r))
    assert v == "allow"


def test_branch_switch_untouched(tmp_path):
    # A plain branch checkout is git-protected already; the guard stays out.
    r = _repo(tmp_path)
    (r / "f.txt").write_text("dirty\n")
    assert classify("git checkout main", cwd=str(r)) == "allow"


def test_hook_end_to_end(tmp_path):
    r = _repo(tmp_path)
    (r / "f.txt").write_text("dirty\n")
    hook = Path(__file__).resolve().parents[1] / "check_destructive_revert.sh"
    payload = '{"tool_input": {"command": "git checkout -- f.txt"}}'
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(r))
    p = subprocess.run(["bash", str(hook)], input=payload, text=True,
                       capture_output=True, env=env, cwd=r)
    assert p.returncode == 2 and "UNCOMMITTED" in p.stderr
    subprocess.run(["git", "checkout", "--", "f.txt"], cwd=r, check=True)
    p2 = subprocess.run(["bash", str(hook)], input=payload, text=True,
                        capture_output=True, env=env, cwd=r)
    assert p2.returncode == 0
