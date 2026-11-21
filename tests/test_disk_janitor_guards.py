"""disk_janitor.sh GUARDS pass (operator 2026-11-21): trash tick every pass, hygiene reclaim under the floor, fail-soft."""
import os
import subprocess
from pathlib import Path

JANITOR = Path(__file__).resolve().parent.parent / "scripts/coordination/churn/disk_janitor.sh"


def _run(tmp_path, floor, trash_rc=0, hyg_rc=0):
    tools = tmp_path / "tools"
    (tools / "safety").mkdir(parents=True)
    (tools / "system").mkdir()
    (tools / "safety/trash_reap_tick.sh").write_text(f"#!/bin/bash\necho TRASHRAN\nexit {trash_rc}\n")
    (tools / "system/host_hygiene_tick.py").write_text(f"import sys\nprint('HYGRAN', sys.argv[1:])\nsys.exit({hyg_rc})\n")
    flags = tmp_path / "flags"
    flags.mkdir()
    env = dict(os.environ, JANITOR_FLAGS=str(flags), JANITOR_TOOLS=str(tools), JANITOR_KEEPER=str(tmp_path / "nokeeper"),
               JANITOR_LIFECYCLE="0", JANITOR_TRASHES="", JANITOR_RECLAIM_FLOOR_GIB=str(floor), JANITOR_DISK="/")
    cp = subprocess.run(["bash", str(JANITOR), "--once"], env=env, capture_output=True, text=True, timeout=120)
    return cp, (flags / "disk-janitor.log").read_text()


def test_trash_every_pass_reclaim_only_under_floor(tmp_path):
    cp, log = _run(tmp_path, floor=1)  # free >= 1 GiB: no reclaim
    assert cp.returncode == 0
    assert "GUARD-TRASH rc=0" in log and "TRASHRAN" in log
    assert "GUARD-RECLAIM-SKIP" in log and "HYGRAN" not in log


def test_reclaim_under_floor_and_failsoft(tmp_path):
    cp, log = _run(tmp_path, floor=10**9, trash_rc=3, hyg_rc=5)
    assert cp.returncode == 0, cp.stderr  # guard errors never break the janitor
    assert "GUARD-TRASH rc=3" in log
    assert "GUARD-RECLAIM rc=5" in log and "HYGRAN" in log and "'reclaim'" in log
    assert log.rstrip().splitlines()[-1].count("FREE") == 1  # the pass still reached its final FREE line
