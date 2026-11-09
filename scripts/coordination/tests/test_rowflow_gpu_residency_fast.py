#!/usr/bin/env python3
"""Fast GPU residency: only this smoke's own process tree counts, above the floor, however short the job."""
import os
import shutil
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "rowflow"))
import rowflow as rf  # noqa: E402

JOB, FOREIGN = 5001, 5002
MB = 1 << 20


class T(unittest.TestCase):
    def setUp(self):
        self.kfd = tempfile.mkdtemp(prefix="res-")
        p = mock.patch.object(rf, "KFD_PROC", self.kfd)
        p.start()
        self.addCleanup(p.stop)
        self.addCleanup(shutil.rmtree, self.kfd, True)
        p = mock.patch.object(rf, "harness_tree", lambda root, tracked: tracked.setdefault(JOB, "1"))
        p.start()
        self.addCleanup(p.stop)

    def client(self, pid, b):
        os.makedirs(os.path.join(self.kfd, str(pid)), exist_ok=True)
        open(os.path.join(self.kfd, str(pid), "vram_0"), "w").write(str(b))

    def gone(self, pid):
        shutil.rmtree(os.path.join(self.kfd, str(pid)), ignore_errors=True)

    def peak(self):
        tracked, own = {}, {}
        rf.gpu_sample_window(1, tracked, own, n=6, interval=0.05)
        return rf.own_vram_peak(own), own

    def test_cpu_only_run_has_no_proof(self):
        self.assertEqual(self.peak()[0], 0)

    def test_foreign_vram_does_not_count(self):
        self.client(FOREIGN, 8 << 30)
        self.assertEqual(self.peak()[0], 0)

    def test_noop_13mb_is_below_floor(self):
        self.client(JOB, 13 * MB)
        self.assertLess(self.peak()[0], rf.RESIDENCY_FLOOR_B)

    def test_short_real_job_is_caught_and_kept_after_exit(self):
        def job():
            time.sleep(0.05)
            self.client(JOB, 4500 * MB)
            time.sleep(0.15)
            self.gone(JOB)
        t = threading.Thread(target=job)
        t.start()
        got, own = self.peak()
        t.join()
        self.assertEqual(got, 4500 * MB)
        self.assertEqual(own, {JOB: 4500 * MB})

    def test_long_job_keeps_peak(self):
        self.client(JOB, 2 << 30)
        tracked, own = {}, {}
        rf.sample_gpu_residency(1, tracked, own)
        self.client(JOB, 1 << 30)
        rf.sample_gpu_residency(1, tracked, own)
        self.assertEqual(rf.own_vram_peak(own), 2 << 30)


if __name__ == "__main__":
    unittest.main()
