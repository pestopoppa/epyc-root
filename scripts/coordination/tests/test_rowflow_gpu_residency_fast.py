#!/usr/bin/env python3
"""Fast GPU residency: only this row's own clients count (its cgroup leaf; legacy: its process tree), above the floor."""
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
        p = mock.patch.object(rf, "ROWFLOW_CGROUP", self.kfd + "/no-cgroup")
        p.start()
        self.addCleanup(p.stop)
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



class CgroupAttribution(unittest.TestCase):
    """Audit #1: a pid is a row's iff /proc/<pid>/cgroup is under /rowflow/<id>@<tag>; legacy only for leafless rows."""

    def setUp(self):
        self.cg = tempfile.mkdtemp(prefix="cg-")
        self.addCleanup(shutil.rmtree, self.cg, True)
        for p in (mock.patch.object(rf, "ROWFLOW_CGROUP", self.cg),
                  mock.patch.object(rf, "lineage_filler_id", return_value=None),
                  mock.patch.object(rf, "harness_tree", side_effect=lambda r, t: t),
                  mock.patch.object(rf, "pid_container_id", return_value=None)):
            p.start()
            self.addCleanup(p.stop)
        self.cgroups = {}
        p = mock.patch.object(rf, "pid_cgroup_row", lambda q: rf.cgroup_row(self.cgroups.get(q, "0::/\n")))
        p.start()
        self.addCleanup(p.stop)

    def leaf(self, rid, pids, tag="77"):
        d = os.path.join(self.cg, f"{rid}@{tag}")
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "cgroup.events"), "w").write("populated %d\nfrozen 0\n" % bool(pids))
        open(os.path.join(d, "cgroup.procs"), "w").write("".join(f"{x}\n" for x in pids))
        for x in pids:
            self.cgroups[x] = f"0::/rowflow/{rid}@{tag}\n"

    def sample(self, occ, tracked=None, containers=None):
        own = {}
        with mock.patch.object(rf, "gpu_occupancy", return_value={"pids": occ}):
            rf.sample_gpu_residency(1, dict(tracked or {}), own, "row-a", containers)
        return own

    def test_cgroup_row_parse(self):
        self.assertEqual(rf.cgroup_row("0::/rowflow/row-a@123\n"), "row-a")
        self.assertEqual(rf.cgroup_row("0::/rowflow/row-a.v2@9/sub\n"), "row-a.v2")
        self.assertIsNone(rf.cgroup_row("0::/\n"))
        self.assertIsNone(rf.cgroup_row("0::/rowflow\n"))
        self.assertIsNone(rf.cgroup_row("0::/rowflow/no-tag\n"))
        self.assertIsNone(rf.cgroup_row("0::/autokernel-1-abc\n"))

    def test_leaf_pid_counts_outside_tree_and_without_filler_id(self):
        self.leaf("row-a", [700])
        self.assertEqual(self.sample({700: 2 << 30}), {700: 2 << 30})

    def test_unrelated_pid_refused_even_in_tree_once_row_has_leaf(self):
        self.leaf("row-a", [700])
        self.assertEqual(self.sample({999: 8 << 30}, tracked={999: "s"}), {})

    def test_other_rows_leaf_refused_even_if_tracked(self):
        self.leaf("row-a", [700])
        self.leaf("row-ab", [701])      # a prefix-sharing id is another row
        self.assertEqual(self.sample({701: 8 << 30}, tracked={701: "s"}), {})

    def test_floor_still_applies(self):
        self.leaf("row-a", [700])
        self.assertLess(rf.own_vram_peak(self.sample({700: 13 * MB})), rf.RESIDENCY_FLOOR_B)

    def test_container_label_still_works_with_leaf(self):
        self.leaf("row-a", [700])
        cid = "c" * 64
        with mock.patch.object(rf, "pid_container_id", lambda q: cid if q == 800 else None), \
                mock.patch.object(rf, "docker_row_label", return_value="row-a"):
            self.assertEqual(self.sample({800: 3 << 30}, containers={}), {800: 3 << 30})

    def test_legacy_fallback_for_leafless_row(self):   # MIGRATION: a grant started by the pre-cgroup engine
        self.assertEqual(self.sample({500: 1 << 30}, tracked={500: "s"}), {500: 1 << 30})
        self.leaf("row-a", [])                          # an emptied leaf (job ended) is not a leaf
        self.assertEqual(self.sample({500: 1 << 30}, tracked={500: "s"}), {500: 1 << 30})

    def test_keeper_own_pids_uses_leaf_not_tree(self):
        self.leaf("row-a", [700, 701])
        with mock.patch.object(rf, "tree_pids") as tp, mock.patch.object(rf, "load_json", return_value=None):
            self.assertEqual(rf.own_pids("/nonexistent", {"id": "row-a", "pid": 1234}), {700, 701})
            tp.assert_not_called()
        with mock.patch.object(rf, "tree_pids", return_value={1235}), mock.patch.object(rf, "load_json", return_value=None):
            self.assertEqual(rf.own_pids("/nonexistent", {"id": "row-b", "pid": 1234}), {1234, 1235})   # legacy


REAL_BASE = "/sys/fs/cgroup/rowflow"


@unittest.skipUnless(os.access(REAL_BASE, os.W_OK), "no writable cgroup v2 rowflow base")
class RealCgroupLeaf(unittest.TestCase):
    """On the host: a cleaned-env, setsid, double-forked grandchild stays in the row's leaf."""

    def test_detached_grandchild_is_attributed(self):
        import subprocess
        rid = f"cgtest-{os.getpid()}"
        leaf = os.path.join(REAL_BASE, f"{rid}@1")
        os.mkdir(leaf)
        script = (f"echo $$ > {leaf}/cgroup.procs; exec env -i /usr/bin/setsid /bin/bash -c "
                  "'( /usr/bin/setsid /bin/sleep 30 & echo $! >&3 ) 3>&1; exec /bin/sleep 30'")
        p = subprocess.Popen(["/bin/bash", "-c", script], stdout=subprocess.PIPE, text=True, start_new_session=True)
        try:
            gc = int(p.stdout.readline())
            self.assertEqual(rf.pid_cgroup_row(gc), rid)
            self.assertNotIn(b"FILLER_ID", open(f"/proc/{gc}/environ", "rb").read())
            self.assertIn(gc, rf.row_leaf_pids(rid)[1])
            with mock.patch.object(rf, "lineage_filler_id", return_value=None):
                self.assertTrue(rf.pid_is_rows(gc, rid, {}))
                self.assertFalse(rf.pid_is_rows(os.getpid(), rid, {}))       # the harness itself is not the row's
                self.assertFalse(rf.pid_is_rows(gc, "cgtest-other", {gc}))   # another row never claims it
        finally:
            open(os.path.join(leaf, "cgroup.kill"), "w").write("1")
            p.wait(timeout=10)
            for _ in range(50):
                if "populated 0" in open(os.path.join(leaf, "cgroup.events")).read():
                    break
                time.sleep(0.1)
            os.rmdir(leaf)

if __name__ == "__main__":
    unittest.main()
