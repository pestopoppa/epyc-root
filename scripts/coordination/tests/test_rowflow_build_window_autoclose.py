#!/usr/bin/env python3
"""BUILD-WINDOW auto-close / --close / IDLE-WHY note / status unit count (pipeline-mgmt 2026-11-25)."""
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "rowflow"))
import rowflow as rf  # noqa: E402

NOW = 1_800_000_000.0


class T(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.flags = self.tmp.name
        self.sd = os.path.join(self.flags, "state")
        os.makedirs(self.sd)
        os.makedirs(os.path.join(self.flags, "grants"))
        self.ps = [mock.patch.object(rf, "state_dir", lambda f: self.sd),
                   mock.patch.object(rf, "_keeper_log_line", lambda f, m: None),
                   mock.patch.object(rf, "claim_requests", lambda f, prune=False: list(self.reqs))]
        for p in self.ps:
            p.start()
        self.reqs, self.logs = [], []
        rf.atomic_json(os.path.join(self.sd, rf.BUILD_WINDOW), {"by": "ak", "reason": "r", "minutes": 40, "until": NOW + 1200})

    def tearDown(self):
        for p in self.ps:
            p.stop()
        self.tmp.cleanup()

    def win(self):
        return rf.load_json(os.path.join(self.sd, rf.BUILD_WINDOW))

    def tick(self, t=NOW):
        return rf.build_window_autoclose(self.flags, now=t, log=self.logs.append)

    def test_autoclose_after_two_idle_ticks(self):
        self.assertFalse(self.tick())
        self.assertGreater(self.win()["until"], NOW)
        self.assertTrue(self.tick(NOW + 30))
        self.assertEqual(self.win()["until"], NOW + 30)
        self.assertEqual(rf.build_lane_open(self.flags, NOW + 31), ("", ""))
        self.assertIn("BUILD-WINDOW auto-closed: no build claim queued/running for 2 ticks", self.logs)

    def test_no_close_while_build_running_or_queued(self):
        bp = os.path.join(self.flags, "grants", "build-ak-1.build.json")
        rf.atomic_json(bp, {"id": "build-ak-1", "owner": "ak"})
        for i in range(4):
            self.assertFalse(self.tick(NOW + 30 * i))
        self.assertGreater(self.win()["until"], NOW + 100)
        open(os.path.join(self.flags, "grants", "build-ak-1.ended"), "w").write("rc=0\n")   # finished -> counts toward idle
        self.assertFalse(self.tick(NOW + 200))
        self.reqs.append({"id": "req-x"})   # a queued claim resets the idle count
        self.assertFalse(self.tick(NOW + 230))
        self.reqs.clear()
        self.assertFalse(self.tick(NOW + 260))
        self.assertTrue(self.tick(NOW + 290))

    def test_flag_off(self):
        with mock.patch.object(rf, "BUILD_WINDOW_AUTOCLOSE", False):
            self.assertFalse(self.tick())
            self.assertFalse(self.tick(NOW + 30))
        self.assertGreater(self.win()["until"], NOW + 100)

    def test_close_owner_check(self):
        with self.assertRaises(rf.Refused):
            rf.build_window_close(self.flags, "someone", "done", now=NOW, log=self.logs.append)
        self.assertGreater(self.win()["until"], NOW)
        rf.build_window_close(self.flags, "ak", "builds done", now=NOW, log=self.logs.append)
        self.assertEqual(self.win()["until"], NOW)
        self.assertEqual(self.win()["closed_by"], "ak")
        with self.assertRaises(rf.Refused):   # nothing open now
            rf.build_window_close(self.flags, "ak", "again", now=NOW + 1)

    def test_close_by_operator(self):
        rf.build_window_close(self.flags, "operator", "r", now=NOW, log=self.logs.append)
        self.assertEqual(self.win()["until"], NOW)

    def test_idle_why_note(self):
        s = rf.build_window_idle_note(self.flags, ["rowA", "rowB"], now=NOW)
        self.assertRegex(s, r"^BUILD-WINDOW open until \d\d:\d\dZ \(opened by ak\) holds quiet row\(s\) rowA,rowB$")
        self.assertEqual(rf.build_window_idle_note(self.flags, [], now=NOW), "")
        self.assertEqual(rf.build_window_idle_note(self.flags, ["rowA"], now=NOW + 5000), "")

    def test_status_units_counts_file(self):
        f = os.path.join(self.flags, "results.jsonl")
        with open(f, "w") as fh:
            for i in range(9):
                fh.write(json.dumps({"unit": i, "tps": 1.5}) + "\n")
        p = {"units": 0, "result_path": f, "result_format": "jsonl"}
        self.assertEqual(rf._status_units(p, {}), "9 unit(s) now, dry run added 0")
        self.assertEqual(rf._status_units({"units": 9, "result_path": f, "result_format": "jsonl"}, {}), "9 unit(s)")
        self.assertEqual(rf._status_units({"units": 0, "result_path": f, "result_format": "custom:true"}, {}), "0 unit(s)")


if __name__ == "__main__":
    unittest.main()
