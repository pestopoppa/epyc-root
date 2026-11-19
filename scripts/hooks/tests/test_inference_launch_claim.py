"""REG-ENF-2: inference launch without a region claim is denied; mentions are data."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

HOOKS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HOOKS))
from inference_launch_claim_scan import launch_kind, verdict  # noqa: E402

HOOK = HOOKS / "check_inference_launch_claim.sh"


def _occ(tmp_path, entries):
    (tmp_path / "cpu_region.occupancy.json").write_text(json.dumps({"entries": entries}))


def test_launch_detection():
    assert launch_kind("llama-server -m x.gguf") == "launch"
    assert launch_kind("FOO=1 timeout 5 numactl -N0 /opt/bin/llama-bench -m x") == "launch"
    assert launch_kind("cd a && nohup llama-cli -p hi") == "launch"
    assert launch_kind("region-lock run --regions q0 -- llama-bench -m x") == "wrapped"


def test_mentions_and_info_are_data():
    for c in ["grep llama-server notes.md", 'echo "run llama-bench now"',
              "cat <<'EOF'\nllama-server -m x\nEOF", "# llama-cli later",
              "llama-server --version", "ls /mnt/raid0/llm/llama.cpp/build/bin/llama-bench",
              "git commit -m 'llama-bench fix'"]:
        assert launch_kind(c) == "clean", c


def test_claim_states(tmp_path):
    cmd = "llama-server -m x"
    assert verdict(cmd, str(tmp_path), {}, set()) == "launch:uncovered"     # no registry
    (tmp_path / "cpu_region.occupancy.json").write_text("{not json")
    assert verdict(cmd, str(tmp_path), {}, set()) == "launch:unreadable"
    _occ(tmp_path, [{"pid": os.getpid(), "token": "T", "request_tag": "tag"}])
    assert verdict(cmd, str(tmp_path), {}, set()) == "launch:uncovered"     # someone else's
    assert verdict(cmd, str(tmp_path), {}, {os.getpid()}) == "launch:covered"
    assert verdict(cmd, str(tmp_path), {"EPYC_REGION_CLAIM_TOKEN": "T"}, set()) == "launch:covered"
    assert verdict(cmd, str(tmp_path), {"EPYC_REGION_CLAIM_TAG": "tag"}, set()) == "launch:covered"
    _occ(tmp_path, [{"pid": 2**22 + 1, "token": "T"}])                      # dead pid
    assert verdict(cmd, str(tmp_path), {"EPYC_REGION_CLAIM_TOKEN": "T"}, set()) == "launch:uncovered"
    _occ(tmp_path, ["junk"])
    assert verdict(cmd, str(tmp_path), {}, set()) == "launch:unreadable"


def _run(cmd, lock_dir, **env):
    e = {**os.environ, "EPYC_REGION_LOCK_DIR": str(lock_dir), **env}
    e.pop("EPYC_REGION_CLAIM_TOKEN", None) if "EPYC_REGION_CLAIM_TOKEN" not in env else None
    return subprocess.run(["bash", str(HOOK)], input=json.dumps({"tool_input": {"command": cmd}}),
                          capture_output=True, text=True, env=e).returncode


def test_hook_exit_codes(tmp_path):
    assert _run("llama-bench -m x", tmp_path) == 2                 # no claim
    assert _run("ls -la", tmp_path) == 0                           # fail-open, non-launch
    assert _run("region-lock run --regions q0 -- llama-bench", tmp_path) == 0
    (tmp_path / "cpu_region.occupancy.json").write_text("garbage")
    assert _run("llama-server -m x", tmp_path) == 2                # unreadable -> closed
    assert _run("echo hi", tmp_path) == 0
    assert _run("llama-server -m x", tmp_path, EPYC_ALLOW_UNCLAIMED_LAUNCH="1") == 0
