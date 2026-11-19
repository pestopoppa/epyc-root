#!/usr/bin/env python3
"""CHURNUP-OBSERVER-ARGV: per-session `handoff_sessions.py pane-status <slug>` processes share the dispatcher's installed
path. churn_up.sh must identify the dispatcher by its pidfile (alive AND argv carries `dispatch`) and fall back to an argv
scan that matches only the `dispatch` subcommand token, never pane-status.

Real stand-in processes in a temp dir; nothing is killed except the stand-ins this test spawned (by their own pids)."""
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest

_TESTS = os.path.dirname(os.path.abspath(__file__))
CO = os.path.dirname(_TESTS)
CU = os.path.join(CO, "churn", "churn_up.sh")
REPO = os.path.dirname(os.path.dirname(CO))


class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="cudisp-")
        self.F = os.path.join(self.tmp, "flags")
        os.makedirs(os.path.join(self.F, "bin"))
        self.hs = os.path.join(self.F, "bin", "handoff_sessions.py")
        with open(self.hs, "w") as f:
            f.write("import time\ntime.sleep(60)\n")
        self.procs = []

    def tearDown(self):
        for p in self.procs:
            if p.poll() is None:
                p.send_signal(signal.SIGKILL)
                p.wait(timeout=10)

    def spawn(self, *args):
        p = subprocess.Popen([sys.executable, "-I", self.hs, *args])
        self.procs.append(p)
        for _ in range(100):
            try:
                if self.hs.encode() in open(f"/proc/{p.pid}/cmdline", "rb").read():
                    return p
            except OSError:
                pass
            time.sleep(0.05)
        self.fail("stand-in never visible")

    def pane_status(self):
        return self.spawn("pane-status", "some-slug", "--flags", self.F)

    def dispatcher(self):
        return self.spawn("dispatch", "--loop", "--interval", "60")

    def pidfile(self, pid):
        with open(os.path.join(self.F, "handoff-sessions.dispatcher.pid"), "w") as f:
            f.write(f"{pid}\n")

    def observe(self):
        env = dict(os.environ, EPYC_ROOT=REPO, CHURN_REPO=REPO, CHURN_FLAGS=self.F,
                   CHURN_OBS_PIDFILE="handoff-sessions.dispatcher.pid", CHURN_OBS_MARKER="handoff_sessions.py dispatch",
                   CHURN_OBS_PATH=f"{self.hs} dispatch", OG_STATE_DIR=os.path.join(self.tmp, "alerts"))
        r = subprocess.run(["bash", CU, "observe"], env=env, capture_output=True, text=True, timeout=60)
        return r.returncode, r.stdout + r.stderr

    def test_pane_status_alone_is_absent_not_blind(self):
        self.pane_status(); self.pane_status()
        rc, out = self.observe()
        self.assertEqual((rc, "state=absent" in out), (1, True), out)

    def test_pidfile_dispatcher_present_beside_pane_status(self):
        self.pane_status()
        d = self.dispatcher()
        self.pidfile(d.pid)
        rc, out = self.observe()
        self.assertEqual((rc, "state=present" in out), (0, True), out)

    def test_pidfile_naming_a_pane_status_pid_is_not_the_dispatcher(self):
        p = self.pane_status()
        self.pidfile(p.pid)
        rc, out = self.observe()
        self.assertEqual((rc, "state=absent" in out), (1, True), out)

    def test_pidfileless_dispatch_still_seen_by_fallback_scan(self):
        self.pane_status()
        self.dispatcher()
        rc, out = self.observe()
        self.assertEqual((rc, "state=unobservable" in out), (3, True), out)

    def test_dry_run_offers_dispatcher_start_despite_pane_status(self):
        self.pane_status()
        env = dict(os.environ, CHURN_FLAGS=self.F, CHURN_SHADOW_OUT=os.path.join(self.F, "shadow"),
                   CHURN_TMUX_SESSION="churn-test-absent", OG_STATE_DIR=os.path.join(self.tmp, "alerts"))
        out = subprocess.run(["bash", CU, "--dry-run", "--with-dispatcher"], env=env, capture_output=True, text=True,
                             timeout=120).stdout
        self.assertNotIn("dispatcher: OBSERVATION BLIND", out)
        self.assertIn(f"START python3 -I {self.hs} dispatch", out)


if __name__ == "__main__":
    unittest.main()
