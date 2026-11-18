"""Model-free controls for the prospective official EXP01 writer."""
from __future__ import annotations

import importlib.util
import json
import os
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "scripts/experiments/exp01-pilot/capture.py"
SPEC = importlib.util.spec_from_file_location("exp01_official_capture", SOURCE)
capture = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(capture)


@pytest.fixture
def packet(tmp_path, monkeypatch):
    packet = tmp_path / "packet"
    packet.mkdir()
    monkeypatch.setattr(capture, "P", packet)
    mask = set(range(100, 104))
    monkeypatch.setattr(os, "sched_getaffinity", lambda _: mask)
    items = packet / "items.jsonl"
    items.write_text("".join(json.dumps({"id": f"item-{i}"}) + "\n" for i in range(24)))
    modelset = packet / "models.env"
    modelset.write_text("# synthetic fixture\n")
    (packet / "look.py").write_text("# synthetic fixture\n")
    (packet / "SOURCE.json").write_text("{}\n")
    (packet / "fixture.grant").write_text("id=fixture regions=100-103\n")
    date = time.time()
    for key, value in dict(FILLER_ID="fixture", FILLER_CPUS="100-103", FILLER_THREADS="4",
                           FILLER_GRANTS_DIR=str(packet), FILLER_DEADLINE=str(date + 60),
                           EXP01_CONTROL_END=str(date + 30), FILLER_STOPFILE=str(packet / "STOP"),
                           MODELSET=str(modelset), IK="fixture-instrument", LAUNCHES="2",
                           PP="512", TG="128", CAP_S="30", EXP01_JOB_SOURCE=str(SOURCE)).items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("FILLER_DRYRUN", raising=False)
    monkeypatch.setattr(capture, "checked", lambda: {
        "artifacts": {"modelset": capture.artifact(modelset), "producer": capture.artifact(SOURCE),
                      "items": capture.artifact(items)},
        "trees": {"fixture-instrument": "a" * 40},
    })
    return packet


def test_official_writer_separates_modes_and_refuses_smoke_or_resource_drift(packet, monkeypatch):
    official = packet / "official"
    run = capture.begin(official, mode="official")
    assert run["mode"] == "official"
    assert run["planned"]["planned_looks"] == [2]
    (official / "results.jsonl").touch()
    capture.emit(official / "results.jsonl", {"unit": "validity", "ok": True})
    with pytest.raises(ValueError, match="resource mismatch"):
        capture.emit(official / "results.jsonl", {"unit": "speed-Q4KM-1", "kind": "speed",
                                                 "cpus": "100-103", "threads": 24})
    assert capture.terminal_official(official, 0) == 4
    terminal = json.loads((official / "TERMINAL.json").read_bytes())
    assert terminal["state"] == "partial-or-failed" and terminal["raw"]["sha256"]
    with pytest.raises(ValueError, match="fresh"):
        capture.begin(official, mode="official")
    monkeypatch.setenv("FILLER_DRYRUN", "1")
    with pytest.raises(ValueError, match="uses smoke"):
        capture.begin(packet / "false-official", mode="official")
    control = capture.begin(packet / "control")
    assert control["run_id"] != run["run_id"] and control["mode"] == "capture-control"
    with pytest.raises(ValueError, match="official source envelope"):
        capture.terminal_official(packet / "control", 0)


def test_original_schedule_look_and_all_paired_items_are_required(packet):
    out = packet / "official"
    run = capture.begin(out, mode="official")
    (out / "launches").mkdir()
    result = out / "results.jsonl"
    capture.emit(result, {"unit": "validity", "ok": True})

    def emit_native(kind, name):
        (out / "launches" / f"{name}.json").write_text("{}\n")
        if kind == "speed":
            (out / f"{name}.json").write_text("[]\n")
        capture.emit(result, {"unit": name, "kind": kind, "rc": 0, "cpus": "100-103", "threads": 4})

    for launch in range(1, 3):
        for first, second in zip(capture.ARMS[::2], capture.ARMS[1::2], strict=True):
            for arm in (first, second):
                emit_native("speed", f"speed-{arm}-{launch}")
            if launch == 2:
                capture.emit(result, {"unit": f"look-{first}-{second}", "kind": "look", "stop": "continue"})
    for item in run["planned"]["paired_item_ids"]:
        for arm in capture.ARMS[:2]:
            emit_native("quality", f"q-{arm}-{item}")
    (out / "SUMMARY.json").write_text("{}\n")
    rows = list(map(json.loads, result.read_text().splitlines()))
    assert not capture._complete_schedule(rows[:-1], run["planned"])
    assert not capture._complete_schedule(rows[:1] + rows[2:], run["planned"])
    assert capture.terminal_official(out, 0) == 0
    assert json.loads((out / "TERMINAL.json").read_bytes())["state"] == "complete-unprojected"


def test_shell_refuses_unqualified_and_official_smoke_invocations(tmp_path):
    import subprocess

    job = SOURCE.with_name("job_r3.sh")
    for args, expected in (([], "explicit EXP01 capture mode"),
                           (["--capture-official"], "separate capture-control entry point")):
        outcome = subprocess.run(["/bin/bash", str(job), *args], check=False,
                                 env={"EXP01_CAPTURE_DIR": str(tmp_path), "FILLER_DRYRUN": "1"},
                                 capture_output=True, text=True)
        assert outcome.returncode == 2 and expected in outcome.stderr
        assert not list(tmp_path.iterdir())
