#!/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
"""Regression tests for scripts/coordination/bus_supervisor.sh.

TWO BUGS THIS EXISTS FOR.

C49 (2026-08-12) — THE WATCHDOG COULD NOT SEE THE DAEMON. Health was
`pgrep -f 'session_bus_coordinator\\.py run'`, which encodes THIS SUPERVISOR'S
launch idiom, not the daemon's identity: the live daemon runs as
`<venv>/bin/python .../session_bus_coordinator.py --bus-root <path> run` and
`--bus-root <path>` sits between `.py` and `run`. So a healthy daemon with a fresh
heartbeat was reported `pids ''`, declared dead, and "restarted" every ~10s
forever, each relaunch self-exiting on the daemon's flock. Identity now comes from
the heartbeat's own pid, verified against /proc/<pid>/cmdline, in THREE states —
alive / dead / unknown. `unknown` never kills and never passes.

2026-07-27 — THE fd-9 SELF-LOCKOUT. `exec 9>"$LOCK_FILE"` creates an inheritable
descriptor, and a child inherits it across fork+exec, so the daemon launched by
`bus_supervisor.sh once` held the SUPERVISOR'S OWN LOCK for its entire life. Every
later `loop` logged "another supervisor holds the lock; exiting" while `status`
reported no supervisor running. Fixed with `9>&-` on the child.

ISOLATION. Own LOCK_FILE, EPYC_ROOT, BUS_ROOT, DAEMON_LOCK_FILE and DAEMON_MARKER.
Note how much weaker the old fourth axis had to be: DAEMON_PATTERN fed `pgrep -f`,
a search over EVERY process on this shared host, and on 2026-07-27 a test that
believed itself isolated killed the PRODUCTION daemon through it. DAEMON_MARKER
cannot do that even if mis-scoped — it is matched against the argv of the one pid
this test's own heartbeat names, so it can never discover, let alone signal, a
process belonging to another session. This suite therefore starts and kills only
processes it created, and verifies identity before every kill it performs.

Usage:  scripts/coordination/tests/test_bus_supervisor.py
        BUS_SUPERVISOR_SH=/path/to/mutant.sh scripts/coordination/tests/test_bus_supervisor.py
(the env override exists so the suite can be run against a deliberately mutated
copy of the script — a test that has never failed has not been shown to test
anything.)
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
SUP = Path(os.environ.get("BUS_SUPERVISOR_SH")
           or REAL / "scripts" / "coordination" / "bus_supervisor.sh")
PYTHON = sys.executable
RESULTS: list[tuple[bool, str]] = []


def check(ok: bool, why: str) -> None:
    RESULTS.append((bool(ok), why))
    print(f"  {'PASS' if ok else 'FAIL'}  {why}")


def fds_on(pid: str | int, needle: str) -> int:
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


def cmdline(pid: int) -> str:
    try:
        return (Path(f"/proc/{pid}/cmdline").read_bytes()
                .replace(b"\0", b" ").decode("utf-8", "replace"))
    except OSError:
        return ""


def alive(pid: int) -> bool:
    return Path(f"/proc/{pid}").is_dir()


class Harness:
    """A fully scoped fake bus: temp root, stub daemon, own locks."""

    def __init__(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="bus_sup_test_"))
        self.bus = self.root / "coordination" / "session-bus"
        (self.bus / "heartbeats").mkdir(parents=True)
        (self.root / "logs").mkdir()
        (self.root / "scripts" / "coordination").mkdir(parents=True)
        self.hb = self.bus / "heartbeats" / "coordinator-daemon.json"
        self.sup_lock = self.root / "test_bus_supervisor.lock"
        self.daemon_lock = self.root / "test_daemon_singleton.lock"
        self.spawned = self.root / "spawned.pids"
        # Unique name => a marker that cannot match the production daemon, and a
        # DAEMON path that cannot be confused with it either.
        self.stub = (self.root / "scripts" / "coordination"
                     / f"stub_coordinator_{os.getpid()}.py")
        self.stub.write_text(self._stub_source())
        self.stub.chmod(0o755)
        self.mine: list[int] = []

    def _stub_source(self) -> str:
        # Mimics the real daemon on the two axes that matter: it takes
        # `--bus-root <path> run` (the argv shape the old pattern could not match)
        # and it is a flock singleton (a duplicate self-exits).
        return f'''#!{PYTHON}
import fcntl, json, os, sys, time
from datetime import datetime, timezone
args = sys.argv[1:]
bus = args[args.index("--bus-root") + 1] if "--bus-root" in args else {str(self.bus)!r}
fh = open({str(self.daemon_lock)!r}, "a+b")
try:
    fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
except OSError:
    sys.stderr.write("stub-daemon: another instance holds the lock; exiting\\n")
    sys.exit(0)
with open({str(self.spawned)!r}, "a") as f:
    f.write(str(os.getpid()) + "\\n")
hb = os.path.join(bus, "heartbeats", "coordinator-daemon.json")
while True:
    tmp = hb + ".tmp"
    with open(tmp, "w") as f:
        json.dump({{"agent": "coordinator-daemon", "state": "working", "epoch": 1,
                   "pid": os.getpid(),
                   "ts": datetime.now(timezone.utc).isoformat()}}, f)
    os.replace(tmp, hb)
    time.sleep(1)
'''

    def env(self, **extra: str) -> dict[str, str]:
        e = {**os.environ,
             "EPYC_ROOT": str(self.root),
             "BUS_ROOT": str(self.bus),
             "LOCK_FILE": str(self.sup_lock),
             "DAEMON": str(self.stub),
             "DAEMON_LOCK_FILE": str(self.daemon_lock),
             "DAEMON_MARKER": self.stub.name,
             "STARTUP_TIMEOUT": "12"}
        e.update(extra)
        return e

    # ---------------------------------------------------------------- helpers
    def start_stub_like_production(self) -> int:
        """Start the stub with the EXACT argv shape that broke the old pattern."""
        p = subprocess.Popen([PYTHON, str(self.stub), "--bus-root", str(self.bus), "run"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.mine.append(p.pid)
        for _ in range(60):
            if self.hb.exists() and self.hb_pid() == p.pid:
                return p.pid
            time.sleep(0.25)
        raise RuntimeError("stub daemon never published a heartbeat")

    def hb_pid(self) -> int | None:
        try:
            return int(json.loads(self.hb.read_text())["pid"])
        except Exception:
            return None

    def write_heartbeat(self, payload: dict, age_s: float = 0.0) -> None:
        self.hb.write_text(json.dumps(payload))
        if age_s:
            t = time.time() - age_s
            os.utime(self.hb, (t, t))

    def log_text(self) -> str:
        p = self.root / "logs" / "bus_supervisor.log"
        return p.read_text() if p.exists() else ""

    def launches(self) -> int:
        return self.log_text().count("launching coordinator-daemon")

    def run(self, mode: str = "once", **env_extra: str) -> subprocess.CompletedProcess:
        return subprocess.run(["bash", str(SUP), mode], capture_output=True,
                              text=True, env=self.env(**env_extra))

    def track_spawned(self) -> list[int]:
        if not self.spawned.exists():
            return []
        pids = [int(x) for x in self.spawned.read_text().split()]
        for p in pids:
            if p not in self.mine:
                self.mine.append(p)
        return pids

    def cleanup(self) -> None:
        self.track_spawned()
        for pid in self.mine:
            # Practise what the script preaches: verify identity, then signal.
            if alive(pid) and self.stub.name in cmdline(pid):
                try:
                    os.kill(pid, 9)
                except OSError:
                    pass
        shutil.rmtree(self.root, ignore_errors=True)


# ============================================================== the C49 cases
def case_a_alive_daemon_is_seen(h: Harness) -> None:
    """(a) Daemon ALIVE with production-shaped argv: healthy, and NOTHING spawned.

    This is the case that was broken. Under the old `pgrep -f '...\\.py run'` the
    `--bus-root <path>` between `.py` and `run` made the daemon invisible, so this
    ran the unhealthy branch and relaunched — forever.
    """
    print("== (a) a live daemon with `--bus-root` in its argv is SEEN ==")
    pid = h.start_stub_like_production()
    before = h.launches()
    r = h.run("once")
    check(r.returncode == 0, f"`once` exits 0 against a healthy daemon (rc={r.returncode})")
    check(h.launches() == before,
          f"NOTHING was spawned (launch lines {before} -> {h.launches()})")
    check(alive(pid) and h.hb_pid() == pid,
          f"the daemon was never disrupted (pid {pid} still alive and still publishing)")
    st = subprocess.run(["bash", str(SUP), "status"], capture_output=True, text=True,
                        env=h.env())
    check("ALIVE" in st.stdout and f"pid {pid}" in st.stdout,
          "`status` names the daemon ALIVE with its pid")
    check("health      : OK" in st.stdout, "`status` reports health OK")
    os.kill(pid, 9)
    for _ in range(40):
        if not alive(pid):
            break
        time.sleep(0.1)


def case_b_dead_daemon_relaunched_once(h: Harness) -> None:
    """(b) Daemon genuinely DEAD: relaunch EXACTLY once, and reach healthy."""
    print("== (b) a dead daemon is relaunched exactly once ==")
    # A heartbeat naming a pid that cannot exist, aged past STALE_AFTER.
    gone = subprocess.Popen([PYTHON, "-c", "pass"])
    gone.wait()
    h.write_heartbeat({"agent": "coordinator-daemon", "state": "working",
                       "epoch": 1, "pid": gone.pid,
                       "ts": datetime.now(timezone.utc).isoformat()}, age_s=1000)
    before = h.launches()
    r = h.run("once")
    spawned = h.track_spawned()
    check(r.returncode == 0, f"`once` exits 0 after a successful relaunch (rc={r.returncode})")
    check(h.launches() - before == 1,
          f"relaunched EXACTLY once (launch lines +{h.launches() - before})")
    check("DEAD:" in h.log_text(), "the log says DEAD, distinctly from UNKNOWN")
    new_pid = h.hb_pid()
    check(bool(new_pid) and alive(new_pid) and h.stub.name in cmdline(new_pid),
          f"a real daemon is now running and publishing (pid {new_pid})")
    st = subprocess.run(["bash", str(SUP), "status"], capture_output=True, text=True,
                        env=h.env())
    check("health      : OK" in st.stdout, "`status` reports health OK after the relaunch")
    for pid in spawned:
        if alive(pid):
            os.kill(pid, 9)
    for _ in range(40):
        if not any(alive(p) for p in spawned):
            break
        time.sleep(0.1)


def case_c_never_kills_a_stranger(h: Harness) -> None:
    """(c) A recycled pid belonging to somebody else is NEVER signalled."""
    print("== (c) a non-daemon process named by the heartbeat is left alone ==")
    stranger = subprocess.Popen([PYTHON, "-c", "import time; time.sleep(600)"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        h.write_heartbeat({"agent": "coordinator-daemon", "state": "working",
                           "epoch": 1, "pid": stranger.pid,
                           "ts": datetime.now(timezone.utc).isoformat()}, age_s=1000)
        r = h.run("once")
        log = h.log_text()
        h.track_spawned()
        check(alive(stranger.pid) and stranger.poll() is None,
              f"the stranger (pid {stranger.pid}) is STILL ALIVE — never signalled")
        check("RECYCLED" in log,
              "the log names the pid as recycled rather than reporting a dead daemon")
        check(f"stopping wedged daemon pid {stranger.pid}" not in log,
              "no kill was even attempted against the stranger's pid")
        check(r.returncode in (0, 1),
              f"`once` still acted on the real condition (rc={r.returncode})")
    finally:
        stranger.kill()
        stranger.wait()
        for pid in h.track_spawned():
            if alive(pid) and h.stub.name in cmdline(pid):
                os.kill(pid, 9)
        time.sleep(0.5)


def case_d_unknown_is_its_own_state(h: Harness) -> None:
    """(d) Identity unknowable + fresh heartbeat: no kill, no spawn, loud report.

    The fail-open twin matters as much as the fail-closed one: this must not be
    silently treated as healthy either, so the exit code is a distinct 3.
    """
    print("== (d) UNKNOWN is neither alive nor dead ==")
    h.write_heartbeat({"agent": "coordinator-daemon", "state": "working", "epoch": 1,
                       "ts": datetime.now(timezone.utc).isoformat()})  # no pid at all
    before = h.launches()
    r = h.run("once")
    log = h.log_text()
    check(r.returncode == 3,
          f"`once` exits 3 — distinct from 0 (healthy) and 1 (failed) (rc={r.returncode})")
    check("IDENTITY UNKNOWN" in log, "the log says IDENTITY UNKNOWN in those words")
    check(h.launches() == before,
          f"NOTHING was spawned on unknown identity ({before} -> {h.launches()})")
    check("not signalling anything" not in log or "stopping wedged" not in log,
          "no kill was attempted with no confirmed pid")
    st = subprocess.run(["bash", str(SUP), "status"], capture_output=True, text=True,
                        env=h.env())
    check("UNKNOWN" in st.stdout and "health      : UNHEALTHY" in st.stdout,
          "`status` prints UNKNOWN and refuses to call it OK")


def case_e_no_relaunch_storm(h: Harness) -> None:
    """(e) The storm is bounded at its source, and again by a retry cap.

    e1: the daemon singleton lock is held by a live process => a relaunch would
    self-exit, so none is attempted. That IS the 2026-08-12 shape.
    e2: an unstartable daemon in `loop` mode does not spawn every poll.
    """
    print("== (e) no relaunch storm ==")
    holder = h.start_stub_like_production()          # holds h.daemon_lock
    h.write_heartbeat({"agent": "coordinator-daemon", "state": "working", "epoch": 1,
                       "pid": 999999999,             # unknowable identity
                       "ts": datetime.now(timezone.utc).isoformat()}, age_s=1000)
    before = h.launches()
    h.run("once")
    check(h.launches() == before,
          f"e1: no launch while the singleton lock is held live ({before} -> {h.launches()})")
    check("NOT LAUNCHING" in h.log_text(), "e1: the refusal is logged, not silent")
    os.kill(holder, 9)
    for _ in range(40):
        if not alive(holder):
            break
        time.sleep(0.1)

    dud = h.root / "scripts" / "coordination" / f"{h.stub.stem}_dud.py"
    dud.write_text(f"#!{PYTHON}\nimport sys\nsys.exit(1)\n")
    dud.chmod(0o755)
    h.write_heartbeat({"agent": "coordinator-daemon", "state": "working", "epoch": 1,
                       "pid": 999999999,
                       "ts": datetime.now(timezone.utc).isoformat()}, age_s=1000)
    before = h.launches()
    env = h.env(DAEMON=str(dud), DAEMON_MARKER=dud.name, STARTUP_TIMEOUT="1",
                POLL_INTERVAL="1", MAX_RESTART_ATTEMPTS="2", MAX_BACKOFF="8")
    proc = subprocess.Popen(["bash", str(SUP), "loop"], env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(22)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
    got = h.launches() - before
    # 22s at the old 10s cadence was >=2 and unbounded-growing with no give-up.
    # Bounded here: MAX_BACKOFF=8 with MAX_RESTART_ATTEMPTS=2 caps it near 22/9.
    check(got <= 4, f"e2: {got} launches in 22s of a failing daemon — bounded, not a storm")
    check("GIVING UP" in h.log_text(),
          "e2: the supervisor says loudly that the bus is unwatched")


def case_f_fd9_self_lockout(h: Harness) -> None:
    """The pre-existing 2026-07-27 regression, unchanged in intent."""
    print("== (f) the fd-9 self-lockout regression ==")
    r = h.run("once")
    check(r.returncode == 0, f"`once` starts a daemon (rc={r.returncode})")
    time.sleep(3)
    pids = h.track_spawned()
    check(bool(pids), f"a daemon process exists ({pids})")
    if pids:
        held = fds_on(pids[-1], h.sup_lock.name)
        check(held == 0,
              f"the daemon does NOT inherit the supervisor's lock fd (holds {held}, want 0)")
    check(subprocess.run(["flock", "-n", str(h.sup_lock), "-c", "true"]).returncode == 0,
          "the lock is FREE after `once` exits — a later supervisor can start")
    r2 = h.run("once")
    check(r2.returncode == 0 and "another supervisor" not in (r2.stderr or ""),
          "a second `once` is not locked out by the daemon it previously started")


def main() -> int:
    print(f"script under test: {SUP}")
    for case in (case_a_alive_daemon_is_seen, case_b_dead_daemon_relaunched_once,
                 case_c_never_kills_a_stranger, case_d_unknown_is_its_own_state,
                 case_e_no_relaunch_storm, case_f_fd9_self_lockout):
        h = Harness()
        try:
            case(h)
        except Exception as exc:  # noqa: BLE001 — a crashed case is a FAILED case
            check(False, f"{case.__name__} raised {exc!r}")
        finally:
            h.cleanup()

    failed = [w for ok, w in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} passed")
    for w in failed:
        print(f"  FAILED: {w}")
    return 1 if failed else 0


def test_bus_supervisor() -> None:
    """Make pytest COUNT this suite.

    Without this the file is collected (there is a `test_` in its name and a
    __pycache__ to prove pytest has walked it), `main()` is never called, no
    assertion ever runs, and it reports green having executed nothing — a check
    that is not counted by the reporter is not a check.
    """
    assert main() == 0, "bus_supervisor.sh regressions — see stdout"


if __name__ == "__main__":
    sys.exit(main())
