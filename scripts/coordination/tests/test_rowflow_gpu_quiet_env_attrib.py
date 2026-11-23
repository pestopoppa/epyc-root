"""c20-fold-a3b-gpu-20261123-r2: an AK multi-server A/B row (a new llama-server every ~18 s, start_new_session) read
gpu-quiet=0% IDLE-HELD. gpu_grant_busy attributes KFD clients by FILLER_ID env, fails closed on unreadable environ,
counts a recent row-dir write as busy, and queue_status uses that predicate instead of device % alone."""
import os
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rowflow"))
import rowflow as rf  # noqa: E402

RID = "c20-fold-x-r2"
IDLE_UTIL = {"gpu": {"busy": 0}}


class GpuQuietEnvAttrib(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.mkdtemp()
        self.flags = os.path.join(self.td, "flags")
        os.makedirs(os.path.join(self.flags, "dryrun"))
        self.g = {"id": RID, "pid": None, "path": os.path.join(self.flags, "x.grant")}
        old = time.time() - 3600
        self.p = [mock.patch.object(rf, "row_leaf_pids", return_value=(True, {100})),
                  mock.patch.object(rf, "pid_cgroup_row", return_value=None),
                  mock.patch.object(rf, "row_container_pids", return_value=set()),
                  mock.patch.object(rf, "TMP", self.td + "/"),
                  mock.patch.object(rf, "_environ_readable", return_value=True)]
        for p in self.p:
            p.start()
        self.old = old

    def tearDown(self):
        for p in self.p:
            p.stop()

    def test_env_matched_server_is_own_and_busy(self):
        occ = {"pids": {555: 38 << 30}, "vram_used": 38 << 30}
        with mock.patch.object(rf, "pid_filler_id", side_effect=lambda q: RID if q == 555 else None):
            busy, why = rf.gpu_grant_busy(self.flags, self.g, IDLE_UTIL, occ, now=time.time())
        self.assertTrue(busy)
        self.assertIn("> 1 GiB VRAM", why)

    def test_foreign_env_server_not_attributed(self):
        occ = {"pids": {555: 38 << 30}, "vram_used": 38 << 30}
        with mock.patch.object(rf, "pid_filler_id", return_value="other-row"):
            busy, why = rf.gpu_grant_busy(self.flags, self.g, IDLE_UTIL, occ, now=time.time() + 10_000)
        self.assertFalse(busy, why)

    def test_other_rows_cgroup_wins_over_env(self):
        occ = {"pids": {555: 1 << 30}, "vram_used": 1 << 30}
        with mock.patch.object(rf, "pid_cgroup_row", return_value="other-row"), \
                mock.patch.object(rf, "pid_filler_id", return_value=RID):
            busy, _ = rf.gpu_grant_busy(self.flags, self.g, IDLE_UTIL, occ, now=time.time() + 10_000)
        self.assertFalse(busy)

    def test_unreadable_environ_fails_closed(self):
        occ = {"pids": {555: 1 << 30}, "vram_used": 1 << 30}
        with mock.patch.object(rf, "pid_filler_id", return_value=None), \
                mock.patch.object(rf, "_environ_readable", return_value=False):
            busy, why = rf.gpu_grant_busy(self.flags, self.g, IDLE_UTIL, occ, now=time.time() + 10_000)
        self.assertTrue(busy)
        self.assertIn("unattributable", why)

    def test_recent_row_dir_write_between_loads_is_busy(self):
        d = os.path.join(self.td, RID, "ab")
        os.makedirs(d)
        open(os.path.join(d, "server-17.log"), "w").close()
        occ = {"pids": {}, "vram_used": 13 << 20}
        busy, why = rf.gpu_grant_busy(self.flags, self.g, IDLE_UTIL, occ, now=time.time() + 30)
        self.assertTrue(busy)
        self.assertIn("written", why)
        busy, _ = rf.gpu_grant_busy(self.flags, self.g, IDLE_UTIL, occ, now=time.time() + rf.GPU_RECENT_WRITE_S + 60)
        self.assertFalse(busy)

    def test_no_dirs_no_clients_idle_device_reads_quiet(self):
        occ = {"pids": {}, "vram_used": 13 << 20}
        busy, _ = rf.gpu_grant_busy(self.flags, self.g, IDLE_UTIL, occ, now=time.time())
        self.assertFalse(busy)


class QueueStatusGpuIdle(unittest.TestCase):
    def _qs(self):
        here = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, os.path.join(here, "..", "..", "..", ".claude", "skills", "inference-backlog-scheduling", "scripts"))
        import queue_status
        return queue_status

    def test_busy_grant_not_idle_and_error_fails_closed(self):
        qs = self._qs()
        fake = mock.Mock()
        fake.open_grants.return_value = [{"id": RID}]
        fake.gpu_occupancy.return_value = {"pids": {}, "vram_used": 1}
        fake.gpu_grant_busy.return_value = (True, "row dir written 3s ago")
        with mock.patch.object(qs, "_rowflow", return_value=fake):
            self.assertEqual(qs._gpu_idle("/f", RID, IDLE_UTIL), [])
            fake.gpu_grant_busy.return_value = (False, "quiet")
            self.assertEqual(qs._gpu_idle("/f", RID, IDLE_UTIL), ["gpu-quiet"])
            fake.gpu_grant_busy.side_effect = OSError("boom")
            self.assertEqual(qs._gpu_idle("/f", RID, IDLE_UTIL), [])


if __name__ == "__main__":
    unittest.main()
