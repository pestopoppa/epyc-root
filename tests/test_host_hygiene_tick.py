"""Tests for scripts/system/host_hygiene_tick.py — offline, temp dirs, no real alarms or daemons.

Every alarm call is captured by replacing the module's `run` (the alarm channel is a subprocess),
and the only process spawned is a stand-in daemon this file launches and reaps by its own pid.
"""
from __future__ import annotations

import importlib.util
import json
import os
import signal
import subprocess
import sys
import textwrap
import time
from collections import namedtuple
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location("host_hygiene_tick", ROOT / "scripts/system/host_hygiene_tick.py")
hh = importlib.util.module_from_spec(_SPEC)
sys.modules["host_hygiene_tick"] = hh
_SPEC.loader.exec_module(hh)

Usage = namedtuple("Usage", "total used free")


@pytest.fixture
def calls(monkeypatch):
    rec: list[list[str]] = []

    def fake_run(argv, timeout=60, **kw):
        rec.append(list(argv))
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(hh, "run", fake_run)
    return rec


def alarm_calls(rec):
    return [(a[2], a[a.index("--key") + 1]) for a in rec if len(a) > 3 and a[1].endswith("alarm_channel.py")]


def tick(tmp_path):
    return hh.Tick(dry_run=False, state_dir=tmp_path / "state")


# --------------------------------------------------------------------------- disk free
def test_disk_free_two_sample_raise_and_clear(tmp_path, calls, monkeypatch):
    free = {"v": 150e9}
    monkeypatch.setattr(hh.shutil, "disk_usage", lambda p: Usage(0, 0, free["v"]))
    t = tick(tmp_path)
    hh.disk_free(t)
    assert alarm_calls(calls) == []                       # one low sample is not enough
    hh.disk_free(t)
    assert alarm_calls(calls) == [("raise", "host-disk-free-low")]
    raise_argv = calls[-1]
    assert raise_argv[raise_argv.index("--severity") + 1] == "warning"
    free["v"] = 210e9                                     # above warn but below the 110% clear line
    hh.disk_free(t)
    hh.disk_free(t)
    assert alarm_calls(calls)[-1] == ("raise", "host-disk-free-low")
    free["v"] = 300e9
    hh.disk_free(t)
    assert alarm_calls(calls)[-1][0] == "raise"           # one high sample is not enough either
    hh.disk_free(t)
    assert alarm_calls(calls)[-1] == ("clear", "host-disk-free-low")


def test_disk_free_critical_and_growers_named(tmp_path, calls, monkeypatch):
    monkeypatch.setattr(hh.shutil, "disk_usage", lambda p: Usage(0, 0, 50e9))
    t = tick(tmp_path)
    now = time.time()
    t.state["grower_history"] = [
        {"at_epoch": now - 7 * 86400, "sizes": {"/a": 10e9, "/b": 100e9}},
        {"at_epoch": now, "sizes": {"/a": 60e9, "/b": 101e9}},
    ]
    hh.disk_free(t)
    hh.disk_free(t)
    argv = calls[-1]
    assert argv[argv.index("--severity") + 1] == "critical"
    msg = argv[argv.index("--message") + 1]
    assert msg.index("/a") < msg.index("/b")              # ranked by growth, not size
    assert t.state["heavy_due_now"] is True


def test_disk_free_unreadable_neither_raises_nor_clears(tmp_path, calls, monkeypatch):
    def boom(p):
        raise OSError("nope")
    monkeypatch.setattr(hh.shutil, "disk_usage", boom)
    t = tick(tmp_path)
    t.state["active_alarms"] = ["host-disk-free-low"]
    for _ in range(3):
        hh.disk_free(t)
    assert alarm_calls(calls) == []


def test_top_growers_without_baseline_ranks_by_size():
    rows = hh.top_growers([{"at_epoch": 1, "sizes": {"/s": 1, "/l": 9, "/none": None}}])
    assert [r["path"] for r in rows] == ["/l", "/s"]


# --------------------------------------------------------------------------- keeper
def _registry(tmp_path, script, pidfile, extra=None):
    rt = {"pidfile": str(pidfile), "expected_path": script.name, "provenance": str(pidfile) + ".prov",
          "relaunch_if_down": True, "start_argv": ["/bin/bash", "{canonical_root}/" + script.name],
          "log": str(tmp_path / "daemon.log")}
    rt.update(extra or {})
    reg = {"observers": [{"id": "fake_daemon", "script": script.name, "runtime": rt}]}
    p = tmp_path / "registry.json"
    p.write_text(json.dumps(reg))
    return p


def _daemon_script(tmp_path, pidfile):
    s = tmp_path / "fake_daemon_xyz.sh"
    s.write_text(textwrap.dedent(f"""\
        #!/bin/bash
        echo $$ > {pidfile}
        trap 'kill $c 2>/dev/null; exit 0' TERM
        sleep 60 & c=$!
        wait $c
    """))
    return s


def _reap(pidfile):
    try:
        pid = int(Path(pidfile).read_text())
    except (OSError, ValueError):
        return
    try:
        os.kill(pid, signal.SIGTERM)                       # the stand-in's trap reaps its sleep
    except ProcessLookupError:
        pass


def test_keeper_relaunches_a_down_daemon_once_then_rate_limits(tmp_path, calls):
    pidfile = tmp_path / "d.pid"
    script = _daemon_script(tmp_path, pidfile)
    reg = _registry(tmp_path, script, pidfile)
    t = tick(tmp_path)
    try:
        hh.keeper(t, registry_path=reg, root=tmp_path)
        assert pidfile.exists(), "\n".join(t.lines)
        pid = int(pidfile.read_text())
        assert Path(f"/proc/{pid}").exists()
        assert any("relaunched" in ln for ln in t.lines)
    finally:
        _reap(pidfile)
    time.sleep(0.2)
    pidfile.unlink()
    t.lines.clear()
    hh.keeper(t, registry_path=reg, root=tmp_path)          # down again, inside the rate limit
    assert not pidfile.exists()
    assert any("rate-limited" in ln for ln in t.lines)


def test_keeper_dry_run_never_launches(tmp_path, calls):
    pidfile = tmp_path / "d.pid"
    script = _daemon_script(tmp_path, pidfile)
    reg = _registry(tmp_path, script, pidfile)
    t = hh.Tick(dry_run=True, state_dir=tmp_path / "state")
    hh.keeper(t, registry_path=reg, root=tmp_path)
    time.sleep(0.3)
    assert not pidfile.exists()
    assert any("DRY-RUN would launch" in ln for ln in t.lines)


def test_keeper_ignores_rows_without_opt_in(tmp_path, calls):
    pidfile = tmp_path / "d.pid"
    script = _daemon_script(tmp_path, pidfile)
    reg = _registry(tmp_path, script, pidfile, {"relaunch_if_down": False})
    t = tick(tmp_path)
    hh.keeper(t, registry_path=reg, root=tmp_path)
    time.sleep(0.3)
    assert not pidfile.exists()


def test_keeper_does_not_launch_a_second_copy(tmp_path, calls):
    """pidfile missing but the script runs (unregistered copy) -> no relaunch."""
    pidfile = tmp_path / "d.pid"
    script = _daemon_script(tmp_path, tmp_path / "other.pid")
    reg = _registry(tmp_path, script, pidfile)
    proc = subprocess.Popen(["/bin/bash", str(script)])
    try:
        time.sleep(0.3)
        t = tick(tmp_path)
        hh.keeper(t, registry_path=reg, root=tmp_path)
        assert not pidfile.exists()
        assert any("not relaunching" in ln for ln in t.lines)
    finally:
        _reap(tmp_path / "other.pid")
        proc.kill()
        proc.wait()


def test_keeper_alarms_when_relaunch_dies(tmp_path, calls):
    pidfile = tmp_path / "d.pid"
    script = tmp_path / "dies_fast.sh"
    script.write_text("#!/bin/bash\nexit 7\n")
    reg = _registry(tmp_path, script, pidfile)
    t = tick(tmp_path)
    hh.keeper(t, registry_path=reg, root=tmp_path)
    assert ("raise", "daemon-down-fake_daemon") in alarm_calls(calls)


def test_production_registry_opts_in_only_the_opencode_reaper():
    reg = json.loads((ROOT / "scripts/coordination/observer_registry.json").read_text())
    opted = [r["id"] for r in reg["observers"] if (r.get("runtime") or {}).get("relaunch_if_down")]
    assert opted == ["opencode_event_reaper"]


# --------------------------------------------------------------------------- backups
def test_backups_stale_raises_and_fresh_clears(tmp_path, calls):
    st = tmp_path / "LAST_STATUS"
    st.write_text("2026-08-02T02:00:00Z STATUS OK\n")
    old = time.time() - 40 * 3600
    os.utime(st, (old, old))
    t = tick(tmp_path)
    hh.backups(t, status=st)
    assert alarm_calls(calls) == [("raise", "claude-backups-stale")]
    st.write_text("2026-10-04T02:14:16Z STATUS OK\n")
    hh.backups(t, status=st)
    assert alarm_calls(calls)[-1] == ("clear", "claude-backups-stale")


def test_backups_failed_status_raises(tmp_path, calls):
    st = tmp_path / "LAST_STATUS"
    st.write_text("2026-10-04T02:14:16Z STATUS FAILED\n")
    t = tick(tmp_path)
    hh.backups(t, status=st)
    assert alarm_calls(calls) == [("raise", "claude-backups-stale")]


# --------------------------------------------------------------------------- heavy gate
def _fake_region_lock(tmp_path, rows, rc=0):
    p = tmp_path / "region-lock"
    p.write_text(f"#!/bin/bash\necho '{json.dumps(rows)}'\nexit {rc}\n")
    p.chmod(0o755)
    return str(p)


def test_heavy_gate_states(tmp_path, monkeypatch):
    monkeypatch.setattr(hh, "CPU_WINDOW", tmp_path / "absent.json")
    monkeypatch.setattr(hh, "REGION_LOCK", _fake_region_lock(tmp_path, [{"region": "q0", "global_held": False}]))
    assert hh.heavy_gate()[0] is True
    monkeypatch.setattr(hh, "REGION_LOCK", _fake_region_lock(tmp_path, [{"region": "q0", "global_held": True}]))
    assert hh.heavy_gate()[0] is False
    monkeypatch.setattr(hh, "REGION_LOCK", _fake_region_lock(tmp_path, [], rc=1))
    assert hh.heavy_gate() == (False, "region-lock status unreadable")
    monkeypatch.setattr(hh, "REGION_LOCK", str(tmp_path / "missing"))
    assert hh.heavy_gate()[0] is False                      # unreadable == closed


def test_heavy_gate_cpu_window(tmp_path, monkeypatch):
    monkeypatch.setattr(hh, "REGION_LOCK", _fake_region_lock(tmp_path, [{"region": "q0", "global_held": False}]))
    cw = tmp_path / "cw.json"
    monkeypatch.setattr(hh, "CPU_WINDOW", cw)
    future = "2999-01-01T00:00:00Z"
    cw.write_text(json.dumps({"state": "open", "loop_holds_claim": True, "expires_at": future}))
    assert hh.heavy_gate()[0] is False
    cw.write_text(json.dumps({"state": "closing", "loop_holds_claim": False, "expires_at": future}))
    assert hh.heavy_gate()[0] is False
    cw.write_text(json.dumps({"state": "open", "loop_holds_claim": True, "expires_at": "2000-01-01T00:00:00Z"}))
    assert hh.heavy_gate()[0] is True                       # expired window = dead loop, ignore it
    cw.write_text("{not json")
    assert hh.heavy_gate()[0] is False


def test_heavy_defers_and_alarms_when_starved(tmp_path, calls):
    t = tick(tmp_path)
    t.state["heavy_last_ok_epoch"] = time.time() - 4 * 86400
    hh.heavy(t, gate=lambda: (False, "CPU regions held: ['q0']"))
    assert ("raise", "host-hygiene-heavy-starved") in alarm_calls(calls)
    assert any("deferred" in ln for ln in t.lines)


def test_heavy_stops_when_gate_closes_mid_run(tmp_path, calls, monkeypatch):
    seq = iter([(True, "open"), (False, "closed")])
    ran = []
    monkeypatch.setattr(hh, "grower_snapshot", lambda t, check: ran.append("growers"))
    monkeypatch.setattr(hh, "stray_files", lambda t: ran.append("stray"))
    monkeypatch.setattr(hh, "codex_report", lambda t: ran.append("codex"))
    t = tick(tmp_path)
    hh.heavy(t, gate=lambda: next(seq))
    assert ran == ["growers"]
    assert "heavy_last_ok_epoch" not in t.state
    assert any("stopped mid-run" in ln for ln in t.lines)


def test_heavy_not_due_does_nothing(tmp_path, calls):
    t = tick(tmp_path)
    t.state["heavy_last_ok_epoch"] = time.time()
    hh.heavy(t, gate=lambda: pytest.fail("gate must not be consulted when not due"))


# --------------------------------------------------------------------------- reports
def test_stray_files_reports_only_old_unheld(tmp_path, calls):
    root = tmp_path / "models"
    (root / "repo" / ".cache").mkdir(parents=True)
    old = time.time() - 3 * 86400
    stale = root / "repo" / ".cache" / "blob.incomplete"
    stale.write_bytes(b"x" * 10)
    os.utime(stale, (old, old))
    fresh = root / "repo" / "new.gguf.part"
    fresh.write_bytes(b"x")
    held = root / "repo" / "held.part"
    held.write_bytes(b"x")
    os.utime(held, (old, old))
    big = tmp_path / "tmp" / "stray.gguf"
    big.parent.mkdir()
    with open(big, "wb") as fh:
        fh.truncate(11 * 2**30)                              # sparse: costs no disk
    os.utime(big, (old, old))
    t = tick(tmp_path)
    with open(held, "rb"):
        rep = hh.stray_files(t, partial_roots=[(str(root), 6)], large_roots=[(str(tmp_path / "tmp"), 3)])
    assert [r["path"] for r in rep["partials"]] == [str(stale)]
    assert [r["path"] for r in rep["large_tmp_files"]] == [str(big)]
    assert ("raise", "stray-download-files") in alarm_calls(calls)


def test_tick_writes_heartbeat_and_log(tmp_path, calls, monkeypatch):
    monkeypatch.setattr(hh.shutil, "disk_usage", lambda p: Usage(0, 0, 500e9))
    monkeypatch.setattr(hh, "keeper", lambda t: None)
    monkeypatch.setattr(hh, "backups", lambda t: None)
    monkeypatch.setattr(hh, "heavy", lambda t, force=False: None)
    sd = tmp_path / "state"
    assert hh.tick(state_dir=sd) == 0
    st = json.loads((sd / "state.json").read_text())
    assert st["heartbeat_at"] and st["disk_free_bytes"] == 500e9
    assert "disk-free" in (sd / "host_hygiene.log").read_text()


def test_hub_supervisor_runs_tick_from_both_once_and_loop():
    """C42 lesson: a hook called from `once` but not `loop` (or vice versa) silently half-works."""
    src = (ROOT / "scripts/dashboard/hub_supervisor.sh").read_text()
    for fn in ("cmd_once", "cmd_loop"):
        body = src.split(f"{fn}() {{", 1)[1].split("\n}\n", 1)[0]
        assert "run_hygiene_tick" in body, fn
    assert "9>&-" in src.split("run_hygiene_tick() {", 1)[1].split("\n}\n", 1)[0]


def test_no_worktree_or_scratch_sweep_in_the_tick():
    """Operator direction 2026-10-04: worktree/scratch cleanup belongs to wrap-up, not a cron job."""
    src = (ROOT / "scripts/system/host_hygiene_tick.py").read_text()
    body = src.split("def heavy(", 1)[1].split("\ndef ", 1)[0]
    assert "worktree" not in body and "scratch_cleanup" not in src.split('"""', 2)[2]
