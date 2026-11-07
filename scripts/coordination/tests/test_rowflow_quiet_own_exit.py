#!/usr/bin/env python3
"""c8-lcattn-gate-r2 2026-11-07: the device-quiet wait fast-paths ONE sample after OUR grant's exit (INVARIANTS 13 is
about unknown processes; a foreign/unknown client keeps two-sample persistence), and IDLE-WHY names the quiet wait."""
import os
import shutil
import sys
import tempfile
import unittest

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "rowflow"))
import rowflow as rf  # noqa: E402

DEAD = 2 ** 22 + 12345   # beyond pid_max on this host: never alive


class QuietOwnExit(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="qoe-")
        self.flags = os.path.join(self.d, "flags")
        os.makedirs(os.path.join(self.flags, "grants"))
        self.kfd = os.path.join(self.d, "kfd")
        os.makedirs(self.kfd)
        self.old = rf.KFD_PROC
        rf.KFD_PROC = self.kfd

    def tearDown(self):
        rf.KFD_PROC = self.old
        shutil.rmtree(self.d, ignore_errors=True)

    def foreign(self, pid=4242, gib=2):
        os.makedirs(os.path.join(self.kfd, str(pid)), exist_ok=True)
        open(os.path.join(self.kfd, str(pid), "vram_0"), "w").write(str(gib << 30))

    def gate(self, grants=()):
        return rf.gpu_quiet_gate(self.flags, list(grants), {}, lambda *_: None, set())

    def own_grant(self, ended=True, pid=DEAD):
        g = {"id": "row-a", "holds": [rf.GPU], "pid": pid, "path": os.path.join(self.flags, "grants", "row-a")}
        self.assertIsNone(self.gate([g]))   # grant open: records the owner
        if ended:
            open(os.path.join(self.flags, "grants", "row-a.ended"), "w").write("rc=0 reason=complete\n")

    def test_own_exit_one_sample(self):
        self.own_grant()
        self.assertIsNone(self.gate())

    def test_no_prior_owner_needs_two(self):
        self.assertIn("1/2", self.gate())
        self.assertIsNone(self.gate())

    def test_not_ended_needs_two(self):
        self.own_grant(ended=False)
        self.assertIn("1/2", self.gate())

    def test_pid_still_alive_needs_two(self):
        self.own_grant(pid=os.getpid())
        self.assertIn("1/2", self.gate())

    def test_foreign_client_resets_to_full_persistence(self):
        self.own_grant()
        self.foreign()
        self.assertIn("not quiet", self.gate())
        os.remove(os.path.join(self.kfd, "4242", "vram_0"))
        os.rmdir(os.path.join(self.kfd, "4242"))
        self.assertIn("1/2", self.gate())      # the foreign sighting dropped the own-exit record
        self.assertIsNone(self.gate())


if __name__ == "__main__":
    unittest.main()
