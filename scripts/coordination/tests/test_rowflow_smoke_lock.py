#!/usr/bin/env python3
"""F2 (AK audit B2): one smoke runner per row id. A concurrent dryrun_run waits on dryrun/<id>/SMOKE.lock and returns
the verdict the running smoke recorded; a concurrent publish is refused naming the lock holder; the row stays ready."""
import json
import os
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "rowflow"))
import publish_row as pr  # noqa: E402
import rowflow as rf  # noqa: E402

RID = "row-lock-20261120"


class SmokeLock(unittest.TestCase):
    def setUp(self):
        self.flags = tempfile.mkdtemp(prefix="smklock-")
        os.makedirs(os.path.join(self.flags, "ready"))
        self.ready = rf.ready_path(self.flags, RID)
        json.dump({"id": RID}, open(self.ready, "w"))
        self.calls = 0
        self.started = threading.Event()

    def fake_smoke(self, flags, rid, regions, one_quarter=False, smoke_s=None):
        self.calls += 1
        self.started.set()
        time.sleep(1.5)   # the fixture "60 s" smoke, shortened
        rf.atomic_json(rf.pass_path(flags, rid), {"id": rid, "passed_at": rf.now_iso()})
        return "PASS", "first progress"

    def test_second_runner_returns_recorded_verdict(self):
        out = {}
        logs = []
        with mock.patch.object(rf, "_dryrun_run_locked", side_effect=self.fake_smoke):
            t = threading.Thread(target=lambda: out.setdefault("a", rf.dryrun_run(self.flags, RID, "0-3", smoke_s=60)))
            t.start()
            self.assertTrue(self.started.wait(5))
            self.assertIsNotNone(rf.smoke_lock_holder(self.flags, RID))
            b = rf.dryrun_run(self.flags, RID, "4-7", smoke_s=60, log=logs.append)
            t.join()
        self.assertEqual(self.calls, 1)
        self.assertEqual(out["a"][0], "PASS")
        self.assertEqual(b[0], "PASS")
        self.assertTrue(any("smoke in progress by pid" in m for m in logs), logs)
        self.assertEqual(len([f for f in os.listdir(rf.dry_dir(self.flags, RID)) if f == "PASS.json"]), 1)
        self.assertIsNone(rf.smoke_lock_holder(self.flags, RID))

    def test_wait_bounded_returns_wait(self):
        with mock.patch.object(rf, "_dryrun_run_locked", side_effect=self.fake_smoke):
            t = threading.Thread(target=lambda: rf.dryrun_run(self.flags, RID, "0-3", smoke_s=60))
            t.start()
            self.assertTrue(self.started.wait(5))
            v, msg = rf.dryrun_run(self.flags, RID, "4-7", smoke_s=60, wait_s=0, log=lambda m: None)
            t.join()
        self.assertEqual(v, "WAIT")
        self.assertIn("not run twice", msg)
        self.assertEqual(self.calls, 1)

    def test_concurrent_publish_refused_row_stays_ready(self):
        with mock.patch.object(rf, "_dryrun_run_locked", side_effect=self.fake_smoke):
            t = threading.Thread(target=lambda: pr.run_smoke(self.flags, RID, "0-3", 60))
            t.start()
            self.assertTrue(self.started.wait(5))
            with mock.patch.object(pr.rf, "publish") as pub, self.assertRaises(rf.Refused) as cm:
                pr.publish_smoked({"id": RID, "lane": "cpu"}, self.flags, "src")
            t.join()
        pub.assert_not_called()
        self.assertIn("SMOKE.lock held by pid", str(cm.exception))
        self.assertTrue(os.path.exists(self.ready))
        self.assertEqual(self.calls, 1)


if __name__ == "__main__":
    unittest.main()
