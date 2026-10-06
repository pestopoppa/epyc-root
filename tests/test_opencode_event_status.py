"""Hosted synthetic shell fixtures: fake observer channels and a temporary prune stub."""
from __future__ import annotations

import fcntl
import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/system/opencode_event_reaper.sh"


@pytest.fixture
def shell(tmp_path):
    guard = tmp_path / "scripts/coordination"
    guard.mkdir(parents=True)
    (guard / "observer_guard.sh").write_text("""
OG_ALARM_TOKEN=OBSERVER-BLIND
og_init() { :; }
og_round_begin() { :; }
og_channel() { :; }
og_proc_scan() { printf ''; }
og_present_if_any() { printf 'absent\\n'; }
og_verdict() { printf '%s\\n' "$TEST_STATE"; }
og_why() { printf 'synthetic channels\\n'; }
og_note_sighting() { :; }
og_clear() { rm -f "$TEST_ALARM"; }
og_alarm() { printf 'blind\\n' > "$TEST_ALARM"; }
""")
    (guard / "daemon_provenance.sh").write_text("dp_attest() { :; }\ndp_stale_since_start() { return 2; }\n")
    prune = tmp_path / "prune.py"
    prune.write_text("import os, pathlib, sys\n"
                     "pathlib.Path(os.environ['TEST_ARGV']).write_text('\\n'.join(sys.argv[1:]))\n"
                     "print('synthetic prune')\n"
                     "sys.exit(int(os.environ['TEST_RC']))\n")
    env = dict(os.environ, EPYC_ROOT=str(tmp_path), OPENCODE_DB="", OPENCODE_PIDFILE="",
               REAPER_PRUNE=str(prune), REAPER_PIDFILE=str(tmp_path / "daemon.pid"),
               REAPER_ONCE_LOCK=str(tmp_path / "once.lock"), TEST_STATE="absent", TEST_RC="0",
               TEST_ARGV=str(tmp_path / "argv"), TEST_ALARM=str(tmp_path / "guardian"))
    return tmp_path, env


def call(shell, mode):
    return subprocess.run(["/bin/bash", str(SCRIPT), mode], env=shell[1], capture_output=True,
                          text=True, timeout=15)


@pytest.mark.parametrize("state", ["absent", "present", "unobservable"])
def test_once_status_preserves_vacuum_guard_with_no_guardian_alarm(shell, state):
    tmp, env = shell
    env["TEST_STATE"] = state
    cp = call(shell, "once-status")
    assert cp.returncode == 0, cp.stderr
    args = (tmp / "argv").read_text().splitlines()
    assert "--apply" in args
    assert ("--vacuum" in args) == (state == "absent")
    assert cp.stdout.splitlines()[-1] == f"LR8_ONCE_STATUS_V1 state={state} prune_rc=0"
    assert not (tmp / "guardian").exists()
    assert not (tmp / "daemon.pid").exists()


def test_once_status_returns_actual_prune_rc(shell):
    shell[1]["TEST_RC"] = "7"
    cp = call(shell, "once-status")
    assert cp.returncode == 7
    assert cp.stdout.splitlines()[-1] == "LR8_ONCE_STATUS_V1 state=absent prune_rc=7"


def test_once_status_present_does_not_clear_guardian_alarm(shell):
    tmp, env = shell
    env["TEST_STATE"] = "present"
    (tmp / "guardian").write_text("existing legacy alert")
    cp = call(shell, "once-status")
    assert cp.returncode == 0
    assert (tmp / "guardian").read_text() == "existing legacy alert"


def test_once_status_overlap_exits_without_prune(shell):
    tmp, _ = shell
    with (tmp / "once.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        cp = call(shell, "once-status")
    assert cp.returncode == 75
    assert not (tmp / "argv").exists()


def test_legacy_once_preserves_swallowed_failure(shell):
    shell[1]["TEST_RC"] = "7"
    cp = call(shell, "once")
    assert cp.returncode == 0
    assert "prune failed" in cp.stdout
    assert "LR8_ONCE_STATUS_V1" not in cp.stdout


def test_legacy_once_keeps_guardian_alarm(shell):
    shell[1]["TEST_STATE"] = "unobservable"
    cp = call(shell, "once")
    assert cp.returncode == 0
    assert (shell[0] / "guardian").exists()
    assert "--vacuum" not in (shell[0] / "argv").read_text()


def test_daemon_run_branch_is_unchanged():
    # Hash of the complete original run branch from the approved source base.
    import hashlib
    source = SCRIPT.read_text()
    branch = source.split("\n  run)\n", 1)[1].split("\n    ;;", 1)[0]
    assert hashlib.sha256(branch.encode()).hexdigest() == "fc1c86d4a40844f6e803cb7e135a742786642ecf2cfc82b4227f825ba46dfb49"
