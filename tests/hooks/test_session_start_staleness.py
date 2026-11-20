"""AK audit C5: SessionStart staleness line; silent unless > threshold; never fails a start."""
import json
import os
import subprocess
import sys

import pytest

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts", "hooks", "session_start_staleness.py")


def git(cwd, *a):
    subprocess.run(["git", "-C", str(cwd), *a], check=True, capture_output=True,
                   env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
                        "GIT_COMMITTER_EMAIL": "t@t", "EPYC_SKIP_HOOKS": "1"})


@pytest.fixture()
def repo(tmp_path):
    r = tmp_path / "r"
    r.mkdir()
    git(r, "init", "-q", "-b", "main")
    git(r, "config", "core.hooksPath", "/dev/null")
    git(r, "commit", "-q", "--allow-empty", "-m", "base")
    git(r, "branch", "old")
    for i in range(5):
        git(r, "commit", "-q", "--allow-empty", "-m", f"c{i}")
    git(r, "update-ref", "refs/remotes/origin/main", "HEAD")
    git(r, "checkout", "-q", "old")
    return r


def run(cwd, threshold=None, stdin=None):
    env = dict(os.environ)
    env.pop("CLAUDE_PROJECT_DIR", None)
    if threshold is not None:
        env["EPYC_STALE_THRESHOLD"] = str(threshold)
    payload = stdin if stdin is not None else json.dumps({"hook_event_name": "SessionStart", "cwd": str(cwd)})
    return subprocess.run([sys.executable, HOOK], input=payload, capture_output=True, text=True, env=env, cwd=str(cwd))


def test_behind_more_than_threshold_emits_one_notice(repo):
    r = run(repo, threshold=3)
    assert r.returncode == 0
    ctx = json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "5 commits behind origin/main" in ctx


def test_at_or_under_threshold_is_silent(repo):
    for t in (5, 50, None):
        r = run(repo, threshold=t)
        assert r.returncode == 0 and r.stdout == ""


def test_no_origin_or_not_a_repo_or_bad_input_is_silent(tmp_path, repo):
    git(repo, "update-ref", "-d", "refs/remotes/origin/main")
    assert run(repo, threshold=0).stdout == ""
    plain = tmp_path / "plain"
    plain.mkdir()
    r = run(plain, threshold=0)
    assert r.returncode == 0 and r.stdout == ""
    r = run(plain, threshold="junk", stdin="not json")
    assert r.returncode == 0 and r.stdout == ""
