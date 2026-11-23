#!/usr/bin/env python3
"""BUILD LANE (coordinator 2026-11-23): a non-light build claim refused > 15 min opens the lane (no new quiet row granted,
QUIET-RESERVE stops refusing builds); `rowflow.py build-window` opens it explicitly (<= 90 min) and it closes itself."""
import os
import sys
import tempfile
import time
import unittest
from unittest import mock

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "rowflow"))
import rowflow as rf  # noqa: E402


class BuildLane(unittest.TestCase):
    def setUp(self):
        self.flags = tempfile.mkdtemp(prefix="blane-")
        os.makedirs(os.path.join(self.flags, "grants"))
        p = mock.patch.object(rf, "host_snapshot", side_effect=lambda f, g: (None, set(rf.REGIONS) | set(rf.CORES) | set(rf.THREADS), None))
        p.start(); self.addCleanup(p.stop)
        self.reserve()

    def reserve(self, ts=None):
        rf.atomic_json(os.path.join(rf.state_dir(self.flags), rf.QUIET_RESERVE_STATE),
                       {"active": True, "released": False, "ts": ts or time.time(), "rows": ["quiet-b"]})

    def claim(self, now=None):
        return rf.claim_build(self.flags, "autokernel", "24", 30, log=lambda m: None, allrows={}, now=now)

    def test_refused_by_reserve_then_lane_opens_after_15_min(self):
        t0 = time.time()
        with self.assertRaises(rf.Refused) as e:
            self.claim(t0)
        self.assertIn("QUIET-RESERVE", str(e.exception))
        self.assertEqual(rf.build_lane_open(self.flags, t0 + 600), ("", ""))
        for k in range(1, 17):   # retried every 60 s
            self.reserve(t0 + 60 * k)
            if k < 16:
                with self.assertRaises(rf.Refused):
                    self.claim(t0 + 60 * k)
        label, kind = rf.build_lane_open(self.flags, t0 + 16 * 60)
        self.assertEqual(kind, "claim")
        self.assertIn("autokernel|24", label)
        gid, _ = self.claim(t0 + 16 * 60)   # the reserve no longer refuses it
        self.assertTrue(gid.startswith("build-autokernel"))
        self.assertEqual(rf.build_lane_open(self.flags, t0 + 16 * 60 + 1), ("", ""))   # granted: the lane closes
        self.assertIn("BUILD-LANE open for", open(os.path.join(self.flags, "ws58-calendar-keeper.log")).read())

    def test_abandoned_refusal_never_opens_lane(self):
        t0 = time.time() - 3600
        rf.record_build_refusal(self.flags, "autokernel", "24", t0)
        rf.record_build_refusal(self.flags, "autokernel", "24", t0 + 1200)   # gap > stale: restarts the clock
        self.assertEqual(rf.build_lane_open(self.flags, t0 + 1300), ("", ""))

    def test_build_window_opens_and_expires(self):
        t0 = time.time()
        rec = rf.build_window(self.flags, 10, "autokernel", "c20 build", now=t0, log=lambda m: None)
        self.assertEqual(rec["minutes"], 10)
        self.assertEqual(rf.build_lane_open(self.flags, t0 + 60)[1], "window")
        self.assertEqual(rf.build_lane_open(self.flags, t0 + 601), ("", ""))
        self.assertIn("BUILD-WINDOW", open(os.path.join(self.flags, "ws58-calendar-keeper.log")).read())
        gid, _ = (rf.build_window(self.flags, 5, "autokernel", "x", now=t0, log=lambda m: None), self.claim(t0 + 5))[1]
        self.assertTrue(gid)

    def test_build_window_max_90(self):
        with self.assertRaises(rf.Refused):
            rf.build_window(self.flags, 91, "autokernel", "r", log=lambda m: None)
        with self.assertRaises(rf.Refused):
            rf.build_window(self.flags, 10, "", "r", log=lambda m: None)

    def test_running_quiet_row_still_refuses_build(self):
        rf.write_grant(self.flags, "quiet-a", "q0", {"q0"}, 3600)
        rf.build_window(self.flags, 10, "autokernel", "r", log=lambda m: None)
        with self.assertRaises(rf.Refused) as e:
            rf.claim_build(self.flags, "autokernel", "24", 30, log=lambda m: None,
                           allrows={"quiet-a": {"id": "quiet-a", "requires_quiet_host": True}})
        self.assertIn("is running", str(e.exception))   # never pre-empted

    def test_cli_build_window(self):
        import subprocess
        r = subprocess.run([sys.executable, os.path.join(os.path.dirname(_TESTS), "rowflow", "rowflow.py"), "--flags", self.flags,
                            "build-window", "--minutes", "5", "--by", "autokernel", "--reason", "t"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("BUILD-WINDOW", r.stdout)


if __name__ == "__main__":
    unittest.main()
