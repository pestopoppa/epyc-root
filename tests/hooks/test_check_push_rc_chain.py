"""AK audit C6: refuse `push | grep PUSH && git worktree remove`; never refuse the safe shapes."""
import json
import os
import subprocess
import sys

import pytest

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts", "hooks", "check_push_rc_chain.py")
sys.path.insert(0, os.path.dirname(HOOK))
import check_push_rc_chain as c  # noqa: E402

SP = "python3 /workspace/scripts/coordination/serialized_push.py --agent x --repo . --push"


@pytest.mark.parametrize("cmd", [
    f"{SP} | grep PUSH && git -C /workspace worktree remove /mnt/raid0/llm/worktrees/a",
    f"{SP} 2>&1 | tail -3; git worktree remove wt",
    f"cd wt && {SP} | grep -q 'PUSH VERIFIED' && cd .. && git branch -D lane-x",
    "git push origin HEAD | tee log && git worktree remove wt",
    f"{SP} | grep PUSH\ngit worktree remove wt",
])
def test_masked_push_then_cleanup_is_refused(cmd):
    assert "BLOCKED" in c.verdict(cmd)


@pytest.mark.parametrize("cmd", [
    f"{SP} && git -C /workspace worktree remove wt",              # branches on the real rc
    f"{SP} | grep PUSH",                                          # piped, but nothing destroyed
    f"set -o pipefail; {SP} | grep PUSH && git worktree remove wt",
    f"{SP} || echo failed; git status",
    f"{SP} || exit 1; git worktree remove wt",                     # || is not a pipe
    "git log | grep push && git worktree remove wt",              # no push command
    "git worktree remove wt && git push origin main | tail -1",   # cleanup precedes the push
    "git pushd-like-thing | grep x && git worktree list",
    "git branch -a | grep push && git worktree remove wt",
    "",
])
def test_safe_shapes_pass(cmd):
    assert c.verdict(cmd) is None


def run(payload):
    return subprocess.run([sys.executable, HOOK], input=payload, capture_output=True, text=True)


def test_process_protocol():
    bad = json.dumps({"tool_name": "Bash", "tool_input": {"command": f"{SP} | grep PUSH && git worktree remove wt"}})
    r = run(bad)
    assert r.returncode == 2 and len(r.stderr.strip().splitlines()) == 1
    assert run(json.dumps({"tool_name": "Bash", "tool_input": {"command": SP}})).returncode == 0
    assert run("not json").returncode == 0
    assert run(json.dumps({"tool_name": "Edit", "tool_input": {"command": "x"}})).returncode == 0
