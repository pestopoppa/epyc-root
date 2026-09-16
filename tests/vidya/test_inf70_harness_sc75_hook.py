"""VB-WIRE-2: the promoted INF-70 HARNESS-1 arm scripts really emit SC75 belief rows.

``test_inf70_serving_arm_adapter.py`` proves the writer and reader. This file proves the
PRODUCER calls them, which was the gap: the writer existed, the arm scripts never called it,
and ``ingest inf70-arms`` read zero sidecars.

No benchmark runs. The arm's capture step is factored into ``sc75_capture.sh`` (sourced by
both arm scripts), so it is exercised here in isolation against a fixture arm directory:
a synthetic ``/proc/<pid>`` tree (``SC75_PROC``), rows and a corrected-sampler coresidency file.

Pinned:
* launch.json is built from the server's /proc environ + cmdline, and the capture step emits a
  sidecar that ``cli.py ingest inf70-arms`` ingests end to end;
* a missing required launch field FAILS LOUDLY (stdout, stderr, marker file) and still returns
  0, so the arm is never aborted, and no sidecar is written;
* a capture beyond ``MAX_CAPTURE_LAG_S`` is refused the same loud, non-aborting way;
* both arm scripts source the helper, write launch.json before the arm and call the capture
  after the per-arm coresummary line (capture-after-measure), and carry no scratch-only paths.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
HARNESS = ROOT / "scripts" / "inf70" / "harness1"
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))

import cli  # noqa: E402
from adapters import inf70_serving_arm as reader  # noqa: E402
from adapters import inf70_serving_arm_capture as capture  # noqa: E402

PID = "424242"
GGUF_SHA = "b" * 64
VERSION = "version: 10125 (0db32c06e) built with cc (GCC) 14.2.0 for x86_64-linux-gnu "


def _fixture_helpers():
    spec = importlib.util.spec_from_file_location(
        "_sc75_hook_fx", HERE / "test_inf70_serving_arm_adapter.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _proc_tree(root: Path, env: dict[str, str]) -> Path:
    d = root / "proc" / PID
    d.mkdir(parents=True)
    d.joinpath("environ").write_bytes(
        b"\0".join(f"{k}={v}".encode() for k, v in env.items()) + b"\0")
    argv = ["/x/bin-h1/llama-server", "--no-webui", "-np", "1", "-c", "8192", "-t", "48",
            "--no-mmap", "-m", "/models/trunk.gguf", "-fa", "on"]
    d.joinpath("cmdline").write_bytes(b"\0".join(a.encode() for a in argv) + b"\0")
    return root / "proc"


def _bash(script: str, env: dict[str, str]) -> subprocess.CompletedProcess:
    full = dict(os.environ)
    full.update(env)
    return subprocess.run(["bash", "-c", f'set -u; . "{HARNESS}/sc75_capture.sh"; {script}'],
                          capture_output=True, text=True, env=full, timeout=60)


@pytest.fixture()
def arm(tmp_path):
    h = _fixture_helpers()
    (tmp_path / "agents" / "harness1").mkdir(parents=True)
    runs = h.make_arm(tmp_path / "agents" / "harness1")
    proc = _proc_tree(tmp_path, {"PATH": "/usr/bin", "OMP_PROC_BIND": "spread",
                                 "GGML_IQK": "1", "GGML_NOHUGEPAGE_PROCESS": "1"})
    return {"h": h, "runs": runs, "label": h.LABEL, "proc": proc, "tmp": tmp_path}


def _launch(arm, *, sha: str | None = GGUF_SHA) -> subprocess.CompletedProcess:
    env = {"SC75_PROC": str(arm["proc"])}
    if sha is not None:
        env["GGUF_SHA256"] = sha
    else:
        env["GGUF_SHA256"] = ""
    lj = arm["runs"] / "S1.launch.json"
    return _bash(
        f'sc75_launch_json "{lj}" "S1-20260916T100000Z-pid{PID}" "{PID}" "/models/nosidecar.gguf" '
        f'"{VERSION}" "taskset -c 0-95" "0-95"', env)


def _capture(arm, launch_json: Path, a0: int) -> subprocess.CompletedProcess:
    return _bash(f'sc75_capture_arm "{arm["runs"]}" "{arm["label"]}" "{launch_json}" "{a0}"', {})


def test_capture_step_emits_a_row_that_ingest_inf70_arms_ingests(arm, capsys):
    res = _launch(arm)
    assert res.returncode == 0, res.stderr
    assert "complete" in res.stdout
    launch = json.loads((arm["runs"] / "S1.launch.json").read_text())
    assert launch["gguf_sha256"] == GGUF_SHA
    assert launch["kernel_commit"] == "0db32c06e"
    # env is the SERVER's, filtered to the recipe prefixes; argv drops argv[0]
    assert launch["launch_recipe"]["env"] == {
        "GGML_IQK": "1", "GGML_NOHUGEPAGE_PROCESS": "1", "OMP_PROC_BIND": "spread"}
    assert launch["launch_recipe"]["args"][:2] == ["--no-webui", "-np"]

    # hot-server per-arm copy carries the knob-page payload
    arm_lj = arm["runs"] / f"{arm['label']}.launch.json"
    res = _bash(f'sc75_arm_launch_json "{arm["runs"]}/S1.launch.json" "{arm_lj}" '
                '"GGML_QSPLIT=0,GGML_VEC_Q8K=0"', {})
    assert res.returncode == 0, res.stdout + res.stderr
    assert json.loads(arm_lj.read_text())["launch_recipe"]["knob_page_payload"] == [
        "GGML_QSPLIT=0", "GGML_VEC_Q8K=0"]

    res = _capture(arm, arm_lj, int(time.time()) - 300)
    assert res.returncode == 0
    assert res.stdout.startswith("SC75 belief sidecar:"), res.stdout + res.stderr
    sidecar = capture.sidecar_path_for(arm["runs"], arm["label"])
    rows = reader.native_rows(sidecar)
    assert len(rows) == 1
    row = rows[0]["row"]
    assert capture.validate_row(row) == []
    assert row["label"] == arm["label"] and row["producer"] == "inf70-serving-harness1"
    assert row["extra"]["thp_knob_state"] == "set:1"
    assert row["extra"]["kernel_commit"] == "0db32c06e"
    assert row["extra"]["contention"]["contention_verdict"] == capture.VERDICT_CLEAN
    assert not (arm["runs"] / f"{arm['label']}.sc75_capture_failed").exists()

    ledger = arm["tmp"] / "ledger.jsonl"
    as_of = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rc = cli.main(["--ledger", str(ledger), "--json", "ingest", "inf70-arms",
                   "--path", str(arm["tmp"] / "agents"), "--as-of", as_of])
    assert rc == 0
    report = json.loads(capsys.readouterr().out)
    assert report["refused"] == [], report["refused"]
    assert report["rows_projected"] == 1
    assert report["frames_emitted"] == 3


def test_missing_launch_field_fails_loudly_and_never_aborts(arm):
    res = _launch(arm, sha=None)
    assert res.returncode == 0
    assert "MISSING gguf_sha256" in res.stdout
    res = _capture(arm, arm["runs"] / "S1.launch.json", int(time.time()) - 300)
    assert res.returncode == 0                      # the arm continues
    assert "SC75 CAPTURE FAILED" in res.stdout and "SC75 CAPTURE FAILED" in res.stderr
    assert "gguf_sha256" in res.stdout
    marker = arm["runs"] / f"{arm['label']}.sc75_capture_failed"
    assert marker.exists() and "gguf_sha256" in marker.read_text()
    assert not capture.sidecar_path_for(arm["runs"], arm["label"]).exists()


def test_missing_launch_json_fails_loudly(arm):
    res = _capture(arm, arm["runs"] / "nope.launch.json", int(time.time()))
    assert res.returncode == 0
    assert "launch.json not found" in res.stdout


def test_backfill_beyond_max_capture_lag_is_refused_loudly(arm):
    assert _launch(arm).returncode == 0
    rows = arm["runs"] / f"{arm['label']}.rows.jsonl"
    old = time.time() - capture.MAX_CAPTURE_LAG_S - 600
    os.utime(rows, (old, old))
    res = _capture(arm, arm["runs"] / "S1.launch.json", int(old) - 300)
    assert res.returncode == 0
    assert "SC75 CAPTURE FAILED" in res.stdout
    assert "backfill" in res.stdout
    assert not capture.sidecar_path_for(arm["runs"], arm["label"]).exists()


@pytest.mark.parametrize("script,label_var", [("arm_cold.sh", "$LABEL"), ("arm_hot.sh", "$lbl")])
def test_arm_scripts_call_the_hook_after_measuring(script, label_var):
    text = (HARNESS / script).read_text()
    lines = text.splitlines()
    assert any(re.match(r'^\. "\$H/sc75_capture\.sh"$', ln) for ln in lines)
    idx = {name: next(i for i, ln in enumerate(lines) if pat in ln) for name, pat in {
        "launch": "sc75_launch_json",
        "client": "client.py",
        "coresummary": "coresummary.sh",
        "capture": "sc75_capture_arm",
    }.items()}
    # launch identity before the measurement; capture after the client and after coresummary
    assert idx["launch"] < idx["client"] < idx["coresummary"] < idx["capture"]
    assert label_var in lines[idx["capture"]]
    # the capture line cannot abort the arm: it is wrapped in `say "$(...)"`
    assert lines[idx["capture"]].lstrip().startswith('say "')
    # no scratch-only path survives except the runs default
    scratch = [ln for ln in lines if "/mnt/raid0/llm/tmp/inf70" in ln and not ln.lstrip().startswith("#")]
    assert all("INF70_RUNS" in ln for ln in scratch), scratch
    for dep in ("client.py", "tools/cores_sampler.sh", "tools/coresummary.sh",
                "evict_targeted.sh", "sc75_capture.sh", "sc75_launch.py", "classify.py",
                "prompts.json", "tools/cpuoverlap.py", "tools/pagecache.c"):
        assert (HARNESS / dep).is_file(), dep


def test_arm_scripts_parse():
    for script in ("arm_cold.sh", "arm_hot.sh", "sc75_capture.sh", "evict_targeted.sh",
                   "evict_nodes_force.sh", "tools/cores_sampler.sh"):
        res = subprocess.run(["bash", "-n", str(HARNESS / script)], capture_output=True, text=True)
        assert res.returncode == 0, (script, res.stderr)
