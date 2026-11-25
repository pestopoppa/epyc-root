"""Resumed bookings use elapsed archived work and preserve scheduling caps."""
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "rowflow"))
import rowflow as rf  # noqa: E402


class ResumableWindow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.flags = self.tmp.name
        self.archive = rf.autorequeue_dir(self.flags)
        os.makedirs(self.archive)
        self.row = {"resumable": True, "estimate_s": 18450, "min_window_s": 2400, "window_s": 20000}

    def ended(self, rid, stamp, start, end):
        with open(os.path.join(self.archive, f"{rid}.{stamp}.ended"), "w") as f:
            f.write(f"rc=75 time={end} reason=partial-native-stopped\nstarted={start}\n")

    def test_remaining_time_across_attempts(self):
        self.ended("row", "20261125T010000Z", "2026-11-25T00:00:00Z", "2026-11-25T01:00:00Z")
        self.ended("row", "20261125T030000Z", "2026-11-25T02:00:00Z", "2026-11-25T03:00:00Z")
        self.ended("row-other", "20261125T040000Z", "2026-11-25T03:00:00Z", "2026-11-25T04:00:00Z")
        self.assertEqual(rf.resumable_window_s(self.flags, "row", self.row), 18450 - 7200 + rf.CAP_SLACK_S)

    def test_window_and_launcher_minimum_bounds(self):
        self.ended("row", "20261125T010000Z", "2026-11-25T00:00:00Z", "2026-11-25T01:00:00Z")
        self.assertEqual(rf.resumable_window_s(self.flags, "row", dict(self.row, window_s=5000)), 5000)
        self.assertEqual(rf.resumable_window_s(self.flags, "row", dict(self.row, estimate_s=1000)), 2400 + rf.CAP_SLACK_S)

    def test_absent_bad_or_disabled_history_preserves_existing_booking(self):
        self.assertIsNone(rf.resumable_window_s(self.flags, "row", self.row))
        self.ended("row", "20261125T010000Z", "invalid", "2026-11-25T01:00:00Z")
        self.assertIsNone(rf.resumable_window_s(self.flags, "row", self.row))
        self.ended("row", "20261125T020000Z", "2026-11-25T01:00:00Z", "2026-11-25T02:00:00Z")
        self.assertIsNone(rf.resumable_window_s(self.flags, "row", dict(self.row, resumable=False)))
        with mock.patch.object(rf, "RESUMABLE_WINDOW_SIZING", False):
            self.assertIsNone(rf.resumable_window_s(self.flags, "row", self.row))

    def test_build_pocket_still_limits_resumed_grant(self):
        self.ended("row", "20261125T010000Z", "2026-11-25T00:00:00Z", "2026-11-25T01:00:00Z")
        window = rf.resumable_window_s(self.flags, "row", self.row)
        cand = dict(self.row, id="row", kind="grant", lane="cpu", rank=40, lane_count=1, gib=8,
                    bench=False, options=[frozenset({"q0", "q1", "q2"})], shape="multi-quarter(3)",
                    since=1800000000, window_s=window, book_s=window)
        out, _, _ = rf.plan({"q0", "q1", "q2", "q3"}, [cand], 900, now=1800000000,
                            build_policy={"long_hold_s": 7200, "max_hold_s": 7200})
        self.assertEqual(out[0][0]["window_s"], window)
        self.assertEqual(rf.plan.hard_end["row"], 1800007200)


if __name__ == "__main__":
    unittest.main()
