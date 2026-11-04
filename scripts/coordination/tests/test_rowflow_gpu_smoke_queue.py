#!/usr/bin/env python3
"""Operator 2026-11-02: a GPU smoke never loads the MI210 while a GPU job runs; it is QUEUED and the allocator runs the
queue as one detached batch in the next GPU gap, before any GPU grant."""
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


class GpuQueueTests(unittest.TestCase):
    def setUp(self):
        self.flags = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.flags, "ready"))
        self.rid = "g1"

    def _publish(self, spec, flags, source=None):
        rf.atomic_json(rf.ready_path(flags, self.rid), {"id": self.rid})
        return {"id": self.rid}

    def _go(self, busy, verdict="PASS"):
        calls = []

        def dry(flags, rid, regions, one_quarter=False, smoke_s=None):
            calls.append((rid, regions))
            return verdict, "m"
        with mock.patch.object(rf, "publish", self._publish), mock.patch.object(rf, "dryrun_run", dry), \
                mock.patch.object(pr, "gpu_busy", return_value=busy), mock.patch.object(rf, "tail", return_value=[]):
            row = pr.publish_smoked({"lane": "gpu", "regions": "mi210_0,184-191"}, self.flags, "t")
        return row, calls

    def test_free_gpu_runs_now(self):
        row, calls = self._go(False)
        self.assertEqual(row["id"], self.rid)
        self.assertEqual(calls, [(self.rid, "mi210_0,184-191")])

    def test_busy_gpu_queues_without_failure_or_manifest(self):
        row, calls = self._go(True)
        self.assertIsNone(row)
        self.assertEqual(calls, [])
        q = rf.load_json(pr.queued_path(self.flags, self.rid))
        self.assertEqual(q["regions"], "mi210_0,184-191")
        self.assertFalse(os.path.exists(rf.ready_path(self.flags, self.rid)))
        self.assertFalse(rf.fail_paths(self.flags, self.rid))
        # the batch restores the manifest, runs the smoke, removes QUEUED
        with mock.patch.object(rf, "dryrun_run", return_value=("PASS", "ok")) as d:
            self.assertEqual(pr.run_gpu_queue(self.flags), 1)
        d.assert_called_once()
        self.assertTrue(os.path.exists(rf.ready_path(self.flags, self.rid)))
        self.assertFalse(os.path.exists(pr.queued_path(self.flags, self.rid)))

    def test_batch_fail_unpublishes(self):
        self._go(True)
        with mock.patch.object(rf, "dryrun_run", return_value=("FAIL", "bad")):
            pr.run_gpu_queue(self.flags)
        self.assertFalse(os.path.exists(rf.ready_path(self.flags, self.rid)))
        self.assertTrue(os.path.exists(pr.unpublished_path(self.flags, self.rid)))

    def test_gpu_busy_sources(self):
        with mock.patch.object(rf, "rl_status", return_value={rf.GPU: ("HELD", "x")}):
            self.assertTrue(pr.gpu_busy(self.flags))
        with mock.patch.object(rf, "rl_status", return_value={}), \
                mock.patch.object(rf, "open_grants", return_value=[{"holds": {rf.GPU}}]):
            self.assertTrue(pr.gpu_busy(self.flags))
        with mock.patch.object(rf, "rl_status", return_value={}), mock.patch.object(rf, "open_grants", return_value=[]):
            self.assertFalse(pr.gpu_busy(self.flags))

    def test_allocator_batch_lock(self):
        logs = []
        self.assertFalse(rf.start_gpu_batch(self.flags, logs.append))  # nothing queued
        rf.atomic_json(rf.gpu_batch_lock(self.flags), {"pid": os.getpid()})
        self.assertTrue(rf.start_gpu_batch(self.flags, logs.append))  # live batch owns the GPU
        rf.atomic_json(rf.gpu_batch_lock(self.flags), {"pid": 2 ** 22 + 7})
        self.assertFalse(rf.gpu_batch_running(self.flags))  # dead lock cleared
        self.assertFalse(os.path.exists(rf.gpu_batch_lock(self.flags)))
        os.makedirs(rf.dry_dir(self.flags, "q1"))
        rf.atomic_json(os.path.join(rf.dry_dir(self.flags, "q1"), "GPU-SMOKE-QUEUED.json"), {})
        with mock.patch.object(rf.subprocess, "Popen") as P:
            P.return_value.pid = os.getpid()
            self.assertTrue(rf.start_gpu_batch(self.flags, logs.append))
        self.assertIn("--run-gpu-queue", P.call_args[0][0])
        self.assertEqual(json.load(open(rf.gpu_batch_lock(self.flags)))["pid"], os.getpid())


if __name__ == "__main__":
    unittest.main()
