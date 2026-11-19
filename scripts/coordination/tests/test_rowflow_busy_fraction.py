"""Operator 2026-11-03 (session review 3.1): drain / quiet-host promotion KEEPS, but a row spec may carry busy_fraction
(0..1, the share of its claimed cpus the job keeps busy) and a row below 0.5 is never promoted to a quiet-host /
whole-host drain - a ~4%-busy row cannot book a quiet host. Unset = unknown = 1.0. Such a row still takes free regions.
publish (rowflow.publish and publish_row's lint, before the smoke) refuses a value outside 0..1."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rowflow"))
import rowflow as rf  # noqa: E402
import publish_row as pr  # noqa: E402
import test_rowflow as tr  # noqa: E402  (fixture only)

NOW = 1_000_000.0
QUARTER_OPTS = [frozenset({q}) for q in sorted(rf.QUARTERS)]
ALL = [frozenset(rf.REGIONS)]
HOST = [frozenset(rf.QUARTERS)]


def cand(rid, opts, rank, **kw):
    c = {"id": rid, "kind": "grant", "lane": "cpu", "rank": float(rank), "lane_count": 0, "gib": 0, "bench": False,
         "options": list(opts), "window_s": 3000}
    c.update(kw)
    return c


def run(cands, free):
    out, _, pend = rf.plan(set(free), cands, 1000, now=NOW, grant_ends=[NOW + 1800])
    return [c["id"] for c, _ in out], [c["id"] for c in pend], rf.plan.last_drain, [c["id"] for c in rf.plan.drain_lowbusy]


class BusyFractionDrain(unittest.TestCase):
    def test_low_busy_quiet_host_row_does_not_drain_the_host(self):
        qh = cand("qh-4pct", ALL, 1, shape="quiet-host", busy_fraction=0.04)
        q = cand("quarter-row", QUARTER_OPTS, 50, min_window_s=1000 * 3600)  # D9 2026-11-11: min_window above the gap, so the cap fails cap_ok and the row stays late
        placed, pend, drain, low = run([qh, q], {"q0", "q1"})
        self.assertIsNone(drain)
        self.assertEqual(placed, ["quarter-row"])          # the free quarter is used, not held empty for the 4% row
        self.assertEqual(pend, ["qh-4pct"])
        self.assertEqual(low, ["qh-4pct"])

    def test_unset_busy_fraction_is_one_and_still_drains(self):
        qh = cand("qh-unknown", ALL, 1, shape="quiet-host")
        q = cand("quarter-row", QUARTER_OPTS, 50, min_window_s=1000 * 3600)  # D9 2026-11-11: min_window above the gap, so the cap fails cap_ok and the row stays late
        placed, pend, drain, low = run([qh, q], {"q0", "q1"})
        self.assertEqual(drain[0]["id"], "qh-unknown")     # control: the drain rule itself is kept
        self.assertEqual(placed, [])                       # a 3000 s quarter row would end after T: not backfilled
        self.assertEqual(low, [])

    def test_threshold_is_half_inclusive_for_an_aged_host_row(self):
        old = NOW - 2 * rf.DRAIN_AFTER_S
        for bf, drains in ((0.49, False), (0.5, True), (1.0, True), (0.0, False)):
            h = cand("host-row", HOST, 5, shape="host", since=old, busy_fraction=bf)
            _, _, drain, low = run([h], {"q0"})
            self.assertEqual(drain is not None, drains, bf)
            self.assertEqual(low == ["host-row"], not drains, bf)

    def test_low_busy_row_still_takes_free_regions(self):
        qh = cand("qh-4pct", ALL, 1, shape="quiet-host", busy_fraction=0.04)
        placed, _, drain, _ = run([qh], set(rf.REGIONS))
        self.assertEqual(placed, ["qh-4pct"])
        self.assertIsNone(drain)

    def test_row_busy_reads_unknown_and_invalid_as_one(self):
        for v, want in ((None, 1.0), ("x", 1.0), (True, 1.0), (1.5, 1.0), (-0.1, 1.0), (0.04, 0.04), (0, 0.0), ("0.3", 0.3)):
            self.assertEqual(rf.row_busy({"busy_fraction": v}), want, v)
        self.assertEqual(rf.row_busy({}), 1.0)


class BusyFractionPublish(unittest.TestCase):
    def test_publish_gate_refuses_out_of_range_in_one_line(self):
        for bad in (1.5, -0.1, "0.5", True, [0.5]):
            with self.assertRaises(rf.Refused) as cm:
                rf.check_busy_fraction({"busy_fraction": bad})
            self.assertIn("busy_fraction", str(cm.exception))
            self.assertNotIn("\n", str(cm.exception))
            with self.assertRaises(rf.Refused):
                pr.lint({"id": "x", "busy_fraction": bad})       # publish_row refuses before the smoke
        for ok in (None, 0, 1, 0.04, 0.5):
            rf.check_busy_fraction({"busy_fraction": ok})
        self.assertIn("busy_fraction", pr.SPEC_KEYS)             # --repair carries it over

    def test_published_row_carries_busy_fraction(self):
        fx = tr.Fixture()
        try:
            d = fx.job("t-busy-20261103")
            row = rf.publish(fx.spec("t-busy-20261103", d, busy_fraction=0.04), fx.flags)
            self.assertEqual(row["busy_fraction"], 0.04)
            d2 = fx.job("t-busy2-20261103")
            self.assertNotIn("busy_fraction", rf.publish(fx.spec("t-busy2-20261103", d2), fx.flags))
            with self.assertRaises(rf.Refused):
                rf.publish(fx.spec("t-busy3-20261103", fx.job("t-busy3-20261103"), busy_fraction=4), fx.flags)
        finally:
            fx.cleanup()


if __name__ == "__main__":
    unittest.main()
