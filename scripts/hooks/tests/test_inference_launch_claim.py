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


# --- AK false positive: a binary name in ARGUMENT position of a build/inspect tool ---------
def test_build_tool_targets_and_inspection_are_not_launches():
    for c in [
        "cmake --build build --target llama-server -j8",
        "cmake --build build --target=llama-server",
        "cmake --build build -t llama-server",
        "make llama-server", "ninja llama-server", "ninja -C build llama-server",
        "nohup cmake --build build --target llama-server",
        "taskset -c 0-23 cmake --build build --target llama-server",
        "numactl -N0 -m0 ninja llama-server",
        "time make llama-server -j48",
        "timeout 3000 cmake --build build -t llama-server",
        "env CC=gcc nice -n5 make llama-server",
        "region-lock run --regions q0 -- cmake --build build --target llama-server",
        "cp build/bin/llama-server /tmp/x", "nice -n5 cp build/bin/llama-server /tmp/x",
        "g++ -o build/bin/llama-server main.o",
        "strings build/bin/llama-server | grep KNOB", "time strings build/bin/llama-server",
        "ls -l build/bin/llama-server", "ldd build/bin/llama-server",
        "file build/bin/llama-server", "sha256sum build/bin/llama-server",
        "timeout 30 sha256sum build/bin/llama-server",
    ]:
        assert launch_kind(c) == "clean", c


def test_real_launches_still_detected_with_prefixes():
    for c in [
        "llama-server -m x", "/opt/b/llama-server -m x", "exec llama-server -m x",
        "nohup llama-server -m x &", "numactl -N0 llama-server -m x",
        "taskset -c 0-23 llama-server -m x", "env A=1 llama-server -m x",
        "env A=1 numactl -N0 taskset -c 1 nohup llama-server -m x",
        "timeout 600 numactl --interleave=all llama-server -m x",
        "sudo -u bob llama-server -m x",
        "make -j8 && nohup llama-server -m x",   # build, then a real launch in a later segment
        "cmake --build b --target llama-server; llama-server -m x",
    ]:
        assert launch_kind(c) == "launch", c
    assert launch_kind("region-lock run --regions q0 -- llama-server -m x") == "wrapped"


def test_exemption_is_syntactic_not_claim_based(tmp_path):
    # A held claim never turns a real launch into a non-launch, and the build form needs none.
    _occ(tmp_path, [{"pid": os.getpid(), "token": "T"}])
    assert verdict("llama-server -m x", str(tmp_path), {}, set()) == "launch:uncovered"
    assert verdict("nohup cmake --build b --target llama-server",
                   str(tmp_path), {}, set()) == "clean"
    _occ(tmp_path, [])                       # pytest pid is a hook ancestor: drop the claim
    assert _run("nohup cmake --build b --target llama-server", tmp_path) == 0
    assert _run("nohup llama-server -m x", tmp_path) == 2
