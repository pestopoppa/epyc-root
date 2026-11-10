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

    def containers(self, label="row-a", pid=6001, b=4 << 30, cid="a" * 64):
        self.client(pid, b)
        calls = []
        def lab(c):
            calls.append(c)
            return label
        tracked, own, seen = {}, {}, {}
        with mock.patch.object(rf, "pid_container_id", lambda q: cid if q == pid else None), mock.patch.object(rf, "docker_row_label", lab):
            rf.sample_gpu_residency(1, tracked, own, "row-a", seen)
            rf.sample_gpu_residency(1, tracked, own, "row-a", seen)
        self.assertEqual(len(calls), 1)   # one docker inspect per container
        return rf.own_vram_peak(own)

    def test_own_container_counts(self):
        self.assertEqual(self.containers(), 4 << 30)

    def test_other_rows_container_does_not_count(self):
        self.assertEqual(self.containers(label="row-b"), 0)

    def test_unlabelled_or_unreadable_container_does_not_count(self):
        self.assertEqual(self.containers(label=None), 0)
        self.gone(6001)
        self.assertEqual(self.containers(label="", cid="b" * 64), 0)

    def test_own_container_at_13mb_stays_below_floor(self):
        self.assertLess(self.containers(b=13 * MB), rf.RESIDENCY_FLOOR_B)

    def test_host_process_outside_any_container_does_not_count(self):
        self.client(FOREIGN, 8 << 30)
        own = {}
        with mock.patch.object(rf, "pid_container_id", return_value=None), mock.patch.object(rf, "docker_row_label") as lab:
            rf.sample_gpu_residency(1, {}, own, "row-a", {})
        lab.assert_not_called()
        self.assertEqual(own, {})

    def test_real_cgroup_shapes(self):
        cid = "a810a03e2d605b561f3cb5cf46f949f03b9ea82cfa75bf84fe0dee46c6d338cc"
        self.assertEqual(rf.cgroup_container_id(f"0::/../docker-{cid}.scope\n"), cid)   # as read on this host
        self.assertEqual(rf.cgroup_container_id(f"0::/docker/{cid}\n"), cid)
        self.assertIsNone(rf.cgroup_container_id("0::/\n"))
        self.assertIsNone(rf.cgroup_container_id("0::/user.slice/session-1.scope\n"))


class DetachedJobIdentity(unittest.TestCase):
    """A launcher detaches the job from the harness tree; FILLER_ID still identifies it."""

    def run_sample(self, filler_id):
        own = {}
        with mock.patch.object(rf, "harness_tree", side_effect=lambda r, t: t), \
             mock.patch.object(rf, "gpu_occupancy", return_value={"pids": {4242: 1 << 30}, "vram_used": 1 << 30}), \
             mock.patch.object(rf, "lineage_filler_id", return_value=filler_id), \
             mock.patch.object(rf, "pid_container_id", return_value=None):
            rf.sample_gpu_residency(1, {}, own, "row-a", {})
        return own

    def test_detached_job_counts(self):
        self.assertEqual(self.run_sample("row-a"), {4242: 1 << 30})

    def test_other_rows_job_does_not_count(self):
        self.assertEqual(self.run_sample("row-b"), {})

    def test_no_filler_id_does_not_count(self):
        self.assertEqual(self.run_sample(None), {})

    def test_cleaned_env_child_inherits_row_from_parent(self):
        import subprocess, sys, time
        code = ("import subprocess,sys,time;c=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'],env={'PATH':'/usr/bin'},"
                "start_new_session=True);print(c.pid,flush=True);time.sleep(30)")
        p = subprocess.Popen([sys.executable, "-c", code], env=dict(os.environ, FILLER_ID="row-lin"), stdout=subprocess.PIPE, text=True)
        try:
            child = int(p.stdout.readline())
            time.sleep(0.2)
            self.assertIsNone(rf.pid_filler_id(child))
            self.assertEqual(rf.lineage_filler_id(child), "row-lin")
        finally:
            p.kill(); p.wait()
            subprocess.run(["kill", str(child)], check=False)

    def test_reads_real_environ(self):
        import subprocess, sys, time
        p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"], env=dict(os.environ, FILLER_ID="row-env"))
        try:
            time.sleep(0.2)
            self.assertEqual(rf.pid_filler_id(p.pid), "row-env")
        finally:
            p.kill(); p.wait()


if __name__ == "__main__":
    unittest.main()
