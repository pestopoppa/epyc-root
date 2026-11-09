#!/usr/bin/env python3
"""publish_smoked refuses a republish while the id's own smoke is in flight; stale records never block."""
import datetime as dt
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "rowflow"))
import publish_row as pr  # noqa: E402
import rowflow as rf  # noqa: E402

RID = "row-a-20261109"
DEAD = 4194399   # above pid_max: never a live process


def iso(delta):
    return (dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=delta)).strftime("%Y-%m-%dT%H:%M:%SZ")


class Tests(unittest.TestCase):
    def setUp(self):
        self.flags = tempfile.mkdtemp(prefix="psif-")
        os.makedirs(rf.dry_dir(self.flags, RID))

    def rec(self, path, **kw):
        json.dump(kw, open(path, "w"))

    def publish(self):
        """Stop right after the guard: the sentinel proves rf.publish was reached."""
        with mock.patch.object(pr.rf, "publish", side_effect=SystemError("reached publish")) as m:
            try:
                pr.publish_smoked({"id": RID, "lane": "cpu"}, self.flags, "src")
            except SystemError:
                pass
            return m

    def test_live_running_refused_before_publish(self):
        self.rec(rf.running_path(self.flags, RID), pid=os.getpid(), deadline=iso(600), started=iso(-5))
        with mock.patch.object(pr.rf, "publish") as m, self.assertRaises(rf.Refused) as cm:
            pr.publish_smoked({"id": RID, "lane": "cpu"}, self.flags, "src")
        m.assert_not_called()
        self.assertIn("in flight", str(cm.exception))

    def test_dead_running_does_not_block(self):
        self.rec(rf.running_path(self.flags, RID), pid=DEAD, deadline=iso(600))
        self.assertTrue(self.publish().called)

    def test_past_deadline_running_does_not_block(self):
        self.rec(rf.running_path(self.flags, RID), pid=os.getpid(), deadline=iso(-rf.DRYRUN_DEADLINE_GRACE_S - 60))
        self.assertTrue(self.publish().called)

    def test_live_placed_runner_refused(self):
        self.rec(rf.smoke_placed_path(self.flags, RID), pid=os.getpid(), at=iso(-1))
        with mock.patch.object(pr, "pid_argv", return_value=f"python3 publish_row.py --run-smoke {RID} --regions 0-3"):
            with self.assertRaises(rf.Refused):
                pr.publish_smoked({"id": RID, "lane": "cpu"}, self.flags, "src")

    def test_dead_placed_does_not_block(self):
        self.rec(rf.smoke_placed_path(self.flags, RID), pid=DEAD, at=iso(-1))
        self.assertTrue(self.publish().called)

    def test_recycled_placed_pid_does_not_block(self):
        self.rec(rf.smoke_placed_path(self.flags, RID), pid=os.getpid(), at=iso(-1))
        with mock.patch.object(pr, "pid_argv", return_value="sshd: something unrelated"):
            self.assertTrue(self.publish().called)

    def test_other_rows_smoke_does_not_block(self):
        other = "row-b-20261109"
        os.makedirs(rf.dry_dir(self.flags, other))
        self.rec(rf.running_path(self.flags, other), pid=os.getpid(), deadline=iso(600))
        self.assertTrue(self.publish().called)

    def test_allocator_runner_path_has_no_guard(self):
        """The keeper's --run-smoke and GPU batch go through run_smoke, never publish_smoked."""
        with mock.patch.object(pr.rf, "dryrun_run", return_value=("PASS", "ok")):
            self.rec(rf.running_path(self.flags, RID), pid=os.getpid(), deadline=iso(600))
            self.assertEqual(pr.run_smoke(self.flags, RID, "0-3", 60)[0], "PASS")


if __name__ == "__main__":
    unittest.main()
