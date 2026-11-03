"""ws58 2026-11-02: the dry-run/smoke harness reaps every process it started (own group, setsid'd grandchildren) on
PASS/FAIL/timeout; nothing is left for the operator. 2026-11-03 (session review): it reaps ONLY tracked descendants -
the id-substring/cwd sweep (row_dir_procs) is deleted; a process that merely names the row id is never signalled."""
import os
import subprocess
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rowflow"))
import rowflow as rf  # noqa: E402


def _alive(pid):
    return rf._proc_stat(pid) is not None


class ReapTest(unittest.TestCase):
    def test_detached_grandchild_does_not_survive(self):
        rid = "ws58-reap-test-%d" % os.getpid()
        with tempfile.TemporaryDirectory() as td:
            pidf = os.path.join(td, "pids")
            lp = os.path.join(td, "launcher.sh")
            # a private-engine-style launcher: a setsid'd grandchild (own session, not naming the row), a nohup'd detached
            # one naming the row id, and the launcher itself blocking like a long GPU benchmark
            with open(lp, "w") as f:
                f.write("#!/bin/bash\n"
                        f"setsid bash -c 'sleep 600 & echo $! >> {pidf}; wait' </dev/null >/dev/null 2>&1 &\n"
                        f"setsid nohup bash -c 'exec -a {rid}-job sleep 600' </dev/null >/dev/null 2>&1 & echo $! >> {pidf}\n"
                        "sleep 600\n")
            p = subprocess.Popen(["bash", lp], start_new_session=True)
            tracked = {p.pid: rf._proc_stat(p.pid)[2]}
            for _ in range(20):
                time.sleep(0.25)
                rf.harness_tree(p.pid, tracked)
            spawned = [int(x) for x in open(pidf).read().split()]
            self.assertEqual(len(spawned), 2)
            reaped, surv = rf.reap_pids(tracked, grace=5)
            p.wait(timeout=10)
            self.assertEqual(surv, [])
            time.sleep(0.5)
            for pid in spawned + [p.pid]:
                self.assertFalse(_alive(pid), f"pid {pid} survived")

    def test_id_substring_reaper_is_gone(self):
        # 2026-11-03: the argv/cwd sweep killed the publisher's own shells (exit 144 x3) and an armed sibling launcher (rc=143)
        self.assertFalse(hasattr(rf, "row_dir_procs"))
        self.assertFalse(hasattr(rf, "_owned_by_other_row"))

    def test_foreign_process_naming_the_row_id_survives_the_reap(self):
        rid = "ws58-foreign-%d" % os.getpid()
        # a process that is NOT a descendant of the dry run but names the row id in its argv (an operator shell, another
        # session's tool, a sibling launcher) must survive: ownership is pid + start time, never a name
        foreign = subprocess.Popen(["bash", "-c", "sleep 30; true", "x", rid + "-foreign"], start_new_session=True)  # ; true: no exec-optimisation
        with tempfile.TemporaryDirectory() as td:
            lp = os.path.join(td, "launcher.sh")
            with open(lp, "w") as f:
                f.write("#!/bin/bash\nsleep 600\n")
            run = subprocess.Popen(["bash", lp], start_new_session=True)
            try:
                tracked = {run.pid: rf._proc_stat(run.pid)[2]}
                for _ in range(4):
                    time.sleep(0.25)
                    rf.harness_tree(run.pid, tracked)
                self.assertNotIn(foreign.pid, tracked)
                self.assertIn(foreign.pid, rf.row_orphans(rid))   # reported read-only
                reaped, surv = rf.reap_pids(tracked, grace=5)
                run.wait(timeout=10)
                self.assertEqual(surv, [])
                self.assertTrue(_alive(foreign.pid), "foreign process naming the row id was killed")
            finally:
                foreign.terminate()
                foreign.wait(timeout=10)


if __name__ == "__main__":
    unittest.main()
