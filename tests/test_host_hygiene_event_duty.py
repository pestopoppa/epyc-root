"""Hosted synthetic fixtures only; no production DB, processes, alarms or cleanup."""
from __future__ import annotations

import fcntl
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("lr8_hygiene", ROOT / "scripts/system/host_hygiene_tick.py")
hh = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = hh
SPEC.loader.exec_module(hh)
ORIGINAL_RUN = hh.run


@pytest.fixture
def duty(tmp_path, monkeypatch):
    t = hh.Tick(state_dir=tmp_path / "state")
    events = []
    monkeypatch.setattr(t, "raise_alarm", lambda *a, **k: events.append(("raise", *a)))
    monkeypatch.setattr(t, "clear_alarm", lambda *a: events.append(("clear", *a)))
    root = tmp_path / "root"
    script = root / "scripts/system/opencode_event_reaper.sh"
    script.parent.mkdir(parents=True)
    script.write_text("# LR8_ONCE_STATUS_V1\n")
    row = {"id": "opencode_event_reaper", "script": "scripts/system/opencode_event_reaper.sh",
           "runtime": {"mode": "scheduled", "scheduler": "host_hygiene_tick",
                       "restart_on_stale": False, "relaunch_if_down": False,
                       "log": str(t.state_dir / "opencode_event_reaper.log"), "max_age_s": 3600}}
    registry = tmp_path / "registry.json"
    registry.write_text(json.dumps({"observers": [row]}))
    monkeypatch.setenv("HYGIENE_OPENCODE_EVENTS", "1")
    monkeypatch.setattr(hh, "_event_daemon_copies", lambda: [])
    monkeypatch.setattr(hh, "heavy_gate", lambda: (True, "open"))
    monkeypatch.setattr(hh.time, "time", lambda: 10000)
    launched = []
    def execute(argv, **kw):
        launched.append((argv, kw))
        return subprocess.CompletedProcess(argv, 0, "LR8_ONCE_STATUS_V1 state=absent prune_rc=0\n", "")
    monkeypatch.setattr(hh, "run", execute)
    return t, registry, root, row, events, launched


def invoke(duty):
    t, registry, root, *_ = duty
    hh.event_duty(t, registry, root)


def test_default_is_inactive_without_registry_or_process_reads(duty, monkeypatch):
    monkeypatch.delenv("HYGIENE_OPENCODE_EVENTS")
    monkeypatch.setattr(hh, "_load_census", lambda: pytest.fail("inactive census read"))
    duty[1].unlink()
    invoke(duty)
    assert duty[4] == duty[5] == []


@pytest.mark.parametrize("mutation", ["broken", "duplicate", "daemon", "relaunch", "restart",
                                      "owner", "log", "age", "age_nan", "age_inf", "argv", "capability"])
def test_handover_refuses_before_any_subprocess(duty, mutation):
    t, registry, root, row, events, launched = duty
    if mutation == "broken":
        registry.write_text("{")
    else:
        rt = row["runtime"]
        if mutation == "daemon": rt["mode"] = "daemon"
        elif mutation == "relaunch": rt["relaunch_if_down"] = True
        elif mutation == "restart": rt["restart_on_stale"] = True
        elif mutation == "owner": rt["scheduler"] = "other"
        elif mutation == "log": rt["log"] = "/wrong"
        elif mutation == "age": rt["max_age_s"] = 0
        elif mutation == "age_nan": rt["max_age_s"] = float("nan")
        elif mutation == "age_inf": rt["max_age_s"] = float("inf")
        elif mutation == "argv": rt["start_argv"] = ["/bin/bash", "run"]
        elif mutation == "capability": (root / row["script"]).write_text("legacy only")
        registry.write_text(json.dumps({"observers": [row, row] if mutation == "duplicate" else [row]}))
    invoke(duty)
    assert launched == []
    assert events[0][:2] == ("raise", hh.EVENT_ALARM)


@pytest.mark.parametrize("blind", [False, True])
def test_live_or_blind_daemon_refuses(duty, monkeypatch, blind):
    def scan():
        if blind: raise OSError("unreadable")
        return [123]
    monkeypatch.setattr(hh, "_event_daemon_copies", scan)
    invoke(duty)
    assert duty[5] == [] and duty[4][0][1] == hh.EVENT_ALARM


def test_independent_1800_second_cadence(duty):
    t, _, _, _, _, launched = duty
    t.state["heavy_last_ok_epoch"] = 10000
    t.state["opencode_event_last_attempt_epoch"] = 8201
    invoke(duty)
    assert launched == []
    t.state["opencode_event_last_attempt_epoch"] = 8200
    invoke(duty)
    assert len(launched) == 1
    assert t.state["opencode_event_last_attempt_epoch"] == 10000
    invoke(duty)
    assert len(launched) == 1


@pytest.mark.parametrize("last", ["invalid", True, float("nan"), -1, 10001])
def test_invalid_cadence_fails_closed(duty, last):
    duty[0].state["opencode_event_last_attempt_epoch"] = last
    invoke(duty)
    assert duty[5] == [] and duty[4][0][1] == hh.EVENT_ALARM


def test_cpu_gate_closed_does_not_consume_cadence(duty, monkeypatch):
    monkeypatch.setattr(hh, "heavy_gate", lambda: (False, "CPU busy"))
    invoke(duty)
    assert duty[5] == []
    assert "opencode_event_last_attempt_epoch" not in duty[0].state


def test_dry_run_does_not_consume_cadence_or_write_result(duty):
    duty[0].dry_run = True
    invoke(duty)
    assert duty[5] == [] and "opencode_event_result" not in duty[0].state


@pytest.mark.parametrize("out,rc", [("", 0), ("bad", 0),
    ("LR8_ONCE_STATUS_V1 state=absent prune_rc=0\n", 7),
    ("LR8_ONCE_STATUS_V1 state=absent prune_rc=7\n", 7),
    ("LR8_ONCE_STATUS_V1 state=absent prune_rc=0\n" * 2, 0),
    ("LR8_ONCE_STATUS_V1 state=absent prune_rc=0\nextra0\n", 0),
    ("x" * 8193 + "\nLR8_ONCE_STATUS_V1 state=absent prune_rc=0\n", 0),
    (None, None)])
def test_bad_failed_or_timeout_result_keeps_single_alarm(duty, monkeypatch, out, rc):
    monkeypatch.setattr(hh, "run", lambda *a, **k: None if out is None else subprocess.CompletedProcess(a, rc, out, ""))
    invoke(duty)
    t = duty[0]
    assert t.state["opencode_event_result"]["state"] == "failed"
    assert duty[4][0][:2] == ("raise", hh.EVENT_ALARM)
    assert not (t.state_dir / "opencode_event_reaper.log").exists()
    assert t.state["opencode_event_last_attempt_epoch"] == 10000


@pytest.mark.parametrize("state", ["present", "absent", "unobservable"])
def test_confirmed_state_has_one_alarm_owner(duty, monkeypatch, state):
    monkeypatch.setattr(hh, "run", lambda *a, **k: subprocess.CompletedProcess(a, 0, f"LR8_ONCE_STATUS_V1 state={state} prune_rc=0\n", ""))
    invoke(duty)
    assert duty[0].state["opencode_event_result"]["state"] == state
    assert duty[4][0][:2] == ("raise" if state == "unobservable" else "clear", hh.EVENT_ALARM)
    assert (duty[0].state_dir / "opencode_event_reaper.log").exists()


def test_global_tick_lock_prevents_concurrent_duty(tmp_path, monkeypatch):
    lock = (tmp_path / ".tick.lock").open("w")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    monkeypatch.setattr(hh, "event_duty", lambda t: pytest.fail("overlapping duty"))
    try:
        assert hh.tick(state_dir=tmp_path) == 0
    finally:
        lock.close()


@pytest.mark.parametrize("error", ["timeout", "unavailable"])
def test_actual_run_exception_path_refuses_result(duty, monkeypatch, error):
    def execute(argv, **kw):
        if error == "timeout":
            raise subprocess.TimeoutExpired(argv, kw["timeout"])
        raise OSError("unavailable")
    monkeypatch.setattr(hh, "run", ORIGINAL_RUN)
    monkeypatch.setattr(hh.subprocess, "run", execute)
    invoke(duty)
    assert duty[0].state["opencode_event_result"]["state"] == "failed"
    assert duty[4][0][:2] == ("raise", hh.EVENT_ALARM)


@pytest.mark.parametrize("target", ["result", "log"])
def test_result_or_log_write_failure_never_clears_alarm(duty, monkeypatch, target):
    write = hh.write_json
    def fail(path, data):
        if path.name == ("opencode_event_result.json" if target == "result" else "opencode_event_reaper.log"):
            raise OSError("write denied")
        write(path, data)
    monkeypatch.setattr(hh, "write_json", fail)
    invoke(duty)
    t = duty[0]
    t.flush()
    saved = json.loads(t.state_path.read_text())
    assert saved["heartbeat_at"]
    assert saved["opencode_event_result"]["state"] == "failed"
    assert "storage_error" in saved["opencode_event_result"]
    assert duty[4][0][:2] == ("raise", hh.EVENT_ALARM)
    assert not (t.state_dir / "opencode_event_reaper.log").exists()


def test_process_observation_reads_only_synthetic_tree(tmp_path):
    for pid, argv in ((901, b"bash\0/fake/opencode_event_reaper.sh\0run\0"), (902, b"other\0")):
        path = tmp_path / str(pid)
        path.mkdir()
        (path / "cmdline").write_bytes(argv)
    assert hh._event_daemon_copies(tmp_path) == [901]
    (tmp_path / "903").mkdir()
    with pytest.raises(OSError):
        hh._event_daemon_copies(tmp_path)


def test_current_registry_keeps_daemon_defaults():
    reg = json.loads((ROOT / "scripts/coordination/observer_registry.json").read_text())
    row = next(r for r in reg["observers"] if r["id"] == "opencode_event_reaper")
    assert row["runtime"].get("mode", "daemon") == "daemon"
    assert row["runtime"]["relaunch_if_down"] is True
    assert row["runtime"]["start_argv"][-1] == "run"


def test_keeper_never_launches_scheduled_row_even_if_mixed(duty, monkeypatch):
    t, registry, root, row, _, launched = duty
    row["runtime"]["relaunch_if_down"] = True
    row["runtime"]["start_argv"] = ["/bin/bash", "run"]
    registry.write_text(json.dumps({"observers": [row]}))
    class Census:
        def live_check_row(self, *a):
            pytest.fail("scheduled row treated as daemon")
    monkeypatch.setattr(hh, "_load_census", lambda: Census())
    hh.keeper(t, registry, root)
    assert launched == []
