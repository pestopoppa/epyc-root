"""Backfill-if-fits (operator 2026-11-07 "Approve + deploy", port of rowflow2 59f09b81e). A waiting wide row reserves its
regions only until its EARLIEST FEASIBLE START S (the ends of the grants holding the regions it needs); a lower row may
take them iff now + its estimate <= S. Unknown S, an expired S or one beyond the longest busy window -> no reservation;
a persisted drain T in the past never blocks. Origin: c7-local-code28k-20261106-r3 (q0-q3) kept q2/q3 drained while the
LSA rows held q0/q1 for 10+ h."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rowflow"))
import rowflow as rf  # noqa: E402

NOW = 1_800_000_000.0
H = 3600.0


def cand(rid, options, rank=50, shape="quarter", since=NOW, est=3 * H):
    return {"id": rid, "kind": "grant", "lane": "cpu", "rank": rank, "lane_count": 1, "gib": 8, "bench": False,
            "options": [frozenset(o) for o in options], "shape": shape, "since": since, "window_s": est + 900,
            "estimate_s": est}


def wide():
    return cand("c7-wide", [set(rf.QUARTERS)], rank=40, shape="host", since=NOW - 4 * H, est=1.5 * H)


def lsa_ends(t_end):
    """q0 + q1 held by the LSA grants until t_end (every token they hold)."""
    return {r: t_end for r in rf.expand({"q0", "q1"})}


FREE = {"q2", "q3"}


def ids(assigned):
    return {c["id"] for c, _ in assigned}


class BackfillIfFits(unittest.TestCase):
    def run_plan(self, rows, region_ends, grant_ends, drain_prev=None):
        return rf.plan(FREE, rows, 1000, now=NOW, grant_ends=grant_ends, drain_prev=drain_prev, region_ends=region_ends)

    def test_rows_ending_before_the_wide_start_are_granted(self):
        a, idle, _ = self.run_plan([wide(), cand("q2-3h", [{"q2"}]), cand("q3-3h", [{"q3"}])], lsa_ends(NOW + 10 * H), [NOW + 10 * H])
        self.assertEqual(ids(a), {"q2-3h", "q3-3h"})
        self.assertAlmostEqual(rf.plan.last_drain[1], NOW + 10 * H)

    def test_row_ending_after_the_wide_start_waits(self):
        """book_s = 0.75 * 14 h = 10.5 h > the 10 h start: waits."""
        a, idle, _ = self.run_plan([wide(), {**cand("q2-14h", [{"q2"}], est=14 * H), "min_window_s": 1000 * 3600}], lsa_ends(NOW + 10 * H), [NOW + 10 * H])
        self.assertEqual(ids(a), set())
        self.assertIn("draining for host c7-wide", idle["q2"])

    def test_row_booked_inside_the_wide_start_is_admitted_capped(self):
        """ONE BOOKING DURATION (audit 2026-11-10 #3): a 12 h estimate books 9 h <= the 10 h start, so it is admitted,
        and its 12 h window is capped at the start (the hard-end safety)."""
        a, _, _ = self.run_plan([wide(), cand("q2-12h", [{"q2"}], est=12 * H)], lsa_ends(NOW + 10 * H), [NOW + 10 * H])
        self.assertEqual(ids(a), {"q2-12h"})
        self.assertAlmostEqual(rf.plan.hard_end["q2-12h"], NOW + 10 * H)

    def test_start_is_the_needed_regions_end_not_any_grant(self):
        """A long grant on regions the wide row does not need never pushes its start later."""
        ends = lsa_ends(NOW + 2 * H)
        ends[rf.GPU] = NOW + 30 * H
        a, _, _ = self.run_plan([wide(), {**cand("q2-3h", [{"q2"}]), "min_window_s": 1000 * 3600}], ends, [NOW + 2 * H, NOW + 30 * H])
        self.assertAlmostEqual(rf.plan.last_drain[1], NOW + 2 * H)
        self.assertEqual(ids(a), set())   # 3 h ends after the 2 h start: waits

    def test_foreign_hold_on_one_region_keeps_the_reservation(self):
        """coordinator 2026-11-10 (rank-2 floor slipped 19:07Z -> 21:11Z): q1 foreign (no known end), q0 known until 10 h.
        The reservation stays at T = 10 h; a row booking past T waits, one booking inside T is admitted capped at T."""
        ends = lsa_ends(NOW + 10 * H)
        for r in rf.expand({"q1"}):
            ends.pop(r)   # q1 held by a foreign region-lock hold: no known end
        a, _, _ = self.run_plan([wide(), {**cand("q2-14h", [{"q2"}], est=14 * H), "min_window_s": 1000 * 3600}], ends, [NOW + 10 * H])
        self.assertEqual(ids(a), set())
        self.assertAlmostEqual(rf.plan.last_drain[1], NOW + 10 * H)
        a, _, _ = self.run_plan([wide(), cand("q2-12h", [{"q2"}], est=12 * H)], ends, [NOW + 10 * H])
        self.assertEqual(ids(a), {"q2-12h"})
        self.assertAlmostEqual(rf.plan.hard_end["q2-12h"], NOW + 10 * H)

    def test_no_known_end_anywhere_reserves_nothing(self):
        ends = {}
        a, _, _ = self.run_plan([wide(), cand("q2-12h", [{"q2"}], est=12 * H)], ends, [])
        self.assertEqual(ids(a), {"q2-12h"})
        self.assertIsNone(rf.plan.last_drain)
        self.assertIn("c7-wide", [c["id"] for c, _ in rf.plan.no_reserve])

    def test_start_beyond_the_longest_busy_window_reserves_nothing(self):
        a, _, _ = self.run_plan([wide(), cand("q2-12h", [{"q2"}], est=12 * H)], lsa_ends(NOW + 20 * H), [NOW + 10 * H])
        self.assertEqual(ids(a), {"q2-12h"})
        self.assertIsNone(rf.plan.last_drain)

    def test_expired_grant_end_reserves_nothing(self):
        a, _, _ = self.run_plan([wide(), cand("q2-12h", [{"q2"}], est=12 * H)], lsa_ends(NOW - 60), [NOW - 60])
        self.assertEqual(ids(a), {"q2-12h"})

    def test_expired_persisted_drain_never_blocks(self):
        rows = [wide(), cand("q2-3h", [{"q2"}]), cand("q3-3h", [{"q3"}])]
        a, _, _ = self.run_plan(rows, lsa_ends(NOW + 10 * H), [NOW + 10 * H], drain_prev={"c7-wide": NOW - 2 * H})
        self.assertEqual(ids(a), {"q2-3h", "q3-3h"})
        self.assertAlmostEqual(rf.plan.last_drain[1], NOW + 10 * H)

    def test_future_persisted_drain_still_only_moves_earlier(self):
        a, _, _ = self.run_plan([wide(), {**cand("q2-3h", [{"q2"}]), "min_window_s": 1000 * 3600}], lsa_ends(NOW + 10 * H), [NOW + 10 * H],
                                drain_prev={"c7-wide": NOW + 2 * H})
        self.assertAlmostEqual(rf.plan.last_drain[1], NOW + 2 * H)
        self.assertEqual(ids(a), set())

    def test_region_end_map(self):
        g = [{"id": "lsa", "holds": rf.expand({"q0"}), "end": "2026-11-08T04:45Z"},
             {"id": "noend", "holds": rf.expand({"q1"}), "end": None}]
        busy = rf.expand({"q0", "q1"}) | {"c88"}
        m = rf.region_end_map("/nonexistent-flags", g, busy, now=NOW)
        self.assertEqual(m["q0"], rf.iso_epoch("2026-11-08T04:45Z"))
        self.assertIsNone(m["q1"])
        self.assertNotIn("c88", m)   # foreign: unknown


if __name__ == "__main__":
    unittest.main()
