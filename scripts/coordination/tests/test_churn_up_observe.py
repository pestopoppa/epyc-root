#!/usr/bin/env python3
"""OBS-CHURN-UP: churn_up.sh probes are three-valued (present / absent / unobservable) via observer_guard.sh.

Real stand-in process, temp flags dir; nothing is killed except the stand-in this test spawned (by its own pid)."""
import os
import signal
import subprocess
import tempfile
import time
import unittest

_TESTS = os.path.dirname(os.path.abspath(__file__))
CO = os.path.dirname(_TESTS)
CU = os.path.join(CO, "churn", "churn_up.sh")
REPO = os.path.dirname(os.path.dirname(CO))
MARK = "epyc_churn_obs_standin_91c2"


class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="cuobs-")
        self.F = os.path.join(self.tmp, "flags")
        os.makedirs(self.F)
        self.proc = None

    def tearDown(self):
        if self.proc and self.proc.poll() is None:
            self.proc.send_signal(signal.SIGKILL)
            self.proc.wait(timeout=10)

    def standin(self):
        path = os.path.join(self.tmp, MARK + ".sh")
        with open(path, "w") as f:
            f.write("#!/bin/bash\nsleep 60\n")
        os.chmod(path, 0o755)
        self.proc = subprocess.Popen(["/bin/bash", path])
        for _ in range(100):
            try:
                if MARK.encode() in open(f"/proc/{self.proc.pid}/cmdline", "rb").read():
                    return path
            except OSError:
                pass
            time.sleep(0.05)
        self.fail("stand-in never visible")

    def observe(self, path):
        env = dict(os.environ, EPYC_ROOT=REPO, CHURN_REPO=REPO, CHURN_FLAGS=self.F, CHURN_OBS_PIDFILE="t.pid",
                   CHURN_OBS_MARKER=MARK, CHURN_OBS_PATH=path, OG_STATE_DIR=os.path.join(self.tmp, "alerts"))
        r = subprocess.run(["bash", CU, "observe"], env=env, capture_output=True, text=True, timeout=60)
        return r.returncode, r.stdout, r.stderr

    def pidfile(self, text):
        with open(os.path.join(self.F, "t.pid"), "w") as f:
            f.write(text)

    def test_present_plain_pidfile(self):
        path = self.standin()
        self.pidfile(f"{self.proc.pid}\n")
        rc, out, _ = self.observe(path)
        self.assertEqual((rc, "state=present" in out), (0, True), out)

    def test_absent_when_nothing_anywhere(self):
        rc, out, _ = self.observe(os.path.join(self.tmp, MARK + ".sh"))
        self.assertEqual((rc, "state=absent" in out), (1, True), out)

    def test_stale_pidfile_with_live_holder_is_unobservable_not_absent(self):
        path = self.standin()
        dead = subprocess.Popen(["/bin/true"]); dead.wait()
        self.pidfile(f"{dead.pid}\n")
        rc, out, err = self.observe(path)
        self.assertEqual((rc, "state=unobservable" in out), (3, True), out)
        self.assertIn("cannot observe its target", err)

    def test_garbage_pidfile_is_blind_not_dead(self):
        self.pidfile("not-a-pid\n")
        rc, out, _ = self.observe(os.path.join(self.tmp, MARK + ".sh"))
        self.assertEqual((rc, "state=unobservable" in out), (3, True), out)

    def test_no_start_while_unobservable(self):
        """ensure_loops must refuse a start on unobservable: pidfile dead, a live exact-path holder."""
        wd = os.path.join(self.F, "ws58-keeper-watchdog.sh")
        with open(wd, "w") as f:
            f.write("#!/bin/bash\nsleep 60\n")
        os.chmod(wd, 0o755)
        self.proc = subprocess.Popen(["/bin/bash", wd])
        time.sleep(0.3)
        dead = subprocess.Popen(["/bin/true"]); dead.wait()
        self.pidfile("")
        with open(os.path.join(self.F, "ws58-keeper-watchdog.pid"), "w") as f:
            f.write(f"{dead.pid}\n")
        env = dict(os.environ, CHURN_FLAGS=self.F, CHURN_SHADOW_OUT=os.path.join(self.F, "shadow"),
                   CHURN_TMUX_SESSION="churn-test-absent", OG_STATE_DIR=os.path.join(self.tmp, "alerts"))
        out = subprocess.run(["bash", CU, "--dry-run"], env=env, capture_output=True, text=True, timeout=120).stdout
        self.assertIn("watchdog: OBSERVATION BLIND or channels disagree", out)
        self.assertNotIn(f"START bash {wd}", out)


if __name__ == "__main__":
    unittest.main()
