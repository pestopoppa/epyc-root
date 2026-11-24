#!/usr/bin/env python3
"""BUILD-WINDOW-PROPOSE (pipeline-mgmt 2026-11-24): advisory alert when >= 2 builds wait behind a resumable quiet row with > 1 h left."""
import datetime as dt
import os
import sys
import tempfile
import unittest
from unittest import mock

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "rowflow"))
import rowflow as rf  # noqa: E402

NOW = 1_800_000_000.0
ROW = "ak-quiet-row-r1"


def iso(t):
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class T(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.flags = self.tmp.name
        self.sd = os.path.join(self.flags, "state")
        os.makedirs(self.sd)
        self.p = mock.patch.object(rf, "state_dir", lambda f: self.sd)
        self.p.start()
        self.emits, self.logs = [], []

    def tearDown(self):
        self.p.stop()
        self.tmp.cleanup()

    def emit(self, *a, **k):
        self.emits.append(a)
        return {"key": "x"}

    def run_(self, builds=2, left=7200, resumable=True, quiet=True, now=NOW, window=False):
        reqc = [{"id": f"b{i}", "request": {"owner": f"o{i}", "requested_at": now - 60, "minutes": 20 + i}} for i in range(builds)]
        d = {"owner": "ak", "resumable": resumable, "requires_quiet_host": quiet}
        grants = [{"id": ROW, "end": iso(now + left), "dryrun": False}]
        if window:
            rf.atomic_json(os.path.join(self.sd, rf.BUILD_WINDOW), {"by": "x", "reason": "r", "until": now + 600})
        with mock.patch.object(rf, "quiet_sensitive", lambda d: bool((d or {}).get("requires_quiet_host"))):
            return rf.build_window_propose(self.flags, grants, {ROW: d}, reqc, self.logs.append, now=now, emit=self.emit)

    def test_trigger(self):
        out = self.run_()
        self.assertEqual([r for r, _ in out], [ROW])
        self.assertEqual(len(self.emits), 1)
        a = self.emits[0]
        self.assertEqual((a[1], a[2], a[5], a[6]), ("build-window-proposal", ROW, "warning", "ak"))
        self.assertIn("rowflow.py build-window --minutes", a[4])
        self.assertIn("b0 (20 min)", a[4])
        self.assertIn("b1 (21 min)", a[4])
        self.assertIn(f"BUILD-WINDOW-PROPOSE {ROW} builds=2", self.logs)

    def test_one_build_no_trigger(self):
        self.assertEqual(self.run_(builds=1), [])
        self.assertEqual(self.emits, [])

    def test_short_left_no_trigger(self):
        self.assertEqual(self.run_(left=3500), [])
        self.assertEqual(self.emits, [])

    def test_not_resumable_no_trigger(self):
        self.assertEqual(self.run_(resumable=False), [])
        self.assertEqual(self.emits, [])

    def test_not_quiet_no_trigger(self):
        self.assertEqual(self.run_(quiet=False), [])

    def test_window_open_no_trigger(self):
        self.assertEqual(self.run_(window=True), [])

    def test_dedupe_per_hour(self):
        t0 = (int(NOW // 3600) + 1) * 3600 + 5
        self.assertEqual(len(self.run_(now=t0)), 1)
        self.assertEqual(self.run_(now=t0 + 600), [])
        self.assertEqual(len(self.emits), 1)
        self.assertEqual(len(self.run_(now=t0 + 3600)), 1)
        self.assertEqual(len(self.emits), 2)


if __name__ == "__main__":
    unittest.main()
