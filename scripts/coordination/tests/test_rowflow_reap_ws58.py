"""ws58 2026-11-02: the dry-run/smoke harness reaps every process it started (own group, setsid'd grandchildren, detached
processes naming the row) on PASS/FAIL/timeout; nothing is left for the operator."""
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
            left = rf.row_dir_procs(rid, [td])
            r2, s2 = rf.reap_pids(left, grace=5)
            self.assertEqual(s2, [])
            time.sleep(0.5)
            for pid in spawned + [p.pid]:
                self.assertFalse(_alive(pid), f"pid {pid} survived")
            self.assertEqual(rf.row_dir_procs(rid, [td]), {})

    def test_shared_workdir_never_matches_by_cwd(self):
        self.assertEqual(rf.row_dir_procs("q" + os.urandom(8).hex(), ["/workspace", "/"]), {})


if __name__ == "__main__":
    unittest.main()
