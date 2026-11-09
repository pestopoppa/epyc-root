#!/usr/bin/env python3
"""churn_up.sh dry-run only (temp flags): the watchdog guard and core.bare watcher are started once and never duplicated."""
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

_TESTS = os.path.dirname(os.path.abspath(__file__))
CU = os.path.join(os.path.dirname(_TESTS), "churn", "churn_up.sh")


class Tests(unittest.TestCase):
    def setUp(self):
        self.F = tempfile.mkdtemp(prefix="cus-")
        self.kids = []
        self.env = dict(os.environ, CHURN_FLAGS=self.F, CHURN_SHADOW_OUT=os.path.join(self.F, "shadow"), CHURN_TMUX_SESSION="churn-test-absent")

    def tearDown(self):
        for k in self.kids:   # pids this test started and captured
            k.terminate()
            k.wait(timeout=10)
        shutil.rmtree(self.F, ignore_errors=True)

    def run_cu(self, *a):
        return subprocess.run(["bash", CU, *a], env=self.env, capture_output=True, text=True, timeout=120).stdout

    def holder(self, *argv):
        """A live process whose argv carries the given elements, like the real component would."""
        k = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)", *argv])
        self.kids.append(k)
        time.sleep(0.3)
        return k.pid

    def test_bringup_starts_guard_and_watcher_when_absent(self):
        out = self.run_cu("--dry-run")
        self.assertIn("--supervise-watchdog", out)
        self.assertRegex(out, r"START python3 -I \S+watch_git_config\.py")

    def test_running_watcher_not_duplicated(self):
        path = os.path.join(self.F, "bin", "watch_git_config.py")
        self.holder(path)
        out = self.run_cu("--dry-run")
        self.assertIn("NOT starting a duplicate", out)
        self.assertNotRegex(out, r"START python3 -I \S+watch_git_config\.py")

    def test_supervise_starts_absent_watchdog_only(self):
        wd = os.path.join(self.F, "ws58-keeper-watchdog.sh")
        open(wd, "w").write("#!/bin/bash\n")
        out = self.run_cu("--supervise-watchdog", "--dry-run")
        self.assertIn(f"START bash {wd}", out)
        self.assertNotIn("ws58-calendar-keeper-v", out)

    def test_supervise_never_duplicates_live_watchdog(self):
        wd = os.path.join(self.F, "ws58-keeper-watchdog.sh")
        open(wd, "w").write("#!/bin/bash\n")
        self.holder(wd)   # alive by exact argv, no pidfile
        self.assertNotIn("START", self.run_cu("--supervise-watchdog", "--dry-run"))
        pid = self.holder(wd)   # alive by pidfile + argv marker
        open(os.path.join(self.F, "ws58-keeper-watchdog.pid"), "w").write(f"{pid}\n")
        self.assertNotIn("START", self.run_cu("--supervise-watchdog", "--dry-run"))

    def test_existing_guard_blocks_second_guard(self):
        self.holder(CU, "--supervise-watchdog")
        out = self.run_cu("--dry-run")
        self.assertIn("watchdog-guard: running pid(s)", out)
        self.assertNotIn(f"START bash {CU} --supervise-watchdog", out)

    def test_concurrent_status_is_not_a_guard(self):
        self.holder(CU, "--status")
        self.assertIn(f"START bash {CU} --supervise-watchdog", self.run_cu("--dry-run"))

    def test_stop_stops_guard_before_watchdog(self):
        g = self.holder(CU, "--supervise-watchdog")
        wd = os.path.join(self.F, "ws58-keeper-watchdog.sh")
        w2 = self.holder(wd)
        out = self.run_cu("--stop", "--dry-run")
        self.assertLess(out.index(f"STOP watchdog-guard pid {g}"), out.index(f"STOP watchdog pid {w2}"))


if __name__ == "__main__":
    unittest.main()
