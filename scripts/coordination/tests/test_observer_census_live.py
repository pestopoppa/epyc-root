#!/usr/bin/env python3
"""Tests for ``observer_census.py --live`` — the read-only /proc walk (NIB2-81
remedy (b); tmp/daemon-staleness-20260917/report.md).

WHY THIS EXISTS. The static census (tests/test_observer_contract.py,
observer_census.py's CHECKS) certifies the registry FILE is honest. It stayed
green throughout the 2026-09-17 incident ("census OK (17 observers)") while
the live reaper executed a copy of its own script that a commit had orphaned
nine days earlier. This suite exercises the second half: given a REAL process
this test spawns itself, does the live walk correctly tell "still executing
the code that is committed now" apart from the three broken shapes the report
found on this host (lane-pinned/orphaned-inode collapsed here into one
mechanism — a write+rename replacing the file under a running process — plus
orphaned-tree, a dead pid, and a recycled pid).

ISOLATION. Every fixture is a throwaway temp dir; every spawned process is
started and killed by this suite and never touched by name/pattern (only by
the pid this test itself captured — CLAUDE.md Process Management). The
canonical-root comparison is pointed at a fixture via DP_CANONICAL_ROOT /
canonical_root=, never the real /workspace. Alarm tests set ALARM_STATE_PATH
and ALARM_FILE_PATH to temp files before ever calling into alarm_channel, so
no test run writes to coordination/session-bus/{alarm_state.json,alarms.jsonl}.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

_COORD = Path(__file__).resolve().parents[1]
if str(_COORD) not in sys.path:
    sys.path.insert(0, str(_COORD))

import observer_census as census  # noqa: E402


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #

class Daemon:
    """A real `bash <script>` process this test owns end to end.

    Mirrors the shape every live daemon censused on 2026-09-17 actually has:
    bash opens the script and holds it on fd 255 for the process's whole life
    (report §1, every row's `fd/255 -> ...` column) — reproducing that
    mechanism for real is the only way this suite tests the real code path
    rather than a description of it.
    """

    def __init__(self, path: Path):
        self.path = path
        self.proc: subprocess.Popen | None = None

    def start(self) -> int:
        self.proc = subprocess.Popen(
            ["/bin/bash", str(self.path)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        deadline = time.time() + 5
        while time.time() < deadline:
            if Path(f"/proc/{self.proc.pid}/fd/255").exists():
                return self.proc.pid
            time.sleep(0.05)
        raise AssertionError("daemon never opened its script on fd 255")

    def stop(self):
        if self.proc is not None and self.proc.poll() is None:
            self.proc.kill()
            self.proc.wait(timeout=10)
        self.proc = None


def _write_script(path: Path, body: str = "#!/bin/bash\nsleep 300\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    path.chmod(0o755)


def _row(pidfile: Path, script_rel: str, **extra) -> dict:
    runtime = {
        "pidfile": str(pidfile),
        "expected_path": script_rel,
        "provenance": str(pidfile) + ".provenance.json",
    }
    runtime.update(extra)
    return {"id": "t_daemon", "script": script_rel, "runtime": runtime}


@pytest.fixture
def canon(tmp_path):
    root = tmp_path / "canon"
    root.mkdir()
    return root


# --------------------------------------------------------------------------- #
# live_check_row — the five states
# --------------------------------------------------------------------------- #

def test_running_current(tmp_path, canon):
    script_rel = "scripts/system/daemon.sh"
    script = canon / script_rel
    _write_script(script)
    d = Daemon(script)
    pid = d.start()
    pidfile = tmp_path / "d.pid"
    pidfile.write_text(str(pid))
    try:
        r = census.live_check_row(_row(pidfile, script_rel), canonical_root=str(canon))
        assert r["state"] == "running_current", r
        assert r["pid"] == pid
    finally:
        d.stop()


def test_running_stale_after_write_and_rename(tmp_path, canon):
    """The exact mechanism (report §2b): git never writes a tracked file in
    place, it unlink+recreates, so a running process's fd 255 is orphaned onto
    the OLD inode while the path now names a new one. Reproduced here with the
    same write-to-a-sibling + os.replace idiom git itself uses, against a
    daemon this test spawned and still holds a handle on.
    """
    script_rel = "scripts/system/daemon.sh"
    script = canon / script_rel
    _write_script(script)
    d = Daemon(script)
    pid = d.start()
    pidfile = tmp_path / "d.pid"
    pidfile.write_text(str(pid))
    try:
        sibling = canon / "daemon.sh.new"
        _write_script(sibling, "#!/bin/bash\nsleep 300\n# a committed fix\n")
        os.replace(sibling, script)  # unlink+recreate at the SAME path

        r = census.live_check_row(_row(pidfile, script_rel), canonical_root=str(canon))
        assert r["state"] == "running_stale", r
        assert "inode" in r["detail"]
    finally:
        d.stop()


def test_running_off_canon(tmp_path):
    """A daemon executing from a LANE, never canon/view — shape 1 of the report
    (the reaper holding a lane copy under worktrees/mains/...).
    """
    lane = tmp_path / "lane"
    script_rel = "scripts/system/daemon.sh"
    _write_script(lane / script_rel)
    d = Daemon(lane / script_rel)
    pid = d.start()
    pidfile = tmp_path / "d.pid"
    pidfile.write_text(str(pid))
    empty_canon = tmp_path / "canon_elsewhere"
    empty_canon.mkdir()
    try:
        r = census.live_check_row(_row(pidfile, script_rel), canonical_root=str(empty_canon))
        assert r["state"] == "running_off_canon", r
    finally:
        d.stop()


def test_not_running_dead_pid(tmp_path, canon):
    """A pidfile naming a pid that is certainly not running."""
    script_rel = "scripts/system/daemon.sh"
    _write_script(canon / script_rel)
    dead = subprocess.Popen(["/bin/true"])
    dead.wait()
    time.sleep(0.05)
    assert not Path(f"/proc/{dead.pid}").exists()
    pidfile = tmp_path / "d.pid"
    pidfile.write_text(str(dead.pid))

    r = census.live_check_row(_row(pidfile, script_rel), canonical_root=str(canon))
    assert r["state"] == "not_running", r


def test_not_running_missing_pidfile(tmp_path, canon):
    script_rel = "scripts/system/daemon.sh"
    _write_script(canon / script_rel)
    pidfile = tmp_path / "does_not_exist.pid"

    r = census.live_check_row(_row(pidfile, script_rel), canonical_root=str(canon))
    assert r["state"] == "not_running", r


def test_not_running_pid_reused_by_different_cmdline(tmp_path, canon):
    """A pidfile whose pid is alive but belongs to a stranger process. Identity
    MUST come from cmdline, never from the pid number alone (the exact
    recycled-pid hazard bus_supervisor.sh's C49 note names for its own daemon).
    """
    script_rel = "scripts/system/daemon.sh"
    _write_script(canon / script_rel)
    stranger = subprocess.Popen(["/bin/sleep", "60"])
    time.sleep(0.1)
    pidfile = tmp_path / "d.pid"
    pidfile.write_text(str(stranger.pid))
    try:
        r = census.live_check_row(_row(pidfile, script_rel), canonical_root=str(canon))
        assert r["state"] == "not_running", r
        assert "RECYCLED" in r["detail"]
    finally:
        stranger.kill()
        stranger.wait()


def test_cannot_tell_when_runtime_row_incomplete(canon, tmp_path):
    row = {"id": "broken", "script": "x", "runtime": {}}
    r = census.live_check_row(row, canonical_root=str(canon))
    assert r["state"] == "cannot_tell", r


def test_run_live_census_skips_rows_without_runtime(canon):
    reg = {"observers": [{"id": "a", "script": "x"}, {"id": "b", "script": "y", "runtime": None}]}
    assert census.run_live_census(reg, canonical_root=str(canon)) == []


# --------------------------------------------------------------------------- #
# mode: "scheduled" — a target with NO persistent process between ticks (an
# external, host-side scheduler invokes it repeatedly instead). Corrected in
# 2026-09-23: hub_supervisor.sh runs no `loop` today, only host-cron `once`
# ticks, so its loop pidfile is PERMANENTLY absent by design — the first
# --live run against it read that as not_running and would have alarmed
# forever on a target that is, in fact, healthy.
# --------------------------------------------------------------------------- #

def _scheduled_row(log: Path, max_age_s=600, **extra) -> dict:
    runtime = {"mode": "scheduled", "log": str(log), "max_age_s": max_age_s}
    runtime.update(extra)
    return {"id": "t_scheduled", "script": "x", "runtime": runtime}


def test_scheduled_current_fresh_log(tmp_path):
    log = tmp_path / "sched.log"
    log.write_text("once: healthy\n")
    r = census.live_check_row(_scheduled_row(log, max_age_s=600))
    assert r["state"] == "scheduled_current", r
    assert r["pid"] is None


def test_scheduled_stale_old_log(tmp_path):
    """An old mtime, forced via os.utime — no process involved at all, matching
    the actual mechanism: a scheduler that stopped ticking leaves its log
    exactly this way, with nothing left alive to signal or restart."""
    log = tmp_path / "sched.log"
    log.write_text("once: healthy\n")
    old = time.time() - 1000
    os.utime(log, (old, old))
    r = census.live_check_row(_scheduled_row(log, max_age_s=600))
    assert r["state"] == "scheduled_stale", r


def test_scheduled_not_running_missing_log(tmp_path):
    """Missing log => not_running (positive evidence nothing has ticked),
    mirroring daemon mode's own 'missing pidfile = not_running' — documented
    choice, see _live_check_scheduled's docstring."""
    log = tmp_path / "does_not_exist.log"
    r = census.live_check_row(_scheduled_row(log, max_age_s=600))
    assert r["state"] == "not_running", r


def test_scheduled_cannot_tell_missing_max_age(tmp_path):
    log = tmp_path / "sched.log"
    log.write_text("x\n")
    row = {"id": "t", "script": "x", "runtime": {"mode": "scheduled", "log": str(log)}}
    r = census.live_check_row(row)
    assert r["state"] == "cannot_tell", r


def test_scheduled_current_never_alarms_on_a_missing_daemon_pidfile(tmp_path):
    """The exact regression this correction fixes: a row with mode=scheduled
    must never be graded against pidfile presence at all."""
    log = tmp_path / "sched.log"
    log.write_text("once: healthy\n")
    row = {
        "id": "hub_like", "script": "x",
        "runtime": {"mode": "scheduled", "log": str(log), "max_age_s": 600,
                    "pidfile": str(tmp_path / "never_exists.pid")},
    }
    r = census.live_check_row(row)
    assert r["state"] == "scheduled_current", r


# --------------------------------------------------------------------------- #
# Alarm integration — reuses alarm_channel.py, the SAME sink fleet_watch.sh
# already raises through. Every test below points ALARM_STATE_PATH and
# ALARM_FILE_PATH at temp files before calling in, so nothing here can ever
# touch coordination/session-bus/{alarm_state.json,alarms.jsonl}.
# --------------------------------------------------------------------------- #

@pytest.fixture
def alarm_env(tmp_path, monkeypatch):
    state = tmp_path / "alarm_state.json"
    record = tmp_path / "alarms.jsonl"
    monkeypatch.setenv("ALARM_STATE_PATH", str(state))
    monkeypatch.setenv("ALARM_FILE_PATH", str(record))
    return state, record


def _events(record: Path, event: str, key: str):
    if not record.exists():
        return []
    import json
    out = []
    for line in record.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("event") == event and row.get("key") == key:
            out.append(row)
    return out


def test_raise_live_alarms_no_alarm_writes_nothing(alarm_env):
    state, record = alarm_env
    results = [{"id": "x", "state": "running_stale", "detail": "d", "pid": 1}]
    census.raise_live_alarms(results, no_alarm=True, alarm_state=state)
    assert not state.exists()
    assert not record.exists()


def test_raise_live_alarms_raises_for_a_problem_state(alarm_env):
    state, record = alarm_env
    results = [{"id": "reaper_fixture", "state": "running_stale",
                "detail": "stale detail", "pid": 42}]
    census.raise_live_alarms(results, no_alarm=False, alarm_state=state)
    raised = _events(record, "raised", "daemon-live:reaper_fixture")
    assert len(raised) == 1, raised
    assert raised[0]["severity"] == "critical"


def test_raise_live_alarms_clears_a_healthy_daemon(alarm_env):
    state, record = alarm_env
    bad = [{"id": "reaper_fixture", "state": "not_running", "detail": "d", "pid": None}]
    census.raise_live_alarms(bad, no_alarm=False, alarm_state=state)
    assert _events(record, "raised", "daemon-live:reaper_fixture")

    good = [{"id": "reaper_fixture", "state": "running_current", "detail": "d2", "pid": 42}]
    census.raise_live_alarms(good, no_alarm=False, alarm_state=state)
    cleared = _events(record, "cleared", "daemon-live:reaper_fixture")
    assert len(cleared) == 1, cleared


def test_raise_live_alarms_clears_on_scheduled_current_too(alarm_env):
    """scheduled_current must be treated as a GOOD state by the alarm path,
    not just by the report printer — the exact axis the 'grade good states,
    not one magic string' correction targets."""
    state, record = alarm_env
    bad = [{"id": "hub_like", "state": "scheduled_stale", "detail": "d", "pid": None}]
    census.raise_live_alarms(bad, no_alarm=False, alarm_state=state)
    assert _events(record, "raised", "daemon-live:hub_like")

    good = [{"id": "hub_like", "state": "scheduled_current", "detail": "d2", "pid": None}]
    census.raise_live_alarms(good, no_alarm=False, alarm_state=state)
    cleared = _events(record, "cleared", "daemon-live:hub_like")
    assert len(cleared) == 1, cleared


def test_raise_live_alarms_dedupes_repeat_problems(alarm_env):
    """The Phase 0 gate this whole channel exists for (test_alarm_channel.py's
    TestDedupe): N raises of an unchanged key deliver exactly once."""
    state, record = alarm_env
    bad = [{"id": "reaper_fixture", "state": "running_stale", "detail": "d", "pid": 1}]
    for _ in range(4):
        census.raise_live_alarms(bad, no_alarm=False, alarm_state=state)
    raised = _events(record, "raised", "daemon-live:reaper_fixture")
    assert len(raised) == 1, raised


# --------------------------------------------------------------------------- #
# CLI: --live vs the unchanged static path
# --------------------------------------------------------------------------- #

def test_cli_static_path_unchanged_without_live():
    res = subprocess.run(
        [sys.executable, str(_COORD / "observer_census.py")],
        capture_output=True, text=True, timeout=120,
    )
    assert res.returncode == 0, res.stderr
    assert "observer census: OK" in res.stdout


def test_cli_live_surface_exits_cleanly_against_the_real_registry():
    # observer_census.REGISTRY_PATH is a module-level constant resolved from
    # __file__, so the CLI always reads the REAL registry — the per-row
    # STATE MACHINE is exercised directly above via live_check_row/
    # run_live_census(reg=...) against fixtures. This test only proves --live's
    # CLI surface (arg parsing, report printing, exit code) works end to end.
    res = subprocess.run(
        [sys.executable, str(_COORD / "observer_census.py"), "--live", "--no-alarm"],
        capture_output=True, text=True, timeout=120,
    )
    assert "LIVE CENSUS" in res.stdout, res.stdout
    assert res.returncode in (0, 1)


if __name__ == "__main__":
    raise SystemExit(
        "REFUSING: pytest-fixture suite; run: "
        "python -m pytest scripts/coordination/tests/test_observer_census_live.py -q"
    )
