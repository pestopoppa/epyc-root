#!/usr/bin/env python3
"""PIPE-EVE-CHURN-UP-PIDFILE: start_bg must record the component's own pid, not a wrapper subshell's.

Uses temp flags and a fake disk_janitor.sh that records $$ and exits by itself after a few seconds (nothing is killed)."""
import os
import shutil
import subprocess
import tempfile
import time
import unittest

_TESTS = os.path.dirname(os.path.abspath(__file__))
CU = os.path.join(os.path.dirname(_TESTS), "churn", "churn_up.sh")


class Tests(unittest.TestCase):
    def setUp(self):
        self.F = tempfile.mkdtemp(prefix="cupf-")

    def tearDown(self):
        time.sleep(4)  # the fake component exits on its own
        shutil.rmtree(self.F, ignore_errors=True)

    def test_pidfile_is_component_pid(self):
        with open(os.path.join(self.F, "disk_janitor.sh"), "w") as f:
            f.write('#!/bin/bash\necho $$ > "$(dirname "$0")/self.pid"\nsleep 3\n')
        env = dict(os.environ, CHURN_FLAGS=self.F, CHURN_SHADOW_OUT=os.path.join(self.F, "shadow"),
                   CHURN_TMUX_SESSION="churn-test-absent")
        out = subprocess.run(["bash", CU, "--janitor=start"], env=env, capture_output=True, text=True, timeout=60).stdout
        self.assertIn("START bash", out)
        recorded = open(os.path.join(self.F, "disk-janitor.pid")).read().strip()
        own = open(os.path.join(self.F, "self.pid")).read().strip()
        self.assertEqual(recorded, own, out)
        self.assertFalse([n for n in os.listdir(self.F) if ".tmp." in n])


if __name__ == "__main__":
    unittest.main()
