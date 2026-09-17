"""Offline tests for scripts/system/opencode_event_reaper.sh (NI-OC-a).

The reaper's only observer-derived decision is whether to pass ``--vacuum`` to
``prune_agent_event_store.py``. VACUUM while opencode holds the DB is the destructive
branch; skipping it is always safe (freed pages are reused, the file just does not
shrink yet). So the contract under test is:

    present       -> no --vacuum
    unobservable  -> no --vacuum, and an OBSERVER-BLIND breadcrumb
    absent        -> --vacuum

Everything here is offline: no model calls, no real DB, no real opencode. The only
processes spawned are stand-ins this file creates and reaps by their own pid.
The full observer battery (tests/test_observer_contract.py) also runs against the
registered sandbox; this file additionally exercises the production ``db_fd``
channel, which the generic battery cannot express.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "system" / "opencode_event_reaper.sh"
MARK = "epyc_reaper_test_standin_5d2e9b"


class Standin:
    """A real process with MARK in its argv, optionally holding a file open on fd 3."""

    def __init__(self, tmp: Path, hold_open: Path | None = None):
        self.path = tmp / f"{MARK}.sh"
        body = "#!/bin/bash\n"
        if hold_open is not None:
            body += f"exec 3<'{hold_open}'\n"
        body += "sleep 120\n"
        self.path.write_text(body)
        self.path.chmod(0o755)
        self.proc = None

    def start(self) -> int:
        self.proc = subprocess.Popen(["/bin/bash", str(self.path)],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.time() + 5
        while time.time() < deadline:
            try:
                if MARK.encode() in Path(f"/proc/{self.proc.pid}/cmdline").read_bytes():
                    # give `exec 3<` a moment to land
                    time.sleep(0.1)
                    return self.proc.pid
            except OSError:
                pass
            time.sleep(0.05)
        raise AssertionError("stand-in never became visible in /proc")

    def stop(self):
        if self.proc is not None and self.proc.poll() is None:
            self.proc.send_signal(signal.SIGKILL)   # only the pid this test created
            self.proc.wait(timeout=10)
        self.proc = None


def _dead_pid() -> int:
    p = subprocess.Popen(["/bin/true"])
    p.wait()
    time.sleep(0.05)
    assert not Path(f"/proc/{p.pid}").exists()
    return p.pid


def _env(tmp: Path, **extra) -> dict:
    env = dict(os.environ)
    env.pop("OG_BLIND_STREAK_MAX", None)
    env.update({
        "EPYC_ROOT": str(REPO),
        "OG_STATE_DIR": str(tmp / "alerts"),
        "OPENCODE_MARK": MARK,
        "OPENCODE_PIDFILE": str(tmp / "hb.json"),
        "OPENCODE_DB": "",                      # db_fd channel off unless a test enables it
        "REAPER_PIDFILE": str(tmp / "reaper.pid"),
        "REAPER_PRUNE": str(tmp / "prune_stub.sh"),
    })
    env.update({k: str(v) for k, v in extra.items()})
    return env


def _prune_stub(tmp: Path) -> Path:
    """Records its argv instead of touching any database (the reaper runs PRUNE via python3)."""
    stub = tmp / "prune_stub.sh"
    stub.write_text(
        "import sys, pathlib\n"
        f"pathlib.Path({str(tmp / 'prune_argv')!r}).write_text('\\n'.join(sys.argv[1:]) + '\\n')\n"
        "print('ok')\n"
    )
    return stub


def _observe(env: dict) -> tuple[int, dict]:
    res = subprocess.run(["/bin/bash", str(SCRIPT), "observe"],
                         capture_output=True, text=True, env=env, timeout=120)
    kv = dict(re.findall(r"^(\w+)=(.*)$", res.stdout, re.M))
    kv["_stderr"] = res.stderr
    return res.returncode, kv


def _once(env: dict, tmp: Path) -> tuple[list[str], str]:
    (tmp / "prune_argv").unlink(missing_ok=True)
    res = subprocess.run(["/bin/bash", str(SCRIPT), "once"],
                         capture_output=True, text=True, env=env, timeout=120)
    assert res.returncode == 0, res.stderr[-2000:]
    argv = (tmp / "prune_argv").read_text().split()
    return argv, res.stdout + res.stderr


def _hb(tmp: Path, pid):
    payload = {"ts": time.time()}
    if pid is not None:
        payload["pid"] = pid
    (tmp / "hb.json").write_text(json.dumps(payload))


# --------------------------------------------------------------------------- #
# observe: the three states
# --------------------------------------------------------------------------- #

def test_observe_present_withholds_vacuum(tmp_path):
    s = Standin(tmp_path)
    try:
        _hb(tmp_path, s.start())
        rc, kv = _observe(_env(tmp_path))
    finally:
        s.stop()
    assert (rc, kv["state"], kv["vacuum"]) == (0, "present", "withheld"), kv


def test_observe_absent_permits_vacuum(tmp_path):
    rc, kv = _observe(_env(tmp_path))          # no stand-in, no pidfile
    assert (rc, kv["state"], kv["vacuum"]) == (1, "absent", "permitted"), kv


def test_observe_channel_disagreement_is_unobservable_and_withholds(tmp_path):
    """The specimen: pidfile names a dead pid while a live target is right there."""
    s = Standin(tmp_path)
    try:
        s.start()
        _hb(tmp_path, _dead_pid())
        rc, kv = _observe(_env(tmp_path))
    finally:
        s.stop()
    assert (rc, kv["state"], kv["vacuum"]) == (3, "unobservable", "withheld"), kv
    assert "DISAGREE" in kv["why"]


def test_observe_partial_blindness_is_unobservable_and_withholds(tmp_path):
    _hb(tmp_path, None)                        # pidfile exists, carries no pid; no target
    rc, kv = _observe(_env(tmp_path))
    assert (rc, kv["state"], kv["vacuum"]) == (3, "unobservable", "withheld"), kv


def test_observe_never_writes_the_reaper_pidfile(tmp_path):
    _observe(_env(tmp_path))
    assert not (tmp_path / "reaper.pid").exists(), "observe clobbered the daemon's pidfile"


# --------------------------------------------------------------------------- #
# once: the CONSUMER — what actually reaches prune_agent_event_store.py
# --------------------------------------------------------------------------- #

def test_once_absent_passes_vacuum(tmp_path):
    _prune_stub(tmp_path)
    argv, _ = _once(_env(tmp_path), tmp_path)
    assert "--vacuum" in argv and "--apply" in argv, argv
    assert not list((tmp_path / "alerts").glob("*.json"))


def test_once_present_withholds_vacuum(tmp_path):
    _prune_stub(tmp_path)
    s = Standin(tmp_path)
    try:
        _hb(tmp_path, s.start())
        argv, _ = _once(_env(tmp_path), tmp_path)
    finally:
        s.stop()
    assert "--vacuum" not in argv and "--apply" in argv, argv


def test_once_unobservable_withholds_vacuum_and_alarms(tmp_path):
    """The third state takes the SAME branch as present, and says so loudly."""
    _prune_stub(tmp_path)
    s = Standin(tmp_path)
    try:
        s.start()
        _hb(tmp_path, _dead_pid())
        argv, out = _once(_env(tmp_path), tmp_path)
    finally:
        s.stop()
    assert "--vacuum" not in argv and "--apply" in argv, argv
    assert "OBSERVER-BLIND" in out
    alerts = list((tmp_path / "alerts").glob("*.json"))
    assert alerts, "went blind silently — no breadcrumb"
    payload = json.loads(alerts[0].read_text())
    assert payload["state"] == "unobservable" and payload["detail"].strip()


def test_once_present_clears_a_stale_alarm(tmp_path):
    _prune_stub(tmp_path)
    s = Standin(tmp_path)
    try:
        s.start()
        _hb(tmp_path, _dead_pid())
        _once(_env(tmp_path), tmp_path)
        assert list((tmp_path / "alerts").glob("*.json"))
        _hb(tmp_path, s.proc.pid)
        _once(_env(tmp_path), tmp_path)
    finally:
        s.stop()
    assert not list((tmp_path / "alerts").glob("*.json")), "sighting did not clear the breadcrumb"


# --------------------------------------------------------------------------- #
# db_fd: the production channel (no pidfile in production)
# --------------------------------------------------------------------------- #

def _prod_env(tmp: Path, db: Path) -> dict:
    return _env(tmp, OPENCODE_DB=str(db), OPENCODE_PIDFILE="")


def test_db_fd_present_when_target_holds_db_open(tmp_path):
    db = tmp_path / "fake.db"; db.write_bytes(b"\0" * 16)
    s = Standin(tmp_path, hold_open=db)
    try:
        s.start()
        rc, kv = _observe(_prod_env(tmp_path, db))
    finally:
        s.stop()
    assert (rc, kv["state"], kv["vacuum"]) == (0, "present", "withheld"), kv


def test_db_fd_absent_when_nothing_holds_db(tmp_path):
    db = tmp_path / "fake.db"; db.write_bytes(b"\0" * 16)
    rc, kv = _observe(_prod_env(tmp_path, db))
    assert (rc, kv["state"], kv["vacuum"]) == (1, "absent", "permitted"), kv


def test_db_fd_disagreement_argv_without_db_is_unobservable(tmp_path):
    """argv says present, fd says absent — a drifted identity, not a verdict."""
    db = tmp_path / "fake.db"; db.write_bytes(b"\0" * 16)
    s = Standin(tmp_path)                      # mark in argv, DB NOT open
    try:
        s.start()
        rc, kv = _observe(_prod_env(tmp_path, db))
    finally:
        s.stop()
    assert (rc, kv["state"], kv["vacuum"]) == (3, "unobservable", "withheld"), kv


def test_db_fd_missing_db_is_unavailable_not_absent(tmp_path):
    rc, kv = _observe(_prod_env(tmp_path, tmp_path / "does-not-exist.db"))
    assert (rc, kv["state"], kv["vacuum"]) == (3, "unobservable", "withheld"), kv


# --------------------------------------------------------------------------- #
# hygiene
# --------------------------------------------------------------------------- #

def test_script_is_valid_bash_and_executable():
    assert os.access(SCRIPT, os.X_OK)
    res = subprocess.run(["bash", "-n", str(SCRIPT)], capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
    head = SCRIPT.read_text().splitlines()
    assert head[0] == "#!/bin/bash"
    assert any(ln.strip() == "set -euo pipefail" for ln in head[:60])


def test_no_bare_name_probe_left_in_code():
    """Comments may mention the old probe; code may not run it."""
    code = [ln for ln in SCRIPT.read_text().splitlines() if not ln.lstrip().startswith("#")]
    assert not any(re.search(r"\b(pgrep|pidof)\b", ln) for ln in code)


def test_shellcheck_clean():
    sc = shutil.which("shellcheck") or os.environ.get("SHELLCHECK")
    if not sc:
        pytest.skip("shellcheck not installed")
    res = subprocess.run([sc, "-x", "-S", "warning", str(SCRIPT)],
                         capture_output=True, text=True, cwd=REPO)
    assert res.returncode == 0, res.stdout + res.stderr
