import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from scripts.vidya.producers import p5_scorer_custody as custody


def window(tmp_path, *, smoke):
    grants = tmp_path / "grants"
    grants.mkdir()
    fields = "kind=rowflow-dryrun id=" + custody.ROW + " " if smoke else ""
    end = 1767226200
    grant = grants / (custody.ROW + ".grant")
    grant.write_text(fields + "regions=0-3 start=2026-01-01T00:00Z end=2026-01-01T00:10Z holds=q0\n")
    return grant, {
        "FILLER_ID": custody.ROW, "FILLER_NEEDGPU": "0", "FILLER_CPUS": "0-3",
        "FILLER_DRYRUN": "1" if smoke else "0", "FILLER_SMOKE": "1" if smoke else "0",
        "FILLER_FLAGS_DIR": str(tmp_path), "FILLER_DRYRUN_DIR": str(tmp_path),
        "FILLER_DRYRUN_RESULT_PATH": str(tmp_path / "publisher/RESULT.json"),
        "FILLER_STOPFILE": str(tmp_path / "STOP"), "FILLER_DEADLINE": str(end - 90),
    }


@pytest.mark.parametrize("smoke", [False, True])
def test_grant_snapshot_and_placement(tmp_path, smoke):
    grant, env = window(tmp_path, smoke=smoke)
    attempt = tmp_path / "attempt"
    attempt.mkdir()
    captured = custody.grant_context(attempt, env, set(range(4)), 1767225601)
    assert captured["mode"] == ("smoke" if smoke else "official")
    assert captured["snapshot_sha256"] == custody.sha(grant)
    assert captured["actual_cpus"] == [0, 1, 2, 3]
    assert (attempt / "rowflow.grant").read_bytes() == grant.read_bytes()
    with pytest.raises(ValueError, match="placement"):
        custody.grant_context(attempt, env, {0, 1}, 1767225601)


@pytest.mark.parametrize("smoke", [False, True])
def test_preserve_native_controls_and_refuse_changed_artifact(tmp_path, monkeypatch, smoke):
    _, env = window(tmp_path, smoke=smoke)
    for key in ("P5_NATIVE_RESULT", "P5_INSTRUMENT_DEADLINE", "TMPDIR"):
        monkeypatch.setenv(key, "")
    monkeypatch.setattr(custody, "ROOT", tmp_path)
    monkeypatch.setattr(custody.time, "time", lambda: 1767225601)
    monkeypatch.setattr(custody.os, "sched_getaffinity", lambda _pid: set(range(4)))
    monkeypatch.setattr(custody.signal, "signal", lambda *_: None)
    monkeypatch.setattr(custody.subprocess, "run", lambda *_, **__: None)
    monkeypatch.setitem(sys.modules, "complete", SimpleNamespace(validate_native=lambda raw, _: raw["decision"]))
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    for name in ("SOURCE.sha256", "launch.sh", "case.json"):
        (tmp_path / name).write_text("{}")

    def scorer(*_, **__):
        arms = {}
        for arm in ("gold", "negative"):
            folder = tmp_path / "logs/run_evaluation" / arm
            folder.mkdir(parents=True)
            for name in ("report.json", "test_output.txt"):
                (folder / name).write_text(f"original {arm} {name}")
            arms[arm] = {"native_report": str(folder / "report.json"), "test_log": str(folder / "test_output.txt")}
        Path(os.environ["P5_NATIVE_RESULT"]).write_text(json.dumps({
            "arms": arms, "decision": "PASS",
            "producer_source_manifest_sha256": custody.sha(tmp_path / "SOURCE.sha256"),
            "producer_launcher_sha256": custody.sha(tmp_path / "launch.sh"),
        }))

    monkeypatch.setattr(custody.runpy, "run_path", scorer)
    assert custody.run() == custody.complete() == 0
    path = custody.result_path()
    assert path.parent.name == ("publisher" if smoke else "official")
    result = json.loads(path.read_bytes())
    assert result["status"] == "COMPLETE" and result["completion_utc"]
    attempt = path.parent / result["attempt"]
    assert (attempt / "gold-report.json").read_text() == "original gold report.json"
    (attempt / "negative-test_output.txt").write_text("changed")
    with pytest.raises(ValueError, match="binding"):
        custody.complete()


def test_refusal_retains_primary_error_without_completing(tmp_path, monkeypatch):
    _, env = window(tmp_path, smoke=False)
    for key in ("P5_NATIVE_RESULT", "P5_INSTRUMENT_DEADLINE", "TMPDIR"):
        monkeypatch.setenv(key, "")
    monkeypatch.setattr(custody, "ROOT", tmp_path)
    monkeypatch.setattr(custody.time, "time", lambda: 1767225601)
    monkeypatch.setattr(custody.os, "sched_getaffinity", lambda _pid: set(range(4)))
    monkeypatch.setattr(custody.signal, "signal", lambda *_: None)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    for name in ("SOURCE.sha256", "launch.sh"):
        (tmp_path / name).write_text("sealed")

    def refused(*_, **__):
        raise ValueError("control refused before starting arms")

    monkeypatch.setattr(custody.subprocess, "run", refused)
    assert custody.run() == 1
    path = custody.result_path()
    assert not path.exists()
    terminal, = path.parent.glob("attempt-*/terminal.json")
    result = json.loads(terminal.read_bytes())
    assert result["status"] == "UNKNOWN" and result["completion_utc"]
    assert result["grant"]["actual_cpus"] == [0, 1, 2, 3]
    assert "control refused before starting arms" in result["error"]
