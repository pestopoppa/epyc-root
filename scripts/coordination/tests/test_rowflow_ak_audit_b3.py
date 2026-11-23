#!/usr/bin/env python3
"""AK audit B3 (2026-11-23): a NEW non-light q3 build claim yields to a grantable GPU row that waits only on q3 host cores; running
builds are never pre-empted; a light claim on 84-87 yields only when it actually overlaps the GPU row's cores."""
import os
import sys
import tempfile
import unittest
from unittest import mock

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "rowflow"))
import rowflow as rf  # noqa: E402

GPU_OPT = frozenset(rf.GPU_Q3_TOKENS)


class B3(unittest.TestCase):
    def setUp(self):
        self.flags = tempfile.mkdtemp(prefix="b3-")
        os.makedirs(os.path.join(self.flags, "grants"))
        self.opt = GPU_OPT
        self.allrows = {"gpu-row": {"id": "gpu-row", "lane": "gpu"}}
        for name, fn in (("runnable", lambda st: True), ("status", lambda *a, **k: {}),
                         ("contract_of", lambda d, o=None, flags=None: {"options": [self.opt]})):
            p = mock.patch.object(rf, name, side_effect=fn)
            p.start(); self.addCleanup(p.stop)
        # 88-95 are held by a running build (so the GPU row waits only on q3 host cores)
        busy = {f"c{k}" for k in range(88, 96)}
        self.free = (set(rf.REGIONS) | set(rf.CORES) | set(rf.THREADS)) - busy
        p = mock.patch.object(rf, "host_snapshot", side_effect=lambda f, g: (None, set(self.free), None))
        p.start(); self.addCleanup(p.stop)

    def build(self, cpus="72-87"):
        return rf.claim_build(self.flags, "autokernel", cpus, 30, log=lambda m: None, allrows=self.allrows)

    def test_waiting_row_detected(self):
        w = rf.gpu_rows_waiting_on_q3(self.flags, [], self.allrows, self.free)
        self.assertEqual(list(w), ["gpu-row"])

    def test_new_q3_build_refused(self):
        with self.assertRaises(rf.Refused) as e:
            self.build("72-87")
        self.assertIn("yields", str(e.exception))
        self.assertIn("gpu-row", str(e.exception))

    def test_q0_q2_build_unaffected(self):
        gid, _ = self.build("24")
        self.assertTrue(gid.startswith("build-"))

    def test_row_not_waiting_when_it_fits_or_runs(self):
        self.assertEqual(rf.gpu_rows_waiting_on_q3(self.flags, [{"id": "gpu-row", "holds": set()}], self.allrows, self.free), {})
        full = set(rf.REGIONS) | set(rf.CORES) | set(rf.THREADS)
        self.assertEqual(rf.gpu_rows_waiting_on_q3(self.flags, [], self.allrows, full), {})   # fits: it is placed, not waiting
        gid, _ = (self.free.update(full), self.build("72-87"))[1]   # nothing waits: the pocket claim is granted
        self.assertTrue(gid)

    def test_running_build_never_preempted(self):
        self.free |= {f"c{k}" for k in range(88, 96)}
        gid, _ = self.build("72-87")
        self.free -= {f"c{k}" for k in range(88, 96)}
        self.assertIn(gid, [g["id"] for g in rf.open_grants(self.flags)])   # the later GPU-row wait leaves it open

    def test_light_claim_84_87_unaffected_unless_overlap(self):
        gid, _ = rf.claim_build(self.flags, "autokernel", "84-87", 5, log=lambda m: None, allrows=self.allrows, light=True)
        self.assertTrue(rf.is_light_build(self.flags, gid))
        rf.release_grant(self.flags, gid, "autokernel", "t")
        self.opt = frozenset({"gpu-quiet"} | {f"c{k}" for k in range(84, 96)} | {f"t{k}" for k in range(180, 192)})
        with self.assertRaises(rf.Refused) as e:
            rf.claim_build(self.flags, "autokernel", "84-87", 5, log=lambda m: None, allrows=self.allrows, light=True)
        self.assertIn("LIGHT-REFUSED", str(e.exception))


if __name__ == "__main__":
    unittest.main()
