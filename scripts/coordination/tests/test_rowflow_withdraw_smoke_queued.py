#!/usr/bin/env python3
"""withdraw() of a GPU row that exists only as dryrun/<id>/GPU-SMOKE-QUEUED.json (+ unpublished.json), no ready manifest
(real case c14-fold-gpu-20261118). Temp dirs only; nothing live is touched."""
import json
import os
import sys
import unittest
from unittest import mock

_HERE = os.path.dirname(os.path.abspath(__file__))
_RF = os.path.join(os.path.dirname(_HERE), "rowflow")
sys.path.insert(0, _RF)
import publish_row as pr  # noqa: E402
import rowflow as rf  # noqa: E402
sys.path.insert(0, _HERE)
from test_rowflow_shape_evidence import Fx  # noqa: E402

NOLOG = lambda *_: None  # noqa: E731
RID = "c14-fold-gpu-20261118"


class WithdrawSmokeQueued(Fx):
    def queue(self, rid=RID):
        d = rf.dry_dir(self.flags, rid)
        os.makedirs(d, exist_ok=True)
        json.dump({"id": rid, "smoke_s": 300}, open(os.path.join(d, "GPU-SMOKE-QUEUED.json"), "w"))
        json.dump({"id": rid, "lane": "gpu"}, open(os.path.join(d, "unpublished.json"), "w"))
        return d

    def ended(self, rid=RID):
        p = os.path.join(self.flags, "grants", rid + ".ended")
        return open(p).read() if os.path.exists(p) else None

    def test_queued_not_running_withdrawn(self):
        d = self.queue()
        logs = []
        with mock.patch.object(rf, "gpu_batch_running", return_value=False):
            self.assertEqual(rf.withdraw(self.flags, RID, "superseded-by:x", logs.append), "WITHDRAWN")
        self.assertFalse(os.path.exists(os.path.join(d, "GPU-SMOKE-QUEUED.json")))
        self.assertTrue(os.path.exists(os.path.join(d, ".withdrawn", "GPU-SMOKE-QUEUED.json")))
        self.assertIn("rc=75 reason=superseded-by:x", self.ended())
        self.assertTrue(any("WITHDRAWN-SMOKE-QUEUED" in m for m in logs))
        self.assertFalse(os.path.exists(rf.withdraw_pending_path(self.flags, RID)))

    def test_queued_running_pending_then_finished(self):
        d = self.queue()
        json.dump({"pid": os.getpid(), "started": rf.now_iso()}, open(rf.running_path(self.flags, RID), "w"))
        with mock.patch.object(rf, "gpu_batch_running", return_value=False):
            self.assertEqual(rf.withdraw(self.flags, RID, "superseded-by:x", NOLOG), "PENDING")
            self.assertTrue(os.path.exists(rf.withdraw_pending_path(self.flags, RID)))
            self.assertIsNone(self.ended())
            self.assertTrue(os.path.exists(os.path.join(d, "GPU-SMOKE-QUEUED.json")))
            # smoke ends without PASS: batch removes the marker, manifest stays unpublished; keeper finishes it
            os.remove(rf.running_path(self.flags, RID))
            os.remove(os.path.join(d, "GPU-SMOKE-QUEUED.json"))
            rf.finish_withdrawals(self.flags, log=NOLOG)
        self.assertIn("rc=75 reason=superseded-by:x", self.ended())
        self.assertFalse(os.path.exists(rf.withdraw_pending_path(self.flags, RID)))
        self.assertTrue(os.path.exists(os.path.join(rf.withdrawn_dir(self.flags), RID + ".done.json")))

    def test_cpu_queued_withdrawn_even_if_gpu_batch_alive(self):
        d = self.queue()
        os.rename(os.path.join(d, "GPU-SMOKE-QUEUED.json"), os.path.join(d, "SMOKE-QUEUED.json"))
        with mock.patch.object(rf, "gpu_batch_running", return_value=True):
            self.assertEqual(rf.withdraw(self.flags, RID, "owner", NOLOG), "WITHDRAWN")
        self.assertFalse(os.path.exists(os.path.join(d, "SMOKE-QUEUED.json")))
        self.assertTrue(os.path.exists(os.path.join(d, ".withdrawn", "SMOKE-QUEUED.json")))
        self.assertTrue(os.path.exists(os.path.join(d, "unpublished.json")))
        self.assertIn("rc=75 reason=owner", self.ended())

    def test_cpu_running_pending_then_finished(self):
        for marker in ("SMOKE-PLACED.json", "RUNNING.json"):
            with self.subTest(marker=marker):
                rid = RID + marker
                d = self.queue(rid)
                q = os.path.join(d, "SMOKE-QUEUED.json")
                os.rename(os.path.join(d, "GPU-SMOKE-QUEUED.json"), q)
                runner = os.path.join(d, marker)
                json.dump({"pid": os.getpid()}, open(runner, "w"))
                with mock.patch.object(rf, "gpu_batch_running", return_value=True):
                    self.assertEqual(rf.withdraw(self.flags, rid, "owner", NOLOG), "PENDING")
                    rf.finish_withdrawals(self.flags, log=NOLOG)
                    self.assertIsNone(self.ended(rid))
                    os.remove(runner)
                    rf.finish_withdrawals(self.flags, log=NOLOG)
                self.assertIn("rc=75 reason=owner", self.ended(rid))
                self.assertTrue(os.path.exists(os.path.join(d, ".withdrawn", "SMOKE-QUEUED.json")))
                self.assertTrue(os.path.exists(os.path.join(rf.withdrawn_dir(self.flags), rid + ".done.json")))

    def test_cpu_running_without_queue_marker_finishes(self):
        d = self.queue()
        os.remove(os.path.join(d, "GPU-SMOKE-QUEUED.json"))
        runner = os.path.join(d, "SMOKE-PLACED.json")
        json.dump({"pid": os.getpid()}, open(runner, "w"))
        with mock.patch.object(rf, "gpu_batch_running", return_value=True):
            self.assertEqual(rf.withdraw(self.flags, RID, "owner", NOLOG), "PENDING")
            os.remove(runner)
            rf.finish_withdrawals(self.flags, log=NOLOG)
        self.assertIn("rc=75 reason=owner", self.ended())

    def test_batch_alive_counts_as_running(self):
        self.queue()
        with mock.patch.object(rf, "gpu_batch_running", return_value=True):
            self.assertEqual(rf.withdraw(self.flags, RID, "x", NOLOG), "PENDING")

    def test_neither_absent(self):
        with mock.patch.object(rf, "gpu_batch_running", return_value=False):
            self.assertEqual(rf.withdraw(self.flags, "nope", "x", NOLOG), "ABSENT")
        self.assertIsNone(self.ended("nope"))

    def test_pass_does_not_publish_withdrawn_pending(self):
        d = self.queue()
        os.makedirs(rf.withdrawn_dir(self.flags), exist_ok=True)

        def smoke(flags, rid, regions, s):   # withdrawal lands during the smoke
            json.dump({"id": rid, "reason": "x"}, open(rf.withdraw_pending_path(flags, rid), "w"))
            return "PASS", "ok"
        with mock.patch.object(pr, "run_smoke", side_effect=smoke), \
                mock.patch.object(pr, "file_if_complete") as fic, mock.patch.object(pr, "alert_queued_nonpass") as al:
            pr.run_gpu_queue(self.flags)
        fic.assert_not_called(); al.assert_not_called()
        self.assertFalse(os.path.exists(rf.ready_path(self.flags, RID)))
        self.assertTrue(os.path.exists(os.path.join(d, "unpublished.json")))
        with mock.patch.object(rf, "gpu_batch_running", return_value=False):
            rf.finish_withdrawals(self.flags, log=NOLOG)
        self.assertIn("rc=75", self.ended())

    def test_batch_skips_withdrawn_pending_before_smoke(self):
        self.queue()
        os.makedirs(rf.withdrawn_dir(self.flags), exist_ok=True)
        json.dump({"id": RID, "reason": "x"}, open(rf.withdraw_pending_path(self.flags, RID), "w"))
        with mock.patch.object(pr, "run_smoke") as rs:
            pr.run_gpu_queue(self.flags)
        rs.assert_not_called()
        self.assertFalse(os.path.exists(rf.ready_path(self.flags, RID)))


if __name__ == "__main__":
    unittest.main()
