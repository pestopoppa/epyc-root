"""guard_production_kernel.py: production cutover is operator-only; champion work and reads pass (2026-11-18)."""
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / "guard_production_kernel.py"
sys.path.insert(0, str(HOOK.parent))
import guard_production_kernel as g  # noqa: E402

PROD = "/mnt/raid0/llm/kernels/production/cpu"
FROZEN = "/mnt/raid0/llm/kernels/builds/cpu-20260922-ffc1bac82/bin/llama-server"
LLAMA = "/mnt/raid0/llm/llama.cpp"


@pytest.fixture(autouse=True)
def ratify_path(tmp_path, monkeypatch):
    p = tmp_path / "operator-ratify" / "production-kernel.json"
    monkeypatch.setattr(g, "RATIFY", str(p))
    return p


def bash(cmd, branch="llama.cpp-experimental", cwd="/workspace"):
    return g.verdict({"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": cwd}, branch_of=lambda t: branch)


@pytest.mark.parametrize("cmd", [
    f"ln -sfn /x {PROD}", f"rm -rf {PROD}", f"mv /tmp/a {PROD}/bin", f"chmod +w {FROZEN}", f"echo x > {FROZEN}",
    f"cp a {PROD}/lib/x.so", f"sudo rsync -a b/ {PROD}/",
    f"git -C {LLAMA} push origin production-consolidated-v11", f"git -C {LLAMA} branch -f production-consolidated-v10 HEAD",
    "git -C /mnt/raid0/llm/whisper.cpp reset --hard production-speech-v1",
])
def test_denied(cmd):
    assert bash(cmd) and "FROZEN" in bash(cmd)


def test_commit_on_checked_out_production_branch_denied():
    assert bash(f"cd {LLAMA} && git commit -m x", branch="production-consolidated-v10")
    assert bash("git commit -am x", branch="production-speech-v1", cwd="/mnt/raid0/llm/qwentts.cpp")


@pytest.mark.parametrize("cmd", [
    f"ls -la {PROD}", f"readlink -f {PROD}", f"stat {FROZEN}", "bash scripts/session/verify_llama_cpp.sh",
    "bash scripts/session/verify_kernel_store.sh", f"cat {PROD}/MANIFEST.json",
    "rm -rf /mnt/raid0/llm/kernels/builds/cpu-20261118-c14champ", "cp a /mnt/raid0/llm/kernels/builds/c15/x",
    f"git -C {LLAMA} commit -m champion", f"git -C {LLAMA} push origin llama.cpp-experimental",
    "git -C /workspace commit -m x",
])
def test_allowed(cmd):
    assert bash(cmd) is None


def test_write_edit():
    assert g.verdict({"tool_name": "Write", "tool_input": {"file_path": PROD + "/x"}})
    assert g.verdict({"tool_name": "Edit", "tool_input": {"file_path": FROZEN}})
    assert g.verdict({"tool_name": "Write", "tool_input": {"file_path": "/workspace/x.md"}}) is None


def _write(p, **kw):
    p.parent.mkdir(parents=True, exist_ok=True)
    d = {"by": "operator", "at": dt.datetime.now(dt.timezone.utc).isoformat(), "reason": "v11 cutover", "version": "v11"}
    d.update(kw)
    p.write_text(json.dumps(d))


def test_ratification_lifts_only_when_complete_and_fresh(ratify_path):
    cmd = f"ln -sfn /x {PROD}"
    _write(ratify_path, version="")
    assert bash(cmd)
    _write(ratify_path, at=(dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=25)).isoformat())
    assert bash(cmd)
    _write(ratify_path)
    assert bash(cmd) is None


def test_cli_exit_codes(tmp_path):
    env = dict(os.environ, ROWFLOW_FLAGS=str(tmp_path))
    run = lambda p: subprocess.run([sys.executable, str(HOOK)], input=json.dumps(p), text=True, capture_output=True, env=env)
    assert run({"tool_name": "Bash", "tool_input": {"command": f"rm -rf {PROD}"}}).returncode == 2
    assert run({"tool_name": "Bash", "tool_input": {"command": f"ls {PROD}"}}).returncode == 0
    assert subprocess.run([sys.executable, str(HOOK)], input="garbage", text=True, capture_output=True, env=env).returncode == 0
