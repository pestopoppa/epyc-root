#!/usr/bin/env python3
"""LOOP-11: a parked or replaced poller is stopped only when proven to be this row's and job-free. Uses throwaway processes."""
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "rowflow"))
import rowflow as rf  # noqa: E402

RID = "row-a"
NOLOG = lambda *_: None  # noqa: E731


class T(unittest.TestCase):
    def setUp(self):
        self.flags = tempfile.mkdtemp(prefix="l11-")
        os.makedirs(os.path.join(self.flags, "grants"))
        os.makedirs(rf.dry_dir(self.flags, RID))
        self.lp = os.path.join(self.flags, "launch.sh")
        self.d = {"launcher": {"path": self.lp}}
        self.groups = []

    def tearDown(self):
        for g in self.groups:
            for q in rf.tree_pids(g):
                try:
                    os.kill(q, signal.SIGKILL)
                except OSError:
                    pass
        shutil.rmtree(self.flags, ignore_errors=True)

    def poller(self, body="sleep 300 & wait\n"):
        open(self.lp, "w").write("#!/bin/bash\n" + body)
        p = subprocess.Popen(["bash", self.lp], start_new_session=True, stdout=subprocess.DEVNULL)
        self.p = p
        self.groups.append(p.pid)
        time.sleep(0.5)
        return p.pid

    def dead(self, pid):
        self.p.poll()
        return not rf.proc_alive(pid)

    def test_parked_refusal_stops(self):
        pid = self.poller()
        self.assertEqual(rf.stop_poller_if_parked(self.flags, RID, self.d, pid, "x", rf.MAX_FAILS, NOLOG), "stopped")
        self.assertTrue(self.dead(pid))
        self.assertFalse(os.path.exists(os.path.join(self.flags, "grants", RID + ".ended")))

    def test_precond_refusal_stops_on_first(self):
        pid = self.poller()
        self.assertEqual(rf.stop_poller_if_parked(self.flags, RID, self.d, pid, rf._PRECOND_REFUSED, 1, NOLOG), "stopped")

    def test_transient_refusal_leaves_it(self):
        pid = self.poller()
        self.assertIsNone(rf.stop_poller_if_parked(self.flags, RID, self.d, pid, "window too short", 1, NOLOG))
        self.assertFalse(self.dead(pid))

    def test_rearm_replacement_leaves_no_old_poller(self):
        pid = self.poller()
        self.assertEqual(rf.stop_row_poller(self.flags, RID, self.d, pid, NOLOG), "stopped")
        self.assertEqual(rf.tree_pids(pid), set())

    def test_recycled_pid_untouched(self):
        pid = self.poller()
        other = {"launcher": {"path": "/nonexistent/other.sh"}}
        self.assertEqual(rf.stop_row_poller(self.flags, RID, other, pid, NOLOG), "not-ours")
        self.assertFalse(self.dead(pid))

    def test_setsid_job_untouched(self):
        pid = self.poller("setsid sleep 300 &\nwait\nsleep 300\n")
        kids = rf.tree_pids(pid) - {pid}
        self.assertTrue(kids)
        self.assertEqual(rf.stop_row_poller(self.flags, RID, self.d, pid, NOLOG), "job")
        self.assertFalse(self.dead(pid))
        self.assertTrue(all(rf.proc_alive(k) for k in kids))

    def test_open_grant_untouched(self):
        pid = self.poller()
        open(os.path.join(self.flags, "grants", RID + ".grant"), "w").close()
        self.assertEqual(rf.stop_row_poller(self.flags, RID, self.d, pid, NOLOG), "job")
        self.assertFalse(self.dead(pid))

    def test_live_smoke_untouched(self):
        pid = self.poller()
        open(rf.running_path(self.flags, RID), "w").write("{}")
        self.assertEqual(rf.stop_row_poller(self.flags, RID, self.d, pid, NOLOG), "job")

    def test_members_killed_after_leader_exits_and_tick_bounded(self):
        pid = self.poller("trap '' TERM\nsleep 300 &\ntrap 'exit 0' TERM\nwait\n")
        t0 = time.time()
        self.assertEqual(rf.stop_row_poller(self.flags, RID, self.d, pid, NOLOG), "stopped")
        self.assertLess(time.time() - t0, 3)
        self.assertEqual(rf.tree_pids(pid), set())

    def test_term_ignoring_group_still_goes_within_bound(self):
        pid = self.poller("trap '' TERM\nwhile :; do sleep 1; done\n")
        t0 = time.time()
        self.assertEqual(rf.stop_row_poller(self.flags, RID, self.d, pid, NOLOG), "stopped")
        self.assertLess(time.time() - t0, 3)

    def test_vanished_member_is_not_foreign(self):
        pid = self.poller()
        real = rf.tree_pids
        with mock.patch.object(rf, "tree_pids", side_effect=[real(pid) | {4194399}, set()]), mock.patch.object(rf, "stop_group_bounded", return_value=True) as k:
            self.assertEqual(rf.stop_row_poller(self.flags, RID, self.d, pid, NOLOG), "stopped")
        k.assert_called_once()

    def test_vanished_poller_is_gone(self):
        self.assertIn(rf.stop_row_poller(self.flags, RID, self.d, 4194399, NOLOG), ("gone", "not-ours"))

    def test_shared_group_is_not_ours(self):
        open(self.lp, "w").write("#!/bin/bash\nsleep 300\n")
        p = subprocess.Popen(["bash", self.lp])   # keeps the test's own group
        self.p = p
        try:
            time.sleep(0.3)
            self.assertEqual(rf.stop_row_poller(self.flags, RID, self.d, p.pid, NOLOG), "not-ours")
            self.assertIsNone(p.poll())
        finally:
            for q in rf.tree_pids(p.pid) if False else [p.pid]:
                p.kill()
            p.wait()


if __name__ == "__main__":
    unittest.main()
