#!/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
"""Regression tests for scripts/coordination/bus_supervisor.sh.

THE BUG THIS EXISTS FOR (2026-07-27). `exec 9>"$LOCK_FILE"` creates an inheritable
descriptor, and a child inherits it across fork+exec. So the daemon launched by
`bus_supervisor.sh once` inherited fd 9 — flock included — and held the
SUPERVISOR'S OWN LOCK for its entire life. Every later `loop` logged "another
supervisor holds the lock; exiting" while `status` reported no supervisor running:
a complete, silent self-lockout of the watchdog. Fixed with `9>&-` on the child.

Isolated: its own LOCK_FILE, EPYC_ROOT and BUS_ROOT, so it never touches the live
supervisor, daemon, or lock.

Usage: scripts/coordination/tests/test_bus_supervisor.py
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

REAL = Path(__file__).resolve().parents[3]
SUP = REAL / "scripts" / "coordination" / "bus_supervisor.sh"
RESULTS: list[tuple[bool, str]] = []


def check(ok: bool, why: str) -> None:
    RESULTS.append((bool(ok), why))
    print(f"  {'PASS' if ok else 'FAIL'}  {why}")


def fds_on(pid: str, needle: str) -> int:
    d = Path(f"/proc/{pid}/fd")
    if not d.exists():
        return -1
    n = 0
    for f in d.iterdir():
        try:
            if needle in os.readlink(f):
                n += 1
        except OSError:
            continue
    return n


def main() -> int:
    root = Path(tempfile.mkdtemp())
    lock = root / "test_bus_supervisor.lock"
    bus = root / "coordination" / "session-bus"
    (bus / "heartbeats").mkdir(parents=True)
    (root / "logs").mkdir()
    (root / "scripts" / "coordination").mkdir(parents=True)
    # a stand-in daemon: writes a heartbeat, then sleeps like the real one
    stub = root / "scripts" / "coordination" / "session_bus_coordinator.py"
    stub.write_text(
        "#!/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python\n"
        "import json,sys,time,os\n"
        "from datetime import datetime,timezone\n"
        f"hb=r'{bus}/heartbeats/coordinator-daemon.json'\n"
        "while True:\n"
        "    open(hb,'w').write(json.dumps({'agent':'coordinator-daemon','state':'working',"
        "'ts':datetime.now(timezone.utc).isoformat(),'epoch':1,'pid':os.getpid()}))\n"
        "    time.sleep(2)\n")
    stub.chmod(0o755)

    env = {**os.environ, "EPYC_ROOT": str(root), "BUS_ROOT": str(bus),
           "LOCK_FILE": str(lock), "STARTUP_TIMEOUT": "12"}
    try:
        print("== the fd-9 self-lockout regression ==")
        r = subprocess.run(["bash", str(SUP), "once"], capture_output=True, text=True, env=env)
        check(r.returncode == 0, f"`once` starts a daemon (rc={r.returncode})")
        time.sleep(2)
        pids = subprocess.run(["pgrep", "-f", f"{stub} run"], capture_output=True,
                              text=True).stdout.split()
        check(bool(pids), f"a daemon process exists ({pids})")
        if pids:
            held = fds_on(pids[0], lock.name)
            check(held == 0,
                  f"the daemon does NOT inherit the supervisor's lock fd (holds {held}, want 0)")
        check(subprocess.run(["flock", "-n", str(lock), "-c", "true"]).returncode == 0,
              "the lock is FREE after `once` exits — a later supervisor can start")

        r2 = subprocess.run(["bash", str(SUP), "once"], capture_output=True, text=True, env=env)
        check(r2.returncode == 0 and "another supervisor" not in (r2.stderr or ""),
              "a second `once` is not locked out by the daemon it previously started")
    finally:
        for p in subprocess.run(["pgrep", "-f", f"{stub} run"], capture_output=True,
                                text=True).stdout.split():
            subprocess.run(["kill", "-9", p], capture_output=True)
        shutil.rmtree(root, ignore_errors=True)
        print("  (temp root and stub daemon cleaned up)")

    failed = [w for ok, w in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} passed")
    for w in failed:
        print(f"  FAILED: {w}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
